# 04 — State Machine Diagrams (Executor Continuation)

**Status:** PLANNING ARTIFACT — no runtime code
**Scope:** Implementation-level expansion of ADR-MC-001 Sections 4 (state-machine diagrams) and 5 (timing diagrams), plus recovery protocol from Section 2.15.
**Source of truth:** `docs/mission-control/ADR_MC_001_EXECUTOR_CONTINUATION.md` (ACCEPTED, ratified 2026-08-05).
**Purpose:** Specify every state, transition, guard, and action required to implement the executor continuation subsystem. This document is a planning artifact only; it does not ratify behavior, unblock `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE`, or authorize implementation.

## How to read these diagrams

- States are rendered as boxed labels. Terminal states are marked `(terminal)`.
- Transitions are labelled `event / [guard] / action`. A bare label is an event; bracketed text is a guard (a boolean condition that must hold for the transition to fire); text after a slash is the action performed on transition.
- `⟶` denotes a normal transition; `==>` denotes a transition that occurs only during a declared Brain outage (i.e., outside normal Brain authority).
- Time references (T0..T4) align with the ADR Section 5.1 timing diagram.
- Every transition that changes durable state emits an immutable audit event (ADR Section 2.13). Audit emission is implicit on all transitions below and is not repeated per-arrow unless the event is itself the subject of the transition.

Legend of recurring guards and actions:

| Symbol | Meaning |
|---|---|
| `[lease.token.valid]` | Signed lease token is unexpired, unrevoked, and signature verifies. |
| `[cap.token.valid]` | Signed continuation capability token signature verifies and time bounds hold. |
| `[2-signal]` | At least two independent outage signals crossed thresholds, one of which is a direct-Brain signal (ADR 2.2.2). |
| `[watermark.ok]` | Observed revocation watermark >= `revocation_watermark_required` and cache age <= `max_revocation_cache_age`. |
| `[no-cancel]` | No cancellation command observed in cached ledger events at or before the watermark. |
| `[class.permitted]` | Command `continuation_class` and capability `permitted_operation_ids` permit the operation. |
| `[tenant.match]` | Executor `tenant_id` == capability `tenant_id` == command `tenant_id`. |
| `/emit.audit` | Append an immutable audit event with causation link. |
| `/rotate.capability` | Revoke prior capability, issue new capability bound to the renewed lease, record supersession. |
| `/freeze.effects` | Freeze affected downstream resources; route to manual review. |

---

## 1. Lease Lifecycle State Machine

This machine governs the Brain-issued lease token (ADR 2.1). The lease is the temporal and authority boundary for normal execution. It is **not** the continuation authority; the continuation capability is a separate, cryptographically distinct token (Section 2 below).

The ADR's Section 4.1 collapses lease and capability into one diagram. Here they are separated for implementation clarity, and the lease machine adds the `REVOKED` terminal state and explicit renewal-loop semantics.

```text
                         +-----------------------+
                         | LEASE_ISSUED          |
   entry / emit.audit    |  (token signed,       |
   (dispatch causation)  |   expires_at set)     |
                         +-----------+-----------+
                                     |
                                     | executor presents token / [lease.token.valid] / begin work
                                     v
                         +-----------------------+
                +-------->| LEASE_ACTIVE          |
                |         |  (work in progress)   |
                |         +-----------+-----------+
                |                     |
                |                     | renewal requested before expires_at
                |                     | [command not cancelled] AND
                |                     | [executor is holder] AND
                |                     | [max execution duration not exceeded] AND
                |                     | [policy snapshot not superseded] AND
                |                     | [Brain available]
                |                     v
                |         +-----------------------+
                |         | LEASE_RENEWED          |
                |         |  (new token, new       |
                |         |   expires_at)          |
                |         +-----------+-----------+
                |                     |
                |                     | / rotate.capability (revoke prior cap, issue new cap)
                |                     | / emit.audit (renewal + capability rotation)
                |                     v
                +-------< (return to ACTIVE)
                |
                | (renewal denied: any guard above false)
                |   / emit.audit (renewal denied w/ reason)
                |   v
                |   (falls through to EXPIRED or REVOKED path below)
                |
                | wall-clock reaches expires_at (T1)
                |   / invalidate token / emit.audit (expiry)
                v
                         +-----------------------+
                         | LEASE_EXPIRED          |
                         |  (token loses all      |
                         |   authority)           |
                         +-----+-----------+-----+
                               |               |
                               |               | Brain explicitly revokes
                               |               |   / emit.audit (revocation)
                               |               v
                               |         +---------------+
                               |         | LEASE_REVOKED  | (terminal)
                               |         +---------------+
                               |
                               | (lease expiry alone does NOT permit continuation;
                               |  see Capability + Execution machines below)
                               v
                         (lease is now historical; control passes to the
                          Continuation Capability and Continuation Execution
                          state machines, if a capability was issued)
```

State inventory:

| State | Description | Token authority | Terminal? |
|---|---|---|---|
| `LEASE_ISSUED` | Lease signed and dispatched; executor has not yet begun work. | Valid but unused. | No |
| `LEASE_ACTIVE` | Executor is performing command work under the lease. | Valid and active. | No |
| `LEASE_RENEWED` | Brain granted renewal; new token issued, `expires_at` extended. Prior token revoked. | New token valid; prior token invalid. | No (transient; returns to ACTIVE) |
| `LEASE_EXPIRED` | `expires_at` reached or exceeded. Token immediately loses all authority. | Invalid. | Yes (for the lease itself) |
| `LEASE_REVOKED` | Brain explicitly revoked the lease before natural expiry. | Invalid. | Yes |

Implementation notes:

- `LEASE_RENEWED` is modeled as a distinct state (not just a self-loop on `ACTIVE`) because the ADR requires capability rotation and prior-token revocation as atomic side effects of renewal (ADR 2.1.2). Treating renewal as a state makes the `/rotate.capability` action a first-class transition rather than an implicit side effect.
- The transition `LEASE_ACTIVE ⟶ LEASE_EXPIRED` is time-driven and fires at T1 regardless of Brain availability. Expiry does not require a Brain signature at the instant of expiry (ADR 2.8); the executor derives expiry from the latest signed anchor plus monotonic elapsed time.
- `LEASE_EXPIRED` is terminal **for the lease**, but it is the precondition for the continuation capability becoming usable. The continuation execution machine (Section 3) picks up from here.

