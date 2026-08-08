# Failure and Recovery Model

## Dead-Letter Queue (§22)

```text
DeadLetterEvent:
  event_id, consumer_id, tenant_id, channel_id
  failure_class, last_error, failure_count
  retry_eligible, max_retries (3), first_failed, last_failed
  quarantined, quarantine_reason, event_payload
```

- Failure is persisted immediately (JSON store) — a failed event
  never disappears.
- Retry is bounded: `retry_eligible = failure_count < max_retries`.
- Mission Control can inspect `list_all()` and `list_quarantined()`.

## Poison-Event Quarantine (§23)

When retries are exhausted (or an event is explicitly marked), the
event transitions to `PoisonEvent` (QUARANTINED_EVENT):

```text
event_id, consumer_id, reason, quarantine_ts, security_receipt_id
```

No endless restart. A security/operations receipt is emitted.
Proof: `test_retry_bounded`, `test_poison_event_quarantined`.

## Effect Receipts and Idempotency (§20, §117)

`EffectService.apply()`:

- First call with `idempotency_key` → creates immutable
  `EffectReceipt` (operation, target, before/after state,
  authorization, result, hash).
- Retry with the same key → **returns the existing receipt**; the
  effect is not duplicated.
- `verify_hash()` detects tampering.
Proof: `test_idempotent_retry`, `test_hash_verify`.

## Compensation Workflows (§46)

Reversible operations define compensating actions (rollback/restore)
in Phase CF-2 where effect services execute; CF-1 provides the
receipt/audit substrate. Irreversible operations are never claimed
compensable.

## Disaster Recovery (§45)

Recoverable state now includes: dead-letter entries, poison events,
agent quarantine records, capability leases, effect receipts, causal
records, uncertainties, assumptions — all JSON-persisted via
`CollaborationStore` and proven reloadable after "restart"
(TestPersistenceRestart suite).

## Chaos Testing (§44)

Deferred to CF-2+ (killing workers, dropping DB, interrupting
queues requires the runtime surfaces). The persistence-restart suite
covers the restart/reload axis available in CF-1.
