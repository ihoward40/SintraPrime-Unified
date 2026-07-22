# SintraPrime-Unified — Canonical Architecture Authority

> Authoritative as of commit `2d6ff2e10b639ec2601a46ba1592aaa62e597349` (tree `584d44a1bf8f267ea3f00e84018f10026d8c4297`) plus PR-B branch changes for PostgreSQL fresh-bootstrap reconciliation.
> This document is the single source of architectural truth. Where no single
> authority exists, the status is `UNRESOLVED — convergence required`.

## Product authority

| Concern | Authority | Notes |
|---------|-----------|-------|
| Backend / API / identity boundary | `portal/` | FastAPI app (`portal/main.py`, `create_app`). Routers, services, models, auth, RBAC, websocket. |
| Current React frontend | `web/` | React + TypeScript; shared shell (`App.tsx`, `Sidebar.tsx`). Operator projection only. |
| Durable workflow engine | `workflow_builder/` | `workflow_engine.py` (engine), `workflow_api.py` (API), `web_tui.py`. Background execution via `scheduler/`. |
| Mission Control | `portal/services/mission_control_*.py` + `portal/models/mission_control_*.py` | Command-ledger + run-control projection (read-only state machine). Refusal-only commands. |
| Monitoring / telemetry | `observability/` | `metrics.py`, `tracer.py`, `thought_debugger.py`, `time_travel.py`. Telemetry only. |
| Database models | `portal/models/` | SQLAlchemy declarative models; Base in `portal/database.py`. |
| Migrations | `portal/migrations/*.sql` + `portal/scripts/postgresql_bootstrap.py` | Raw SQL fresh-bootstrap sequence with CI verifier. **No Alembic.** Fresh bootstrap only; not unknown-schema upgrade certification. See `docs/DATABASE_AUTHORITY.md`. |
| Evidence / governance | `docs/`, `artifacts/`, `mission-control-evidence/`, `docs/governance/` | Frozen receipts, gate evidence, decision logs, tags. |

## Authority matrix (exactly one authority per concern)

| Concern              | Authority                                          | Non-authoritative / legacy alternatives |
| -------------------- | -------------------------------------------------- | --------------------------------------- |
| API entrypoint       | `portal/main.py` (FastAPI)                         | `backend/stripe-payments/main.py`, `apps/*` |
| Frontend             | `web/`                                             | legacy `apps/SintraPrime`, `apps/sintraprime` |
| Authentication       | `portal/auth/` (JWT)                               | `portal/sso/` (delegated) |
| Tenant identity      | request context / `portal/middleware`              | per-package tenant fields (unverified) |
| RBAC                 | `portal/auth/rbac.py` + `portal/models/user.py`    | feature-package role assumptions |
| Identity claims      | `portal/auth/rbac.py` (identity-claim validation)  | per-package identity assumptions |
| Correlation context  | `portal/auth/correlation.py` + `portal/middleware/correlation_middleware.py` | ad-hoc request tagging |
| Audit envelopes      | `portal/auth/audit_envelope.py`                    | per-package event logs |
| WebSocket auth        | `portal/auth/websocket_auth.py`                    | query-token (deprecated) |
| WebSocket hardening  | `portal/auth/ws_hardening.py`                      | none (new in PR #217) |
| Workflow execution   | `workflow_builder/` + `scheduler/`                 | `agent_protocol/` (agent orchestration, not durable WF) |
| Execution governance | `portal/services/mission_control_command_guard.py` | `secure_execution/` (separate TEE, not wired to RBAC) |
| Monitoring           | `observability/`                                   | ad-hoc logging in packages |
| Database models      | `portal/models/`                                   | models declared inside feature packages |
| Migration execution  | `portal/migrations/*.sql` (raw)                    | test `create_all` (runtime only, NOT deployed schema) |
| Audit events         | `MissionControlRunControlEvent` (Mission Control) + `audit_records` + `portal/auth/audit_envelope.py` | per-package event logs |
| Evidence manifests   | `docs/governance/` + `mission-control-evidence/`   | root-level `PHASE_*.md` receipts (historical) |
| Payments             | `backend/stripe-payments/`                         | `legal_integrations` (billing context), `src/payment/` (MISSING) |
| Agent runtime        | `UNRESOLVED — convergence required`                | `agents/`, `agent_protocol/`, `core/universe`, `superintelligence/` |

## Runtime flow

```
User
  → web/ (React, operator projection)
  → portal/main.py (API)
  → portal/middleware/correlation_middleware.py (HTTP request-ID assignment)
  → portal/auth/ (JWT authentication)
  → portal/auth/rbac.py (identity-claim validation + permission check)
  → tenant context (portal/middleware)
  → portal/auth/correlation.py (correlation context propagation)
  → portal/services/* (service boundary)
  → workflow_builder/ + scheduler/ OR agents/ (workflow / agent execution)
  → portal/models/ (database persistence)
  → portal/auth/audit_envelope.py (immutable audit event envelope)
  → audit / MissionControlRunControlEvent (audit)
  → Result → web/ projection
```

Execution may also originate from: background `scheduler/` jobs, `workflow_builder`
runners, agent runtimes, CLI (`portal/scripts/`, `scripts/`), webhooks (`channels/`),
and admin scripts. There is **no centralized execution authority** across all origins
(see `UNRESOLVED` agent runtime above).

## Certification CI lanes

The following certification-specific CI lanes are defined in `.github/workflows/ci.yml`:

| CI lane | Scope | Certifying PR | Test file |
|---------|-------|----------------|-----------|
| `auth-tenant-rbac-certification` | Authentication, tenant isolation, RBAC | PR #214 | `portal/tests/test_auth_tenant_rbac_certification.py` |
| `audit-correlation-non-http-certification` | Audit correlation, non-HTTP authorization | PR #215 | `portal/tests/test_audit_correlation_non_http_certification.py` |
| `http-correlation-ws-hardening-certification` | HTTP request-ID correlation, WebSocket hardening | PR #217 | `portal/tests/test_http_correlation_ws_hardening_certification.py` |
| `postgresql-bootstrap-certification` | Raw-SQL fresh bootstrap, affected evidence/audit live-catalog ORM CRUD, and PostgreSQL ORM create_all guard | PR-B | `portal/tests/test_postgresql_bootstrap_schema_authority.py` |

These lanes are CERTIFIED FOR THE RECORDED SCOPE of their respective increments.
They do NOT constitute production certification, compliance certification,
or distributed enforcement.

## Explicit non-authorities (do NOT own live execution authority)

- Mission Control run-control projection — state machine only, no runner control.
- Observatory / `observability/` monitoring — telemetry only.
- `secure_execution/` — TEE/zero-trust primitives; not wired to portal RBAC authority.
- Old nested apps (`apps/*`) — legacy shells.
- Stale PR branches — not deployed.
- Test harnesses — verification only.
- Evidence artifacts — records, not executors.

## Ambiguity

The repository currently has **no single agent runtime authority** and **no single
execution-control authority** spanning API, workflow, and agent origins. Convergence
Increment One documented this; it does NOT resolve it. Resolving requires a future
shared execution protocol (see `docs/governance/MISSION_CONTROL_OBSERVATORY_AUTHORITY.md`).

Security certifications from PRs #214–#217 enforce identity, tenant, correlation, audit,
and transport controls at the code level, but they do NOT establish a centralized
execution authority. The shared execution-control protocol remains the prerequisite
for Mission Control Increment Two B and Observatory G4.8.