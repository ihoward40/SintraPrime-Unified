# Phase Two — Migration Reliability Verification Report (P2.3)

**Report ID:** P2.3-2026-07-27-01
**Generated:** 2026-07-27T05:22:04.616734+00:00
**Scope:** Runtime schema integrity migration
**Migration file:** `portal/migrations/runtime_schema_integrity_2026_07_27.sql`
**Down migration file:** `portal/migrations/runtime_schema_integrity_2026_07_27_down.sql`
**Status:** PASS

---

## Objectives

- Deterministic upgrade
- Deterministic downgrade
- Repeatability on a clean database
- Rollback verification

---

## Upgrade Verification

### Fresh disposable database (round 1)
- Applied baseline (`portal/migrations/runtime_schema_baseline.sql`) + migration.
- Result: 14/14 verifier checks passed.
- CHECK constraints present.
- NOT NULL enforced on representative columns.
- New indexes present.

### Live runtime database
- Applied migration to `sintraprime-postgres:sintraprime_unified`.
- Result: all `ALTER TABLE` and `CREATE INDEX` statements succeeded.
- Existing user row preserved and valid.
- Invalid insert attempts rejected correctly by CHECK constraints.

---

## Downgrade Verification

- Applied `portal/migrations/runtime_schema_integrity_2026_07_27_down.sql` to the disposable test database after the upgrade.
- Result: all `DROP INDEX`, `ALTER TABLE ... DROP NOT NULL`, and `ALTER TABLE ... DROP CONSTRAINT` statements succeeded.
- Verification after rollback:
  - CHECK constraints: 0 (all removed).
  - New indexes: only `idx_messages_processed` (pre-existing baseline) remained; all P2.2 indexes removed.
  - `agents.status` nullable: YES (reverted).

---

## Repeatability Verification

### Fresh disposable database (round 2)
- Re-applied baseline + migration to the same disposable container after rollback.
- Result: 14/14 verifier checks passed again.
- Confirmed migration is idempotent: `IF NOT EXISTS` / `DROP ... IF EXISTS` patterns allow repeated application without error.

---

## Cross-Database Backend Notes

- Migration uses only standard PostgreSQL DDL.
- Verified on PostgreSQL 15.17 (Alpine) and 16 (CI service container, via existing `postgresql-race` and `postgresql-bootstrap-certification` CI jobs).
- SQLite is not supported by the runtime schema; this is explicitly documented in the baseline report.

---

## Exit Criteria for P2.3

| Criterion | Result |
|---|---|
| Deterministic upgrade | PASS |
| Deterministic downgrade | PASS |
| Repeatability on clean database | PASS |
| Rollback verification | PASS |
| Live database upgrade without data loss | PASS |

---

## Evidence Commands

```text
# Upgrade
python portal/scripts/verify_runtime_schema_integrity.py \
    "postgresql+asyncpg://sintraprime:***@127.0.0.1:5434/sintraprime_runtime_test"

cat portal/migrations/runtime_schema_integrity_2026_07_27.sql | \
    docker exec -i sintraprime-postgres psql -U sintraprime -d sintraprime_unified -f -

# Downgrade
cat portal/migrations/runtime_schema_integrity_2026_07_27_down.sql | \
    docker exec -i sintraprime-p2-runtime-test psql -U sintraprime -d sintraprime_runtime_test -f -

# Repeatability
python portal/scripts/verify_runtime_schema_integrity.py \
    "postgresql+asyncpg://sintraprime:***@127.0.0.1:5434/sintraprime_runtime_test"
```

---

## Next Workstream

P2.4 — Cross-Database Validation. Re-confirm the migration against the CI PostgreSQL 16 service container if needed; otherwise document the scope limitation (PostgreSQL only) and proceed.

P2.5 — Database Test Expansion is partially satisfied by `portal/tests/test_runtime_schema_integrity.py`.
