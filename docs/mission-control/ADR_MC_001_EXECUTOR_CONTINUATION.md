# ADR-MC-001: Executor Continuation After Lease Expiry

**Status:** DRAFT — NOT YET RATIFIED
**References:** ADR-002 Section 2.5 (Sigma continuation condition)
**Baseline:** mission-control-foundation-v1 at 97bd539f82ee9099003b0ba5c3729092bf470604
**Supersedes:** None
**Superseded by:** None

## 1. Context

ADR-002 Section 2.5 defines the Sigma continuation condition: the circumstances under which an executor may optionally continue work after its lease has expired. The condition is gated by `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE`, which is currently **BLOCKED**. This ADR is required to define the precise criteria that must be satisfied before the gate can be unblocked.

The gate exists to prevent uncontrolled speculative continuation by executors when the Brain is unavailable or a lease has expired. Without explicit criteria, continuation could produce conflicting results, lost updates, unreconciled divergent state, or command authority leakage into executors.

This ADR is a policy and systems-design document. It defines behavior, invariants, protocols, and acceptance tests. It does not implement any code, change runtime behavior, enable cancellation, enable command authority, modify Mission Control, begin Phase 3B, or deploy anything.

## 2. Decision

Before `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE` may be unblocked, the following architecture and policy must be ratified and implemented.

### 2.1 Executor Lease Lifecycle

Every command dispatched to an executor is associated with a lease. The lease is the temporal and authority boundary within which the executor may perform work on behalf of the Brain.

#### 2.1.1 Lease Acquisition

- The Brain issues a lease to exactly one executor per command at a time.
- The lease contains:
  - `command_id` — the command being executed
  - `executor_id` — the executor holding the lease
  - `tenant_id` — the tenant scope
  - `issued_at` — lease issuance timestamp
  - `expires_at` — lease expiration timestamp
  - `lease_token` — cryptographically signed token
  - `policy_snapshot_id` — identifier of the policy version in effect
  - `side_effect_permitted` — whether the command may produce external effects
  - `continuation_policy` — one of `STOP`, `CONTINUE_IF_ELIGIBLE`, or `DELEGATE_TO_BACKUP`
- The executor must present a valid, unexpired lease token to perform any work.
- Lease acquisition is logged as an immutable audit event with causation link to the dispatch event.

#### 2.1.2 Lease Renewal

- The executor may request lease renewal before expiry.
- The Brain grants renewal only if:
  - the command has not been cancelled,
  - the executor is still the lease holder,
  - the command has not exceeded its maximum execution duration,
  - the policy snapshot has not been superseded,
  - the Brain is available.
- Renewal extends `expires_at` and produces a new signed lease token.
- The previous lease token is revoked and must not be honored by downstream systems.

#### 2.1.3 Lease Expiry

- A lease expires when `expires_at` is reached or when the Brain explicitly revokes it.
- Upon expiry, the executor loses authority to perform work on the command.
- Expiry is logged as an immutable audit event.
- Expiry alone does **not** permit continuation. Continuation requires all eligibility criteria in Section 2.3.

### 2.2 Brain Outage Detection

An executor must not declare a Brain outage based solely on a single failed request. Detection must be robust against transient failures.

#### 2.2.1 Detection Signals

The executor monitors the following signals:

| Signal | Source | Threshold |
|---|---|---|
| Heartbeat acknowledgement | Brain heartbeat endpoint | Missing for `brain_heartbeat_miss_threshold` consecutive intervals |
| Lease renewal rejection | Brain lease endpoint | Rejected as `BRAIN_UNAVAILABLE` for `lease_rejection_threshold` attempts |
| Command status query failure | Brain command endpoint | Failed with timeout or `UNAVAILABLE` for `status_query_threshold` attempts |
| Outage beacon | Peer executors or witness nodes | Quorum of witnesses reports Brain unavailability |
| Policy broadcast silence | Brain policy channel | No policy broadcast for `policy_silence_threshold` |

