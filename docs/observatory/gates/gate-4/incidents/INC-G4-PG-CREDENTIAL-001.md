# INC-G4-PG-CREDENTIAL-001: PostgreSQL Test Credential Drift and Disclosure

**Date:** 2026-07-16
**Severity:** High — credential drift and plaintext disclosure
**Status:** Resolved (corrective action taken, production password rotated twice)
**Discovery Phase:** G4.6 stabilization — database guard marker validation

## Summary

During G4.6 stabilization, the `sintraprime` PostgreSQL role could not
authenticate to the `gate4_test` database via asyncpg. The root cause was
**credential drift**: the password stored in PostgreSQL did not match what
was being supplied in the `GATE4_TEST_DATABASE_URL` environment variable.

An initial incorrect diagnosis attributed the failure to URL encoding. The
actual root cause was that `ALTER USER` statements in previous sessions changed
the stored password away from the Docker-configured value, and subsequent test
runs used a different assumed password.

**Disclosure incident:** During the investigation, a previous iteration of
this incident report contained a plaintext production-role password. That
credential has been rotated. No plaintext passwords appear in current reports,
source files, or Git artifacts.

## Role Affected

- **Role:** `sintraprime` (production superuser)
- **Container:** `sintraprime-postgres` (port 5433)
- **Databases:** `sintraprime_unified` (production), `gate4_test` (disposable test)

## Whether Production Was Affected

- The `ALTER USER` command was executed against the running PostgreSQL instance,
  affecting the role globally — including the production database.
- **No production data was modified.** The password change affects authentication
  only.
- The production application uses `sqlite+aiosqlite` as its primary database.
  The PostgreSQL `sintraprime_unified` database is used only for the observatory
  module in development/test contexts.
- **Disclosure risk:** The production password was included in a diagnostic
  report. It has been rotated. No services should be using the disclosed value.

## Root Cause

Credential drift between three sources:

1. Docker environment variable `POSTGRES_PASSWORD` (set at container creation).
2. PostgreSQL stored password (modified by `ALTER USER` in multiple sessions).
3. `GATE4_TEST_DATABASE_URL` environment variable (assumed different values
   across sessions).

Each source diverged independently. No single authoritative credential store
existed.

## Corrective Action Taken

1. Production password rotated twice (once for the initial drift, once for the
   disclosure). Neither the old nor new values are recorded in any file.
2. A dedicated `sintraprime_test_runner` role created with restricted
   privileges (LOGIN, CREATEDB, NO SUPERUSER, NO REPLICATION, NO BYPASSRLS).
3. CONNECT revoked on `sintraprime_unified` (production) for the test role.
4. `GATE4_TEST_DATABASE_URL` is now the single authoritative source for test
   credentials, loaded from `.env.test` (excluded from Git).
5. `.env.test.example` contains only `REDACTED` placeholders.
6. All source files updated to load passwords from environment variables with
   fail-closed behavior (raise `RuntimeError` if absent, not empty-string default).

## Secret Rotation Procedure

1. Generate a hex-only secret: `python -c "import secrets; print(secrets.token_hex(24))"`
2. Set it via psql inside the container (trust auth): `docker exec <container> psql -U sintraprime -c "ALTER USER <role> WITH PASSWORD '<secret>';"`
3. Update `.env.test` with the new secret (never commit to Git).
4. Verify connectivity via asyncpg from the host (through Docker bridge,
   which uses `scram-sha-256`, NOT through localhost trust).
5. Verify incorrect passwords are REJECTED (negative authentication test).
6. Restart any dependent services.

## Residual Risks

- The `sintraprime_test_runner` role has `CREATEDB`, which permits creation of
  databases with arbitrary names. This is broader than desired but is required
  for the bootstrap lifecycle. Application-level name checks enforce the
  `gate4_*` naming convention, but PostgreSQL does not restrict the privilege
  itself. This is documented as a broader-than-desired privilege.
- The Docker `POSTGRES_PASSWORD` environment variable and the `sintraprime`
  role password may drift on container recreation. A declarative role management
  script is recommended.

## Evidence

- Successful authentication via asyncpg from host (scram-sha-256 path).
- Successful rejection of incorrect passwords (negative authentication test).
- 30/30 authentication diagnostic passes (10 asyncpg + 10 SQLAlchemy + 10 subprocess).
- No plaintext passwords in current source files, test output, or Git artifacts.