# Chronos Trade — Master Task List

Single tracker for every task across the roadmap. Pairs with
[`00-master-architecture-and-roadmap.md`](00-master-architecture-and-roadmap.md) (the *why/what*) — this
file is the *what's-left and in-what-order*.

**Legend:** ✅ done · 🟡 in progress / partial · ⬜ not started   |   Size: S (≤2d) · M (≤1wk) · L (multi-wk)

---

## Done so far (this engagement)

- ✅ Full architecture + 10-phase roadmap (`00-master-architecture-and-roadmap.md` + `phase-0`…`phase-9`).
- ✅ Phase 0 broken into per-task plans (`task-0-1`…`task-0-7`).
- ✅ CI bug fixed — `apt_get`→`apt-get` in `.github/workflows/ci.yml`.
- ✅ Contract repo scaffolded — `contracts/` (proto, `WIRE_FORMAT.md`, `buf.yaml`, `buf.gen.yaml`, README).
- ✅ Wire codec implemented — `libs/client-core/include/chronos/client/wire.hpp` (C++) + `bridge/wire.py`
  (Python); bridge & dashboard migrated to single-source scaling.
- ✅ Golden gate tests — `tests/test_wire_codec.cpp` (C++, CI) + `bridge/tests/test_wire.py` (15 tests, green).
- ✅ **Backend domain core implemented & tested in Python** — `services/core/` (ledger, reference_data,
  risk, matching venue, portfolio, OMS saga, options pricing, market-data ingest) with a full end-to-end
  trade-lifecycle integration test. Runnable reference for Phases 1.3/1.4, 2.1, 3.2/3.3/3.4, 6.1, 7.1.
- ✅ **Runnable HTTP API service** — `services/api/` (stdlib `http.server`, no deps): `TradingApp` facade
  + JSON REST endpoints (accounts/fund, orders, **cancel via `DELETE /orders/{id}`**, positions, balance,
  book, chain, option pricing, risk kill switch). Run: `PYTHONPATH=. python3 -m services.api.server`.
  Verified live as a process and via real-HTTP integration tests.
- ✅ **Order cancellation** — `OMS.cancel()`: pulls the resting remainder from the book, releases the
  unfilled buying-power hold, marks `canceled`; rejects cancel of filled/unknown orders. Cancel state is
  durable (canceled orders are not re-rested on restart; hold stays released).
- ✅ **Trade history (the tape)** — `services/core/trades.py` `TradeLog`: every fill recorded with both
  counterparties, persisted, replayed on restart; queryable per-account and per-symbol via
  `GET /accounts/{id}/trades` and `GET /trades/{symbol}`. The trade's monotonic `seq` is also the
  settlement txn id (removed a latent ledger idempotency-collision risk).
- ✅ **Time-in-force (GTC / IOC / FOK)** — `OMS.place(..., tif=)`: GTC rests the remainder (default);
  IOC fills immediately and kills the rest; FOK executes only if fully fillable now (book
  `fillable_qty`), else kills with zero fills. Buying-power holds released correctly per TIF. Set via
  `POST /orders {..., "tif":"ioc"}`.
- ✅ **Market orders (cash-bounded)** — `OMS.place(..., order_type="market")` + `OrderBook.match_market`:
  sweeps the book with no price limit and never rests; a market **buy** is capped by available cash so it
  can never overspend (partial-fills to the budget, remainder canceled); market **sell** sweeps bids.
  Set via `POST /orders {..., "order_type":"market"}` (no price).
- ✅ **Stop / stop-limit orders** — `order_type="stop"|"stop_limit"` with `stop_price`: rest dormant
  (`pending`) until the last trade price crosses the stop (buy: rises to; sell: falls to), then activate
  (stop→market, stop-limit→limit). Cascade-safe trigger loop; pending stops + last price persist and
  recover on restart (no auto-fire on boot). Set via `POST /orders {..., "order_type":"stop", "stop_price":…}`.
