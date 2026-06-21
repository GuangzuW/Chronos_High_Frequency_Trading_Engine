"""TradingApp — framework-agnostic application facade over services.core.

Translates between the human/API world (prices & quantities as floats, money in dollars)
and the engine's fixed-point integers, and wires the bounded contexts into one cohesive
backend. Methods return plain JSON-able dicts so any transport (HTTP, gRPC, CLI) can use it.
"""

from __future__ import annotations

from datetime import date

from services.core import pricing
from services.core import statements as statements_mod
from services.core.alerts import AlertEngine
from services.core.corporate_actions import CorporateActions
from services.core.event_bus import EventBus
from services.core.ledger import Ledger
from services.core.matching import Venue
from services.core.ohlc import build_bars
from services.core.surveillance import Surveillance
from services.core.money import (
    PRICE_SCALE,
    QUANTITY_SCALE,
    from_cents,
    to_price,
    to_quantity,
)
from services.core.oms import OMS, Order, cash_account
from services.core.portfolio import Portfolio
from services.core.reference_data import Instrument, ReferenceData
from services.core.risk import RiskEngine
from services.core.trades import TradeLog


def _instrument_dict(i: Instrument) -> dict:
    d = {"symbol": i.symbol, "kind": i.kind}
    if i.kind == "option":
        d.update({
            "underlying": i.underlying,
            "expiry": i.expiry,
            "strike": (i.strike or 0) / PRICE_SCALE,
            "right": i.right,
            "multiplier": i.multiplier,
        })
    return d


