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

Every command dispatched to an executor is associated with a lease. The lease is the temporal and authority boundary within which the executor may perform work on behalf of the Brain. The lease itself is **not** the continuation authority. A separate, pre-authorized continuation capability is required (see Section 2.1.4).

#### 2.1.1 Lease Acquisition

- The Brain issues a lease to exactly one executor per command at a time.
- The lease contains:
  - `command_id` — the command being executed
  - `executor_id` — the executor holding the lease
  - `tenant_id` — the tenant scope
  - `issued_at` — lease issuance timestamp (signed anchor time)
  - `expires_at` — lease expiration timestamp
  - `lease_token` — cryptographically signed token
  - `policy_snapshot_id` — identifier of the policy version in effect
  - `continuation_class` — side-effect class this command may perform under continuation (Section 2.9)
  - `continuation_capability_id` — reference to the pre-issued continuation capability, if any
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
- Renewal invalidates any prior continuation capability. The Brain issues a new continuation capability referencing the renewed lease. Only the capability referenced by the latest valid lease may be exercised.
- Capability rotation is auditable: the issuance, supersession, and revocation of each capability are recorded as immutable audit events.
- Capability revocation applies even where a former capability has a later `not_valid_after`; downstream systems must reject superseded capability IDs.

#### 2.1.3 Lease Expiry

- A lease expires when `expires_at` is reached or when the Brain explicitly revokes it.
- Upon expiry, the lease token immediately loses all authority to perform work or produce effects.
- The executor cannot use an expired lease to prove authority to downstream systems.
- Expiry is logged as an immutable audit event.
- Expiry alone does **not** permit continuation. Continuation requires a separate, unexpired continuation capability and all eligibility criteria in Section 2.3.

#### 2.1.4 Continuation Capability

Continuation requires a distinct, pre-authorized **continuation capability** issued by the Brain at dispatch or lease-renewal time. The capability is cryptographically separate from the lease token and is **unusable before lease expiry**.

| Capability Field | Purpose |
|---|---|
| `capability_id` | Unique identifier for this continuation grant |
| `command_id` | The command for which continuation is authorized |
| `tenant_id` | Tenant scope |
| `executor_id` | Executor authorized to continue |
| `issued_at` | When the capability was issued |
| `not_valid_before` | Must be equal to or after lease `expires_at`; prevents use while lease is active |
| `not_valid_after` | Maximum absolute wall-clock time the capability may be exercised |
| `max_continuation_duration` | Bound on how long continuation may run |
| `max_continuation_operations` | Bound on how many discrete operations may be performed |
| `continuation_class` | Side-effect class permitted (Section 2.9) |
| `permitted_operation_ids` | List of operation identifiers the executor may perform |
| `side_effect_slot_spec` | Specification of permitted side-effect slots |
| `policy_snapshot_hash` | Cryptographic hash of the pinned policy snapshot |
| `policy_snapshot_id` | Identifier of the pinned policy snapshot |
| `revocation_watermark_required` | Minimum revocation sequence number the executor must have observed |
| `signed_capability_token` | Brain-signed token binding all fields; distinct from lease token |

- The continuation capability is issued only when the Brain explicitly determines continuation may be allowed for a command.
- The capability is not a general grant of authority; it is narrowly scoped to a single command, tenant, executor, operation set, and time envelope.
- The capability cannot be used before `not_valid_before`, which is set to the lease expiry or later.
- Downstream systems must validate the signed continuation capability token — not the expired lease — before honoring any effect produced during continuation.
- The capability is revocable through a signed revocation stream; if the executor has not observed the required revocation watermark, it must not continue.

### 2.2 Brain Outage Detection

An executor must not declare a Brain outage based solely on a single failed request. Detection must be robust against transient failures and must not allow executors to bootstrap their own authority through friendly peer votes.

#### 2.2.1 Detection Signals

The executor monitors the following independent signals:

| Signal | Source | Threshold |
|---|---|---|
| Heartbeat acknowledgement | Brain heartbeat endpoint | Missing for `brain_heartbeat_miss_threshold` consecutive intervals |
| Lease renewal rejection | Brain lease endpoint | Rejected as `BRAIN_UNAVAILABLE` for `lease_rejection_threshold` attempts |
| Command status query failure | Brain command endpoint | Failed with timeout or `UNAVAILABLE` for `status_query_threshold` attempts |
| Witness outage statements | Independent control-plane witnesses (Section 2.2.4) | Quorum of witnesses reports Brain unavailability |
| Policy broadcast silence | Brain policy channel | No policy broadcast for `policy_silence_threshold` |

#### 2.2.2 Detection Rules

- Brain outage is declared only when at least **two independent signals** cross their thresholds.
- One of the two signals must be either heartbeat acknowledgement, lease renewal rejection, or command status query failure (a direct Brain observation).
- Witness statements alone are never sufficient to declare outage.
- The grace period before outage declaration is at least `brain_outage_grace_period` (default: 30 seconds, configurable per tenant with platform upper bound).
- A declared outage must be persisted locally with timestamp, signals observed, lease token fingerprint, and signed time anchor.

#### 2.2.3 Time Basis for Detection

All detection timestamps must use a trusted time source (Section 2.8). The executor records:
- `monotonic_outage_start` — monotonic clock marker when outage conditions began
- `wall_outage_declared_at` — signed wall-clock anchor when outage was declared
- `grace_period_end` — wall-clock time after which continuation may be considered

