# Task 0.6 — Observability Baseline

## Goal
Make traces, metrics, and logs first-class from day one, with a correlation ID that follows an order
from the client all the way into the Chronos audit stream.

## Key Files & Context
- New: `deploy/observability/` (OTel collector, Prometheus, Loki, Tempo/Jaeger, Grafana, Alertmanager).
- Existing audit sink: `include/chronos/audit_logger.hpp` (PUB `:5556` consumer) — correlation IDs
  should be carried through to it.

## Implementation Steps
1. **OpenTelemetry**: deploy the collector; instrument the service template (Task 0.7) with traces +
   metrics + structured logs by default.
2. **Correlation ID convention**: generated at the BFF (or client), propagated via gRPC metadata and
   Kafka headers, and stamped onto Chronos order events so the audit trail joins the distributed trace.
3. **Golden-signal dashboards**: latency, traffic, errors, saturation per service; an order-flow
   dashboard spanning BFF → OMS → Risk → Gateway → engine.
4. **Alerting**: Alertmanager rules for SLO breaches; routes to on-call (stubbed in dev).
5. **Cost/retention**: sane retention for logs/traces; sampling strategy for high-volume market data.

## Verification
- A synthetic order produces a single distributed trace spanning every hop, including the engine audit
  event, joined by correlation ID.
- Grafana shows the golden-signal dashboards populated; a forced error fires an alert.
