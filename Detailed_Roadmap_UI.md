# Chronos HFT Engine: UI & Dashboard Roadmap

This document outlines the tasks required to build a professional, real-time trading dashboard for the Chronos HFT Engine.

## Phase 1: The API Bridge (Python/FastAPI)
*Goal: Establish a low-latency gateway between C++ ZeroMQ events and WebSockets.*

*   **Task 1.1: Environment Setup**
    *   Initialize a Python project with `FastAPI`, `uvicorn`, and `pyzmq`.
    *   Define the `pydantic` models for `Order` and `Trade` mirroring the C++ structs.
*   **Task 1.2: Binary Decoder Implementation**
    *   Implement a decoding utility using Python's `struct` module to parse the 64-byte binary messages from Chronos.
    *   Handle `OrderId`, `Price`, and `Quantity` strong-type conversions.
*   **Task 1.3: Real-time Event Broadcaster**
    *   Create a background `ZMQ SUB` thread that polls Chronos (Port 5556).
    *   Implement a `WebSocket` endpoint in FastAPI to broadcast decoded JSON events to all connected clients.
*   **Task 1.4: Order Ingress Proxy**
    *   Implement a `POST /order` endpoint that accepts JSON, packs it into the 64-byte binary format, and sends it to Chronos via `ZMQ DEALER` (Port 5555).

## Phase 2: Frontend Foundation (Next.js)
*Goal: Build a high-performance, reactive UI skeleton.*

*   **Task 2.1: Next.js Initialization**
    *   Setup Next.js 14+ with TypeScript and Tailwind CSS.
    *   Install UI primitives: `shadcn/ui` and `lucide-react` icons.
*   **Task 2.2: Global State Management (Zustand)**
    *   Implement a store to hold the current `OrderBook` state, `TradeHistory`, and `ConnectionStatus`.
    *   Optimize for high-frequency updates (batching state changes if necessary).
*   **Task 2.3: Layout & Theme**
    *   Design a dark-themed "Terminal" layout with a sidebar for order entry and a main area for charts and data.

## Phase 3: Real-time Components
*Goal: Visualize market data with minimal latency.*

*   **Task 3.1: High-Frequency Order Book**
    *   Implement a vertical Bid/Ask list with "depth bars" (visualizing volume at each level).
    *   Ensure the book re-sorts and updates instantly upon receiving WebSocket events.
*   **Task 3.2: Price Charts (TradingView Integration)**
    *   Integrate `lightweight-charts`.
    *   Implement a data feeder that translates `Trade` events into real-time price candles.
*   **Task 3.3: The "Tape" (Time & Sales)**
    *   Create a scrolling, virtualized list of recent trade executions with color-coded Buy/Sell signals.

## Phase 4: Control & Integration
*Goal: Manual control and simulation features.*

*   **Task 4.1: Professional Order Entry Form**
    *   Build a form for Limit and Market orders.
    *   Include "Quick Quantity" buttons and input validation.
*   **Task 4.2: Engine Heartbeat & Monitoring**
    *   Display real-time connection status to the API Bridge.
    *   Show "Matching Latency" metrics broadcasted by the engine.
*   **Task 4.3: Multi-Symbol Support**
    *   Implement a symbol selector to switch between different shards (e.g., AAPL, BTC, ETH).