#### 2.2.2 Detection Rules

- Brain outage is declared only when at least **two independent signals** cross their thresholds.
- One of the two signals must be either heartbeat acknowledgement or command status query failure.
- The grace period before outage declaration is at least `brain_outage_grace_period` (default: 30 seconds, configurable per tenant with upper bound).
- A declared outage must be persisted locally with timestamp, signals observed, and lease token fingerprint.

### 2.3 Continuation Eligibility

Continuation is **optional and pessimistic**. Even when all criteria are met, the executor may choose to stop safely. Continuation is permitted only when all of the following are true.

| Criterion | Requirement | Verification |
|---|---|---|
| Lease expired | Lease `expires_at` reached or exceeded | Local clock + signed lease token |
| Brain outage declared | Two independent signals crossed thresholds | Outage record with signals |
| No revocation observed | No lease revocation received during grace period | Local cache of revocation stream |
| No cancellation pending | No cancellation command in local ledger cache | Cached command events up to lease expiry |
| Local state sufficient | All required inputs and deterministic path available | Self-check against task manifest |
| Side-effect safety | Continuation policy allows external effects for this command | Lease `side_effect_permitted` and `continuation_policy` |
| Policy snapshot valid | Policy snapshot in lease has not been superseded | Policy version registry cache |
| Bounded continuation | Estimated completion within `max_continuation_duration` | Task envelope estimate |
| Tenant isolation | Executor tenant matches command tenant | Lease `tenant_id` and execution context |
| Audit capability | Executor can emit continuation audit events and receipts | Local audit log buffer + recovery queue |

If any criterion is not met, the executor must stop and enter safe-hold state.

### 2.4 Continuation Limits

Continuation is bounded to prevent uncontrolled speculative execution.

| Limit | Default | Purpose |
|---|---|---|
| `max_continuation_duration` | 5 minutes | Bound how long an executor may continue without Brain contact |
| `max_continuation_operations` | 1 | Bound how many discrete operations an executor may perform |
| `max_continuation_attempts_per_command` | 1 | Prevent repeated continuation attempts for the same lease |
| `max_concurrent_continuations_per_executor` | 3 | Prevent an executor from continuing many commands simultaneously |
| `side_effect_cooldown_after_continuation` | Until reconciliation | Prevent additional external effects before Brain reconciliation |
| `tenant_max_continuation_rate` | 10 per minute | Tenant-level circuit breaker |

All limits are configurable per tenant subject to platform maximums. A platform break-glass policy may reduce limits but never increase them beyond the platform maximum.

### 2.5 Idempotency Requirements

Continuation must not produce duplicate effects that violate command semantics.

- Every operation performed during continuation must carry the original command idempotency key.
- Every operation must be tagged with a `continuation_id` unique to the continuation attempt.
- Downstream systems must be able to recognize and suppress duplicate operations by `(command_id, idempotency_key, continuation_id)`.
- If the executor cannot guarantee idempotency of an operation, that operation must not be performed during continuation.
- The executor must maintain a local continuation journal recording every operation attempted, its input, output, success/failure, and timestamp.

### 2.6 Reconciliation Protocol

When the Brain recovers, all continuations must be reconciled before the command reaches a terminal state.

#### 2.6.1 Recovery Detection

- The Brain or a witness node declares recovery when the Brain has been available and responsive for at least `brain_recovery_confirmation_period` (default: 10 seconds).
- Executors are notified of recovery through the heartbeat channel.
- Executors may also detect recovery by successful lease renewal for another command.

#### 2.6.2 Completion Reporting

Within `completion_report_deadline` of recovery detection, every executor that continued must report:

