# Monorepo Layout — Chronos Trade Platform

This repo is evolving from a single C++ matching engine into the **Chronos Trade** platform: a
microservices backend (built around the reused Chronos engine) plus multi-platform clients. The layout
below is being introduced **additively** — existing code keeps working and is relocated only in
deliberate, separate steps so the current `cmake`/`ctest`/Docker build never breaks mid-flight.

See `Plan/Platform/00-master-architecture-and-roadmap.md` for the full design and roadmap.

## Top-level directories

| Directory | Owns | Status |
|---|---|---|
| `contracts/` | Protobuf/AsyncAPI/GraphQL schemas; generated C++/Go/TS bindings; wire-format spec | **created** |
| `services/` | Backend microservices (Go / C++ / Rust), each hexagonal + containerized | scaffold (stubs) |
| `clients/` | Apps — React Native (Android/iOS/macOS/Windows) + web reference | scaffold (stubs) |
| `libs/` | Shared libraries, incl. `chronos-client-core` (C++ via JSI) and the service template | scaffold (stubs) |
| `infra/` | Terraform IaC + local `docker-compose`/`kind` for the dev inner loop | scaffold (stubs) |
| `deploy/` | Helm charts, Argo CD apps, mesh + observability manifests (GitOps) | scaffold (stubs) |
| `Plan/Platform/` | Architecture + phased roadmap + per-task plans | **created** |

## Existing code (unchanged for now)

| Today | Eventual home | Migration |
|---|---|---|
| `include/`, `src/`, `tests/`, `CMakeLists.txt` | `services/execution-core/` | Task 0.1b (deliberate move; update CMake/CI/Docker paths together) |
| `bridge/` (FastAPI + ZMQ + Finnhub) | `services/market-data/` (seed) | Phase 2 |
| `dashboard/` (Next.js) | `clients/web/` (reference) | Phase 4 |

**Why additive first:** moving `include/`/`src/` would break CMake include paths, the GitHub Actions
build, and the Docker build context simultaneously. Those moves are scheduled as explicit tasks with
their own verification, not done implicitly here.

## Build orchestration
A top-level `Makefile`/`justfile` delegates to each project's native toolchain (CMake, Go, Gradle/Xcode,
npm) rather than forcing one build system across heterogeneous languages. The engine continues to build
exactly as documented in `CLAUDE.md`.
