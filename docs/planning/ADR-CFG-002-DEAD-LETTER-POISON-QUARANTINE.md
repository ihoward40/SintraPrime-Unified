# Architecture Decision Record (ADR): ADR-CFG-002 — Dead-Letter + Poison Quarantine

**Status:** Approved  
**Date:** 2026-08-08  
**Author:** Hermes Agent  
**Decision ID:** ADR-CFG-002  
**Scope:** Phase CF-1 / Governance Expansion — Dead-Letter Queue and Poison-Event Quarantine

---

## 1. Context

Failed events must not silently disappear. Repeated-failure events
must not be endlessly retried. The fabric dispatch chain (10+ gates)
processes events deterministically before any model invocation; a
failure in the downstream consumer leaves the event in an undefined
state without explicit tracking.

The directive (§22–23, §140) requires:

- a durable `DeadLetterEvent` with failure tracking and bounded
  retry;
- a poison-event quarantine state with security receipts;
- Mission Control inspection of both.

## 2. Decision

Implement `DeadLetterQueue` backed by `CollaborationStore` (JSON,
consistent with the rest of CF-1 — PostgreSQL deferred to CF-2).

```text
DeadLetterEvent:
  event_id, consumer_id, tenant_id, channel_id
  failure_class, last_error, failure_count
  retry_eligible, max_retries (default 3)
  first_failed, last_failed, quarantined, quarantine_reason
  event_payload

PoisonEvent:
  event_id, consumer_id, reason, quarantine_ts, security_receipt_id
```

Design rules:
- failure is recorded on every consumer exception;
- `retry_eligible` flips to False when `failure_count >= max_retries`;
- `mark_quarantined` creates the poison record; no event-level
  restart after quarantine;
- both are persisted via `CollaborationStore` — proven reloadable;
- a poison event's security receipt is `f"sec_{event_id}"` for
  correlation (a real security receipt follows in CF-2 audit trail).

## 3. Consequences

- Positive: every failed event is inspectable, recoverable, and
  never silently dropped.
- Positive: poison events stop the retry cycle without manual
  intervention.
- Positive: `DeadLetterEvent.quarantined` is a boolean, so
  `list_quarantined()` is a simple filter; no new enum needed.
- Positive: consistent with the existing `CollaborationStore`
  pattern (no new infrastructure).
- Negative: JSON file persistence has no atomicity guarantee across
  concurrent writes — acceptable for CF-1's scope; CF-2 moves to
  PostgreSQL with transactional semantics.