| Field | Type | Description |
|---|---|---|
| `command_id` | string | The continued command |
| `executor_id` | string | The continuing executor |
| `continuation_id` | string | Unique continuation attempt |
| `lease_token_fingerprint` | string | Fingerprint of the expired lease token |
| `continuation_started_at` | datetime | When continuation began |
| `continuation_ended_at` | datetime | When continuation ended |
| `final_state` | enum | `SUCCEEDED`, `FAILED`, `ABORTED`, `TIMEOUT` |
| `operations_performed` | integer | Count of operations performed |
| `result_digest` | hash | Digest of the completion result |
| `evidence_refs` | list | References to any produced artifacts |
| `continuation_journal` | encrypted blob | Full continuation journal |
| `audit_receipt_id` | string | Immutable audit receipt for the continuation |

Reporting is mandatory regardless of outcome. Silent continuation is forbidden.

#### 2.6.3 Reconciliation Steps

1. The Brain collects all continuation reports for a command.
2. The Brain compares reports against its ledger last-known state.
3. The Brain evaluates each report against the continuation eligibility criteria (Section 2.3) retroactively.
4. The Brain classifies the result:
   - `VALID_CONTINUATION` — all criteria met, single report, no conflict.
   - `VALID_BUT_RECONCILED` — all criteria met, but executor result differs from Brain expectation; resolution policy applied.
   - `INVALID_CONTINUATION` — criteria were not met at continuation time; executor exceeded authority.
   - `CONFLICTING_REPORTS` — multiple reports with irreconcilable differences.
5. The Brain emits a reconciliation record with classification and resolution.
6. The command transitions to a reconciled terminal state or to `MANUAL_REVIEW_REQUIRED`.

### 2.7 Replay Semantics

Replay is the re-execution of a command after Brain recovery. It is distinct from continuation.

- Replay may occur only when the Brain explicitly authorizes it.
- Replay uses a new lease, a new idempotency context, and a fresh policy snapshot.
- The Brain must mark the original command as `REPLAYED` and link the replay command through causation.
- Executors must not autonomously replay a command during continuation.
- A continuation that fails may be followed by a Brain-authorized replay; the continuation journal informs the replay parameters.

### 2.8 Duplicate Suppression

The system must suppress duplicate work across continuation, replay, and normal execution.

| Layer | Key | Action |
|---|---|---|
| Brain dispatch | `(command_id, executor_id, lease_token)` | Reject duplicate dispatch for active lease |
| Executor operation | `(command_id, idempotency_key, continuation_id)` | Skip already-performed operations |
| Downstream system | `(idempotency_key, continuation_id)` | Refuse duplicate external effects |
| Brain reconciliation | `(command_id, continuation_id)` | Reject duplicate continuation reports |

### 2.9 Completion Receipts

Every continuation must produce an immutable completion receipt.

- The receipt is generated by the executor at continuation end.
- The receipt contains the fields in Section 2.6.2 and a cryptographic hash.
- The receipt is signed by the executor's identity key.
- The receipt is submitted to the Brain during reconciliation.
- The receipt becomes part of the command's causation chain.
- Receipts are tamper-evident; any modification invalidates the signature.

### 2.10 Split-Brain Handling

Split-brain occurs when multiple executors independently conclude that the Brain is unavailable and continue the same command, or when the Brain recovers while executors are still continuing.

#### 2.10.1 Detection

- Multiple continuation reports for the same `command_id` with different `continuation_id` values.
- Continuation reports arriving while the Brain considers the command still active.
- Divergent `result_digest` values for the same command.

#### 2.10.2 Resolution

| Scenario | Resolution |
|---|---|
| Multiple executors continued, results agree | First completed wins; later reports are marked `DUPLICATE_AGREED` and linked to the winning continuation |
| Multiple executors continued, results conflict | `MANUAL_REVIEW_REQUIRED`; conflict record captures all reports; downstream effects frozen |
| Brain recovers while continuation active | Executor receives recovery signal and must stop; already-completed operations are reported; in-progress operations are aborted idempotently |
| Brain never recovers within `max_continuation_duration` | Executor must stop; partial results recorded; manual recovery process initiated |

No silent conflict resolution is permitted. All conflicts are recorded and surfaced.

### 2.11 Audit Chain Requirements

The continuation event must be fully traceable in the causation chain.

