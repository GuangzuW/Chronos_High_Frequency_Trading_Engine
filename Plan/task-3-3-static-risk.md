# Implementation Plan: Task 3.3 - Static Risk Checks

Implement static, hard-coded risk checks to ensure compliance with trading rules and prevent catastrophic errors.

## Objective
Add a set of pre-defined risk rules to the `RiskEngine` that run alongside the AI-based scoring. These checks should be fast and deterministic.

## Key Files & Context
- `include/chronos/risk_engine.hpp`: Add static risk check logic.
- `tests/test_risk.cpp`: Update tests to cover static risk rules.

## Implementation Steps

### 1. Update `include/chronos/risk_engine.hpp`
Add a `RiskConfig` struct and the following methods to `RiskEngine`:
- `struct RiskConfig`:
    - `int64_t max_order_quantity`
    - `int64_t max_order_value`
- `bool checkStaticRules(const Order& order)`:
    - Rule 1: Check if `order.quantity` exceeds `max_order_quantity`.
    - Rule 2: Check if `order.price * order.quantity` exceeds `max_order_value`.
    - Rule 3: Check for invalid prices (e.g., <= 0).
- Update `validateOrder` to call `checkStaticRules` first. If any static rule fails, it should return an "automatic rejection" score (e.g., 1.0).

### 2. Update `tests/test_risk.cpp`
- Test 1: Verify that an order with excessive quantity is flagged.
- Test 2: Verify that an order with excessive value is flagged.
- Test 3: Verify that an order with invalid price is flagged.
- Test 4: Verify that normal orders pass the static checks.

## Verification & Testing
1.  Run `cmake --build build`.
2.  Run `cd build && ctest --output-on-failure`.
3.  Ensure that all `RiskEngineTest` pass.
