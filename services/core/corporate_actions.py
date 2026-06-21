"""Corporate actions (Phase 7.2) — splits and cash dividends applied to positions/ledger."""

from __future__ import annotations

from services.core.ledger import Ledger
from services.core.money import QUANTITY_SCALE
from services.core.oms import cash_account
from services.core.portfolio import Portfolio


class CorporateActions:
    def __init__(self, portfolio: Portfolio, ledger: Ledger) -> None:
        self.portfolio = portfolio
        self.ledger = ledger
        self._seq = 0

    def split(self, symbol: str, numerator: int, denominator: int = 1) -> dict:
        """Forward/reverse split numerator:denominator (2:1 -> qty doubles, cost basis unchanged
        so cost-per-share halves)."""
        if numerator <= 0 or denominator <= 0:
            raise ValueError("split ratio must be positive")
        self._seq += 1
        affected = 0
        for account, p in self.portfolio.holders(symbol):
            p.qty = p.qty * numerator // denominator
            self.portfolio.persist(account, symbol)
            affected += 1
        return {"symbol": symbol, "ratio": f"{numerator}:{denominator}", "accounts": affected}

    def dividend(self, symbol: str, per_share_cents: int) -> list[tuple[str, int]]:
        """Pay a cash dividend (cents per whole share) to long holders."""
        if per_share_cents <= 0:
            raise ValueError("dividend must be positive")
        self._seq += 1
        paid: list[tuple[str, int]] = []
        for account, p in self.portfolio.holders(symbol):
            if p.qty <= 0:
                continue
            shares = p.qty / QUANTITY_SCALE
            amount = int(round(per_share_cents * shares))
            if amount > 0:
                self.ledger.fund(cash_account(account), amount, f"div-{symbol}-{self._seq}-{account}")
                paid.append((account, amount))
        return paid
