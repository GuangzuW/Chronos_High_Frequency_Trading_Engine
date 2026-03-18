# Task 7.1: Finnhub WebSocket Client & Symbol Mapping

## Goal
Establish a resilient real-time connection to Finnhub and map external market symbols to internal engine symbols.

## Implementation Steps
1. **Environment Setup**:
   - Add `websockets` and `python-dotenv` to `bridge/requirements.txt`.
   - Update `.gitignore` to exclude `.env`.
   - Create `bridge/.env.example` as a template for API keys.
2. **WebSocket Client**:
   - Implement `connect_to_finnhub()` using `websockets.connect`.
   - Use the `FINNHUB_API_KEY` from environment variables.
   - Implement an auto-reconnect loop with exponential backoff.
3. **Symbol Mapping**:
   - Define a `SYMBOL_MAP` in `feeder.py`.
   - Map `BINANCE:BTCUSDT` -> `BTC` (8-char max).
   - Map `BINANCE:ETHUSDT` -> `ETH`.
   - Map `AAPL` -> `AAPL`.
4. **Subscription Logic**:
   - Send `{"type": "subscribe", "symbol": "..."}` messages for each mapped symbol on connection.

## Verification
- Run `PYTHONPATH=. python bridge/feeder.py` and verify "Subscribed to ..." logs.
- Verify that messages of `type: trade` are received in the `on_message` handler.
