# Implementation Plan: Task 2.3 - FIFO Matching Logic

Implement the core matching algorithm in the `LimitOrderBook` to execute trades between matching buy and sell orders.

## Objective
Implement a matching loop that compares incoming orders against the top of the opposite book side, generates `Trade` events, and updates order quantities according to FIFO priority.

## Key Files & Context
- `include/chronos/limit_order_book.hpp`: Add matching logic to the `addOrder` or a new `match` method.
- `include/chronos/types.hpp`: Ensure `Order` and `Trade` structs are ready for updates.
- `tests/test_matching.cpp`: New test file to verify matching scenarios.

## Implementation Steps

### 1. Update `include/chronos/limit_order_book.hpp`
- Add a `std::pmr::vector<Trade> match(Order* order)` method (or integrate into `addOrder`).
- Logic for `match`:
    1. Check opposite side (if Buy, check Asks; if Sell, check Bids).
    2. While order has remaining quantity and best price matches (Buy Price >= Ask Price or Sell Price <= Bid Price):
        - Take the oldest order (`front()`) from the best `PriceLevel`.
        - Calculate `match_quantity = min(order.quantity, matching_order.quantity)`.
        - Create a `Trade` record.
        - Subtract `match_quantity` from both orders.
        - If `matching_order` is fully filled, remove it from the book and the `order_lookup_`.
        - If `order` is fully filled, return.
    3. If `order` still has quantity, add it to the book (already handled by `addOrder`).

### 2. Update `tests/test_matching.cpp`
- Test 1: Exact match (Buy $100, Sell $100).
- Test 2: Partial match (Buy 100 @ $100, Sell 50 @ $100).
- Test 3: Multiple level match (Buy 100 @ $110, Sell 50 @ $100, Sell 50 @ $105).
- Test 4: FIFO priority (Buy 50 @ $100 (T1), Buy 50 @ $100 (T2), Sell 50 @ $100 -> matches T1).
- Test 5: No match (Buy $99, Sell $100).

### 3. Update `tests/CMakeLists.txt`
- Add `test_matching.cpp` to the `unit_tests` executable.

## Verification & Testing
1.  Run `cmake --build build`.
2.  Run `cd build && ctest --output-on-failure`.
3.  Ensure all `MatchingTest` pass.
