# libs/ — Shared Libraries

- `client-core/` — **`chronos-client-core`**, the shared C++20 library (wire codec, L2 order-book
  aggregation, fixed-point math, resilient WebSocket transport, cache + request signing). Built once and
  bound to each client platform; exposed to React Native via JSI. See `Plan/Platform/phase-4-client-core.md`.
- `service-template/` — the golden-path microservice template all backend services are cloned from
  (Task 0.7).

Both consume generated bindings from `contracts/`. _Scaffold only._
