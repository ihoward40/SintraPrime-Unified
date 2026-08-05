# ADR-MC-001: Executor Continuation After Lease Expiry

**Status:** DRAFT — NOT YET RATIFIED
**References:** ADR-002 Section 2.5 (Sigma continuation condition)
**Supersedes:** None
**Superseded by:** None

## 1. Context

ADR-002 Section 2.5 defines the Sigma continuation condition: the circumstances under which an executor may optionally continue work after its lease has expired. The condition is gated by `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE`, which is currently **BLOCKED**. This ADR is required to define the precise criteria that must be satisfied before the gate can be unblocked.

The gate exists to prevent uncontrolled speculative continuation by executors when the Brain is unavailable or a lease has expired. Without explicit criteria, continuation could produce conflicting results, lost updates, or unreconciled divergent state.

## 2. Decision

Define five criteria that must be satisfied before `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE` may be unblocked. The gate remains BLOCKED until this ADR is ratified and all five criteria are implemented.

### 2.1 Criterion 1 — Explicit Continuation Permission

Define explicit criteria for when optional executor continuation is permitted after lease expiry. Continuation must not be the default behavior. The executor must determine, from locally available and verifiable signals, that continuation is permitted. At minimum:

- The lease must have expired (not been revoked or cancelled).
- The Brain must be unreachable for a defined grace period.
- The task must be non-cancellable at the point of expiry (no pending cancellation in the local cache of the ledger).
- Continuation must be optional — the executor may always choose to stop safely.

### 2.2 Criterion 2 — Local State Sufficiency

Define what constitutes "local state sufficient to complete the task." The executor must be able to verify that it holds:

- The full command payload required to complete the task.
- Any dependent state (inputs, configuration, prior step outputs) cached locally.
- A deterministic completion path — the task must be completable without further Brain interaction.
- A bounded completion envelope (time, resource) so continuation cannot run indefinitely.

If any required state is missing or ambiguous, continuation is NOT permitted.

### 2.3 Criterion 3 — Mandatory Completion Reporting on Brain Recovery

When the Brain recovers, any executor that continued during unavailability MUST report its completion outcome. The report must include:

- The command id.
- The executor id.
- The continuation start and end timestamps.
- The final outcome (success, failure, partial).
- Any artifacts or result references produced.

Reporting is mandatory regardless of outcome. Silent continuation is forbidden.

### 2.4 Criterion 4 — Reconciliation Between Executor State and Brain Ledger

On recovery, the Brain must reconcile executor-reported state against its ledger. The reconciliation must:

- Compare executor-reported outcomes against the ledger's last-known state.
- Detect divergence (e.g., the Brain believes the command was cancelled, but the executor reports success).
- Produce a reconciliation record capturing the divergence, if any.
- Define a resolution policy for each divergence class (e.g., executor result wins, Brain wins, manual review required).

Reconciliation must be auditable and idempotent.

### 2.5 Criterion 5 — Conflicting Results From Multiple Executors

If multiple executors continued during unavailability, conflicting results must be handled. The policy must define:

- Detection of conflicts (same command id, different executors, different outcomes).
- A deterministic conflict resolution rule (e.g., last-write-wins by timestamp, or first-completed wins, or manual review).
- A conflict record capturing all competing results.
- Notification of the conflict to operators/Brain for review.

No silent conflict resolution is permitted. All conflicts must be recorded.

## 3. Consequences

Until this ADR is ratified and the five criteria are implemented:

- `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE` remains **BLOCKED**.
- All cancellation controls remain **DISABLED**.
- `is_cancellation_blocked()` returns `True`.
- Executors must not continue after lease expiry.
- Phase 3B remains blocked pending this ADR.

## 4. Status

| Item | State |
|------|-------|
| ADR-MC-001 | DRAFT — not ratified |
| SIGMA_LEASE_EXPIRY_CONTINUATION_GATE | BLOCKED |
| Cancellation controls | DISABLED |
| Phase 3B | BLOCKED |

## 5. Open Questions

- What is the exact grace period before continuation is permitted? (To be resolved in ratification.)
- Should the reconciliation policy be configurable per tenant or global? (To be resolved.)
- What telemetry must executors emit during continuation? (To be resolved.)