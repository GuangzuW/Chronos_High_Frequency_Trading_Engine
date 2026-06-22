"""Per-client token-bucket rate limiter (thread-safe, no deps).

Disabled when rate_per_min <= 0. Applied to mutating requests in the server.
"""

from __future__ import annotations

import threading
import time


class RateLimiter:
    def __init__(self, rate_per_min: int) -> None:
        self.capacity = float(rate_per_min)
        self.refill_per_sec = rate_per_min / 60.0
        self._buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_ts)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        if self.capacity <= 0:
            return True  # disabled
        now = time.monotonic()
        with self._lock:
            tokens, last = self._buckets.get(key, (self.capacity, now))
            tokens = min(self.capacity, tokens + (now - last) * self.refill_per_sec)
            if tokens < 1.0:
                self._buckets[key] = (tokens, now)
                return False
            self._buckets[key] = (tokens - 1.0, now)
            return True