---

## 2. Continuation Capability Lifecycle State Machine

This machine governs the signed continuation capability (ADR 2.1.4). The capability is cryptographically separate from the lease token and is **unusable before lease expiry** (`not_valid_before` == lease `expires_at` or later).

The ADR's Section 4.1 shows capability only implicitly. This machine makes the capability's own lifecycle explicit, including the `NOT_YET_VALID`, `SUPERSEDED`, and `EXERCISED` states required by the rotation and revocation rules (ADR 2.1.2, 2.1.4, Invariant 3a).

```text
                         +-------------------------+
                         | CAPABILITY_ISSUED       |
   entry / emit.audit    |  (signed at dispatch    |
   (causation: dispatch  |   or renewal;           |
    or renewal event)    |   not_valid_before set  |
                         |   to lease expires_at)  |
                         +-----------+-------------+
                                     |
                                     | issued at dispatch (lease still active)
                                     v
                         +-------------------------+
                         | CAP_NOT_YET_VALID       |
                         |  (lease active; cap     |
                         |   cannot be exercised)  |
                         +-----------+-------------+
                                     |
                                     | wall-clock >= not_valid_before (T1)
                                     |   AND [cap.token.valid]
                                     |   AND [watermark.ok]
                                     |   AND [no-cancel]
                                     |   / emit.audit (cap became valid)
                                     v
                         +-------------------------+
          +------------->| CAP_VALID               |
          |              |  (eligible to be        |
          |              |   exercised)            |
          |              +-----+-----------+-------+
          |                    |                 |
          |                    |                 | lease renewed by Brain
          |                    |                 |   / rotate.capability
          |                    |                 |   / emit.audit (supersession)
          |                    |                 v
          |                    |          +---------------------+
          |                    |          | CAP_SUPERSEDED       | (terminal)
          |                    |          |  (prior cap revoked;  |
          |                    |          |   downstream must     |
          |                    |          |   reject cap_id)      |
          |                    |          +---------------------+
          |                    |                 ^
          |                    |                 | Brain revokes capability
          |                    |                 |   (signed revocation stream)
          |                    |                 |   / emit.audit (revocation)
          |                    |                 v
          |                    |          +---------------------+
          |                    |          | CAP_REVOKED          | (terminal)
          |                    +--------->|  (capability invalid;|
          |                               |   must not continue) |
          |                               +---------------------+
          |                    |
          |                    | wall-clock >= not_valid_after
          |                    |   OR policy_snapshot_not_valid_after reached
          |                    |   / emit.audit (capability expiry)
          |                    v
          |              +---------------------+
          |              | CAP_EXPIRED           | (terminal)
          |              |  (absolute time bound  |
          |              |   reached)             |
          |              +-----+-----------------+
          |                    ^
          +--------------------+
          | (cap expires while still CAP_VALID)

          (separate path: executor exercises the capability)
          | CAP_VALID
          |   executor validates token, observes watermark, checks eligibility
          |   / emit.audit (exercise attempt)
          v
                         +-------------------------+
                         | CAP_EXERCISED            |
                         |  (capability consumed;   |
                         |   single-use per ADR     |
                         |   2.4 max_continuation_  |
                         |   attempts_per_command=1)|
                         +-----------+-------------+
                                     |
                                     | continuation ends
                                     |   / emit.audit (exercise complete)
                                     v
                         (control passes to Continuation Execution
                          machine, Section 3; capability remains
                          EXERCISED for audit and dedup)
```

State inventory:

| State | Description | Exerciseable? | Terminal? |
|---|---|---|---|
| `CAPABILITY_ISSUED` | Brain signed and emitted the capability; transient entry state. | No | No |
| `CAP_NOT_YET_VALID` | `not_valid_before` not yet reached (lease still active or grace not elapsed). | No | No |
| `CAP_VALID` | All time and watermark guards hold; capability may be exercised. | Yes | No |
| `CAP_EXERCISED` | Executor has consumed the capability for a continuation attempt. | No (single-use) | Yes (for exercise) |
| `CAP_EXPIRED` | `not_valid_after` or `policy_snapshot_not_valid_after` reached. | No | Yes |
| `CAP_REVOKED` | Brain revoked the capability via signed revocation stream. | No | Yes |
| `CAP_SUPERSEDED` | Lease renewal issued a new capability; this one is revoked even if its `not_valid_after` is later (ADR Invariant 3a). | No | Yes |

Implementation notes:

- `CAP_SUPERSEDED` is distinct from `CAP_REVOKED` because the cause and audit semantics differ: supersession is a routine consequence of renewal, whereas revocation is an exceptional Brain-initiated invalidation. Downstream systems must reject both, but operators need to distinguish them in the audit chain.
- The capability is single-use: `max_continuation_attempts_per_command` defaults to 1 (ADR 2.4). Once `CAP_EXERCISED`, the same `capability_id` cannot be re-exercised; a second attempt requires a new lease and a new capability.
- `CAP_VALID ⟶ CAP_EXPIRED` can fire even while the capability is valid but unexercised, if the Brain recovers before the executor uses it. The executor must not exercise an expired capability.
- The `not_valid_before` guard ties this machine to the lease machine: the capability cannot enter `CAP_VALID` until the lease has entered `LEASE_EXPIRED`.

---

## 3. Continuation Execution State Machine

This machine governs the executor's actual continuation work after lease expiry (ADR 2.3, 2.4, 2.6, 2.12). It picks up where the lease machine (`LEASE_EXPIRED`) and capability machine (`CAP_VALID`) meet.

The ADR's Section 4.1 collapses execution into a single `CONTINUING` node with terminal branches. Here the execution path is expanded into `ELIGIBLE`, `CONTINUING`, the three outcome states, `RECONCILING`, and the four reconciliation classifications.

