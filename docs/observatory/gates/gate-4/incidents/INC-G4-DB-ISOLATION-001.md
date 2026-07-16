# Incident Report: INC-G4-DB-ISOLATION-001

## Title
Test suite observed operational database state due to insufficient test-database isolation

## Date
2026-07-15

## Severity
Medium — no data corruption confirmed, but the test configuration could observe and potentially depend on operational state

## Status
Resolved — isolation guard implemented and verified

## Summary

During Gate 4.6 testing, five PostgreSQL tests failed when the test runner was configured with `GATE4_TEST_DATABASE_URL` pointing at the production-like `sintraprime` database rather than a disposable test database. The failures revealed that the prior test configuration could observe or depend on operational database state, including stale kill-switch rows.

## Affected Tests

1. `test_gate4_hardening.py::TestPostgreSQLConcurrency::test_pg_clear_deactivates_state`
2. `test_gate4_hardening.py::TestPostgreSQLConcurrency::test_pg_partial_unique_index_exists`
3. `test_gate4_hardening.py::TestPostgreSQLConcurrency::test_pg_concurrent_activation_no_pending_rollback`
4. `test_migration_backfill.py::TestMigrationBackfill::test_hash_version_backfill_postgresql`
5. (5th failure was a collection-time error from the above)

## Stale State Involved

The `sintraprime` production-like database contained **2 active kill-switch rows** in `observatory_kill_switch_state`, violating the intended single-active-row invariant enforced by the partial unique index `uq_observatory_single_active_kill_switch`.

The partial unique index exists on the production database, but the duplicate rows were likely created before the index was applied, or through a path that bypassed the constraint (e.g., `create_all()` before migration head was reached).

## Why the Clean Disposable Database Passed

When the same tests were re-run against `gate4_test` (a disposable PostgreSQL database freshly migrated with `alembic upgrade head`):
- The kill-switch table had exactly 1 active row (or 0 rows)
- No stale test data existed
- All 12 concurrency tests passed
- All 3 hardening tests passed
- The migration backfill test passed

The disposable database had a clean schema with the partial unique index correctly enforced from the start.

## Did Any Test Modify the Production-Like Database?

**Potentially yes.** The PG concurrency tests in `test_gate4_pg_concurrency.py` perform:
- `DELETE FROM observatory_*` (clean_pg_tables) before and after each test
- `INSERT` operations for concurrent event submission
- `Base.metadata.create_all()` calls

If the tests had proceeded past the connection check (which some did before the failures), they would have cleaned and populated tables in the `sintraprime` database. The `clean_pg_tables` function deletes all rows from observatory tables.

**Confirmation:** The test failures occurred at assertion time (e.g., "Expected 1 active row, got 2"), meaning the tests had already connected to and queried the production-like database. The `clean_pg_tables` function may or may not have been called before the assertions failed.

## Whether Any Operational Records Were Deleted or Changed

**Not confirmed.** The test suite was stopped before full completion. The `clean_pg_tables` call happens inside the `pg_engine` fixture's setup and teardown. If the fixture setup ran, it would have deleted all rows from observatory tables. However, the failures suggest the tests reached the assertion phase, meaning the fixture setup (including `clean_pg_tables`) likely executed.

## Corrective Measures

### 1. Test Database Isolation Guard (`portal/tests/test_db_guard.py`)

A comprehensive guard module was implemented that enforces all of the following conditions before any destructive test can run:

1. **Database name must match an approved disposable pattern** (gate4_test, gate4_clean, gate3_bootstrap, sintraprime_test_*, tmp_test_*, test_*)
2. **Explicit test-environment variable must be set** (`GATE4_TEST_MODE=true`)
3. **Production mode must be false** (URL must not match `DATABASE_URL` env var)
4. **Database name must not be in the prohibited list** (sintraprime, production, prod, staging, stage)
5. **Test marker table must exist** in the target database (`__gate4_test_marker`)
6. **Socket reachability check** before connection

If any check fails, the guard raises `DatabaseIsolationError` and sets `PG_URL = None`, causing all PG tests to **skip** (not error, not connect).

### 2. Guard Wired Into All PG Test Files

- `test_gate4_hardening.py` — PG_URL validation at import time
- `test_gate4_pg_concurrency.py` — PG_URL validation at import time + None check in each fixture
- `test_migration_backfill.py` — Uses centralized `validate_test_database_url()` instead of local check

### 3. Fixture Factory Pattern

The concurrency test file was refactored to use a `_make_pg_fixture(pool_size, max_overflow)` factory, eliminating duplicated fixture code and ensuring every fixture has the None guard.

### 4. Isolation Guard Tests (`portal/tests/test_db_guard_isolation.py`)

40 tests proving:
- Disposable test database accepted
- Production database rejected
- Missing test marker rejected
- Missing explicit test flag rejected
- Similar-looking but unauthorized database name rejected
- Multiple failures all reported (not just first)
- URL matching logic (same host/port/db, different ports, different databases)
- Case-insensitive name matching

## Residual Risk

1. **The stale kill-switch rows in the `sintraprime` database have not been remediated.** They remain as evidence of the incident. A separate remediation plan is required (see item 7: Production-state readiness audit).

2. **The test marker table** (`__gate4_test_marker`) is created lazily by the guard on first connection. A database that was previously authorized could have the marker table even after its purpose changes. The marker should be verified as part of the database setup, not just existence.

3. **The guard currently skips marker checks for import-time validation** (to avoid blocking test discovery when the DB is down). Full marker checks happen at fixture time. If a fixture doesn't call the full guard, it could still connect.

4. **SQLite tests are not affected by this guard** — they use in-memory databases. However, the migration backfill test's SQLite guard remains unchanged and is adequate.

## Root Cause

The test files used `os.environ.get("GATE4_TEST_DATABASE_URL")` directly without validating that the URL pointed to a disposable database. The only protection was a name-pattern check in `test_migration_backfill.py` that checked for disposable name substrings. The hardening and concurrency tests had no protection at all — any URL, including the production database URL, would be accepted.

## Lesson

Test-database isolation is not optional. The test suite must refuse to run destructive operations against any database that has not been explicitly marked as disposable and authorized for testing. The cost of a mistake here is data loss in a production-like environment.
