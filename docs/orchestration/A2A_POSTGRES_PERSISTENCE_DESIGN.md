# C10-R2 PostgreSQL Persistence Design

**Baseline:** `1c5ddbf3bc3e1ed8c6a5cec9ce52a0ebe34e7baf`  
**Status:** DESIGN COMPLETE / PARTIAL  
**Authorization:** Design, documentation, and interface planning only. No executor or external capability is enabled.

## Decision

Use PostgreSQL as the authoritative multi-host governance ledger for audit, approval, and outbox state. Keep the existing JSONL stores as the local-development adapter. Redis remains the delivery transport for inbox, in-flight, ACK, reclaim, retry, and DLQ behavior; it is not the sole authority for approval or governance audit.

The existing portal already provides an async SQLAlchemy/asyncpg database boundary and tenant context through `set_config`. The A2A adapter should use the same async session factory and require an explicit `tenant_id` for every tenant-scoped operation.

## Authority split

| Concern | Authoritative store | Role |
|---|---|---|
| Approval issuance, revocation, expiry, one-time consumption | PostgreSQL | Transactional lifecycle and row lock |
| Audit lifecycle events | PostgreSQL | Immutable append-only ledger |
| Outbox status and claims | PostgreSQL | Durable state machine and exclusive claim |
| Message inbox and in-flight delivery | Redis | Transport delivery state |
| Redis retry and DLQ delivery events | PostgreSQL audit reference plus Redis payload | Reconcile transport to governance ledger |
| Local development | JSONL adapters | Single-host only; never multi-host authority |

## Core invariants

1. Every tenant-scoped row carries `tenant_id`; no query may omit tenant scope.
2. Lifecycle event rows are immutable. Corrections are new events, never updates or deletes.
3. Current-state rows are projections of lifecycle events and are updated in the same transaction as the event insert.
4. Approval consumption uses `SELECT ... FOR UPDATE` on the current receipt row, validates all bindings, changes `issued` to `used`, and commits the lifecycle event atomically.
5. Outbox claiming uses `FOR UPDATE SKIP LOCKED`, a lease owner, a lease expiry, and a version check.
6. Receipt, payload, and attachment hashes are persisted and compared before any transition.
7. Idempotency keys are unique within tenant scope; duplicate requests return the existing state rather than creating a second effect.
8. Every blocked, failed, expired, revoked, used, reclaimed, and DLQ transition writes an audit event in the same transaction where possible.
9. External execution remains disabled until later certification gates pass.

## Transaction rules

### Issue approval

Validate issuer authority and receipt bindings, insert an `approval_events` row with `event_type='issued'`, insert the matching `approval_current_state` row, and insert the audit event in one transaction. A duplicate `(tenant_id, receipt_id)` is rejected.

### Revoke approval

Lock the current state row. Reject a missing or terminal receipt according to policy. Insert a `revoked` event, update current status, and append the audit event atomically.

### Consume approval once

Lock the row with `FOR UPDATE`. Validate receipt ID, tenant, sender, recipient, content hash, attachment hashes, expiry, signature, and current status. Change status to `used`, record the consumer and timestamp, insert a `used` event, and write the audit event before commit. A second transaction observes `used` and fails closed.

### Create outbox intent

Validate that the approval is durable and hash-bound. Insert an `outbox_events` `pending` record and `outbox_current_state` projection with the same idempotency key. Do not mark the record dispatched in this transaction.

### Claim outbox record

In a short transaction, select one eligible `pending` or expired-lease row with `FOR UPDATE SKIP LOCKED`, set `lease_owner`, `lease_until`, increment `claim_version`, append a claim event, and commit. The worker must revalidate approval, tenant, registry policy, and hashes after claiming.

### Mark dispatched, failed, blocked, expired, or DLQ

Require the current lease owner and claim version. Insert a lifecycle event, update the projection, and append an audit event atomically. A stale worker cannot overwrite a newer state.

### Redis delivery reconciliation

For send, ACK, reclaim, retry, and DLQ events, persist a delivery reference with message ID, delivery ID, tenant, agent, retry count, and payload hash. Reconciliation must be idempotent on `(tenant_id, delivery_id, event_type, attempt_number)`.

## Tenant isolation

The adapter must set `app.tenant_id` on every database transaction, matching the existing portal database convention. Enable PostgreSQL row-level security for tenant-scoped tables in production. Application predicates remain mandatory even with RLS. Cross-tenant IDs must return the same safe denial behavior as an unknown ID and must not reveal existence.

## Failure and recovery model

A committed database transaction is the source of truth. If a worker crashes before Redis ACK, Redis reclaim can redeliver; the delivery ID and idempotency key prevent duplicate governance transitions. If Redis is unavailable after an outbox claim, the lease expires and another worker can reclaim the record. If PostgreSQL is unavailable, the worker must not send or acknowledge governed work.

## Non-goals for C10-R2

This design does not implement the adapter, create migrations, connect to a production database, enable an executor, activate Dispatch Desk, or set any `can_send_external` capability.
