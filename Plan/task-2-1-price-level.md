# Implementation Plan: Task 2.1 - Price Level Implementation

Implement the `PriceLevel` class, which manages a collection of orders at a specific price point within the Limit Order Book (LOB).

## Objective
Create a `PriceLevel` class that maintains FIFO priority for orders at the same price and allows for efficient (O(1)) addition and removal of orders using `std::pmr` containers and the established `MemoryPool`.

## Key Files & Context
- `include/chronos/price_level.hpp`: New header for the `PriceLevel` class.
- `tests/test_price_level.cpp`: New test file to verify FIFO logic and order management.
- `include/chronos/memory_pool.hpp`: Used to provide memory for the internal list of orders.

## Implementation Steps

### 1. Create `include/chronos/price_level.hpp`
Define the `PriceLevel` class:
- Member variables:
    - `Price price_`: The price this level represents.
    - `std::pmr::list<Order*> orders_`: A list of pointers to `Order` objects, using a PMR allocator.
- Methods:
    - `explicit PriceLevel(Price price, std::pmr::memory_resource* resource)`: Constructor.
    - `void addOrder(Order* order)`: Append an order to the end (FIFO).
    - `void removeOrder(OrderId id)`: Remove an order by ID (initially O(N), but we'll optimize this in Task 2.2 with a lookup map if needed, or stick to O(N) for now as per Task 2.1 scope). *Correction:* Task 2.1 mentions constant-time removal, which usually implies having an iterator or using an intrusive list. For now, I'll use `std::pmr::list` and provide an iterator-based or pointer-based removal if the LOB manages the mapping.
    - `Order* front()`: Get the oldest order at this price.
    - `void popFront()`: Remove the oldest order.
    - `bool empty() const`: Check if no orders remain.
    - `Quantity totalQuantity() const`: Cached total quantity at this price level.

### 2. Create `tests/test_price_level.cpp`
- Verify that orders are returned in the same order they were added (FIFO).
- Verify that `totalQuantity` is updated correctly.
- Verify that removing an order works as expected.
- Verify that the `MemoryPool` resource is correctly used by the `std::pmr::list`.

### 3. Update `tests/CMakeLists.txt`
- Add `test_price_level.cpp` to the `unit_tests` executable.

## Verification & Testing
1.  Run `cmake --build build`.
2.  Run `cd build && ctest --output-on-failure`.
3.  Ensure all `PriceLevelTest` pass.
