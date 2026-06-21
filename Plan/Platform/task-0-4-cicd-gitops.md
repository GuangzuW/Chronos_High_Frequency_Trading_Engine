# Task 0.4 — CI/CD & GitOps

## Goal
Extend the existing GitHub Actions pipeline into reusable, multi-language workflows and adopt GitOps for
deployment, with security gates throughout.

## Key Files & Context
- Existing: `.github/workflows/ci.yml` (build/test/coverage, release, Trivy), `codeql.yml`, `Dockerfile`.
- The `apt_get` typo in `ci.yml` (lines 24, 65) — **fixed in this pass**.
- New: `.github/workflows/*` reusable workflows, `deploy/` (Helm charts + Argo CD `Application`s).

## Implementation Steps
1. **Reusable build workflow** per language (C++/Go/TS): build → unit → contract tests → image build →
   SBOM → Trivy/Grype scan → push to registry.
2. **GitOps**: install Argo CD (or Flux); `deploy/` holds Helm charts and `Application` manifests synced
   automatically. App images updated by digest via PRs (no imperative `kubectl apply`).
3. **Ephemeral previews**: each PR deploys to a temporary namespace; teardown on merge/close.
4. **Repo hygiene**: required status checks, signed commits, trunk-based development with short-lived
   branches, branch protection.
5. **Release**: keep the existing tag-triggered release job; add progressive-delivery hooks (canary)
   for backend services (full rollout in Phase 9).

## Verification
- A trivial PR runs build + scans, deploys to a preview namespace, and tears down on close.
- `ci.yml` dependency install now succeeds (`apt-get`, not `apt_get`).
- Merging to `main` triggers an Argo CD sync that rolls out the change.