```text
                         +-------------------------+
                         | CONT_ELIGIBLE            |
   entry: lease EXPIRED  |  (all ADR 2.3 criteria   |
   + cap VALID           |   checked; default STOP)  |
                         +-----------+-------------+
                                     |
                                     | executor chooses to continue (optional)
                                     | [2-signal] AND [cap.token.valid] AND
                                     |   [watermark.ok] AND [no-cancel] AND
                                     |   [class.permitted] AND [tenant.match] AND
                                     |   [local state sufficient] AND
                                     |   [bounded: est. within max_continuation_duration
                                     |    and max_continuation_operations] AND
                                     |   [time bounds within cap window] AND
                                     |   [audit + receipt capability available]
                                     |   / emit.audit (eligibility decision)
                                     |   / open continuation journal
                                     |   / mark cap EXERCISED
                                     v
                         +-------------------------+
                         | CONT_CONTINUING          |
                         |  (performing bounded     |
                         |   operations under cap)  |
                         +-----+------+------+------+
                               |             |             |
                               | all ops     | abort       | wall-clock or monotonic
                               | succeed     | trigger     | reaches T3
                               | /write      | (revocation | (min(not_valid_after,
                               |  receipt    |  received,  |  T2+max_continuation_
                               |             |  cancel     |  duration))
                               |             |  observed,  | /write partial receipt
                               |             |  class      | /freeze in-flight
                               |             |  violation) |  effects
                               v             v             v
                  +-----------------+  +--------------+  +--------------+
                  | CONT_COMPLETED  |  | CONT_ABORTED  |  | CONT_TIMEOUT | (terminal
                  | (receipt signed)|  | (receipt w/   |  | (receipt w/  |  for the
                  |  /emit.audit    |  |  ABORTED)     |  |  TIMEOUT)    |  execution
                  |  /close journal |  |  /emit.audit  |  |  /emit.audit |  attempt)
                  +--------+--------+  +------+--------+  +------+--------+
                           |                 |                  |
                           |                 |                  |
                           +--------+--------+--------+---------+
                                    |
                                    | Brain recovery detected (ADR 2.6.1)
                                    |   [Brain available >= brain_recovery_
                                    |    confirmation_period]
                                    |   / notify executors via heartbeat
                                    v
                         +-------------------------+
                         | CONT_RECONCILING         |
                         |  (Brain receiving and    |
                         |   classifying reports     |
                         |   within completion_     |
                         |   report_deadline)       |
                         +-----+-----+-----+--------+
                               |     |     |     |
              result selection |     |     |     | divergent results OR
              + effect recon   |     |     |     | non-reversible effects OR
              + compensation   |     |     |     | revocation/cancel status
              all clean:      |     |     |     | was unknown OR cap validity
              single report,  |     |     |     | disputed OR no deterministic
              no conflict,    |     |     |     | outcome
              effects applied |     |     |     v
              by stable ID    |     |     | +-------------------+
                               v     v     v| CONT_CONFLICT     |  (terminal)
                  +---------------------+   |  /freeze.effects  |
                  | CONT_VALID           |   |  /queue manual    |
                  |  (VALID_CONTINUATION)|   |   review          |
                  |  /apply effects by   |   |  /emit.audit      |
                  |   stable identity    |   +-------------------+
                  |  /emit.audit         |
                  +----------+----------+
                             |
                             | effects required reconciliation
                             |   or compensation; result still valid
                             |   /emit.audit (reconciled)
                             v
                  +---------------------+
                  | CONT_RECONCILED      |  (terminal)
                  |  (VALID_BUT_         |
                  |   RECONCILED)        |
                  +---------------------+

                  (separate terminal from RECONCILING:)
                  +---------------------+
                  | CONT_INVALID         |  (terminal)
                  |  (INVALID_CONTINUATION:
                  |   criteria not met at
                  |   continuation time;
                  |   executor flagged;
                  |   downstream effects
                  |   frozen if any)
                  +---------------------+
```

`CONT_INVALID` is reachable from `CONT_RECONCILING` when the Brain determines, during report reconciliation, that the executor continued without meeting eligibility (e.g., missing receipt, Class 3 attempt, stale watermark). It is a reconciliation classification, not an executor-observed state.

State inventory:

| State | Description | Terminal? | Reconciliation class (ADR 2.6.4) |
|---|---|---|---|
| `CONT_ELIGIBLE` | All ADR 2.3 criteria checked; executor has not yet decided to continue. Default decision is STOP. | No | — |
| `CONT_CONTINUING` | Executor is performing bounded operations under the capability. | No | — |
| `CONT_COMPLETED` | All operations succeeded; signed receipt produced. | Yes (attempt) | (pending reconciliation) |
| `CONT_ABORTED` | Continuation aborted (revocation observed, cancellation, class violation). | Yes (attempt) | (pending reconciliation) |
| `CONT_TIMEOUT` | Time bound reached before completion. | Yes (attempt) | (pending reconciliation) |
| `CONT_RECONCILING` | Brain is collecting reports and running result selection, effect reconciliation, compensation, manual-review routing. | No | — |
| `CONT_VALID` | `VALID_CONTINUATION` — single report, no conflict, effects applied. | Yes | `VALID_CONTINUATION` |
| `CONT_RECONCILED` | `VALID_BUT_RECONCILED` — valid but effects needed reconciliation/compensation. | Yes | `VALID_BUT_RECONCILED` |
| `CONT_INVALID` | `INVALID_CONTINUATION` — criteria not met at continuation time. | Yes | `INVALID_CONTINUATION` |
| `CONT_CONFLICT` | `CONFLICTING_REPORTS` / `MANUAL_REVIEW_REQUIRED` — divergent or non-reversible. | Yes | `CONFLICTING_REPORTS` / `MANUAL_REVIEW_REQUIRED` |

Implementation notes:

