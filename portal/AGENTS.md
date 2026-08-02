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
- `portal/scripts/migration_runner.py` is the reversible, ledgered migration runner (`schema_migrations` table, `NNNN_slug/up.sql` + mandatory `down.sql`, optional `<direction>.<dialect>.sql` overrides). It governs only migrations under a root passed with `--root`; it does not manage the legacy flat `portal/migrations/*.sql` corpus applied by `portal/scripts/postgresql_bootstrap.py`
- AI-OS versioned migrations live under `portal/migrations/ai_os/` and are governed by a local subtree contract in `portal/migrations/ai_os/AGENTS.md`
- Migration-runner behavior is covered by `portal/tests/test_migration_framework.py` using the fixture migrations in `portal/tests/support/migration_probe/`; the PostgreSQL case runs only when `AI_OS_MIGRATION_TEST_POSTGRES_URL` is set
- Rationale and alternatives: `docs/adr/ADR-0001-ai-os-migration-framework.md`

## Work Guidance

*(No project-specific standards yet — fill when engineering conventions emerge.)*

## Verification

*(No verification framework documented yet — fill when test/coverage thresholds exist.)*

## Child DOX Index

- `routers/` — API route handlers (FastAPI router modules)
- `migrations/ai_os/` — AI-OS versioned migrations and their local migration contract
