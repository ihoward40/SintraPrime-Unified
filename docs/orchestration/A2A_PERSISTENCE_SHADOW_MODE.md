# A2A Persistence Shadow Mode

## Contract

JSONL remains the primary local-development adapter. PostgreSQL is opt-in through:

```text
A2A_PERSISTENCE_BACKEND=postgres
A2A_PERSISTENCE_SHADOW=true
```

The backend configuration is explicit. Invalid values fail configuration loading, and shadow mode cannot be enabled with the JSONL backend. There is no silent fallback from PostgreSQL to JSONL.

## Comparison behavior

`ShadowComparator` canonicalizes mirrored records while ignoring storage-local sequence/timestamp fields. It compares tenant, receipt, lifecycle status, actor, recipient, payload hash, attachment hashes, approval binding, and terminal reason fields. A mismatch:

1. Is sent to the configured mismatch sink.
2. Raises `ShadowMismatchError`.
3. Must be recorded as a security/audit event by the integration layer.
4. Blocks certification and any authority switch.

A mismatch must never be ignored, overwritten by the local adapter, or converted into a successful dispatch.

## Required integration pattern

For each lifecycle operation:

```text
validate request
  -> write JSONL lifecycle event
  -> write PostgreSQL lifecycle event in the same logical operation
  -> read normalized projections
  -> compare
  -> audit mismatch and fail closed on divergence
```

The production implementation should use a correlation ID so both stores and the mismatch audit record can be joined. If PostgreSQL is unavailable, the shadow operation is considered failed; external action remains blocked.

## Exit gates before authority switch

- Both adapters pass the same contract suite.
- Two concurrent approval consumers produce exactly one `used` transition.
- Two outbox workers produce one exclusive claim.
- Stale lease owners are rejected.
- Wrong tenant and hash drift are rejected in both adapters.
- PostgreSQL RLS is enabled and tested.
- Restart and crash recovery preserve immutable events and projections.
- Every shadow mismatch is durable and visible.
- Full repository suite and C9 bypass matrix pass.
- External actions remain blocked throughout.

C10-R3 implements the boundary and deterministic primitives. C10-R4 is required for live PostgreSQL shadow validation and dual-write proof.
