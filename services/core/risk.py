"""Risk service (Phase 3.3) — pre-trade checks. Extends the engine's static rules with
buying-power validation and a global kill switch (margin/PDT are future work).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class RiskConfig:
    max_order_quantity: int = 10_000 * 1000        # 10,000 units (scaled)
    max_order_value_cents: int = 1_000_000 * 100   # $1,000,000 notional


@dataclass
class RiskResult:
    ok: bool
    reason: str = ""


class RiskEngine:
    def __init__(self, config: Optional[RiskConfig] = None) -> None:
        self.config = config or RiskConfig()
        self.kill_switch = False

    def check(self, side: str, price: int, qty: int, notional_cents: int,
              available_cents: Optional[int] = None) -> RiskResult:
        if self.kill_switch:
            return RiskResult(False, "kill switch engaged")
        if qty <= 0:
            return RiskResult(False, "quantity must be positive")
        if price <= 0:
            return RiskResult(False, "price must be positive")
        if qty > self.config.max_order_quantity:
            return RiskResult(False, "exceeds max order quantity")
        if notional_cents > self.config.max_order_value_cents:
            return RiskResult(False, "exceeds max order value")
        if side == "buy" and available_cents is not None and notional_cents > available_cents:
            return RiskResult(False, "insufficient buying power")
        return RiskResult(True)

    def check_market(self, qty: int) -> RiskResult:
        """Pre-trade checks for market orders (no limit price; affordability enforced by
        cash-bounded matching, not a notional cap)."""
        if self.kill_switch:
            return RiskResult(False, "kill switch engaged")
        if qty <= 0:
            return RiskResult(False, "quantity must be positive")
        if qty > self.config.max_order_quantity:
            return RiskResult(False, "exceeds max order quantity")
        return RiskResult(True)
