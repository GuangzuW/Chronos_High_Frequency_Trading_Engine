# contracts/ — Single Source of Truth for Schemas

Every cross-boundary type — service APIs, event payloads, and the engine wire format — is defined here
**once** and code-generated for C++, Go, and TypeScript. Nothing downstream hand-writes these types.

This directly replaces the previously duplicated/hand-synced definitions:

| Was (duplicated, drift-prone) | Now (generated from here) |
|---|---|
| `include/chronos/types.hpp` structs | `proto/chronos/trading/v1/types.proto` + `WIRE_FORMAT.md` |
| `bridge/decoder.py` `ORDER_FORMAT`/`TRADE_FORMAT` | generated codec + golden test |
| `×100` / `×1000` scaling in `main.py`, `feeder.py`, `useTradeStore.ts` | `Scaling` enum + generated helpers |

## Layout
```
contracts/
  buf.yaml            # lint + breaking-change config
  buf.gen.yaml        # codegen targets (cpp / go / ts)
  WIRE_FORMAT.md      # authoritative 64-byte binary layout + golden fixtures
  proto/chronos/trading/v1/
    types.proto       # Order, Trade, enums, fixed-point scaling
  gen/                # generated code (git-ignored or checked in per policy)
```

## Workflow
```bash
buf lint                       # style
buf breaking --against '.git#branch=main'   # no breaking changes
buf generate                   # regenerate cpp/go/ts; CI fails if this produces a diff
```

## Rules
1. **Logical schema lives in `.proto`; the on-wire byte layout lives in `WIRE_FORMAT.md`.** Protobuf's own
   encoding is *not* the engine's wire format — the engine uses fixed 64-byte structs. The C++ codec maps
   the proto types to that layout and is locked by the golden-bytes test.
2. **Additive changes only** without a version bump (`v1` → `v2`). `buf breaking` enforces this in CI.
3. Touching `Order`/`Trade` means: edit `types.proto`, update `WIRE_FORMAT.md` if the layout changes,
   regenerate, and update the golden fixture. The build fails until all three agree.

## Implementation
- **Codec:** `libs/client-core/include/chronos/client/wire.hpp` — the portable, explicit-LE C++
  implementation of `WIRE_FORMAT.md`. Single source of the 64-byte encode/decode and `×100`/`×1000`
  scaling.
- **Golden gate:** `tests/test_wire_codec.cpp` (`WireCodecTest`) locks the codec to the exact bytes and
  proves binary-compatibility with the engine `chronos::Order`/`Trade` structs. Run with
  `ctest -R WireCodecTest`.

See `Plan/Platform/task-0-2-contracts.md` for the full task plan.
