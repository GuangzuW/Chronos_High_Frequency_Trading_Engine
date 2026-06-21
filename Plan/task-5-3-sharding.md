# Implementation Plan: Task 5.3 - Symbol Sharding

Scale the Chronos HFT Engine by implementing symbol sharding, allowing multiple order books to run in parallel or be isolated by symbol.

## Objective
Implement a `ShardedMatchingEngine` that routes incoming orders to the correct `LimitOrderBook` based on their symbol. This enables horizontal scaling and reduces contention.

## Key Files & Context
- `include/chronos/sharded_matching_engine.hpp`: New header for the sharded engine.
- `src/main.cpp`: Update to use the sharded engine.
- `tests/test_sharding.cpp`: New test to verify correct routing.

## Implementation Steps

### 1. Create `include/chronos/sharded_matching_engine.hpp`
Define the `ShardedMatchingEngine` class:
- Member variables:
    - `std::pmr::unordered_map<std::string, std::unique_ptr<LimitOrderBook>> shard_map_`: Maps symbol names to order books.
    - `std::pmr::memory_resource* resource_`: PMR resource for allocation.
- Methods:
    - `void addShard(const std::string& symbol)`: Initialize a new order book for a symbol.
    - `std::pmr::vector<Trade> processOrder(Order* order, std::pmr::memory_resource* trade_resource)`:
        - Extract symbol from `order->symbol`.
        - Lookup the corresponding shard.
        - If shard exists, delegate to `Shard->processOrder`.
        - If not, return error/empty trades.

### 2. Update `src/main.cpp`
- Replace single `LimitOrderBook` with `ShardedMatchingEngine`.
- Initialize shards for a few symbols (e.g., "AAPL", "GOOGL").

### 3. Create `tests/test_sharding.cpp`
- Verify that an order for "AAPL" goes to the "AAPL" book and doesn't affect "GOOGL".
- Verify that trades are generated correctly across different shards.

## Verification & Testing
1.  Run `cmake --build build`.
2.  Run `cd build && ctest --output-on-failure`.
3.  Ensure that `ShardingTest` passes.
