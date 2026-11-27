# A2A PostgreSQL Persistence Cutover Plan

## Status

Design-only plan for C10-R2. The JSONL local adapter remains intact. No production deployment or external executor enablement is authorized by this plan.

## Phase 0 — Freeze and baseline

Keep `A2A_PERSISTENCE_BACKEND=jsonl` for local development. Record the current C10-R1 baseline, run the complete repository suite, and preserve the C9 bypass matrix as a release gate. Do not mount JSONL state on shared network storage.

## Phase 1 — Introduce interfaces

Add adapter protocols for audit, approval, and outbox stores. Refactor orchestration dependencies to consume the protocols rather than concrete JSONL classes. Preserve method semantics, including hash binding, tenant checks, one-time approval consumption, terminal outbox states, and audit-on-block.

The default remains JSONL. Unknown backend values must fail startup rather than silently falling back to local files.

## Phase 2 — Build PostgreSQL adapter in shadow mode

Implement async SQLAlchemy repositories using the existing portal database/session conventions. Use PostgreSQL transactions, `FOR UPDATE`, `SKIP LOCKED`, unique idempotency constraints, optimistic version checks, and tenant context. Shadow mode writes the same logical event to both stores but does not use PostgreSQL to authorize execution yet.

Every shadow write must include a correlation ID. The comparison worker checks event type, tenant, receipt, status, hashes, sequence/order, and timestamps within a defined tolerance. Divergence is a blocking security event.

## Phase 3 — Contract and concurrency validation

Run the same contract suite against JSONL and PostgreSQL. Required cases include:

- Two concurrent consumers attempting the same approval.
- Two workers claiming the same outbox item.
- Stale lease owner attempting a transition.
- Duplicate idempotency key.
- Wrong tenant and wrong hash.
- Crash after claim and before transition.
- Crash after PostgreSQL commit and before Redis ACK.
- PostgreSQL restart and connection loss.
- Redis reclaim/retry/DLQ reconciliation.
- Missing audit event or projection/event mismatch.

The adapter does not advance if any case allows duplicate consumption, cross-tenant visibility, hash drift, or unaudited terminal state.

## Phase 4 — Read comparison and controlled authority switch

For a bounded period, read both adapters and compare projections without changing external behavior. Then make PostgreSQL authoritative for governance state while continuing JSONL export for local diagnostics. The switch must be an explicit configuration change reviewed as a deployment artifact; it must not be automatic.

At this stage, external actions remain blocked. Dispatch Desk remains blocked and all registry profiles remain `can_send_external=false`.

## Phase 5 — Recovery and topology proof

Run the adapter against the actual production PostgreSQL topology with backups, failover, connection pooling, RLS, and migration tooling. Prove recovery from database restart, worker crash, network partition, and Redis restart. Verify that an ACKed message does not reappear and that an unacknowledged message cannot bypass approval or tenant checks after reclaim.

## Phase 6 — Certification gate

C10-R3/R4 evidence must include schema version, migration checksum, database topology, RLS policy verification, transaction traces, concurrent-worker results, restart results, reconciliation results, and a complete rerun of the C9 bypass suite. Any mismatch produces `PARTIAL` or `FAIL`; no executor review begins until the gate is `PASS`.

## Rollback

Rollback means returning governance reads/writes to the known-good JSONL local adapter only in a private single-host environment. Production rollback must not silently downgrade to shared JSONL. If PostgreSQL is unavailable in production, fail closed and preserve pending state rather than dispatching.

## Exit criteria

C10-R2 design is complete when the schema, interfaces, transaction rules, and cutover sequence are reviewed. C10-R3 implementation is complete only when the adapter contract tests pass in shadow mode. Production certification remains separate and requires C10-R4 evidence.
