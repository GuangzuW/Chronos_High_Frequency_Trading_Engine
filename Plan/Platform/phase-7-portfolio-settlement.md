# Phase 7 — Portfolio, Settlement & Notifications

## Goal
Round out the post-trade and engagement surface: rich portfolio/analytics, settlement & corporate
actions, statements/tax docs, and a notification/alerts system.

## Tasks

### 7.1 Portfolio & analytics
- Tax-lot accounting (FIFO/specific-lot), realized/unrealized P&L, cost basis, returns, exposure and
  net Greeks across positions.
- Historical performance projection from ledger + fills.
- **Verification:** tax-lot disposal matches expected cost basis; portfolio value reconciles with
  ledger + marks.

### 7.2 Settlement & clearing
- Settlement service: T+1 cash/position settlement state machine; corporate-action processing
  (splits, dividends, symbol changes) updating positions and ledger.
- **Verification:** a simulated split adjusts position quantity and cost basis; a dividend posts cash.

### 7.3 Statements & documents
- Generated account statements, trade confirmations, and tax documents stored in the object store;
  client download via signed URLs.
- **Verification:** a monthly statement reconciles with ledger activity for the period.

### 7.4 Notification service
- Push (FCM/APNs), email, in-app; user-configurable **price alerts**, **fill/order alerts**, margin
  calls, corporate-action notices. Driven by Kafka domain events.
- Per-platform push wiring through the RN clients.
- **Verification:** a price-cross alert and a fill event each deliver a push to a real device sandbox.

### 7.5 Client polish
- Notifications center, alerts management, statements screen, portfolio analytics views on all platforms.
- **Verification:** alerts can be created/edited and fire; statements list and open.

## Exit criteria
Post-trade lifecycle is complete and auditable; users receive timely notifications and can retrieve
accurate statements and portfolio analytics.
