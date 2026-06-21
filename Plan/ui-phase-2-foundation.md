# Implementation Plan: Phase 2 - Frontend Foundation

Build the reactive UI core for the Chronos Dashboard, focusing on state management and professional dark-themed layout.

## Objective
Establish the frontend project structure, implement a high-frequency state store with Zustand, and design a dark "Trading Terminal" layout.

## Key Files
- `dashboard/src/store/useTradeStore.ts`: Zustand store for market data.
- `dashboard/src/app/layout.tsx`: Global layout with dark theme.
- `dashboard/src/app/page.tsx`: Main dashboard entry point.

## Implementation Steps

### 1. Global State Management (`useTradeStore.ts`)
- Define `OrderBookLevel` and `Trade` interfaces.
- Create a Zustand store:
    - `bids`: Array of price/quantity levels.
    - `asks`: Array of price/quantity levels.
    - `trades`: Array of recent executions.
    - Actions to update the book and add new trades.

### 2. Dashboard Layout
- Update `tailwind.config.ts` with custom colors (dark terminal theme).
- Create a base `layout.tsx` with a dark background.
- Build a responsive grid in `page.tsx`:
    - Sidebar: Order Entry.
    - Center Top: Price Chart.
    - Center Bottom: Trade Tape.
    - Right: Order Book.

### 3. Connection Hook
- Create a `useZmqSocket` hook (or integrated into the store) to connect to the FastAPI Bridge's WebSocket (`ws://localhost:8000/ws`).
- Route incoming messages to the Zustand actions.

## Verification
- Run `npm run dev` in the `dashboard` directory.
- Verify that the page renders correctly in the browser.
- Use a mock WebSocket sender to verify that the Zustand state updates.
