# Phase 2 — Market Data Pipeline

## Goal
Turn the existing `bridge/feeder.py` Finnhub prototype into a production **Market Data service**:
multi-source ingest, normalization, persistence of ticks/OHLC, and low-latency fan-out to clients.

## Tasks

### 2.1 Ingest & normalization
- Generalize `feeder.py` into a provider-abstracted ingester (Finnhub today; interface for others).
- Normalize all feeds into the canonical `contracts/` market-data messages (trade, quote/L1, L2 delta).
- Resilient WebSocket clients with reconnect/backoff (the feeder already has the seed of this).
- **Verification:** live Finnhub trades arrive normalized; provider outage triggers clean reconnect.

### 2.2 Time-series persistence
- Write ticks + derived OHLC bars (1s/1m/1d) to ClickHouse/TimescaleDB.
- Backfill/historical query API for charts.
- **Verification:** query OHLC for a symbol/timeframe; bar aggregation matches raw ticks.

### 2.3 Real-time fan-out
- Publish normalized data to Kafka/Redpanda topics; the BFF subscribes and pushes to clients over
  WebSocket with **per-client subscription management** and backpressure.
- L2 book deltas published so the client C++ core (Phase 4) can maintain local books.
- **Verification:** a subscribed client receives quote/trade/L2 updates at p99 within budget; an
  unsubscribed symbol sends nothing.

### 2.4 Options market data
- Options quotes + computed/served **implied volatility** and chain snapshots (coordinates with Phase 6
  Pricing).
- **Verification:** a chain snapshot streams bid/ask/IV per contract.

### 2.5 Decouple from the engine's synthetic feed
- Today `feeder.py` synthesizes buy/sell pairs into Chronos to *drive* the engine. Separate concerns:
  Market Data is for **display/analytics**; driving the venue with synthetic liquidity becomes a
  dedicated **simulator** profile used only in paper-trading/sim environments.
- **Verification:** market-data display works with the venue idle; the simulator can be toggled on/off
  independently.

## Exit criteria
Clients can display real-time and historical equity (and option) data sourced from a normalized,
persisted, fanned-out pipeline — independent of order execution.
