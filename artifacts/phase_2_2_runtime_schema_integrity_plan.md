# P2.2 — Runtime Schema Integrity Plan

**Plan ID:** P2.2-2026-07-27-01
**Scope:** Live 8-table runtime schema in `sintraprime-postgres`
**Option:** C (bounded runtime-only stabilization)
**Date:** 2026-07-27

---

## Baseline Evidence

Source: `artifacts/phase_2_1_database_baseline_report.md`

Live schema tables:
- agents
- execution_history
- knowledge_entries
- messages
- sessions
- skills
- swarms
- users

Current state:
- 0 rows in most tables, 1 user row.
- 3 foreign keys exist.
- 5 unique constraints exist.
- 0 CHECK constraints.
- Several columns are nullable despite having defaults.
- No dedicated migration regression tests.

---

## Proposed Changes

All changes are additive or tightening constraints on existing tables. No table drops, no column renames, no data migration required.

### 1. CHECK constraints (justified by application invariants)

| Table | Column | Constraint | Rationale |
|---|---|---|---|
| agents | status | `status IN ('idle', 'active', 'paused', 'stopped', 'failed')` | Runtime state machine invariants |
| execution_history | status | `status IN ('pending', 'running', 'completed', 'failed', 'cancelled')` | Job lifecycle invariants |
| swarms | status | `status IN ('initializing', 'active', 'paused', 'dissolved', 'failed')` | Swarm lifecycle invariants |
| messages | priority | `priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')` or existing casing | Message priority invariants |
| knowledge_entries | confidence | `confidence >= 0.0 AND confidence <= 1.0` | Probability semantic |
| users | is_active | already boolean | No change needed |

### 2. NOT NULL enforcement (columns with sensible defaults)

| Table | Column | Default | Justification |
|---|---|---|---|
| agents | status | 'idle' | Cannot be null with default |
| agents | config | '{}' | Empty config is valid |
| agents | created_at | NOW() | Audit timestamp |
| agents | updated_at | NOW() | Audit timestamp |
| execution_history | status | 'pending' | Job state |
| execution_history | started_at | NOW() | Audit timestamp |
| knowledge_entries | confidence | 1.0 | Valid default |
| knowledge_entries | created_at | NOW() | Audit timestamp |
| knowledge_entries | updated_at | NOW() | Audit timestamp |
| messages | priority | 'NORMAL' | Default priority |
| messages | processed | false | Boolean state |
| messages | created_at | NOW() | Audit timestamp |
| sessions | created_at | NOW() | Audit timestamp |
| skills | parameters | '{}' | Empty parameters valid |
| skills | version | '1.0.0' | Default version |
| skills | enabled | true | Default enabled state |
| skills | created_at | NOW() | Audit timestamp |
| swarms | status | 'initializing' | Default state |
| swarms | config | '{}' | Empty config valid |
| swarms | agent_ids | '{}' | Empty array valid |
| swarms | created_at | NOW() | Audit timestamp |
| swarms | updated_at | NOW() | Audit timestamp |
| users | is_active | true | Default active state |
| users | created_at | NOW() | Audit timestamp |

### 3. Indexes for FK and common lookups

| Table | Columns | Rationale |
|---|---|---|
| messages | (sender_id) | Filter/join by sender |
| messages | (recipient_id) | Filter/join by recipient |
| execution_history | (agent_id) | Existing FK but no index beyond PK |
| execution_history | (swarm_id) | Existing FK but no index beyond PK |
| sessions | (user_id) | Existing FK but no index beyond PK |
| users | (is_active) | Active-user filtering |
| knowledge_entries | (source) | Source filtering |

### 4. Migration tooling

- Add `portal/migrations/runtime_schema_integrity_2026_07_27.sql` with:
  - All changes as `ALTER TABLE ... ADD CONSTRAINT IF NOT EXISTS` / `ALTER COLUMN ... SET NOT NULL` / `CREATE INDEX IF NOT EXISTS`.
  - Inline DOWN migration comments.
- Add `portal/scripts/verify_runtime_schema_integrity.py` to apply and verify the migration against a target database.
- Add `portal/tests/test_runtime_schema_integrity.py` with regression tests for:
  - Constraint enforcement (valid/invalid values)
  - NOT NULL enforcement
  - Index existence
  - Downgrade statement validity (where applicable)

### 5. Rollback path

- Each constraint is added with `IF NOT EXISTS` and can be dropped with `DROP CONSTRAINT IF EXISTS`.
- Each NOT NULL can be reverted with `ALTER TABLE ... ALTER COLUMN ... DROP NOT NULL`.
- Each index can be dropped with `DROP INDEX IF EXISTS`.
- Full down migration script will be documented inline.

---

## Out of Scope

- Portal schema (`portal_schema.sql`) modifications.
- Alembic introduction.
- Table merges or renames.
- Multi-tenancy additions.
- Data migration (no data exists to migrate).

---

## Verification

1. Apply migration to a fresh disposable PostgreSQL database.
2. Apply migration to the live container (safe because all changes are additive/compatible with existing single user row).
3. Run new regression tests.
4. Run full test suite.
5. Generate verification report.
