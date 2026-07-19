# PR #212 — PostgreSQL Concurrency Race Harness Evidence

## Scope
Fixture/harness hardening only for the draft PR #212
(`feat/mission-control-phase-2-permissions-run-control`).
No production concurrency logic, operational command, durable workflow,
frontend, or Increment-Two-B/C behavior was modified.

## Authorized starting point
- Repository: `ihoward40/SintraPrime-Unified`
- PR: `#212` (draft, OPEN, MERGEABLE, unmerged)
- Starting head: `5ab9ac86003c8830c05182fbff8f498e790ec5c2`

## Root-cause localization (prior runs)
1. The original race harness returned `transition_run_control()` results
   (which only **flush**, leaving transaction completion to the caller) and
   counted a flushed-but-uncommitted outcome as success. Two contenders both
   appeared to "win" because neither committed; on session close the loser
   rolled back and the second transaction could still observe the original
   version. This was a **transaction-harness defect**, not a service defect.
2. After correcting contenders to own their commit/rollback boundary and to
   return typed results (`COMMITTED_SUCCESS` / `VERSION_CONFLICT` /
   `UNEXPECTED_ERROR`), the dedicated CI job failed on a **post-race test
   assertion**, not on the concurrency core.
3. The post-race failure was localized via CI diagnostics (pre/post event
   baseline + structured event prints + uploaded `/tmp/pg_race.log` artifact):
   `assert delta_event.tenant_id == tenant_id` raised
   `AttributeError: 'MissionControlRunControlEvent' object has no attribute
   'tenant_id'`. The event model is keyed by `run_control_id`, not
   `tenant_id`. This is an **assertion-baseline defect** — the persisted data
   was already correct.

## Corrected subject-code head
`abb962878c577117296f3867b1376562465211bd`

## Evidence-container CI run
- Workflow run: `29690682439` (SintraPrime CI — 797 Tests)
- PostgreSQL job: `88202726551` (postgresql-race) — **success**
- PostgreSQL version: 16
- Exact pytest command:
  ```
  python -m pytest -vv -rs -s --tb=long --maxfail=1 \
    portal/tests/test_mission_control_run_controls.py::test_parallel_pg_transition_race_appends_exactly_one_event \
    portal/tests/test_mission_control_run_controls.py::test_pg_flushed_transition_rollback_does_not_persist
  ```

## Results (authoritative, from CI artifact)
```
collecting ... collected 2 items
test_parallel_pg_transition_race_appends_exactly_one_event PASSED
test_pg_flushed_transition_rollback_does_not_persist PASSED
============================== 2 passed in 1.11s ===============================
```
- Two tests collected: **yes**
- Two tests executed: **yes**
- Zero skipped: **yes**
- Two passed: **yes**

### Concurrency core (race test)
- `RACE EVENTS before=1 types=['CREATED']` — `create_run_control` emits
  exactly one initialization (CREATED) event.
- `RACE RESULT: results=['COMMITTED_SUCCESS', 'VERSION_CONFLICT']`
  `committed=1 conflicts=1 errors=0`
- `RACE FINAL: state_version=2 state=PAUSE_REQUESTED`
- One committed winner; one version conflict; zero unexpected errors.

### Event baseline and delta
- Pre-race event count: **1** (CREATED)
- Post-race event count: **2**
- Exact event delta: **1** (exactly one new durable transition event)
- Delta event: `seq=2 type=STATE_TRANSITIONED src=RUNNING tgt=PAUSE_REQUESTED
  ver=2 prev=<hash of CREATED>`

### Hash-chain result
- `seq=1` CREATED: `prev=None hash=e8288191...`
- `seq=2` STATE_TRANSITIONED: `prev=e8288191... hash=642a1ba6...`
- `seq2.previous_event_hash == seq1.event_hash` → **valid chain**

### Rollback-protection test
- `test_pg_flushed_transition_rollback_does_not_persist` PASSED
- Flush occurs; explicit rollback; fresh session sees original state and
  version; no transition event persists; a later committed transition using
  the original expected state/version succeeds.

### Command immutability
- `RACE COMMAND: state=REFUSED` — the MissionControlCommand remained
  refusal-only; no operational execution mutation occurred solely because the
  run-control projection transitioned.

## Classification
- Transaction-harness correction: **PASS**
- Core PostgreSQL concurrency result: **PASS**
- Post-race persistence assertions: **PASS** (after fixing the invalid
  `tenant_id` assertion — an assertion-baseline defect, not a data defect)
- Production service defect: **NOT ESTABLISHED**
- Evidence finalization: **COMPLETE**
- Merge authorization: **UNAVAILABLE** (PR remains draft/unmerged per scope)

## Other required CI checks (head `abb96287`)
- `test`: success
- `lint`: success
- `security`: success
- `IssueVerifier CI`: success
- `Sigma Gate`: success

## Local verification (non-PostgreSQL)
- Run-control module: 17 passed, 2 skipped (PG tests) — Ruff clean,
  `git diff --check` OK.
- Idempotency tests: 2 passed.
- Tenant-isolation / SQL-predicate: 1 passed.
- Related suites (commands, mission_control, permission_provisioning,
  permission_sync_cli): 55 passed.
- Auth / RBAC: passed (1 unrelated PyJWT warning).
- `ruff check portal/tests/`: All checks passed.

## Remaining limitations
- The dedicated CI job exercised real PostgreSQL 16 with the canonical app
  data path; local execution against PostgreSQL was not possible in the
  sandbox due to credential-redaction behavior, so the authoritative proof is
  the CI artifact above.
- The service's conditional UPDATE
  (`WHERE state_version == expected_version AND tenant_id == ? AND state == ?`,
  `rowcount != 1 -> RunControlConflictError`) was not modified and is the
  mechanism that arbitrates the single winner.