- `CONT_ELIGIBLE` is a decision state, not a work state. The executor re-evaluates all ADR 2.3 criteria atomically. If any guard fails, the executor transitions to a local safe-hold (not shown; it stops and waits for Brain recovery). The default is STOP.
- The three outcome states (`COMPLETED`, `ABORTED`, `TIMEOUT`) are terminal **for the execution attempt** but not for the command; they all flow into `CONT_RECONCILING` after Brain recovery.
- `CONT_RECONCILING` is the only non-terminal post-outcome state. It is owned by the Brain, not the executor. The executor's role ends once it submits its report; the Brain drives reconciliation.
- The four reconciliation classifications (`VALID`, `RECONCILED`, `INVALID`, `CONFLICT`) are terminal for the continuation but may trigger further command-level transitions (see Section 4).
- Split-brain (ADR 2.12) manifests here as multiple executors reaching `CONT_RECONCILING` for the same `command_id` with different `continuation_id` values. The Brain's reconciliation logic (ADR 2.6.3) determines which classification each report receives.

---

## 4. Command State Machine (with Continuation and Replay Paths)

This machine governs the command record itself (ADR 2.6, 2.7). It is the Brain-owned lifecycle that subsumes lease, continuation, and replay outcomes. This expands ADR Section 4.2.

```text
          +-------------------+
          | CMD_PENDING        |
          | (dispatched, not   |
          |  yet leased)       |
          +---------+---------+
                    |
                    | lease issued to executor
                    |   /emit.audit (dispatch + lease)
                    v
          +-------------------+
          | CMD_LEASED         |
          | (executor working  |
          |  under active lease)|
          +----+--------+-----+
               |        |
               |        | lease expires (T1)
               |        |   /emit.audit (expiry)
               |        v
               |  +-------------------+
               |  | CMD_EXPIRED        |
               |  | (lease expired;   |
               |  |  no active work    |
               |  |  authority)       |
               |  +----+-----------+--+
               |       |           |
               |       | cap issued + outage declared + eligible
               |       |   ==> continuation path (Section 3)
               |       |   /emit.audit (continuation started)
               |       v
               |  +-------------------+
               |  | CMD_CONTINUING      |
               |  | (executor in       |
               |  |  CONT_CONTINUING)   |
               |  +----+-----------+--+
               |       |           |
               |       |           | continuation aborted/timed out
               |       |           |   /emit.audit
               |       |           v
               |       |  +-------------------+
               |       |  | CMD_CONT_ABORTED   |
               |       |  | (CONT_ABORTED or   |
               |       |  |  CONT_TIMEOUT)      |
               |       |  +----+-----------+----+
               |       |       |
               |       |       | recovery + reconciliation
               |       |       v
               |       |  +-------------------+
               |       |  | CMD_RECONCILING    |
               |       |  | (Brain classifying |
               |       |  |  report)           |
               |       |  +----+-----------+----+
               |       |       |
               |       |       +--- VALID -----> CMD_SUCCEEDED
               |       |       +--- RECONCILED -> CMD_RECONCILED -> CMD_SUCCEEDED
               |       |       +--- INVALID ---> CMD_INVALID (terminal)
               |       |       +--- CONFLICT ---> CMD_MANUAL_REVIEW (terminal)
               |       |
               |       | continuation completed (CONT_COMPLETED)
               |       |   + recovery + reconciliation
               |       v
               |  +-------------------+
               |  | CMD_RECONCILING    |
               |  | (same as above)    |
               |  +----+-----------+----+
               |       |
               |       | (same four classification exits)
               |       v
               |  (classification outcomes as above)
               |
               | command completes normally under lease
               |   /emit.audit (completion)
               v
          +-------------------+        +-------------------+
          | CMD_SUCCEEDED      |        | CMD_FAILED         |
          | (terminal)          |        | (terminal)        |
          +-------------------+        +-------------------+

          (replay path — Brain-authorized, post-reconciliation)
          +-------------------+
          | CMD_RECONCILED     |
          | (VALID_BUT_        |
          |  RECONCILED;       |
          |  effects applied)  |
          +---------+---------+
                    |
                    | Brain authorizes replay
                    |   [all continuation reports reconciled]
                    |   [effect status known or compensated]
                    |   /emit.audit (replay authorized)
                    |   /mark original CMD as REPLAYED
                    |   /link replay command via causation
                    v
          +-------------------+
          | CMD_REPLAY          |
          | (new lease, new     |
          |  execution identity;|
          |  SAME root_command_ |
          |  id for effect       |
          |  identity)           |
          +----+-----------+----+
               |           |
               | replay completes / [effect identity == root]
               |   /emit.audit
               v
          +-------------------+
          | CMD_SUCCEEDED      | (terminal)
          | (replay success)   |
          +-------------------+
               |
               | replay fails
               v
          +-------------------+
          | CMD_FAILED         | (terminal)
          | (replay failure)   |
          +-------------------+

          (cancellation path — orthogonal)
          +-------------------+
          | CMD_LEASED or      |
          | CMD_CONTINUING     |
          +---------+---------+
                    | cancellation observed at or before watermark
                    |   /emit.audit (cancellation)
                    v
          +-------------------+
          | CMD_CANCELLED       | (terminal)
          +-------------------+

          (revocation path — orthogonal)
          +-------------------+
          | CMD_LEASED or      |
          | CMD_CONTINUING     |
          +---------+---------+
                    | lease or capability revoked by Brain
                    |   /emit.audit (revocation)
                    v
          +-------------------+
          | CMD_REVOKED         | (terminal)
          +-------------------+
```

State inventory:

