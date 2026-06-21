# Implementation Plan: Task 4.2 - Audit Logger Service

Implement an asynchronous audit logger that subscribes to the matching engine's event feed and persists all trades and order updates to disk.

## Objective
Provide a reliable, non-blocking audit trail for all trading activity. The logger will run independently of the matching engine to ensure that disk I/O does not impact trading latency.

## Key Files & Context
- `include/chronos/audit_logger.hpp`: New header for the `AuditLogger` class.
- `src/persistence/audit_logger.cpp`: Implementation of the logging logic.
- `tests/test_audit.cpp`: New test file to verify persistence.

## Implementation Steps

### 1. Create `include/chronos/audit_logger.hpp`
Define the `AuditLogger` class:
- Member variables:
    - `std::thread logger_thread_`: Background thread for processing.
    - `std::atomic<bool> running_`: Control flag.
    - `std::string filename_`: Path to the audit log file.
    - `std::string pub_endpoint_`: ZMQ endpoint to subscribe to.
- Methods:
    - `explicit AuditLogger(const std::string& pub_endpoint, const std::string& filename)`: Constructor.
    - `void start()`: Launch the background thread.
    - `void stop()`: Signal the thread to exit and join.
    - `void run()`: Internal loop that receives ZMQ messages and writes to file.

### 2. Implement `run()` loop
- Create a ZMQ SUB socket and connect to `pub_endpoint`.
- Subscribe to all topics ("").
- Open `filename` in binary append mode.
- In a loop:
    - Receive topic and payload.
    - Write a timestamp, topic name, and the raw binary data to the file.
    - Periodically flush the file or use unbuffered I/O for safety.

### 3. Create `tests/test_audit.cpp`
- Integration test: 
    1. Start `EventPublisher` and `AuditLogger`.
    2. Publish a few trades and order updates.
    3. Stop the logger.
    4. Read the audit log file and verify that the data matches what was published.

## Verification & Testing
1.  Run `cmake --build build`.
2.  Run `cd build && ctest --output-on-failure`.
3.  Ensure that `AuditLoggerTest` passes.
