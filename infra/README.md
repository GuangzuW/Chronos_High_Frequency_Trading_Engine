# infra/ — Infrastructure as Code

- `terraform/` — reusable modules (Kubernetes, PostgreSQL, ClickHouse/Timescale, Redis, object store,
  Redpanda/Kafka, Vault) and per-environment workspaces (`dev`/`staging`/`prod`).
- `compose/` — local `docker-compose`/`kind` bringing up the same dependencies for the dev inner loop.

See `Plan/Platform/task-0-3-iac.md`. _Scaffold only._
