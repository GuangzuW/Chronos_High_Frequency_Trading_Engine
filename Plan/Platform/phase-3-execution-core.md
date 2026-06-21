# Phase 3 — Execution: OMS + Risk + Chronos Venue

## Goal
Wire the server-side order path end-to-end: **OMS** orchestrates placement as a saga, the **Risk**
service gates pre-trade, and the **Market Gateway** routes to the reused **Chronos** matching engine,
streaming fills back to the ledger and clients.

## Tasks

### 3.1 Market Gateway adapter
- New service owning the **ZMQ boundary** to Chronos: encode orders to the 64-byte contract (from
  generated codec, §0.2), send on DEALER→`:5555`; subscribe to PUB `:5556` TRADE/ORDER and bridge
  events into Kafka.
- Owns symbol registration (today hardcoded `AAPL/BTC/ETH` in `src/main.cpp`) driven by Reference Data.
- Pluggable backend: `chronos` (internal venue) | `fix` (external broker) — same OMS interface.
- **Verification:** an order placed via gRPC reaches Chronos, matches, and the resulting TRADE event
  appears on Kafka with the original correlation ID.

### 3.2 OMS (order lifecycle, event-sourced)
- Order aggregate with states New→Acked→Partial→Filled / Canceled / Rejected; append-only event log.
- **Placement saga:** validate (Reference Data) → reserve buying power (Ledger) → risk check (Risk) →
  route (Market Gateway) → on fill post to Ledger / on reject release reservation (compensation).
- Idempotency keys; cancel/replace; GTC/IOC/FOK time-in-force.
- **Verification:** happy path fills and posts to ledger; a rejected risk check releases the buying-power
  hold (saga compensation) with no orphaned reservations.

### 3.3 Risk service (extends `chronos::RiskEngine`)
- Reuse the existing static checks (`RiskConfig`: qty/price/notional). Add: **buying-power** check vs
  Ledger, **Reg-T margin**, **PDT** rule, per-symbol/per-account limits, and a global **kill switch**.
- Keep the deterministic, exception-free style of the engine's risk path; expose as a fast gRPC service
  (C++/Rust) co-located on the hot path.
- The engine's in-loop `risk_score > 0.8` reject stays as the **last-line** in-venue guard; the service
  is the rich pre-trade gate.
- **Verification:** an order exceeding buying power is rejected pre-trade; flipping the kill switch
  blocks all new orders instantly.

### 3.4 Fill → Ledger → Portfolio flow
- Trade events drive double-entry postings (cash ↔ position) and position/P&L projection updates.
- **Verification:** after a fill, ledger cash and position quantities reconcile; P&L projection updates.

### 3.5 Multi-symbol & sharding config
- Replace hardcoded `addSymbol` calls with config sourced from Reference Data; document the
  scaling/sharding story (one `LimitOrderBook` per symbol, shard across engine instances).
- **Verification:** adding a symbol in Reference Data makes it tradable without code changes.

## Exit criteria
A server-side order placed through the OMS is risk-checked, matched by Chronos, settled into the ledger,
and emitted as events — fully traced, with sagas compensating on failure.