The executor must reject any time value that appears to roll backward relative to the last signed anchor by more than `max_clock_rollback_tolerance`.

#### 2.2.4 Witness Trust Model

Witnesses are independent control-plane identities, not executors. The witness model is defined as follows.

| Rule | Requirement |
|---|---|
| Witness identity | A witness is a control-plane service or Brain observer, not an executor participating in the command |
| Authentication | Witness statements are signed with witness identity keys and include `tenant_id`, `brain_region`, `witness_id`, `statement_id`, and timestamp |
| Quorum | Outage declaration requires at least `witness_quorum_size` valid witness statements from distinct witnesses. The fault model is: with `N` total witnesses and `f` faulty witnesses, the system requires `N >= 3f + 1` and `witness_quorum_size >= 2f + 1`. This is the standard Byzantine fault tolerance bound: it guarantees that any quorum of `2f + 1` witnesses contains at least `f + 1` honest witnesses, so a quorum cannot be formed by faulty witnesses alone. The first implementation may use a crash-fault tolerant (CFT) model (`N >= 2f + 1`, `quorum >= f + 1`) if it explicitly documents that it is not Byzantine-fault tolerant. The `witness_quorum_size` must be strictly less than `N` in either model. |
| Tenant partitioning | Witness statements are scoped to the tenant's Brain partition. A witness for tenant A cannot declare outage for tenant B. |
| Replay resistance | Each statement includes a monotonically increasing nonce and a signed anchor; stale or replayed statements are rejected |
| Stale witness protection | Witness statements older than `witness_statement_max_age` are ignored |
| Compromised witness handling | If a witness key is revoked, its statements are invalid. A threshold of valid witnesses must remain. |
| Self-exclusion | An executor cannot count itself, its peers, or any process it controls toward witness quorum |
| Network partition | A network partition alone does not grant continuation authority. A partition that isolates the executor from the Brain but not from witnesses must still satisfy the direct-Brain-signal requirement. |

### 2.3 Continuation Eligibility

Continuation is **optional and pessimistic**. Even when all criteria are met, the executor may choose to stop safely. Continuation is permitted only when all of the following are true.

| Criterion | Requirement | Verification |
|---|---|---|
| Lease expired | Lease `expires_at` reached or exceeded; continuation capability `not_valid_before` reached | Local clock + signed lease token + signed capability |
| Brain outage declared | Two independent signals crossed thresholds, including one direct-Brain signal | Outage record with signals and witness quorum if witnesses used |
| Continuation capability valid | Signed, unexpired, scoped to this command/executor/tenant, `not_valid_before` satisfied | Capability token validation |
| No revocation observed above watermark | No revocation for this command or capability; required revocation watermark observed | Local revocation stream and watermark |
| No cancellation confirmed | No cancellation command in cached ledger events up to the required revocation watermark | Cached command events and revocation watermark |
| Local state sufficient | All required inputs and deterministic path available | Self-check against task manifest |
| Side-effect class permitted | Command's `continuation_class` and capability permit the operation (Section 2.9) | Capability `continuation_class` and `permitted_operation_ids` |
| Policy snapshot pinned | Capability carries `policy_snapshot_hash`; executor trusts only that exact snapshot | Capability token |
| Bounded continuation | Estimated completion within capability `max_continuation_duration` and operation count | Task envelope estimate |
| Tenant isolation | Executor tenant matches command tenant | Capability `tenant_id` and execution context |
| Audit capability | Executor can emit continuation audit events and receipts | Local audit log buffer + recovery queue |
| Time bounds satisfied | Current signed wall-clock time is within capability validity window | Signed time anchors (Section 2.8) |

If any criterion is not met, the executor must stop and enter safe-hold state. The default decision is **STOP**.

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
| `continuation_capability_max_validity` | 24 hours | Absolute upper bound on continuation capability lifetime |
| `max_clock_rollback_tolerance` | 1 second | Maximum tolerated clock rollback (Section 2.8) |

All limits are configurable per tenant subject to platform maximums. A platform break-glass policy may reduce limits but never increase them beyond the platform maximum.

### 2.5 Idempotency and Duplicate Suppression

Continuation must not produce duplicate externally visible effects.

#### 2.5.1 Stable External-Effect Identity

The uniqueness key for an externally visible effect must be stable across normal execution, continuation, replay, and multiple executors. The key must identify the business operation, not the execution attempt.

Recommended form:

```text
(command_id, operation_id, side_effect_slot)
```

Where:
- `command_id` — the original command
- `operation_id` — the deterministic operation within the command's execution plan
- `side_effect_slot` — the specific external-effect slot being claimed (e.g., a resource write, notification, transfer)

`continuation_id`, `executor_id`, `lease_token`, and replay attempt number are **execution metadata**, not part of the external-effect identity. Downstream systems must reject duplicate effects matching the same `(command_id, operation_id, side_effect_slot)` regardless of which executor or attempt produced them.

**Replay identity rule:** When a replay creates a new command record, the `command_id` in the effect identity must always refer to the `root_command_id` — the original command that initiated the work — never the replay-attempt command record. See Section 2.7.

#### 2.5.2 Duplicate Suppression Layers