- ✅ **Single-leg options trading + position Greeks (Phase 6.1 cont.)** — option contracts trade through
  the same OMS/venue with **contract-multiplier** money semantics ($2.50 premium ×100 = $250/contract),
  threaded through reservation, settlement, and positions (equities stay ×1). `POST /accounts/{id}/greeks`
  aggregates net Δ/Γ/V/Θ/ρ across an account's option positions (Black-Scholes), signed by position size
  × multiplier.
- ✅ **Multi-leg option combos (Phase 6.3)** — `OMS.place_combo` / `POST /combos`: atomic all-or-none
  execution of N legs (e.g. verticals/spreads), pre-checking per-leg fillability + summed buy-leg
  affordability; rejects with zero fills if any leg can't fully fill.
- ✅ **Corporate actions (Phase 7.2)** — `CorporateActions`: forward/reverse splits (scale qty, keep
  basis) and cash dividends (credit long holders); `POST /corporate-actions/{split,dividend}`.
- ✅ **Account statements (Phase 7.3)** — `GET /accounts/{id}/statement`: cash postings, trades, and
  positions reconciled against ending cash.
- ✅ **Price alerts (Phase 7.4)** — `AlertEngine` fired on every fill via the OMS hook; one-shot
  above/below conditions; `POST/GET /accounts/{id}/alerts`.
- ✅ **Trade surveillance (Phase 8.2)** — `Surveillance` self-trade/wash detection over the trade log;
  `GET /surveillance`.
- ✅ **OHLC bars (Phase 2.2)** — `build_bars` aggregates the trade stream into OHLCV candles; `POST /ohlc/{symbol}`.
- ✅ **SQLite persistence (Phase 1 durability)** — `services/core/persistence.py`: event-sourced ledger
  journal + holds, OMS orders, and portfolio positions persist; on restart the ledger replays, positions
  reload, and the **open order book is rebuilt**. Enable via `CHRONOS_DB=chronos.db`. Verified across a
  real process restart (kill + relaunch on the same DB). Also fixed a real buying-power-hold lifecycle
  bug (resting buys now correctly reserve their unfilled remainder).
- ✅ **Web trading dashboard (zero-build UI)** — `services/api/web.py` served at `GET /`: a modern dark
  trading UI (order ticket with all order types/TIF, live order book with depth bars, price chart, time &
  sales, positions, balance, setup controls) that polls `/snapshot`, `/instruments`, `/accounts/*`. CORS
  enabled so the existing Next.js `dashboard/` can target the same backend. Open
  `http://localhost:8080` after `python3 -m services.api.server`.
- ✅ **Live SSE stream** — `EventBus` + `GET /stream` (Server-Sent Events): the OMS publishes trade/order
  events; both the served dashboard and the Next.js app refresh instantly on each event (polling stays as
  fallback). Verified live (a fill pushes a `trade` event in real time).
- ✅ **Next.js dashboard — full trading terminal on the Python backend** — `dashboard/`: REST+SSE client
  (`lib/api.ts`), store with market + account state (`applySnapshot`/`applyAccount`), and a market-grade
  layout (`page.tsx`): header ticker (last/bid/ask/spread, live status), order ticket (all order
  types/TIF + fund/seed), **account summary**, **positions**, **open orders with one-click cancel**,
  depth-bar order book, **real OHLC candlestick chart** (`lightweight-charts`), and time & sales — all
  refreshing on SSE events with a polling fallback. Backend gained `GET /accounts/{id}/orders`.
  _(Code written here; run on your Mac with `npm run dev` — no Node in this Windows sandbox.)_
- ✅ **Options workspace + depth chart (dashboard)** — new `/options` route: live **options chain**
  (calls/strike/puts grid + add-contract), **multi-leg spread builder** → `/combos`, and a **position
  Greeks** panel (`/accounts/{id}/greeks`, spot auto-sourced from last trade). Main terminal gained a
  **cumulative depth chart** and a **Greeks tab**. Backend: `position_greeks` now defaults spot to the
  underlying's last trade price when not supplied.
