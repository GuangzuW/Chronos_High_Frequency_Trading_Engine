# services/ — Backend Microservices

Each subdirectory is one bounded context (see `Plan/Platform/00-master-architecture-and-roadmap.md` §4),
cloned from `libs/service-template` (Task 0.7): hexagonal layout, gRPC + Kafka adapters, generated
`contracts/` bindings, OTel, multi-stage Dockerfile, Helm chart.

Planned services: `api-gateway`, `identity`, `account`, `ledger`, `reference-data`, `market-data`
(seeded from `bridge/`), `pricing`, `risk`, `oms`, `market-gateway`, `portfolio`, `settlement`,
`compliance`, `notification`, and `execution-core` (the relocated Chronos engine, Task 0.1b).

_Scaffold only — services are created per phase._
