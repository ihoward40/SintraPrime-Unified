# C10-R1 Production Gap Remediation Plan

## Executive decision

Do not extend `fcntl`-locked JSONL stores to a multi-host deployment. The current implementation is acceptable for one Linux host with local disk or a single-host Docker volume, but it is not a distributed coordination mechanism.

For multi-host operation, move audit, approval, and outbox state to **PostgreSQL (preferred)** or a dedicated single-writer persistence service. Redis should remain the delivery transport, not the sole durable governance ledger.

## Remaining production gaps

| Gap | Current state | Remediation owner/action | Exit evidence |
|---|---|---|---|
| Redis ACL/consumer topology | Local ACL and AOF tests pass | Define production users, TLS, key prefixes, worker identity, consumer ownership, retry/DLQ policy | Deployment config plus live failover/restart test |
| Redis persistence/failover | Local AOF restart passes | Reproduce with production AOF/RDB, Sentinel/Cluster, backup, and restore settings | In-flight, DLQ, retry, and ACK-after-restart evidence |
| Identity provider | Static credential map only | Implement signed internal service tokens with rotation, tenant binding, issuer/audience, expiry, and revocation | Token acceptance/rejection matrix and key-rotation evidence |
| Multi-host state locking | Local `fcntl` locking only | Migrate JSONL governance state to PostgreSQL or a single-writer service | Concurrent multi-host writer test with sequence/integrity proof |
| Deployed route inventory | Source routes inventoried | Export production gateway/service mounts and reconcile every route/seam | Signed route inventory plus rerun of C9 matrix |
| Production executor | Disabled | Keep disabled until all preceding gates pass | Explicit enablement decision after C10-R1 PASS |

## Preferred multi-host architecture

```text
A2A HTTP / memory / Redis seams
          |
          v
Governance validation + identity + tenant checks
          |
          +--> PostgreSQL governance ledger
          |      - approval lifecycle
          |      - outbox state
          |      - audit events
          |      - idempotency keys
          |
          +--> Redis delivery transport
                 - inbox
                 - in-flight
                 - ACK/reclaim
                 - retry/DLQ
```

PostgreSQL should provide transaction boundaries, unique constraints, row locks, and durable ordering. Redis should carry messages and delivery state, while the governance ledger remains authoritative for approval, outbox, and audit state.

## Migration sequence

### Phase 1: freeze the current boundary

Keep external actions blocked, Dispatch Desk blocked, and `can_send_external=false` for all profiles. Continue writing JSONL locally only for development evidence. Do not mount the JSONL stores on NFS or SMB.

### Phase 2: introduce a persistence interface

Define repository interfaces for `AuditStore`, `ApprovalStore`, and `OutboxStore`. Preserve the current method semantics—issue, revoke, consume-once, enqueue, revalidate, transition, integrity check—behind the interface. Keep the JSONL implementation as a local development adapter.

### Phase 3: implement PostgreSQL tables and constraints

Use tenant-scoped tables with:

- `event_id` or UUID primary keys.
- Monotonic per-stream sequence numbers.
- Unique `(tenant_id, receipt_id)` and `(tenant_id, idempotency_key)` constraints.
- Approval status transition constraints.
- Outbox status transition constraints.
- `created_at`, `updated_at`, and immutable event timestamps.
- Hash columns for payload, attachments, and approval binding.
- Database-side tenant isolation/RLS where available.

### Phase 4: dual-read/dual-write shadow validation

Write both the JSONL adapter and PostgreSQL in a non-authoritative shadow mode. Compare record counts, hashes, lifecycle states, and sequence/order invariants. Any divergence blocks progression.

### Phase 5: multi-host failure testing

Run two or more worker processes on separate hosts or host-like containers. Test simultaneous approval consumption, duplicate outbox claims, crash after claim, crash before ACK, Redis reclaim, database restart, and network partition. Prove that only one worker can consume an approval or claim an idempotency key.

### Phase 6: cutover and retirement

Make PostgreSQL authoritative, retain JSONL only as an export/debug artifact, and require the deployed route inventory plus C9 rerun before any external capability review. No executor enablement is part of this remediation plan.

## Alternative: single-writer service

If PostgreSQL cannot be introduced, run a single authoritative governance service on one host. All agents submit authenticated requests to that service; only it writes audit, approval, and outbox state. This avoids multi-host file locking but introduces service availability, failover, and API authentication obligations. It is acceptable only with durable storage behind the service and an explicit failover plan.

## Redis production checklist

Before production deployment, record:

1. Redis version and deployment mode.
2. TLS and certificate rotation.
3. ACL users and exact allowed commands.
4. Key prefixes per environment and tenant.
5. Producer and consumer identities.
6. Visibility timeout and retry limit.
7. DLQ retention and operator access.
8. AOF/RDB settings, backup, restore, and failover procedure.
9. Consumer-group or worker-ownership model.
10. Live restart and failover evidence for in-flight, ACKed, retry, and DLQ records.

## Acceptance gates

The multi-host remediation is complete only when:

- No shared JSONL file is used as a multi-host coordination primitive.
- Concurrent approval consumption is exactly once under contention.
- Outbox claims are exclusive and restart-safe.
- Audit events are durable, ordered, tenant-scoped, and integrity-checkable.
- Redis delivery state and the governance ledger reconcile after restart/failover.
- Every blocked or failed path remains auditable.
- External actions remain fail-closed throughout validation.
