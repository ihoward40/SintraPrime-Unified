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
- JWT revocation must be checked anywhere an access token is accepted, including middleware and `get_current_user`.

## Verification

- Auth, tenant isolation, revocation, production secret gates, public route allowlisting, and RLS activation are certified in `portal/tests/test_auth_tenant_rbac_certification.py`. Run that focused suite after portal auth, config, middleware, or database-session changes.

## Child DOX Index

- `routers/` — API route handlers (FastAPI router modules)
- `services/orchestration/` — adaptive orchestration service contracts, policies, routing, verification, reconciliation, and mock-provider execution

## Persistent Matter Intelligence

Persistent matter intelligence is owned by `models/matter_intelligence.py`, `models/deadline_evidence.py`, the corresponding schemas/services, and their migrations. Records are tenant- and matter-scoped, soft-deleted where mutable, and sensitive values must be redacted before persistence and audit logging. Assessment and deadline versions are append-only; attorney approval is required for legal/evidence conclusions and accountant approval for tax/accounting assessments. Phase 2C-3 adds rule-provenance deadlines and immutable evidence graph links. Phase 2C-4 owns the frontend matter workspace; Phase 2C-5 owns redacted JSON/PDF packet exports, dedicated export authorization, canonical packet hashes, and export audit events.