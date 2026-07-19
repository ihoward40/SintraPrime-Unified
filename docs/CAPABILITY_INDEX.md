# Product Capability Index

> Not a marketing matrix. Authoritative as of commit 10cad07f046b5675ed10a1fba1aa4a955636f739. Status reflects
> current `main` tree + CI, not claims.

| Capability | User value | Implementation | Entrypoint | Test location | Status | Limitations | Next cert req |
|-----------|-----------|---------------|-----------|---------------|--------|-------------|---------------|
| Authentication | Identity | `portal/auth/` (JWT) | `portal/main.py` | `portal/tests/test_auth.py` | SUPPORTED | Refresh edge cases untested | Session revocation test |
| Tenancy / RBAC | Isolation | `portal/auth/rbac.py`, `portal/models/user.py` | API middleware | `portal/tests/test_rbac.py` | SUPPORTED | Per-package role assumptions | Cross-package RBAC audit |
| Intake | Client intake | `portal/routers/` + `agents/` | API | `tests/` | FUNCTIONAL | — | CI coverage |
| Case management | Case tracking | `portal/` models | API | `portal/tests/` | FUNCTIONAL | — | Dedicated suite |
| Document generation | Legal drafts | `legal_integrations/` (was `document_gen`, MISSING) | API/CLI | UNKNOWN | PARTIAL | `document_gen` path missing | Restore module + tests |
| Trust-law support | Jurisdiction analysis | `trust_law/` | CLI/API | `trust_law/tests/` | FUNCTIONAL | 19 jurisdictions only | Expand coverage |
| Consumer-protection | Dispute support | `legal_integrations/` | API | UNKNOWN | PARTIAL | — | Tests |
| Financial analysis | Statements | `financial_mastery/` | API | UNKNOWN | FUNCTIONAL | Simplified GAAP, not audit-grade | CPA review workflow |
| Payments | Fees | `backend/stripe-payments/` | API | backend tests? | DUPLICATED | Competes with `legal_integrations`; no CI verify | Unify + CI |
| Agents | Reasoning | `agents/` + `agent_protocol/` | API/runtime | package tests | EXPERIMENTAL | No unified runtime authority | Convergence |
| Durable workflows | Orchestration | `workflow_builder/` + `scheduler/` | API | `workflow_builder/tests/` | FUNCTIONAL | No dedicated CI WF test | WF CI gate |
| Mission Control | Governance ledger | `portal/services/mission_control_*` | API (ledger) | `portal/tests/test_mission_control_*` | SUPPORTED | Refusal-only; no live exec | Inc-2B (held) |
| Observability | Telemetry | `observability/` | internal | `observability/tests/` | FUNCTIONAL | Not a control plane | — |
| Audit / evidence | Compliance | `MissionControlRunControlEvent` + `audit_records` | internal | PG race lane | SUPPORTED | Multiple event logs | Unify |
| Reporting / export | Output | UNKNOWN | — | UNKNOWN | UNKNOWN | — | Locate |
| Frontend dashboards | Operator view | `web/` | browser | web build/lint | SUPPORTED | No behavior tests | Add e2e |
| Operations Floor | Ops view | `web/src/pages/OperationsFloor.tsx` | browser | visual checkpoint (not on main) | FROZEN LOCALLY | Commit 0aaffdc not on main | Merge visual PR |
| Deployment | Hosting | `deployment/`, `infrastructure/`, `docker-compose.yml` | ops | none in CI | DOCUMENTED ONLY | Not CI-verified | Deploy CI |

> "Next cert req" = the next evidence step before a subsystem may be called CERTIFIED.