| State | Description | Terminal? | Owner |
|---|---|---|---|
| `CMD_PENDING` | Command dispatched but no lease issued yet. | No | Brain |
| `CMD_LEASED` | Lease issued; executor working under active lease. | No | Brain |
| `CMD_SUCCEEDED` | Command completed successfully (normal or replay). | Yes | Brain |
| `CMD_FAILED` | Command failed (normal or replay). | Yes | Brain |
| `CMD_EXPIRED` | Lease expired; no active work authority. | No | Brain |
| `CMD_CONTINUING` | Executor is in `CONT_CONTINUING` under a valid capability. | No | Brain (observed) |
| `CMD_CONT_ABORTED` | Continuation aborted or timed out; awaiting reconciliation. | No | Brain |
| `CMD_RECONCILING` | Brain is classifying continuation report(s). | No | Brain |
| `CMD_RECONCILED` | `VALID_BUT_RECONCILED`; effects applied after reconciliation/compensation. | No | Brain |
| `CMD_INVALID` | `INVALID_CONTINUATION`; executor exceeded authority. | Yes | Brain |
| `CMD_MANUAL_REVIEW` | `CONFLICTING_REPORTS` / `MANUAL_REVIEW_REQUIRED`; operator decision required. | Yes | Brain |
| `CMD_REPLAY` | Brain-authorized replay with new lease, new execution identity, same root effect identity. | No | Brain |
| `CMD_CANCELLED` | Cancellation observed at or before revocation watermark. | Yes | Brain |
| `CMD_REVOKED` | Lease or capability revoked by Brain. | Yes | Brain |

Implementation notes:

- `CMD_REPLAY` preserves the **root** command ID for all external-effect identities (ADR 2.7). The replay creates a new command record for execution metadata, but the stable key `(root_command_id, operation_id, side_effect_slot)` must never use the replay record's command ID. This is the single most important replay invariant.
- Replay is reachable only from `CMD_RECONCILED` (or from `CMD_EXPIRED`/`CMD_CONT_ABORTED` paths after reconciliation), never directly from `CMD_CONTINUING`. The Brain must reconcile all continuation reports before authorizing replay (ADR 2.7).
- `CMD_CANCELLED` and `CMD_REVOKED` are orthogonal terminal states reachable from multiple working states. They are triggered by observation of cancellation/revocation at or before the revocation watermark.
- `CMD_MANUAL_REVIEW` is terminal until an operator resolves it; no automatic transition out exists.

---

## 5. Brain Outage Detection State Machine

This machine governs the executor's detection of Brain unavailability (ADR 2.2). It is executor-owned and runs concurrently with the lease and capability machines. It is the precondition for `CONT_ELIGIBLE` (Section 3) allowing continuation.

The ADR's Section 2.2 specifies the detection rules textually; this machine makes the detection lifecycle and the grace-period semantics explicit.

```text
                         +-------------------------+
                         | OUTAGE_MONITORING        |
   entry (lease active   |  (executor observing     |
    or expired)          |   Brain signals)         |
                         +-----+-----------+-------+
                               |                 |
                               | first signal     | all signals
                               | crosses          | return below
                               | threshold        | threshold
                               | (1 of 5)         | within grace
                               v                 |
                         +-------------------------+ |
                         | OUTAGE_SIGNAL_DETECTED  | |
                         |  (1 signal over          | |
                         |   threshold; NOT yet    | |
                         |   an outage)            | |
                         +-----+-----------+-------+ |
                               |                 |
                               | second          |
                               | independent     |
                               | signal crosses  |
                               | threshold        |
                               | [2-signal] AND   |
                               |   [at least 1    |
                               |    direct-Brain] |
                               | (start grace     |
                               |  timer at         |
                               |  monotonic_outage_|
                               |  start)           |
                               v                 |
                         +-------------------------+ |
                         | OUTAGE_GRACE_PERIOD      | |
                         |  (waiting >=             | |
                         |   brain_outage_grace_   | |
                         |   period; default 30s)   | |
                         +-----+-----------+-------+ |
                               |                 |
                               | grace elapsed    |
                               | AND [2-signal    |
                               |   still holds]   |
                               | AND [time anchor  |
                               |   signed; no      |
                               |   rollback >      |
                               |   max_clock_       |
                               |   rollback_       |
                               |   tolerance]      |
                               | /persist outage   |
                               |  record locally:   |
                               |  timestamp,        |
                               |  signals, lease   |
                               |  fingerprint,     |
                               |  signed anchor    |
                               | /emit.audit        |
                               |  (outage declared) |
                               v                 |
                         +-------------------------+ |
                         | OUTAGE_DECLARED          | |
                         |  (continuation may now  | |
                         |   be considered if cap  | |
                         |   valid; control passes | |
                         |   to CONT_ELIGIBLE)     | |
                         +-----+-----------+-------+ |
                               |                 |
                               | Brain heartbeat  |
                               | acknowledged    |
                               | OR lease renewal |
                               |   succeeds OR   |
                               |   status query   |
                               |   succeeds       |
                               | [Brain available |
                               |   observed]       |
                               | /emit.audit       |
                               |  (recovery signal  |
                               |   detected)       |
                               v                 |
                         +-------------------------+ |
                         | OUTAGE_RECOVERING        | |
                         |  (Brain available;       | |
                         |   confirming for         | |
                         |   brain_recovery_       | |
                         |   confirmation_period;   | |
                         |   default 10s)           | |
                         +-----+-----------+-------+ |
                               |                 |
                               | [Brain available  |
                               |   for full        |
                               |   confirmation    |
                               |   period]         |
                               | /emit.audit        |
                               |  (recovery declared)|
                               | /time-anchor        |
                               |  recovery          |
                               v                 |
                         +-------------------------+ |
                         | OUTAGE_RECOVERED         | |
                         |  (normal operation       | |
                         |   resumes; executors     | |
                         |   refresh policy +       | |
                         |   watermark)            | |
                         +-------------------------+ |
                               |                 |
                               +------<----------+
                               (return to MONITORING)

          (signal disappears during grace period:)
          OUTAGE_GRACE_PERIOD
                               |
                               | signals drop below
                               |   threshold before
                               |   grace elapsed
                               |   /emit.audit
                               |    (transient; no
                               |     outage declared)
                               v
                         (return to OUTAGE_MONITORING)

          (revocation received during any outage state:)
          any outage state
                               |
                               | revocation entry
                               |   received in
                               |   revocation stream
                               |   /STOP continuation
                               |   /emit.audit
                               v
                         (executor must stop immediately;
                          no state transition within this
                          machine — control passes to
                          CMD_CANCELLED / CMD_REVOKED)
```