| Layer | Key | Action |
|---|---|---|
| Brain dispatch | `(command_id, executor_id, lease_token)` | Reject duplicate dispatch for active lease |
| Continuation capability | `(command_id, capability_id)` | Reject duplicate or reused continuation capability |
| Executor operation | `(command_id, operation_id, side_effect_slot)` | Skip already-performed externally visible operations |
| Downstream system | `(command_id, operation_id, side_effect_slot)` | Refuse duplicate external effects |
| Brain reconciliation | `(command_id, continuation_id)` | Reject duplicate continuation reports |
| Replay authorization | `(command_id, replay_attempt_id)` | Ensure replay is authorized and reconciled before re-execution |

#### 2.5.3 Continuation Journal

The executor must maintain a local continuation journal recording every operation attempted, its input, output, success/failure, timestamp, and the stable external-effect identity used.

### 2.6 Reconciliation Protocol

When the Brain recovers, all continuations must be reconciled before the command reaches a terminal state. Reconciliation has four distinct concerns: result selection, effect reconciliation, compensation, and manual review.

#### 2.6.1 Recovery Detection

- The Brain or an independent witness node declares recovery when the Brain has been available and responsive for at least `brain_recovery_confirmation_period` (default: 10 seconds).
- Executors are notified of recovery through the heartbeat channel.
- Recovery must be time-anchored and signed.

#### 2.6.2 Completion Reporting

Within `completion_report_deadline` of recovery detection, every executor that continued must report:

| Field | Type | Description |
|---|---|---|
| `command_id` | string | The continued command |
| `executor_id` | string | The continuing executor |
| `continuation_id` | string | Unique continuation attempt (metadata only) |
| `capability_id` | string | The continuation capability used |
| `lease_token_fingerprint` | string | Fingerprint of the expired lease token |
| `continuation_started_at` | datetime | When continuation began |
| `continuation_ended_at` | datetime | When continuation ended |
| `final_state` | enum | `SUCCEEDED`, `FAILED`, `ABORTED`, `TIMEOUT` |
| `operations_performed` | list | Each operation with `(operation_id, side_effect_slot, stable_effect_identity, result_digest)` |
| `result_digest` | hash | Digest of the completion result |
| `evidence_refs` | list | References to any produced artifacts |
| `continuation_journal` | encrypted blob | Full continuation journal |
| `audit_receipt_id` | string | Immutable audit receipt for the continuation |
| `revocation_watermark_observed` | integer | Revocation sequence number the executor observed |

Reporting is mandatory regardless of outcome. Silent continuation is forbidden.

#### 2.6.3 Reconciliation Concerns

Reconciliation is not a single decision. It addresses four concerns in order.

##### 2.6.3.1 Result Selection

Result selection determines which executor-reported outcome becomes authoritative for the command.

| Scenario | Result Selection Rule |
|---|---|
| Single valid continuation, no conflict | Select that result |
| Multiple continuations, same result and effect identity | Select the result from the first completed continuation by monotonic timestamp; mark others `DUPLICATE_AGREED` |
| Multiple continuations, divergent results | No automatic selection; route to `MANUAL_REVIEW_REQUIRED` and effect reconciliation |
| Invalid continuation | Discard the result; executor may be flagged |

Result selection by timestamp is permitted **only** when all reported effects are provably idempotent and equivalent.

##### 2.6.3.2 Effect Reconciliation

Effect reconciliation determines what happens to externally visible side effects already emitted by executors.

| Scenario | Effect Reconciliation Rule |
|---|---|
| Effect identity matches an already-applied effect | Mark as duplicate; do not re-apply |
| Effect identity is new and result is valid | Apply the effect if the selected result is authoritative |
| Effect identity conflicts with another effect | Freeze the affected downstream resource; route to manual review |
| Effect is non-reversible and multiple executors attempted it | Freeze and require manual review; no automatic application |
| Effect class is high-risk/irreversible (Class 3) | Freeze and require manual review regardless of result selection |

##### 2.6.3.3 Compensation

Where effects are reversible or idempotent, the Brain may authorize compensation:

- Re-issuing an idempotent operation with the authoritative result.
- Reversing a reversible effect produced by a losing executor.
- Compensation is itself a command with its own lease, idempotency key, and audit chain.
- Irreversible or destructive effects cannot be compensated automatically.

##### 2.6.3.4 Manual Review

Manual review is mandatory when:

- Multiple continuations produce divergent results.
- Non-reversible or high-risk effects are involved.
- Revocation or cancellation status was unknown during continuation.
- The continuation capability validity is disputed.
- Any reconciliation step cannot produce a deterministic outcome.

The command remains in `MANUAL_REVIEW_REQUIRED` until an authorized operator resolves it. All evidence, receipts, and continuation journals must be surfaced.

#### 2.6.4 Reconciliation Classifications

After reconciliation, each continuation is classified:

- `VALID_CONTINUATION` — all criteria met, single report, no conflict, effects reconciled.
- `VALID_BUT_RECONCILED` — all criteria met, but effects required reconciliation or compensation.
- `INVALID_CONTINUATION` — criteria were not met at continuation time; executor exceeded authority.
- `CONFLICTING_REPORTS` — multiple reports with irreconcilable differences or non-reversible effects.
- `MANUAL_REVIEW_REQUIRED` — deterministic resolution impossible; operator decision required.

