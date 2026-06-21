# Task 0.3 — Infrastructure as Code

## Goal
Declare all infrastructure in Terraform so environments are reproducible and reviewable, with no
click-ops.

## Key Files & Context
- New: `infra/terraform/` with reusable modules and per-environment workspaces (`dev`/`staging`/`prod`).

## Implementation Steps
1. **Modules** for: Kubernetes cluster, managed PostgreSQL, ClickHouse/TimescaleDB, Redis,
   object store (MinIO/S3), Redpanda/Kafka, HashiCorp Vault.
2. **Remote state** with locking; environment isolation via workspaces or separate state backends.
3. **Network baseline**: VPC/subnets, private networking for data stores, ingress controller.
4. **Policy as code**: `tflint` + a policy check (OPA/Conftest) in CI; tag/label conventions for cost.
5. **Local dev**: a `docker-compose.yml` (or `kind` config) that brings up the same dependencies locally
   for fast inner-loop development.

## Verification
- `terraform plan` is clean and `terraform apply` brings up a `dev` cluster from zero.
- `docker compose up` provisions Postgres + Redis + Redpanda locally; a smoke script connects to each.
