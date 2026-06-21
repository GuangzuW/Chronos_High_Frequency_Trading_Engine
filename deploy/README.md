# deploy/ — GitOps Deployment Manifests

Declarative deployment state synced by Argo CD/Flux (Task 0.4).

- `charts/` — Helm charts per service.
- `apps/` — Argo CD `Application` manifests.
- `mesh/` — service mesh install + mTLS/NetworkPolicy (Task 0.5).
- `observability/` — OTel collector, Prometheus, Loki, Tempo/Jaeger, Grafana, Alertmanager (Task 0.6).

_Scaffold only._
