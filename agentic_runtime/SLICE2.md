# Slice 2 — Native SintraPrime integration

## Authority rule

**Agents may become more capable without becoming more authoritative.**

This slice connects the provider-neutral runtime to existing SintraPrime
machinery rather than creating new authority stores.

## Added

- `ApprovalGatewayAdapter`: fail-closed bridge to the existing Nova approval gateway.
- `ExecutionLedgerAdapter`: writes runtime events into Nova's existing hash-chained ledger.
- `CapabilityRouterAdapter`: requires VERIFIED capability metadata before using the existing ModelRouter.
- `ContextPackBuilder`: bounded, provenance-labelled, relevance-ranked context packages.
- `GovernedComfyUIAdapter`: policy admission is mandatory before transport invocation.
- `ExecutionBudget`: token and dollar ceilings.
- `Checkpoint` + `ChangedFileManifest`: explicit rollback/change evidence primitives.
- `TestDeltaReceipt`: before/after regression signal.
- `CircuitBreaker`: bounded repeated-failure shutdown.
- `BenchmarkResult` + `ModelPromotionGate`: evidence-backed model admission.

## Not granted

No direct shell authority, unrestricted filesystem writes, push/merge,
deployment, payment, publication, or external-media authority is added here.

## Follow-on integration

The next implementation step should thread `ExecutionBudget` and
`CircuitBreaker` directly through `GovernedExecutionLoop`, add concrete
checkpoint/rollback executors behind approval, and produce a combined
execution receipt referencing the existing ledger hash.
