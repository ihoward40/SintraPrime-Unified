# Event Model (Governance Expansion)

The canonical event envelope and dispatch pipeline were established in
the fabric foundation (PR #276, `docs/collaboration/EVENT_MODEL.md`).
This increment adds the failure and governance dimension:

## Failure Path (§22–23)

```text
event dispatched
  → consumer fails
  → DeadLetterQueue.record_failure()
      failure_count += 1
      retry_eligible = failure_count < max_retries (default 3)
  → failure_count >= max_retries
      → quarantined = True
      → PoisonEvent created (QUARANTINED_EVENT)
  → Mission Control can inspect: list_all(), list_quarantined()
```

A failed event never silently disappears. A poison event is never
endlessly restarted.

## Event Dispatch Chain (extended)

```text
validate envelope
→ binding exists?
→ tenant matches?
→ agent quarantined?            (NEW 3a — SKIPPED_QUARANTINE)
→ constitutional invariants?    (NEW 3b — BLOCKED_INVARIANT)
→ event type allowed?
→ actor authorized?
→ loop guard (hop ≤ 4)?
→ dedup (not consumed)?
→ rate limit OK?
→ concurrency slot?
→ kill switch NOT active?
→ ACTIVATE
```

## Idempotency (§19–20)

- Fabric: event consumption keys `hash(agent_id + event_id +
  policy_version)` (DeduplicationPolicy).
- NEW: effect-level idempotency — `EffectService.apply()` returns the
  existing `EffectReceipt` for a repeated `idempotency_key` instead of
  duplicating the effect.

## Event Receipts

Fabric `EventReceipt` records matched/activated/skipped + reason codes
(§49, §116). Governance adds `CausalRecord` (§89) so every action can
be explained: triggering event, matched policy, agent selected,
selection reason, workflow version, lease, approval, provider, effect
receipt, reason code.
