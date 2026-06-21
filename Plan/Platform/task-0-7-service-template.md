# Task 0.7 — Service Template (Golden Path)

## Goal
Produce a reference microservice that bakes in every platform convention, so new services are cloned
rather than hand-assembled. This locks in hexagonal architecture, observability, and contract usage.

## Key Files & Context
- New: `libs/service-template/` (Go reference) — hexagonal layout, gRPC server + Kafka consumer,
  generated contract bindings, health/readiness, OTel, Dockerfile, Helm chart, tests.

## Implementation Steps
1. **Hexagonal layout**: `domain/` (framework-free core), `app/` (use cases), `adapters/` (gRPC, Kafka,
   Postgres, HTTP). Mirrors how the Chronos engine keeps domain logic free of ZMQ.
2. **Contract wiring**: consume generated stubs from `contracts/` (Task 0.2); no hand-written DTOs.
3. **Cross-cutting**: health/readiness probes, graceful shutdown, OTel tracing/metrics/logging,
   correlation-ID propagation, config via environment (12-factor).
4. **Testing scaffold**: unit + a consumer-driven contract test (Pact) + an integration test using the
   local compose dependencies (Task 0.3).
5. **Packaging**: multi-stage Dockerfile (mirroring the existing engine Dockerfile pattern) and a Helm
   chart wired for Argo CD (Task 0.4).
6. **Generator**: a `make new-service NAME=...` (or `copier`/`cookiecutter`) that stamps a new service
   from the template.

## Verification
- `make new-service NAME=ping` produces a service that builds, passes its tests, deploys via CI/CD to a
  preview namespace, reports healthy, and emits a trace/metric/log to the observability stack.
