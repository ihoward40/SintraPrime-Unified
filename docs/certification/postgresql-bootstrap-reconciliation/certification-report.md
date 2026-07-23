# PostgreSQL Bootstrap Reconciliation - Certification Report

## Scope

PR-B certifies the repository raw-SQL fresh-bootstrap path and the directly affected evidence/audit ORM compatibility boundary. It certifies fresh bootstrap only. It does not certify production migration execution, upgrades from unknown existing schemas, populated VARCHAR-to-UUID conversion, Alembic adoption, workshop activation, payment authority, PR-C work, or repository-wide model/migration convergence.

## Base

- Base commit: `2d6ff2e10b639ec2601a46ba1592aaa62e597349`
- Base tree: `584d44a1bf8f267ea3f00e84018f10026d8c4297`
- PostgreSQL image used locally: `postgres:16-alpine`
- PostgreSQL version observed in final independent bootstrap evidence: `16.14`

## Migration sequence

Raw SQL remains the deployment schema authority for this PR. No Alembic migration framework is introduced.

1. `portal/migrations/portal_schema.sql`
2. `portal/migrations/add_evidence_snapshots.sql`
3. `portal/migrations/add_audit_records.sql`
4. `portal/migrations/add_mission_control_command_ledger.sql`
5. `portal/migrations/add_mission_control_run_control_projection.sql`

ORM models express runtime expectations and portability behavior; they do not replace the raw-SQL bootstrap authority.

## Untouched-main failure proof

Sanitized evidence:

- `evidence/baseline_20260722T213820Z_rerun.log.sanitized`

Failures reproduced on untouched main:

- `portal_schema.sql`: PostgreSQL rejects the stored generated expression using `CONCAT` as non-immutable.
- `add_evidence_snapshots.sql`: `VARCHAR(36)` foreign keys reference UUID primary keys on `cases(id)` and `users(id)`.
- `add_audit_records.sql`: duplicate primary key declaration, bad trigger function name, and identifier/FK type drift.

## Generated-column semantic parity

Final generated expression:

```sql
COALESCE(
  NULLIF(company_name, ''),
  COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')
)
```

This expression avoids `CONCAT` in a stored generated expression while preserving original CONCAT-style NULL handling as closely as possible:

- `company_name` precedence is preserved through `COALESCE(NULLIF(company_name, ''), ...)`.
- NULL first or last names are treated as empty strings.
- No trimming is introduced.
- No display-name normalization is introduced.
- Leading, trailing, and single-space outcomes are deliberately preserved.

Focused PostgreSQL cases: 9 passed.

## UUID authority decision

- Raw SQL remains PostgreSQL fresh-bootstrap authority and uses native UUID for the affected evidence/audit identifiers and UUID foreign keys.
- `EvidenceSnapshot.snapshot_id`, `AuditRecord.audit_id`, `AuditRecord.snapshot_id`, `AuditRecord.packet_id`, and Blackstone primary UUID identifiers use shared `PortableUUID` for ORM portability while preserving string serialization output where existing callers expect serialized IDs.
- `EvidenceSnapshot.case_id`, `EvidenceSnapshot.created_by`, and `AuditRecord.created_by` intentionally remain `String(36)` in ORM metadata because their referenced ORM tables (`cases.id`, `users.id`) remain legacy `String(36)`. This is the narrow correction that makes the PostgreSQL `Base.metadata.create_all()` race setup internally consistent without starting a repository-wide case/user UUID conversion.
- The live raw-SQL PostgreSQL bootstrap still proves those columns as native UUID in the database catalog and proves ORM CRUD against that live catalog.
- `PortableUUID` is an ORM portability mechanism only. It is not a migration framework and does not certify existing database conversion.
- `portal.models.blackstone` now imports the shared `PortableUUID`; affected Blackstone runtime tests passed in the PortableUUID path.

## Implementation summary

- Corrected client `display_name` generated expression to avoid non-immutable `CONCAT` and preserve NULL/empty-name semantics.
- Aligned affected evidence/audit SQL identifiers to UUID.
- Preserved restrictive FK deletion behavior for evidence/audit relationships.
- Removed duplicate audit primary-key declaration.
- Corrected audit immutability trigger function binding.
- Added shared `PortableUUID` type and reused it instead of keeping a second implementation in `blackstone.py`.
- Reconciled `EvidenceSnapshot` and `AuditRecord` ORM identifier columns with live PostgreSQL UUID columns where the ORM can do so coherently (`snapshot_id`, `audit_id`, `snapshot_id`, `packet_id`) while preserving string serialization output.
- Kept evidence/audit ORM foreign-key fields to legacy `cases.id` and `users.id` as `String(36)` so PostgreSQL `Base.metadata.create_all()` remains internally consistent; raw-SQL fresh bootstrap remains the native-UUID catalog authority for those live columns.
- Added a raw-SQL bootstrap verifier/runner for CI and local certification.
- Added live PostgreSQL catalog, CRUD, FK, rollback, generated-column, ORM `create_all`, and immutability tests.
- Fixed the PostgreSQL race test setup to create relationship-required tables (`audit_logs`, command events, command receipts) before running the existing race suite.

## Verification results

