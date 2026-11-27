# A2A Persistence Interface Plan

## Goal

Introduce a narrow persistence boundary so governance code does not depend directly on JSONL files or PostgreSQL sessions. The current JSONL stores remain the local adapter; a PostgreSQL adapter can be added behind the same interfaces in shadow mode.

## Interfaces

### `AuditStore`

```python
class AuditStore(Protocol):
    def append(self, record: DispatchAudit) -> None: ...
    def read(self, *, tenant_id: str | None = None, mission_id: str | None = None) -> list[dict]: ...
    def integrity_check(self, *, tenant_id: str | None = None) -> dict: ...
```

The PostgreSQL implementation should provide async equivalents and return immutable event projections. `append` must be idempotent on an explicit event ID or idempotency key and must preserve payload, attachment, tenant, actor, and lifecycle hashes.

### `ApprovalStore`

```python
class ApprovalStore(Protocol):
    def issue(self, receipt: ApprovalReceipt) -> ApprovalReceipt: ...
    def get(self, receipt_id: str, *, tenant_id: str) -> dict | None: ...
    def verify_and_consume(self, receipt: ApprovalReceipt, *, tenant_id: str) -> None: ...
    def revoke(self, receipt_id: str, *, tenant_id: str, reason: str = "revoked") -> None: ...
    def expire(self, *, tenant_id: str | None = None) -> int: ...
    def integrity_check(self, *, tenant_id: str | None = None) -> dict: ...
```

The critical operation is `verify_and_consume`: the production adapter must perform validation and the one-time status transition inside one database transaction with a row lock. The JSONL adapter retains current behavior for private development but should receive explicit tenant arguments before production adapter parity is claimed.

### `OutboxStore`

```python
class OutboxStore(Protocol):
    def enqueue(self, *, receipt_id: str, sender_agent_id: str, tenant_id: str, recipient: str, payload_hash: str, attachment_hashes: tuple[str, ...] = (), idempotency_key: str | None = None) -> str: ...
    def get(self, outbox_id: str, *, tenant_id: str) -> dict | None: ...
    def claim(self, *, worker_id: str, limit: int = 1) -> list[dict]: ...
    def revalidate(self, outbox_id: str, *, approval_store: ApprovalStore, agent_policy: Any, payload_hash: str, tenant_id: str) -> dict: ...
    def transition(self, outbox_id: str, *, worker_id: str, expected_version: int, status: str, reason: str | None = None) -> None: ...
    def integrity_check(self, *, tenant_id: str | None = None) -> dict: ...
```

The current JSONL `revalidate` logic should be preserved semantically. The PostgreSQL implementation adds exclusive claims, leases, expected-version checks, idempotency constraints, and transactional audit events.

## Adapter selection

Use an explicit configuration value such as `A2A_PERSISTENCE_BACKEND=jsonl|postgres`. The default remains `jsonl` for local development. Production startup must reject an unrecognized backend and must not silently fall back from PostgreSQL to JSONL.

A feature flag may select PostgreSQL in shadow mode, but shadow writes must fail closed on mismatch rather than silently dropping the comparison. No adapter selection should affect external-action policy; every adapter remains behind the same governance gates.

## Compatibility mapping

| JSONL behavior | PostgreSQL equivalent |
|---|---|
| `sequence` | Identity sequence plus per-stream ordering column |
| Append-only event line | Immutable lifecycle event row |
| Latest event reconstructed as state | Current-state projection table |
| `fcntl` lock | Transaction and row-level lock |
| File integrity check | Constraints, hash checks, sequence checks, reconciliation query |
| Final partial-line tolerance | Database transaction atomicity; malformed input rejected before insert |
| `receipt_id` lookup | Tenant-scoped unique index |
| Outbox terminal status | State transition constraint and event row |

## Testing contract

Both adapters must pass the same contract suite for:

- Tenant isolation and cross-tenant denial.
- Immutable lifecycle events.
- Approval issue/revoke/expire/use and exactly-once consumption under contention.
- Payload and attachment hash binding.
- Outbox claim exclusivity and stale-worker rejection.
- Idempotent retries and duplicate requests.
- Crash recovery and restart readability.
- Audit presence for every blocked or terminal transition.

No PostgreSQL adapter should be considered production-ready until the contract suite runs against a real PostgreSQL instance with at least two concurrent workers.
