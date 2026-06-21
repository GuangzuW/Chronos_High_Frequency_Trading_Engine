# Chronos Wire Format (v1) — Authoritative Byte Layout

This document defines the **exact 64-byte, cache-aligned binary layout** exchanged between the Chronos
engine and its clients over ZeroMQ. It is the on-wire contract that the generated C++ codec
(`chronos-client-core`) and the Market Gateway MUST produce and parse. A golden-bytes test
(`contracts` CI) locks generated code against the fixtures below.

It mirrors `include/chronos/types.hpp` (`alignas(64)` structs) and the Python `struct` format strings in
`bridge/decoder.py`. **Change this only by changing `types.proto` and regenerating — never by hand.**

- **Endianness:** little-endian. All four client targets (Android arm64, iOS/macOS arm64+x86_64,
  Windows x86_64) and the Linux x86_64 engine are little-endian. The codec encodes LE explicitly for
  portability — it does not rely on host byte order.
- **Sizes:** total 64 bytes per message; offsets are byte offsets from the start of the frame.
- **Enums on the wire** use the engine's native `uint8_t` values (BUY=0, SELL=1; NEW=0, PARTIAL=1,
  FILLED=2, CANCELED=3, REJECTED=4) — see the mapping note in `types.proto`.

## §Order — 64 bytes  (Python: `Q8sqqBB6xQ16x`)

| Offset | Size | Field | Type | Notes |
|---|---|---|---|---|
| 0  | 8  | `id`          | uint64 LE | OrderId |
| 8  | 8  | `symbol`      | char[8]   | ASCII, NUL-padded, max 8 chars |
| 16 | 8  | `price`       | int64 LE  | fixed-point ×100 |
| 24 | 8  | `quantity`    | int64 LE  | fixed-point ×1000 |
| 32 | 1  | `side`        | uint8     | 0=Buy, 1=Sell |
| 33 | 1  | `status`      | uint8     | 0=New … 4=Rejected |
| 34 | 6  | (padding)     | zero      | alignment to 8 for timestamp |
| 40 | 8  | `timestamp_ns`| uint64 LE | nanoseconds since epoch |
| 48 | 16 | (padding)     | zero      | pad struct to 64 |

### Golden fixture — Order
`id=1001, symbol="AAPL", price=15025 (150.25), quantity=5000 (5.000), side=Buy, status=New, timestamp=0`

```
offset 00: E9 03 00 00 00 00 00 00   # id = 1001
offset 08: 41 41 50 4C 00 00 00 00   # "AAPL"
offset 10: B1 3A 00 00 00 00 00 00   # price = 15025
offset 18: 88 13 00 00 00 00 00 00   # quantity = 5000
offset 20: 00 00 00 00 00 00 00 00   # side=0, status=0, +6 pad
offset 28: 00 00 00 00 00 00 00 00   # timestamp = 0
offset 30: 00 00 00 00 00 00 00 00   # pad
offset 38: 00 00 00 00 00 00 00 00   # pad
```

## §Trade — 64 bytes  (Python: `QQqqQ24x`)

| Offset | Size | Field | Type | Notes |
|---|---|---|---|---|
| 0  | 8  | `buy_order_id`  | uint64 LE | |
| 8  | 8  | `sell_order_id` | uint64 LE | |
| 16 | 8  | `price`         | int64 LE  | fixed-point ×100 |
| 24 | 8  | `quantity`      | int64 LE  | fixed-point ×1000 |
| 32 | 8  | `timestamp_ns`  | uint64 LE | |
| 40 | 24 | (padding)       | zero      | pad struct to 64 |

## ZeroMQ framing
- **Ingress** (client → engine): single frame containing the 64-byte `Order`, sent on a DEALER socket to
  the engine ROUTER `:5555`.
- **Egress** (engine → subscribers): two frames — a topic string frame (`"TRADE"` or `"ORDER"`) followed
  by the 64-byte payload — published on PUB `:5556`.
