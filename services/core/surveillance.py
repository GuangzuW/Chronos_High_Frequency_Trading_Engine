"""Trade surveillance (Phase 8.2) — post-trade pattern detection over the trade log."""

from __future__ import annotations

from services.core.trades import TradeRecord


def self_trades(trades: list[TradeRecord]) -> list[TradeRecord]:
    """Trades where the same account is on both sides (wash/self-trade indicator)."""
    return [t for t in trades if t.buyer == t.seller]


class Surveillance:
    def scan(self, trades: list[TradeRecord]) -> dict:
        st = self_trades(trades)
        return {
            "self_trades": [
                {"seq": t.seq, "account": t.buyer, "symbol": t.symbol,
                 "price": t.price, "qty": t.qty}
                for t in st
            ],
            "self_trade_count": len(st),
        }