### 2.7 Replay Semantics

Replay is the Brain-authorized re-execution of a command after recovery. It is distinct from continuation and must not bypass prior-effect deduplication.

- Replay may occur only when the Brain explicitly authorizes it.
- The Brain must reconcile all continuation reports before authorizing replay. Unknown or unreconciled effect status blocks replay or requires compensation/manual review.
- Replay uses a new lease and a new **execution** identity (`replay_attempt_id`). The replay creates a new command record, but that record is execution metadata — it is not the identity root for external effects.
- Replay does **not** receive a new external-effect identity. Every replayed operation must derive its external-effect identity from the original root command, never from the replay-attempt command record. The stable key is `(root_command_id, operation_id, side_effect_slot)` where `root_command_id` is the original command that initiated the work. An implementer must never use the replay record's new command ID in the effect identity, as that would bypass deduplication against effects already produced by the original command or any prior continuation.
- The Brain must mark the original command as `REPLAYED` and link the replay command through causation.
- Executors must not autonomously replay a command during continuation.
- A continuation that fails may be followed by a Brain-authorized replay only after the continuation is reconciled and the Brain determines which effects are already applied.

### 2.8 Time Authority and Clock Rules

Continuation depends critically on time. The design must define trusted time semantics.

| Aspect | Rule |
|---|---|
| Trusted clock source | The Brain is the authoritative clock source. All lease, capability, and revocation timestamps are signed by the Brain. |
| Executor clock | The executor maintains a monotonic clock for duration measurement and a wall-clock corrected by signed Brain anchors. |
| Clock skew tolerance | Maximum skew between executor wall-clock and Brain time is `max_clock_skew_tolerance` (default: 5 seconds). Exceeding skew is a security event. |
| Monotonic time | `max_continuation_duration` and grace periods are measured with monotonic time to prevent extension via clock rollback. |
| Signed time anchors | The Brain issues signed time anchors at dispatch, renewal, and recovery. A signed anchor at the instant of lease expiry is not required: the latest pre-outage signed anchor establishes the wall-clock reference, and the executor derives lease expiry locally from that anchor plus monotonic elapsed time. The executor advances elapsed time using its monotonic clock. If the monotonic clock loses continuity (e.g., process restart, suspend/resume) or wall-clock drift exceeds `max_clock_skew_tolerance`, the executor must STOP. A fresh Brain signature at the instant of expiry is not required to declare expiry. |
| Timestamp rollback | The executor rejects any signed timestamp that rolls backward more than `max_clock_rollback_tolerance` relative to the last anchor. Larger rollbacks require operator intervention. |
| Disagreement | If executor and Brain time disagree beyond tolerance, the executor must stop and wait for a fresh signed anchor. Continuation is not permitted under disputed time. |
| Capability validity | Capability `not_valid_before` and `not_valid_after` are evaluated against signed Brain anchors, not executor wall-clock alone. |

### 2.9 Side-Effect Classification

Continuation authority is classified by the risk and reversibility of the side effects it may produce. The capability explicitly states the class.

| Class | Description | Continuation Eligibility |
|---|---|---|
| Class 0 | Local computation only; no external effects | Eligible with capability and journal |
| Class 1 | Reversible internal writes or safe local state changes | Eligible with capability, journal, and rollback plan |
| Class 2 | Idempotent external writes with proven downstream duplicate suppression | Eligible only if downstream system validates `(command_id, operation_id, side_effect_slot)` |
| Class 3 | Irreversible, destructive, financial, legal, or high-risk external effects | **Prohibited during continuation.** Requires fresh Brain authorization. |

The default class is `STOP` (no continuation permitted). A command's `continuation_class` is assigned by the Brain at dispatch based on the command type, tenant policy, and side-effect risk.

### 2.10 Revocation and Cancellation Watermark

Absence of evidence is not evidence of absence. The executor must use a revocation/cancellation watermark model.

| Concept | Rule |
|---|---|
| Revocation stream | The Brain publishes a signed, monotonic revocation/cancellation stream partitioned by tenant. Each entry has a sequence number and timestamp. |
| Watermark | The executor records the highest revocation sequence number it has observed. Continuation requires the watermark to be at least `revocation_watermark_required` from the capability. |
| Cache age | The local revocation cache must be no older than `max_revocation_cache_age` (default: 5 seconds) at the moment of lease expiry. Older caches are stale. |
| Fail-closed | If the revocation watermark is missing, stale, or below the capability requirement, continuation is **not** permitted. |
| Command-class rule | High-risk, legal, financial, destructive, or irreversible commands default to `STOP` and may not continue without fresh revocation knowledge. |
| Revocation during outage | If the executor receives a revocation entry during outage, it must stop immediately. |
| Cancellation in cache | A cancellation command observed at or before the revocation watermark is authoritative. Continuation is forbidden. |

### 2.11 Policy Snapshot Model

The executor cannot determine whether policy has been superseded during an outage. Instead, it relies on a pinned policy snapshot carried in the continuation capability.

