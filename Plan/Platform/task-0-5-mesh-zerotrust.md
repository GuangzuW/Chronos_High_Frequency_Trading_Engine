# Task 0.5 — Service Mesh & Zero-Trust Baseline

## Goal
Enforce mutual TLS between all services, default-deny networking, and centralized secret management
before any business service ships.

## Key Files & Context
- New: `deploy/mesh/` (Istio/Linkerd install + policies), `deploy/policies/` (NetworkPolicies),
  Vault config in `infra/`.

## Implementation Steps
1. **Install the mesh** (Linkerd for simplicity, or Istio for richer policy) into the cluster via GitOps.
2. **mTLS everywhere**: enable strict mTLS; reject plaintext traffic between pods.
3. **Default-deny NetworkPolicies**: services explicitly allow only the peers they need (e.g. only OMS
   and Risk may reach Ledger).
4. **Secrets**: HashiCorp Vault with dynamic DB credentials and short-lived tokens; no plaintext secrets
   in env, Git, or images. Wire the existing `.env` pattern (`bridge/.env`) to Vault for non-local envs.
5. **Workload identity**: per-service SPIFFE/SVID or service accounts; least-privilege RBAC.

## Verification
- Traffic capture shows service-to-service calls are mTLS-encrypted.
- A pod outside policy cannot reach the Ledger service (connection denied).
- A service obtains its DB credential from Vault at runtime; rotating the secret takes effect without a
  rebuild.
