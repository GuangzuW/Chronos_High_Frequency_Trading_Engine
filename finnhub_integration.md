# Finnhub Integration Architecture & Roadmap

## 1. Architectural Design

To integrate real-time market data from Finnhub without altering the core deterministic nature of the C++ Chronos Matching Engine, we will implement a **Market Data Feeder** pattern.

### The Flow:
1. **Finnhub WebSocket:** Provides real-time trade execution data (Price, Volume, Symbol, Timestamp) for configured assets.
2. **Data Feeder (`bridge/feeder.py`):** A new asynchronous Python service that connects to the Finnhub WebSocket.
3. **Order Synthesis (The "Market Maker"):** For every real-world trade received from Finnhub, the Feeder synthesizes **two** opposing Limit Orders:
   - A `BUY` order at the exact trade price and volume.
   - A `SELL` order at the exact trade price and volume.
4. **ZMQ Ingress:** The Feeder packs these synthesized orders into the 64-byte binary format and injects them into the Chronos C++ Engine via the existing `ZMQ DEALER` socket (Port 5555).
5. **Chronos Engine:** Receives the matching orders, immediately executes a match, and publishes a `TRADE` event on `ZMQ PUB` (Port 5556).
6. **Dashboard:** The existing UI receives the trade, updating the Order Book, Tape, and Charts seamlessly.

**Benefit:** This architecture tests the entire HFT pipeline (Ingress -> Risk -> Matching -> Egress) under real-world load conditions without requiring bypasses or mock endpoints in the C++ core.

---

## 2. Implementation Roadmap

### Task 1: Environment & Dependency Setup
*   **Action:** Update `bridge/requirements.txt` to include `websockets` (for the Finnhub client) and `python-dotenv` (for API key management).
*   **Action:** Create a `.env` file template to store the `FINNHUB_API_KEY`.
*   **Action:** Define a symbol mapping configuration (e.g., UI `BTC` -> Finnhub `BINANCE:BTCUSDT`).

### Task 2: Feeder Script Implementation (`bridge/feeder.py`)
*   **Action:** Create an `asyncio` WebSocket client that connects to `wss://ws.finnhub.io?token={KEY}`.
*   **Action:** Implement subscription logic for the target symbols on startup.
*   **Action:** Implement the `on_message` handler to parse incoming JSON trade events (`type: "trade"`).
*   **Action:** Utilize the existing `bridge.decoder.encode_order` to convert the JSON data into paired binary C++ `Order` structs.

### Task 3: ZMQ Integration in the Feeder
*   **Action:** Initialize a `ZMQ DEALER` socket within `feeder.py` connected to `tcp://localhost:5555`.
*   **Action:** Implement a rapid-fire send loop that pushes the paired Buy/Sell orders into the engine with consecutive Order IDs.
*   **Action:** Add rate-limiting or batching (if necessary) to prevent overwhelming the local ZMQ buffers during extreme market volatility.

### Task 4: Ecosystem Integration & UI Mapping
*   **Action:** Update `bridge/main.py` or the startup instructions to run the `feeder.py` alongside the bridge.
*   **Action:** Ensure the UI components gracefully handle the high frequency of incoming trades without browser lag (the Zustand store is already optimized, but we will verify under load).

---

## 3. Execution Plan
Once this plan is approved, I will sequentially execute Tasks 1 through 4, directly modifying the Python bridge components and ensuring the system remains stable.