| Rule | Description |
|---|---|
| Pinned snapshot | The continuation capability carries `policy_snapshot_id` and `policy_snapshot_hash`. The executor may rely only on that exact policy version during continuation. |
| Snapshot validity | The capability defines a `policy_snapshot_not_valid_after` time. After that, the executor must not continue. |
| Emergency deny channel | Critical policy denies/revocations must travel through a survivable channel (e.g., signed revocation stream, witness broadcast). If the executor cannot verify the required watermark, it stops. |
| New effects | A pinned policy snapshot cannot authorize side-effect classes or operations not explicitly permitted by the capability. |

### 2.12 Split-Brain Handling

Split-brain occurs when multiple executors independently continue the same command, or when the Brain recovers while executors are still continuing.

#### 2.12.1 Detection

- Multiple continuation reports for the same `command_id` with different `continuation_id` values.
- Continuation reports arriving while the Brain considers the command still active.
- Divergent `result_digest` values or conflicting `(command_id, operation_id, side_effect_slot)` claims.

#### 2.12.2 Resolution

| Scenario | Result Selection | Effect Reconciliation | Final State |
|---|---|---|---|
| Multiple executors continued, results agree and effects are idempotent | First completed wins; others marked `DUPLICATE_AGREED` | Deduplicate by stable effect identity | SUCCEEDED |
| Multiple executors continued, results agree but effects are non-reversible | First completed wins; others marked `DUPLICATE_AGREED` | Freeze effects; manual review | MANUAL_REVIEW_REQUIRED |
| Multiple executors continued, results conflict | No automatic selection | Freeze all affected downstream effects; manual review | MANUAL_REVIEW_REQUIRED |
| Brain recovers while continuation active | Stop active continuations; complete in-progress idempotent operations safely | Report completed operations; abort in-progress operations idempotently | RECONCILING |
| Brain never recovers within capability window | Executor must stop at `not_valid_after` | Partial results recorded; manual recovery process | MANUAL_REVIEW_REQUIRED |

No silent conflict resolution is permitted. All conflicts are recorded and surfaced.

### 2.13 Audit Chain Requirements

The continuation event must be fully traceable in the causation chain and the immutable audit ledger.

- Lease expiry event.
- Continuation capability issuance event.
- Brain outage declaration event.
- Continuation eligibility decision event.
- Each operation performed during continuation, with stable effect identity.
- Continuation completion event and receipt.
- Brain recovery detection event.
- Reconciliation event.
- Terminal state event.

**Authoritative audit storage is never truncated.** The immutable audit ledger stores every event. Read-only projection APIs (such as Mission Control causation chain) may paginate or cap displayed links at `MAX_CAUSATION_LINKS` with truncation metadata, but that truncation applies only to the projection, not to the ledger.

### 2.14 Tenant Isolation Guarantees

Continuation respects tenant boundaries.

- An executor may only continue commands within its own tenant scope.
- Continuation capabilities, revocation streams, and witness statements are tenant-scoped.
- Continuation limits are enforced per tenant.
- Continuation reports are routed to the tenant's Brain partition.
- Cross-tenant continuation is forbidden and treated as a security event.
- Tenant-level policies may disable continuation entirely (`continuation_class = STOP`).

### 2.15 Recovery Protocol

The recovery protocol governs how the system returns to normal operation after Brain recovery.

1. **Recovery detection** — Brain availability confirmed for `brain_recovery_confirmation_period` by direct signals and/or witness confirmation.
2. **Report collection** — Brain receives all pending continuation reports within `completion_report_deadline`.
3. **Reconciliation** — Brain performs result selection, effect reconciliation, compensation, and manual-review routing (Section 2.6).
4. **Conflict freeze** — Conflicting results freeze downstream effects until resolved.
5. **Manual review queue** — Conflicts, invalid continuations, and non-reversible effects are enqueued for operator review.
6. **Replay authorization** — Valid commands that did not complete receive Brain-authorized replay only after reconciliation.
7. **Policy refresh** — All executors refresh policy snapshots and revocation watermarks before accepting new work.
8. **Audit completion** — All continuation events are finalized in the immutable audit ledger.
9. **Gate evaluation** — Only after the implementation is certified may `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE` be evaluated for unblocking.

## 3. Sequence Diagrams

### 3.1 Normal Lease Lifecycle

```text
Brain          Executor          Downstream
 |               |                    |
 |-- issue lease + capability -->|   |
 |               |-- perform work --->|
 |               |<--- result --------|
 |<-- renew -----|                  |
 |-- renew ok + capability -------->|   |
 |               |-- perform work --->|
 |               |<--- result --------|
 |<-- complete --|                  |
```

### 3.2 Lease Expiry with Continuation

```text
Brain          Executor          Downstream
 |               |                    |
 |-- issue lease + capability -->|   |
 |               |-- perform op 1 ---->|
 |               |<--- result 1 -------|
 |   lease       |                    |
 |   expires     |                    |
 |   (no contact)|                    |
 |               |== declare outage ==|
 |               |== validate capability |
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
   |<== declare outage + witness quorum ==|
   |== continue command X (capability C-A) |
   |               |== also declare outage |
   |               |== continue command X (capability C-B) |
   |== report X-A =|===============>|
   |               |== report X-B ========>|
   |               |<== detect conflict ===|
   |<== freeze ===|               |
   |               |<== manual review queue |
```

## 4. State-Machine Diagrams

### 4.1 Lease and Capability State Machine

