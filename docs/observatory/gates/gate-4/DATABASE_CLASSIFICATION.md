# G4.6 Database Classification

## All Databases in Cluster

| Database | Owner | Classification | test_runner Access | test_bootstrap Access |
|----------|-------|---------------|-------------------|----------------------|
| postgres | sintraprime | ADMINISTRATIVE | CONNECT (for admin queries) | CONNECT (for CREATE DATABASE) |
| sintraprime | sintraprime | PRODUCTION (legacy name) | **BLOCKED** | **BLOCKED** |
| sintraprime_unified | sintraprime | PRODUCTION | **BLOCKED** | **BLOCKED** |
| gate4_test | sintraprime | DISPOSABLE TEST | Full access (read/write/create tables) | CONNECT + CREATE schema |
| gate4_clean | sintraprime | DISPOSABLE TEST (stale) | Not yet configured | Not yet configured |
| gate3_bootstrap | sintraprime | DISPOSABLE TEST (stale, from Gate 3) | Not yet configured | Not yet configured |
| gate4_stress_1 | sintraprime | DISPOSABLE TEST (stale, from stress run) | Not yet configured | Not yet configured |
| gate4_stress_run_1 | sintraprime | DISPOSABLE TEST (stale, from stress run) | Not yet configured | Not yet configured |
| template0 | sintraprime | SYSTEM | No access | No access |
| template1 | sintraprime | SYSTEM (default) | No access | No access |

## Protected Databases

The following databases MUST NOT be accessible to test roles:

1. **sintraprime** — Legacy production database (no test role CONNECT)
2. **sintraprime_unified** — Current production database (REVOKE CONNECT from PUBLIC, GRANT only to sintraprime)
3. **template0** — System template (no test role access)
4. **template1** — System template (no test role access)

## Disposal Candidates

The following databases are stale disposable test databases that should be cleaned up:
- gate3_bootstrap
- gate4_clean
- gate4_stress_1
- gate4_stress_run_1

## Note on CREATEDB Scope

`sintraprime_test_bootstrap` has CREATEDB privilege, which permits creating databases with arbitrary names.
This is a broader-than-desired privilege — PostgreSQL does not support restricting CREATEDB to a naming pattern.
Application-level enforcement in `db_bootstrap.py` validates that database names match `gate4_*`, `sintraprime_test_*`,
`tmp_test_*`, or `test_*` patterns before creation. This is documented as a residual risk.