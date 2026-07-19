# SintraPrime-Unified — Canonical Architecture Authority

> Authoritative as of commit 10cad07f046b5675ed10a1fba1aa4a955636f739 (tree 66f59a5bf832e9f3ce3c484c64891fd543359abf).
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
| Migrations | `portal/migrations/*.sql` | Raw SQL applied by bootstrap/entrypoint. **No Alembic.** See `docs/DATABASE_AUTHORITY.md`. |
| Evidence / governance | `docs/`, `artifacts/`, `mission-control-evidence/`, `docs/governance/` | Frozen receipts, gate evidence, decision logs, tags. |

## Authority matrix (exactly one authority per concern)

| Concern              | Authority                                          | Non-authoritative / legacy alternatives |
| -------------------- | -------------------------------------------------- | --------------------------------------- |
| API entrypoint       | `portal/main.py` (FastAPI)                         | `backend/stripe-payments/main.py`, `apps/*` |
| Frontend             | `web/`                                             | legacy `apps/SintraPrime`, `apps/sintraprime` |
| Authentication       | `portal/auth/` (JWT)                               | `portal/sso/` (delegated) |
| Tenant identity      | request context / `portal/middleware`              | per-package tenant fields (unverified) |
| RBAC                 | `portal/auth/rbac.py` + `portal/models/user.py`    | feature-package role assumptions |
| Workflow execution   | `workflow_builder/` + `scheduler/`                 | `agent_protocol/` (agent orchestration, not durable WF) |
| Execution governance | `portal/services/mission_control_command_guard.py` | `secure_execution/` (separate TEE, not wired to RBAC) |
| Monitoring           | `observability/`                                   | ad-hoc logging in packages |
| Database models      | `portal/models/`                                   | models declared inside feature packages |
| Migration execution  | `portal/migrations/*.sql` (raw)                    | test `create_all` (runtime only, NOT deployed schema) |
| Audit events         | `MissionControlRunControlEvent` (Mission Control) + `audit_records` | per-package event logs |
| Evidence manifests   | `docs/governance/` + `mission-control-evidence/`   | root-level `PHASE_*.md` receipts (historical) |
| Payments             | `backend/stripe-payments/`                         | `legal_integrations` (billing context), `src/payment/` (MISSING) |
| Agent runtime        | `UNRESOLVED — convergence required`                | `agents/`, `agent_protocol/`, `core/universe`, `superintelligence/` |

## Runtime flow

```
User
  → web/ (React, operator projection)
  → portal/main.py (API)
  → portal/auth/ (JWT authentication)
  → tenant context (portal/middleware)
  → portal/auth/rbac.py (permission check)
  → portal/services/* (service boundary)
  → workflow_builder/ + scheduler/ OR agents/ (workflow / agent execution)
  → portal/models/ (database persistence)
  → audit / MissionControlRunControlEvent (audit)
  → Result → web/ projection
```

Execution may also originate from: background `scheduler/` jobs, `workflow_builder`
runners, agent runtimes, CLI (`portal/scripts/`, `scripts/`), webhooks (`channels/`),
and admin scripts. There is **no centralized execution authority** across all origins
(see `UNRESOLVED` agent runtime above).

## Explicit non-authorities (do NOT own live execution authority)

- Mission Control run-control projection — state machine only, no runner control.
- Observatory / `observability/` monitoring — telemetry only.
- Old nested apps (`apps/*`) — legacy shells.
- Stale PR branches — not deployed.
- Test harnesses — verification only.
- Evidence artifacts — records, not executors.

## Ambiguity

The repository currently has **no single agent runtime authority** and **no single
execution-control authority** spanning API, workflow, and agent origins. Convergence
Increment One documents this; it does NOT resolve it. Resolving requires a future
shared execution protocol (see `docs/governance/MISSION_CONTROL_OBSERVATORY_AUTHORITY.md`).

