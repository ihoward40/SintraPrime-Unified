# Product Capability Index

> Not a marketing matrix. Authoritative as of commit `48e2caa759661cc75617cc752bcc26eaad666647` (tree `9ee6d193dd7f607cd59487df9ef26d46b9593803`). Status reflects
> current `main` tree + CI, not claims.

| Capability | User value | Implementation | Entrypoint | Test location | Status | Limitations | Next cert req |
|-----------|-----------|---------------|-----------|---------------|--------|-------------|---------------|
| Authentication | Identity | `portal/auth/` (JWT) | `portal/main.py` | `portal/tests/test_auth_tenant_rbac_certification.py` | CERTIFIED FOR RECORDED SCOPE | Refresh edge cases untested; session revocation not implemented; no token rotation; no logout invalidation | Session/token lifecycle certification |
| Tenancy / RBAC | Isolation | `portal/auth/rbac.py`, `portal/models/user.py`, `portal/routers/{billing,blackstone,users}.py` | API middleware | `portal/tests/test_auth_tenant_rbac_certification.py` | CERTIFIED FOR RECORDED SCOPE | Per-package role assumptions audited in certification scope; cross-package RBAC audit pending | Cross-package RBAC audit |
| Intake | Client intake | `portal/routers/` + `agents/` | API | `tests/` | FUNCTIONAL | — | CI coverage |
| Case management | Case tracking | `portal/` models | API | `portal/tests/` | FUNCTIONAL | — | Dedicated suite |
| Document generation | Legal drafts | `legal_integrations/` (was `document_gen`, MISSING) | API/CLI | UNKNOWN | PARTIAL | `document_gen` path missing | Restore module + tests |
| Trust-law support | Jurisdiction analysis | `trust_law/` | CLI/API | `trust_law/tests/` | FUNCTIONAL | 19 jurisdictions only | Expand coverage |
| Consumer-protection | Dispute support | `legal_integrations/` | API | UNKNOWN | PARTIAL | — | Tests |
| Financial analysis | Statements | `financial_mastery/` | API | UNKNOWN | FUNCTIONAL | Simplified GAAP, not audit-grade | CPA review workflow |
| Payments | Fees | `backend/stripe-payments/` | API | backend tests? | DUPLICATED | Competes with `legal_integrations`; no CI verify; annual savings mismatch (issue #185) | Unify + CI |
| Agents | Reasoning | `agents/` + `agent_protocol/` | API/runtime | package tests | EXPERIMENTAL | No unified runtime authority | Convergence |
| Durable workflows | Orchestration | `workflow_builder/` + `scheduler/` | API | `workflow_builder/tests/` | FUNCTIONAL | No dedicated CI WF test | WF CI gate |
| Mission Control | Governance ledger | `portal/services/mission_control_*` | API (ledger) | `portal/tests/test_mission_control_*` | SUPPORTED | Refusal-only; no live exec | Shared execution protocol |
| Observability | Telemetry | `observability/` | internal | `observability/tests/` | FUNCTIONAL | Not a control plane | — |
| Audit / evidence | Compliance | `portal/auth/audit_envelope.py` + `MissionControlRunControlEvent` + `audit_records` | internal | `portal/tests/test_audit_correlation_non_http_certification.py` + PG race lane | CERTIFIED FOR RECORDED SCOPE | Multiple event logs; unified audit schema pending | Unified audit event schema |
| Correlation | Request tracing | `portal/auth/correlation.py` + `portal/middleware/correlation_middleware.py` | HTTP middleware | `portal/tests/test_http_correlation_ws_hardening_certification.py` | CERTIFIED FOR RECORDED SCOPE | Incomplete server-level exception correlation | Server-level exception correlation |
| WebSocket transport | Real-time transport | `portal/auth/websocket_auth.py` + `portal/auth/ws_hardening.py` | WebSocket | `portal/tests/test_http_correlation_ws_hardening_certification.py` | CERTIFIED FOR RECORDED SCOPE | Process-local enforcement; deprecated query-token support; no distributed enforcement | Distributed WebSocket enforcement |
| Reporting / export | Output | UNKNOWN | — | UNKNOWN | UNKNOWN | — | Locate |
| Frontend dashboards | Operator view | `web/` | browser | web build/lint | SUPPORTED | No behavior tests | Add e2e |
| Operations Floor | Ops view | `web/src/pages/OperationsFloor.tsx` | browser | web build/lint (restored via PR #208, commit `aa0c9a74`) | SUPPORTED | No behavior tests; visual checkpoint `0aaffdc` not resolvable in current repository object database or authoritative refs | Add e2e |
| Deployment | Hosting | `deployment/`, `infrastructure/`, `docker-compose.yml` | ops | none in CI | DOCUMENTED ONLY | Not CI-verified; secrets missing (issue #186) | Deploy CI |

> "Next cert req" = the next evidence step before a subsystem may be called CERTIFIED.
> CERTIFIED FOR RECORDED SCOPE means the specific increment's test suite passes in CI.
> It does NOT mean production-certified, compliance-certified, or distributed enforcement.