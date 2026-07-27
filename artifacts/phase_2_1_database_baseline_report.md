# Phase Two — Database Baseline Report (P2.1)

**Report ID:** DBL-2026-07-27-01
**Generated:** 2026-07-27T03:17:06.018648+00:00
**Repository:** SintraPrime-Unified
**Governance checkpoint:** `governance/blackstone/checkpoints/phase-1.5-ci-certification.md` (Phase 1.5 CLOSED)
**Status:** Baseline documented — architectural drift discovered; remediation decision required before schema modifications

---

## 1. Supported Database Engines

The project declares **PostgreSQL** as its primary and only supported relational database.

Evidence:
- `pyproject.toml` depends on `psycopg2-binary>=2.9.9` and `asyncpg>=0.29.0`.
- `portal/config.py` default `DATABASE_URL` is `postgresql+asyncpg://portal:portal@localhost:5432/sintra_portal`.
- `.github/workflows/ci.yml` runs a PostgreSQL 16 service container for integration tests.
- `portal/database.py` uses SQLAlchemy async engine with `create_async_engine` and PostgreSQL-specific RLS (`SET LOCAL`).

No SQLite, MySQL, or other backend configuration is present. **Scope: PostgreSQL only.**

---

## 2. Migration Tooling

| Tool | Status | Finding |
|---|---|---|
| Alembic | Dependency present in `pyproject.toml` (`alembic>=1.12.1`) | No operational configuration found |
| `portal/alembic/versions/` | Directory exists | **No `.py` migration source files present** |
| `portal/alembic/versions/__pycache__/` | Stale `.pyc` files only | Compiled from a different worktree (`C:\Users\admin\Desktop\SintraPrime-Unified\portal\alembic\versions\...`) |
| `alembic.ini` / `portal/alembic.ini` | Missing | No Alembic config file in repo |
| `portal/alembic/env.py` | Missing | No Alembic environment script in repo |
| Raw SQL migrations | Present | `portal/migrations/*.sql` |
| Bootstrap runner | Present | `portal/scripts/postgresql_bootstrap.py` applies `portal/migrations/*.sql` in order |

Conclusion: the project currently uses **raw SQL migrations** plus a Python bootstrap runner, not Alembic. The Alembic package is installed but unconfigured.

---

## 3. Migration History (Raw SQL)

| Order | File | Size | Purpose |
|---|---|---|---|
| 1 | `portal/migrations/portal_schema.sql` | 43,855 bytes | Multi-tenant client-portal base schema (25 tables) |
| 2 | `portal/migrations/add_evidence_snapshots.sql` | 4,432 bytes | Immutable evidence snapshot table + trigger |
| 3 | `portal/migrations/add_audit_records.sql` | 3,699 bytes | Immutable audit record table + trigger |
| 4 | `portal/migrations/add_mission_control_command_ledger.sql` | 5,582 bytes | Command ledger, events, receipts |
| 5 | `portal/migrations/add_mission_control_run_control_projection.sql` | 4,949 bytes | Run-control projection + events |

No downgrade SQL files exist. Downgrade instructions are embedded as comments in two files only (`add_audit_records.sql`, `add_evidence_snapshots.sql`).

---

## 4. Declared Schema vs. Actual Database Drift

### Declared schema (`portal/migrations/portal_schema.sql`)

- 25 tables: tenants, roles, users, clients, matters, cases, case_events, case_deadlines, case_notes, case_tasks, document_folders, documents, document_versions, document_shares, message_threads, messages, message_attachments, time_entries, expenses, invoices, invoice_line_items, payments, trust_accounts, notifications, audit_logs.
- Multi-tenant design with foreign keys, unique constraints, soft-delete columns, full-text-search indexes.
- Intended to be applied via `portal/scripts/postgresql_bootstrap.py`.

### Actual running database (Docker container `sintraprime-postgres`, PostgreSQL 15.17)

- 8 tables: agents, execution_history, knowledge_entries, messages, sessions, skills, swarms, users.
- Generic agent/skill runtime schema.
- No tenants, roles, cases, clients, matters, documents, billing, or trust tables.
- No connection to the declared portal schema.

### Impact

