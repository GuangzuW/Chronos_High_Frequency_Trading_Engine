# Implementation Plan: Task 1.2 - Binary Decoder Implementation

Implement the logic to convert raw 64-byte C++ binary buffers into Python-friendly objects (JSON/Pydantic).

## Objective
Create a robust decoder that understands the memory layout of the C++ `Order` and `Trade` structs, ensuring perfect compatibility with the matching engine's output.

## Key Files
- `bridge/decoder.py`: New utility for binary parsing.
- `bridge/tests/test_decoder.py`: Local tests for the decoder.

## Implementation Steps

### 1. Define Format Strings
- `ORDER_FORMAT = "Q8sqqBB6xQ16x"` (64 bytes)
- `TRADE_FORMAT = "QQqqQ24x"` (64 bytes)

### 2. Implement `decode_order(buffer: bytes) -> Order`
- Use `struct.unpack` with the order format.
- Clean up the `symbol` (remove null terminators).
- Map to the `Order` Pydantic model.

### 3. Implement `decode_trade(buffer: bytes) -> Trade`
- Use `struct.unpack` with the trade format.
- Map to the `Trade` Pydantic model.

### 4. Implement Encoder (Optional for Task 1.4)
- `encode_order(order: Order) -> bytes`
- This will be needed later when sending orders from the UI to the engine.

## Verification
- Create a dummy 64-byte buffer in a Python script.
- Verify that `decode_order` returns an object with correct values.
