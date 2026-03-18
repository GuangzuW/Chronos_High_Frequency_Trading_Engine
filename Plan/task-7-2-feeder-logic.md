# Task 7.2: Market Data Feeder Logic & ZMQ Injection

## Goal
Transform real-world market trades into internal engine execution events.

## Implementation Steps
1. **Order Synthesis Logic**:
   - Implement `synthesize_and_send_orders(trade_data)`.
   - Create a **BUY** order at the market trade price (`p`).
   - Create a **SELL** order at the same price (`p`) with the same quantity (`v`).
   - Assign consecutive `OrderId` values starting from a high range (e.g., 500,000+).
2. **Binary Packing**:
   - Utilize `bridge.decoder.encode_order` to serialize the synthetic orders into the 64-byte C++ binary format.
3. **ZMQ Dealer Injection**:
   - Initialize a `ZMQ DEALER` socket (`ingress_socket`) in `feeder.py`.
   - Connect the dealer to `tcp://localhost:5555`.
   - Send both synthetic orders in rapid succession to force a match in the engine.
4. **Main Bridge Integration**:
   - Update `bridge/main.py` to check for `START_FEEDER == "1"`.
   - Use `subprocess.Popen` in the FastAPI `startup_event` to launch `feeder.py`.

## Verification
- Run the engine and the bridge/feeder.
- Verify `[Bridge] Starting Market Data Feeder subprocess...` log in terminal.
- Confirm trades appear in the Engine's logs.
