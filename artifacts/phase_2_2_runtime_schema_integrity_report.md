# Phase Two — Runtime Schema Integrity Verification Report (P2.2)

**Report ID:** P2.2-2026-07-27-01
**Generated:** 2026-07-27T05:18:45.174602+00:00
**Scope:** Live 8-table runtime schema in `sintraprime-postgres`
**Option:** C (bounded runtime-only stabilization)
**Migration file:** `portal/migrations/runtime_schema_integrity_2026_07_27.sql`
**Baseline file:** `portal/migrations/runtime_schema_baseline.sql`
**Status:** PASS

---

## Migration Applied

### Fresh disposable database
- Container: `sintraprime-p2-runtime-test` (PostgreSQL 15.17)
- Database: `sintraprime_runtime_test`
- Method: `python portal/scripts/verify_runtime_schema_integrity.py`
- Result: **14/14 checks passed**

### Live runtime database
- Container: `sintraprime-postgres` (PostgreSQL 15.17)
- Database: `sintraprime_unified`
- Method: `cat portal/migrations/runtime_schema_integrity_2026_07_27.sql | docker exec -i sintraprime-postgres psql -U sintraprime -d sintraprime_unified -f -`
- Result: **Success** — all ALTER TABLE and CREATE INDEX statements completed without error.
- Existing user row preserved and remains valid.

---

## CHECK Constraints Added

| Table | Constraint | Definition |
|---|---|---|
| agents | ck_agents_status | `status IN ('idle', 'active', 'paused', 'stopped', 'failed')` |
| execution_history | ck_execution_history_status | `status IN ('pending', 'running', 'completed', 'failed', 'cancelled')` |
| swarms | ck_swarms_status | `status IN ('initializing', 'active', 'paused', 'dissolved', 'failed')` |
| messages | ck_messages_priority | `priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')` |
| knowledge_entries | ck_knowledge_entries_confidence | `confidence >= 0.0 AND confidence <= 1.0` |

---

## NOT NULL Columns Enforced

| Table | Columns |
|---|---|
| agents | status, config, created_at, updated_at |
| execution_history | status, started_at |
| knowledge_entries | confidence, created_at, updated_at |
| messages | priority, processed, created_at |
| sessions | created_at |
| skills | parameters, version, enabled, created_at |
| swarms | status, config, agent_ids, created_at, updated_at |
| users | is_active, created_at |

---

## Indexes Added

| Index | Table/Columns |
|---|---|
| idx_messages_sender_id | messages(sender_id) |
| idx_messages_recipient_id | messages(recipient_id) |
| idx_execution_history_agent_id | execution_history(agent_id) |
| idx_execution_history_swarm_id | execution_history(swarm_id) |
| idx_sessions_user_id | sessions(user_id) |
| idx_users_is_active | users(is_active) |
| idx_knowledge_entries_source | knowledge_entries(source) |

---

## Remaining Nullable Columns (Justified)

| Table | Column | Justification |
|---|---|---|
| execution_history | result | Optional; may be NULL for pending jobs |
| execution_history | agent_id | Optional; job may not yet be assigned to an agent |
| execution_history | swarm_id | Optional; job may not belong to a swarm |
| execution_history | completed_at | Optional; NULL until job completes |
| knowledge_entries | source | Optional provenance metadata |
| messages | sender_id | Optional for system-generated messages |
| messages | recipient_id | Optional for broadcast messages |
| sessions | user_id | Anonymous/session-only sessions allowed |
| skills | description | Optional documentation field |
| skills | code | Optional for declarative/config-only skills |
| users | email | Retained nullable to avoid breaking existing rows; should be revisited if email becomes mandatory |
| users | role | Retained nullable; existing row has value but schema allows future extension |

---

## Regression Tests

File: `portal/tests/test_runtime_schema_integrity.py`

| Test | Result |
|---|---|
| test_runtime_schema_integrity_migration | PASS |
| test_agents_status_check | PASS |
| test_messages_priority_check | PASS |
| test_knowledge_entries_confidence_check | PASS |
| test_agents_status_not_null | PASS |

All 5 tests pass against the disposable test database.

---

## Rollback Path

Inline DOWN migration is provided in `portal/migrations/runtime_schema_integrity_2026_07_27.sql`. It includes:
- `DROP INDEX IF EXISTS` for each new index.
- `ALTER TABLE ... ALTER COLUMN ... DROP NOT NULL` for each tightened column.
- `ALTER TABLE ... DROP CONSTRAINT IF EXISTS` for each new CHECK constraint.

Rollback was validated by syntax review and by verifying each object name is correct. Full rollback execution will be performed during the final certification run to confirm reversibility.

---

## Cross-Platform Notes

- Migration uses only standard PostgreSQL DDL (`ALTER TABLE`, `CREATE INDEX`, `CHECK` constraints).
- No Windows-specific paths or local `.venv` assumptions in migration.
- Verified on PostgreSQL 15.17 (Alpine container) and 16 (CI service container, via existing CI jobs).

---

## Exit Criteria for P2.2

| Criterion | Result |
|---|---|
| Live runtime schema audited | PASS |
| Integrity improvements implemented | PASS |
| CHECK constraints added with evidence | PASS |
| NOT NULL constraints tightened | PASS |
| Indexes added for FK/common lookups | PASS |
| Migration deterministic (raw SQL with IF NOT EXISTS) | PASS |
| Rollback path documented | PASS |
| Regression tests pass | PASS (5/5) |
| Live database migration successful | PASS |
| Existing data preserved | PASS |

---

## Evidence Commands

```text
python portal/scripts/verify_runtime_schema_integrity.py \
    "postgresql+asyncpg://sintraprime:***@127.0.0.1:5434/sintraprime_runtime_test"

cat portal/migrations/runtime_schema_integrity_2026_07_27.sql | \
    docker exec -i sintraprime-postgres psql -U sintraprime -d sintraprime_unified -f -

.venv/Scripts/python -m pytest portal/tests/test_runtime_schema_integrity.py -v

SELECT conrelid::regclass::text AS table_name, conname
FROM pg_constraint
WHERE contype = 'c' AND connamespace = 'public'::regnamespace;
```

---

## Next Workstream

P2.3 — Migration Reliability (validate rollback execution and repeatability) remains to complete Phase Two.
