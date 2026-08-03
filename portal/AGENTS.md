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

*(No project-specific standards yet — fill when engineering conventions emerge.)*

## Verification

*(No verification framework documented yet — fill when test/coverage thresholds exist.)*

## Child DOX Index

- `routers/` — API route handlers (FastAPI router modules)

## Persistent Matter Intelligence

Phase 2C-2 persistence is owned by `models/matter_intelligence.py`, `schemas/matter_intelligence.py`, `services/matter_intelligence_service.py`, and `migrations/add_matter_intelligence.sql`. Records are tenant- and matter-scoped, soft-deleted where mutable, and sensitive values must be redacted before persistence and audit logging. Assessment versions are append-only; attorney approval is required for legal assessments and accountant approval for tax/accounting assessments. This increment does not include deadlines, evidence-graph relationships, frontend matter views, or export generation.