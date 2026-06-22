"""Lightweight Prometheus metrics for the API (no third-party deps).

Tracks HTTP request counts by status; business gauges are read from app state on scrape.
"""

from __future__ import annotations

import threading
from collections import Counter


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: Counter = Counter()

    def inc_request(self, status: int) -> None:
        with self._lock:
            self._requests[status] += 1

    def request_snapshot(self) -> dict[int, int]:
        with self._lock:
            return dict(self._requests)


def render_prometheus(metrics: Metrics, app) -> str:
    """Render the Prometheus text exposition format from request counters + app state."""
    lines: list[str] = []
    lines.append("# HELP chronos_http_requests_total HTTP requests by response status.")
    lines.append("# TYPE chronos_http_requests_total counter")
    for status, count in sorted(metrics.request_snapshot().items()):
        lines.append(f'chronos_http_requests_total{{status="{status}"}} {count}')

    gauges = {
        "chronos_instruments": len(app.ref.all()),
        "chronos_orders_total": app.oms.order_count(),
        "chronos_trades_total": len(app.trade_log.all()),
        "chronos_sse_clients": app.events.subscriber_count(),
    }
    for name, value in gauges.items():
        lines.append(f"# TYPE {name} gauge")
        lines.append(f"{name} {value}")
    return "\n".join(lines) + "\n"