State inventory:

| State | Description | Outage declared? | Continuation permitted? |
|---|---|---|---|
| `OUTAGE_MONITORING` | Normal observation; no signals over threshold. | No | No |
| `OUTAGE_SIGNAL_DETECTED` | One signal over threshold; not yet an outage. | No | No |
| `OUTAGE_GRACE_PERIOD` | Two independent signals (one direct-Brain) over threshold; waiting for grace to elapse. | No (pending) | No |
| `OUTAGE_DECLARED` | Grace elapsed; outage record persisted with signed anchor. | Yes | Conditionally (if `CAP_VALID` and all `CONT_ELIGIBLE` guards hold) |
| `OUTAGE_RECOVERING` | Brain availability observed; confirming for `brain_recovery_confirmation_period`. | Yes (still) | No (continuation must stop) |
| `OUTAGE_RECOVERED` | Brain confirmed available for full confirmation period; recovery declared and time-anchored. | No | No (normal operation resumes) |

Implementation notes:

- `OUTAGE_SIGNAL_DETECTED` is explicitly **not** an outage. A single signal crossing threshold is a monitoring state; the ADR requires at least two independent signals, one of which must be a direct-Brain signal (ADR 2.2.2). This state exists to prevent executors from bootstrapping authority on transient failures.
- `OUTAGE_GRACE_PERIOD` is timed with the **monotonic** clock (ADR 2.2.3, 2.8) to prevent extension via wall-clock rollback. The grace period starts at `monotonic_outage_start`, not at the first signal.
- `OUTAGE_DECLARED` is the only state from which continuation may be considered. Even then, continuation is optional and pessimistic; the executor may always choose STOP (ADR 2.3).
- Witness statements alone can never drive the machine past `OUTAGE_SIGNAL_DETECTED` without a direct-Brain signal (ADR 2.2.2). If only witness signals are over threshold, the machine stays in `SIGNAL_DETECTED` until a direct-Brain signal joins or the witness signals drop.
- `OUTAGE_RECOVERING` requires confirmation for `brain_recovery_confirmation_period` (default 10s) before transitioning to `OUTAGE_RECOVERED`. If Brain availability flickers during this period, the machine returns to `OUTAGE_DECLARED`.
- The revocation-received edge is not a state transition within this machine; it is an interrupt that forces the executor to stop and routes the command to `CMD_CANCELLED` or `CMD_REVOKED` (Section 4).

---

## 6. Recovery Protocol State Machine

This machine governs the Brain-owned recovery protocol (ADR 2.15). It is the Brain-side counterpart to the executor's outage machine (Section 5) and the continuation execution machine (Section 3). It runs after `OUTAGE_RECOVERED` and drives commands through reconciliation to terminal states.

The ADR's Section 2.15 lists the recovery protocol as a 10-step sequence. This machine makes the states, transitions, and gating conditions explicit.

```text
                         +-----------------------------+
                         | RECOVERY_DETECTION           |
   entry: Brain available|  (confirm availability for   |
   observed              |   brain_recovery_confirma-  |
                         |   tion_period; witness      |
                         |   confirmation optional)    |
                         +-----------+-----------------+
                                     |
                                     | [available >= confirmation_period]
                                     |   /time-anchor recovery
                                     |   /emit.audit (recovery declared)
                                     |   /notify executors via heartbeat
                                     v
                         +-----------------------------+
                         | RECOVERY_ATOMICITY           |
                         |  (for each active            |
                         |   continuation: apply        |
                         |   operation atomicity rule)  |
                         +-----------+-----------------+
                                     |
                                     | for each in-flight op:
                                     |   IF op committed or irreversible:
                                     |     finish + report
                                     |   IF op not yet committed:
                                     |     abort
                                     |   (never both for same op)
                                     |   /emit.audit (per-op decision)
                                     v
                         +-----------------------------+
                         | RECOVERY_REPORT_COLLECTION   |
                         |  (receive all pending        |
                         |   continuation reports       |
                         |   within completion_report_  |
                         |   deadline)                  |
                         +-----------+-----------------+
                                     |
                                     | [all reports received] OR
                                     |   [deadline elapsed]
                                     |   /emit.audit (collection closed)
                                     v
                         +-----------------------------+
                         | RECOVERY_RECONCILIATION       |
                         |  (result selection +         |
                         |   effect reconciliation +    |
                         |   compensation +             |
                         |   manual-review routing)     |
                         +-----+-----+-----+-----+------+
                               |     |     |     |
              single valid,    |     |     |     | divergent results OR
              no conflict,     |     |     |     | non-reversible effects OR
              effects applied  |     |     |     | revocation/cancel status
              by stable ID     |     |     |     | unknown during continuation
                               v     |     |     v
                  +----------------+ |   +---------------------+
                  | RECOVERY_VALID  | |   | RECOVERY_CONFLICT   |
                  | (VALID_CONTIN-  | |   |  (freeze effects;   |
                  |  UATION; cmd -> | |   |   queue manual       |
                  |  CMD_SUCCEEDED) | |   |   review; cmd ->     |
                  +----------------+ |   |   CMD_MANUAL_REVIEW) |
                                     |   +---------------------+
              effects needed         |
              reconciliation         |
              or compensation;       |
              result still valid     |
                                     v
                  +----------------+
                  | RECOVERY_RECONCILED |
                  |  (VALID_BUT_        |
                  |   RECONCILED;       |
                  |   cmd ->            |
                  |   CMD_RECONCILED)   |
                  +--------+-----------+
                           |
                           | Brain authorizes replay
                           |   [all reports reconciled]
                           |   [effect status known or
                           |    compensated]
                           |   /emit.audit (replay
                           |    authorized)
                           v
                  +----------------+
                  | RECOVERY_REPLAY_AUTH |
                  |  (authorize replay;  |
                  |   new lease + new    |
                  |   execution identity;|
                  |   same root_command_ |
                  |   id for effects)    |
                  +--------+-----------+
                           |
                           | replay command dispatched
                           |   /emit.audit
                           v
                  (control passes to CMD_REPLAY,
                   Section 4)

          (invalid continuation detected during reconciliation:)
          RECOVERY_RECONCILIATION
                                     |
                                     | [executor continued without
                                     |  eligibility OR no receipt OR
                                     |  Class 3 attempted]
                                     |   /freeze downstream effects
                                     |   /flag executor
                                     |   /emit.audit
                                     v
                  +---------------------+
                  | RECOVERY_INVALID      | (terminal)
                  |  (INVALID_CONTINUATION;|
                  |   cmd -> CMD_INVALID)  |
                  +---------------------+

          (after all reconciliation + replay decisions:)
          any RECOVERY_* terminal or RECOVERY_REPLAY_AUTH
                                     |
                                     | [all executors refreshed
                                     |  policy snapshot + revocation
                                     |  watermark]
                                     v
                         +-----------------------------+
                         | RECOVERY_POLICY_REFRESH       |
                         |  (all executors refresh      |
                         |   policy + watermark before   |
                         |   accepting new work)         |
                         +-----------+-----------------+
                                     |
                                     | [all executors refreshed]
                                     |   /emit.audit
                                     v
                         +-----------------------------+
                         | RECOVERY_AUDIT_COMPLETION     |
                         |  (finalize all continuation   |
                         |   events in immutable ledger) |
                         +-----------+-----------------+
                                     |
                                     | [audit ledger complete]
                                     |   /emit.audit (recovery complete)
                                     v
                         +-----------------------------+
                         | RECOVERY_COMPLETE             | (terminal)
                         |  (normal operation resumed;   |
                         |   SIGMA gate may be evaluated |
                         |   for unblocking ONLY after   |
                         |   implementation certified)   |
                         +-----------------------------+
```