```text
         +------------------+
         | LEASE ISSUED     |
         | CAPABILITY ISSUED|
         +------------------+
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
              | capability not_valid_before reached + eligible
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

### 4.2 Command State Machine (with Continuation and Replay Path)

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
                        |
                        | Brain-authorized replay
                        v
                   +---------+
                   | REPLAY  |
                   +---------+
```

## 5. Timing Diagrams

### 5.1 Grace Period and Continuation Window

```text
Time -->
|---- lease active ----|-- grace --|-- continuation window --|-- report deadline --|
0                      T1          T2                          T3                    T4

T0: Lease issued
T1: Lease expires; capability not_valid_before may equal T1
T2: Brain outage declared (after grace period)
T3: Latest permitted continuation end (min(T2 + max_continuation_duration, capability not_valid_after))
T4: Completion report deadline (after recovery)
```

### 5.2 Overlapping Continuation and Recovery

```text
Executor A:  [validate cap] [continue X]----------[receipt]--[report]
Executor B:        [validate cap] [continue X]----------[receipt]--[report]
Brain:            [unavailable]...............[recovery]--[reconcile]
Time ->
```

## 6. Failure Matrices

### 6.1 Lease Expiry Decision Matrix

| Lease State | Capability State | Brain Available | Eligible | Executor Decision | Next State |
|---|---|---|---|---|---|
| Expired | Not issued | Any | N/A | Stop | ABORTED or REPLAY later |
| Expired | Issued, not yet valid | Yes | N/A | Stop and request new lease | EXPIRED /> RENEWED or FAILED |
| Expired | Valid | Yes | N/A | Stop; capability cannot be used while Brain is available | EXPIRED /> RENEWED or FAILED |
| Expired | Valid | No (outage) | Yes | May continue (optional) | CONTINUING |
| Expired | Valid | No (outage) | No | Stop | EXPIRED /> ABORTED |
| Expired | Valid | Unknown | Unknown | Stop | EXPIRED /> ABORTED |
| Revoked | Any | Any | N/A | Stop | REVOKED /> FAILED |
| Cancelled | Any | Any | N/A | Stop | CANCELLED |

### 6.2 Continuation Outcome Matrix

| Outcome | Receipt | Reconciliation Class | Effect Reconciliation | Command State |
|---|---|---|---|---|
| Success, single executor | Valid | VALID_CONTINUATION | Apply authoritative effects by stable identity | SUCCEEDED |
| Success, but Brain expected different | Valid | VALID_BUT_RECONCILED | Reconcile/apply per effect rules; compensation if reversible | RECONCILED /> SUCCEEDED or REVIEW |
| Success, multiple executors agree and effects idempotent | Valid | VALID_CONTINUATION (duplicate agreed) | Deduplicate by stable effect identity | SUCCEEDED |
| Success, multiple executors agree but effects non-reversible | Valid | VALID_BUT_RECONCILED | Freeze; manual review | MANUAL_REVIEW_REQUIRED |
| Success, multiple executors conflict | Valid each | CONFLICTING_REPORTS | Freeze all affected effects; manual review | MANUAL_REVIEW_REQUIRED |
| Failure during continuation | Valid | VALID_CONTINUATION or INVALID | None or compensation if reversible | FAILED or RECONCILED |
| Continuation without eligibility | Valid | INVALID_CONTINUATION | None; executor flagged; downstream effects frozen if any | INVALID /> REVIEW |
| No receipt produced | Missing | INVALID_CONTINUATION | None | INVALID /> REVIEW |
| Class 3 side effect attempted | Valid/Invalid | INVALID_CONTINUATION | Freeze; security event; manual review | INVALID /> REVIEW |

### 6.3 Threat Model

| Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Executor continues without capability | Medium | Critical | Separate signed capability; capability validation by downstream systems; capability unusable before lease expiry |
| Executor continues without Brain outage | Medium | High | Two independent signals including direct-Brain signal; witness quorum only supplementary; grace period |
| Executor continues without local state sufficiency | Medium | High | Self-check against task manifest; deterministic path requirement |
| Multiple executors continue same command | Low | Critical | Lease exclusivity; distinct per-executor capabilities; conflict detection; manual review for conflicts |
| Executor produces duplicate external effects | Medium | High | Stable `(command_id, operation_id, side_effect_slot)` identity; downstream duplicate suppression |
| Executor lies about continuation outcome | Low | High | Signed receipts; continuation journal; result digest; audit chain |
| Brain recovers during continuation | Medium | Medium | Recovery signal; stop in-progress ops; report completed ops; reconcile |
| Cross-tenant continuation | Low | Critical | Tenant-scoped capabilities; tenant isolation enforcement; security event |
| Continuation runs unbounded | Low | High | Capability time bounds; operation count limits; per-tenant rate limits |
| Stale revocation/cancellation knowledge | Medium | Critical | Revocation watermark; cache-age limit; fail-closed; high-risk classes default to STOP |
| Pinned policy exploited | Low | High | Policy snapshot hash; not_valid_after; emergency deny channel; watermark requirement |
| Clock skew/rollback extends authority | Low | Critical | Signed time anchors; monotonic time bounds; skew tolerance; rollback tolerance |
| Silent continuation | Medium | High | Mandatory completion reporting; receipt requirement; reconciliation deadline |
| Witness quorum compromised | Low | Critical | Independent control-plane witnesses; self-exclusion; replay-resistant signed statements; key revocation |

