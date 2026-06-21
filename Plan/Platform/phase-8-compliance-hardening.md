# Phase 8 — Compliance, Surveillance & Hardening

## Goal
Make the platform defensible: regulatory recordkeeping, trade surveillance, and a full
security/resilience hardening pass before scale-up.

## Tasks

### 8.1 Compliance service & recordkeeping
- Consume the Chronos **audit stream** (`AuditLogger` / PUB `:5556`) plus OMS/ledger events into an
  immutable, queryable store (ClickHouse) for regulatory recordkeeping and **best-execution** logging.
- Order-event audit trail with full correlation lineage (client → fill).
- **Verification:** any historical order reconstructs its complete lifecycle with timestamps and actors.

### 8.2 Trade surveillance
- Detection jobs for spoofing/layering, wash trades, and abnormal patterns (the engine's AI risk hook
  in `RiskEngine` is the seed; here it becomes a post-trade surveillance pipeline + alerts).
- **Verification:** a seeded spoofing scenario raises a surveillance alert.

### 8.3 Security hardening
- Threat model (STRIDE) per bounded context; secrets rotation; dependency/SBOM scanning gates;
  SAST/DAST in CI; least-privilege review of mesh policies; encryption-at-rest verification.
- Run the repo's existing CodeQL + Trivy gates across all services.
- **Verification:** clean SAST/DAST/dependency scans; documented threat model with mitigations.

### 8.4 Penetration test & remediation
- External-style pen test of auth, BFF, order placement, and client token handling; remediate findings.
- **Verification:** no high/critical findings open; retest passes.

### 8.5 Resilience & chaos
- Validate circuit breakers, bulkheads, backpressure, idempotency, and the **kill switch** under
  failure injection (kill venue, kill ledger, network partition).
- Define and verify SLOs and error budgets.
- **Verification:** chaos experiments degrade gracefully (e.g. read-only mode) without data loss or
  orphaned reservations.

## Exit criteria
The platform meets recordkeeping/surveillance expectations, passes security review and pen test, and
provably degrades gracefully under failure.