- Lease expiry event.
- Brain outage declaration event.
- Continuation eligibility decision event.
- Each operation performed during continuation.
- Continuation completion event and receipt.
- Brain recovery detection event.
- Reconciliation event.
- Terminal state event.

All events link to the previous event hash, forming a chain. The chain is capped at `MAX_CAUSATION_LINKS` with truncation metadata.

### 2.12 Tenant Isolation Guarantees

Continuation respects tenant boundaries.

- An executor may only continue commands within its own tenant scope.
- Continuation limits are enforced per tenant.
- Continuation reports are routed to the tenant's Brain partition.
- Cross-tenant continuation is forbidden and treated as a security event.
- Tenant-level policies may disable continuation entirely (`continuation_policy = STOP`).

### 2.13 Recovery Protocol

The recovery protocol governs how the system returns to normal operation after Brain recovery.

1. **Recovery detection** — Brain availability confirmed for `brain_recovery_confirmation_period`.
2. **Report collection** — Brain receives all pending continuation reports within `completion_report_deadline`.
3. **Reconciliation** — Brain classifies and resolves each continuation (Section 2.6).
4. **Conflict freeze** — Conflicting results freeze downstream effects until resolved.
5. **Manual review queue** — Conflicts and invalid continuations are enqueued for operator review.
6. **Lease reissue** — Valid commands that did not complete during continuation receive new leases for replay if authorized.
7. **Policy refresh** — All executors refresh policy snapshots before accepting new work.
8. **Audit completion** — All continuation events are finalized in the audit log.
9. **Gate evaluation** — Only after the implementation is certified may `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE` be evaluated for unblocking.

## 3. Sequence Diagrams

### 3.1 Normal Lease Lifecycle

```text
Brain          Executor          Downstream
 |               |                    |
 |-- issue lease-->|                  |
 |               |-- perform work --->|
 |               |<--- result --------|
 |<-- renew -----|                  |
 |-- renew ok --->|                  |
 |               |-- perform work --->|
 |               |<--- result --------|
 |<-- complete --|                  |
```

### 3.2 Lease Expiry with Continuation

```text
Brain          Executor          Downstream
 |               |                    |
 |-- issue lease-->|                  |
 |               |-- perform op 1 ---->|
 |               |<--- result 1 -------|
 |   lease       |                    |
 |   expires     |                    |
 |   (no contact)|                    |
 |               |== declare outage ==|
 |               |== check eligibility |
 |               |== continue op 2 -->|
 |               |<== result 2 --------|
 |               |== generate receipt |
 |   recovers    |                    |
 |<== submit report|                  |
 |== reconcile ==|                    |
 |== terminal ===|                  |
```

### 3.3 Reconciliation After Recovery

```text
Executor A      Executor B       Brain
   |               |               |
   |<== declare outage ===========|
   |== continue command X =======|
   |               |== also declare outage |
   |               |== continue command X ==|
   |== report X-A =|==============>|
   |               |== report X-B ========>|
   |               |<== detect conflict ===|
   |<== freeze ===|               |
   |               |<== manual review queue |
```

## 4. State-Machine Diagrams

### 4.1 Lease State Machine

```text
         +---------+
         | ISSUED  |
         +---------+
              |
              v
         +---------+     renew     +---------+
    +--->| ACTIVE  |<------------->| RENEWED |
    |    +---------+               +---------+
    |         |
  expire      |
    |         v
    |    +---------+
    +--->| EXPIRED |
         +---------+
              |
              | outage + eligible
              v
         +-------------+
         | CONTINUING  |----> COMPLETED (with receipt)
         +-------------+      ABORTED
              |
              | recovery
              v
         +-------------+
         | RECONCILING |
         +-------------+
              |
     +--------+--------+--------+
     v        v        v        v
   VALID  RECONCILED INVALID CONFLICT
```

### 4.2 Command State Machine (with Continuation Path)

