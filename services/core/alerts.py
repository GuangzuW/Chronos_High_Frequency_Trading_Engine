"""Price alerts (Phase 7.4) — armed conditions fired when the market trades through a level.

The OMS calls `on_trade(symbol, price)` on every fill; armed alerts whose condition is met
fire once and move to the delivered log (a real notifier would push FCM/APNs/email here).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Alert:
    id: int
    account: str
    symbol: str
    op: str       # "above" | "below"
    price: int    # scaled
    status: str = "armed"  # armed | fired


class AlertEngine:
    def __init__(self) -> None:
        self._alerts: dict[int, Alert] = {}
        self._fired: list[Alert] = []
        self._next_id = 1

    def add(self, account: str, symbol: str, op: str, price: int) -> Alert:
        if op not in ("above", "below"):
            raise ValueError("op must be 'above' or 'below'")
        alert = Alert(self._next_id, account, symbol, op, price)
        self._alerts[alert.id] = alert
        self._next_id += 1
        return alert

    def on_trade(self, symbol: str, price: int) -> list[Alert]:
        fired = []
        for a in self._alerts.values():
            if a.status != "armed" or a.symbol != symbol:
                continue
            if (a.op == "above" and price >= a.price) or (a.op == "below" and price <= a.price):
                a.status = "fired"
                self._fired.append(a)
                fired.append(a)
        return fired

    def armed_for(self, account: str) -> list[Alert]:
        return [a for a in self._alerts.values() if a.account == account and a.status == "armed"]

    def fired_for(self, account: str) -> list[Alert]:
        return [a for a in self._fired if a.account == account]
