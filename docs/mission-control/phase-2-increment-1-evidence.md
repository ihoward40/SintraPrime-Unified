# Mission Control Phase Two Increment One Evidence

## Scope

Authorized increment: command ledger + guard + idempotency + refusal-only endpoint.

No command in this increment mutates run, task, scheduler, agent, mission, or assignment state. The Mission Control UI remains read-only and no frontend files were changed.

## Baseline

- Frozen tag: `mission-control-phase-1`
- Baseline commit: `bedccf2ff92291b9fbc51c72146255dd83d26663`
- Baseline tree: `eeb8886fae074d1c20f9aa18ed65272c40cf0ca8`
- Working branch: `feat/mission-control-phase-2-command-ledger`
- Parent for implementation branch: `bedccf2ff92291b9fbc51c72146255dd83d26663`
- Final commit/tree: recorded in PR metadata, PR comments, and completion response. A commit cannot contain its own hash without changing that hash.

## Changed Files

- `portal/auth/rbac.py`
- `portal/main.py`
- `portal/migrations/add_mission_control_command_ledger.sql`
- `portal/models/__init__.py`
- `portal/models/audit.py`
- `portal/models/mission_control_command.py`
- `portal/routers/mission_control_commands.py`
- `portal/services/audit_service.py`
- `portal/services/mission_control_command_guard.py`
- `portal/services/mission_control_command_service.py`
- `portal/tests/test_mission_control_commands.py`
- `portal/tests/test_service_units.py`
- `docs/mission-control/phase-2-increment-1-evidence.md`

## Migration

- File: `portal/migrations/add_mission_control_command_ledger.sql`
- SHA256: `8898E116F75261C57185C2232803137085FCF6B2F4DE2896B49CFE4CEBD2BD71`

Migration creates only:

- `mission_control_commands`
- `mission_control_command_events`
- `mission_control_command_receipts`

It does not create run-state, scheduler-state, mission-state, agent-state, or assignment-state tables.

## Permission Matrix

| Permission | Super Admin | Firm Admin | Attorney | Paralegal | Accountant | Viewer | Client |
|---|---:|---:|---:|---:|---:|---:|---:|
| `mission_control:command_read` | yes | yes | yes | no | no | no | no |
| `mission_control:command_create` | yes | yes | yes | no | no | no | no |
| `mission_control:run_start` | yes | yes | yes | no | no | no | no |
| `mission_control:run_pause` | yes | yes | yes | no | no | no | no |
| `mission_control:run_resume` | yes | yes | yes | no | no | no | no |
| `mission_control:run_cancel` | yes | yes | no | no | no | no | no |
| `mission_control:agent_assign` | yes | yes | yes | no | no | no | no |
| `mission_control:agent_reassign` | yes | yes | no | no | no | no | no |
| `mission_control:command_admin` | yes | no | no | no | no | no | no |

Super Admin receives all permissions through the existing `frozenset(Permission)` behavior.

## Endpoint

`POST /api/v1/mission-control/commands`

No direct mutation endpoints were added.

## Request Example

```json
{
  "command_type": "PAUSE_RUN",
  "target_type": "run",
  "target_id": "run-123",
  "idempotency_key": "client-generated-key-0001",
  "reason": "operator requested hold",
  "payload": {},
  "metadata": {
    "source": "mission-control-ui"
  }
}
```

## Refusal Response Example

```json
{
  "command_id": "uuid",
  "command_type": "PAUSE_RUN",
  "target_type": "run",
  "target_id": "run-123",
  "state": "REFUSED",
  "reason_code": "COMMAND_EXECUTION_NOT_ENABLED",
  "reason": "operator requested hold",
  "duplicate": false,
  "idempotency_key": "client-generated-key-0001",
  "request_hash": "sha256",
  "audit_log_id": "uuid",
  "event_ids": ["uuid", "uuid", "uuid"],
  "receipt_id": "uuid",
  "created_at": "timestamp",
  "completed_at": "timestamp"
}
```

## Idempotency Contract

Idempotency keys are required and must be 16-128 characters.

- New command: HTTP 201 with `duplicate: false`.
- Identical replay: HTTP 200 with `duplicate: true`.
- Changed replay: HTTP 409 with `DUPLICATE_CONFLICT`.

The service recovers from the database unique-constraint collision path for concurrent requests. If the initial lookup misses because another transaction won the `(tenant_id, requested_by, idempotency_key)` race, the losing request rolls back its failed insert, reloads the winning command, and returns the deterministic replay/conflict response.

## Idempotency Replay Example

Same tenant + requester + idempotency key + identical canonical request hash returns the original command response with:

```json
{
  "duplicate": true,
  "state": "REFUSED",
  "reason_code": "COMMAND_EXECUTION_NOT_ENABLED"
}
```

