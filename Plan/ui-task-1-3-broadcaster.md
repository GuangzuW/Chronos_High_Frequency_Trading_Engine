# Implementation Plan: Task 1.3 - Real-time Event Broadcaster

Establish a real-time data stream from the C++ engine to the web browser using ZeroMQ and WebSockets.

## Objective
Create a background process that listens for trades and order updates via ZeroMQ PUB/SUB and pushes them to all connected WebSocket clients in JSON format.

## Key Files
- `bridge/main.py`: Update to include WebSocket logic and background ZMQ listener.

## Implementation Steps

### 1. Implement ZMQ Listener Thread
- Use `threading` or `asyncio` to run a loop that subscribes to Port 5556.
- Topics to subscribe to: `"TRADE"` and `"ORDER"`.
- Use the decoders from `bridge/decoder.py` to parse the messages.

### 2. Implement WebSocket Manager
- Create a `ConnectionManager` class to track active WebSocket connections.
- Method to `broadcast(message: dict)` to all clients.

### 3. Integrate into FastAPI
- Add an `@app.websocket("/ws")` endpoint.
- Start the ZMQ background thread on application startup (`@app.on_event("startup")`).

## Verification
- Run the C++ matching engine.
- Use a WebSocket test client (e.g., a browser extension or a Python script) to connect to `ws://localhost:8000/ws`.
- Send an order to the engine and verify the trade/update appears in the WebSocket.
