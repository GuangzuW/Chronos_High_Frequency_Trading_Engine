# Implementation Plan: Task 2.2 - Limit Order Book (LOB) Logic

Implement the `LimitOrderBook` class to manage the overall buy and sell sides of the order book for a single symbol.

## Objective
Create a `LimitOrderBook` that maintains sorted price levels (Bids and Asks) and provides efficient order entry and cancellation. It must support $O(1)$ lookup for order cancellation and $O(\log N)$ (or better) for finding price levels.

## Key Files & Context
- `include/chronos/limit_order_book.hpp`: New header for the `LimitOrderBook` class.
- `tests/test_lob.cpp`: New test file to verify order book management.
- `include/chronos/price_level.hpp`: Used to manage individual price points.
- `include/chronos/memory_pool.hpp`: Used to allocate `PriceLevel` objects and internal containers.

## Implementation Steps

### 1. Create `include/chronos/limit_order_book.hpp`
Define the `LimitOrderBook` class:
- Member variables:
    - `std::pmr::map<Price, PriceLevel, std::greater<Price>> bids_`: Sorted high-to-low.
    - `std::pmr::map<Price, PriceLevel, std::less<Price>> asks_`: Sorted low-to-high.
    - `std::pmr::unordered_map<OrderId, PriceLevel::OrderListIterator> order_map_`: Fast lookup for order cancellation.
    - `MemoryPool* pool_`: Reference to the memory pool for allocating orders and internal nodes.
- Methods:
    - `void addOrder(Order* order)`: Add a new limit order to the appropriate side.
    - `void cancelOrder(OrderId id)`: Remove an existing order in $O(1)$ time.
    - `const PriceLevel* getBestBid() const`: Return the top of the bid book.
    - `const PriceLevel* getBestAsk() const`: Return the top of the ask book.
    - `void removeLevelIfEmpty(Price price, OrderSide side)`: Clean up maps when a level is exhausted.

### 2. Update `include/chronos/price_level.hpp`
- Ensure `addOrder` returns an iterator (already implemented).
- Ensure `removeOrder` accepts an iterator (already implemented).

### 3. Create `tests/test_lob.cpp`
- Verify that Buy orders are sorted correctly (highest price first).
- Verify that Sell orders are sorted correctly (lowest price first).
- Verify that `cancelOrder` removes the order correctly in $O(1)$ (using the internal map).
- Verify that `getBestBid`/`getBestAsk` always point to the top of the book.
- Verify that empty price levels are cleaned up properly.

### 4. Update `tests/CMakeLists.txt`
- Add `test_lob.cpp` to the `unit_tests` executable.

## Verification & Testing
1.  Run `cmake --build build`.
2.  Run `cd build && ctest --output-on-failure`.
3.  Ensure all `LOBTest` pass.
