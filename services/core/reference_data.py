"""Reference Data service (Phase 1.4) — instruments, option contracts, trading calendar."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class Instrument:
    symbol: str
    kind: str  # "equity" | "option"
    tick: int = 1            # min price increment (scaled)
    lot: int = 1000          # min quantity increment (scaled; 1.000 units)
    # Option-only fields:
    underlying: Optional[str] = None
    expiry: Optional[str] = None      # ISO date
    strike: Optional[int] = None      # scaled price
    right: Optional[str] = None       # "call" | "put"
    multiplier: int = 1               # shares per contract (1 for equities; e.g. 100 for options)


class ReferenceData:
    def __init__(self) -> None:
        self._instruments: dict[str, Instrument] = {}
        self._holidays: set[str] = set()

    def add(self, inst: Instrument) -> Instrument:
        if len(inst.symbol) > 8:
            raise ValueError(f"symbol '{inst.symbol}' exceeds 8 chars (wire limit)")
        self._instruments[inst.symbol] = inst
        return inst

    def add_equity(self, symbol: str, tick: int = 1, lot: int = 1000) -> Instrument:
        return self.add(Instrument(symbol=symbol, kind="equity", tick=tick, lot=lot))

    def add_option(self, symbol: str, underlying: str, expiry: str, strike: int,
                   right: str, multiplier: int = 100) -> Instrument:
        if right not in ("call", "put"):
            raise ValueError("right must be 'call' or 'put'")
        return self.add(Instrument(symbol=symbol, kind="option", underlying=underlying,
                                   expiry=expiry, strike=strike, right=right,
                                   multiplier=multiplier))

    def get(self, symbol: str) -> Instrument:
        if symbol not in self._instruments:
            raise KeyError(f"unknown instrument: {symbol}")
        return self._instruments[symbol]

    def exists(self, symbol: str) -> bool:
        return symbol in self._instruments

    def all(self) -> list[Instrument]:
        return list(self._instruments.values())

    def chain(self, underlying: str) -> list[Instrument]:
        """All option contracts on an underlying, sorted by (expiry, strike, right)."""
        opts = [i for i in self._instruments.values()
                if i.kind == "option" and i.underlying == underlying]
        return sorted(opts, key=lambda i: (i.expiry or "", i.strike or 0, i.right or ""))

    # ---- Trading calendar ----
    def add_holiday(self, iso_date: str) -> None:
        self._holidays.add(iso_date)

    def is_trading_day(self, d: date) -> bool:
        if d.weekday() >= 5:  # Sat/Sun
            return False
        return d.isoformat() not in self._holidays
