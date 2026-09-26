# A2A Shadow Dual-Write Results

## Status: PARTIAL

The C10-R3 implementation provides:

- Explicit `jsonl|postgres` backend selection.
- `A2A_PERSISTENCE_SHADOW` configuration validation.
- `ShadowComparator` canonical comparison.
- Fail-closed `ShadowMismatchError` behavior.
- Mismatch tests for missing audit events, wrong approval state, wrong outbox state, payload hash drift, and tenant drift.

The live C10-R4 run validated the PostgreSQL side independently, but full dual-write integration across every audit, approval, outbox, delivery-attempt, and DLQ lifecycle call is not yet wired into the orchestration dependency graph.

## Mismatch behavior

A mismatch is not normalized away. The comparator sends a structured record to its mismatch sink and raises `ShadowMismatchError`. The caller must treat this as a blocking security/certification event. No external execution path is invoked.

## Required next step

C10-R5 must integrate the comparator into all lifecycle calls, persist mismatch records durably, compare JSONL and PostgreSQL projections by correlation ID, and prove that PostgreSQL outages or divergence fail closed. The JSONL adapter remains the local-development default and is not removed.

## Evidence classification

```text
PostgreSQL live local validation: PASS
Shadow comparator and mismatch unit coverage: PASS
Full lifecycle dual-write integration: PENDING
Production authority switch: BLOCKED
External actions: BLOCKED / FAIL-CLOSED
```
