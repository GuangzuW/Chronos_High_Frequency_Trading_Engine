# Implementation Plan: Task 5.1 - CPU Pinning & Thread Isolation

Optimize the performance of the Chronos HFT Engine by isolating the matching engine thread and pinning it to a specific CPU core to minimize context switching and cache invalidation.

## Objective
Implement a thread-safe mechanism to pin the critical matching path to a dedicated CPU core. Update the `main.cpp` to run the order ingress and matching in a high-priority, pinned thread.

## Key Files & Context
- `include/chronos/thread_utils.hpp`: New header for thread optimization utilities.
- `src/main.cpp`: Refactor to use a dedicated, pinned thread for matching.
- `Dockerfile`: Update to ensure the container has the necessary permissions for CPU pinning (if applicable).

## Implementation Steps

### 1. Create `include/chronos/thread_utils.hpp`
Define utility functions:
- `bool pinThreadToCore(int core_id)`: Uses `pthread_setaffinity_np` (Linux) or platform-specific equivalent to bind the current thread to a core.
- `void setThreadRealtimePriority()`: Set thread priority to SCHED_FIFO or similar for deterministic execution.

### 2. Update `src/main.cpp`
- Refactor the main loop:
    - Create a `MatchingEngine` class (or keep using `LimitOrderBook` directly in a wrapper).
    - Launch a dedicated thread for the matching loop.
    - Inside the matching thread, call `pinThreadToCore(1)` (or configurable core).
    - Use a lock-free queue or a simple synchronized structure to pass orders from the `ZmqGateway` (on the main thread) to the matching thread. *Correction:* To maintain ultra-low latency, the matching thread should ideally poll the gateway directly if possible, or use a very fast inter-thread communication.

### 3. Update `Dockerfile`
- Ensure the production image is configured for high performance.
- Add notes about `--cpuset-cpus` and `--privileged` flags for Docker runtime.

## Verification & Testing
1.  Verify that the thread affinity is correctly set (using `taskset` or internal logs).
2.  Benchmark latency before and after pinning (if possible in this environment).
