# Task 0.1 — Monorepo & Workspace Layout

## Goal
Establish a monorepo layout that hosts the existing Chronos engine, new microservices, the client apps,
and shared contracts — **additively**, without breaking the current `cmake`/`ctest` build.

## Key Files & Context
- Existing (unchanged for now): `include/`, `src/`, `tests/`, `bridge/`, `dashboard/`, `CMakeLists.txt`.
- New: `MONOREPO.md` (layout + migration), top-level `services/`, `clients/`, `libs/`, `contracts/`,
  `infra/`, `deploy/` with placeholder `README.md` each.

## Implementation Steps
1. **Document the target layout** in `MONOREPO.md`: what each top-level directory owns and the
   eventual home of today's code (engine → `services/execution-core/`, `bridge/` → `services/market-data/`,
   `dashboard/` → `clients/web/`).
2. **Create the directories additively** with README stubs so the structure exists and CI can find it,
   but **do not move existing code yet** — relocation is a deliberate, separate step (Task 0.1b) to avoid
   breaking CMake include paths, CI, and Docker context.
3. **Pick the build orchestration** approach: a pragmatic top-level `Makefile`/`justfile` that delegates
   to each project's native tool (CMake, Go, Gradle, Xcode, npm). Avoid forcing one build system over
   heterogeneous languages.
4. **Codeowners & conventions**: `CODEOWNERS`, commit conventions (Conventional Commits), and a
   `CONTRIBUTING.md` describing trunk-based development.

## Verification
- `cmake -B build -S . -DCMAKE_BUILD_TYPE=Release && cmake --build build` still succeeds from repo root.
- `cd build && ctest --output-on-failure` still green.
- New top-level directories exist with READMEs; nothing existing was relocated or broken.
