# Database and Migration Authority

Authoritative as of commit 10cad07f046b5675ed10a1fba1aa4a955636f739.

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

