# Phase 0 — Platform Engineering Foundation

## Goal
Stand up the monorepo, infrastructure-as-code, CI/CD, service mesh, observability, and the
**contract-first tooling** that every later phase depends on. No business features yet — this is the
paved road.

## Why first
Every principle in the master doc (contract-first, GitOps, observability-by-default, zero-trust) is
cheap to adopt now and expensive to retrofit. The single most important deliverable is the
**versioned wire/event contract** that replaces today's hand-synced 64-byte struct format.

## Tasks

### 0.1 Monorepo & workspace layout
- Create a monorepo (e.g. `Nx`/`Bazel` or a pragmatic folder + `make` layout) with top-level
  `services/`, `clients/`, `libs/`, `contracts/`, `infra/`, `deploy/`.
- Keep the existing `include/`, `src/`, `tests/`, `bridge/`, `dashboard/` and re-home them:
  Chronos engine → `services/execution-core/`, bridge → `services/market-data/` (seed), dashboard →
  `clients/web/` (reference).
- **Verification:** existing `cmake --build` and `ctest` still pass from the new path.

### 0.2 Contract-first schema repository
- Create `contracts/` with **Protobuf** for gRPC service APIs and event payloads, **AsyncAPI** for
  Kafka topics, **GraphQL SDL** for the BFF.
- Define the canonical `Order` / `Trade` messages **once** here; generate the C++ codec, the Go structs,
  and the TS types. This supersedes `bridge/decoder.py`'s `ORDER_FORMAT`/`TRADE_FORMAT` and the
  fixed-point scaling scattered across the bridge/dashboard.
- Add a CI check that fails on breaking schema changes (buf lint + buf breaking).
- **Verification:** generated C++ decode round-trips the existing 64-byte layout (golden-bytes test).

### 0.3 Infrastructure as Code
- Terraform modules for: Kubernetes cluster, managed Postgres, ClickHouse/Timescale, Redis, object
  store, Redpanda/Kafka, Vault.
- Per-environment workspaces (dev / staging / prod).
- **Verification:** `terraform plan` clean; a dev cluster comes up from zero.

### 0.4 CI/CD & GitOps
- Extend the existing GitHub Actions pipeline into reusable workflows: build → unit → contract → image
  build → SBOM/Trivy scan → push.
- Argo CD (or Flux) syncs `deploy/` manifests; ephemeral preview environments per PR.
- **Fix the existing CI bug:** `apt_get` → `apt-get` in `.github/workflows/ci.yml` (lines 24, 65).
- Trunk-based branching, required checks, signed commits.
- **Verification:** a trivial PR builds, scans, and deploys to a preview namespace automatically.

### 0.5 Service mesh & zero-trust baseline
- Install Istio/Linkerd; enforce **mTLS** mesh-wide; default-deny network policies.
- Vault for secrets; no plaintext secrets in env or Git.
- **Verification:** service-to-service traffic is mTLS; a pod without policy cannot reach the ledger.

### 0.6 Observability baseline
- OpenTelemetry SDK/collector; Prometheus, Loki, Tempo/Jaeger, Grafana, Alertmanager.
- A **correlation-ID** convention propagated from client → BFF → services → Chronos audit.
- Starter dashboards + golden-signal alerts (latency, errors, saturation, traffic).
- **Verification:** a synthetic request shows a full distributed trace end-to-end.

### 0.7 Service template (golden path)
- A reference microservice (hexagonal layout, health/readiness, OTel, gRPC + event consumer, Dockerfile,
  Helm chart, test scaffolding) that all later services are cloned from.
- **Verification:** template service deploys and reports healthy with traces/metrics flowing.

## Exit criteria
Contracts generate code in 3 languages; a templated service ships through CI/CD to a meshed, observable
cluster; Chronos still builds and tests green from its new monorepo home.
