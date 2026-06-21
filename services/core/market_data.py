"""Market Data ingest (Phase 2.1) — provider abstraction + normalization.

Generalizes the bridge/feeder.py Finnhub prototype: any provider yields raw ticks which are
normalized into a canonical NormalizedTrade (engine fixed-point scaling). A deterministic
MockProvider makes the pipeline testable with no network; FinnhubProvider keeps the live
parsing logic (its WebSocket transport lives in the bridge and is not exercised in tests).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, Optional, Protocol

from services.core.money import to_price, to_quantity


@dataclass(frozen=True)
class NormalizedTrade:
    symbol: str       # internal (<=8 char) symbol
    price: int        # scaled x100
    quantity: int     # scaled x1000
    timestamp_ns: int


class MarketDataProvider(Protocol):
    def stream(self) -> Iterator[NormalizedTrade]:
        ...


class MockProvider:
    """Deterministic provider for tests: feed (symbol, price_float, qty_float, ts) tuples."""

    def __init__(self, ticks: Iterable[tuple[str, float, float, int]]) -> None:
        self._ticks = list(ticks)

    def stream(self) -> Iterator[NormalizedTrade]:
        for symbol, price, qty, ts in self._ticks:
            yield NormalizedTrade(symbol=symbol, price=to_price(price),
                                  quantity=to_quantity(qty), timestamp_ns=ts)


class FinnhubProvider:
    """Normalizes Finnhub trade messages. Transport (WebSocket) handled by bridge/feeder.py."""

    DEFAULT_SYMBOL_MAP = {
        "BINANCE:BTCUSDT": "BTC",
        "BINANCE:ETHUSDT": "ETH",
        "AAPL": "AAPL",
    }

    def __init__(self, symbol_map: Optional[dict[str, str]] = None) -> None:
        self.symbol_map = symbol_map or dict(self.DEFAULT_SYMBOL_MAP)

    def normalize_message(self, message: dict) -> list[NormalizedTrade]:
        """Parse a Finnhub `{"type":"trade","data":[{s,p,v,t}, ...]}` message."""
        if message.get("type") != "trade":
            return []
        out: list[NormalizedTrade] = []
        for d in message.get("data", []):
            internal = self.symbol_map.get(d.get("s"))
            if internal is None:
                continue
            out.append(NormalizedTrade(
                symbol=internal,
                price=to_price(d.get("p", 0.0)),
                quantity=max(1, to_quantity(d.get("v", 0.0))),
                timestamp_ns=int(d.get("t", 0)) * 1_000_000,  # Finnhub ms -> ns
            ))
        return out
