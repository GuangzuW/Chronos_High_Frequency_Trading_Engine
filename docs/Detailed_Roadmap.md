# Chronos HFT Engine: Detailed Technical Roadmap

This document provides a granular, task-oriented roadmap for the development of the Chronos High-Frequency Trading Engine. Each task is designed to be a discrete unit of work suitable for Git commits.

## Phase 1: Foundation (Core Data Structures & Memory)
**Objective:** Establish zero-allocation memory management and cache-efficient data structures.

*   **Task 1.1: Define Core Logic Structs**
    *   Implement `Order` struct with fields: `id`, `symbol`, `price`, `quantity`, `side` (Buy/Sell), `timestamp`.
    *   Implement `Trade` struct with fields: `buy_order_id`, `sell_order_id`, `price`, `quantity`, `timestamp`.
    *   Use `std::byte` padding and alignment to ensure structs fit within a 64-byte cache line.
    * I have completed Task 1.1: Define Core Logic Structs.
    * Changes:
      * - Created include/chronos/types.hpp with the following:
      * - Order and Trade structs aligned to 64-byte cache lines.
      * - Explicit std::byte padding to ensure exactly 64-byte size for both structs.
      * - Type-safe OrderSide and OrderStatus enums.
      * - Fixed-point representation for Price and Quantity using int64_t.
    * Created tests/test_types.cpp to verify:
     * - sizeof(Order) == 64 and alignof(Order) == 64.
     * - sizeof(Trade) == 64 and alignof(Trade) == 64.
     * - Proper initialization of all fields.
   * Updated CMakeLists.txt and tests/CMakeLists.txt to include the new header directory and test file.
   * Verification:
   * Ran ctest and all tests passed, confirming the structural integrity and performance alignment of the core types.


   * 1 Test project /Users/gz/Projects/Chronos_HFT_Engine/build
   * 2     Start 1: CoreLogicTest
   * 3 1/2 Test #1: CoreLogicTest ....................   Passed    0.18 sec
   * 4     Start 2: CoreTypesTest
   * 5 2/2 Test #2: CoreTypesTest ....................   Passed    0.00 sec
   * 100% tests passed, 0 tests failed out of 2*
*   **Task 1.2: Implement `std::pmr` Memory Pool Manager**
    *   Create a `MemoryPool` wrapper using `std::pmr::monotonic_buffer_resource`.
    *   Pre-allocate a large memory block (e.g., 100MB) at startup to avoid `malloc` on the hot path.
*   **Task 1.3: Define Type-Safe Identifiers**
    *   Use `enum class` for `OrderSide` and `OrderStatus`.
    *   Implement basic `FixedPoint` or `int64_t` price representation to avoid floating-point inaccuracies.
*   **Verification:**
    *   Unit test: Verify that `sizeof(Order)` is a multiple of 64 or optimized for cache.
    *   Unit test: Verify no allocations occur during `Order` creation from the memory pool.

## Phase 2: The Matching Engine (Limit Order Book)
**Objective:** Build a single-threaded, high-performance LOB with FIFO matching.

*   **Task 2.1: Price Level Implementation**
    *   Create a `PriceLevel` class that stores a queue of `Order` objects at a specific price.
    *   Use `std::list` or a custom intrusive doubly-linked list for constant-time order removal.
*   **Task 2.2: Limit Order Book (LOB) Logic**
    *   Implement `addOrder`, `cancelOrder`, and `match` functions.
    *   Maintain two `std::map` (or `std::unordered_map` for speed) for Buy and Sell sides, sorted by price.
*   **Task 2.3: FIFO Matching Logic**
    *   Implement the core matching loop: compare top of Buy book with top of Sell book.
    *   Generate `Trade` events and update remaining quantities.
*   **Verification:**
    *   Unit test: Add a Buy order at $100 and a Sell order at $100 and verify a trade is generated.
    *   Unit test: Verify price-time priority (older orders at the same price match first).

## Phase 3: Gateway & Risk Engine (AI Integration)
**Objective:** Handle external connectivity and pre-trade AI validation.

*   **Task 3.1: ZeroMQ Order Ingress**
    *   Implement a `ZmqGateway` using `libzmq`.
    *   Set up a `ROUTER/DEALER` pattern to receive incoming order requests in binary format.
*   **Task 3.2: ONNX Runtime Integration**
    *   Add ONNX Runtime C++ dependency.
    *   Implement `RiskEngine::validateOrder(Order)` which runs an ONNX model inference.
*   **Task 3.3: Static Risk Checks**
    *   Implement hard-coded checks (e.g., Max Order Value, Max Position Size).
*   **Verification:**
    *   Integration test: Send a mock ZMQ message and verify it is parsed into an `Order` struct.
    *   Mock test: Verify an order is rejected if the `RiskEngine` returns a fraud score above the threshold.

## Phase 4: Persistence & Audit (Asynchronous Logging)
**Objective:** Decouple disk I/O from the critical matching path.

*   **Task 4.1: Trade Publication (PUB/SUB)**
    *   Implement a ZMQ `PUB` socket in the `MatchingEngine`.
    *   Publish `Trade` and `OrderUpdate` events immediately after matching.
*   **Task 4.2: Audit Logger Service**
    *   Create a separate process/thread that subscribes to the trade feed.
    *   Write logs to a binary file or a high-performance database (QuestDB).
*   **Verification:**
    *   Benchmark: Measure the latency impact of ZMQ publication on the matching loop.
    *   Audit: Verify that all matched trades are correctly logged to disk.

## Phase 5: Optimization & Deployment
**Objective:** Fine-tune performance and prepare for production.

*   **Task 5.1: CPU Pinning & Thread Isolation**
    *   Update `Dockerfile` or startup scripts to pin the `MatchingEngine` thread to a specific core using `pthread_setaffinity_np`.
*   **Task 5.2: Performance Profiling**
    *   Use `google-perftools` or `perf` to identify bottlenecks in the matching loop.
    *   Minimize branch mispredictions and cache misses.
*   **Task 5.3: Symbol Sharding**
    *   Implement logic to route orders for different symbols (e.g., BTC, ETH) to different `MatchingEngine` instances.
