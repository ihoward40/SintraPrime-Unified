# portal — Client Portal

## Purpose

Owns the SintraPrime client portal — the FastAPI application that provides secure multi-tenant document vault, case management, billing, encrypted messaging, authentication/authorization, SSO, WebSocket realtime, and compliance features for law firm operations.

## Ownership

- Application entry point (`main.py`, `config.py`, `database.py`)
- All portal subdirectories: `auth/`, `models/`, `schemas/`, `routers/`, `services/`, `middleware/`, `websocket/`, `sso/`, `security/`, `migrations/`, `admin/`
- Portal-level tests in `portal/tests/` and `portal/sso/tests/`
- Portal-level router tests in `portal/routers/tests/`

## Local Contracts

- FastAPI async application with lifespan-managed services
- Infrastructure dependencies: PostgreSQL (async), Redis, MinIO (S3-compatible)
- 7 RBAC roles enforced at DB layer via Row-Level Security
- All changes must preserve: AES-256 encryption, immutable audit log, soft deletes
- No raw SQL in application code (SQLAlchemy ORM only; migrations exempt)
- JWT access tokens 15-min, refresh tokens 30d httpOnly cookie, TOTP MFA
- Runtime schema migrations live in `portal/migrations/` and must include inline DOWN migration comments or a separate `_down.sql` file

## Work Guidance

- Portal-wide HTTP authentication is enforced by `middleware/auth_middleware.py` and installed in `main.py`; public routes must be exact allowlist entries or narrowly scoped prefix entries with tests. Never use a root `startswith("/")` style public check.
- Production configuration must fail closed when default secrets, local object storage endpoints, insecure MinIO transport, or placeholder encryption/session keys remain configured. Development may use deterministic local defaults only outside production.
- Tenant-scoped database sessions must activate PostgreSQL RLS settings from verified request/user context. Maintain both `app.current_*` and legacy `app.*` session variables until all migrations converge on one naming convention.
- Orchestration run projections and document packet provenance are durable DB-backed service concerns. Do not reintroduce process-memory storage for protected run retrieval, packet snapshots, or packet audit records except as explicit injected test doubles.
- JWT revocation must be checked anywhere an access token is accepted, including middleware and `get_current_user`.

## Verification

- Auth, tenant isolation, revocation, production secret gates, public route allowlisting, and RLS activation are certified in `portal/tests/test_auth_tenant_rbac_certification.py`. Run that focused suite after portal auth, config, middleware, or database-session changes.
- Durable orchestration persistence, document packet provenance, and transactional audit behavior are certified in `portal/tests/test_orchestration_api.py`, `portal/tests/test_document_export_endpoint.py`, and `portal/tests/test_persistence_audit_correctness.py`.
- Governed external action (JARVIS-001-B1) is certified in `portal/tests/test_jarvis_b1_governed_action.py`. Run it after any change to the `jarvis_action_*` services or the GitHub label adapter. Its contracts below are constitutional for JARVIS agency work.

## Governed External Actions (JARVIS-001-B1)

- The only mutation boundary is `services/jarvis_action_executor.py` (`GovernedActionExecutor`). No other component may perform an external mutation; INTELLIGENCE != AUTHORITY holds at that boundary.
- Proposed actions are frozen, allowlisted (`github.issue.add_label` only for B1), params-hash-bound, and tenant/mission/request-bound (`services/jarvis_proposed_action.py`).
- Approvals are action-bound artifacts (`services/jarvis_action_approval.py`): PENDING -> APPROVED -> CONSUMED, single-consume, params-hash bound, tenant-bound. Nova-style dict approvals are never authority. Consume happens only after independent post-state verification (or timeout reconciliation proving the effect landed).
- Mutation credentials never enter worker environments (`services/jarvis_action_credential_isolation.py` filters them), never appear in receipts/memory/logs, and flow only authority_context -> adapter -> provider at the execution boundary.
- Provider responses are never proof: pre-state capture, mutation, post-state refetch, canonical comparison. Provider timeout -> refetch -> reconcile; never an automatic second POST; undeterminable state is VERIFICATION_INCONCLUSIVE / SIDE_EFFECT_UNKNOWN, never fabricated success.
- Receipts extend the hash-chain architecture with pre/post state hashes, authority, and tamper detection (`services/jarvis_action_receipt.py`).
- The A-chain (`jarvis_principal_mission`, read-only workflow, memory writeback, a4 acceptance) is frozen: B1 services must not modify it.

## Child DOX Index

- `routers/` — API route handlers (FastAPI router modules)
- `services/orchestration/` — adaptive orchestration service contracts, policies, routing, verification, reconciliation, and mock-provider execution

## Persistent Matter Intelligence

Persistent matter intelligence is owned by `models/matter_intelligence.py`, `models/deadline_evidence.py`, the corresponding schemas/services, and their migrations. Records are tenant- and matter-scoped, soft-deleted where mutable, and sensitive values must be redacted before persistence and audit logging. Assessment and deadline versions are append-only; attorney approval is required for legal/evidence conclusions and accountant approval for tax/accounting assessments. Phase 2C-3 adds rule-provenance deadlines and immutable evidence graph links. Phase 2C-4 owns the frontend matter workspace; Phase 2C-5 owns redacted JSON/PDF packet exports, dedicated export authorization, canonical packet hashes, and export audit events.