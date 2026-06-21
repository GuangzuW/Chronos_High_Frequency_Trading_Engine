# Phase 1 — Core Backend Domains

## Goal
Build the foundational bounded contexts every trading flow depends on: **Identity**, **Account**,
**Ledger**, and **Reference Data**. These have no dependency on the matching engine and can be
hardened independently.

## Tasks

### 1.1 Identity service
- OIDC provider integration (or self-hosted, e.g. Keycloak/Ory) with **MFA** and device binding.
- Session/token issuance (short-lived JWT access + rotating refresh), token introspection for the BFF.
- KYC/AML status fields and a pluggable 3rd-party KYC adapter (stubbed in dev).
- **Verification:** login + MFA flow issues tokens; BFF validates them; revoked tokens are rejected.

### 1.2 Account service
- Account aggregate: cash vs margin, base currency, **options approval level (0–4)**, account status.
- Domain events: `account.opened`, `account.status.changed`, `account.options.level.changed`.
- **Verification:** open account → events emitted → projection queryable via gRPC.

### 1.3 Ledger service (event-sourced, double-entry)
- Append-only event store in Postgres; **double-entry** postings; balance & **buying-power** projections.
- Money as integer minor units (consistent with the engine's fixed-point philosophy); no floats.
- Idempotent posting API keyed by transaction ID; reservation/hold primitives for order placement.
- **Verification:** property test — sum of all postings per account always nets to zero; replaying the
  event log reproduces current balances exactly.

### 1.4 Reference Data service
- Instrument master: equities + **options contracts** (underlying, expiry, strike, call/put,
  multiplier), trading calendar, tick sizes, lot sizes, corporate actions.
- Symbol routing metadata (which venue/shard a symbol maps to — feeds Chronos `addSymbol` and the
  Market Gateway).
- **Verification:** options chain for an underlying resolves to fully-specified contracts; calendar
  correctly flags a market holiday.

### 1.5 BFF wiring
- GraphQL schema for `me`, `accounts`, `instruments`, `chain(underlying)`.
- WebSocket channel scaffolding (no market data yet — that's Phase 2).
- **Verification:** authenticated GraphQL query returns the user's accounts and an options chain.

## Exit criteria
A user can authenticate, an account exists with a balance in the ledger, and reference data resolves
both equities and option contracts — all observable and contract-tested.
