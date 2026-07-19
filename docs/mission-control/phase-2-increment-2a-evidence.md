# Mission Control Phase Two Increment Two A Evidence

## Scope

Increment Two A closure only: deterministic permission verification/reconciliation, permission drift detection, additive run-control projection, immutable run-control transition history, protected diagnostics, and evidence-backed verification.

All operational commands remain refusal-only with `COMMAND_EXECUTION_NOT_ENABLED`.

## Baseline

- Baseline tag: `mission-control-phase-2-increment-1`
- Baseline commit: `88bc4da5f44820a9466c5497e1aab84b811ce17f`
- Baseline tree: `320084225fa78244e4373272c5e9a82b7651c240`
- Implementation commit: `ad4898110f8f394cba45d77163bb544948585a99`
- Final commit: `__FINAL_COMMIT__`
- Final tree: `__FINAL_TREE__`
- Parent commit: `__FINAL_PARENT__`
- Branch: `__FINAL_BRANCH__`

## Environment issue and resolution

Standalone evidence generation collided with unrelated local environment variables and the repository `.env` file.

- Environment variables: `NOTION_TOKEN`, `NOTION_PARENT_PAGE`, `notion_token`, `notion_cases_db_id`, `notion_trigger_codes_db_id`
- Resolution: run the evidence subprocesses from a clean temporary working directory, outside the repository `.env`, and unset the unrelated environment variables in the subprocess environment.

Safety:

- only unrelated local variables were isolated;
- the repository `.env` was avoided by changing the working directory;
- production configuration validation was not weakened;
- no production code was changed to accommodate evidence generation.

## Repository facts

Implementation changed files relative to the baseline:

- `portal/migrations/add_mission_control_run_control_projection.sql`
- `portal/models/__init__.py`
- `portal/models/mission_control_run_control.py`
- `portal/scripts/sync_mission_control_permissions.py`
- `portal/services/__init__.py`
- `portal/services/mission_control_run_control_service.py`
- `portal/services/permission_provisioning.py`
- `portal/tests/test_mission_control_run_controls.py`
- `portal/tests/test_permission_provisioning.py`

Migration checksum:

- `5a78067c30cf66b816f37c5b4f94585c23e4238db1d0617e9ebbb881b183343e`

## Evidence artifacts

- `docs/mission-control/phase-2-increment-2a-permission-manifest.json`
- `docs/mission-control/phase-2-increment-2a-drift-report.json`
- `docs/mission-control/phase-2-increment-2a-transition-matrix.json`
- `docs/mission-control/phase-2-increment-2a-decision-log.json`
- `docs/mission-control/phase-2-increment-2a-test-results.json`
- `docs/mission-control/phase-2-increment-2a-deployment-checklist.md`
- `docs/mission-control/phase-2-increment-2a-rollback.md`

## Summary

- Deterministic permission manifest and drift scenarios were generated from the live implementation.
- JWT login/refresh behavior was exercised against the synchronized permission graph.
- Run-control transition history, stale-version conflict handling, and append-only event hashes were exercised against the live projection.
- Backend regression suites, RBAC, auth/JWT, service-unit, and orchestration tests passed under isolated evidence subprocesses.
- Ruff and `git diff --check` passed on the touched Python files.

## Known limitations

- The repository still contains a legacy authorization source in `portal/migrations/portal_schema.sql:47` (`permissions TEXT[]`); the new synchronization logic is authoritative over the normalized tables.
- JWT test output includes a benign key-length warning in the test fixture environment.
- Orchestration tests emit deprecation warnings from `asyncio.iscoroutinefunction`; they do not fail.

## Final receipt

- Final commit: `__FINAL_COMMIT__`
- Final tree: `__FINAL_TREE__`
- Parent commit: `__FINAL_PARENT__`
- Branch: `__FINAL_BRANCH__`
- CI head: `__FINAL_HEAD_FOR_CI__`
