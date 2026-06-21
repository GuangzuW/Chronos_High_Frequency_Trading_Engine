"""Canonical Chronos wire codec — Python side (single source of truth).

This module is the ONE place the Python services define the 64-byte Order/Trade binary
format and the fixed-point scaling convention. It mirrors:
  - contracts/WIRE_FORMAT.md                              (authoritative byte layout + golden fixtures)
  - libs/client-core/include/chronos/client/wire.hpp      (the portable C++ codec)
  - contracts/proto/chronos/trading/v1/types.proto        (logical schema + Scaling enum)

It replaces the previously duplicated/hand-synced definitions:
  * struct format strings that used to live only in bridge/decoder.py
  * the ×100 / ×1000 scaling that was copy-pasted into bridge/main.py, bridge/feeder.py
    and dashboard/src/store/useTradeStore.ts

Backward compatibility: bridge/decoder.py now re-exports from here, so existing
`from bridge.decoder import decode_order, ...` imports keep working.
"""

import struct

from bridge.schemas import Order, OrderSide, OrderStatus, Trade

# ---- Layout constants (see WIRE_FORMAT.md) ----------------------------------------------
MESSAGE_SIZE = 64
SYMBOL_SIZE = 8

# ---- Fixed-point scaling (see WIRE_FORMAT.md / proto Scaling enum) -----------------------
PRICE_SCALE = 100      # 2 decimal places
QUANTITY_SCALE = 1000  # 3 decimal places

# Explicit little-endian, standard sizes, with explicit padding bytes — matches the
# C++ alignas(64) structs on every (little-endian) target platform. The leading '<'
# makes endianness explicit and disables native alignment padding; the explicit pad
# fields (6x / 16x / 24x) reproduce the C++ struct layout exactly.
#   Order: id(Q) symbol(8s) price(q) quantity(q) side(B) status(B) pad(6x) timestamp(Q) pad(16x)
#   Trade: buy(Q) sell(Q) price(q) quantity(q) timestamp(Q) pad(24x)
ORDER_FORMAT = "<Q8sqqBB6xQ16x"
TRADE_FORMAT = "<QQqqQ24x"


# ---- Symbol helpers ----------------------------------------------------------------------
def make_symbol(symbol: str) -> bytes:
    """Encode a ticker into the fixed 8-byte NUL-padded field (truncates > 8 chars)."""
    return symbol.encode("ascii")[:SYMBOL_SIZE].ljust(SYMBOL_SIZE, b"\x00")


def symbol_to_string(raw: bytes) -> str:
    """Decode a fixed 8-byte symbol field back to a string (strips NUL padding)."""
    return raw.split(b"\x00", 1)[0].decode("ascii", errors="ignore")


# ---- Fixed-point helpers -----------------------------------------------------------------
# Uses round(), matching the C++ std::llround in wire.hpp. (The old code used int(), which
# truncated — e.g. int(0.29 * 100) == 28 due to float error; round() correctly gives 29.)
def scale_price(price: float) -> int:
    return round(price * PRICE_SCALE)


def unscale_price(scaled: int) -> float:
    return scaled / PRICE_SCALE


def scale_quantity(qty: float) -> int:
    return round(qty * QUANTITY_SCALE)


def unscale_quantity(scaled: int) -> float:
    return scaled / QUANTITY_SCALE


# ---- Order codec (WIRE_FORMAT.md §Order) -------------------------------------------------
def encode_order(order: Order) -> bytes:
    """Encode an Order into its 64-byte wire representation for the C++ engine."""
    return struct.pack(
        ORDER_FORMAT,
        order.id,
        make_symbol(order.symbol),
        order.price,
        order.quantity,
        int(order.side),
        int(order.status),
        order.timestamp,
    )


def decode_order(data: bytes) -> Order:
    if len(data) != MESSAGE_SIZE:
        raise ValueError(f"Invalid Order data size: {len(data)}, expected {MESSAGE_SIZE}")
    u = struct.unpack(ORDER_FORMAT, data)
    return Order(
        id=u[0],
        symbol=symbol_to_string(u[1]),
        price=u[2],
        quantity=u[3],
        side=OrderSide(u[4]),
        status=OrderStatus(u[5]),
        timestamp=u[6],
    )


# ---- Trade codec (WIRE_FORMAT.md §Trade) -------------------------------------------------
def encode_trade(trade: Trade) -> bytes:
    return struct.pack(
        TRADE_FORMAT,
        trade.buy_order_id,
        trade.sell_order_id,
        trade.price,
        trade.quantity,
        trade.timestamp,
    )


def decode_trade(data: bytes) -> Trade:
    if len(data) != MESSAGE_SIZE:
        raise ValueError(f"Invalid Trade data size: {len(data)}, expected {MESSAGE_SIZE}")
    u = struct.unpack(TRADE_FORMAT, data)
    return Trade(
        buy_order_id=u[0],
        sell_order_id=u[1],
        price=u[2],
        quantity=u[3],
        timestamp=u[4],
    )
