# G4.6 Stale Database Disposition

## Disposition Table

| Database | Owner | Migration | Marker | Tables | Size | Purpose | Recommendation |
|----------|-------|-----------|--------|--------|------|---------|----------------|
| gate4_clean | sintraprime | 905b70986558 | **NONE** | 11 | 7975 kB | Gate 4 cleanup test | UNMARKED — guard must block. Archive and delete. |
| gate3_bootstrap | sintraprime | 905b70986558 | **NONE** | 40 | 9967 kB | Gate 3 bootstrap test | UNMARKED — guard must block. Archive and delete. |
| gate4_stress_1 | sintraprime | **NONE** | **NONE** | 0 | 7551 kB | Stress test run 1 | Empty DB, no migration. Delete. |
| gate4_stress_run_1 | sintraprime | **NONE** | **NONE** | 0 | 7551 kB | Stress test run 1 | Empty DB, no migration. Delete. |

## Evidence Dependencies

No evidence packages depend on these databases. All test evidence for Gate 4
is stored in `docs/observatory/gates/gate-4/` and verified against `gate4_test`.

## Guard Behavior

The database guard MUST block connections to all four stale databases because:
1. None have the `__gate4_test_marker` table
2. Without a valid marker, the guard classifies them as unmarked/invalid
3. This is the correct fail-closed behavior

## Disposition Action (requires authorization)

Before deletion, each database should be:
1. Dumped to a compressed SQL archive (`pg_dump | gzip > archive.sql.gz`)
2. Archived to `docs/observatory/gates/gate-4/archives/`
3. Dropped by the `sintraprime_test_bootstrap` role

**Do not delete without explicit authorization from the project lead.**