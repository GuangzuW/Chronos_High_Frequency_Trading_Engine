"""Portfolio service (Phase 3.4 / 7.1) — positions, cost basis, realized/unrealized P&L.

Cost basis is tracked in cents for the open long quantity; selling realizes the
proportional gain/loss. (Long-only cost-basis model for the reference; shorting reduces
qty below zero without cost-basis tracking.)
"""

from __future__ import annotations

from dataclasses import dataclass

from services.core.money import notional_cents


@dataclass
class Position:
    qty: int = 0             # scaled (x1000)
    cost_cents: int = 0      # cost basis of the current long qty
    realized_cents: int = 0


class Portfolio:
    def __init__(self, db=None) -> None:
        self._positions: dict[tuple[str, str], Position] = {}
        self._db = db
        if db is not None:
            for account, symbol, qty, cost_cents, realized_cents in db.load_positions():
                self._positions[(account, symbol)] = Position(qty, cost_cents, realized_cents)

    def _persist(self, account: str, symbol: str) -> None:
        if self._db is not None:
            p = self._positions[(account, symbol)]
            self._db.save_position(account, symbol, p.qty, p.cost_cents, p.realized_cents)

    def position(self, account: str, symbol: str) -> Position:
        return self._positions.setdefault((account, symbol), Position())

    def holdings(self, account: str) -> dict[str, Position]:
        """All positions for an account, keyed by symbol."""
        return {sym: p for (acct, sym), p in self._positions.items() if acct == account}

    def holders(self, symbol: str) -> list[tuple[str, Position]]:
        """All (account, position) pairs holding a non-zero position in a symbol."""
        return [(acct, p) for (acct, sym), p in self._positions.items()
                if sym == symbol and p.qty != 0]

    def persist(self, account: str, symbol: str) -> None:
        """Public hook for external mutators (e.g. corporate actions) to persist a change."""
        self._persist(account, symbol)

    def seed(self, account: str, symbol: str, qty: int, price: int, multiplier: int = 1) -> None:
        p = self.position(account, symbol)
        p.qty += qty
        p.cost_cents += notional_cents(price, qty, multiplier)
        self._persist(account, symbol)

    def on_fill(self, account: str, symbol: str, side: str, price: int, qty: int,
                multiplier: int = 1) -> None:
        p = self.position(account, symbol)
        value = notional_cents(price, qty, multiplier)
        if side == "buy":
            p.qty += qty
            p.cost_cents += value
        else:  # sell
            if p.qty > 0:
                cost_portion = p.cost_cents * qty // p.qty
                p.realized_cents += value - cost_portion
                p.cost_cents -= cost_portion
            p.qty -= qty
        self._persist(account, symbol)

    def unrealized_cents(self, account: str, symbol: str, mark_price: int) -> int:
        p = self.position(account, symbol)
        if p.qty <= 0:
            return 0
        return notional_cents(mark_price, p.qty) - p.cost_cents
