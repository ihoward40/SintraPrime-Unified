# R3-K — Deployment Contract: Migration Artifact Strategy

## Decision: Option B — Migrations Ship as a Separate Provisioning Artifact

### Rationale

R2 established that the installed application wheel does not bundle migration
files (SQL files were not inside the wheel).  R3 formalizes this as a
deliberate architectural decision rather than an oversight.

Option A (migrations bundled with the app wheel) was considered and rejected
because:
- SQL migration files are large and change independently of the application code
- The wheel artifact is deployed to runtime environments that should not run
  DDL operations
- Bundling migrations creates a coupling between schema history and app releases

### Canonical Provisioning Path

```
git checkout <release-tag>   # or: use dedicated migrations repo
cd SintraPrime-Unified

# Option 1 — Alembic (production, CI, staging)
SQLALCHEMY_URL="postgresql://..." alembic -c alembic.ini upgrade head

# Option 2 — bootstrap script (disposable/test databases)
python -m portal.scripts.postgresql_bootstrap \
    --database-url "postgresql://..." \
    --reset-public-schema   # only for empty databases
```

### Environment Convergence

| Environment | Authority | Command |
|---|---|---|
| Local dev | Alembic | `alembic upgrade head` |
| CI (postgresql-race) | `Base.metadata.create_all` | via pytest fixture |
| CI (migration-authority-gate) | bootstrap script | `apply_migrations()` |
| CI (bootstrap-certification) | bootstrap script | `apply_migrations()` |
| Docker | shell init script | `docker_init.sh` → runs SQL files |
| Staging | Alembic | `alembic upgrade head` |
| Production-like | Alembic | `alembic upgrade head` |

All paths converge on the same canonical migration sequence defined in:
- `portal/scripts/postgresql_bootstrap.py::MIGRATION_SEQUENCE`
- `portal/alembic/versions/a1b2c3d4e5f6_r3_canonical_baseline.py::_SQL_SEQUENCE`
- `shared/schemas/docker_init.sh` (mounted into Docker init directory)

### What Is NOT Acceptable

- Cloning the source repo manually, finding SQL files, and running them in a
  guessed order
- Running `Base.metadata.create_all()` as the sole provisioning mechanism in
  non-test environments (missing: RLS, triggers, functions, non-ORM tables)
- Maintaining a second independent schema definition that diverges from the
  canonical sequence

### Verification Gate

The `migration-authority-gate` CI job enforces this contract on every PR.
It:
1. Provisions a fresh PostgreSQL database using `apply_migrations()`
2. Runs `test_orm_schema_drift.py` to verify all ORM tables are present and
   match the database schema
3. Verifies RLS is enabled on all required tables
4. Confirms idempotency (re-running migrations does not error)
