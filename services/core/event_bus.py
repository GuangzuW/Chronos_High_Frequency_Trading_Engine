"""In-process pub/sub for streaming domain events to SSE clients.

The OMS publishes lightweight trade/order events; each SSE connection subscribes to its own
bounded queue. Publishing never blocks the trading path — if a slow consumer's queue fills,
the oldest events are dropped for that consumer only.
"""

from __future__ import annotations

import queue
import threading


class EventBus:
    def __init__(self, maxsize: int = 1000) -> None:
        self._subscribers: set[queue.Queue] = set()
        self._lock = threading.Lock()
        self._maxsize = maxsize

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=self._maxsize)
        with self._lock:
            self._subscribers.add(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            self._subscribers.discard(q)

    def publish(self, event: dict) -> None:
        with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(event)
            except queue.Full:
                pass  # drop for this slow consumer; never block the producer

    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)
