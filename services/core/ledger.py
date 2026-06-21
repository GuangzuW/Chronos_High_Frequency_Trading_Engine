"""Ledger service (Phase 1.3) — event-sourced-lite double-entry accounting.

Money is integer cents. Every transaction must balance (legs sum to zero), so the sum of
all account balances is invariant at zero (a virtual EXTERNAL account funds the system).
Posting is idempotent by transaction id. Buying-power reservations (holds) model the cash
set aside when an order is placed and released on fill/cancel.
"""

from __future__ import annotations

EXTERNAL = "external"  # virtual funding counterparty; keeps the books balanced


class LedgerError(Exception):
    pass


class Ledger:
    def __init__(self, db=None) -> None:
        self._balance: dict[str, int] = {}
        self._reserved: dict[str, int] = {}
        self._applied: set[str] = set()          # idempotency by txn id
        self._holds: dict[str, tuple[str, int]] = {}
        self._journal: list[tuple[str, list[tuple[str, int]]]] = []  # append-only event log
        self._db = db
        if db is not None:
            # Rebuild the read model by replaying the persisted event log + active holds.
            for txn_id, legs in db.load_journal():
                self._apply(txn_id, legs)
            for hold_id, (account, amount) in db.load_holds().items():
                self._reserved[account] = self.reserved(account) + amount
                self._holds[hold_id] = (account, amount)

    def _apply(self, txn_id: str, legs: list[tuple[str, int]]) -> None:
        """Apply a balanced posting to the in-memory read model (no persistence)."""
        for account, delta in legs:
            self._balance[account] = self._balance.get(account, 0) + delta
        self._applied.add(txn_id)
        self._journal.append((txn_id, list(legs)))

    # ---- queries ----
    def balance(self, account: str) -> int:
        return self._balance.get(account, 0)

    def reserved(self, account: str) -> int:
        return self._reserved.get(account, 0)

    def available(self, account: str) -> int:
        return self.balance(account) - self.reserved(account)

    def total_balance(self) -> int:
        return sum(self._balance.values())

    def journal(self) -> list[tuple[str, list[tuple[str, int]]]]:
        return list(self._journal)

    # ---- postings ----
    def post(self, txn_id: str, legs: list[tuple[str, int]]) -> bool:
        """Apply a balanced set of (account, delta_cents) legs. Idempotent by txn_id."""
        if txn_id in self._applied:
            return False
        if sum(delta for _, delta in legs) != 0:
            raise LedgerError(f"unbalanced transaction {txn_id}: legs sum != 0")
        self._apply(txn_id, legs)
        if self._db is not None:
            self._db.append_journal(txn_id, legs)
        return True

    def fund(self, account: str, amount_cents: int, txn_id: str) -> bool:
        if amount_cents <= 0:
            raise LedgerError("fund amount must be positive")
        return self.post(txn_id, [(EXTERNAL, -amount_cents), (account, amount_cents)])

    def transfer(self, src: str, dst: str, amount_cents: int, txn_id: str) -> bool:
        if amount_cents <= 0:
            raise LedgerError("transfer amount must be positive")
        return self.post(txn_id, [(src, -amount_cents), (dst, amount_cents)])

    # ---- buying-power holds ----
    def reserve(self, hold_id: str, account: str, amount_cents: int) -> None:
        if hold_id in self._holds:
            raise LedgerError(f"hold {hold_id} already exists")
        if amount_cents < 0:
            raise LedgerError("reserve amount must be non-negative")
        if self.available(account) < amount_cents:
            raise LedgerError("insufficient buying power")
        self._reserved[account] = self.reserved(account) + amount_cents
        self._holds[hold_id] = (account, amount_cents)
        if self._db is not None:
            self._db.save_hold(hold_id, account, amount_cents)

    def release(self, hold_id: str) -> None:
        if hold_id not in self._holds:
            return
        account, amount = self._holds.pop(hold_id)
        self._reserved[account] = self.reserved(account) - amount
        if self._db is not None:
            self._db.delete_hold(hold_id)
