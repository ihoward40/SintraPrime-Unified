# G4.6 Credential Provenance Report

## PostgreSQL Cluster Identity

| Property | Value |
|----------|-------|
| Container | sintraprime-postgres (f878fa31733a) |
| Image | postgres:15-alpine |
| Version | PostgreSQL 15.17 (Alpine) |
| Host port | 5433 → container 5432 |
| Data directory | /var/lib/postgresql/data/pgdata |
| Start time | 2026-07-14 17:11:43 UTC |
| pg_hba | Local: trust; Host 127.0.0.1: trust; Host all: scram-sha-256 |

## Identity Verification (4 channels)

All four channels resolve to the same cluster, port, and database:

| Channel | Database | User | Server Address | Server Port | Match |
|---------|----------|------|---------------|-------------|-------|
| psql (local) | gate4_test | sintraprime | (local) | 5432 | ✗ (different path) |
| asyncpg (host) | gate4_test | sintraprime_test_runner | 192.168.80.3 | 5432 | ✓ |
| SQLAlchemy (host) | gate4_test | sintraprime_test_runner | 192.168.80.3 | 5432 | ✓ |
| subprocess (host) | gate4_test | sintraprime_test_runner | 192.168.80.3 | 5432 | ✓ |

Note: psql uses local Unix socket (trust auth), host connections use Docker bridge (scram-sha-256).

## Credential Provenance Matrix

| Source | Variable | Loaded | Precedence | Host | Port | DB | User | Can Override |
|--------|----------|--------|------------|------|------|----|------|-------------|
| `.env` | `DATABASE_URL` | Yes (dotenv) | Low (app default) | N/A | N/A | sqlite | N/A | No (different purpose) |
| `.env.test` | `GATE4_TEST_DATABASE_URL` | Manual (source/.env.test) | **Authoritative** | localhost | 5433 | gate4_test | sintraprime_test_runner | Yes (test URL) |
| `.env.test` | `GATE4_TEST_ADMIN_DB` | Manual (source/.env.test) | **Authoritative** | localhost | 5433 | postgres | sintraprime_test_runner | Yes (admin URL) |
| Docker Compose | `POSTGRES_PASSWORD` | Container only | N/A (init-only) | N/A | N/A | N/A | sintraprime (superuser) | No |
| `docker-compose.yml` | `POSTGRES_USER` | Container only | N/A (init-only) | N/A | N/A | N/A | sintraprime | No |
| pytest fixtures | `GATE4_TEST_DATABASE_URL` | os.environ | **Authoritative** | (from env) | (from env) | (from env) | sintraprime_test_runner | No (reads only) |
| Alembic `env.py` | `DATABASE_URL` | os.environ | Production | (from env) | (from env) | (from env) | (from env) | No |
| db_bootstrap.py | `GATE4_TEST_DATABASE_URL` | os.environ | **Authoritative** | (from env) | (from env) | (from env) | sintraprime_test_runner | No (reads only) |
| db_bootstrap.py | `GATE4_TEST_ADMIN_DB` | os.environ | **Authoritative** | (from env) | (from env) | postgres | sintraprime_test_runner | No (reads only) |
| stress runner | Hardcoded URL | Hardcoded | **MUST UPDATE** | localhost | 5433 | gate4_test | sintraprime | N/A |

## Role Privileges

### sintraprime (PRODUCTION — DO NOT USE FOR TESTS)

| Privilege | Value |
|-----------|-------|
| LOGIN | Yes |
| SUPERUSER | Yes |
| REPLICATION | Yes |
| BYPASSRLS | Yes |
| CREATEDB | Yes |
| **Must NOT be used by test suite** | |

### sintraprime_test_runner (TEST — dedicated role)

| Privilege | Value |
|-----------|-------|
| LOGIN | Yes |
| SUPERUSER | No |
| REPLICATION | No |
| BYPASSRLS | No |
| CREATEDB | Yes |
| Connect to gate4_test | Yes |
| Connect to postgres (admin) | Yes |
| Connect to sintraprime_unified (production) | **BLOCKED** |
| Create/drop disposable databases | Yes |
| Read/write gate4_test tables | Yes |
| Alter roles | **BLOCKED** |
| Escalate privileges | **BLOCKED** |

## Root Cause of Previous Authentication Failures

The `sintraprime` role password was altered multiple times with `ALTER USER` during earlier sessions, creating credential drift between:
1. The Docker environment variable `POSTGRES_PASSWORD` (set at container creation)
2. The stored PostgreSQL role password (changed by ALTER USER)
3. The URL used by asyncpg in test fixtures (different in each session)

The fix: create a dedicated test role (`sintraprime_test_runner`) with a known, stable password that is never changed by ALTER USER, and store it in `.env.test` (excluded from Git).

## Residual Risks

1. `sintraprime_test_runner` has CREATEDB — it can create any database name, not just disposable test databases. A database naming convention check (`LIKE 'gate4_%'`) would be more restrictive but requires a custom PostgreSQL extension or trigger.
2. The `sintraprime` superuser password in Docker env is the original creation password — it should not be relied upon for tests.
3. The stress runner (`stress/gate4_ten_run_stress.py`) has a hardcoded URL that must be updated to use `sintraprime_test_runner`.