| Command / evidence | Result |
|---|---|
| Three independent fresh PostgreSQL bootstrap containers, `postgres:16-alpine`, tmpfs-only | 3/3 passed; 0 volumes; 0 bind mounts; exact containers removed |
| `python -m pytest -q portal/tests/test_postgresql_bootstrap_schema_authority.py` | 15 passed, 0 failed, 0 skipped; includes PostgreSQL ORM `Base.metadata.create_all()` CI-path regression |
| Focused generated-column semantic cases | 9 passed, 0 failed, 0 skipped |
| `python -m pytest -q portal/tests/test_evidence_snapshot.py portal/tests/test_audit_record.py` | 66 passed, 0 failed, 0 skipped |
| Mission Control PostgreSQL race selected nodes | 2 passed, 0 failed, 0 skipped |
| `python -m pytest -q portal/tests/test_mission_control_run_controls.py` | 19 passed, 0 failed, 2 skipped |
| Affected Blackstone PortableUUID tests: `portal/tests/test_blackstone_service.py blackstone/tests/test_blackstone_engines.py` | 12 passed, 0 failed, 0 skipped |
| Auth/correlation certification suite group | 189 passed, 0 failed, 0 skipped; PyJWT short-key warnings only |
| Full authoritative Python suite under Python 3.11.9 with JUnit XML | 374 tests, 0 failures, 0 errors, 0 skipped; 2 collection warnings; time 119.031s; timestamp 2026-07-22T19:26:37.858964-04:00 |
| `ruff check .` | passed |
| `python scripts/ci/validate_repository_claims.py` | passed |
| `.github/workflows/*.yml` YAML parse | passed |
| PostgreSQL race workflow credential inspection | passed: separate test-only PG components, no literal credential-bearing URL in YAML, no shell tracing, URL constructed in Python and passed only through subprocess environment |
| changed-diff secret scan | passed; changed added lines contain 0 credential-pattern hits |
| `git diff --check` | passed |
| Exact disposable repro container cleanup | `sp_prb_orm_repro_1784760815` resolved to full ID `ad563ccece61c593e7f54d7e2a822f6fa80d9085f385d7eb2fd98fe811c0b480`, verified `postgres:16-alpine`, no mounts, stopped/removed, absent afterward |

## Evidence index

- `evidence/three_independent_fresh_bootstraps_final.json`
- `evidence/three_independent_fresh_bootstraps_final.log`
- `evidence/final_null_semantics_bootstrap_certification.log`
- `evidence/final_affected_sqlite_evidence_audit.log`
- `evidence/final_mission_control_pg_race.log`
- `evidence/final_mission_control_run_controls_sqlite.log`
- `evidence/final_blackstone_portable_uuid.log`
- `evidence/blackstone_origin_main_repro.log`
- `evidence/final_auth_correlation_certification.log`
- `evidence/final_full_pytest_py311_after_null.xml`
- `evidence/final_full_pytest_py311_after_null_junit.log`
- `evidence/final_ruff_post_reconcile.log`
- `evidence/final_validate_repository_claims_post_reconcile.log`
- `evidence/final_ci_yaml_parse_after_null.log`
- `evidence/final_changed_diff_secret_scan_post_reconcile.log`
- `evidence/final_git_diff_check_post_reconcile.log`

## Blackstone failure classification

The broader Blackstone command:

```text
python -m pytest -q portal/tests/test_blackstone_service.py portal/tests/test_blackstone_case_workflow.py blackstone/tests/test_blackstone_engines.py
```

produced two 401 failures on the PR-B worktree:

- `portal/tests/test_blackstone_case_workflow.py::test_case_intake_endpoint_creates_evaluation`
- `portal/tests/test_blackstone_case_workflow.py::test_case_status_endpoint_returns_evaluations`

The same command and CI-compatible Python 3.11 environment reproduced the same two 401 failures on untouched `origin/main` at `2d6ff2e10b639ec2601a46ba1592aaa62e597349`. PR-B does not modify Blackstone authentication. The affected `PortableUUID` path is exercised by `portal/tests/test_blackstone_service.py` and `blackstone/tests/test_blackstone_engines.py`, which passed 12/12 on the PR-B worktree. Classification: pre-existing excluded test-boundary behavior, nonblocking for PR-B because the authoritative full suite remains green and the affected PortableUUID path is separately green.

## Existing-installation boundary

See `existing-installation-safety.md`. This PR certifies fresh bootstrap only. Unknown existing installations are not certified. Ambiguous existing schemas fail closed. Populated VARCHAR-to-UUID identifier conversion is not certified. No production migration execution is certified.

## Explicit nonclaims

- No production migration execution certified.
- No upgrade safety from unknown existing installations certified.
- No populated VARCHAR-to-UUID conversion certified.
- No Alembic introduced.
- No workshop activation.
- No payment or PR #219 authority.
- No PR-C work; PR-C remains frozen.
- No repository-wide model/migration convergence certification beyond the recorded PR-B scope.

## Rollback

Code rollback is by reverting this PR. Database rollback is fresh-bootstrap only: create a new disposable database after revert and re-run the prior raw-SQL sequence. Do not apply destructive rollback to existing installations without separate owner authorization.