```text
        +---------+
        | PENDING |
        +---------+
             |
             v
        +---------+
        |LEASED   |
        +---------+
             |
    +--------+--------+
    |                 |
 complete          expire
    |                 |
    v                 v
+---------+     +---------+     +-------------+
|SUCCEEDED|     |EXPIRED  |---->|CONTINUING   |
| FAILED  |     +---------+     +-------------+
+---------+           ^              |
                        |              |
                 reconcile             |
                        |              v
                   +---------+   +---------+
                   |RECONCILED|   |ABORTED  |
                   |INVALID   |   +---------+
                   |CONFLICT  |
                   +---------+
```

## 5. Timing Diagrams

### 5.1 Grace Period and Continuation Window

```text
Time -->
|---- lease active ----|-- grace --|-- continuation window --|-- report deadline --|
0                      T1          T2                          T3                    T4

T0: Lease issued
T1: Lease expires
T2: Brain outage declared (after grace period)
T3: Latest permitted continuation end (T2 + max_continuation_duration)
T4: Completion report deadline (after recovery)
```

### 5.2 Overlapping Continuation and Recovery

```text
Executor A:  [continue X]----------[receipt]--[report]
Executor B:       [continue X]----------[receipt]--[report]
Brain:            [unavailable]...............[recovery]--[reconcile]
Time ->
```

## 6. Failure Matrices

### 6.1 Lease Expiry Decision Matrix

| Lease State | Brain Available | Eligible | Executor Decision | Next State |
|---|---|---|---|---|
| Expired | Yes | N/A | Stop and request new lease | EXPIRED /> RENEWED or FAILED |
| Expired | No (outage) | Yes | May continue (optional) | CONTINUING |
| Expired | No (outage) | No | Stop | EXPIRED /> ABORTED |
| Expired | Unknown | Unknown | Stop | EXPIRED /> ABORTED |
| Revoked | Any | N/A | Stop | REVOKED /> FAILED |
| Cancelled | Any | N/A | Stop | CANCELLED |

### 6.2 Continuation Outcome Matrix

| Outcome | Receipt | Reconciliation Class | Downstream Effects | Command State |
|---|---|---|---|---|
| Success, single executor | Valid | VALID_CONTINUATION | Apply | SUCCEEDED |
| Success, but Brain expected different | Valid | VALID_BUT_RECONCILED | Apply per resolution policy | RECONCILED /> SUCCEEDED or REVIEW |
| Success, multiple executors agree | Valid | VALID_CONTINUATION (duplicate agreed) | Apply once | SUCCEEDED |
| Success, multiple executors conflict | Valid each | CONFLICTING_REPORTS | Freeze | MANUAL_REVIEW_REQUIRED |
| Failure during continuation | Valid | VALID_CONTINUATION or INVALID | None | FAILED or RECONCILED |
| Continuation without eligibility | Valid | INVALID_CONTINUATION | None, executor flagged | INVALID /> REVIEW |
| No receipt produced | Missing | INVALID_CONTINUATION | None | INVALID /> REVIEW |

### 6.3 Threat Model

| Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Executor continues without Brain outage | Medium | High | Require two independent outage signals; grace period; local cache verification |
| Executor continues without local state sufficiency | Medium | High | Self-check against task manifest; deterministic path requirement |
| Multiple executors continue same command | Low | Critical | Lease exclusivity; conflict detection; manual review for conflicts |
| Executor produces duplicate external effects | Medium | High | Idempotency keys; continuation_id; downstream duplicate suppression |
| Executor lies about continuation outcome | Low | High | Signed receipts; continuation journal; result digest; audit chain |
| Brain recovers during continuation | Medium | Medium | Recovery signal; stop in-progress ops; report completed ops; reconcile |
| Cross-tenant continuation | Low | Critical | Tenant-scoped leases; tenant isolation enforcement; security event |
| Continuation runs unbounded | Low | High | max_continuation_duration; max_continuation_operations; per-tenant rate limits |
| Policy snapshot superseded during continuation | Low | High | Policy version check; policy broadcast silence detection |
| Silent continuation | Medium | High | Mandatory completion reporting; receipt requirement; reconciliation deadline |