## 7. Invariants

The following invariants must hold at all times. Any violation is a security or correctness event.

| # | Invariant | Enforcement |
|---|-----------|-------------|
| 1 | An executor without a valid lease cannot produce authoritative command effects during normal execution. | Lease token validation |
| 2 | An executor cannot use an expired lease to authorize continuation or effects. | Lease expiry + separate capability validation |
| 3 | A continuation capability cannot be used before lease expiry or after its own expiry. | `not_valid_before`, `not_valid_after`, signed time anchors |
| 3a | Only the continuation capability referenced by the latest valid lease may be exercised. Prior capabilities are superseded at renewal, even if their `not_valid_after` is later. | Capability rotation audit chain; downstream capability ID validation |
| 4 | Continuation is never the default behavior. | Eligibility check; optional stop; default class STOP |
| 5 | Continuation cannot exceed its bounded envelope. | Capability `max_continuation_duration`; `max_continuation_operations`; monotonic clock |
| 6 | Every continuation produces an immutable, signed receipt. | Executor receipt generation; signature verification |
| 7 | Every continuation is reconciled before the command reaches terminal state. | Reconciliation protocol |
| 8 | Conflicting continuation results or non-reversible effects never resolve silently. | Conflict record; freeze; manual review queue |
| 9 | Cross-tenant continuation is impossible. | Tenant-scoped capabilities and policies |
| 10 | Idempotency is preserved across continuation, replay, and normal execution. | Stable `(command_id, operation_id, side_effect_slot)` identity; duplicate suppression layers |
| 11 | Authoritative audit storage is complete and never truncated. | Immutable audit ledger |
| 12 | Policy snapshot validity is bounded to the exact pinned snapshot in the capability. | `policy_snapshot_hash`; `policy_snapshot_not_valid_after` |
| 13 | Revocation/cancellation knowledge must be fresh enough; absence of evidence is not permission. | Revocation watermark; `max_revocation_cache_age`; fail-closed |
| 14 | Time cannot be manipulated to extend authority. | Signed time anchors; monotonic clocks; skew and rollback tolerances |
| 15 | High-risk or irreversible side effects cannot be produced during continuation. | Class 3 prohibition; downstream class validation |

## 8. Glossary

| Term | Definition |
|---|---|
| Brain | The central command authority that owns intent, dispatch, and cancellation state under ADR-002. |
| Executor | A worker process that performs command work under a lease from the Brain. |
| Lease | A time-bound, signed grant of authority from the Brain to an executor for a specific command. |
| Lease expiry | The moment a lease's `expires_at` is reached or the lease is revoked. |
| Continuation capability | A distinct, pre-authorized, signed grant that permits an executor to continue a specific command after lease expiry under strict bounds. |
| Continuation | Optional executor work performed after lease expiry during a declared Brain outage, authorized by a continuation capability. |
| Brain outage | A declared state where the Brain is unreachable, confirmed by two independent signals including at least one direct-Brain signal. |
| Grace period | The waiting time after lease expiry before an outage can be declared. |
| Witness | An independent control-plane identity that publishes signed statements about Brain availability. |
| Stable external-effect identity | The business-level identity of an externally visible effect: `(command_id, operation_id, side_effect_slot)`. |
| Idempotency key | A key that identifies a command such that duplicate execution produces the same effect once. |
| Continuation_id | A unique identifier for a single continuation attempt; used as metadata, not as an effect-identity boundary. |
| Replay | A Brain-authorized re-execution of a command using a new lease and execution identity, but preserving original external-effect identities. |
| Root command ID | The original command that initiated a unit of work. All external-effect identities for continuations and replays of that work derive from the root command ID, never from continuation or replay-attempt command records. |
| Split-brain | A condition where multiple executors independently continue the same command. |
| Policy snapshot | The exact version of execution policy pinned in a continuation capability. |
| Completion receipt | An immutable, signed record of a continuation's outcome. |
| Causation chain | A hash-linked sequence of events showing command lineage; projection views may truncate, but the audit ledger does not. |
| Revocation watermark | The highest revocation/cancellation sequence number an executor has observed from the Brain. |
| Sigma gate | `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE`, currently BLOCKED. |

## 9. Implementation Prerequisites

This section lists what must exist before implementation of this ADR may begin. It does not implement anything.

### 9.1 Required Components

| Component | Purpose | Status |
|---|---|---|
| Signed lease token service | Issue, renew, and revoke signed lease tokens | Not implemented |
| Continuation capability service | Issue, validate, and revoke signed continuation capabilities | Not implemented |
| Brain heartbeat endpoint | Allow executors to detect Brain availability | Not implemented |
| Witness statement service | Publish and validate signed witness statements | Not implemented |
| Executor local state cache | Store inputs, configuration, and prior step outputs | Not implemented |
| Revocation stream | Publish lease revocations, cancellations, and emergency denies | Not implemented |
| Policy snapshot registry | Pin and validate policy snapshots by hash | Not implemented |
| Continuation journal store | Immutable per-continuation operation log | Not implemented |
| Completion receipt service | Generate and verify signed continuation receipts | Not implemented |
| Reconciliation engine | Classify and resolve continuation reports with result selection, effect reconciliation, compensation, and manual review | Not implemented |
| Conflict review queue | Surface conflicting continuation results for operators | Not implemented |
| Audit event pipeline | Append continuation events to immutable audit ledger | Not implemented |
| Downstream effect identity layer | Validate `(command_id, operation_id, side_effect_slot)` before applying effects | Not implemented |
| Signed time-anchor service | Issue and validate signed wall-clock anchors | Not implemented |