No second command row, event chain, audit row, or receipt row is created.

## Duplicate Conflict Example

Same tenant + requester + idempotency key + changed canonical request hash returns HTTP 409:

```json
{
  "detail": {
    "state": "DUPLICATE_CONFLICT",
    "reason_code": "IDEMPOTENCY_KEY_CONFLICT",
    "command_id": "original-command-id"
  }
}
```

No second command row, event chain, audit row, or receipt row is created.

## Command Target Compatibility

| Command | Allowed target types |
|---|---|
| `START_GOVERNED_RUN` | `run`, `mission` |
| `PAUSE_RUN` | `run` |
| `RESUME_RUN` | `run` |
| `CANCEL_RUN` | `run` |
| `ASSIGN_AGENT` | `run`, `task`, `mission` |
| `REASSIGN_AGENT` | `run`, `task`, `mission` |

Invalid command-target combinations return HTTP 422 before command, event, audit, or receipt persistence.

## Audit And Receipt Behavior

For an accepted non-duplicate command request, the service:

1. creates a `mission_control_commands` row;
2. appends `RECEIVED`, `VALIDATING`, and `REFUSED` command events;
3. writes the existing hash-chained `audit_logs` record;
4. creates a `REFUSAL` receipt with a deterministic receipt hash;
5. publishes requester-scoped realtime status on a best-effort basis.

Atomic behavior: audit failure rolls back the command transaction and raises. It does not leave an apparently successful command record.

## Command Event Hash Verification

Focused tests recompute each event hash from:

- command ID;
- sequence;
- event type;
- state;
- payload;
- previous hash.

The test asserts the stored `previous_hash` and `event_hash` chain is deterministic.

## Realtime Behavior

The implementation reuses `ws_manager.send_to_user` for requester-scoped command status events only.

No unauthenticated or tenant-wide Mission Control command broadcasts were added. Realtime delivery failure is logged and does not change the terminal `REFUSED` outcome.

## Proof No Mutation Path Was Enabled

- No frontend files changed.
- Mission Control command buttons remain disabled.
- No direct `/runs/{id}/pause`, `/runs/{id}/resume`, `/runs/{id}/cancel`, `/agents/{id}/assign`, or `/agents/{id}/reassign` endpoints were added.
- Code search for direct scheduler mutation calls in touched portal/web areas returned no matches.
- The command guard always returns `COMMAND_EXECUTION_NOT_ENABLED`.
- Tests assert supported commands persist and end in `REFUSED`.

## Phase One Visual Evidence

No files under these Phase One evidence paths were changed:

- `docs/ui-audit/screenshots/preservation-main-20260718`
- `docs/ui-audit/preservation-main-20260718-results.json`

`git diff -- docs/ui-audit/screenshots/preservation-main-20260718 docs/ui-audit/preservation-main-20260718-results.json` returned no output.

## Verification Results

Passed:

- `python -m py_compile portal\tests\test_mission_control_commands.py portal\models\mission_control_command.py portal\models\audit.py portal\services\audit_service.py portal\services\mission_control_command_service.py portal\routers\mission_control_commands.py`
- `python -m pytest portal\tests\test_mission_control_commands.py -q` -> 20 passed
- `python -m pytest portal\tests\test_mission_control.py portal\tests\test_rbac.py -q` -> 35 passed
- `python -m pytest portal\tests\test_service_units.py -q` -> 70 passed
- `python -m pytest portal\tests\test_mission_control_commands.py portal\tests\test_mission_control.py portal\tests\test_rbac.py portal\tests\test_service_units.py -q` -> 125 passed
- `python -m ruff check` on touched Python files -> all checks passed
- `git diff --check` -> clean
- SQLAlchemy model smoke check confirmed `mission_control_commands`, `mission_control_command_events`, and `mission_control_command_receipts` are registered in metadata.
- Focused collision-recovery tests prove stale initial lookup plus unique-constraint collision reloads the winning command and creates no duplicate command, events, audit entry, or receipt.

Full repository Python test command:

- `python -m pytest --tb=short -q` completed with 4 failures in `tests/test_scheduler_executor.py`.
- Failures are Windows shell environment failures while spawning Unix-like shell commands `echo`, `sleep`, and `false` from `scheduler/task_executor.py` tests.
- These failures are unrelated to the Mission Control command ledger and do not indicate a command mutation path.

Frontend checks:

- Not run because no frontend or shared frontend types were touched.

## Known Limitations

- Increment One records and refuses commands only.
- No confirmation flow exists.
- No approval consumption exists.
- No runner pause/resume/cancel integration exists.
- No scheduler mutation exists.
- No assignment mutation exists.
- No command history UI is enabled.
- Command rows are a projection; command events and receipts are the immutable history.
