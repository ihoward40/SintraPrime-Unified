# PostgreSQL Concurrency Evidence

## Approval consumption

Two independent async SQLAlchemy sessions attempted to consume the same issued receipt concurrently. The adapter selected the current row with `FOR UPDATE`, validated the receipt, updated it to `used`, and committed one lifecycle transition.

Observed result:

```text
one worker: won
one worker: lost with PermissionError after the row lock released
```

No second `used` transition was accepted.

## Outbox claims

Two independent workers attempted to claim the same pending outbox row concurrently. The adapter used:

```sql
FOR UPDATE SKIP LOCKED
```

Observed result:

```text
claim counts: [0, 1]
```

Exactly one worker received the row. The other worker skipped the locked row and received no claim.

## Idempotency

A second enqueue using the same tenant-scoped idempotency key failed with PostgreSQL uniqueness enforcement on `(tenant_id, idempotency_key)`.

## Stale lease rejection

After the winning claim, a different worker attempted a terminal transition using the same claim version but the wrong lease owner. The guarded update affected no row and the adapter raised `PermissionError`.

## Transaction rollback

An intentional exception after an audit insert rolled back the transaction. A subsequent query confirmed that the probe row was absent.

## Remaining proof

The local concurrency evidence does not prove behavior across the production pooler, failover topology, network partitions, worker process crashes, or a real multi-host deployment. Those remain C10-R5/topology and recovery work.
