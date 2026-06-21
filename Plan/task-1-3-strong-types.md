# Implementation Plan: Task 1.3 - Define Type-Safe Identifiers

Enhance the type safety of the Chronos HFT Engine by replacing basic type aliases with strong types for critical identifiers and values.

## Objective
Implement strong types for `Price`, `Quantity`, `OrderId`, and `Symbol` to prevent accidental type mixing and ensure clear semantic meaning in the codebase.

## Key Files & Context
- `include/chronos/types.hpp`: Update existing type definitions.
- `tests/test_types.cpp`: Update and add tests for strong types.

## Implementation Steps

### 1. Implement Strong Type Wrapper
Define a simple template wrapper `StrongType<T, Tag>` in `include/chronos/types.hpp` (or a new `strong_type.hpp` if it gets too large) to provide:
- Explicit construction from underlying type.
- Implicit conversion to underlying type (where safe/desired) or an `underlying()` method.
- Comparison operators.
- Arithmetic operators (for `Price` and `Quantity`).

### 2. Update `include/chronos/types.hpp`
Replace the current `using` aliases with strong types:
- `OrderId`: `StrongType<uint64_t, struct OrderIdTag>`
- `Price`: `StrongType<int64_t, struct PriceTag>`
- `Quantity`: `StrongType<int64_t, struct QuantityTag>`
- Keep `OrderSide` and `OrderStatus` as `enum class` (already implemented).
- Refactor `Order` and `Trade` structs to use these new types.

### 3. Update `tests/test_types.cpp`
- Verify that `Price` and `Quantity` cannot be implicitly mixed.
- Verify that arithmetic on `Price` and `Quantity` works as expected.
- Verify that `OrderId` works as a unique identifier type.
- Ensure struct alignment and size (64 bytes) are preserved.

## Verification & Testing
1.  Run `cmake --build build`.
2.  Run `cd build && ctest --output-on-failure`.
3.  Ensure all `CoreTypesTest` pass with the new strong types.