class TradingApp:
    def __init__(self, db_path: str | None = None) -> None:
        # db_path enables SQLite persistence (balances, holds, orders, positions survive
        # restart). Reference data is config — re-seed instruments at boot regardless.
        self._db = None
        if db_path is not None:
            from services.core.persistence import Database
            self._db = Database(db_path)
        self.ref = ReferenceData()
        self.ledger = Ledger(db=self._db)
        self.risk = RiskEngine()
        self.portfolio = Portfolio(db=self._db)
        self.venue = Venue()
        self.trade_log = TradeLog(db=self._db)
        self.alerts = AlertEngine()
        self.events = EventBus()
        self.corporate_actions = CorporateActions(self.portfolio, self.ledger)
        self.surveillance = Surveillance()
        self.oms = OMS(self.ref, self.ledger, self.risk, self.portfolio, self.venue,
                       db=self._db, trades=self.trade_log, alerts=self.alerts, events=self.events)
        # Seed the funding counter past the replayed journal so fund txn ids stay unique
        # across restarts (otherwise a repeat fund would be a no-op via idempotency).
        self._fund_seq = len(self.ledger.journal())

    def close(self) -> None:
        if self._db is not None:
            self._db.close()

    # ---- reference data ----
    def add_equity(self, symbol: str) -> dict:
        return _instrument_dict(self.ref.add_equity(symbol))

    def add_option(self, symbol: str, underlying: str, expiry: str, strike: float,
                   right: str, multiplier: int = 100) -> dict:
        inst = self.ref.add_option(symbol, underlying, expiry, to_price(strike), right, multiplier)
        return _instrument_dict(inst)

    def instrument(self, symbol: str) -> dict:
        return _instrument_dict(self.ref.get(symbol))

    def instruments(self) -> dict:
        return {"instruments": [_instrument_dict(i) for i in self.ref.all()]}

    def markets(self) -> dict:
        """One-shot quote board for all instruments (last + best bid/ask) — powers a watchlist."""
        rows = []
        for inst in self.ref.all():
            book = self.venue.book(inst.symbol)
            bb, ba = book.best_bid(), book.best_ask()
            last = self.oms.last_price(inst.symbol)
            rows.append({
                "symbol": inst.symbol, "kind": inst.kind,
                "last": (last / PRICE_SCALE) if last is not None else None,
                "best_bid": (bb / PRICE_SCALE) if bb is not None else None,
                "best_ask": (ba / PRICE_SCALE) if ba is not None else None,
            })
        return {"markets": rows}

    def snapshot(self, symbol: str) -> dict:
        """Aggregate view for a UI poll: book depth + recent tape + last/best prices."""
        book = self.book(symbol)
        last = self.oms.last_price(symbol)
        return {
            "symbol": symbol,
            "last": (last / PRICE_SCALE) if last is not None else None,
            "best_bid": book["bids"][0]["price"] if book["bids"] else None,
            "best_ask": book["asks"][0]["price"] if book["asks"] else None,
            "bids": book["bids"],
            "asks": book["asks"],
            "trades": self.symbol_trades(symbol)["trades"][-40:],
        }

    def chain(self, underlying: str) -> list[dict]:
        return [_instrument_dict(i) for i in self.ref.chain(underlying)]

    # ---- accounts / ledger ----
    def fund(self, account: str, amount: float) -> dict:
        self._fund_seq += 1
        self.ledger.fund(cash_account(account), to_price(amount), f"fund-{account}-{self._fund_seq}")
        return self.balance(account)

    def balance(self, account: str) -> dict:
        c = cash_account(account)
        return {
            "account": account,
            "cash": from_cents(self.ledger.balance(c)),
            "available": from_cents(self.ledger.available(c)),
            "reserved": from_cents(self.ledger.reserved(c)),
        }

    def positions(self, account: str) -> dict:
        out = []
        for symbol, p in self.portfolio.holdings(account).items():
            out.append({
                "symbol": symbol,
                "quantity": p.qty / QUANTITY_SCALE,
                "cost_basis": from_cents(p.cost_cents),
                "realized_pnl": from_cents(p.realized_cents),
            })
        return {"account": account, "positions": out}

    # ---- trading ----
    def place_order(self, account: str, symbol: str, side: str, price: float = 0.0,
                    quantity: float = 0.0, tif: str = "gtc", order_type: str = "limit",
                    stop_price: float = 0.0) -> dict:
        order = self.oms.place(account, symbol, side, to_price(price), to_quantity(quantity),
                               tif=tif, order_type=order_type, stop_price=to_price(stop_price))
        return self._order_dict(order)

    def place_combo(self, account: str, legs: list[dict]) -> dict:
        scaled = [{"symbol": leg["symbol"], "side": leg["side"],
                   "price": to_price(leg["price"]), "qty": to_quantity(leg["quantity"])}
                  for leg in legs]
        result = self.oms.place_combo(account, scaled)
        result["orders"] = [self._order_dict(self.oms.get(oid)) for oid in result.get("legs", [])]
        return result

    def get_order(self, order_id: int) -> dict:
        return self._order_dict(self.oms.get(order_id))

    def orders(self, account: str) -> dict:
        return {"account": account,
                "orders": [self._order_dict(o) for o in self.oms.orders_for(account)]}

    def cashflow(self, account: str) -> dict:
        """Cash-balance time series for an account, derived from the ledger journal.
        Each point is the running cash after a posting that touched the account."""
        cash = cash_account(account)
        bal = 0
        funded = 0
        series = []
        step = 0
        for txn_id, legs in self.ledger.journal():
            delta = sum(d for acct, d in legs if acct == cash)
            if delta == 0:
                continue
            bal += delta
            step += 1
            kind = txn_id.split("-", 1)[0]  # fund | trade | div | ...
            if kind == "fund":
                funded += delta
            series.append({"step": step, "txn": txn_id, "kind": kind,
                           "delta": from_cents(delta), "balance": from_cents(bal)})
        return {
            "account": account,
            "series": series,
            "ending_cash": from_cents(bal),
            "funded": from_cents(funded),
            "net_ex_funding": from_cents(bal - funded),
        }

    def cancel_order(self, order_id: int) -> dict:
        return self._order_dict(self.oms.cancel(order_id))

    def book(self, symbol: str) -> dict:
        bids, asks = self.venue.book(symbol).depth()
        return {
            "symbol": symbol,
            "bids": [{"price": p / PRICE_SCALE, "quantity": q / QUANTITY_SCALE} for p, q in bids],
            "asks": [{"price": p / PRICE_SCALE, "quantity": q / QUANTITY_SCALE} for p, q in asks],
        }

    def trades(self, account: str) -> dict:
        """Account-centric trade history (side/counterparty relative to this account)."""
        out = []
        for t in self.trade_log.for_account(account):
            side = "buy" if t.buyer == account else "sell"
            out.append({
                "seq": t.seq,
                "symbol": t.symbol,
                "side": side,
                "price": t.price / PRICE_SCALE,
                "quantity": t.qty / QUANTITY_SCALE,
                "counterparty": t.seller if side == "buy" else t.buyer,
                "buy_order_id": t.buy_order_id,
                "sell_order_id": t.sell_order_id,
                "ts_ns": t.ts_ns,
            })
        return {"account": account, "trades": out}

    def symbol_trades(self, symbol: str) -> dict:
        """Public tape for a symbol."""
        return {"symbol": symbol, "trades": [
            {"seq": t.seq, "price": t.price / PRICE_SCALE, "quantity": t.qty / QUANTITY_SCALE,
             "buy_order_id": t.buy_order_id, "sell_order_id": t.sell_order_id, "ts_ns": t.ts_ns}
            for t in self.trade_log.for_symbol(symbol)]}

    # ---- alerts (Phase 7.4) ----
    def add_alert(self, account: str, symbol: str, op: str, price: float) -> dict:
        a = self.alerts.add(account, symbol, op, to_price(price))
        return {"id": a.id, "symbol": a.symbol, "op": a.op, "price": a.price / PRICE_SCALE,
                "status": a.status}

    def alerts_for(self, account: str) -> dict:
        def dump(a):
            return {"id": a.id, "symbol": a.symbol, "op": a.op,
                    "price": a.price / PRICE_SCALE, "status": a.status}
        return {"account": account,
                "armed": [dump(a) for a in self.alerts.armed_for(account)],
                "fired": [dump(a) for a in self.alerts.fired_for(account)]}

    # ---- corporate actions (Phase 7.2) ----
    def apply_split(self, symbol: str, numerator: int, denominator: int = 1) -> dict:
        return self.corporate_actions.split(symbol, numerator, denominator)

    def apply_dividend(self, symbol: str, per_share: float) -> dict:
        paid = self.corporate_actions.dividend(symbol, to_price(per_share))
        return {"symbol": symbol, "paid": [{"account": a, "amount": amt / PRICE_SCALE} for a, amt in paid]}

    # ---- statements / surveillance / OHLC ----
    def statement(self, account: str) -> dict:
        return statements_mod.account_statement(account, self.ledger, self.trade_log, self.portfolio)

    def run_surveillance(self) -> dict:
        return self.surveillance.scan(self.trade_log.all())

    def ohlc(self, symbol: str, bucket_ns: int) -> dict:
        ticks = [(t.ts_ns, t.price, t.qty) for t in self.trade_log.for_symbol(symbol)]
        return {"symbol": symbol, "bucket_ns": bucket_ns, "bars": build_bars(ticks, bucket_ns)}

    # ---- analytics ----
    def price_option(self, S: float, K: float, t: float, r: float, sigma: float, right: str) -> dict:
        g = pricing.greeks(S, K, t, r, sigma, right)
        return {"price": g.price, "delta": g.delta, "gamma": g.gamma,
                "vega": g.vega, "theta": g.theta, "rho": g.rho}

    def position_greeks(self, account: str, spots: dict | None = None, rate: float = 0.05,
                        vol: float = 0.2, as_of: str | None = None) -> dict:
        """Aggregate Greeks across an account's option positions, scaled by signed position
        size x contract multiplier. `spots` maps underlying -> spot; any missing underlying
        falls back to the engine's last trade price. `as_of` defaults to today."""
        spots = dict(spots or {})
        as_of_d = date.fromisoformat(as_of) if as_of else date.today()
        net = {"delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0, "rho": 0.0}
        positions = []
        for symbol, p in self.portfolio.holdings(account).items():
            if p.qty == 0:
                continue
            inst = self.ref.get(symbol)
            if inst.kind != "option":
                continue
            spot = spots.get(inst.underlying)
            if spot is None:
                last = self.oms.last_price(inst.underlying)  # fall back to last trade
                spot = (last / PRICE_SCALE) if last is not None else None
            if spot is None:
                continue
            strike = (inst.strike or 0) / PRICE_SCALE
            t = max(0.0, (date.fromisoformat(inst.expiry) - as_of_d).days / 365.0)
            g = pricing.greeks(spot, strike, t, rate, vol, inst.right)
            factor = (p.qty / QUANTITY_SCALE) * inst.multiplier   # signed (short < 0)
            for k in net:
                net[k] += getattr(g, k) * factor
            positions.append({"symbol": symbol, "contracts": p.qty / QUANTITY_SCALE,
                              "delta": g.delta, "gamma": g.gamma, "vega": g.vega,
                              "theta": g.theta, "rho": g.rho})
        return {"account": account, "net": net, "positions": positions}

    # ---- internals ----
    def _order_dict(self, o: Order) -> dict:
        return {
            "id": o.id,
            "account": o.account,
            "symbol": o.symbol,
            "side": o.side,
            "tif": o.tif,
            "order_type": o.order_type,
            "stop_price": o.stop_price / PRICE_SCALE,
            "price": o.price / PRICE_SCALE,
            "quantity": o.qty / QUANTITY_SCALE,
            "status": o.status,
            "filled": o.filled / QUANTITY_SCALE,
            "reject_reason": o.reject_reason,
            "fills": [
                {"buy_order_id": f.buy_order_id, "sell_order_id": f.sell_order_id,
                 "price": f.price / PRICE_SCALE, "quantity": f.qty / QUANTITY_SCALE}
                for f in o.fills
            ],
        }
