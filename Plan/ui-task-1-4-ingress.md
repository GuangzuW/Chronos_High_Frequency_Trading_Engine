# Implementation Plan: Task 1.4 - Order Ingress Proxy

Allow the web frontend to submit orders to the C++ matching engine through a standard REST API.

## Objective
Implement a FastAPI endpoint that translates incoming JSON order requests into the 64-byte binary format required by the C++ engine and forwards them via ZeroMQ.

## Key Files
- `bridge/main.py`: Add the POST endpoint and ZMQ DEALER logic.

## Implementation Steps

### 1. Initialize ZMQ Ingress Socket
- In `bridge/main.py`, create a global `zmq.Context` and a `zmq.DEALER` socket.
- Connect the socket to `tcp://localhost:5555`.

### 2. Implement `POST /order`
- Use the `OrderRequest` schema for the request body.
- Generate a unique `OrderId` (for simulation purposes, maybe a simple counter or UUID).
- Convert `OrderRequest` to a full `Order` object.
- Use `encode_order()` from `bridge/decoder.py` to get the binary buffer.
- Send the buffer via the `DEALER` socket.

### 3. Return Confirmation
- Return the generated `OrderId` to the frontend so it can track its own order.

## Verification
- Run the C++ engine.
- Use `curl` or Postman to send a JSON POST request to `http://localhost:8000/order`.
- Verify the C++ engine terminal shows "Executed trades" or "Order added".
