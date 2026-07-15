# Chronos HFT Engine: UI & Dashboard Roadmap

This document outlines the tasks required to build a professional, real-time trading dashboard for the Chronos HFT Engine.

## Phase 1: The API Bridge (Python/FastAPI) - COMPLETED
*Goal: Establish a low-latency gateway between C++ ZeroMQ events and WebSockets.*

*   **Task 1.1: Environment Setup** - DONE
    *   Defined pydantic models in `bridge/schemas.py`.
*   **Task 1.2: Binary Decoder Implementation** - DONE
    *   Implemented decoding in `bridge/decoder.py` with `struct`.
*   **Task 1.3: Real-time Event Broadcaster** - DONE
    *   Implemented `zmq_listener` thread in `bridge/main.py` with WebSocket broadcast.
*   **Task 1.4: Order Ingress Proxy** - DONE
    *   Implemented `POST /order` endpoint in `bridge/main.py`.

## Phase 2: Frontend Foundation (Next.js) - COMPLETED
*Goal: Build a high-performance, reactive UI skeleton.*

*   **Task 2.1: Next.js Initialization** - DONE
    *   Initialized project in `dashboard/`.
*   **Task 2.2: Global State Management (Zustand)** - DONE
    *   Implemented `useTradeStore.ts` with LOB and Trade history.
*   **Task 2.3: Layout & Theme** - DONE
    *   Dark "Terminal" layout in `dashboard/src/app/page.tsx`.

## Phase 3: Real-time Components - COMPLETED
*Goal: Visualize market data with minimal latency.*

*   **Task 3.1: High-Frequency Order Book** - DONE
    *   Implemented `OrderBook.tsx` with depth visualizers.
*   **Task 3.2: Price Charts (TradingView Integration)** - DONE
    *   Integrated `lightweight-charts` in `PriceChart.tsx`.
*   **Task 3.3: The "Tape" (Time & Sales)** - DONE
    *   Implemented scrolling `TradeTape.tsx`.

## Phase 4: Control & Integration - COMPLETED
*Goal: Manual control and simulation features.*

*   **Task 4.1: Professional Order Entry Form** - DONE
    *   Implemented `OrderEntry.tsx` with Limit/Market toggle and Quick Qty.
*   **Task 4.2: Engine Heartbeat & Monitoring** - DONE
    *   Added dynamic latency display in the header.
*   **Task 4.3: Multi-Symbol Support** - DONE
    *   Added symbol switcher for AAPL, BTC, ETH in the terminal header.
