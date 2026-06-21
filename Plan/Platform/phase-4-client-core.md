# Phase 4 — Shared C++ Client Core + React Native Shell

## Goal
Build **`chronos-client-core`** (the shared high-performance C++ library) and the React Native app
shell that runs on **Android, iOS, macOS, and Windows**, with the C++ core exposed to JS via **JSI**.

This realizes the chosen client strategy: *React Native + desktop, with C++ for high performance.*

## Tasks

### 4.1 `chronos-client-core` library (`libs/client-core/`)
- C++20 library with these modules:
  - **Codec** — generated from `contracts/` (§0.2); the single definition of the 64-byte wire format and
    the **fixed-point scaling** (×100 price, ×1000 qty) — replacing the convention duplicated today in
    `bridge/main.py`, `feeder.py`, and `dashboard/.../useTradeStore.ts`.
  - **Order book** — maintain L2 from deltas; produce render-ready aggregated snapshots.
  - **Transport** — multiplexed, compressed, auto-reconnecting WebSocket client + subscription manager.
  - **Cache & signing** — local snapshots, token storage, per-request signing.
- Reuse Chronos idioms (strong types, fixed-point, cache-friendly structs) where applicable.
- Unit + property tests; golden-bytes test against the engine's struct layout.
- **Verification:** core builds standalone for arm64/x86_64; book-from-deltas matches a server snapshot.

### 4.2 Cross-platform build of the core
- Android: NDK/CMake → `.so` via JNI; iOS+macOS: XCFramework via C++ interop / thin Obj-C++ shim;
  Windows: native module (N-API / RN-Windows C++).
- **Verification:** the same core source compiles and loads on all four platforms in CI.

### 4.3 JSI / TurboModule binding
- Expose the core to React Native New Architecture (Fabric + TurboModules) over **JSI** —
  synchronous, low-overhead, zero-copy where possible for book snapshots.
- **Verification:** JS calls into C++ decode and book APIs and gets results without bridge serialization.

### 4.4 React Native app shell
- RN New Architecture project targeting Android + iOS; **React Native for Windows + macOS** for desktop.
- Shared TS UI layer (navigation, theming, auth screens), reusing patterns/components from the existing
  `dashboard/` (OrderBook, TradeTape, PriceChart, OrderEntry) as design references.
- Auth flow against the Identity service; secure token storage per platform (Keychain/Keystore/DPAPI).
- **Verification:** the app launches on all four targets, logs in, and renders an empty trading screen
  fed by the C++ core's transport.

### 4.5 Client observability & CI
- Crash reporting, client-side OTel spans correlated with backend traces, app CI (build all 4 targets,
  Detox E2E smoke).
- **Verification:** a client action produces a trace that joins the backend trace by correlation ID.

## Exit criteria
One React Native codebase + one C++ core runs natively on Android, iOS, macOS, and Windows;
high-performance data handling lives in C++; the app authenticates and connects to live data.
