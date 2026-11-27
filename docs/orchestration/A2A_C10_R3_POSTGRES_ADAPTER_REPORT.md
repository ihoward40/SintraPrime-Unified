# C10-R3 PostgreSQL Adapter Report

**Baseline:** `b1db987afda50fc1acbcfe1b58a86f3ee9f71ea4`  
**Status:** PARTIAL — adapter implementation and deterministic contract tests complete; live PostgreSQL/shadow deployment validation remains pending.

## Implemented

- `orchestration/persistence.py` defines `AuditStore`, `ApprovalStore`, and `OutboxStore` protocols.
- `PersistenceConfig` supports explicit `A2A_PERSISTENCE_BACKEND=jsonl|postgres` selection.
- `A2A_PERSISTENCE_SHADOW=true` is valid only with the explicit PostgreSQL backend and never causes silent fallback.
- `ShadowComparator` raises `ShadowMismatchError` and accepts an audit sink when mirrored projections diverge.
- `PostgresAuditStore` writes tenant-scoped immutable audit events.
- `PostgresApprovalStore` uses `FOR UPDATE` for one-time consumption and tenant/hash binding checks.
- `PostgresOutboxStore` uses `FOR UPDATE SKIP LOCKED` for claims and worker/version lease fields for stale-worker rejection.
- `orchestration/postgres_schema.sql` contains the C10-R2 schema draft at the adapter location.
- JSONL stores remain unchanged and remain the default local adapter.

## Tests

```bash
python -m pytest -q orchestration/tests/test_postgres_persistence.py
```

The deterministic tests cover JSONL default selection, invalid backend configuration, shadow mismatch fail-closed behavior, tenant mismatch, one-time approval semantics, `SKIP LOCKED` claim SQL, invalid terminal transitions, and audit tenant/external-action constraints.

Validation results for this implementation slice:

```text
Focused C10-R3/A2A lane: 44 passed
Standalone agent_protocol lane: all passed
Complete repository suite: all collected tests passed, exit code 0
```

## Safety boundary

No production database was contacted. No migration was applied. No external executor was enabled. Dispatch Desk remains blocked and no profile has `can_send_external=true`.

## Limitations

The adapters are not yet wired into the orchestration dependency graph, and the PostgreSQL implementation has not been run against a live PostgreSQL server with RLS enabled. Shadow dual-write comparison is implemented as a primitive, not yet integrated into every lifecycle call. C10-R4 must add live database contract tests, migration execution, concurrency proof, crash/restart tests, and complete shadow reconciliation before any production authority switch.
