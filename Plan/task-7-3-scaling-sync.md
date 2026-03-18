# Task 7.3: Scaling Synchronization (Engine-Bridge-UI)

## Goal
Ensure consistent interpretation of Price and Quantity across the entire HFT stack.

## Implementation Steps
1. **Engine Layer (Fixed-Point)**:
   - Identify that `chronos::Price` and `chronos::Quantity` are `int64_t` in `include/chronos/types.hpp`.
2. **Feeder/Bridge Layer (Scaling)**:
   - Apply scaling in `bridge/feeder.py`: Price x100, Quantity x1000.
   - Apply identical scaling in `bridge/main.py` (`place_order` endpoint).
3. **UI Layer (Normalizing)**:
   - Update `dashboard/src/store/useTradeStore.ts`.
   - Implement normalization: `trade.price / 100`, `trade.quantity / 1000`.
   - Apply same normalization to `updateOrderBook` to ensure mid-price and levels are correct.
4. **Consistency Audit**:
   - Verify that a `150.25` price in the Feeder results in `15025` in the Engine and back to `150.25` in the UI.

## Verification
- Place a manual order in the Dashboard for `100.50`.
- Verify the Order Book displays `100.50` (not `10050`).
- Verify the Chart shows correctly scaled price candles.
- Confirm the Tape shows correctly scaled trade quantities.
