# Chronos HFT Engine: Implementation Roadmap

This roadmap outlines the phased development of the Chronos High-Frequency Trading Engine, focusing on ultra-low latency, zero-allocation memory management, and AI-driven risk validation.

## Phase 1: Core Data Structures & Memory Management
*   **Goal:** Define the fundamental building blocks of the order book and ensure zero-allocation performance on the hot path.
*   **Tasks:**
    *   Implement `Order` and `Trade` structs with `std::byte` alignment for cache efficiency.
    *   Set up `std::pmr` (Polymorphic Memory Resource) pools for high-frequency object allocation.
    *   Create `OrderSide` (Buy/Sell) and `PriceLevel` abstractions.
*   **Verification:** Unit tests for memory pool exhaustion and cache-line alignment checks.

## Phase 2: The Matching Engine (Core LOB)
*   **Goal:** Build a single-threaded, lock-free Limit Order Book (LOB).
*   **Tasks:**
    *   Implement a `LimitOrderBook` class using `std::map` or a custom skip-list for price levels (initially) to establish logic.
    *   Refactor to a lock-free structure using atomic operations for order insertion/cancellation.
    *   Implement FIFO (First-In-First-Out) matching logic.
*   **Verification:** Performance benchmarks (latency measurements in nanoseconds) for order matching.

## Phase 3: Gateway & Risk Engine (The AI Guard)
*   **Goal:** Enable external connectivity and pre-trade AI validation.
*   **Tasks:**
    *   **Gateway:** Implement a ZeroMQ (ZMQ) REP/ROUTER socket to receive incoming order requests.
    *   **Risk Engine:** Integrate the ONNX Runtime C++ API to run a pre-trained fraud detection model.
    *   **Pipeline:** Connect Gateway -> Risk Engine -> Matching Engine.
*   **Verification:** End-to-end integration tests using a mock client to send orders and verify AI filtering.

## Phase 4: Persistence & Audit (The Ostrich)
*   **Goal:** Asynchronously log trades without slowing down the matching engine.
*   **Tasks:**
    *   Implement a ZMQ PUB/SUB pattern where the Matching Engine publishes trade events.
    *   Create a dedicated Persistence Service that subscribes and writes to a low-latency database (e.g., QuestDB or KDB+).
*   **Verification:** Audit trail consistency checks between the matching engine's internal state and the persistence layer.

## Phase 5: Deployment & Optimization
*   **Goal:** Achieve maximum performance in a production-like environment.
*   **Tasks:**
    *   Implement CPU Pinning in the Docker configuration.
    *   Conduct jitter analysis and profile with `perf` or `Valgrind`.
    *   Set up Symbol Sharding logic in the Gateway for horizontal scaling.
