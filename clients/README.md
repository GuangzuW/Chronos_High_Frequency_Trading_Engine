# clients/ — Applications

- `app/` — React Native (New Architecture: Fabric + TurboModules + **JSI**) targeting **Android, iOS,
  macOS, and Windows** from one TS/React UI codebase. High-performance data handling is delegated to the
  shared C++ core (`libs/client-core`) over JSI. See `Plan/Platform/phase-4-client-core.md`.
- `web/` — the existing Next.js `dashboard/` (relocated in Phase 4) kept as a reference/web client.

_Scaffold only — the app is created in Phase 4._