There is a **major schema drift** between the SQL source-of-truth and the live database used by other parts of the system. The existing PostgreSQL container appears to belong to a different subsystem (possibly `core/` or `agents/`) rather than the `portal/` module.

---

## 5. Actual Database Introspection

### Engine
- PostgreSQL 15.17 on x86_64-pc-linux-musl (Alpine 15.2.0)
- Container: `sintraprime-postgres` (image `postgres:15-alpine`)
- Host: `127.0.0.1:5433`
- Database: `sintraprime_unified`
- User: `sintraprime`

### Tables (8)

| Table | Columns | Purpose |
|---|---|---|
| agents | 7 | Agent registry |
| execution_history | 8 | Execution/job history |
| knowledge_entries | 7 | Knowledge store |
| messages | 8 | Message queue |
| sessions | 5 | User sessions |
| skills | 8 | Skill registry |
| swarms | 8 | Swarm registry |
| users | 7 | User accounts |

### Foreign Keys (3)

| Table | Column | References |
|---|---|---|
| execution_history | agent_id | agents(id) |
| execution_history | swarm_id | swarms(id) |
| sessions | user_id | users(id) |

### Unique Constraints (5)

| Table | Column |
|---|---|
| knowledge_entries | key |
| sessions | token |
| skills | name |
| users | email |
| users | username |

### Check Constraints

None found in the actual database.

### Indexes (15 non-primary, 4 primary)

| Table | Index | Type |
|---|---|---|
| agents | idx_agents_status | btree |
| agents | idx_agents_type | btree |
| execution_history | idx_execution_history_status | btree |
| knowledge_entries | idx_knowledge_key | gin_trgm_ops |
| messages | idx_messages_processed | btree |
| swarms | idx_swarms_status | btree |

### Nullable Columns Without Defaults

| Table | Column | Data Type |
|---|---|---|
| execution_history | result | jsonb |
| execution_history | agent_id | uuid |
| execution_history | swarm_id | uuid |
| execution_history | completed_at | timestamptz |
| knowledge_entries | source | varchar |
| messages | sender_id | uuid |
| messages | recipient_id | uuid |
| sessions | user_id | uuid |
| skills | description | text |
| skills | code | text |

(All other nullable columns have defaults.)

### Extensions

- `pg_trgm` 1.6
- `plpgsql` 1.0
- `uuid-ossp` 1.1

---

## 6. Declared Schema Introspection

### Tables (25)

See full list in Section 4. Key structural patterns:
- UUID primary keys with `uuid_generate_v4()`.
- `tenant_id` on tenant-scoped tables.
- `deleted_at` soft-delete columns.
- `created_at` / `updated_at` timestamps.
- JSONB `custom_fields`, `settings`, `metadata` columns.

### Foreign Keys (declared)

Examples:
- `users.tenant_id -> tenants(id) ON DELETE CASCADE`
- `users.role_id -> roles(id)`
- `clients.tenant_id -> tenants(id) ON DELETE CASCADE`
- `clients.primary_attorney_id -> users(id)`
- `cases.client_id -> clients(id) ON DELETE CASCADE`
- `evidence_snapshots.case_id -> cases(id) ON DELETE RESTRICT`
- `audit_records.snapshot_id -> evidence_snapshots(snapshot_id) ON DELETE RESTRICT`
- `mission_control_commands.tenant_id -> tenants(id)`
- `mission_control_commands.requested_by -> users(id)`
- `mission_control_commands.audit_log_id -> audit_logs(id)`

### CHECK Constraints (declared)

- `evidence_snapshots.status IN ('active', 'superseded', 'archived')`
- `audit_records.verification_status IN ('verified', 'failed')`
- `mission_control_commands.command_type` enumerated
- `mission_control_commands.state` enumerated
- `mission_control_run_controls.state` enumerated

### Indexes (declared)

- Per-tenant indexes (`ix_*_tenant_id`).
- Email/name lookup indexes.
- Full-text-search GIN indexes on `clients`, `cases`, `documents`.
- Partial indexes for active records (`WHERE deleted_at IS NULL`).
- Functional indexes for unique constraints.

---

## 7. Schema Inconsistencies

