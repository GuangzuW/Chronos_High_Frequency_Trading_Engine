# Chronos Trade — Master Architecture & Roadmap

> Multi-platform online trading platform for **equities and options**, built on the existing
> **Chronos** C++20 matching engine as the low-latency execution core, surrounded by a
> Docker/Kubernetes microservices backend, and delivered to **Android, iOS, macOS, and Windows**
> via React Native with a **shared high-performance C++ client core**.

This is the top-level design. Each phase below has a dedicated plan file (`phase-N-*.md`) that
expands its tasks into goals, key files, steps, and verification — mirroring the existing
`Plan/task-X-Y.md` convention. For the consolidated, status-tracked checklist of every task across all
phases, see [`01-task-list.md`](01-task-list.md).

---

## 1. Product scope

| Capability | MVP (Phase 5) | Full (Phase 6+) |
|---|---|---|
| Equities (market/limit/stop, GTC/IOC/FOK) | ✅ | ✅ |
| Real-time L1/L2 market data & charts | ✅ | ✅ |
| Accounts, funding, double-entry ledger | ✅ | ✅ |
| Portfolio, positions, realized/unrealized P&L | ✅ | ✅ |
| Options: chains, single-leg | — | ✅ |
| Options: multi-leg strategies, Greeks, IV surface | — | ✅ |
| Margin (Reg-T), buying power, PDT enforcement | basic | ✅ |
| Paper-trading mode (Chronos as simulated venue) | ✅ | ✅ |
| Notifications (push/email/in-app), alerts | — | ✅ |
| Statements, tax lots, regulatory reporting | — | ✅ |

**Note on the matching engine's role.** Chronos is reused as the **internal execution venue** —
ideal for paper-trading and an internal crossing/simulation book today, and extensible to a real
venue. A pluggable **Market Gateway** (Phase 3) abstracts execution so orders can alternatively be
routed to an external broker/exchange via FIX without changing the OMS. This keeps the deterministic
C++ hot path intact while leaving real-money routing a configuration choice, not a rewrite.

---

## 2. Architecture principles (the "all SD principles" the platform is held to)

- **Domain-Driven Design** — services are bounded contexts (Identity, Accounts, Ledger, OMS,
  Market Data, Pricing, Risk, Portfolio, Settlement, Compliance, Notifications). Ubiquitous language
  documented per context.
- **Hexagonal / Clean Architecture** inside each service — domain core is framework-agnostic; ZMQ,
  Kafka, HTTP, and DB are adapters at the edges. (Chronos already embodies this: header-only domain
  logic, ZMQ only at the boundary.)
