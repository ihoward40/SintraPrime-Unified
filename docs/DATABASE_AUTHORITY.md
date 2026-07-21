# Database and Migration Authority

Authoritative as of commit `48e2caa759661cc75617cc752bcc26eaad666647` (tree `9ee6d193dd7f607cd59487df9ef26d46b9593803`).

## Current schema sources
1. **SQLAlchemy models** — `portal/models/` (Base in `portal/database.py`). Define
   runtime ORM expectations.
2. **Raw-SQL migrations** — `portal/migrations/*.sql` (no Alembic):
   - `portal_schema.sql` (base)
   - `add_audit_records.sql`
   - `add_evidence_snapshots.sql`
   - `add_mission_control_command_ledger.sql`
   - `add_mission_control_run_control_projection.sql` (additive, PR #212)
   Applied by bootstrap/entrypoint in order.
3. **Test `create_all` path** — test suites build schema from models (SQLite in-memory
   or PostgreSQL via the lifecycle API). This is runtime-only and NOT the deployed
   schema.
4. **PostgreSQL CI path** — `portal/tests/test_mission_control_run_controls.py`
   builds from models via the lifecycle API; does not apply `portal/migrations/*.sql`.
5. **SQLite test path** — model `create_all` against in-memory SQLite.

## Certification lanes and database coverage boundary

PRs #214–#217 introduced three certification-specific CI lanes:
`auth-tenant-rbac-certification`, `audit-correlation-non-http-certification`,
and `http-correlation-ws-hardening-certification`. These lanes install
dependencies and run focused pytest suites. They do NOT provision a
PostgreSQL service, do NOT apply `portal/migrations/*.sql`, and do NOT
establish PostgreSQL schema or migration compatibility. Certification lane
evidence is recorded under `docs/certification/`.

PostgreSQL-specific evidence comes from the separate `postgresql-race` lane,
which proves Mission Control immutability and hash-chain integrity using the
lifecycle API. Database compatibility remains a separate certification
requirement.

## Schema on `main` vs open-PR proposals

The schema currently on `main` consists of the 5 migration SQL files listed above
and the SQLAlchemy models in `portal/models/`. Open PRs (e.g., #205, #206) may
contain schema proposals, but those are NOT part of `main` and must not be treated
as current schema authority. Historical local-only recovery work (e.g., lost
visual checkpoints) is not authoritative. Deployment database configuration
(production PostgreSQL, Redis, etc.) is described in `docs/DEPLOYMENT.md` but is
not CI-verified.

## Schema-drift risks
- Models vs `portal/migrations/*.sql` can diverge; the PG test lane uses models, not
  the SQL files. A model change not reflected in SQL migrations would pass tests but
  break deployment.
- Feature packages (`trust_law`, `backend/stripe-payments`, etc.) declare their own
  models; it is unclear whether they share one database or one migration path.

## Alembic status
**Absent.** Migration authority is raw ordered SQL. No versioned migration tooling exists.

## Current rule (release blocker)
> Models define runtime ORM expectations, while applied migrations define deployed
> schema reality. Any divergence is a release blocker.

## Recommended future convergence (NOT implemented here)
A future increment should introduce versioned migrations (Alembic or equivalent) so
that models, applied migrations, and CI schema build share one source of truth, with
a CI check that fails on model/migration divergence. This increment documents the
rule only; it makes no migration or model changes.