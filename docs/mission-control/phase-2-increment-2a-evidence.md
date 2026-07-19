# Mission Control Phase Two Increment Two A Evidence

## Provenance

- Baseline tag: `mission-control-phase-2-increment-1`
- Baseline commit: `88bc4da5f44820a9466c5497e1aab84b811ce17f`
- Baseline tree: `320084225fa78244e4373272c5e9a82b7651c240`
- Reviewed head: `efe4b0f7f1eeb38a73176360800c8c1e57c32596`
- Original implementation commit: `ad4898110f8f394cba45d77163bb544948585a99`
- Correction commit / subject code head: `4510d8ab7013880b8ccfe8bfbaf82da15c832cb7`
- Subject code tree: `ff286746315aed93cc9431511338eae054039b7e`
- Subject branch at verification: `feat/mission-control-phase-2-permissions-run-control`
- Evidence container note: Two-layer provenance: code was verified at the subject_code_head, then evidence artifacts were added in a follow-up evidence commit. The exact evidence-container head is recorded in final PR metadata / final review response because it cannot be self-embedded into the same commit that contains the evidence files.

## What changed in the code subject head

- `docs/mission-control/phase-2-increment-2a-decision-log.json`
- `docs/mission-control/phase-2-increment-2a-deployment-checklist.md`
- `docs/mission-control/phase-2-increment-2a-drift-report.json`
- `docs/mission-control/phase-2-increment-2a-evidence.md`
- `docs/mission-control/phase-2-increment-2a-permission-manifest.json`
- `docs/mission-control/phase-2-increment-2a-rollback.md`
- `docs/mission-control/phase-2-increment-2a-test-results.json`
- `docs/mission-control/phase-2-increment-2a-transition-matrix.json`
- `portal/migrations/add_mission_control_run_control_projection.sql`
- `portal/models/__init__.py`
- `portal/models/mission_control_run_control.py`
- `portal/scripts/sync_mission_control_permissions.py`
- `portal/services/__init__.py`
- `portal/services/mission_control_run_control_service.py`
- `portal/services/permission_provisioning.py`
- `portal/tests/test_mission_control_run_controls.py`
- `portal/tests/test_permission_provisioning.py`
- `portal/tests/test_permission_sync_cli.py`

## Evidence artifacts updated in the follow-up evidence commit

- `docs/mission-control/phase-2-increment-2a-evidence.md`
- `docs/mission-control/phase-2-increment-2a-permission-manifest.json`
- `docs/mission-control/phase-2-increment-2a-drift-report.json`
- `docs/mission-control/phase-2-increment-2a-transition-matrix.json`
- `docs/mission-control/phase-2-increment-2a-decision-log.json`
- `docs/mission-control/phase-2-increment-2a-test-results.json`
- `docs/mission-control/phase-2-increment-2a-deployment-checklist.md`
- `docs/mission-control/phase-2-increment-2a-rollback.md`

## Corrections addressed

1. Exact-head evidence provenance was split into subject code head versus evidence container commit.
2. Run-control transitions now require tenant scope.
3. mission_control_run_control_events.principal_id now matches the users.id foreign key in the migration.
4. Real concurrency coverage was added for PostgreSQL when available.
5. Terminal-precedence tests now cover pause versus terminal outcomes and terminal-state revivals.
6. Verify and dry-run paths no longer commit.
7. Rollback documentation now states forward-disable plus code revert unless a separate approved database procedure exists.

## Verification summary

- Permission provisioning tests: passed.
- Run-control tests: passed.
- Command-ledger tests: passed.
- Mission Control summary tests: passed.
- RBAC tests: passed.
- Auth and JWT tests: passed.
- Service-unit tests: passed.
- Durable workflow tests: passed.
- Ruff on touched Python files: passed.
- `git diff --check`: passed.
- PostgreSQL concurrency test: skipped because no PostgreSQL DATABASE_URL was configured locally.

## Limitations

- The exact evidence-container commit hash is recorded in final PR metadata / final review response rather than self-embedded in the evidence files.
- PostgreSQL concurrency coverage is gated and could not run locally without a configured PostgreSQL test database.
- The repository still contains the legacy authorization source in `portal/migrations/portal_schema.sql:47`; normalized permissions remain authoritative.
