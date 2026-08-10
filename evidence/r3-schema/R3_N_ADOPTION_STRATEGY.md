# R3-N — Existing Database Baseline Adoption Strategy

## Purpose

Before claiming the migration system production-capable, this document defines
the safe adoption procedure for databases that already match the canonical
schema (or a partial subset of it) but have no Alembic migration history.

## Background

R3 establishes the first Alembic revision (`a1b2c3d4e5f6`).  Any database
provisioned before R3 was bootstrapped via raw SQL and has no `alembic_version`
record.  Running `alembic upgrade head` on such a database would re-execute
all SQL — which is safe for most objects (IF NOT EXISTS guards) but would fail
for any object that cannot be created idempotently (e.g., named constraints,
RLS policies without IF NOT EXISTS).

## Adoption Procedure

**Do NOT run against a real production database.**  Test against a disposable
clone-equivalent before executing on any live system.

### Step 1 — Verify the existing database matches the canonical schema

```bash
python -m portal.scripts.postgresql_bootstrap --database-url "$DATABASE_URL" --print-sequence
# Then check existing tables via psql:
psql "$DATABASE_URL" -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"
```

### Step 2 — Stamp the existing database at the baseline revision

If the database schema matches the canonical R3 baseline, stamp it rather than
re-migrating:

```bash
SQLALCHEMY_URL="$DATABASE_URL" alembic -c alembic.ini stamp a1b2c3d4e5f6
```

This inserts a row into `alembic_version` without executing any migration SQL.
The database is now tracked by Alembic and future `alembic upgrade head` calls
will only apply revisions newer than `a1b2c3d4e5f6`.

### Step 3 — Verify the stamp succeeded

```bash
SQLALCHEMY_URL="$DATABASE_URL" alembic -c alembic.ini current
# Expected output: a1b2c3d4e5f6 (head)
```

### Step 4 — Apply any revisions added after R3

```bash
SQLALCHEMY_URL="$DATABASE_URL" alembic -c alembic.ini upgrade head
```

## Schema Mismatch Handling

If the existing database is **missing tables** (e.g., it was provisioned before
some `add_*.sql` files were added):

1. Identify missing tables by comparing against `EXPECTED_TABLES` in
   `portal/scripts/postgresql_bootstrap.py`.
2. Apply only the missing migration SQL files manually (in canonical order),
   or run `apply_migrations` with `reset_public_schema=False` to apply
   all migrations idempotently.
3. Stamp at `a1b2c3d4e5f6`.

If the existing database has **extra tables** not in the canonical schema:

1. Check the intentional allowlist in `portal/tests/test_orm_schema_drift.py`.
2. If the extra table is legitimate, add it to the allowlist with a comment.
3. If the extra table is obsolete, schedule a targeted DROP in a new revision.

## Safety Properties

- All SQL migration files use `CREATE TABLE IF NOT EXISTS` — re-execution is safe.
- Index creation uses `CREATE INDEX IF NOT EXISTS` — re-execution is safe.
- RLS `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` is idempotent.
- `CREATE OR REPLACE FUNCTION` and `CREATE TRIGGER` with explicit `DROP TRIGGER IF EXISTS` 
  are idempotent.
- The stamp procedure does not execute any DDL — it is read-then-write on
  `alembic_version` only.

## Risks

| Risk | Mitigation |
|---|---|
| Named constraint already exists under a different definition | Inspect before stamping; use `DROP CONSTRAINT IF EXISTS` + `ADD CONSTRAINT` in a dedicated revision |
| RLS policy already exists with a different rule | `DROP POLICY IF EXISTS` before `CREATE POLICY` is already in the affected SQL files |
| Duplicate role seeds in `roles` table | `ON CONFLICT (name) DO NOTHING` guards are in `portal_schema.sql` |
| Data loss from accidental `reset_public_schema=True` | Never pass `--reset-public-schema` against a populated database |

## Validation Against Disposable Clone

Before adopting against any live system, validate the procedure against a
pg_dump clone:

```bash
pg_dump "$PROD_DB_URL" | psql "$CLONE_DB_URL"
# then stamp and verify:
SQLALCHEMY_URL="$CLONE_DB_URL" alembic -c alembic.ini stamp a1b2c3d4e5f6
SQLALCHEMY_URL="$CLONE_DB_URL" alembic -c alembic.ini upgrade head
python -m portal.scripts.postgresql_bootstrap --database-url "$CLONE_DB_URL" --print-sequence
# Run drift tests:
POSTGRESQL_BOOTSTRAP_TEST_DATABASE_URL="$CLONE_DB_URL" python -m pytest portal/tests/test_orm_schema_drift.py -v
```
