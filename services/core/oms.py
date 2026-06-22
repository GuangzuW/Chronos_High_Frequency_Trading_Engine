"""Order Management Service (Phase 3.2) — order lifecycle + placement saga.

Orchestrates a placement as: validate instrument -> reserve buying power (ledger) ->
pre-trade risk -> route to venue -> settle each fill (cash transfer + position updates) ->
release the hold. On validation/risk failure the buying-power reservation is released
(compensating action), so no orphaned holds remain.

Cash accounts follow the convention f"{account}:cash". Resting orders are tracked so that
when a later incoming order matches them, BOTH counterparties settle correctly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from services.core.ledger import Ledger, LedgerError
from services.core.matching import Fill, Venue
from services.core.money import PRICE_SCALE, QUANTITY_SCALE, notional_cents
from services.core.portfolio import Portfolio
from services.core.reference_data import ReferenceData
from services.core.risk import RiskEngine
from services.core.trades import TradeLog


def cash_account(account: str) -> str:
    return f"{account}:cash"


@dataclass
class Order:
    id: int
    account: str
    symbol: str
    side: str          # "buy" | "sell"
    price: int         # scaled
    qty: int           # scaled
    status: str = "new"  # new | partial | filled | rejected | canceled
    filled: int = 0
    reject_reason: str = ""
    tif: str = "gtc"           # gtc | ioc | fok  (limit orders)
    order_type: str = "limit"  # limit | market | stop | stop_limit
    stop_price: int = 0        # trigger price for stop / stop_limit (scaled)
    fills: list[Fill] = field(default_factory=list)


class OMS:
    def __init__(self, refdata: ReferenceData, ledger: Ledger, risk: RiskEngine,
                 portfolio: Portfolio, venue: Venue, db=None, trades: TradeLog | None = None,
                 alerts=None, events=None) -> None:
        self.refdata = refdata
        self.ledger = ledger
        self.risk = risk
        self.portfolio = portfolio
        self.venue = venue
        self.trades = trades if trades is not None else TradeLog(db=db)
        self.alerts = alerts
        self.events = events  # optional EventBus for live streaming
        self._db = db
        self._orders: dict[int, Order] = {}
        self._pending_stops: dict[int, Order] = {}   # stop orders awaiting their trigger
        self._last_price: dict[str, int] = {}        # last trade price per symbol
        self._next_id = 1000
        if db is not None:
            self._restore()

    def _restore(self) -> None:
        """Rebuild order history, the id sequence, the open book, pending stops, and the
        last trade price (from the trade log) from persisted state."""
        max_id = self._next_id - 1
        for (oid, account, symbol, side, price, qty, status, filled, reason,
             tif, order_type, stop_price) in self._db.load_orders():
            order = Order(id=oid, account=account, symbol=symbol, side=side, price=price, qty=qty,
                          status=status, filled=filled, reject_reason=reason, tif=tif,
                          order_type=order_type, stop_price=stop_price)
            self._orders[oid] = order
            max_id = max(max_id, oid)
            if status == "pending":
                self._pending_stops[oid] = order          # awaiting trigger; not in the book
            elif status in ("new", "partial"):
                remaining = qty - filled
                if remaining > 0:
                    self.venue.book(symbol).rest(oid, side, price, remaining)
        self._next_id = max_id + 1
        # Recover last trade price per symbol (do not auto-fire stops on boot).
        for t in self.trades.all():
            self._last_price[t.symbol] = t.price

    def _save(self, order: "Order") -> None:
        if self._db is not None:
            self._db.save_order((order.id, order.account, order.symbol, order.side, order.price,
                                 order.qty, order.status, order.filled, order.reject_reason,
                                 order.tif, order.order_type, order.stop_price))
        if self.events is not None:
            self.events.publish({
                "type": "order", "id": order.id, "account": order.account,
                "symbol": order.symbol, "side": order.side, "status": order.status,
                "filled": order.filled / QUANTITY_SCALE, "price": order.price / PRICE_SCALE,
            })

    def get(self, order_id: int) -> Order:
        if order_id not in self._orders:
            raise KeyError(f"unknown order: {order_id}")
        return self._orders[order_id]

    def last_price(self, symbol: str):
        return self._last_price.get(symbol)

    def order_count(self) -> int:
        return len(self._orders)

    def orders_for(self, account: str) -> list[Order]:
        """All orders (any status) for an account, newest first."""
        return sorted((o for o in self._orders.values() if o.account == account),
                      key=lambda o: o.id, reverse=True)

    def cancel(self, order_id: int) -> Order:
        """Cancel an open order: pull its remainder from the book, release any remaining
        buying-power hold, and mark it canceled. Only 'new'/'partial' orders are cancelable.
        """
        order = self.get(order_id)
        if order.status not in ("new", "partial"):
            raise ValueError(f"cannot cancel order in status '{order.status}'")
        self.venue.book(order.symbol).remove(order_id, order.side, order.price)
        if order.side == "buy":
            self.ledger.release(f"hold-{order_id}")  # release the unfilled remainder's reservation
        order.status = "canceled"
        self._save(order)
        return order

    def place(self, account: str, symbol: str, side: str, price: int = 0, qty: int = 0,
              tif: str = "gtc", order_type: str = "limit", stop_price: int = 0) -> Order:
        tif = tif.lower()
        order_type = order_type.lower()
        order_id = self._next_id
        self._next_id += 1
        order = Order(id=order_id, account=account, symbol=symbol, side=side, price=price,
                      qty=qty, tif=tif, order_type=order_type, stop_price=stop_price)
        self._orders[order_id] = order

        if order_type not in ("limit", "market", "stop", "stop_limit"):
            return self._reject(order, f"invalid order type: {order_type}")
        if order_type == "limit" and tif not in ("gtc", "ioc", "fok"):
            return self._reject(order, f"invalid time-in-force: {tif}")
        if not self.refdata.exists(symbol):
            return self._reject(order, f"unknown instrument: {symbol}")

        if order_type in ("stop", "stop_limit"):
            result = self._place_stop(order)
        elif order_type == "market":
            result = self._place_market(order)
        else:
            result = self._place_limit(order)
        # A new trade may have moved the last price — fire any stops it triggers (cascading).
        self._process_triggers(symbol)
        return result

    def place_combo(self, account: str, legs: list[dict]) -> dict:
        """Atomic multi-leg order (e.g. a vertical spread): every leg fully fills at its limit
        now, or the whole combo is rejected with no fills. Legs: {symbol, side, price, qty}.

        Assumes distinct symbols per leg (typical for option spreads — different strikes). Each
        leg's individual buying-power/risk still applies; the combo additionally pre-checks that
        the summed buy-leg cost is affordable.
        """
        for leg in legs:
            if not self.refdata.exists(leg["symbol"]):
                return {"status": "rejected", "reason": f"unknown instrument: {leg['symbol']}", "legs": []}

        total_buy = sum(notional_cents(leg["price"], leg["qty"], self._mult(leg["symbol"]))
                        for leg in legs if leg["side"] == "buy")
        if total_buy > self.ledger.available(cash_account(account)):
            return {"status": "rejected", "reason": "insufficient buying power for combo", "legs": []}

        # Atomic precondition: every leg must be fully fillable right now.
        for leg in legs:
            book = self.venue.book(leg["symbol"])
            if book.fillable_qty(leg["side"], leg["price"]) < leg["qty"]:
                return {"status": "rejected", "reason": "combo not fully fillable now", "legs": []}

        # All legs fill (IOC fully completes given the pre-check).
        child_ids = []
        for leg in legs:
            child = self.place(account, leg["symbol"], leg["side"], leg["price"], leg["qty"], tif="ioc")
            child_ids.append(child.id)
        return {"status": "filled", "legs": child_ids}

    def _mult(self, symbol: str) -> int:
        return self.refdata.get(symbol).multiplier

    def _place_limit(self, order: Order) -> Order:
        account, side, price, qty = order.account, order.side, order.price, order.qty
        notional = notional_cents(price, qty, self._mult(order.symbol))
        hold_id = f"hold-{order.id}"
        reserved = False

        # Reserve buying power for buys (compensating release on later failure).
        if side == "buy":
            try:
                self.ledger.reserve(hold_id, cash_account(account), notional)
                reserved = True
            except LedgerError as e:
                return self._reject(order, str(e))

        # Pre-trade risk.
        available = self.ledger.available(cash_account(account)) + (notional if reserved else 0)
        result = self.risk.check(side, price, qty, notional,
                                 available_cents=available if side == "buy" else None)
        if not result.ok:
            if reserved:
                self.ledger.release(hold_id)  # compensation
            return self._reject(order, result.reason)

        book = self.venue.book(order.symbol)

        # Fill-or-kill: execute only if the whole order can fill right now, else kill.
        if order.tif == "fok" and book.fillable_qty(side, price) < qty:
            if reserved:
                self.ledger.release(hold_id)
            order.status = "canceled"
            order.reject_reason = "fill-or-kill: insufficient immediate liquidity"
            self._save(order)
            return order

        # GTC rests the remainder; IOC/FOK never rest.
        rest_remainder = order.tif == "gtc"
        fills, remaining = book.add_limit(order.id, side, price, qty, rest_remainder=rest_remainder)
        self._apply_fills(order, fills, remaining)

        if order.tif == "gtc":
            order.status = "filled" if remaining == 0 else ("partial" if order.filled > 0 else "new")
            if reserved:
                self._resync_buy_hold(order)   # keep reservation for the resting remainder
        else:  # ioc / fok — nothing rests
            order.status = "filled" if remaining == 0 else "canceled"
            if reserved:
                self.ledger.release(hold_id)   # release the entire reservation
        self._save(order)
        return order

    def _place_market(self, order: Order) -> Order:
        # Market orders have no limit price; affordability is enforced by cash-bounded
        # matching, and they never rest (IOC by nature).
        result = self.risk.check_market(order.qty)
        if not result.ok:
            return self._reject(order, result.reason)

        book = self.venue.book(order.symbol)
        mult = self._mult(order.symbol)
        if order.side == "buy":
            budget = self.ledger.available(cash_account(order.account))
            fills, remaining, _ = book.match_market(order.id, "buy", order.qty,
                                                    budget_cents=budget, multiplier=mult)
        else:
            fills, remaining, _ = book.match_market(order.id, "sell", order.qty, multiplier=mult)
        self._apply_fills(order, fills, remaining)
        order.status = "filled" if remaining == 0 else "canceled"  # market never rests
        self._save(order)
        return order

    def _apply_fills(self, order: Order, fills: list[Fill], remaining: int) -> None:
        for f in fills:
            self._settle(order.symbol, f)
            resting_id = f.sell_order_id if order.side == "buy" else f.buy_order_id
            self._advance(self._orders[resting_id], f.qty)
            self._last_price[order.symbol] = f.price  # drives stop-order triggers
            if self.alerts is not None:
                self.alerts.on_trade(order.symbol, f.price)
        order.fills = fills
        order.filled = order.qty - remaining

    # ---- stop orders -------------------------------------------------------------------
    def _place_stop(self, order: Order) -> Order:
        """Register a stop / stop-limit order as pending; it activates when the market trades
        through its stop price (see _process_triggers). Nothing is reserved while pending."""
        if order.stop_price <= 0:
            return self._reject(order, "stop price must be positive")
        if order.order_type == "stop_limit" and order.price <= 0:
            return self._reject(order, "stop-limit requires a positive limit price")
        order.status = "pending"
        self._pending_stops[order.id] = order
        self._save(order)
        return order

    def _stop_triggered(self, order: Order, last: int | None) -> bool:
        if last is None:
            return False
        # Buy stops fire when price rises to/through the stop; sell stops when it falls.
        return last >= order.stop_price if order.side == "buy" else last <= order.stop_price

    def _process_triggers(self, symbol: str) -> None:
        """Fire any pending stops for `symbol` whose trigger condition is now met. Activating
        one may move the price and trigger others, so loop until quiescent (cascade-safe)."""
        while True:
            ready = [o for o in self._pending_stops.values()
                     if o.symbol == symbol and self._stop_triggered(o, self._last_price.get(symbol))]
            if not ready:
                return
            order = min(ready, key=lambda o: o.id)  # deterministic order
            del self._pending_stops[order.id]
            self._activate(order)

    def _activate(self, order: Order) -> None:
        """Convert a triggered stop into a live order: stop -> market, stop_limit -> limit."""
        if order.order_type == "stop":
            self._place_market(order)
        else:  # stop_limit -> limit (GTC: rests any unfilled remainder)
            self._place_limit(order)

    # ---- internals ----
    def _reject(self, order: Order, reason: str) -> Order:
        order.status = "rejected"
        order.reject_reason = reason
        self._save(order)
        return order

    def _settle(self, symbol: str, f: Fill) -> None:
        buy = self._orders[f.buy_order_id]
        sell = self._orders[f.sell_order_id]
        mult = self._mult(symbol)
        value = notional_cents(f.price, f.qty, mult)
        # Record the execution (its monotonic seq is also a collision-free settlement txn id).
        rec = self.trades.record(symbol, f.buy_order_id, f.sell_order_id,
                                 buy.account, sell.account, f.price, f.qty)
        # Cash moves from buyer to seller (balanced transfer keeps the ledger at zero).
        self.ledger.transfer(cash_account(buy.account), cash_account(sell.account),
                             value, f"trade-{rec.seq}")
        # Positions.
        self.portfolio.on_fill(buy.account, symbol, "buy", f.price, f.qty, mult)
        self.portfolio.on_fill(sell.account, symbol, "sell", f.price, f.qty, mult)
        if self.events is not None:
            self.events.publish({
                "type": "trade", "symbol": symbol, "seq": rec.seq,
                "price": f.price / PRICE_SCALE, "quantity": f.qty / QUANTITY_SCALE,
            })

    def _advance(self, order: Order, qty: int) -> None:
        """Advance a resting order's fill state when a later order matches against it."""
        order.filled = min(order.qty, order.filled + qty)
        order.status = "filled" if order.filled >= order.qty else "partial"
        self._resync_buy_hold(order)  # a resting buy releases reservation as it fills
        self._save(order)

    def _resync_buy_hold(self, order: Order) -> None:
        """Set a buy order's reservation to its unfilled remainder (no-op for sells).

        Cash for filled quantity is debited via settlement; only the resting remainder
        stays reserved. Releasing then re-reserving keeps available buying power exact.
        """
        if order.side != "buy":
            return
        hold_id = f"hold-{order.id}"
        self.ledger.release(hold_id)
        remaining = order.qty - order.filled
        if remaining > 0:
            self.ledger.reserve(hold_id, cash_account(order.account),
                                notional_cents(order.price, remaining, self._mult(order.symbol)))
