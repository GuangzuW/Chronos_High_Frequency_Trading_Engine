"""OHLC bar aggregation (Phase 2.2) — build candlesticks from a trade/tick stream."""

from __future__ import annotations

from typing import Iterable


def build_bars(ticks: Iterable[tuple[int, int, int]], bucket_ns: int) -> list[dict]:
    """Aggregate (ts_ns, price, qty) ticks into time-bucketed OHLCV bars (sorted by time).

    Prices/quantities stay in the engine's scaled integer units.
    """
    if bucket_ns <= 0:
        raise ValueError("bucket_ns must be positive")
    bars: dict[int, dict] = {}
    for ts_ns, price, qty in ticks:
        start = ts_ns - (ts_ns % bucket_ns)
        bar = bars.get(start)
        if bar is None:
            bars[start] = {"start": start, "open": price, "high": price,
                           "low": price, "close": price, "volume": qty}
        else:
            bar["high"] = max(bar["high"], price)
            bar["low"] = min(bar["low"], price)
            bar["close"] = price
            bar["volume"] += qty
    return [bars[k] for k in sorted(bars)]
