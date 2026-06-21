# Implementation Plan: Task 3.1 - ZeroMQ Order Ingress

Implement a `ZmqGateway` that handles external connectivity via ZeroMQ to receive incoming order requests.

## Objective
Establish a high-performance order ingress gateway using ZeroMQ's `ROUTER/DEALER` pattern. The gateway will listen for binary-formatted order messages and pass them to the matching engine.

## Key Files & Context
- `include/chronos/zmq_gateway.hpp`: New header for the `ZmqGateway` class.
- `src/gateway/zmq_gateway.cpp`: Implementation of the gateway logic.
- `include/chronos/types.hpp`: Ensure `Order` struct can be easily serialized/deserialized.
- `src/main.cpp`: Integrate the gateway into the main engine loop.

## Implementation Steps

### 1. Create `include/chronos/zmq_gateway.hpp`
Define the `ZmqGateway` class:
- Member variables:
    - `zmq::context_t context_`: ZMQ context.
    - `zmq::socket_t socket_`: ROUTER socket for asynchronous multi-client handling.
- Methods:
    - `explicit ZmqGateway(const std::string& endpoint)`: Constructor to bind the socket.
    - `std::optional<Order> receiveOrder()`: Non-blocking or timed-wait receive that parses binary messages into `Order` structs.
    - `void sendResponse(const OrderResponse& response)`: Send confirmation back to the client.

### 2. Implement `src/gateway/zmq_gateway.cpp`
- Use `libzmq` and the `cppzmq` header-only wrapper (if available, otherwise raw `zmq.h`).
- Implement robust binary parsing: Ensure that incoming byte streams are correctly mapped to the `Order` struct, respecting alignment and size (64 bytes).
- Handle ZMQ message envelopes (ROUTER/DEALER identity) to ensure responses reach the correct client.

### 3. Update `src/main.cpp`
- Initialize the `ZmqGateway` on a specific port (e.g., `tcp://*:5555`).
- Update the main loop to check for new orders from the gateway before processing them in the `LimitOrderBook`.

### 4. Create `tests/test_gateway.cpp`
- Integration test: Mock a ZMQ client (DEALER) that sends a binary `Order` message.
- Verify that the `ZmqGateway` correctly receives and parses the order.

## Verification & Testing
1.  Run `cmake --build build`.
2.  Run `cd build && ctest --output-on-failure` (mocking ZMQ messages).
3.  Manually verify with a small Python/C++ script if needed.