1. **Database identity mismatch:** The live PostgreSQL container does not contain the portal schema. It contains an unrelated agent runtime schema.
2. **Missing Alembic config:** Alembic is a dependency but has no `.ini`, `env.py`, or migration source files.
3. **No downgrade SQL files:** Only inline comments document downgrades; no tested reverse scripts.
4. **Stale compiled bytecode:** `portal/alembic/versions/__pycache__` contains `.pyc` files with paths from a different machine/directory, indicating deleted source files.
5. **Dual SQL schema sets:** Other SQL files exist outside `portal/migrations/` (`core/universe/db_migrations.sql`, `apps/ike-bot/main/supabase/migrations/*.sql`, `shared/schemas/unified_schema.sql`), suggesting historical divergence.
6. **No migration regression tests:** No dedicated test file verifies upgrade/downgrade sequences.

---

## 8. Existing Rollback Capabilities

| Migration File | Downgrade Provided |
|---|---|
| `portal_schema.sql` | No — schema is idempotent via `IF NOT EXISTS`, but no destructive rollback |
| `add_evidence_snapshots.sql` | Inline comments only |
| `add_audit_records.sql` | Inline comments only |
| `add_mission_control_command_ledger.sql` | No |
| `add_mission_control_run_control_projection.sql` | No |

Actual database rollback state: cannot be assessed until a target database is provisioned with the declared schema.

---

## 9. Test Coverage

| Area | Tests |
|---|---|
| PostgreSQL bootstrap schema authority | `portal/tests/test_postgresql_bootstrap_schema_authority.py` |
| PostgreSQL concurrency race | `.github/workflows/ci.yml` `postgresql-race` job |
| Migration upgrade/downgrade regression | **None** |
| Constraint enforcement tests | **None dedicated** |

---

## 10. Recommendations Before Schema Modifications

Given the discovered drift, any Phase Two schema work requires a decision on **which database is canonical**:

### Option A — Make the declared portal schema operational
1. Provision a fresh PostgreSQL database.
2. Apply `portal/migrations/*.sql` via `postgresql_bootstrap.py`.
3. Verify the live schema matches `portal_schema.sql`.
4. Add Alembic scaffolding and convert future migrations to Alembic.
5. Add migration regression tests.
6. Add `NOT NULL` / `CHECK` / `FK` / `UNIQUE` / index changes incrementally.

### Option B — Reconcile the live agent schema into a unified model
1. Document that the current live DB is the runtime agent store.
2. Determine whether `portal/` schema is aspirational/deprecated or a separate tenant-scoped module.
3. If both are needed, separate connection settings and migration paths.
4. Strengthen constraints on the live schema first (lower risk).

### Option C — Bounded Phase Two scope
1. Restrict Phase Two to **strengthening the live runtime schema** (`agents`, `execution_history`, `knowledge_entries`, `messages`, `sessions`, `skills`, `swarms`, `users`).
2. Add `NOT NULL` / `CHECK` / `FK` / indexes where justified.
3. Add migration scripts (raw SQL or Alembic) with downgrade steps.
4. Add regression tests.
5. Defer portal schema reconciliation to a later phase.

**Governance recommendation:** Choose Option C for Phase Two to keep the phase bounded and evidence-based, then schedule a separate architectural reconciliation phase for the portal schema.

---

## 11. Evidence Commands

```text
gh run view 30233866200 --repo ihoward40/SintraPrime-Unified
docker exec sintraprime-postgres psql -U sintraprime -d sintraprime_unified -c "SELECT version();"
docker exec sintraprime-postgres psql -U sintraprime -d sintraprime_unified -c "\dt public.*"
docker exec sintraprime-postgres psql -U sintraprime -d sintraprime_unified -c "SELECT * FROM information_schema.tables WHERE table_schema='public';"
find portal/alembic/versions -maxdepth 1 -type f
find . -maxdepth 3 -name alembic.ini
python portal/scripts/postgresql_bootstrap.py --help
```

---

## 12. Next Decision Required

Before P2.2 (Schema Integrity) proceeds, the repository owner must select **Option A, B, or C** above. Schema changes made without this decision risk either:
- modifying a schema that is not currently deployed (Option A), or
- ignoring the live database that other subsystems depend on (Option C).

**P2.1 status: COMPLETE**
**P2.2 status: BLOCKED pending scope decision**