### 9.2 Required Configuration

| Setting | Description |
|---|---|
| `brain_heartbeat_miss_threshold` | Consecutive missed heartbeats before outage signal |
| `lease_rejection_threshold` | Consecutive `BRAIN_UNAVAILABLE` lease responses before outage signal |
| `status_query_threshold` | Consecutive failed status queries before outage signal |
| `policy_silence_threshold` | Duration without policy broadcast before outage signal |
| `witness_quorum_size` | Minimum valid witness statements for witness signal |
| `witness_statement_max_age` | Maximum age of a valid witness statement |
| `brain_outage_grace_period` | Minimum time after lease expiry before outage declaration |
| `brain_recovery_confirmation_period` | Duration of confirmed Brain availability before recovery declaration |
| `max_continuation_duration` | Maximum time an executor may continue |
| `max_continuation_operations` | Maximum operations per continuation |
| `max_continuation_attempts_per_command` | Maximum continuation attempts per command |
| `max_concurrent_continuations_per_executor` | Maximum simultaneous continuations per executor |
| `completion_report_deadline` | Time after recovery to submit continuation report |
| `tenant_max_continuation_rate` | Tenant-level continuation rate limit |
| `continuation_capability_max_validity` | Absolute upper bound on continuation capability lifetime |
| `max_clock_skew_tolerance` | Maximum tolerated executor-Brain clock skew |
| `max_clock_rollback_tolerance` | Maximum tolerated timestamp rollback |
| `max_revocation_cache_age` | Maximum age of executor's revocation cache at lease expiry |

### 9.3 Required Tests

| Test | Purpose |
|---|---|
| Lease lifecycle | Verify lease acquisition, renewal, expiry, and revocation |
| Capability issuance and validation | Verify capability cannot be used before lease expiry or after its own expiry |
| Brain outage declaration | Verify two-signal rule, direct-Brain-signal requirement, and grace period |
| Witness statement validation | Verify witness identity, quorum, replay resistance, self-exclusion |
| Continuation eligibility | Verify all criteria must be met; default is STOP |
| Continuation bounds | Verify duration, operation, and concurrency limits |
| Revocation watermark | Verify fail-closed when watermark is stale or missing |
| Idempotency across continuation/replay | Verify stable effect identity deduplication |
| Completion receipt | Verify signature and immutability |
| Reconciliation | Verify result selection, effect reconciliation, compensation, and manual review |
| Split-brain conflict | Verify conflict detection, freeze, and manual review |
| Cross-tenant isolation | Verify tenant boundary enforcement |
| Recovery protocol | Verify full recovery sequence |
| Audit ledger completeness | Verify authoritative storage is never truncated |
| Time authority | Verify signed anchors, monotonic bounds, skew/rollback handling |
| Side-effect class enforcement | Verify Class 3 prohibition |

## 10. Non-Goals

The following are explicitly out of scope for this ADR and must not be implemented under this ADR.

- Implementing the lease service.
- Implementing the continuation capability service.
- Implementing the heartbeat or witness protocol.
- Implementing the reconciliation engine.
- Implementing the completion receipt service.
- Implementing the conflict review UI.
- Implementing the downstream effect identity layer.
- Implementing the signed time-anchor service.
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
| 1 | Lease lifecycle and continuation capability lifecycle are fully specified and separated. |
| 2 | Continuation capability is unusable before lease expiry and bounded by time, operations, and scope. |
| 3 | Brain outage detection uses at least two independent signals including one direct-Brain signal, with a grace period. |
| 4 | Witness trust model is fully defined with identity, quorum, replay resistance, and self-exclusion. |
| 5 | Continuation eligibility criteria are explicit and default to STOP. |
| 6 | Continuation limits are defined with platform and tenant bounds. |
| 7 | Stable external-effect identity is defined and used for duplicate suppression across normal execution, continuation, and replay. |
| 8 | Replay semantics preserve effect identity and require reconciliation before authorization. |
| 9 | Reconciliation protocol separates result selection, effect reconciliation, compensation, and manual review. |
| 10 | Completion receipts are mandatory, signed, and immutable. |
| 11 | Split-brain handling detects conflicts, freezes effects, and routes to manual review. |
| 12 | Audit chain includes all continuation events; authoritative audit storage is never truncated. |
| 13 | Tenant isolation is guaranteed throughout continuation and reconciliation. |
| 14 | Recovery protocol defines recovery detection, report collection, reconciliation, and policy refresh. |
| 15 | Trusted time, clock skew, monotonic time, and signed time anchors are specified. |
| 16 | Policy snapshot is pinned by hash and bounded by validity time. |
| 17 | Revocation watermark and cache-age rules are fail-closed. |
| 18 | Side effects are classified and Class 3 effects are prohibited during continuation. |
| 19 | Threat model, invariants, glossary, and implementation prerequisites are complete. |
| 20 | Non-goals explicitly exclude implementation, deployment, and authority activation. |

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