"""Account statements (Phase 7.3) — reconcile cash postings, trades and positions."""

from __future__ import annotations

from services.core.ledger import Ledger
from services.core.oms import cash_account
from services.core.portfolio import Portfolio
from services.core.trades import TradeLog


def account_statement(account: str, ledger: Ledger, trades: TradeLog,
                      portfolio: Portfolio) -> dict:
    cash_acct = cash_account(account)
    cash_postings = [
        {"txn": txn_id, "delta": delta}
        for txn_id, legs in ledger.journal()
        for acct, delta in legs
        if acct == cash_acct
    ]
    account_trades = [
        {"seq": t.seq, "symbol": t.symbol,
         "side": "buy" if t.buyer == account else "sell",
         "price": t.price, "qty": t.qty}
        for t in trades.for_account(account)
    ]
    positions = [
        {"symbol": sym, "qty": p.qty, "cost_cents": p.cost_cents,
         "realized_cents": p.realized_cents}
        for sym, p in portfolio.holdings(account).items()
    ]
    return {
        "account": account,
        "ending_cash_cents": ledger.balance(cash_acct),
        "reserved_cents": ledger.reserved(cash_acct),
        "cash_postings": cash_postings,
        "trades": account_trades,
        "positions": positions,
    }