State inventory:

| State | Description | Terminal? | ADR 2.15 step |
|---|---|---|---|
| `RECOVERY_DETECTION` | Confirm Brain availability for `brain_recovery_confirmation_period`. | No | Step 1 |
| `RECOVERY_ATOMICITY` | Apply per-operation atomicity rule to all active continuations. | No | Step 2 |
| `RECOVERY_REPORT_COLLECTION` | Receive all continuation reports within `completion_report_deadline`. | No | Step 3 |
| `RECOVERY_RECONCILIATION` | Result selection, effect reconciliation, compensation, manual-review routing. | No | Step 4 |
| `RECOVERY_VALID` | `VALID_CONTINUATION`; command → `CMD_SUCCEEDED`. | Yes (for this recovery) | Step 4 outcome |
| `RECOVERY_RECONCILED` | `VALID_BUT_RECONCILED`; command → `CMD_RECONCILED`. | No (leads to replay) | Step 4 outcome |
| `RECOVERY_CONFLICT` | `CONFLICTING_REPORTS` / `MANUAL_REVIEW_REQUIRED`; freeze + queue. | Yes | Steps 4–6 |
| `RECOVERY_INVALID` | `INVALID_CONTINUATION`; executor flagged, effects frozen. | Yes | Step 4 outcome |
| `RECOVERY_REPLAY_AUTH` | Brain authorizes replay after reconciliation. | No | Step 7 |
| `RECOVERY_POLICY_REFRESH` | All executors refresh policy snapshots and revocation watermarks. | No | Step 8 |
| `RECOVERY_AUDIT_COMPLETION` | Finalize all continuation events in the immutable audit ledger. | No | Step 9 |
| `RECOVERY_COMPLETE` | Normal operation resumed; gate evaluation may be considered (separate from certification). | Yes | Step 10 |

Implementation notes:

- `RECOVERY_ATOMICITY` is the most safety-critical state. The ADR's atomicity rule (2.15 step 2, 2.12.2) requires that for each in-flight operation, the Brain either finishes it (if committed/irreversible) or aborts it (if uncommitted), but **never both** for the same operation. This must be implemented as a per-operation decision with an audit record, not a blanket command-level decision.
- `RECOVERY_REPORT_COLLECTION` has a hard deadline (`completion_report_deadline`). Reports arriving after the deadline are recorded but may be classified as `INVALID_CONTINUATION` if they cannot be reconciled (ADR 2.6.2: "Reporting is mandatory regardless of outcome. Silent continuation is forbidden.").
- `RECOVERY_RECONCILIATION` fans out to four classification states (`VALID`, `RECONCILED`, `CONFLICT`, `INVALID`), matching the continuation execution machine's reconciliation classifications (Section 3). The two machines are consistent by design: the Brain-side classification drives the command state, and the executor-side classification is the same label applied to the continuation record.
- `RECOVERY_REPLAY_AUTH` is the only entry point to `CMD_REPLAY` (Section 4). Replay is never autonomous; it requires explicit Brain authorization after all reports are reconciled (ADR 2.7).
- `RECOVERY_POLICY_REFRESH` and `RECOVERY_AUDIT_COMPLETION` are mandatory post-reconciliation steps. No new work may be accepted until all executors have refreshed their policy snapshots and revocation watermarks (ADR 2.15 step 8).
- `RECOVERY_COMPLETE` is terminal for the recovery protocol, but it is **not** the same as unblocking `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE`. The ADR (Section 2.15 step 10, Section 13) is explicit: gate evaluation is a separate certification process, not an automatic consequence of recovery completion.

---

## Cross-Machine Relationships

The six state machines are not independent; they are coupled at specific synchronization points. Implementers must treat these as protocol handoffs.

