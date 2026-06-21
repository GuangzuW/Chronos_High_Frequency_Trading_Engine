# Phase 5 — Equities MVP (Releasable Vertical Slice)

## Goal
Deliver the first end-to-end, releasable product: **trade equities on all four platforms** in
paper-trading mode against the Chronos venue. This is the integration milestone that proves the whole
stack from Phase 0–4.

## Tasks

### 5.1 Trading UI (equities)
- Watchlist, symbol search (Reference Data), real-time quote + chart (Market Data + client core),
  L2 order book and trade tape (client core book aggregation).
- Order ticket: market/limit/stop, TIF (GTC/IOC/FOK), quantity, buying-power-aware validation.
- **Verification:** placing an order from the ticket reaches the OMS and reflects state changes live.

### 5.2 Order & position blotters
- Open orders (live status from OMS events), order history, positions, realized/unrealized P&L
  (Portfolio projection).
- Cancel/replace from the UI.
- **Verification:** a fill updates the position blotter and P&L within the latency budget.

### 5.3 Funding & buying power (paper)
- Simulated funding into the Ledger; buying power reflected pre-trade and post-fill.
- **Verification:** buying power decreases on reservation and reconciles after fill/cancel.

### 5.4 Paper-trading venue profile
- Run Chronos with the simulator liquidity profile (from Phase 2.5) so orders actually fill in a
  realistic book.
- **Verification:** a marketable order fills against simulated liquidity; a passive order rests and
  fills when crossed.

### 5.5 End-to-end hardening of the slice
- Full trace coverage (client → BFF → OMS → Risk → Gateway → Chronos → Ledger → client).
- Contract tests green across every hop; E2E (Detox) covering place/fill/cancel on at least one mobile
  and one desktop target.
- **Verification:** the E2E suite passes in CI on a mobile + desktop target; dashboards show the slice's
  golden signals healthy under a load test.

## Exit criteria
A user on Android, iOS, macOS, or Windows can fund a paper account, see live data, place/cancel equity
orders, get fills from the Chronos venue, and watch positions and P&L update — observable end-to-end.
This is the first shippable build.
