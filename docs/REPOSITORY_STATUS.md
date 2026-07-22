# Repository Status Taxonomy

## Definitions
- SUPPORTED: maintained, tested in CI, intended for use.
- CERTIFIED FOR RECORDED SCOPE: SUPPORTED + specific increment certification completed and passing in CI. NOT production-certified or compliance-certified.
- FUNCTIONAL: works but not fully covered by CI or not on supported path.
- PARTIAL: partially implemented; key paths missing.
- EXPERIMENTAL: prototype / POC; not production-intended.
- DOCUMENTED ONLY: described but not verified by automated tests.
- LEGACY: older implementation retained for compatibility.
- DUPLICATED: overlaps another subsystem with unclear authority.
- ORPHANED: unreferenced or disconnected from main flows.
- OBSOLETE: superseded; should be removed.
- UNKNOWN: cannot determine status from current tree.

## Subsystem map

| Subsystem | Status | Basis |
|-----------|--------|-------|
| `portal/` | SUPPORTED | Authoritative backend; CI test lane; merged Mission Control; PR #213–217 governance + security certifications. |
| `portal/auth/rbac.py` | CERTIFIED FOR RECORDED SCOPE | PR #214: identity claims, tenant-scoped auth, RBAC escalation controls. CI lane: `auth-tenant-rbac-certification`. |
| `portal/auth/audit_envelope.py` | CERTIFIED FOR RECORDED SCOPE | PR #215: immutable audit envelopes with correlation context. CI lane: `audit-correlation-non-http-certification`. |
| `portal/auth/correlation.py` + `portal/middleware/correlation_middleware.py` | CERTIFIED FOR RECORDED SCOPE | PR #215/#217: correlation context + HTTP request-ID middleware. CI lane: `http-correlation-ws-hardening-certification`. |
| `portal/auth/ws_hardening.py` | CERTIFIED FOR RECORDED SCOPE | PR #217: WebSocket capacity, rate, timeout, payload controls. CI lane: `http-correlation-ws-hardening-certification`. |
| `portal/auth/websocket_auth.py` | CERTIFIED FOR RECORDED SCOPE | PR #215/#217: WebSocket authentication and authorization. |
| `web/` | SUPPORTED | React frontend; CI lint/type/build. No exec mutation. |
| `workflow_builder/` | FUNCTIONAL | Engine + API present; not gated by dedicated CI WF test. |
| `scheduler/` | FUNCTIONAL | Executor/dispatcher; arming test verified (PR #164). |
| `agents/` | EXPERIMENTAL | Multiple agent packages; no unified runtime authority. |
| `agent_protocol/` | EXPERIMENTAL | Agent orchestration protocol; separate from durable WF. |
| `core/universe` | EXPERIMENTAL | Exploratory; unclear production role. |
| `observability/` | FUNCTIONAL | Telemetry module; not a control plane. |
| Mission Control (`portal/services/mission_control_*`) | SUPPORTED | Merged PR #212; PG race proof; refusal-only. Security certifications (PR #214–217) enforce boundary at code level. |
| `secure_execution/` | EXPERIMENTAL | TEE/zero-trust module; not wired to portal RBAC. |
| `trust_law/` | FUNCTIONAL | 19 jurisdictions; test path under trust_law/tests. |
| `legal_integrations/` | FUNCTIONAL | Billing/legal integration context. |
| `backend/stripe-payments/` | DUPLICATED | Separate payment app vs `legal_integrations`; competes for payment authority; annual savings mismatch (issue #185). |
| `apps/SintraPrime` | LEGACY | Vendored app shell; superseded by `web/` + `portal/`. |
| `apps/sintraprime` | LEGACY | Duplicate naming; legacy. |
| `phase18/mobile_app` | UNKNOWN | Not present on current `main` tree (verify before claiming). |
| `app_builder/` | EXPERIMENTAL | Scaffolding tool. |
| `deployment/` (linux/windows) | DOCUMENTED ONLY | Scripts; no CI deploy verification; secrets missing (issue #186). |
| `infrastructure/` (aws/azure/gcp) | DOCUMENTED ONLY | Terraform/Bicep present; not applied in CI. |
| Root `Dockerfile` image build | SUPPORTED (image construction only) | `Docker Image Build Verification` builds the canonical portal image without runtime secrets. Does not verify Compose startup, deployment, registry push, or production readiness. |
| `docker-compose.yml` full-stack runtime | DOCUMENTED ONLY | Runtime Compose remains fail-closed for required secrets; not used by image-build verification and not production-certified. |
| `core/Dockerfile` and `apps/sintraprime/Dockerfile` | LEGACY / EXPERIMENTAL | Present for legacy Compose services; not certified as supported deployment images by PR-E. |
| Evidence/receipts (`docs/`, `artifacts/`, `mission-control-evidence/`, `docs/certification/`) | SUPPORTED (governance) | Current Mission Control evidence fresh; certification evidence from PR #214–217; historical PHASE_* stale. |

## Certification CI lanes

| CI lane | Scope | Status |
|---------|-------|--------|
| `auth-tenant-rbac-certification` | Authentication, tenant isolation, RBAC | CERTIFIED FOR RECORDED SCOPE (PR #214) |
| `audit-correlation-non-http-certification` | Audit correlation, non-HTTP authorization | CERTIFIED FOR RECORDED SCOPE (PR #215) |
| `http-correlation-ws-hardening-certification` | HTTP request-ID correlation, WebSocket hardening | CERTIFIED FOR RECORDED SCOPE (PR #217) |
| `postgresql-race` | Mission Control immutability + hash chain | SUPPORTED (PG race proof) |
| `postgresql-bootstrap-certification` | Raw-SQL fresh bootstrap + affected evidence/audit ORM parity | SUPPORTED for fresh-bootstrap certification only; no unknown-schema upgrade certification |
| `test` (default) | Full Python suite | SUPPORTED |
| `lint` | Ruff lint | SUPPORTED |
| `claims-validation` | Repository claims validation | SUPPORTED |
| `Docker Image Build Verification` | Canonical portal image construction only | SUPPORTED for build verification; no runtime secrets, service startup, registry push, deployment, or production-certification claim. |

> Status is assigned from current `main` tree and CI, not from marketing claims.
> Tests alone do NOT certify a subsystem.
> CERTIFIED FOR RECORDED SCOPE means the specific increment's test suite passes in CI.
> It does NOT mean production-certified, compliance-certified, or distributed enforcement.