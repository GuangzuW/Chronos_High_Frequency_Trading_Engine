import struct
from bridge.schemas import Order, Trade, OrderSide, OrderStatus

# Q: uint64 (8), 8s: char[8] (8), q: int64 (8), q: int64 (8), B: uint8 (1), B: uint8 (1), 6x: padding (6), Q: uint64 (8), 16x: padding (16)
# Total: 8+8+8+8+1+1+6+8+16 = 64 bytes
ORDER_FORMAT = "Q8sqqBB6xQ16x"

# Q: uint64 (8), Q: uint64 (8), q: int64 (8), q: int64 (8), Q: uint64 (8), 24x: padding (24)
# Total: 8+8+8+8+8+24 = 64 bytes
TRADE_FORMAT = "QQqqQ24x"

def decode_order(data: bytes) -> Order:
    if len(data) != 64:
        raise ValueError(f"Invalid Order data size: {len(data)}, expected 64")
    
    unpacked = struct.unpack(ORDER_FORMAT, data)
    symbol = unpacked[1].decode('utf-8').strip('\x00')
    
    return Order(
        id=unpacked[0],
        symbol=symbol,
        price=unpacked[2],
        quantity=unpacked[3],
        side=OrderSide(unpacked[4]),
        status=OrderStatus(unpacked[5]),
        timestamp=unpacked[6]
    )

def decode_trade(data: bytes) -> Trade:
    if len(data) != 64:
        raise ValueError(f"Invalid Trade data size: {len(data)}, expected 64")
    
    unpacked = struct.unpack(TRADE_FORMAT, data)
    
    return Trade(
        buy_order_id=unpacked[0],
        sell_order_id=unpacked[1],
        price=unpacked[2],
        quantity=unpacked[3],
        timestamp=unpacked[4]
    )

def encode_order(order: Order) -> bytes:
    """Encode Order into binary format for the C++ engine"""
    symbol_bytes = order.symbol.encode('utf-8').ljust(8, b'\x00')
    return struct.pack(
        ORDER_FORMAT,
        order.id,
        symbol_bytes,
        order.price,
        order.quantity,
        int(order.side),
        int(order.status),
        order.timestamp
    )
