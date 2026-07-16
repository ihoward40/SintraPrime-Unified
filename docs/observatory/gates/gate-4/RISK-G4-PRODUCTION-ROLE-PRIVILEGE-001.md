# RISK-G4-PRODUCTION-ROLE-PRIVILEGE-001: Production Role Excessive Privileges

**Date:** 2026-07-16
**Severity:** Medium
**Status:** OPEN (deferred to later gate)
**Discovery:** Gate 4.6 stabilization review

## Finding

The `sintraprime` PostgreSQL role currently holds the following privileges:

| Privilege | Granted | Required for Application Runtime |
|-----------|---------|----------------------------------|
| SUPERUSER | Yes | No |
| CREATEDB | Yes | No (databases created by bootstrap role) |
| CREATEROLE | Yes | No (roles managed by provisioning scripts) |
| REPLICATION | Yes | No (no replication topology configured) |
| BYPASSRLS | Yes | No (Row Level Security not in use, and should not be bypassed) |

The `sintraprime` role is used by:
1. Docker entrypoint for initial database creation
2. Alembic migrations in production
3. Application runtime connections (via `DATABASE_URL`)

## Impact

- A compromised application connection could escalate to full database control
- SUPERUSER allows reading/writing any data, modifying roles, and accessing system catalogs
- BYPASSRLS would circumvent any future row-level security policies
- CREATEROLE allows privilege escalation to any other role

## Recommended Least-Privilege Replacement

| Role | Privileges | Purpose |
|------|-----------|---------|
| `sintraprime_admin` | LOGIN, CREATEDB, CREATEROLE | Schema migrations, admin tasks |
| `sintraprime_app` | LOGIN, NOCREATEDB | Application runtime (read/write data only) |
| `sintraprime_readonly` | LOGIN, NOCREATEDB | Reporting, monitoring |

SUPERUSER should only be held by the PostgreSQL superuser account used for cluster administration, never by application roles.

## Deferred Remediation

Remediation is deferred beyond Gate 4.6 because:
1. Changing the production role requires coordination with Docker Compose and application configuration
2. The role is embedded in `docker-compose.yml` as `POSTGRES_USER`
3. Alembic migrations currently run under this role
4. Production runtime changes require a separate authorization process

This risk is ACCEPTED for Gate 4.6 with the following conditions:
- Test roles (`sintraprime_test_runner`, `sintraprime_test_bootstrap`) are properly least-privilege
- Test roles cannot access production databases
- Test roles cannot escalate privileges
- Production role privileges are documented and tracked for remediation

## Remediation Plan (Future Gate)

1. Create `sintraprime_app` role with LOGIN, NOCREATEDB
2. Create `sintraprime_admin` role with LOGIN, CREATEDB, CREATEROLE
3. Update `DATABASE_URL` in production to use `sintraprime_app`
4. Update Alembic configuration to use `sintraprime_admin`
5. Remove SUPERUSER, REPLICATION, BYPASSRLS from `sintraprime`
6. Update `docker-compose.yml` to use separate init and runtime roles
7. Verify application functionality with least-privilege roles