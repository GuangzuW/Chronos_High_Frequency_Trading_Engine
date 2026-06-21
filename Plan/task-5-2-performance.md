# Implementation Plan: Task 5.2 - Performance Profiling & Optimization

Optimize the matching engine's hot path by providing performance hints to the compiler and establishing a micro-benchmarking framework.

## Objective
Identify and minimize micro-bottlenecks in the matching loop. Use C++20 features like `[[likely]]`/`[[unlikely]]` to guide branch prediction and implement a latency measurement utility.

## Key Files & Context
- `include/chronos/limit_order_book.hpp`: Add branch prediction hints.
- `include/chronos/latency_utils.hpp`: New utility for nanosecond-precision measurement.
- `tests/benchmark_matching.cpp`: New micro-benchmark to measure matching performance.

## Implementation Steps

### 1. Create `include/chronos/latency_utils.hpp`
Define a simple RAII-based `LatencyLogger`:
- Uses `std::chrono::high_resolution_clock`.
- Measures nanoseconds between construction and destruction.
- Optional: Store results in a histogram or just print to console for now.

### 2. Update `include/chronos/limit_order_book.hpp`
- Add `[[likely]]` to cases where an order matches (hot path).
- Add `[[unlikely]]` to error conditions or rare paths (e.g., empty book).
- Ensure loop conditions are optimized for cache locality.

### 3. Create `tests/benchmark_matching.cpp`
- Implement a test that processes 1,000,000 orders against a pre-filled book.
- Measure and report the average latency per order.
- This will serve as a baseline for future optimizations.

### 4. Update `tests/CMakeLists.txt`
- Add `benchmark_matching.cpp` as a separate target or part of `unit_tests`.

## Verification & Testing
1.  Run the benchmark: `cd build && ./unit_tests --gtest_filter=Benchmark*`.
2.  Analyze the reported latency.
