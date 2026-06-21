# Implementation Plan: Phase 4 - Control & Integration

Finalize the dashboard by enabling order submission and integrating heartbeat monitoring for the engine.

## Objective
Implement the functional order entry form that talks to the API Bridge, and add real-time health monitoring for the system.

## Key Files
- `dashboard/src/components/OrderEntry.tsx`: New component for order forms.
- `dashboard/src/app/page.tsx`: Final integration.

## Implementation Steps

### 1. Order Entry Logic
- Create `OrderEntry.tsx`.
- Implement `placeOrder` function that sends a `POST` request to `http://localhost:8000/order`.
- Handle form state (Price, Qty).
- Add success/error toast notifications (or simple console logs for now).

### 2. System Heartbeat
- Integrate a heartbeat check into the store.
- If no WebSocket message is received for > 5 seconds, mark the system as "Stale" or "Offline".

### 3. Final Integration
- Replace the placeholder form in `page.tsx` with the `OrderEntry` component.
- Add "Matching Latency" display (mocked or from engine if implemented).

## Verification
- Run Engine, Bridge, and Dashboard.
- Submit an order from the UI.
- Verify the trade appears in the Tape and the Order Book updates.
