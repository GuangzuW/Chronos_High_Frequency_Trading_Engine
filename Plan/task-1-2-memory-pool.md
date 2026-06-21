# Implementation Plan: Task 1.2 - Implement `std::pmr` Memory Pool Manager

Establish a zero-allocation memory management system for the matching engine's hot path using C++20 `std::pmr`.

## Objective
Create a `MemoryPool` class that wraps `std::pmr::monotonic_buffer_resource` to provide fast, pre-allocated memory for core structures like `Order` and `Trade`.

## Key Files & Context
- `include/chronos/memory_pool.hpp`: New header for the memory pool manager.
- `src/common/memory_pool.cpp`: Implementation of the memory pool (if needed, or header-only).
- `tests/test_memory_pool.cpp`: New test file to verify zero-allocation behavior and pool functionality.
- `include/chronos/types.hpp`: May need slight updates to support PMR if we use containers.

## Implementation Steps

### 1. Create `include/chronos/memory_pool.hpp`
Define a `MemoryPool` class:
- Constructor that takes a size (default 100MB).
- Uses `std::pmr::monotonic_buffer_resource` as the underlying resource.
- Provides an `allocate<T>()` method (or similar) that uses the resource.
- Provides a way to get the `std::pmr::memory_resource*` for use with PMR-compatible containers (like `std::pmr::vector` or `std::pmr::list`).

### 2. Create `tests/test_memory_pool.cpp`
- Verify that `MemoryPool` can be initialized with a specific size.
- Verify that objects can be allocated from the pool.
- Verify (using a custom upstream resource or `std::pmr::set_default_resource`) that no global `new`/`malloc` calls occur during steady-state allocation after initial pre-allocation.
- Test allocation of `Order` and `Trade` structs.

### 3. Update `tests/CMakeLists.txt`
- Add `test_memory_pool.cpp` to the `unit_tests` executable.

## Verification & Testing
1.  Run `cmake --build build`.
2.  Run `cd build && ctest --output-on-failure`.
3.  Check that all tests in `MemoryPoolTest` pass.