## 7. Invariants

The following invariants must hold at all times. Any violation is a security or correctness event.

| # | Invariant | Enforcement |
|---|-----------|-------------|
| 1 | An executor without a valid lease cannot produce authoritative command effects. | Lease token validation |
| 2 | Continuation is never the default behavior. | Eligibility check; optional stop |
| 3 | Continuation cannot exceed its bounded envelope. | `max_continuation_duration`; `max_continuation_operations` |
| 4 | Every continuation produces an immutable, signed receipt. | Executor receipt generation; signature verification |
| 5 | Every continuation is reconciled before the command reaches terminal state. | Reconciliation protocol |
| 6 | Conflicting continuation results never resolve silently. | Conflict record; manual review queue |
| 7 | Cross-tenant continuation is impossible. | Tenant-scoped leases and policies |
| 8 | Idempotency is preserved across continuation, replay, and normal execution. | Idempotency keys; continuation_id; duplicate suppression layers |
| 9 | Audit causation chain is complete and tamper-evident. | Hash chaining; MAX_CAUSATION_LINKS cap with warnings |
| 10 | Policy snapshot validity is checked before continuation and before applying effects. | Policy version registry; lease policy_snapshot_id |

## 8. Glossary

| Term | Definition |
|---|---|
| Brain | The central command authority that owns intent, dispatch, and cancellation state under ADR-002. |
| Executor | A worker process that performs command work under a lease from the Brain. |
| Lease | A time-bound, signed grant of authority from the Brain to an executor for a specific command. |
| Lease expiry | The moment a lease's `expires_at` is reached or the lease is revoked. |
| Continuation | Optional executor work performed after lease expiry during a declared Brain outage. |
| Brain outage | A declared state where the Brain is unreachable, confirmed by two independent signals. |
| Grace period | The waiting time after lease expiry before an outage can be declared. |
| Idempotency key | A key that identifies a command such that duplicate execution produces the same effect once. |
| Continuation_id | A unique identifier for a single continuation attempt of a command. |
| Reconciliation | The process by which the Brain merges executor-reported continuation results with its ledger. |
| Replay | A Brain-authorized re-execution of a command using a new lease and idempotency context. |
| Split-brain | A condition where multiple executors independently continue the same command. |
| Policy snapshot | The version of execution policy in effect when the lease was issued. |
| Completion receipt | An immutable, signed record of a continuation's outcome. |
| Causation chain | A hash-linked sequence of events showing command lineage. |
| Sigma gate | `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE`, currently BLOCKED. |

## 9. Implementation Prerequisites

This section lists what must exist before implementation of this ADR may begin. It does not implement anything.

### 9.1 Required Components

| Component | Purpose | Status |
|---|---|---|
| Signed lease token service | Issue, renew, and revoke signed lease tokens | Not implemented |
| Brain heartbeat endpoint | Allow executors to detect Brain availability | Not implemented |
| Executor local state cache | Store inputs, configuration, and prior step outputs | Not implemented |
| Revocation stream | Publish lease revocations and cancellations | Not implemented |
| Policy version registry | Track policy snapshots and supersession | Not implemented |
| Continuation journal store | Immutable per-continuation operation log | Not implemented |
| Completion receipt service | Generate and verify signed continuation receipts | Not implemented |
| Reconciliation engine | Classify and resolve continuation reports | Not implemented |
| Conflict review queue | Surface conflicting continuation results for operators | Not implemented |
| Audit event pipeline | Append continuation events to causation chain | Not implemented |
| Downstream idempotency layer | Suppress duplicate external effects | Not implemented |

### 9.2 Required Configuration