- ✅ **Order toasts · P&L curve · compliance view (dashboard)** — live **order-status toasts** (SSE
  `order` events now carry `account`); a **cash/equity curve** tab (`GET /accounts/{id}/cashflow`,
  derived from the ledger journal); and a **`/compliance`** route showing trade surveillance alerts +
  an account statement (cash postings, trades, positions). Nav: Trade · Options · Compliance.
- ✅ **Click-to-trade ladder + live watchlist (dashboard)** — a DOM **price ladder** (click bid→sell,
  ask→buy at that level) as a tab beside the order book; a **watchlist** quote board powered by a new
  one-shot `GET /markets` endpoint (last/bid/ask for all instruments), click a row to switch symbol.
- ✅ **Keyboard shortcuts + persisted prefs (dashboard)** — global hotkeys (B/S = buy/sell at the touch,
  ↑/↓ = cycle symbol, ? = help overlay) ignored while typing; a configurable hotkey qty; and UI prefs
  (account, symbol, hotkey qty) persisted to `localStorage`. Frontend-only.
- ✅ **"Advanced Sense" palette theme** — whole UI re-skinned via a Tailwind v4 `@theme` override in
  `dashboard/src/app/globals.css` (navy #213271 brand · light-blue #8FB9D1 accent · coral #E86349
  sell/down · teal-green buy/up · charcoal #252C38 surfaces), plus chart/SVG hex updated
  (`PriceChart`/`DepthChart`/`CashCurve`) and the served `web.py` dashboard vars. moomoo/Tiger-style.
- ✅ **Production hardening — Tranche 1** — `services/api/config.py` (12-factor env: PORT, CHRONOS_DB,
  CHRONOS_CORS_ORIGINS, CHRONOS_API_TOKEN); optional **bearer-token auth** on mutating routes (open by
  default; `401` without token when set); **CORS allowlist** (echoes allowed origin); structured JSON
  **access logging** + `X-Request-Id`; **`/readyz`**. Quiet server subclass removes Windows socket-teardown
  flakiness. Tests added (auth/CORS/readyz/request-id). Verified live (token 401↔201, palette served).
- ✅ **Production hardening — Tranche 2 (deployability)** — multi-stage **Dockerfiles** for the API
  (`services/api/Dockerfile`, non-root, healthcheck) and dashboard (`dashboard/Dockerfile`), a
  **`docker-compose`** stack (`deploy/compose/docker-compose.yml`), `.dockerignore`s, and **CI jobs**
  running the Python suites + a Next.js lint+build (validates the dashboard on GitHub's runners).
- ✅ **Production hardening — Tranche 4 (ops/scale, partial)** — Prometheus **`/metrics`** (request
  counters + business gauges); per-IP **rate limiting** on writes (`429`, `CHRONOS_RATE_LIMIT`);
  **graceful shutdown** on SIGTERM/SIGINT.
- ✅ **API depth (Tranche 3, partial)** — **SSE symbol filter** (`/stream?symbols=`) and **order-history
  pagination** (`/accounts/{id}/orders?limit&offset`).
- ✅ Monorepo skeleton — `MONOREPO.md` + additive `services/ clients/ libs/ infra/ deploy/` stubs.

> **Total: 146 Python tests passing** (15 bridge wire + 89 core + 42 API), green across 15 consecutive
> full-suite runs (Windows socket flake eliminated). Run everything:
> `PYTHONPATH=. python3 -m unittest discover -t . -s services -p "test_*.py"` and
> `PYTHONPATH=. python3 -m unittest bridge.tests.test_wire`.
> These implement the *domain logic + a runnable API*; the production deployment (containers/mesh/IaC,
> Kafka, persistent stores, OIDC, RN+C++/JSI clients, settlement, compliance, scale/DR) is still ⬜ —
> those need toolchains/infra not present in a pure-Python environment.

---

## Phase summary & critical path

Status reflects two tracks: **DL** = domain logic implemented & tested as runnable Python in
`services/`; **DEPLOY** = production deployment (containers, real infra, native clients) which needs
toolchains absent from this environment.

| Phase | Theme | Domain logic (runnable here) | Deployment | Detail |
|---|---|---|---|---|
| 0 | Platform engineering foundation | 🟡 contract+codec done | ⬜ IaC/CI/mesh/observability | [phase-0](phase-0-foundation.md) |
| 1 | Core backend domains | 🟢 ledger, reference-data, account money | ⬜ OIDC/MFA identity, real DB | [phase-1](phase-1-core-services.md) |
| 2 | Market data pipeline | 🟢 ingest abstraction, OHLC | ⬜ ClickHouse/Kafka fan-out | [phase-2](phase-2-market-data.md) |
| 3 | Execution: OMS + Risk + venue | 🟢 OMS saga, risk, venue, settlement | ⬜ C++ engine + Market Gateway | [phase-3](phase-3-execution-core.md) |
| 4 | Shared C++ client core + RN shell | ⬜ | ⬜ RN + C++/JSI, 4 platforms | [phase-4](phase-4-client-core.md) |
| 5 | Equities MVP | 🟢 full trade lifecycle (backend) | ⬜ UI / E2E on devices | [phase-5](phase-5-equities-mvp.md) |
| 6 | Options trading | 🟢 pricing, single+multi-leg, Greeks | ⬜ options margin (6.4) | [phase-6](phase-6-options.md) |
| 7 | Portfolio, settlement, notifications | 🟢 P&L, corp-actions, statements, alerts | ⬜ push delivery (FCM/APNs) | [phase-7](phase-7-portfolio-settlement.md) |
| 8 | Compliance, surveillance, hardening | 🟢 surveillance, audit/journal | ⬜ pen-test, chaos, SAST/DAST | [phase-8](phase-8-compliance-hardening.md) |
| 9 | Scale, DR, launch | ⬜ | ⬜ multi-region, autoscale, DR | [phase-9](phase-9-scale-launch.md) |

**Bottom line:** the entire backend **domain** of the platform — every order type, both asset classes,
the full trade lifecycle with double-entry settlement, durability, corporate actions, statements, alerts,
and surveillance — is implemented and **126 tests pass**. What remains is **deployment & delivery**
(containerization, real datastores/streaming, the native mobile/desktop clients, the compiled C++ hot
path, security hardening, and multi-region scale) — none of which can run or be verified in a
pure-Python sandbox, so they stay ⬜ rather than being faked.

---

## Phase 0 — Foundation  🟡  · [detail](phase-0-foundation.md)

- 🟡 **0.1** Monorepo & workspace layout — additive dirs + `MONOREPO.md` ✅; **0.1b** relocate `include/`,
  `src/`, `bridge/`, `dashboard/` into `services/`/`clients/` ⬜ · S · [task-0-1](task-0-1-monorepo.md)
- 🟡 **0.2** Contract-first schemas — proto/spec ✅; C++ codec + golden test ✅; **Python codec
  (`bridge/wire.py`) + 15 passing tests ✅**; bridge & dashboard migrated to single-source scaling ✅;
  `buf generate` C++/Go/TS bindings ⬜ · M · _depends 0.1_ · [task-0-2](task-0-2-contracts.md)
- ⬜ **0.3** Infrastructure as Code — Terraform modules + local compose/kind · L · _depends 0.1_ · [task-0-3](task-0-3-iac.md)
- ⬜ **0.4** CI/CD & GitOps — reusable workflows, Argo CD, preview envs · M · _depends 0.1,0.3_ · [task-0-4](task-0-4-cicd-gitops.md)
- ⬜ **0.5** Service mesh & zero-trust — mTLS, NetworkPolicies, Vault · M · _depends 0.3_ · [task-0-5](task-0-5-mesh-zerotrust.md)
- ⬜ **0.6** Observability baseline — OTel + Prom/Loki/Tempo/Grafana, correlation IDs · M · _depends 0.3_ · [task-0-6](task-0-6-observability.md)
- ⬜ **0.7** Service template (golden path) — hexagonal reference service + generator · M · _depends 0.2,0.4,0.6_ · [task-0-7](task-0-7-service-template.md)

## Phase 1 — Core backend domains  ⬜  · [detail](phase-1-core-services.md)

- ⬜ **1.1** Identity — OIDC + MFA, sessions, device trust, KYC status · L · _depends 0.7_
- ⬜ **1.2** Account — cash/margin accounts, options approval level, account events · M · _depends 0.7_
- ⬜ **1.3** Ledger — event-sourced double-entry, balances, buying-power holds · L · _depends 0.7_
- ⬜ **1.4** Reference Data — instruments, **option contracts**, calendar, corp actions · M · _depends 0.7_
- ⬜ **1.5** BFF wiring — GraphQL `me`/`accounts`/`instruments`/`chain` + WS scaffold · M · _depends 1.1–1.4_

## Phase 2 — Market data pipeline  ⬜  · [detail](phase-2-market-data.md)

- ⬜ **2.1** Ingest & normalization — provider-abstracted feed (from `bridge/feeder.py`) · M · _depends 1.4_
- ⬜ **2.2** Time-series persistence — ticks + OHLC in ClickHouse/Timescale; history API · M · _depends 2.1_
- ⬜ **2.3** Real-time fan-out — Kafka → BFF WS, per-client subscriptions, L2 deltas · M · _depends 2.1_
- ⬜ **2.4** Options market data — option quotes + IV + chain snapshots/stream · M · _depends 2.3,6.1_
- ⬜ **2.5** Decouple from synthetic feed — separate display data from sim-liquidity profile · S · _depends 2.1_

## Phase 3 — Execution: OMS + Risk + venue  ⬜  · [detail](phase-3-execution-core.md)

- ⬜ **3.1** Market Gateway — ZMQ↔Chronos adapter (generated codec), events→Kafka, pluggable FIX · L · _depends 0.2,1.4_
- ⬜ **3.2** OMS — event-sourced order lifecycle + placement **saga** + idempotency + cancel/replace · L · _depends 1.3,3.1,3.3_
- ⬜ **3.3** Risk service — extend `chronos::RiskEngine` (buying power, Reg-T, PDT, kill switch) · M · _depends 1.3_
- ⬜ **3.4** Fill → Ledger → Portfolio — trade events drive postings + position/P&L projection · M · _depends 3.2_
- ⬜ **3.5** Multi-symbol & sharding config — symbols from Reference Data, not hardcoded · S · _depends 3.1_

## Phase 4 — Shared C++ client core + RN shell  ⬜  · [detail](phase-4-client-core.md)

- 🟡 **4.1** `chronos-client-core` lib — codec ✅; order-book aggregation, transport, cache/signing ⬜ · L · _depends 0.2_
- ⬜ **4.2** Cross-platform build — NDK/JNI (Android), XCFramework (iOS+macOS), native module (Windows) · M · _depends 4.1_
- ⬜ **4.3** JSI / TurboModule binding — expose core to RN New Architecture · M · _depends 4.2_
- ⬜ **4.4** React Native app shell — Android/iOS + RN-Windows/macOS, auth, secure token storage · L · _depends 4.3,1.1_
- ⬜ **4.5** Client observability & CI — crash reporting, client OTel spans, 4-target build + Detox smoke · M · _depends 4.4_

## Phase 5 — Equities MVP (first release)  ⬜  · [detail](phase-5-equities-mvp.md)

- ⬜ **5.1** Trading UI — watchlist, quotes/chart, L2 book, trade tape, order ticket · L · _depends 2.3,3.2,4.4_
- ⬜ **5.2** Order & position blotters — live orders, history, positions, P&L, cancel/replace · M · _depends 3.4,5.1_
- ⬜ **5.3** Funding & buying power (paper) — simulated funding; pre/post-trade buying power · M · _depends 1.3,3.3_
- ⬜ **5.4** Paper-trading venue profile — Chronos + simulator liquidity · M · _depends 2.5,3.1_
- ⬜ **5.5** E2E hardening — full-trace coverage, contract tests, Detox E2E, load test · M · _depends 5.1–5.4_

## Phase 6 — Options trading  ⬜  · [detail](phase-6-options.md)

- ⬜ **6.1** Pricing/Analytics — Black-Scholes/binomial, Greeks, IV (C++/Rust) · L · _depends 0.7_
- ⬜ **6.2** Options reference data & chains — expiry/strike grids, multipliers, assignment · M · _depends 1.4,6.1_
- ⬜ **6.3** Options order types & multi-leg — combos with atomic fill semantics in OMS/Gateway · L · _depends 3.2,6.2_
- ⬜ **6.4** Options risk & margin — buying power, defined-risk vs naked, approval gating · L · _depends 3.3,6.3_
- ⬜ **6.5** Options UI — chain view, strategy builder, payoff/Greeks, position Greeks · L · _depends 5.1,6.4_

## Phase 7 — Portfolio, settlement, notifications  ⬜  · [detail](phase-7-portfolio-settlement.md)

- ⬜ **7.1** Portfolio & analytics — tax lots, cost basis, P&L, exposure, net Greeks · L · _depends 3.4_
- ⬜ **7.2** Settlement & clearing — T+1 state machine, corporate-action processing · L · _depends 1.3,3.4_
- ⬜ **7.3** Statements & documents — statements, confirms, tax docs to object store · M · _depends 1.3,7.1_
- ⬜ **7.4** Notification service — push (FCM/APNs)/email/in-app, price & fill alerts · M · _depends 3.4,2.3_
- ⬜ **7.5** Client polish — notifications center, alerts mgmt, statements, analytics views · M · _depends 7.1–7.4,4.4_

## Phase 8 — Compliance, surveillance, hardening  ⬜  · [detail](phase-8-compliance-hardening.md)

- ⬜ **8.1** Compliance service & recordkeeping — audit stream → immutable store, best-ex logging · L · _depends 3.2_
- ⬜ **8.2** Trade surveillance — spoofing/layering/wash detection + alerts · M · _depends 8.1_
- ⬜ **8.3** Security hardening — STRIDE, secrets rotation, SAST/DAST, SBOM, CodeQL/Trivy gates · L · _depends 0.5_
- ⬜ **8.4** Penetration test & remediation — external-style pen test, fix findings · M · _depends 8.3_
- ⬜ **8.5** Resilience & chaos — verify breakers/bulkheads/kill switch under fault injection; SLOs · M · _depends 0.6_

## Phase 9 — Scale, DR, launch  ⬜  · [detail](phase-9-scale-launch.md)

- ⬜ **9.1** Performance & capacity — load/soak, matching-budget check, sharding rollout, autoscaling · L · _depends 3.5,8.5_
- ⬜ **9.2** Multi-region & DR — replication, RPO/RTO, failover runbook + drill · L · _depends 9.1_
- ⬜ **9.3** Operational readiness — runbooks, on-call, backups, game-day · M · _depends 9.1_
- ⬜ **9.4** Release management — canary/blue-green, store + desktop distribution, feature flags · M · _depends 9.1_
- ⬜ **9.5** GA — compliance sign-off, real-money routing decision, docs, launch · M · _depends 9.2–9.4_

---

## Immediate next actions (Phase 0 finish)

1. **0.2 finish** — `buf generate` bindings and migrate `bridge/decoder.py` to consume them (closes the
   last drift gap).
2. **0.7** — scaffold `libs/service-template` so Phase 1 services have a home (highest-leverage unblocker).
3. **0.3 → 0.4** — stand up local `docker-compose` dev stack, then CI/CD + GitOps.
4. **0.1b** — relocate engine/bridge/dashboard into the monorepo layout (deliberate, verified move).
