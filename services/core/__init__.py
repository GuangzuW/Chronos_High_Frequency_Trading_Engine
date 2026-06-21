"""Chronos Trade — backend domain core (runnable Python reference implementation).

This package implements the *business logic* of the platform's bounded contexts as pure,
dependency-free, fully-tested Python — runnable without Docker/Kafka/Postgres or the C++
engine. It is the executable reference the production services (Go/C++) are specified
against, and it lets the whole trade lifecycle be exercised end-to-end in tests.

Modules ↔ roadmap phases:
  money          — fixed-point money/quantity helpers (shared convention)
  reference_data — instruments, option contracts, calendar          (Phase 1.4)
  ledger         — double-entry ledger, balances, buying-power holds (Phase 1.3)
  risk           — static + buying-power pre-trade checks, kill switch (Phase 3.3)
  matching       — price-time-priority limit order book (venue)       (Phase 3 / mirrors C++ engine)
  portfolio      — positions, cost basis, realized/unrealized P&L      (Phase 3.4 / 7.1)
  oms            — order lifecycle + placement saga                    (Phase 3.2)
  pricing        — Black-Scholes, Greeks, implied volatility           (Phase 6.1)
  market_data    — provider-abstracted ingest + normalization          (Phase 2.1)

NOT implemented here (need infrastructure/toolchains absent from a pure-Python env, see
Plan/Platform/01-task-list.md): containerization/mesh/IaC, Kafka eventing, persistent
stores, OIDC identity, the React Native + C++/JSI clients, options multi-leg combos,
settlement, compliance, and scale/DR.
"""
