# PostgreSQL Bootstrap Reconciliation — Baseline and Authority

## Baseline

- Worktree: `C:\Users\admin\Desktop\Projects\SintraPrime-Unified-postgresql-bootstrap-fix`
- Branch: `fix/postgresql-bootstrap-schema-authority`
- Verified `origin/main`: `2d6ff2e10b639ec2601a46ba1592aaa62e597349`
- Verified tree: `584d44a1bf8f267ea3f00e84018f10026d8c4297`
- PostgreSQL used for baseline reproduction: `16.14`

## Applicable authority files inspected

- `AGENTS.md`
- `portal/AGENTS.md`
- `tests/AGENTS.md`
- `docs/DATABASE_AUTHORITY.md`
- `docs/ARCHITECTURE.md`
- `docs/REPOSITORY_STATUS.md`
- `.github/workflows/ci.yml`
- `portal/migrations/*.sql`
- `portal/models/evidence_snapshot.py`
- `portal/models/audit_record.py`
- affected evidence/audit tests and services

## Migration order

The repository authority before this PR listed raw SQL migrations without Alembic. The certified fresh-bootstrap order is:

1. `portal/migrations/portal_schema.sql`
2. `portal/migrations/add_evidence_snapshots.sql`
3. `portal/migrations/add_audit_records.sql`
4. `portal/migrations/add_mission_control_command_ledger.sql`
5. `portal/migrations/add_mission_control_run_control_projection.sql`

## Untouched-main failures reproduced

Evidence logs are under `docs/certification/postgresql-bootstrap-reconciliation/evidence/`.

- `portal_schema.sql`: PostgreSQL rejects the stored generated expression using `CONCAT` as non-immutable.
- `add_evidence_snapshots.sql`: `VARCHAR(36)` foreign keys reference UUID primary keys on `cases(id)` and `users(id)`.
- `add_audit_records.sql`: duplicate primary key declaration, bad trigger function name, and identifier/FK type drift.

## Affected tables

- `clients`
- `evidence_snapshots`
- `audit_records`
- referenced base tables: `cases`, `users`

## Affected ORM models

- `portal.models.evidence_snapshot.EvidenceSnapshot`
- `portal.models.audit_record.AuditRecord`
- the Blackstone-local UUID portability pattern was consolidated into shared `portal.models.types.PortableUUID` and reused.

## Affected API/service paths

No route behavior or runtime authentication was intentionally changed. Directly affected service/test paths are evidence/audit persistence and deterministic serialization paths:

- `portal/services/evidence_snapshot_service.py` inspected; no runtime change.
- `portal/services/evidence_audit_service.py` inspected; no runtime change.
- `portal/tests/test_evidence_snapshot.py` compatibility lane.
- `portal/tests/test_audit_record.py` compatibility lane.
- `portal/tests/test_postgresql_bootstrap_schema_authority.py` added live PostgreSQL raw-SQL and ORM parity certification.

## Historical SQL file decision

These raw SQL files are both fresh-bootstrap definitions and historical migrations. Direct correction is acceptable for the repository fresh-bootstrap path because the existing main sequence does not successfully apply to an empty PostgreSQL database. Direct correction does not by itself repair already-created production or long-lived databases.

This PR does not assume any production migration has been applied. Existing installations require preflight and reviewed upgrade handling as documented in `existing-installation-safety.md`.

## UUID authority decision

| table | column | referenced table/column | previous SQL type | previous ORM type | Python representation | SQLite representation | PostgreSQL representation | selected authority | compatibility implications |
|---|---|---|---|---|---|---|---|---|---|
| evidence_snapshots | snapshot_id | audit_records.snapshot_id | VARCHAR(36) | String(36) | uuid.UUID | VARCHAR(36) | UUID | native UUID via PortableUUID | `to_dict()` remains string; bind accepts UUID or string |
| evidence_snapshots | case_id | cases.id | VARCHAR(36) | String(36) | uuid.UUID | VARCHAR(36) | UUID | referenced base UUID PK | FK now implementable on PostgreSQL |
| evidence_snapshots | created_by | users.id | VARCHAR(36) | String(36) | uuid.UUID | VARCHAR(36) | UUID | referenced base UUID PK | FK now implementable on PostgreSQL |
| audit_records | audit_id | primary key | VARCHAR(36) | String(36) | uuid.UUID | VARCHAR(36) | UUID | native UUID via PortableUUID | duplicate PK removed; default UUID available in SQL |
| audit_records | snapshot_id | evidence_snapshots.snapshot_id | VARCHAR(36) | String(36) | uuid.UUID | VARCHAR(36) | UUID | evidence snapshot UUID authority | FK enforced on PostgreSQL |
| audit_records | packet_id | none | VARCHAR(36) | String(36) | uuid.UUID | VARCHAR(36) | UUID | UUID identifier | callers may bind UUID or string |
| audit_records | created_by | users.id | VARCHAR(36) | String(36) | uuid.UUID | VARCHAR(36) | UUID | referenced base UUID PK | FK enforced on PostgreSQL |

## Nonclaims

- Not production migration certification.
- Not proof of upgrade safety from unknown schemas.
- Not populated VARCHAR-to-UUID conversion certification.
- Not Alembic adoption.
- Not complete repository-wide model/migration convergence.
- Not workshop activation.
- Not payment authority.
- Not PR-C work; PR-C remains frozen.

## Generated display-name expression

The final stored generated expression is:

```sql
COALESCE(
  NULLIF(company_name, ''),
  COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')
)
```

It preserves CONCAT-style NULL handling without using `CONCAT`, preserves company-name precedence, and deliberately introduces no trimming or normalization.
