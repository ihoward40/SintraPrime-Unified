# PostgreSQL Bootstrap Reconciliation — Existing Installation Safety

## Certification boundary

This PR certifies fresh bootstrap only for the repository raw-SQL sequence on disposable PostgreSQL. It does not certify production migration orchestration and does not certify upgrade safety from unknown or populated schemas.

## Supported starting states

| starting state | handling |
|---|---|
| no affected tables exist | supported by fresh-bootstrap sequence |
| affected tables partially created | fail closed; manual reviewed repair required |
| affected tables use VARCHAR identifiers | fail closed; do not auto-cast populated identifiers |
| affected tables use UUID identifiers with expected constraints/triggers | may be compatible after preflight confirms exact shape |
| audit trigger already bound to correct function | compatible only if table/constraint shape also matches |
| unknown extra columns, missing constraints, or mixed identifier types | fail closed |

## Non-destructive preflight queries

Run read-only queries against a candidate non-production database before any reviewed upgrade procedure:

```sql
SELECT current_database(), current_user, version();

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('evidence_snapshots', 'audit_records')
ORDER BY table_name;

SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('evidence_snapshots', 'audit_records')
  AND column_name IN ('snapshot_id', 'case_id', 'created_by', 'audit_id', 'packet_id')
ORDER BY table_name, column_name;

SELECT conrelid::regclass AS table_name, conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid IN ('evidence_snapshots'::regclass, 'audit_records'::regclass)
ORDER BY table_name::text, conname;

SELECT tgrelid::regclass AS table_name, tgname, proname
FROM pg_trigger t
JOIN pg_proc p ON p.oid = t.tgfoid
WHERE tgrelid IN ('evidence_snapshots'::regclass, 'audit_records'::regclass)
  AND NOT tgisinternal
ORDER BY table_name::text, tgname;

SELECT 'evidence_snapshots' AS table_name, count(*) AS row_count
FROM evidence_snapshots
UNION ALL
SELECT 'audit_records' AS table_name, count(*) AS row_count
FROM audit_records;
```

If a table does not exist, run only the metadata queries that do not reference the absent table directly.

## Fail-closed rules

- Do not cast or rewrite populated VARCHAR identifiers automatically.
- Do not drop affected tables in an existing installation.
- Do not disable or remove foreign keys to force compatibility.
- Do not weaken audit immutability triggers.
- Do not infer safety from ORM metadata alone; query the live catalog.
- Ambiguous states require a separate reviewed migration/repair plan.

## Additive repair plan boundary

For already-created empty affected tables with the old broken shape, a separate reviewed repair script may drop and recreate only if row counts are zero and the owner explicitly authorizes that state-specific repair. For populated tables, this PR provides no automatic conversion. A data-preserving UUID migration would require an explicit mapping, backups, lock/transaction plan, rollback plan, and owner review outside this PR.

## Rollback boundary

Fresh-bootstrap rollback is repository-level: revert this PR and re-run bootstrap in a new disposable database. Existing installations must not be rolled back by destructive table drops without separate authorization.
