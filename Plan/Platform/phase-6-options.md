# Phase 6 — Options Trading

## Goal
Add the second asset class: **options**. Chains, pricing/Greeks, single- and multi-leg orders, and
options-aware risk/margin.

## Tasks

### 6.1 Pricing / Analytics service
- C++ (or Rust) service computing **Black-Scholes** + **binomial** prices, **Greeks** (Δ, Γ, Θ, V, ρ),
  and **implied volatility** (root-find). Reuse Chronos numeric idioms (fixed-point/strong types where
  it makes sense; floats for analytics).
- Caching of surfaces; batch endpoints for full chains.
- Property tests (put-call parity, IV round-trip) and benchmarks.
- **Verification:** parity holds within tolerance; Greeks match a reference implementation; full-chain
  pricing meets latency budget.

### 6.2 Options reference data & chains
- Extend Reference Data (§1.4) contract resolution; expiry/strike grids; multipliers; assignment rules.
- Chain snapshot + streaming (coordinates with §2.4).
- **Verification:** UI renders a full chain with live bid/ask/IV/Greeks per contract.

### 6.3 Options order types & multi-leg
- Single-leg buy/sell to open/close; **multi-leg strategies** (verticals, straddles, spreads,
  iron condor) as atomic combo orders.
- Extend OMS order aggregate + Market Gateway to represent multi-leg orders; define how Chronos handles
  combos (leg-by-leg with atomic fill semantics, or a combo book).
- **Verification:** a vertical spread submits as one order and fills both legs atomically (or rejects
  whole) — no partial-leg risk.

### 6.4 Options risk & margin
- Extend Risk service: options buying power, defined-risk vs naked margin, assignment/exercise risk,
  approval-level gating (§1.2), early-assignment handling.
- **Verification:** a naked call beyond approval level is rejected; a defined-risk spread's max-loss
  margin is correctly reserved.

### 6.5 Options UI
- Chain view, strategy builder (payoff diagram, breakevens, max profit/loss), Greeks display, position
  Greeks aggregation in the portfolio.
- **Verification:** strategy builder's payoff/breakevens match Pricing; positions show net Greeks.

## Exit criteria
Users can analyze, build, place, and manage single- and multi-leg options strategies with correct
pricing, Greeks, and margin — across all four platforms.