| Setting | Description |
|---|---|
| `brain_heartbeat_miss_threshold` | Consecutive missed heartbeats before outage signal |
| `lease_rejection_threshold` | Consecutive `BRAIN_UNAVAILABLE` lease responses before outage signal |
| `status_query_threshold` | Consecutive failed status queries before outage signal |
| `policy_silence_threshold` | Duration without policy broadcast before outage signal |
| `brain_outage_grace_period` | Minimum time after lease expiry before outage declaration |
| `brain_recovery_confirmation_period` | Duration of confirmed Brain availability before recovery declaration |
| `max_continuation_duration` | Maximum time an executor may continue |
| `max_continuation_operations` | Maximum operations per continuation |
| `max_continuation_attempts_per_command` | Maximum continuation attempts per command |
| `max_concurrent_continuations_per_executor` | Maximum simultaneous continuations per executor |
| `completion_report_deadline` | Time after recovery to submit continuation report |
| `tenant_max_continuation_rate` | Tenant-level continuation rate limit |

### 9.3 Required Tests

| Test | Purpose |
|---|---|
| Lease acquisition/renewal/revocation | Verify lease lifecycle |
| Brain outage declaration | Verify two-signal rule and grace period |
| Continuation eligibility | Verify all criteria must be met |
| Continuation bounds | Verify duration, operation, and concurrency limits |
| Idempotency across continuation | Verify duplicate suppression |
| Completion receipt | Verify signature and immutability |
| Reconciliation | Verify classification and resolution |
| Split-brain conflict | Verify conflict detection and manual review |
| Cross-tenant isolation | Verify tenant boundary enforcement |
| Recovery protocol | Verify full recovery sequence |
| Audit causation chain | Verify hash-linked event sequence |

## 10. Non-Goals

The following are explicitly out of scope for this ADR and must not be implemented under this ADR.

- Implementing the lease service.
- Implementing the heartbeat protocol.
- Implementing the reconciliation engine.
- Implementing the completion receipt service.
- Implementing the conflict review UI.
- Implementing the downstream idempotency layer.
- Enabling cancellation controls.
- Enabling command authority.
- Modifying Mission Control Foundation code.
- Beginning Phase 3B.
- Deploying any component.

Implementation of the above requires separate ADRs, separate branches, and separate authorizations.

## 11. Acceptance Criteria

This ADR is considered accepted when all of the following are true.

| # | Criterion |
|---|-----------|
| 1 | Lease lifecycle (acquisition, renewal, expiry) is fully specified. |
| 2 | Brain outage detection uses at least two independent signals with a grace period. |
| 3 | Continuation eligibility criteria are explicit and verifiable. |
| 4 | Continuation limits are defined with platform and tenant bounds. |
| 5 | Idempotency and duplicate suppression are specified across all layers. |
| 6 | Reconciliation protocol produces a classified result for every continuation. |
| 7 | Replay semantics are distinct from continuation and require Brain authorization. |
| 8 | Completion receipts are mandatory, signed, and immutable. |
| 9 | Split-brain handling detects conflicts and routes them to manual review. |
| 10 | Audit chain includes all continuation events and links through causation. |
| 11 | Tenant isolation is guaranteed throughout continuation and reconciliation. |
| 12 | Recovery protocol defines recovery detection, report collection, reconciliation, and policy refresh. |
| 13 | Threat model, invariants, glossary, and implementation prerequisites are complete. |
| 14 | Non-goals explicitly exclude implementation, deployment, and authority activation. |

## 12. Consequences

Until this ADR is ratified and the criteria and prerequisites are implemented:

- `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE` remains **BLOCKED**.
- All cancellation controls remain **DISABLED**.
- `is_cancellation_blocked()` returns `True`.
- Executors must not continue after lease expiry.
- Phase 3B remains blocked pending this ADR and its implementation.

## 13. Status

| Item | State |
|------|-------|
| ADR-MC-001 | DRAFT — not ratified |
| SIGMA_LEASE_EXPIRY_CONTINUATION_GATE | BLOCKED |
| Cancellation controls | DISABLED |
| Phase 3B | BLOCKED |
| Implementation | NOT AUTHORIZED |
| Deployment | NOT AUTHORIZED |