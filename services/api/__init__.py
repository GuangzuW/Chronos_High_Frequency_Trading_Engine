"""Chronos Trade — HTTP API service over the backend domain core.

A framework-agnostic application facade (`app.TradingApp`) wires the `services.core` bounded
contexts and exposes human-friendly operations (prices/quantities as floats, balances in
dollars). `server` exposes it over JSON/HTTP using only the Python standard library, so it
runs with zero third-party installs:

    PYTHONPATH=. python3 -m services.api.server      # listens on :8080 (PORT env to override)
"""
