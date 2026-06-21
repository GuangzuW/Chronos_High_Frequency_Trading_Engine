# Task 0.2 — Contract-First Schema Repository

## Goal
Create one **versioned source of truth** for the wire/event/API contracts and generate code for C++, Go,
and TypeScript from it. This eliminates the hand-synced 64-byte struct format and the duplicated
fixed-point scaling that are today's recurring bug source.

## Key Files & Context
- Today's contract is implicit and duplicated across:
  - `include/chronos/types.hpp` — `alignas(64)` `Order`/`Trade` structs.
  - `bridge/decoder.py` — `ORDER_FORMAT = "Q8sqqBB6xQ16x"`, `TRADE_FORMAT = "QQqqQ24x"`.
  - `bridge/main.py`, `bridge/feeder.py`, `dashboard/src/store/useTradeStore.ts` — `×100`/`×1000` scaling.
- New: `contracts/` — `buf.yaml`, `buf.gen.yaml`, `proto/chronos/trading/v1/*.proto`, `WIRE_FORMAT.md`,
  `README.md`.

## Implementation Steps
1. **Define proto messages** for `Order`, `Trade`, enums (`OrderSide`, `OrderStatus`), and the
   fixed-point scaling constants — see `contracts/proto/chronos/trading/v1/types.proto`.
2. **Specify the fixed binary layout** the C++ codec must emit/parse in `WIRE_FORMAT.md` (the canonical
   64-byte layout), since protobuf's own encoding is not the on-wire format Chronos uses. Include a
   golden-bytes fixture.
3. **Set up `buf`**: `buf lint`, `buf breaking` (against `main`), and `buf generate` producing C++
   (for `chronos-client-core` and the Market Gateway), Go (services), and TS (clients/web).
4. **Wire CI**: add a contracts job that lints, checks for breaking changes, and verifies generated code
   is up to date (`buf generate` produces no diff).
5. **Add a golden round-trip test**: encode a known `Order` with the generated codec → assert the exact
   64 bytes match `types.hpp`'s layout (and that `decoder.py`'s format string would decode it).

## Status / what exists
- ✅ `proto/chronos/trading/v1/types.proto`, `WIRE_FORMAT.md`, `buf.yaml`, `buf.gen.yaml`, `README.md`.
- ✅ **Wire codec implemented:** `libs/client-core/include/chronos/client/wire.hpp` — portable,
  explicit-LE, header-only `encode/decode` for `Order`/`Trade` + symbol & fixed-point helpers. This is
  the enforced artifact that replaces `bridge/decoder.py`'s format strings.
- ✅ **Golden gate (C++):** `tests/test_wire_codec.cpp` (`WireCodecTest`) — golden bytes, round-trip, and
  engine binary-compatibility; wired into `tests/CMakeLists.txt`.
- ✅ **Python codec:** `bridge/wire.py` — single source of the format + scaling on the Python side;
  `bridge/decoder.py` is now a backward-compat shim; `main.py`/`feeder.py` use `wire.scale_*` (no more
  inline `×100`/`×1000`).
- ✅ **Python tests:** `bridge/tests/test_wire.py` — 15 cases (golden bytes matching the C++ fixtures,
  round-trip, scaling incl. the float-truncation bug fix, symbol truncation, error handling, shim).
  Run: `PYTHONPATH=. python3 -m unittest bridge.tests.test_wire`. **All passing.**
- ✅ **Dashboard:** `dashboard/src/lib/scaling.ts` centralizes the TS scaling; `useTradeStore.ts` uses it.
- ⬜ `buf generate` of the proto bindings (deferred — needs `buf` + network; not the on-wire format).

## Verification
- `ctest -R WireCodecTest --output-on-failure` passes (run in CI / any box with the C++ toolchain).
- `buf lint` and `buf breaking` pass (once `buf` is available).
- A deliberate field reorder in `encodeOrder` fails the golden test (proving the contract is enforced).
