# A2A Shadow Reconciliation Model

## Record model

Each mismatch is an immutable JSONL record containing `mismatch_id`, `tenant_id`, `store_pair`, `lifecycle_area`, `expected_state`, `actual_state`, `severity`, `detected_at`, and `certification_blocked`. The mismatch ledger uses the same locked, sequence-numbered JSONL primitive as the existing local stores.

## Reconciliation output

`reconcile_records` compares normalized records by an idempotency key and returns JSON counts plus lists of `missing_in_postgres`, `missing_in_jsonl`, and `divergent` records. Any non-empty mismatch category sets `certification_blocked=true`.

## State policy

A mismatch is preserved for forensic review; it is never overwritten by the other store. The caller must audit the mismatch and stop the shadow operation. A PostgreSQL outage, write error, tenant drift, payload-hash drift, recipient drift, lifecycle-state drift, or sequence/order drift is therefore a blocking condition.

The model supports audit, approval, outbox, worker, Redis delivery, retry, and DLQ lifecycle areas. Full production status still requires wiring this model into every concrete lifecycle call and proving reconciliation against live mirrored state.
