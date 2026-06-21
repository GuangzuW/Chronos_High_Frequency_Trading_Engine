# Implementation Plan: Phase 3 - Real-time Components

Enhance the dashboard with specialized trading components for high-frequency data visualization.

## Objective
Implement professional-grade UI components for the Order Book, TradingView Price Chart, and Trade Tape (Time & Sales).

## Key Files
- `dashboard/src/components/OrderBook.tsx`: Bid/Ask visualization.
- `dashboard/src/components/PriceChart.tsx`: Lightweight Charts integration.
- `dashboard/src/components/TradeTape.tsx`: Scrolling trade executions.

## Implementation Steps

### 1. Order Book Component
- Create `OrderBook.tsx`.
- Calculate depth percentages for visual bars.
- Use `memo` to prevent unnecessary re-renders of static price levels.

### 2. TradingView Charts Integration
- Create `PriceChart.tsx` using `lightweight-charts`.
- Handle dynamic resizing.
- Create a `useEffect` that listens to `trades` from the store and updates the candle series.

### 3. Trade Tape Component
- Create `TradeTape.tsx`.
- Use CSS animations for "new trade" flash effects.
- Display timestamp, price, and side.

## Verification
- Run the dashboard and bridge.
- Verify that the chart updates when a trade is executed.
- Verify that the order book shows depth bars correctly.
