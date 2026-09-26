# A2A Shadow Mismatch Policy

## Default severity

All shadow mismatches are `critical` by default because divergence between JSONL governance state and PostgreSQL governance state can change approval, tenant, hash, or delivery semantics. Every mismatch has `certification_blocked=true`.

## Blocking conditions

Certification is blocked for missing records, divergent lifecycle states, payload or attachment hash drift, tenant or recipient drift, idempotency-key drift, sequence/order drift, database write failures, and any inability to compare the two stores.

## Required response

The system must append a durable mismatch record, retain both observed states, emit an audit event when the integration layer is connected, stop the mirrored lifecycle operation, and require human review of the evidence. It must not silently retry into a different state, choose whichever store is newer, fall back from PostgreSQL to JSONL in production, or enable external execution.

## Current implementation boundary

The policy and durable mismatch primitive are implemented and tested. Full lifecycle integration across every approval, outbox, worker, Redis, retry, and DLQ transition remains the next integration gate. External actions remain fail-closed throughout.
