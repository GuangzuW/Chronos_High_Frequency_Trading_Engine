# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Chronos is an ultra-low-latency C++20 Limit Order Book matching engine, plus a Python (FastAPI) bridge and a Next.js dashboard. Three processes talk over ZeroMQ:

```
Finnhub WS ─► bridge/feeder.py ─┐
                                 ├─► [ZMQ DEALER → ROUTER :5555] ─► chronos_engine (C++)
dashboard (Next.js) ─► bridge/main.py ─┘                                   │
        ▲                                                                  │ matches
        │ WebSocket (JSON)                                                 ▼
        └──── bridge/main.py SUB ◄── [ZMQ PUB :5556  topics TRADE/ORDER] ──┘
```

- **Engine** (`src/main.cpp` + `include/chronos/`): receives binary orders on `:5555`, runs risk checks, matches, publishes binary trade/order events on `:5556`.
- **Bridge** (`bridge/`): ZMQ↔WebSocket/REST translator. Subscribes to engine events and rebroadcasts JSON to the dashboard; exposes `POST /order`; optionally spawns the Finnhub feeder.
- **Dashboard** (`dashboard/`): Next.js 16 + React 19 + Zustand + lightweight-charts UI.

## Build, test, run

```bash
# Build engine (Release)
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
cmake --build build

# Run all tests (Debug build enables --coverage)
cmake -B build-debug -S . -DCMAKE_BUILD_TYPE=Debug
cmake --build build-debug
cd build-debug && ctest --output-on-failure

# Run a single test suite — every suite is registered as both a ctest entry
# and a gtest filter. Either of these works:
ctest -R MatchingTest --output-on-failure        # by ctest name
./build-debug/tests/unit_tests --gtest_filter=MatchingTest.*

# Static analysis (CI gate; run before pushing)
cppcheck --enable=all --error-exitcode=1 --suppress=missingIncludeSystem include/ src/

# Run engine
./build/bin/chronos_engine        # gateway :5555, publisher :5556

# Bridge + feeder (needs FINNHUB_API_KEY in bridge/.env)
cp bridge/.env.example bridge/.env
START_FEEDER=1 PYTHONPATH=. python bridge/main.py    # serves :8000

# Dashboard
cd dashboard && npm install && npm run dev    # :3000; npm run lint to lint
```

The build treats warnings as errors (`-Werror` / `/WX`). ONNX Runtime and CppCheck are optional — CMake degrades gracefully (`HAS_ONNXRUNTIME` define gates the AI path; without it the risk engine returns mock scores).

## Architecture notes that span multiple files

**The engine is header-only.** All logic lives in `include/chronos/*.hpp`; `src/main.cpp` is the only translation unit and just wires the components into the hot loop. To change matching/risk/gateway behavior, edit the headers. New components must be added to *both* the `chronos_engine` target and the `tests/unit_tests` target (see `tests/CMakeLists.txt`).

**The hot loop** (`src/main.cpp`): pin to core 1 → `gateway.receiveOrder()` (non-blocking, busy-spins) → `risk_engine.validateOrder()` (reject if score > 0.8) → `matching_engine.processOrder()`. The matching path is designed for zero allocation: a single `MemoryPool` (`std::pmr::monotonic_buffer_resource`) is threaded through everything, and order books are `std::pmr` containers.

**Matching** (`limit_order_book.hpp`): FIFO price-time priority. Bids are a `std::map<Price, PriceLevel, std::greater>`, asks `std::less`, so `begin()` is always the best price. `order_lookup_` gives O(1) cancel. The LOB publishes events itself (it holds the `EventPublisher*`) — both resting-order fills *and* the incoming order's final state.

**Sharding** (`sharded_matching_engine.hpp`): one `LimitOrderBook` per symbol, routed by the order's `symbol` field. **Symbols must be pre-registered** via `addSymbol()` — `main.cpp` hardcodes `AAPL`, `BTC`, `ETH`. **Orders for unregistered symbols are silently dropped** (return empty trades). Add a symbol in all three of: `main.cpp` `addSymbol`, the feeder's `SYMBOL_MAP`, and as needed in the dashboard.

### Two cross-language contracts that MUST stay in sync

These are the most fragile, recurring source of bugs (see recent "scaling sync" / "scaling synchronize" commits).

1. **Binary wire format — 64-byte structs.** `Order` and `Trade` in `include/chronos/types.hpp` are `alignas(64)` with explicit padding. The Python side reconstructs them byte-for-byte via `struct` format strings in `bridge/decoder.py` (`ORDER_FORMAT = "Q8sqqBB6xQ16x"`, `TRADE_FORMAT = "QQqqQ24x"`). The gateway/publisher do raw `memcpy` of `sizeof(Order)`/`sizeof(Trade)`. **Any field/padding change to the C++ structs requires the matching change to the format strings**, or decode silently fails the 64-byte length check. Symbol is a fixed `char[8]` — max 8 chars.

2. **Fixed-point scaling.** The engine stores prices and quantities as scaled integers: **price × 100, quantity × 1000**. This convention is duplicated (not shared) across `bridge/main.py` (`POST /order`), `bridge/feeder.py` (`synthesize_and_send_orders`), and `dashboard/src/store/useTradeStore.ts` (which divides back: `/100`, `/1000`). Change one, change all three.

**ZMQ topology:** engine `ROUTER` binds `:5555` (ingress); clients use `DEALER`. Engine `PUB` binds `:5556`; subscribers filter on string topics `"TRADE"` and `"ORDER"`, each followed by a 64-byte binary frame. The bridge runs its SUB loop on a daemon thread and marshals to the asyncio WebSocket broadcast.

**Strong types** (`strong_type.hpp`): `OrderId`/`Price`/`Quantity` are distinct wrapper types over integers — use `.value()` to get the underlying number. They prevent accidentally mixing a price with a quantity.

**Risk engine** (`risk_engine.hpp`): static checks (qty/price/notional limits in `RiskConfig`) always run and return 1.0 (reject) on violation. The ONNX inference path is currently a placeholder returning a constant — wiring real inference is future work.

## Conventions

- Modern C++20 only; prefer `std::span`/`std::pmr`; no exceptions on the hot path (return codes / `std::optional`).
- Keep critical structs cache-line aligned (64 bytes) — and remember the binary contract above when touching them.
- New engine logic needs a GTest suite in `tests/`, registered in `tests/CMakeLists.txt` as both a source file and an `add_test` filter entry.
- `Architecture.md` and `Detailed_Roadmap*.md` are the design source of truth; `Plan/task-*.md` are per-task implementation notes.
