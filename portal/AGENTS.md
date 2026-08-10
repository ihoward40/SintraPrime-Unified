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
- **Migration authority (R3):** `MIGRATIONS_ARE_AUTHORITY` is the declared doctrine and is now enforced:
  - Alembic revision chain lives in `portal/alembic/versions/`; root config is `alembic.ini`
  - Canonical migration sequence is defined once in `portal/scripts/postgresql_bootstrap.py::MIGRATION_SEQUENCE` and mirrored in the Alembic baseline revision `a1b2c3d4e5f6`
  - Docker provisioning uses `shared/schemas/docker_init.sh` (mounts `portal/migrations/` read-only)
  - Deployment contract: **Option B** — migrations ship as source checkout (not bundled in wheel); see `evidence/r3-schema/R3_K_DEPLOYMENT_CONTRACT.md`
  - Adoption procedure for pre-R3 databases: `evidence/r3-schema/R3_N_ADOPTION_STRATEGY.md`
  - CI gate: `migration-authority-gate` job in `.github/workflows/ci.yml`

## Work Guidance

*(No project-specific standards yet — fill when engineering conventions emerge.)*

## Verification

*(No verification framework documented yet — fill when test/coverage thresholds exist.)*

## Child DOX Index

- `routers/` — API route handlers (FastAPI router modules)

## Persistent Matter Intelligence

Persistent matter intelligence is owned by `models/matter_intelligence.py`, `models/deadline_evidence.py`, the corresponding schemas/services, and their migrations. Records are tenant- and matter-scoped, soft-deleted where mutable, and sensitive values must be redacted before persistence and audit logging. Assessment and deadline versions are append-only; attorney approval is required for legal/evidence conclusions and accountant approval for tax/accounting assessments. Phase 2C-3 adds rule-provenance deadlines and immutable evidence graph links. Phase 2C-4 owns the frontend matter workspace; Phase 2C-5 owns redacted JSON/PDF packet exports, dedicated export authorization, canonical packet hashes, and export audit events.