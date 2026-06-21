# Implementation Plan: Architecture Update & UI Roadmap

Expand the project's documentation to include the UI ecosystem, establishing a clear path for building a professional trading dashboard.

## Objective
1.  Update `Architecture.md` to include the API Bridge and Frontend components.
2.  Create `Detailed_Roadmap_UI.md` with granular tasks for the UI implementation.

## Key Files & Context
- `Architecture.md`: Update existing architecture documentation.
- `Detailed_Roadmap_UI.md`: New file for the UI-specific roadmap.

## Implementation Steps

### 1. Update `Architecture.md`
- Add a new section **"E. UI Ecosystem"**.
- Describe the **API Bridge (FastAPI)**:
    - Translation of 64-byte C++ binary structs to JSON.
    - WebSocket broadcasting for real-time market data.
    - REST API for order submission.
- Describe the **Frontend Dashboard (Next.js)**:
    - Tech: React, Tailwind CSS, Zustand, TradingView Lightweight Charts.
    - Features: Real-time order book, Time & Sales, order entry.

### 2. Create `Detailed_Roadmap_UI.md`
Break down the UI development into 4 phases:
- **Phase 1: The Bridge (Backend Integration)**
    - Task 1.1: Setup FastAPI & ZeroMQ context.
    - Task 1.2: Implement binary decoding for `Order` and `Trade` structs.
    - Task 1.3: Create WebSocket broadcasting for incoming trades.
- **Phase 2: Frontend Foundation**
    - Task 2.1: Initialize Next.js with TypeScript & Tailwind.
    - Task 2.2: Implement global state with Zustand.
    - Task 2.3: Build basic layout (Dark terminal theme).
- **Phase 3: Real-time Visualization**
    - Task 3.1: Build the Order Book component (with depth bars).
    - Task 3.2: Integrate TradingView Lightweight Charts.
    - Task 3.3: Implement the Time & Sales (Tape) scrolling list.
- **Phase 4: Interaction & Control**
    - Task 4.1: Implement Order Entry form (Limit/Market).
    - Task 4.2: Connect form to REST API for order submission.
    - Task 4.3: Add connection status indicator (Engine heartbeat).

## Verification & Testing
- Review the updated `Architecture.md` for clarity and consistency.
- Ensure the roadmap tasks are actionable and logically sequenced.