- **Event-driven & event-sourced where it pays off** — the **ledger** and **order lifecycle** are
  append-only event streams (natural fit with Chronos's existing async audit logger). Read models are
  projections (CQRS). Everything else uses plain CRUD + domain events.
- **Saga pattern** for distributed transactions (e.g. "reserve buying power → place order → settle")
  with compensating actions; no 2-phase commit across services.
- **API-first / contract-first** — schemas defined before code: gRPC + Protobuf for service-to-service,
  GraphQL (BFF) + WebSocket for clients, AsyncAPI for event topics. Contracts are versioned artifacts.
- **12-Factor** services, stateless where possible, config via environment, disposable, horizontally
  scalable.
- **Security by design / zero-trust** — mTLS between services (service mesh), OIDC for users, secrets in
  a vault, least privilege, encryption in transit and at rest, audit everything.
- **SOLID + testing pyramid** — unit (fast, dominant) → contract → integration → a thin E2E layer.
  Determinism in the matching/risk core is property-tested.
- **Observability built-in** — OpenTelemetry traces/metrics/logs from day one; every order carries a
  correlation ID end-to-end.
- **GitOps + IaC** — infrastructure and deployments declared in Git (Terraform + Argo CD/Flux),
  trunk-based development, ephemeral preview environments.
- **Performance budget discipline** — the order hot path inherits Chronos's nanosecond budget; only
  reporting/analytics paths are allowed to be eventually consistent.

---

## 3. System topology

```
                                   ┌──────────────────────────────────────────────┐
   Clients (RN + shared C++ core)  │                  Edge / BFF                   │
   ┌──────────┬──────────┐         │  API Gateway (TLS, rate-limit, authn)         │
   │ Android  │   iOS    │         │  GraphQL BFF + WebSocket fan-out (quotes,      │
   │ macOS    │ Windows  │ ◄─────► │  order/trade/portfolio push)                  │
   └──────────┴──────────┘  HTTPS  └───────────────┬──────────────────────────────┘
        ▲  JSI binds C++ core         gRPC (mTLS)   │   events (Kafka/Redpanda)
        │                                           ▼
        │                ┌───────────────────────────────────────────────────────┐
        │                │                  Microservices mesh                     │
        │                │  Identity · Account · Ledger · Reference-Data           │
        │                │  Market-Data · Pricing/Analytics · Risk(pre-trade)      │
        │                │  OMS · Portfolio · Settlement · Compliance · Notify     │
        │                └───────────────┬───────────────────────────────────────┘
        │                                │ Market Gateway adapter (ZMQ ↔ FIX)
        │                                ▼
        │                ┌───────────────────────────────────────────────────────┐
        │                │   CHRONOS EXECUTION CORE (existing C++20, reused)       │
        │                │   ZMQ ROUTER :5555 ingress · sharded LOB · risk         │
        │                │   ZMQ PUB :5556 (TRADE/ORDER) → audit logger            │
        │                └───────────────────────────────────────────────────────┘
   Data: Postgres (accounts/ledger, event store) · ClickHouse/Timescale (ticks/OHLC) ·
         Redis (cache/session/buying-power) · S3-compatible object store (statements/docs)
```

The existing **64-byte binary wire contract** and **fixed-point scaling (price ×100, qty ×1000)**
between Chronos and its bridge are preserved and become a formally versioned, code-generated contract
shared by the Market Gateway and the client C++ core (see §6 and Phase 0 / Phase 3).

---

## 4. Service decomposition (bounded contexts)

| Service | Responsibility | Store | Notes |
|---|---|---|---|
| **API Gateway / BFF** | TLS termination, authn, rate limiting, GraphQL aggregation, WS fan-out | Redis | Backend-for-frontend; no business rules |
| **Identity** | OIDC, MFA, sessions, device trust, KYC/AML status | Postgres | Integrate 3rd-party KYC |
| **Account** | User profiles, account types (cash/margin), options approval level | Postgres | |
| **Ledger** | Double-entry accounting, balances, buying power reservations | Postgres (event-sourced) | Source of financial truth |
| **Reference Data** | Instruments, symbols, **options contracts**, trading calendar, corporate actions | Postgres + cache | Powers symbol routing & chains |
| **Market Data** | Ingest (Finnhub + others), normalize, L1/L2/OHLC, fan-out | ClickHouse/Timescale + Redis | Extends existing `bridge/feeder.py` |
| **Pricing / Analytics** | Options pricing (Black-Scholes/binomial), Greeks, IV, indicators | stateless + cache | C++ for hot math; can reuse Chronos numeric style |
| **Risk (pre-trade)** | Static limits + margin/Reg-T + PDT + options buying-power; **kill switch** | Redis | Reuses & extends `chronos::RiskEngine` |
| **OMS** | Order lifecycle (new/ack/partial/fill/cancel/reject), routing decision | Postgres (event-sourced) | Saga orchestrator for placement |
| **Market Gateway** | Adapter: OMS ↔ Chronos (ZMQ) and ↔ external venues (FIX) | — | Hot path; owns the binary contract |
| **Portfolio** | Positions, tax lots, realized/unrealized P&L, margin usage | Postgres + projections | Projection of ledger + fills |
| **Settlement** | Trade settlement (T+1), clearing, corporate-action processing | Postgres | |
| **Compliance** | Trade surveillance, best-execution logging, regulatory reporting | ClickHouse | Consumes Chronos audit stream |
| **Notification** | Push (FCM/APNs), email, in-app, price/fill alerts | Redis + queue | |

Inter-service: **gRPC** for request/response, **Kafka/Redpanda** for domain events
(`order.placed`, `trade.executed`, `ledger.posted`, `position.updated`, …). The Chronos
`PUB :5556` TRADE/ORDER stream is bridged into Kafka by the Market Gateway.

---

## 5. Technology stack

- **Execution core:** existing **C++20 Chronos** (header-only domain, ZMQ, PMR memory pools) — unchanged hot path.
- **Backend services:** **Go** for I/O-bound services (Gateway, OMS, Account, Notification — fast, great concurrency, small containers); **C++** (or Rust) for the latency/compute-sensitive **Pricing** and **Risk** services so they can share Chronos numeric idioms. Keep the existing **Python/FastAPI** bridge as the Market-Data ingestion service initially, migrating hot parts later.
- **Eventing:** Redpanda (Kafka API) — single binary, low latency. **gRPC + Protobuf** for sync calls.
- **Data:** PostgreSQL (OLTP + event store), ClickHouse or TimescaleDB (ticks/OHLC/surveillance), Redis (cache/session/buying-power), MinIO/S3 (statements/KYC docs).
- **Client UI:** **React Native** (New Architecture: Fabric + TurboModules + **JSI**) for Android & iOS; **React Native for Windows + macOS** for desktop — one TS/React UI codebase across all four targets.
- **Client core:** **shared C++ library** exposed to JS through **JSI/TurboModule** — handles wire-protocol decode (64-byte structs), fixed-point math, order-book aggregation, low-latency multiplexed WebSocket, local cache, and request signing. Built once; bound per platform (NDK/JNI on Android, C++ interop/Obj-C++ on iOS+macOS, N-API/native on Windows).
- **Infra:** Docker (multi-stage, as today) → Kubernetes; Istio/Linkerd service mesh (mTLS); Terraform (IaC); Argo CD (GitOps); HashiCorp Vault (secrets); GitHub Actions (CI, extending the existing pipeline).
- **Observability:** OpenTelemetry → Prometheus (metrics), Loki (logs), Tempo/Jaeger (traces), Grafana (dashboards), Alertmanager.

---

## 6. The shared C++ client core (per chosen client strategy)

A single C++ library — call it **`chronos-client-core`** — is the high-performance heart of every app.
It deliberately reuses concepts from the engine side so the wire contract has exactly one definition.

Responsibilities:
1. **Wire codec** — the 64-byte `Order`/`Trade` decode/encode, generated from the same Protobuf/IDL the
   Market Gateway uses. Eliminates the current hand-synced `bridge/decoder.py` format strings.
2. **Order-book aggregation** — maintain L2 book deltas in memory, produce render-ready snapshots
   (the perf-critical part the user asked C++ to own).
3. **Fixed-point math** — single source of the ×100/×1000 scaling, replacing the convention currently
   duplicated across `bridge/main.py`, `feeder.py`, and `useTradeStore.ts`.
4. **Transport** — resilient, multiplexed, compressed WebSocket client with reconnect/backoff and
   subscription management.
5. **Local cache & request signing** — offline snapshots, auth token handling, HMAC/request signing.

Exposed to React Native via **JSI** (synchronous, zero-copy where possible) as a TurboModule. UI stays
in TS/React; all hot data manipulation stays in C++.

---

## 7. Cross-cutting concerns

- **Security/compliance:** OIDC + MFA, device binding, per-request signing, mTLS mesh, Vault-managed
  secrets, field-level encryption for PII, full audit trail (reuse Chronos `AuditLogger`), KYC/AML,
  best-execution and order-event recording, options-approval gating, Reg-T margin & PDT enforcement.
- **Resilience:** circuit breakers, bulkheads, backpressure on market-data fan-out, idempotency keys on
  order placement, a global **trading kill switch** in the Risk service, graceful degradation
  (read-only mode if the venue is down).
- **Consistency:** strong consistency on the ledger hot path (within Postgres tx), eventual consistency
  for projections/reporting; sagas with compensations for cross-service flows.
- **Testing:** unit + property tests for matching/risk/pricing determinism, consumer-driven contract
  tests (Pact) for gRPC/event schemas, integration via ephemeral Docker compose / k8s namespaces, thin
  E2E (Detox for RN clients), load tests against the venue.
- **Performance:** keep Chronos's ~286 ns matching budget; gateway/BFF latency budgets defined per
  endpoint; market-data fan-out measured at p99.

---

## 8. Phased roadmap

| Phase | Theme | Plan file | Outcome |
|---|---|---|---|
| **0** | Platform engineering foundation | `phase-0-foundation.md` | Monorepo, IaC, CI/CD, mesh, observability, contract tooling |
| **1** | Core backend domains | `phase-1-core-services.md` | Identity, Account, Ledger, Reference-Data live |
| **2** | Market data pipeline | `phase-2-market-data.md` | Normalized real-time + historical data, fan-out |
| **3** | Execution: OMS + Risk + Chronos venue | `phase-3-execution-core.md` | End-to-end order → match → fill (server side) |
| **4** | Shared C++ client core + RN shell | `phase-4-client-core.md` | `chronos-client-core` + 4-platform app skeleton |
| **5** | **Equities MVP (vertical slice)** | `phase-5-equities-mvp.md` | Trade stocks end-to-end on all 4 platforms |
| **6** | Options trading | `phase-6-options.md` | Chains, Greeks, multi-leg, margin |
| **7** | Portfolio, settlement, notifications | `phase-7-portfolio-settlement.md` | Statements, P&L, alerts, settlement |
| **8** | Compliance, surveillance, hardening | `phase-8-compliance-hardening.md` | Reg reporting, security audit, pen-test |
| **9** | Scale, DR, launch | `phase-9-scale-launch.md` | Multi-region, DR, performance, GA |

Dependencies: 0 → 1 → {2,3} → 4 → **5 (first releasable slice)** → 6 → 7 → 8 → 9. Phases 2 and 3 can run
in parallel after 1; Phase 4 (client core) can start as soon as the Phase 0 contracts exist.

---

## 9. What is reused from today's repo

- `include/chronos/*` matching engine, risk engine, sharded books, audit logger — become the **Market Gateway-fronted venue**.
- `bridge/` FastAPI + ZMQ + Finnhub feeder — seeds the **Market Data** service and the binary-contract tooling.
- `dashboard/` Next.js components — reference for the React Native UI and a possible web client.
- Existing Docker multi-stage build and GitHub Actions CI — extended into the platform's CI/CD.
- The 64-byte struct contract and fixed-point convention — formalized into a generated, versioned schema.

See each `phase-N-*.md` for the detailed task breakdown.
