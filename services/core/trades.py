"""Trade history (the tape) — durable, queryable record of executions (Phase 3.4 / 7.x).

Each fill produced by the matching venue is recorded here with both counterparties' accounts,
so history can be served per-account or per-symbol. The monotonic `seq` also gives settlement
a collision-free transaction id. Persisted via the shared Database; replayed on restart.
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class TradeRecord:
    seq: int
    symbol: str
    buy_order_id: int
    sell_order_id: int
    buyer: str
    seller: str
    price: int   # scaled
    qty: int     # scaled
    ts_ns: int


class TradeLog:
    def __init__(self, db=None, clock=time.time_ns) -> None:
        self._trades: list[TradeRecord] = []
        self._next_seq = 1
        self._db = db
        self._clock = clock
        if db is not None:
            for row in db.load_trades():
                self._trades.append(TradeRecord(*row))
            if self._trades:
                self._next_seq = max(t.seq for t in self._trades) + 1

    def record(self, symbol: str, buy_order_id: int, sell_order_id: int,
               buyer: str, seller: str, price: int, qty: int) -> TradeRecord:
        rec = TradeRecord(self._next_seq, symbol, buy_order_id, sell_order_id,
                          buyer, seller, price, qty, self._clock())
        self._next_seq += 1
        self._trades.append(rec)
        if self._db is not None:
            self._db.save_trade((rec.seq, rec.symbol, rec.buy_order_id, rec.sell_order_id,
                                 rec.buyer, rec.seller, rec.price, rec.qty, rec.ts_ns))
        return rec

    def all(self) -> list[TradeRecord]:
        return list(self._trades)

    def for_account(self, account: str) -> list[TradeRecord]:
        return [t for t in self._trades if t.buyer == account or t.seller == account]

    def for_symbol(self, symbol: str) -> list[TradeRecord]:
        return [t for t in self._trades if t.symbol == symbol]
