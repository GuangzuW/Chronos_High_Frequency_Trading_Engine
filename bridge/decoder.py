"""Backward-compatible shim.

The canonical wire codec now lives in `bridge.wire` (the single source of truth shared
with the C++ engine/client via contracts/WIRE_FORMAT.md). This module re-exports it so
existing `from bridge.decoder import decode_order, decode_trade, encode_order` imports
keep working. New code should import from `bridge.wire` directly.
"""

from bridge.wire import (
    ORDER_FORMAT,
    TRADE_FORMAT,
    decode_order,
    decode_trade,
    encode_order,
    encode_trade,
)

__all__ = [
    "ORDER_FORMAT",
    "TRADE_FORMAT",
    "decode_order",
    "decode_trade",
    "encode_order",
    "encode_trade",
]
