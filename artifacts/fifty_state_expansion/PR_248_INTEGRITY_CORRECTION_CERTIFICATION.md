# PR #248 Integrity Correction Certification

## Status

CERTIFIED

## Scope

This certification covers the corrective commit `42a3bd92fd83085d806b088874fa9cec5786ca6b` on branch `feat/fifty-state-trust-intelligence`, which fixes two PR-regression defects:

1. **RBAC route discovery** — Helper-function auth wrappers (`_actor_read`, `_actor_write`, `_read`, `_write`, `_review`) in `portal/routers/matter_intelligence.py` and `portal/routers/deadline_evidence.py` were not recognized by the RBAC certification classifier. Fix: inline `Depends(require_permissions(...))` in every endpoint signature.
2. **FastAPI `_IncludedRouter` compatibility** — Phase 2C route-registration tests assumed `app.routes` only contained `APIRoute` objects. FastAPI 0.139+ inserts `_IncludedRouter` wrappers with no `.path` attribute. Fix: shared recursive terminal-route iterator in `portal/tests/support/route_enumeration.py`.

## Certification Environment

- **OS:** Windows 11 (git-bash/MSYS)
- **Python:** 3.14.0
- **FastAPI:** 0.141.1 (CI-equivalent)
- **Starlette:** 0.52.1 (CI-equivalent)
- **PostgreSQL:** 16 (Docker disposable, port 55432)
- **Node.js:** npm ci from `web/package-lock.json`
- **Playwright:** 1.62.0

## Gates Passed

### PostgreSQL Integrity Certification

- **Bootstrap certification:** 15 passed, 0 failed, 0 skipped (87s)
  - `test_authoritative_migration_sequence_is_ordered`
  - `test_postgresql_orm_foreign_key_column_types_are_internally_consistent`
  - `test_postgresql_race_prepare_schema_create_all_path_executes`
  - `test_clean_raw_sql_bootstrap_repeats_three_times`
  - `test_client_display_name_generated_expression_matches_concat_null_semantics` (9 parametrized)
  - `test_live_catalog_constraints_and_uuid_authority`
  - `test_real_orm_crud_uuid_binding_and_audit_immutability`

- **PostgreSQL race tests:** 2 passed, 0 failed (4s)
  - `test_parallel_pg_transition_race_appends_exactly_one_event`
  - `test_pg_flushed_transition_rollback_does_not_persist`

- **Phase 2C integrity tests (with PostgreSQL):** 33 passed, 0 failed (5s)
  - Audit-chain tamper detection
  - Tenant/matter scope enforcement
  - Cross-tenant/cross-matter source rejection
  - Evidence approval requires attorney
  - Export authorization and redaction
  - Migration rollback contracts
  - Federal authority provenance and hierarchy

### Full Backend Gates

| Gate | Result |
|---|---|
| pytest | 651 passed, 0 failed, 0 skipped, 6 warnings (207s) |
| ruff check . | All checks passed |
| black --check . | 744 files would be reformatted (pre-existing baseline, unchanged) |
| mypy (legal_authority) | Success: no issues found in 9 source files |
| compileall portal packages | No errors |
| git diff --check | Clean |

### Frontend Gates

| Gate | Result |
|---|---|
| npm run type-check | Pass |
| npm run lint | Pass (0 warnings) |
| npm run build | Pass (2940 modules, 15s) |
| npx playwright test | 4 passed, 1 failed (pre-existing), 3 did not run |

**Playwright failure note:** The document-vault login test fails locally because Python 3.14's email-validator rejects the `.test` TLD in `e2e-attorney@sintraprime.test`. This is a pre-existing environment issue, confirmed by reproducing on the clean HEAD `93a53b5f`. CI (Python 3.11) passes all Playwright tests. The matter-workspace E2E tests (directly related to this PR) pass.

## CI Matrix (PR #248 at head 42a3bd92)

All 13 checks SUCCESS:

| Check | Result |
|---|---|
| auth-tenant-rbac-certification | SUCCESS |
| test | SUCCESS |
| verify | SUCCESS |
| Sigma Quality Gate | SUCCESS |
| Build canonical portal image | SUCCESS |
| smoke | SUCCESS |
| postgresql-race | SUCCESS |
| postgresql-bootstrap-certification | SUCCESS |
| lint | SUCCESS |
| claims-validation | SUCCESS |
| audit-correlation-non-http-certification | SUCCESS |
| http-correlation-ws-hardening-certification | SUCCESS |
| security | SUCCESS |

## Files in Corrective Commit

```
portal/routers/deadline_evidence.py       (modified — inlined Depends)
portal/routers/matter_intelligence.py     (modified — inlined Depends)
portal/tests/support/__init__.py          (new — package marker)
portal/tests/support/route_enumeration.py  (new — shared route iterator)
portal/tests/test_auth_tenant_rbac_certification.py (modified — recursive route discovery)
tests/test_deadline_evidence_phase_two_c_three.py  (modified — uses shared helper)
tests/test_matter_export_phase_two_c_five.py        (modified — uses shared helper)
tests/test_matter_intelligence_phase_two_c_two.py   (modified — uses shared helper)
```

## Permissions Preserved

- Matter read routes → `MATTER_INTELLIGENCE_READ`
- Matter write routes → `MATTER_INTELLIGENCE_WRITE`
- Deadline/evidence review routes → `MATTER_INTELLIGENCE_REVIEW`
- No access broadened, no tenant checks removed, no permission checks weakened.

## Certification Date

2026-08-04