```text
  Lease Machine          Capability Machine         Execution Machine
  -----------            -----------------          -----------------
  LEASE_EXPIRED ----+--> CAP_VALID ----+----------> CONT_ELIGIBLE
                    |                   |
                    |                   +----------> (if exercised) CAP_EXERCISED
                    |
                    | (outage machine must also be OUTAGE_DECLARED)
                    v
              OUTAGE_DECLARED (Outage Machine) ----> CONT_ELIGIBLE [2-signal guard]

  Execution Machine      Command Machine            Recovery Machine
  ----------------       ----------------           ----------------
  CONT_VALID ----------> CMD_SUCCEEDED              (no recovery needed)
  CONT_RECONCILED ------> CMD_RECONCILED ----------> RECOVERY_RECONCILED
                                                   ---> RECOVERY_REPLAY_AUTH ---> CMD_REPLAY
  CONT_INVALID ---------> CMD_INVALID               (recovery classifies)
  CONT_CONFLICT --------> CMD_MANUAL_REVIEW          RECOVERY_CONFLICT

  Outage Machine         Recovery Machine
  ---------------        ----------------
  OUTAGE_RECOVERED ----> RECOVERY_DETECTION (Brain-side)
```

Key handoffs:

1. **Lease → Capability**: `LEASE_EXPIRED` is the precondition for `CAP_NOT_YET_VALID ⟶ CAP_VALID`. The capability's `not_valid_before` is bound to the lease's `expires_at`.
2. **Capability + Outage → Execution**: `CONT_ELIGIBLE` requires both `CAP_VALID` and `OUTAGE_DECLARED`. Neither alone is sufficient.
3. **Execution → Command**: The four reconciliation classifications (`VALID`, `RECONCILED`, `INVALID`, `CONFLICT`) map directly to command states (`CMD_SUCCEEDED`, `CMD_RECONCILED`, `CMD_INVALID`, `CMD_MANUAL_REVIEW`).
4. **Command → Recovery**: `CMD_RECONCILED` is the only entry point to `RECOVERY_REPLAY_AUTH` and thus to `CMD_REPLAY`.
5. **Outage → Recovery**: `OUTAGE_RECOVERED` (executor-side) triggers `RECOVERY_DETECTION` (Brain-side). The recovery machine is the Brain's counterpart to the executor's outage machine.

---

## Timing Alignment (ADR Section 5)

The state machines above operate within the timing envelope defined in ADR Section 5.1. The key time points and the state transitions they gate:

| Time | ADR 5.1 label | State transition gated |
|---|---|---|
| T0 | Lease issued | `LEASE_ISSUED` entry |
| T1 | Lease expires; `not_valid_before` may equal T1 | `LEASE_ACTIVE ⟶ LEASE_EXPIRED`; `CAP_NOT_YET_VALID ⟶ CAP_VALID` |
| T2 | Brain outage declared (after grace period) | `OUTAGE_GRACE_PERIOD ⟶ OUTAGE_DECLARED`; enables `CONT_ELIGIBLE ⟶ CONT_CONTINUING` |
| T3 | Latest permitted continuation end | `CONT_CONTINUING ⟶ CONT_TIMEOUT` (if not completed by T3) |
| T4 | Completion report deadline (after recovery) | `RECOVERY_REPORT_COLLECTION` closes; late reports may be classified `INVALID` |

The grace period (T1 → T2) is bounded below by `brain_outage_grace_period` (default 30s). The continuation window (T2 → T3) is bounded by `min(T2 + max_continuation_duration, capability not_valid_after)`. The report deadline (T3 → T4) is bounded by `completion_report_deadline` after recovery detection.

All durations are measured with the **monotonic** clock to prevent extension via wall-clock rollback (ADR 2.8). Wall-clock anchors are signed by the Brain and used only for cross-machine ordering and audit, not for duration measurement.

---

## Open Implementation Questions

These are planning-level questions to be resolved in subsequent planning documents, not in this artifact:

1. **Capability rotation atomicity**: Is `LEASE_RENEWED`'s `/rotate.capability` action a single atomic write, or a multi-step sequence with its own sub-states? The ADR requires the prior capability to be revoked and the new one issued atomically (Invariant 3a), but the storage layer may not support a single atomic write across two records.
2. **Outage state persistence**: Does `OUTAGE_DECLARED` need to survive executor process restart? The ADR requires the outage record to be persisted locally (2.2.2), but the state machine does not specify a "reloaded" entry path.
3. **Recovery protocol concurrency**: `RECOVERY_ATOMICITY` and `RECOVERY_REPORT_COLLECTION` may overlap in practice (some executors report while others are still being stopped). Should the machine model these as concurrent sub-states, or is the sequential model above sufficient?
4. **Replay authorization gating**: `RECOVERY_REPLAY_AUTH` requires "all reports reconciled," but the ADR does not specify what happens to reports that never arrive (silent continuation). The machine above classifies them as `INVALID`, but this should be confirmed in the reconciliation planning document.
5. **Manual review exit**: `CMD_MANUAL_REVIEW` and `RECOVERY_CONFLICT` are terminal until an operator resolves them. The operator-driven exit state machine is out of scope for this document and should be specified in a separate operations planning artifact.

---

## References

- ADR-MC-001 Section 2.1 — Lease lifecycle (source for Section 1)
- ADR-MC-001 Section 2.1.4 — Continuation capability (source for Section 2)
- ADR-MC-001 Section 2.3 — Continuation eligibility (source for Section 3 entry guards)
- ADR-MC-001 Section 2.4 — Continuation limits (bounds on `CONT_CONTINUING`)
- ADR-MC-001 Section 2.6 — Reconciliation protocol (source for Section 3 reconciliation classifications)
- ADR-MC-001 Section 2.7 — Replay semantics (source for Section 4 replay path)
- ADR-MC-001 Section 2.8 — Time authority (monotonic clock, signed anchors)
- ADR-MC-001 Section 2.12 — Split-brain handling (source for `CONT_CONFLICT`)
- ADR-MC-001 Section 2.15 — Recovery protocol (source for Section 6)
- ADR-MC-001 Section 4.1 — Lease and capability state machine (collapsed; expanded here into Sections 1 and 2)
- ADR-MC-001 Section 4.2 — Command state machine (source for Section 4)
- ADR-MC-001 Section 5.1 — Grace period and continuation window timing (source for Timing Alignment)
- ADR-MC-001 Section 5.2 — Overlapping continuation and recovery (source for cross-machine relationships)
- ADR-MC-001 Section 7 — Invariants (cross-referenced per machine)