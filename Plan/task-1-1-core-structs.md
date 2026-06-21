# Implementation Plan: Task 1.1 - Define Core Logic Structs

Establish the core data structures for the Chronos HFT Engine, ensuring they are cache-efficient and aligned to 64-byte cache lines.

## Objective
Define `Order` and `Trade` structs with appropriate fields, type-safe enums for order properties, and explicit alignment for performance.

## Key Files & Context
- `include/chronos/types.hpp`: New header for core type definitions.
- `tests/test_types.cpp`: New test file to verify struct sizes and alignment.
- `tests/CMakeLists.txt`: Updated to include the new test.

## Implementation Steps

### 1. Create `include/chronos/types.hpp`
Define the following:
- `OrderSide` enum class (Buy/Sell).
- `OrderStatus` enum class (New, Filled, etc.).
- `Price` and `Quantity` as `int64_t` (fixed-point representation).
- `Order` struct:
  - `uint64_t id`
  - `char symbol[8]`
  - `int64_t price`
  - `int64_t quantity`
  - `OrderSide side`
  - `OrderStatus status`
  - `uint64_t timestamp`
  - `alignas(64)` for cache efficiency.
- `Trade` struct:
  - `uint64_t buy_order_id`
  - `uint64_t sell_order_id`
  - `int64_t price`
  - `int64_t quantity`
  - `uint64_t timestamp`
  - `alignas(64)` for cache efficiency.

### 2. Create `tests/test_types.cpp`
- Verify `sizeof(Order) == 64`.
- Verify `sizeof(Trade) == 64`.
- Verify fields are correctly initialized.

### 3. Update `tests/CMakeLists.txt`
- Add `test_types.cpp` to the `unit_tests` executable.

## Verification & Testing
1.  Run `cmake --build build`.
2.  Run `cd build && ctest --output-on-failure`.
3.  Check that all tests in `CoreTypesTest` pass.
