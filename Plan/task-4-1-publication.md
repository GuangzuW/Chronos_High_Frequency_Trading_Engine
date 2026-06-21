# Implementation Plan: Task 4.1 - Trade Publication (PUB/SUB)

Implement a ZeroMQ `PUB` socket to broadcast trading events (trades, order updates) asynchronously to other services (persistence, market data feed).

## Objective
Enable decoupled, low-latency distribution of trading events. The matching engine will publish events without waiting for consumers, ensuring that the critical matching path remains fast.

## Key Files & Context
- `include/chronos/event_publisher.hpp`: New header for the `EventPublisher` class.
- `include/chronos/limit_order_book.hpp`: Integrate the publisher into the order book.
- `include/chronos/types.hpp`: Define event types for publication.

## Implementation Steps

### 1. Create `include/chronos/event_publisher.hpp`
Define the `EventPublisher` class:
- Member variables:
    - `zmq::context_t context_`: ZMQ context.
    - `zmq::socket_t socket_`: PUB socket.
- Methods:
    - `explicit EventPublisher(const std::string& endpoint)`: Constructor to bind the PUB socket.
    - `void publishTrade(const Trade& trade)`: Serialize and send a trade event.
    - `void publishOrderUpdate(const Order& order)`: Serialize and send an order status update.

### 2. Update `include/chronos/limit_order_book.hpp`
- Add an `EventPublisher*` member to `LimitOrderBook`.
- In `processOrder`, after matching is complete and `trades` are generated:
    - Loop through `trades` and call `publisher->publishTrade(trade)`.
    - Publish an update for the incoming order (if it's added or filled).
    - Publish updates for matching orders that were filled or partially filled.

### 3. Create `tests/test_publication.cpp`
- Integration test: Mock a SUB client that listens for trade events.
- Verify that when an order is matched in the `LimitOrderBook`, the corresponding `Trade` is correctly published and received by the SUB client.

## Verification & Testing
1.  Run `cmake --build build`.
2.  Run `cd build && ctest --output-on-failure`.
3.  Ensure that `PublicationTest` passes.
