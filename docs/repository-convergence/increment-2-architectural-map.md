# Repository Convergence Increment Two — Current Architectural Map

Authoritative as of commit `48e2caa759661cc75617cc752bcc26eaad666647` (tree `9ee6d193dd7f607cd59487df9ef26d46b9593803`).

This map identifies the current authority for each subsystem domain on `main`.
Where authority is unresolved, it is labeled `UNRESOLVED — convergence required`.

---

## 1. Authentication / RBAC

| Field | Value |
|-------|-------|
| Current authority | `portal/auth/rbac.py` + `portal/models/user.py` + `portal/routers/{billing,blackstone,users}.py` |
| Status | CERTIFIED FOR RECORDED SCOPE (PR #214) |
| Entry point | `portal/main.py` → `portal/auth/` middleware |
| Source path | `portal/auth/rbac.py`, `portal/auth/jwt_handler.py`, `portal/auth/password_handler.py`, `portal/auth/session_manager.py` |
| Test/evidence path | `portal/tests/test_auth_tenant_rbac_certification.py` |
| CI lane | `auth-tenant-rbac-certification` |
| Known limitation | Refresh edge cases untested; session revocation not implemented; no token rotation; no logout invalidation; no concurrent session policy |
| Next certification requirement | Session/token lifecycle certification (revocation, rotation, logout invalidation, replay detection, key rotation) |
| Conflicting/superseded branches | None open; PR #206 execution guard is separate concern |

---

## 2. Correlation / Audit

| Field | Value |
|-------|-------|
| Current authority | `portal/auth/audit_envelope.py` + `portal/auth/correlation.py` + `portal/middleware/correlation_middleware.py` |
| Status | CERTIFIED FOR RECORDED SCOPE (PR #215 audit correlation; PR #217 HTTP correlation) |
| Entry point | `portal/main.py` (middleware registration) |
| Source path | `portal/auth/audit_envelope.py`, `portal/auth/correlation.py`, `portal/middleware/correlation_middleware.py` |
| Test/evidence path | `portal/tests/test_audit_correlation_non_http_certification.py`, `portal/tests/test_http_correlation_ws_hardening_certification.py` |
| CI lanes | `audit-correlation-non-http-certification`, `http-correlation-ws-hardening-certification` |
| Known limitation | Multiple event logs still exist; incomplete server-level exception correlation; unified audit schema pending |
| Next certification requirement | Unified audit event schema; server-level exception correlation |
| Conflicting/superseded branches | PR #205 (Observatory G4.6) has event model that may conflict with audit envelope authority — REPLACE WITH CLEAN SUCCESSOR |

---

## 3. Mission Control

| Field | Value |
|-------|-------|
| Current authority | `portal/services/mission_control_*.py` + `portal/models/mission_control_*.py` |
| Status | SUPPORTED (refusal-only; no live execution) |
| Entry point | `portal/routers/mission_control.py` + `portal/routers/mission_control_commands.py` |
| Source path | `portal/services/mission_control_command_guard.py`, `portal/services/mission_control_command_service.py`, `portal/services/mission_control_run_control_service.py`, `portal/services/permission_provisioning.py` |
| Test/evidence path | `portal/tests/test_mission_control.py`, `portal/tests/test_mission_control_commands.py`, `portal/tests/test_mission_control_run_controls.py`, `portal/tests/test_permission_provisioning.py` |
| CI lane | `postgresql-race` (proves immutability + hash chain) |
| Known limitation | Refusal-only command execution (`COMMAND_EXECUTION_NOT_ENABLED`); no live pause/resume; no runner ownership; no durable workflow mutation; projection only |
| Next certification requirement | Shared execution-control protocol before Increment Two B or G4.8 |
| Conflicting/superseded branches | PR #206 (Observatory G4.7 execution guard) — CLOSE AS SUPERSEDED; introduces third execution-control surface |

---

## 4. Durable Execution

| Field | Value |
|-------|-------|
| Current authority | `workflow_builder/` + `scheduler/` |
| Status | FUNCTIONAL |
| Entry point | `workflow_builder/workflow_api.py` (API), `scheduler/task_scheduler.py` (scheduler) |
| Source path | `workflow_builder/workflow_engine.py`, `workflow_builder/workflow_schema.py`, `scheduler/task_executor.py`, `scheduler/task_dispatcher.py`, `scheduler/task_queue.py` |
| Test/evidence path | `workflow_builder/tests/` |
| CI lane | Default `test` lane (no dedicated WF CI test) |
| Known limitation | No dedicated CI workflow test; no centralized execution authority across all origins |
| Next certification requirement | WF CI gate; shared execution-control protocol |
| Conflicting/superseded branches | PR #134 (Durable Checkpointer) — CLOSE AS SUPERSEDED (132 behind); PR #206 — CLOSE AS SUPERSEDED |

---

## 5. Observability

| Field | Value |
|-------|-------|
| Current authority | `observability/` |
| Status | FUNCTIONAL (telemetry only; not a control plane) |
| Entry point | internal |
| Source path | `observability/metrics.py`, `observability/tracer.py`, `observability/thought_debugger.py`, `observability/time_travel.py` |
| Test/evidence path | `observability/tests/` |
| CI lane | Default `test` lane |
| Known limitation | Not a control plane; no execution authority |
| Next certification requirement | None (telemetry only) |
| Conflicting/superseded branches | PR #205 (Observatory G4.6) — REPLACE WITH CLEAN SUCCESSOR; PR #206 (Observatory G4.7) — CLOSE AS SUPERSEDED |

---

## 6. Blackstone

| Field | Value |
|-------|-------|
| Current authority | `blackstone/` |
| Status | SUPPORTED (governance infrastructure) |
| Entry point | `portal/routers/blackstone.py` (API) |
| Source path | `blackstone/engines/` (authority, evidence, provenance, reasoning, risk engines), `blackstone/cases/` (7 case modules), `blackstone/bra/` (ccs, cdr, cel, disclaimers, ko), `blackstone/models.py` |
| Test/evidence path | `blackstone/tests/test_blackstone_engines.py`, `blackstone/bra/tests/test_*.py` |
| CI lane | Default `test` lane (not in dedicated certification lane) |
| Known limitation | Not in dedicated CI certification lane; case workflow not unified with Mission Control; evaluation not connected to governed human review |
| Next certification requirement | Dedicated Blackstone CI lane; connect evaluation to governed human review |
| Conflicting/superseded branches | None open |

---

## 7. Payments

| Field | Value |
|-------|-------|
| Current authority | `backend/stripe-payments/` (DUPLICATED — competes with `legal_integrations/` billing) |
| Status | DUPLICATED |
| Entry point | API |
| Source path | `backend/stripe-payments/`, `legal_integrations/financial_connectors.py` |
| Test/evidence path | UNKNOWN (cited 89 in original claims; retired layout) |
| CI lane | NOT in default lane (no payment CI verified) |
| Known limitation | Payment authority duplicated; annual savings pricing mismatch (issue #185, function output 9900 vs test expectation 10800); no CI verification; production disabled |
| Next certification requirement | Unify payment authority; separate checkout, ledger, invoice, case-start; certify test-mode end to end |
| Conflicting/superseded branches | PR #192 (monetization security) — SPLIT REQUIRED (132 behind, base is PR #134) |

---

## 8. Document Generation

| Field | Value |
|-------|-------|
| Current authority | `legal_integrations/` (partial; former `document_gen` path is MISSING) |
| Status | PARTIAL |
| Entry point | API/CLI |
| Source path | `legal_integrations/integrations_api.py`, `trust_law/trust_document_generator.py` (trust documents only) |
| Test/evidence path | UNKNOWN (cited 189 in original claims; retired layout) |
| CI lane | UNKNOWN |
| Known limitation | Former `document_gen` package missing; no deterministic DOCX/PDF contract tests; dead module references remain |
| Next certification requirement | Locate actual current rendering pipeline; establish one supported entry point; add deterministic DOCX/PDF contract tests; remove dead module references |
| Conflicting/superseded branches | None open |

---

## 9. Frontend / Operator Surfaces

| Field | Value |
|-------|-------|
| Current authority | `web/` (React + TypeScript) |
| Status | SUPPORTED |
| Entry point | browser |
| Source path | `web/src/` (App.tsx, Sidebar.tsx, pages/) |
| Test/evidence path | web build/lint (no behavior tests) |
| CI lane | `lint` (web lint/type/build) |
| Known limitation | No behavior tests; no Playwright e2e; no accessibility checks; no auth/tenant routing flow tests; no Mission Control refusal-state behavior tests; no Operations Floor real-data/fallback labeling tests; no no-secret URL tests for WebSockets |
| Next certification requirement | Playwright smoke tests for critical routes; accessibility checks; auth/tenant routing flows; Mission Control refusal-state behavior; Operations Floor real-data/fallback labeling; no-secret URL tests for WebSockets |
| Conflicting/superseded branches | PR #189 (eslint no-explicit-any) — REASSESS (43 behind) |

---

## 10. Deployment

| Field | Value |
|-------|-------|
| Current authority | `deployment/`, `infrastructure/`, `docker-compose.yml` |
| Status | DOCUMENTED ONLY |
| Entry point | ops |
| Source path | `deployment/` (linux/windows scripts), `infrastructure/` (aws/azure/gcp Terraform/Bicep), `docker-compose.yml` |
| Test/evidence path | none in CI |
| CI lane | `deploy.yml` exists but fails (issue #186: required secrets missing) |
| Known limitation | Not CI-verified; deployment secrets missing (issue #186); no staging target defined; no migration-from-zero test; no backup/restore test; no rollback test |
| Next certification requirement | Define staging target; create environment-specific threat model; provision isolated staging; run migration from zero; health checks; auth smoke test; tenant-isolation smoke test; WebSocket smoke test; secret-leak audit; backup/restore test; rollback test |
| Conflicting/superseded branches | None open |

---

## 11. Evidence / Claims Validation

| Field | Value |
|-------|-------|
| Current authority | `docs/governance/` + `mission-control-evidence/` + `docs/certification/` + `scripts/ci/validate_repository_claims.py` |
| Status | SUPPORTED (governance) |
| Entry point | `scripts/ci/validate_repository_claims.py` |
| Source path | `scripts/ci/validate_repository_claims.py`, `scripts/ci/report_test_inventory.py` |
| Test/evidence path | `scripts/ci/tests/test_validate_claims.py`, `scripts/ci/tests/test_report_inventory.py` |
| CI lane | `claims-validation` |
| Known limitation | Historical `PHASE_*.md` receipts are stale; certification evidence is increment-specific, not cumulative |
| Next certification requirement | Cumulative certification evidence index |
| Conflicting/superseded branches | None open |

---

## 12. Agent Runtime

| Field | Value |
|-------|-------|
| Current authority | `UNRESOLVED — convergence required` |
| Status | EXPERIMENTAL |
| Entry point | API/runtime |
| Source path | `agents/`, `agent_protocol/`, `core/universe`, `superintelligence/` |
| Test/evidence path | package tests (varies) |
| CI lane | Default `test` lane (partial) |
| Known limitation | No unified runtime authority; no standardized agent identity; no unified command authorization; no single execution receipt schema; no durable failure/cancellation semantics; Mission Control and scheduler do not agree on agent state |
| Next certification requirement | Standardize agent identity; unify command authorization; establish single execution receipt schema; durable failure/cancellation semantics; Mission Control and scheduler state agreement |
| Conflicting/superseded branches | PR #142 (AIOS second-brain) — CLOSE AS SUPERSEDED (111 behind, 229 files); PR #133 (ollama/slack fixes) — CLOSE AS SUPERSEDED (111 behind) |

---

## Unresolved authority conflicts

1. **Agent runtime** — no single authority across `agents/`, `agent_protocol/`, `core/universe`, `superintelligence/`.
2. **Execution control** — no single authority spanning API, workflow, and agent origins. Mission Control is refusal-only; `workflow_builder/` + `scheduler/` own execution truth; `secure_execution/` is not wired to RBAC.
3. **Payment authority** — `backend/stripe-payments/` vs `legal_integrations/` billing context; no unified authority.
4. **Document generation** — former `document_gen` missing; current pipeline unclear.
5. **Audit event logs** — multiple event logs exist (`MissionControlRunControlEvent`, `audit_records`, `audit_envelope`); unified schema pending.

---

## Next certification requirements (priority order)

1. Session/token lifecycle certification (revocation, rotation, logout invalidation, replay detection, key rotation, concurrent session policy, WebSocket invalidation on identity change, audit events for session termination)
2. Shared execution-control protocol (CommandEnvelope, ExecutionPrincipal, AuthorizationDecision, RunnerAcknowledgement, ExecutionTransition, FailureReceipt, CompensationReceipt, IdempotencyKey, CorrelationContext, AuditEvent, OperatorProjection)
3. Unified audit event schema
4. Distributed WebSocket enforcement
5. Payment authority unification + CI
6. Document generation authority restoration + contract tests
7. Frontend e2e behavior tests
8. Staging deployment certification
9. Blackstone dedicated CI lane + governed human review integration
10. Agent runtime convergence