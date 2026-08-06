# 07 — Failure Mode and Recovery Matrix (Executor Continuation)

**Package:** Executor Continuation Implementation Planning
**Status:** PLANNING ARTIFACT — no runtime code, no deployment, no authority activation
**Source of truth:** `docs/mission-control/ADR_MC_001_EXECUTOR_CONTINUATION.md` (ACCEPTED, ratified 2026-08-05)
**Related docs:** `01_IMPLEMENTATION_ARCHITECTURE.md`, `02_COMPONENT_DEPENDENCY_GRAPH.md`, `03_INTERFACE_SPECIFICATIONS.md`, `04_STATE_MACHINES.md`, `05_SEQUENCE_DIAGRAMS.md`, `06_THREAT_MODEL.md`, `10_ROLLOUT_ROLLBACK_PLAN.md`
**Scope:** This document enumerates every failure mode identified by ADR-MC-001 (Sections 2.12, 2.15, 6.1, 6.2, 6.3) plus implementation-level failure modes surfaced by the 14-component architecture in `01_IMPLEMENTATION_ARCHITECTURE.md`. For each failure mode it specifies the trigger condition, detection mechanism, immediate action, recovery action, final state, data-integrity guarantee, and audit requirement. It maps each failure mode to the affected components (C1–C14) and the ADR invariants (1–15) it touches. It also defines the operation atomicity rule from ADR §2.12.2 and provides a recovery decision tree.

This is a planning artifact only. It introduces no runtime code, ratifies no behavior, unblocks no gate, and authorizes no implementation. Implementation requires separate ADRs, branches, and authorizations per ADR-MC-001 Section 10.

---

## 1. How to Read This Matrix

### 1.1 Failure Mode Identifier Convention

Each failure mode is assigned a stable identifier of the form `FM-<group>-<n>`:

| Group | Prefix | Source |
|---|---|---|
| Lease expiry decisions | `FM-LED-#` | ADR §6.1 lease expiry decision matrix |
| Continuation outcomes | `FM-CO-#` | ADR §6.2 continuation outcome matrix |
| Split-brain scenarios | `FM-SB-#` | ADR §2.12, §6.3 threat model |
| Threat-model entries | `FM-TM-#` | ADR §6.3 threat model |
| Implementation-level | `FM-IMPL-#` | Component architecture (this document) |

Identifiers are stable for cross-reference from acceptance tests, runbooks, and review checklists. New failure modes discovered during implementation must be appended with a new number rather than reusing a retired one.

### 1.2 Column Legend

Every failure-mode entry uses the same columns:

| Column | Meaning |
|---|---|
| **Trigger condition** | The concrete state or event that causes the failure mode to occur. |
| **Detection mechanism** | Which component or signal observes the condition and how (e.g., C3 heartbeat miss, C10 divergent `result_digest`). |
| **Immediate action** | The action taken automatically, in real time, by the executor or Brain, without operator involvement. |
| **Recovery action** | The action taken after Brain recovery (or after operator review) to return the system to a safe, reconciled state. |
| **Final state** | The terminal or quiescent state the command or continuation reaches. |
| **Data integrity guarantee** | What is provably preserved about externally visible effects, audit records, and continuation journals. |
| **Audit requirement** | Which audit events must be present in the immutable ledger (C12) for this failure mode to be considered resolved. |

### 1.3 Component and Invariant References

Components C1–C14 are defined in `01_IMPLEMENTATION_ARCHITECTURE.md` Section 2 and `02_COMPONENT_DEPENDENCY_GRAPH.md` Section 1. Invariants 1–15 are defined in ADR-MC-001 Section 7. The component/invariant mapping columns use the short IDs:

- **C1** Signed lease token service · **C2** Continuation capability service · **C3** Brain heartbeat endpoint · **C4** Witness statement service · **C5** Executor local state cache · **C6** Revocation stream · **C7** Policy snapshot registry · **C8** Continuation journal store · **C9** Completion receipt service · **C10** Reconciliation engine · **C11** Conflict review queue · **C12** Audit event pipeline · **C13** Downstream effect identity layer · **C14** Signed time-anchor service.

### 1.4 Operation Atomicity Rule (ADR §2.12.2)

This rule governs every failure mode in which the Brain recovers while a continuation is still in progress. It is stated here once and referenced by the relevant entries.

> **Operation atomicity rule (ADR §2.12.2):** When the Brain recovers while a continuation is active, for each in-progress operation the executor applies the atomicity rule:
>
> - If the operation has **already committed** or is **irreversible**, **finish** it and report the result.
> - If the operation has **not yet committed**, **abort** it.
> - The same operation is **never** both finished and aborted.
>
> The binary state of the operation at the instant of recovery detection determines the branch. There is no "partially committed" category. An operation is either committed (finish) or uncommitted (abort). The executor must record the determination per operation in the continuation journal (C8) and surface it in the completion report (C9).

This rule is the implementation-level expression of the "no silent conflict resolution" principle (ADR §2.12.2): the system never silently picks both outcomes for the same operation. The rule is restated in the recovery protocol step 2 (ADR §2.15) and is referenced by failure modes `FM-SB-4`, `FM-IMPL-2`, `FM-IMPL-3`, and `FM-IMPL-9`.

### 1.5 Default Decision is STOP

Per ADR §2.3, continuation is optional and pessimistic. The default decision is **STOP**. Any failure mode whose detection cannot positively confirm all eligibility criteria must resolve to STOP and the corresponding aborted/expired state. Failure modes below note this where applicable.

---

## 2. Lease Expiry Decision Matrix (ADR §6.1)

These failure modes correspond row-for-row to ADR §6.1. They describe the executor's decision at the moment of lease expiry, before any continuation is attempted.

### FM-LED-1 — Lease expired, no continuation capability issued

| Field | Value |
|---|---|
| **Trigger condition** | Lease `expires_at` reached; no `continuation_capability_id` was ever issued for this command. |
| **Detection mechanism** | C1 marks the lease EXPIRED; C5 local state cache has no capability reference; executor self-check finds no capability. |
| **Immediate action** | Executor stops. No continuation is possible. Downstream systems (C13) reject any further effect claims under the expired lease token (Invariant 2). |
| **Recovery action** | Brain may authorize a replay (ADR §2.7) after recovery, using a new lease and preserving `root_command_id` in effect identities. |
| **Final state** | `ABORTED` or `REPLAY` later. |
| **Data integrity guarantee** | No continuation effects were produced. Any in-flight normal-execution effects already committed remain authoritative; uncommitted effects are discarded. |
| **Audit requirement** | Lease expiry event (C1 → C12); command terminal state event. |
| **Components** | C1, C5, C12, C13 |
| **Invariants** | 1, 2, 4 |

### FM-LED-2 — Lease expired, capability issued but not yet valid, Brain available

| Field | Value |
|---|---|
| **Trigger condition** | Lease expired; capability exists but `not_valid_before` has not been reached, or `not_valid_before` is in the future; Brain is available (heartbeat OK). |
| **Detection mechanism** | C2 `validate_capability` returns `NOT_YET_VALID`; C3 heartbeat returns OK. |
| **Immediate action** | Executor stops and requests a new lease from the Brain. Capability is not exercisable. |
| **Recovery action** | Brain issues a new lease (and may issue a new capability per ADR §2.1.2 renewal rules, superseding the prior one per Invariant 3a). |
| **Final state** | `EXPIRED → RENEWED` or `FAILED`. |
| **Data integrity guarantee** | No continuation effects produced. Capability was never usable in this window. |
| **Audit requirement** | Lease expiry event; capability issuance/supersession event if renewed (C2 → C12). |
| **Components** | C1, C2, C3, C12 |
| **Invariants** | 2, 3, 3a, 4 |

### FM-LED-3 — Lease expired, capability valid, Brain available

| Field | Value |
|---|---|
| **Trigger condition** | Lease expired; capability is within its validity window; Brain is available (heartbeat OK, lease renewal responsive). |
| **Detection mechanism** | C2 capability validates; C3 heartbeat returns OK. |
| **Immediate action** | Executor stops. Per ADR §6.1, a valid capability **cannot be used while the Brain is available**. The executor requests a new lease. |
| **Recovery action** | Brain issues a new lease; prior capability is superseded by a new one (Invariant 3a). |
| **Final state** | `EXPIRED → RENEWED` or `FAILED`. |
| **Data integrity guarantee** | No continuation effects produced. Capability authority is not exercisable against a healthy Brain. |
| **Audit requirement** | Lease expiry event; capability supersession event (C2 → C12). |
| **Components** | C1, C2, C3, C12 |
| **Invariants** | 2, 3, 3a, 4 |

### FM-LED-4 — Lease expired, capability valid, Brain outage declared, eligibility met

| Field | Value |
|---|---|
| **Trigger condition** | Lease expired; capability within validity window; Brain outage declared (two independent signals incl. one direct-Brain signal, ADR §2.2.2); all eligibility criteria in ADR §2.3 are satisfied. |
| **Detection mechanism** | C3/C4 outage signals cross thresholds; C2 capability validates; C5 self-check passes; C6 revocation watermark ≥ required; C14 time bounds satisfied. |
| **Immediate action** | Executor **may** continue (optional). If it continues, it opens a continuation journal (C8), performs permitted operations, and emits audit events per operation. |
| **Recovery action** | On Brain recovery, executor submits completion report (C9) within `completion_report_deadline`; C10 reconciles per ADR §2.6.3. |
| **Final state** | `CONTINUING → SUCCEEDED` / `FAILED` / `ABORTED` / `TIMEOUT`, then reconciled to `VALID_CONTINUATION` or `VALID_BUT_RECONCILED`. |
| **Data integrity guarantee** | Effects are tagged with stable identity `(root_command_id, operation_id, side_effect_slot)`; C13 deduplicates; receipt is signed and immutable (Invariant 6). |
| **Audit requirement** | Lease expiry event; capability issuance event; outage declaration event; eligibility decision event; per-operation events; completion event + receipt; recovery detection event; reconciliation event; terminal state event (ADR §2.13). |
| **Components** | C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C12, C13, C14 |
| **Invariants** | 2, 3, 4, 5, 6, 7, 10, 13, 14 |

### FM-LED-5 — Lease expired, capability valid, Brain outage declared, eligibility NOT met

| Field | Value |
|---|---|
| **Trigger condition** | Lease expired; capability within validity window; outage declared; at least one eligibility criterion in ADR §2.3 fails (e.g., revocation watermark stale, local state insufficient, policy snapshot expired, time bounds violated). |
| **Detection mechanism** | C5 self-check fails, or C6 watermark below required, or C7 snapshot expired, or C14 time bounds violated. |
| **Immediate action** | Executor stops and enters safe-hold state. Default decision is STOP (ADR §2.3). |
| **Recovery action** | Brain recovers; no continuation report is expected because no continuation occurred. Command may be replayed after recovery. |
| **Final state** | `EXPIRED → ABORTED`. |
| **Data integrity guarantee** | No continuation effects produced. |
| **Audit requirement** | Lease expiry event; eligibility-decision-failed event (which criterion failed) recorded by C12. |
| **Components** | C1, C2, C5, C6, C7, C12, C14 |
| **Invariants** | 4, 12, 13, 14 |

### FM-LED-6 — Lease expired, capability valid, Brain availability unknown

| Field | Value |
|---|---|
| **Trigger condition** | Lease expired; capability within validity window; Brain availability cannot be determined (insufficient signals, e.g., only one signal crossed threshold, or grace period not yet elapsed). |
| **Detection mechanism** | Outage detection logic cannot satisfy the two-signal rule (ADR §2.2.2); C3/C4 signals ambiguous. |
| **Immediate action** | Executor stops. Cannot declare outage → cannot satisfy eligibility → default STOP. |
| **Recovery action** | Await Brain recovery or fresh signals; Brain may replay after recovery. |
| **Final state** | `EXPIRED → ABORTED`. |
| **Data integrity guarantee** | No continuation effects produced. |
| **Audit requirement** | Lease expiry event; outage-detection-incomplete event (signals observed, thresholds not met) recorded by C12. |
| **Components** | C1, C2, C3, C4, C12 |
| **Invariants** | 4 |

### FM-LED-7 — Lease revoked (explicitly)

| Field | Value |
|---|---|
| **Trigger condition** | Brain explicitly revokes the lease before `expires_at` (e.g., operator-initiated, policy change). |
| **Detection mechanism** | C6 revocation stream publishes a lease-revocation entry; executor observes it at or above the required watermark. |
| **Immediate action** | Executor stops immediately. All downstream systems reject effects under the revoked lease token (Invariant 1). |
| **Recovery action** | Brain may issue a new lease for a fresh attempt; original command is not replayed automatically. |
| **Final state** | `REVOKED → FAILED`. |
| **Data integrity guarantee** | No effects produced after revocation. Any pre-revocation committed effects remain; downstream deduplication prevents re-application. |
| **Audit requirement** | Lease revocation event (C1/C6 → C12); command terminal state event. |
| **Components** | C1, C6, C12, C13 |
| **Invariants** | 1, 13 |

### FM-LED-8 — Command cancelled

| Field | Value |
|---|---|
| **Trigger condition** | A cancellation command for this `command_id` is observed in the revocation stream at or before the executor's revocation watermark. |
| **Detection mechanism** | C6 revocation stream carries a cancellation entry; executor's cached ledger events include the cancellation. |
| **Immediate action** | Executor stops. Continuation is forbidden (ADR §2.10, §2.3 "No cancellation confirmed"). |
| **Recovery action** | No replay; cancellation is terminal. |
| **Final state** | `CANCELLED`. |
| **Data integrity guarantee** | No continuation effects produced. |
| **Audit requirement** | Cancellation event (C6 → C12); command terminal state event. |
| **Components** | C6, C12 |
| **Invariants** | 13 |

---

## 3. Continuation Outcome Matrix (ADR §6.2)

These failure modes correspond row-for-row to ADR §6.2. They describe what happens to a continuation that **did occur**, at reconciliation time.

### FM-CO-1 — Success, single executor, no conflict

| Field | Value |
|---|---|
| **Trigger condition** | One continuation report received for `command_id`; receipt valid; no conflicting reports; effects idempotent and unique. |
| **Detection mechanism** | C10 `submit_report` accepts the report; `detect_conflicts` finds no other reports and no effect-identity conflicts. |
| **Immediate action** | C10 selects the result as authoritative. |
| **Recovery action** | C10 applies authoritative effects by stable identity via C13; compensation issued if any reversible effect needs correction. |
| **Final state** | `SUCCEEDED`; classification `VALID_CONTINUATION`. |
| **Data integrity guarantee** | Effects applied exactly once by `(root_command_id, operation_id, side_effect_slot)`; receipt immutable (Invariant 6); audit chain complete (Invariant 11). |
| **Audit requirement** | Completion event + receipt; reconciliation event; terminal state event. |
| **Components** | C9, C10, C12, C13 |
| **Invariants** | 6, 7, 10, 11 |

### FM-CO-2 — Success, but Brain expected a different outcome

| Field | Value |
|---|---|
| **Trigger condition** | Single valid continuation report; result diverges from what the Brain expected (e.g., partial work, different branch taken). |
| **Detection mechanism** | C10 result selection compares `result_digest` against Brain-expected outcome; mismatch detected. |
| **Immediate action** | C10 routes to effect reconciliation per ADR §2.6.3.2. |
| **Recovery action** | Reconcile/apply per effect rules; compensation if reversible; manual review if non-reversible. |
| **Final state** | `RECONCILED → SUCCEEDED` or `MANUAL_REVIEW_REQUIRED`. Classification `VALID_BUT_RECONCILED`. |
| **Data integrity guarantee** | Effect identity deduplication preserved; no silent overwrite; conflicting effects frozen pending resolution. |
| **Audit requirement** | Reconciliation event with divergence record; compensation event if issued; manual-review enqueue event if applicable. |
| **Components** | C9, C10, C11, C12, C13 |
| **Invariants** | 7, 8, 10 |

### FM-CO-3 — Success, multiple executors agree, effects idempotent

| Field | Value |
|---|---|
| **Trigger condition** | Two or more continuation reports for the same `command_id` with agreeing `result_digest` and idempotent effects. |
| **Detection mechanism** | C10 `detect_conflicts` finds multiple reports with matching digests; C13 confirms effects are idempotent. |
| **Immediate action** | C10 selects the first completed by trusted comparable signed time (ADR §2.6.3.1); deterministic tie-breaker: lowest `executor_id` wins. Others marked `DUPLICATE_AGREED`. |
| **Recovery action** | C13 deduplicates by stable effect identity; no re-application. |
| **Final state** | `SUCCEEDED`; classification `VALID_CONTINUATION` (with `DUPLICATE_AGREED` on the others). |
| **Data integrity guarantee** | Each external effect applied exactly once; duplicate reports recorded but not re-applied (Invariant 10). |
| **Audit requirement** | All reports recorded; `DUPLICATE_AGREED` markers; reconciliation event; terminal state event. |
| **Components** | C9, C10, C12, C13 |
| **Invariants** | 6, 7, 10, 11 |

### FM-CO-4 — Success, multiple executors agree, effects non-reversible

| Field | Value |
|---|---|
| **Trigger condition** | Multiple continuation reports with agreeing results but the effects are non-reversible (e.g., Class 2 non-idempotent or any Class 3 attempt). |
| **Detection mechanism** | C10 detects multiple reports; C13 classifies effects as non-reversible. |
| **Immediate action** | C10 selects first completed by trusted signed time (tie-breaker: lowest `executor_id`); marks others `DUPLICATE_AGREED`; **freezes** affected downstream effects. |
| **Recovery action** | Route to manual review (C11). No automatic compensation for non-reversible effects. |
| **Final state** | `MANUAL_REVIEW_REQUIRED`; classification `VALID_BUT_RECONCILED`. |
| **Data integrity guarantee** | Frozen effects are not modified pending operator decision; all reports and evidence surfaced. |
| **Audit requirement** | Freeze event; manual-review enqueue event; all reports and journals surfaced. |
| **Components** | C9, C10, C11, C12, C13 |
| **Invariants** | 7, 8, 10 |

### FM-CO-5 — Success, multiple executors, results conflict

| Field | Value |
|---|---|
| **Trigger condition** | Multiple continuation reports with divergent `result_digest` values or conflicting `(command_id, operation_id, side_effect_slot)` claims. |
| **Detection mechanism** | C10 `detect_conflicts` finds divergent digests or conflicting effect identities. |
| **Immediate action** | No automatic selection. C10 freezes all affected downstream effects. |
| **Recovery action** | Route to manual review (C11). Operator resolves with full evidence. |
| **Final state** | `MANUAL_REVIEW_REQUIRED`; classification `CONFLICTING_REPORTS`. |
| **Data integrity guarantee** | No silent conflict resolution (Invariant 8); frozen effects; all journals and receipts preserved for review. |
| **Audit requirement** | Conflict record; freeze event; manual-review enqueue event; all continuation journals and receipts surfaced. |
| **Components** | C9, C10, C11, C12, C13 |
| **Invariants** | 7, 8, 10, 11 |

### FM-CO-6 — Failure during continuation

| Field | Value |
|---|---|
| **Trigger condition** | Continuation was attempted but the operation(s) failed (e.g., downstream error, exception, timeout within bounds). |
| **Detection mechanism** | C8 journal records failure status; C9 receipt carries `final_state = FAILED`. |
| **Immediate action** | Executor records failure in journal; generates receipt; submits report on recovery. |
| **Recovery action** | C10 reconciles: if the failure left reversible/idempotent effects, compensation may be authorized; otherwise manual review. |
| **Final state** | `FAILED` or `RECONCILED`; classification `VALID_CONTINUATION` (if eligible) or `INVALID_CONTINUATION` (if not). |
| **Data integrity guarantee** | Failure is recorded; no further effects after failure; partial effects, if any, are surfaced for reconciliation. |
| **Audit requirement** | Per-operation failure events; completion event + receipt; reconciliation event. |
| **Components** | C8, C9, C10, C11, C12, C13 |
| **Invariants** | 6, 7, 10 |

### FM-CO-7 — Continuation without eligibility

| Field | Value |
|---|---|
| **Trigger condition** | Executor continued despite failing one or more eligibility criteria (ADR §2.3) — e.g., revoked capability, stale watermark, no outage declared. |
| **Detection mechanism** | C10 validates the submitted outage evidence, capability, and watermark at reconciliation; mismatch detected. |
| **Immediate action** | C10 discards the result; executor may be flagged. Any downstream effects produced are frozen. |
| **Recovery action** | Route to manual review (C11); security event raised (potential authority overreach). |
| **Final state** | `INVALID → REVIEW`; classification `INVALID_CONTINUATION`. |
| **Data integrity guarantee** | Effects produced by the invalid continuation are frozen and surfaced; not silently applied. |
| **Audit requirement** | Invalid-continuation record; security event; manual-review enqueue event; executor flag. |
| **Components** | C2, C6, C9, C10, C11, C12, C13 |
| **Invariants** | 2, 3, 4, 8, 13 |

### FM-CO-8 — No receipt produced

| Field | Value |
|---|---|
| **Trigger condition** | A continuation is believed to have occurred (e.g., downstream effects observed) but no completion receipt was submitted by `completion_report_deadline`. |
| **Detection mechanism** | C10 report collection misses the report; C13 observes effects with no matching receipt. |
| **Immediate action** | C10 marks the continuation `INVALID_CONTINUATION`; freezes downstream effects. |
| **Recovery action** | Route to manual review (C11); investigate executor; silent continuation is forbidden (ADR §2.6.2). |
| **Final state** | `INVALID → REVIEW`; classification `INVALID_CONTINUATION`. |
| **Data integrity guarantee** | Effects frozen pending investigation; no silent acceptance. |
| **Audit requirement** | Missing-receipt event; freeze event; manual-review enqueue event; security event. |
| **Components** | C9, C10, C11, C12, C13 |
| **Invariants** | 6, 8 |

### FM-CO-9 — Class 3 side effect attempted during continuation

| Field | Value |
|---|---|
| **Trigger condition** | Executor attempted an irreversible/destructive/financial/legal (Class 3) side effect during continuation. |
| **Detection mechanism** | C13 detects Class 3 effect attempt (capability `continuation_class` does not permit Class 3); C8 journal records the attempt. |
| **Immediate action** | C13 refuses the effect; freeze; security event raised. |
| **Recovery action** | Route to manual review (C11); executor flagged; any partial Class 3 effect investigated. |
| **Final state** | `INVALID → REVIEW`; classification `INVALID_CONTINUATION`. |
| **Data integrity guarantee** | Class 3 effects are prohibited during continuation (Invariant 15); any leaked effect is frozen and surfaced. |
| **Audit requirement** | Class 3 attempt event; security event; freeze event; manual-review enqueue event. |
| **Components** | C2, C8, C9, C10, C11, C12, C13 |
| **Invariants** | 8, 15 |

---

## 4. Split-Brain Scenarios (ADR §2.12)

These failure modes cover the split-brain resolution matrix in ADR §2.12.2, plus the related recovery-while-active and never-recovers cases.

### FM-SB-1 — Multiple executors continued, results agree, effects idempotent

| Field | Value |
|---|---|
| **Trigger condition** | Two or more executors independently continued the same `command_id` (different `continuation_id`); results agree; effects are idempotent. |
| **Detection mechanism** | C10 receives multiple reports; `result_digest` values match; C13 confirms idempotent effect class. |
| **Immediate action** | C10 selects first completed by trusted comparable signed time; tie-breaker lowest `executor_id`; others marked `DUPLICATE_AGREED`. |
| **Recovery action** | C13 deduplicates by stable effect identity; no re-application. |
| **Final state** | `SUCCEEDED`. |
| **Data integrity guarantee** | Effects applied once; duplicate reports recorded; no silent resolution. |
| **Audit requirement** | All reports; `DUPLICATE_AGREED` markers; reconciliation event. |
| **Components** | C9, C10, C12, C13 |
| **Invariants** | 6, 7, 10, 11 |

### FM-SB-2 — Multiple executors continued, results agree, effects non-reversible

| Field | Value |
|---|---|
| **Trigger condition** | Multiple executors continued; results agree; effects are non-reversible. |
| **Detection mechanism** | C10 detects multiple reports with matching digests; C13 classifies effects as non-reversible. |
| **Immediate action** | C10 selects first by trusted signed time (tie-breaker lowest `executor_id`); others `DUPLICATE_AGREED`; **freeze** effects. |
| **Recovery action** | Manual review (C11); no automatic compensation for non-reversible effects. |
| **Final state** | `MANUAL_REVIEW_REQUIRED`. |
| **Data integrity guarantee** | Frozen effects; all evidence surfaced; no silent resolution. |
| **Audit requirement** | Freeze event; manual-review enqueue event; all reports and journals. |
| **Components** | C9, C10, C11, C12, C13 |
| **Invariants** | 7, 8, 10 |

### FM-SB-3 — Multiple executors continued, results conflict

| Field | Value |
|---|---|
| **Trigger condition** | Multiple executors continued; `result_digest` values diverge or effect identities conflict. |
| **Detection mechanism** | C10 `detect_conflicts` finds divergent digests or conflicting `(command_id, operation_id, side_effect_slot)` claims. |
| **Immediate action** | No automatic selection; C10 freezes all affected downstream effects. |
| **Recovery action** | Manual review (C11); operator resolves with full evidence. |
| **Final state** | `MANUAL_REVIEW_REQUIRED`. |
| **Data integrity guarantee** | No silent conflict resolution (Invariant 8); frozen effects; all journals and receipts preserved. |
| **Audit requirement** | Conflict record; freeze event; manual-review enqueue event; all journals and receipts. |
| **Components** | C9, C10, C11, C12, C13 |
| **Invariants** | 7, 8, 10, 11 |

### FM-SB-4 — Brain recovers while continuation active (operation atomicity)

| Field | Value |
|---|---|
| **Trigger condition** | Brain becomes available (recovery detected per ADR §2.6.1) while one or more executors have active continuations. |
| **Detection mechanism** | C3 heartbeat returns OK for `brain_recovery_confirmation_period`; recovery declared and signed (C14). |
| **Immediate action** | Stop active continuations. For each in-progress operation, apply the **operation atomicity rule (ADR §2.12.2)**: committed/irreversible → finish and report; uncommitted → abort. Never both for the same operation. |
| **Recovery action** | Report completed operations; abort uncommitted operations; flag partial state for reconciliation; C10 reconciles per ADR §2.6.3. |
| **Final state** | `RECONCILING` → (per outcome) `VALID_CONTINUATION` / `VALID_BUT_RECONCILED` / `MANUAL_REVIEW_REQUIRED`. |
| **Data integrity guarantee** | No operation is both finished and aborted; per-operation determination recorded in C8 journal and C9 report; effects respect stable identity deduplication. |
| **Audit requirement** | Recovery detection event; per-operation atomicity determination (finish/abort); completion report; reconciliation event. |
| **Components** | C3, C8, C9, C10, C11, C12, C13, C14 |
| **Invariants** | 5, 6, 7, 10, 14 |

### FM-SB-5 — Brain never recovers within capability window

| Field | Value |
|---|---|
| **Trigger condition** | Brain remains unavailable past the capability `not_valid_after` (and `policy_snapshot_not_valid_after` if set). |
| **Detection mechanism** | C14 time-anchor check shows current signed time ≥ `not_valid_after`; C2 capability validation fails. |
| **Immediate action** | Executor must stop at `not_valid_after` (ADR §2.12.2). No further operations. |
| **Recovery action** | Partial results recorded in C8 journal and C9 receipt (if receipt could be generated); manual recovery process initiated. |
| **Final state** | `MANUAL_REVIEW_REQUIRED`. |
| **Data integrity guarantee** | No effects produced past `not_valid_after`; partial effects, if any, surfaced for manual reconciliation. |
| **Audit requirement** | Capability-expiry stop event; partial-results record; manual-review enqueue event. |
| **Components** | C2, C8, C9, C10, C11, C12, C14 |
| **Invariants** | 3, 5, 7, 14 |

---

## 5. Threat-Model Failure Modes (ADR §6.3)

These failure modes correspond to the threats enumerated in ADR §6.3. They are adversarial or low-likelihood operational conditions, each with a mitigation already mandated by the ADR. The matrix below restates each threat as a concrete failure mode with detection and recovery actions.

### FM-TM-1 — Executor continues without a capability

| Field | Value |
|---|---|
| **Trigger condition** | Executor attempts continuation effects without a valid signed continuation capability (e.g., only an expired lease). |
| **Detection mechanism** | C13 downstream effect identity layer requires a valid signed capability + outage evidence; absence → reject. C10 reconciliation detects missing capability in report. |
| **Immediate action** | Downstream systems (C13) reject the effects; security event raised. |
| **Recovery action** | Route to manual review (C11); executor flagged; effects frozen. |
| **Final state** | `INVALID → REVIEW`. |
| **Data integrity guarantee** | No unauthorized effects applied; capability unusable before lease expiry (Invariant 3). |
| **Audit requirement** | Unauthorized-continuation event; security event; rejection records. |
| **Components** | C2, C9, C10, C11, C12, C13 |
| **Invariants** | 2, 3, 8 |

### FM-TM-2 — Executor continues without a real Brain outage

| Field | Value |
|---|---|
| **Trigger condition** | Executor declares an outage and continues despite the Brain being healthy (e.g., false-positive signals, single transient failure). |
| **Detection mechanism** | Two-signal rule (ADR §2.2.2) requires at least two independent signals incl. one direct-Brain signal; grace period must elapse. C10 validates outage evidence at reconciliation against Brain's actual availability logs. |
| **Immediate action** | If detection prevents it: continuation blocked. If it occurs anyway: C10 detects invalid outage evidence at reconciliation. |
| **Recovery action** | Route to manual review (C11); executor flagged; effects frozen. |
| **Final state** | `INVALID → REVIEW`. |
| **Data integrity guarantee** | Outage evidence is replay-resistant and bound to capability; false outages detected at reconciliation. |
| **Audit requirement** | Outage declaration event with signals; reconciliation invalid-outage event; security event. |
| **Components** | C3, C4, C9, C10, C11, C12 |
| **Invariants** | 4, 8 |

### FM-TM-3 — Executor continues without local state sufficiency

| Field | Value |
|---|---|
| **Trigger condition** | Executor attempts continuation but lacks required inputs or a deterministic path (C5 self-check would fail). |
| **Detection mechanism** | C5 `check_sufficiency` returns false; eligibility gate blocks continuation. |
| **Immediate action** | Executor stops (default STOP). |
| **Recovery action** | Brain may re-dispatch or replay after recovery. |
| **Final state** | `EXPIRED → ABORTED`. |
| **Data integrity guarantee** | No continuation effects produced. |
| **Audit requirement** | Eligibility-decision-failed event (state insufficiency). |
| **Components** | C5, C12 |
| **Invariants** | 4 |

### FM-TM-4 — Multiple executors continue the same command (split-brain)

| Field | Value |
|---|---|
| **Trigger condition** | More than one executor independently continues the same `command_id` (lease exclusivity violated or multiple capabilities issued). |
| **Detection mechanism** | C10 receives multiple reports with different `continuation_id`; C13 detects conflicting effect identity claims. |
| **Immediate action** | C10 conflict detection; freeze affected downstream effects. |
| **Recovery action** | Result selection + effect reconciliation per ADR §2.12.2 (see FM-SB-1 through FM-SB-3); manual review for conflicts. |
| **Final state** | `SUCCEEDED` (if agree + idempotent) or `MANUAL_REVIEW_REQUIRED`. |
| **Data integrity guarantee** | Stable effect identity deduplication; no silent conflict resolution. |
| **Audit requirement** | All reports; conflict record; freeze events; reconciliation event. |
| **Components** | C1, C2, C9, C10, C11, C12, C13 |
| **Invariants** | 7, 8, 10 |

### FM-TM-5 — Executor produces duplicate external effects

| Field | Value |
|---|---|
| **Trigger condition** | Executor (or replay) attempts to apply an effect whose `(root_command_id, operation_id, side_effect_slot)` already exists. |
| **Detection mechanism** | C13 `check_effect` finds existing effect by stable identity; rejects duplicate. |
| **Immediate action** | C13 refuses the duplicate effect. |
| **Recovery action** | No re-application; deduplication recorded. |
| **Final state** | Effect applied once; duplicate rejected. |
| **Data integrity guarantee** | Idempotency preserved across continuation, replay, and normal execution (Invariant 10). |
| **Audit requirement** | Duplicate-rejection event with stable identity. |
| **Components** | C8, C9, C12, C13 |
| **Invariants** | 10 |

### FM-TM-6 — Executor lies about continuation outcome

| Field | Value |
|---|---|
| **Trigger condition** | Executor submits a receipt with a falsified `result_digest` or omits operations from the journal. |
| **Detection mechanism** | C9 receipt signature verification; C10 cross-checks receipt against C8 journal hash chain and C13 effect records; C12 audit chain reveals gaps. |
| **Immediate action** | C10 flags the report; freeze effects; security event. |
| **Recovery action** | Manual review (C11); executor flagged; evidence surfaced. |
| **Final state** | `INVALID → REVIEW`. |
| **Data integrity guarantee** | Signed receipts and hash-chained journals make tampering detectable; authoritative audit storage never truncated (Invariant 11). |
| **Audit requirement** | Tamper-detection event; security event; manual-review enqueue event. |
| **Components** | C8, C9, C10, C11, C12, C13 |
| **Invariants** | 6, 8, 11 |

### FM-TM-7 — Brain recovers during continuation

| Field | Value |
|---|---|
| **Trigger condition** | Brain becomes available while executors are still performing continuation operations. |
| **Detection mechanism** | C3 heartbeat returns OK for `brain_recovery_confirmation_period`; recovery declared (C14). |
| **Immediate action** | Stop active continuations; apply operation atomicity rule (ADR §2.12.2) — see FM-SB-4. |
| **Recovery action** | Report completed ops; abort uncommitted ops; reconcile. |
| **Final state** | `RECONCILING` → terminal classification. |
| **Data integrity guarantee** | No operation both finished and aborted; per-operation determination recorded. |
| **Audit requirement** | Recovery detection event; per-operation atomicity determination; reconciliation event. |
| **Components** | C3, C8, C9, C10, C12, C13, C14 |
| **Invariants** | 5, 6, 7, 10, 14 |

### FM-TM-8 — Cross-tenant continuation

| Field | Value |
|---|---|
| **Trigger condition** | Executor attempts to continue a command outside its tenant scope, or a capability/revocation/witness statement is presented for the wrong tenant. |
| **Detection mechanism** | Every component validates `tenant_id` at its boundary (ADR §2.14); C2, C6, C13 reject tenant mismatch. |
| **Immediate action** | Reject; security event raised. |
| **Recovery action** | Manual review (C11); executor investigated. |
| **Final state** | `INVALID → REVIEW`; security event. |
| **Data integrity guarantee** | Cross-tenant continuation is impossible (Invariant 9); no cross-tenant effects applied. |
| **Audit requirement** | Cross-tenant-attempt event; security event. |
| **Components** | C1, C2, C3, C4, C6, C7, C10, C11, C12, C13 |
| **Invariants** | 9 |

### FM-TM-9 — Continuation runs unbounded

| Field | Value |
|---|---|
| **Trigger condition** | Executor continues past `max_continuation_duration` or `max_continuation_operations` or `not_valid_after`. |
| **Detection mechanism** | C14 monotonic time bounds; C2 capability validity checks; C8 operation count. |
| **Immediate action** | Executor must stop at the bound; further operations rejected by C13. |
| **Recovery action** | Any effects past the bound are invalid; manual review. |
| **Final state** | `INVALID → REVIEW` if bounds exceeded; otherwise `ABORTED` at the bound. |
| **Data integrity guarantee** | Bounds enforced by monotonic clock (Invariant 5); effects past bounds rejected. |
| **Audit requirement** | Bound-violation event; security event if exceeded. |
| **Components** | C2, C8, C9, C10, C11, C12, C13, C14 |
| **Invariants** | 3, 5, 14 |

### FM-TM-10 — Stale revocation/cancellation knowledge

| Field | Value |
|---|---|
| **Trigger condition** | Executor's revocation cache is older than `max_revocation_cache_age` at lease expiry, or watermark below `revocation_watermark_required`. |
| **Detection mechanism** | C6 `cache_age` exceeds limit; C2 capability validation checks watermark. |
| **Immediate action** | Fail-closed: continuation not permitted (ADR §2.10). |
| **Recovery action** | Executor stops; Brain may replay after recovery. |
| **Final state** | `EXPIRED → ABORTED`. |
| **Data integrity guarantee** | Absence of evidence is not permission (Invariant 13); no continuation on stale revocation data. |
| **Audit requirement** | Stale-watermark event; fail-closed decision event. |
| **Components** | C2, C6, C12 |
| **Invariants** | 13 |

### FM-TM-11 — Pinned policy exploited

| Field | Value |
|---|---|
| **Trigger condition** | Attempt to use a pinned policy snapshot to authorize side-effect classes or operations not explicitly permitted by the capability, or to continue past `policy_snapshot_not_valid_after`. |
| **Detection mechanism** | C2 capability validation enforces `policy_snapshot_hash` and `policy_snapshot_not_valid_after`; C13 enforces permitted operation IDs. |
| **Immediate action** | Reject the operation; stop continuation if snapshot expired. |
| **Recovery action** | Manual review if any unauthorized effect leaked. |
| **Final state** | `INVALID → REVIEW` or `ABORTED`. |
| **Data integrity guarantee** | Pinned snapshot cannot authorize beyond capability (Invariant 12); emergency deny channel survives. |
| **Audit requirement** | Policy-snapshot-exploitation event; emergency deny observations. |
| **Components** | C2, C7, C12, C13 |
| **Invariants** | 12 |

### FM-TM-12 — Clock skew/rollback extends authority

| Field | Value |
|---|---|
| **Trigger condition** | Executor wall-clock drifts beyond `max_clock_skew_tolerance` or a signed timestamp rolls backward beyond `max_clock_rollback_tolerance`. |
| **Detection mechanism** | C14 `check_skew` and `check_rollback`; C2 capability validity evaluated against signed Brain anchors, not executor wall-clock alone. |
| **Immediate action** | Executor must STOP (ADR §2.8); continuation not permitted under disputed time. |
| **Recovery action** | Await fresh signed anchor; operator intervention for large rollbacks. |
| **Final state** | `EXPIRED → ABORTED`. |
| **Data integrity guarantee** | Time cannot be manipulated to extend authority (Invariant 14); monotonic time bounds prevent extension. |
| **Audit requirement** | Skew/rollback security event; stop decision event. |
| **Components** | C2, C12, C14 |
| **Invariants** | 14 |

### FM-TM-13 — Silent continuation (no report)

| Field | Value |
|---|---|
| **Trigger condition** | Executor continued but did not submit a completion report by `completion_report_deadline`. |
| **Detection mechanism** | C10 report collection misses the report; C13 observes unexplained effects. |
| **Immediate action** | C10 marks `INVALID_CONTINUATION`; freeze effects. |
| **Recovery action** | Manual review (C11); security event; silent continuation is forbidden (ADR §2.6.2). |
| **Final state** | `INVALID → REVIEW`. |
| **Data integrity guarantee** | Effects frozen; no silent acceptance. |
| **Audit requirement** | Missing-report event; security event; manual-review enqueue event. |
| **Components** | C9, C10, C11, C12, C13 |
| **Invariants** | 6, 8 |

### FM-TM-14 — Witness quorum compromised

| Field | Value |
|---|---|
| **Trigger condition** | A threshold of witness keys is compromised or revoked such that a valid quorum cannot be formed, or faulty witnesses attempt to declare a false outage. |
| **Detection mechanism** | C4 `validate_statement` rejects revoked-key statements; BFT quorum (`N ≥ 3f+1`, `quorum ≥ 2f+1`) ensures a quorum cannot be formed by faulty witnesses alone; self-exclusion rule. |
| **Immediate action** | If witnesses were the only non-direct signal, outage cannot be declared (witness statements alone are never sufficient — ADR §2.2.2). Continuation blocked. |
| **Recovery action** | Revoke compromised witness keys (C4); restore quorum; investigate. |
| **Final state** | `EXPIRED → ABORTED` (continuation blocked) or `INVALID → REVIEW` (if a false outage was declared). |
| **Data integrity guarantee** | Witness statements are signed, replay-resistant, and self-exclusion-enforced; compromised keys revoked. |
| **Audit requirement** | Witness key revocation events; quorum-failure event; security event. |
| **Components** | C4, C9, C10, C11, C12 |
| **Invariants** | 4, 8 |

---

## 6. Implementation-Level Failure Modes

These failure modes are surfaced by the 14-component architecture in `01_IMPLEMENTATION_ARCHITECTURE.md`. They are not explicitly enumerated in ADR §6 but are implied by the component interactions, trust boundaries, and shared dependencies. Each is mapped to the components and invariants it affects.

### FM-IMPL-1 — Component crash (executor process)

| Field | Value |
|---|---|
| **Trigger condition** | Executor process crashes (OOM, segfault, operator kill) during normal execution or continuation. |
| **Detection mechanism** | C3 heartbeat from executor stops; Brain marks executor unresponsive; on restart, C5 local state cache and C8 journal are inspected. |
| **Immediate action** | If during normal execution: lease eventually expires (FM-LED-*). If during continuation: C8 journal records last committed operation; uncommitted operations are lost. |
| **Recovery action** | On Brain recovery, C10 reconciles based on the sealed (or partially sealed) C8 journal and any C9 receipt already generated. If no receipt, FM-CO-8 / FM-TM-13 path. |
| **Final state** | `ABORTED` or `RECONCILING → terminal classification`. |
| **Data integrity guarantee** | C8 journal is append-only and hash-chained; committed operations are recoverable from the journal; uncommitted operations have no external effect (C13 validates before applying). |
| **Audit requirement** | Executor-crash event; journal recovery event; reconciliation event. |
| **Components** | C3, C5, C8, C9, C10, C12, C13 |
| **Invariants** | 6, 7, 10, 11 |

### FM-IMPL-2 — Component crash (Brain process)

| Field | Value |
|---|---|
| **Trigger condition** | Brain process crashes or restarts. |
| **Detection mechanism** | C3 heartbeat endpoint unavailable; C4 witnesses observe Brain unavailability; executors' outage detection signals cross thresholds. |
| **Immediate action** | Executors with active leases enter outage detection. Executors with active continuations apply operation atomicity rule on Brain recovery (FM-SB-4). |
| **Recovery action** | Brain restarts; recovery detected after `brain_recovery_confirmation_period` (ADR §2.6.1); C10 collects reports and reconciles. |
| **Final state** | `RECONCILING → terminal classification`. |
| **Data integrity guarantee** | C12 audit ledger is durable and never truncated (Invariant 11); C6 revocation stream is monotonic; C2 capability state recoverable from audit chain. |
| **Audit requirement** | Brain-unavailability event(s); recovery detection event; reconciliation events. |
| **Components** | C1, C2, C3, C4, C6, C10, C12, C14 |
| **Invariants** | 7, 11, 13, 14 |

### FM-IMPL-3 — Network partition (executor ↔ Brain)

| Field | Value |
|---|---|
| **Trigger condition** | Network isolates executor from Brain but executor can still reach witnesses and/or downstream systems. |
| **Detection mechanism** | C3 heartbeat misses; C1 lease renewal rejections; C4 witnesses may still be reachable. Two-signal rule (ADR §2.2.2) — a partition alone does not grant continuation authority; a direct-Brain signal is still required. |
| **Immediate action** | If two signals (incl. direct-Brain) cross thresholds and grace period elapses: outage declared; eligibility evaluated. If only witnesses reachable (no direct-Brain signal): no outage → STOP. |
| **Recovery action** | On partition heal, Brain recovery detected; C10 reconciles any continuations that occurred. |
| **Final state** | `CONTINUING → reconciled` or `EXPIRED → ABORTED`. |
| **Data integrity guarantee** | Partition alone does not bootstrap authority (ADR §2.2.4); effects, if any, tagged with stable identity and deduplicated by C13. |
| **Audit requirement** | Outage declaration event with signals; partition-heal event; reconciliation event. |
| **Components** | C3, C4, C6, C10, C12, C13 |
| **Invariants** | 4, 10, 13 |

### FM-IMPL-4 — Network partition (executor ↔ witnesses)

| Field | Value |
|---|---|
| **Trigger condition** | Executor can reach Brain (or detect Brain via direct signals) but cannot reach witnesses. |
| **Detection mechanism** | C4 witness statements unavailable; C4 `collect_quorum` fails. |
| **Immediate action** | If direct-Brain signals (C3 heartbeat/lease/status) cross thresholds, outage can still be declared without witnesses (witnesses are supplementary). If only witness signal is missing and direct signals are OK, no outage → normal operation. |
| **Recovery action** | On partition heal, witness statements resume; no special reconciliation needed unless a continuation occurred on direct signals alone (which is permitted). |
| **Final state** | Normal operation or `CONTINUING → reconciled`. |
| **Data integrity guarantee** | Witness statements alone are never sufficient (ADR §2.2.2); their absence does not block outage if direct signals cross. |
| **Audit requirement** | Witness-unavailability event; outage declaration (if any) with signals listed. |
| **Components** | C3, C4, C12 |
| **Invariants** | 4 |

### FM-IMPL-5 — Database failure (audit ledger / C12 backing store)

| Field | Value |
|---|---|
| **Trigger condition** | The durable store backing C12 (immutable audit ledger) becomes unavailable or corrupts. |
| **Detection mechanism** | C12 `append` fails or returns corruption; hash-chain verification fails on read. |
| **Immediate action** | All components that depend on C12 for audit emission cannot record state transitions. Authority-issuing components (C1, C2, C6) must fail-closed: no new leases, capabilities, or revocation entries without audit. Executors must STOP (no audit capability → eligibility criterion "Audit capability" fails, ADR §2.3). |
| **Recovery action** | Restore C12 from durable replica/backup; verify hash-chain integrity; replay any buffered events; reconcile any in-flight continuations. |
| **Final state** | System paused until C12 restored; then `RECONCILING → terminal classification`. |
| **Data integrity guarantee** | Authoritative audit storage is never truncated (Invariant 11); if corruption is detected, the system halts rather than accept an incomplete chain. |
| **Audit requirement** | C12-corruption event (recorded in an out-of-band operator log if C12 itself is down); recovery event; integrity-verification event. |
| **Components** | C1, C2, C6, C8, C9, C10, C12 |
| **Invariants** | 6, 7, 11 |

### FM-IMPL-6 — Database failure (revocation stream / C6 backing store)

| Field | Value |
|---|---|
| **Trigger condition** | The store backing C6 revocation stream is unavailable or loses entries. |
| **Detection mechanism** | C6 `read` fails; `latest_watermark` regresses or is unavailable; `cache_age` exceeds `max_revocation_cache_age`. |
| **Immediate action** | Executors fail-closed (ADR §2.10): no continuation on stale/missing revocation. C2 capability validation fails (watermark requirement cannot be met). |
| **Recovery action** | Restore C6 from durable replica; rebuild watermark; executors refresh before accepting new work (ADR §2.15 step 8). |
| **Final state** | `EXPIRED → ABORTED` for in-flight commands; system resumes after C6 restored. |
| **Data integrity guarantee** | Absence of evidence is not permission (Invariant 13); fail-closed prevents continuation on stale revocation. |
| **Audit requirement** | C6-unavailability event; fail-closed decisions; recovery event. |
| **Components** | C2, C6, C12 |
| **Invariants** | 13 |

### FM-IMPL-7 — Clock drift (executor monotonic or wall-clock)

| Field | Value |
|---|---|
| **Trigger condition** | Executor wall-clock drifts beyond `max_clock_skew_tolerance` relative to signed Brain anchors, or monotonic clock loses continuity (process restart, suspend/resume). |
| **Detection mechanism** | C14 `check_skew` detects drift; monotonic discontinuity detected on process restart. |
| **Immediate action** | Executor must STOP (ADR §2.8): "If the monotonic clock loses continuity or wall-clock drift exceeds tolerance, the executor must STOP." Continuation not permitted under disputed time. |
| **Recovery action** | Await fresh signed anchor (C14); operator intervention for large rollbacks. |
| **Final state** | `EXPIRED → ABORTED`. |
| **Data integrity guarantee** | Time cannot be manipulated to extend authority (Invariant 14); monotonic bounds prevent duration extension. |
| **Audit requirement** | Clock-drift/rollback security event; stop decision event. |
| **Components** | C2, C12, C14 |
| **Invariants** | 14 |

### FM-IMPL-8 — Key compromise (Brain signing key)

| Field | Value |
|---|---|
| **Trigger condition** | The Brain's private signing key (used for lease tokens, capabilities, time anchors, revocation entries) is compromised. |
| **Detection mechanism** | Out-of-band security detection; anomalous tokens observed; key revocation procedure initiated. |
| **Immediate action** | Revoke the compromised key; rotate to a new key pair; re-issue leases and capabilities under the new key. All tokens signed by the compromised key become untrusted. Executors must STOP until fresh signed anchors under the new key are received. |
| **Recovery action** | All in-flight continuations are invalid (their capabilities were signed by the compromised key); route to manual review (C11); re-dispatch commands under new authority. |
| **Final state** | `INVALID → REVIEW` for affected continuations; system resumes under new key. |
| **Data integrity guarantee** | Compromised-key tokens are rejected after rotation; no new effects honored under old key; affected effects frozen and reviewed. |
| **Audit requirement** | Key-compromise event; key-revocation event; key-rotation event; per-continuation invalidation events. |
| **Components** | C1, C2, C6, C10, C11, C12, C14 |
| **Invariants** | 1, 2, 3, 14 |

### FM-IMPL-9 — Key compromise (witness signing key)

| Field | Value |
|---|---|
| **Trigger condition** | A witness's private signing key is compromised. |
| **Detection mechanism** | Out-of-band detection; C4 `validate_statement` rejects statements from revoked keys. |
| **Immediate action** | Revoke the compromised witness key (C4 `revoke_witness_key`); its statements are invalid. If the remaining valid witnesses fall below quorum, witness signal is unavailable. |
| **Recovery action** | Onboard new witnesses to restore quorum; investigate any false outage declarations signed by the compromised key. |
| **Final state** | If quorum restored: normal operation. If a false outage was declared: affected continuations reviewed. |
| **Data integrity guarantee** | Revoked witness keys' statements are rejected; BFT quorum ensures a quorum of honest witnesses is needed (ADR §2.2.4). |
| **Audit requirement** | Witness-key revocation event; quorum-status event; investigation record. |
| **Components** | C4, C9, C10, C11, C12 |
| **Invariants** | 4, 8 |

### FM-IMPL-10 — Cache corruption (executor local state cache / C5)

| Field | Value |
|---|---|
| **Trigger condition** | C5 local state cache is corrupted (inputs, step outputs, or task manifest lost or altered). |
| **Detection mechanism** | C5 `check_sufficiency` fails; hash mismatch on cached step outputs; self-check against task manifest fails. |
| **Immediate action** | Executor stops (eligibility criterion "Local state sufficient" fails, ADR §2.3). |
| **Recovery action** | Brain re-dispatches or replays the command with fresh inputs after recovery. |
| **Final state** | `EXPIRED → ABORTED`. |
| **Data integrity guarantee** | No continuation on corrupted state; corrupted cache not used to produce effects. |
| **Audit requirement** | Cache-corruption event; eligibility-decision-failed event. |
| **Components** | C5, C12 |
| **Invariants** | 4 |

### FM-IMPL-11 — Cache corruption (revocation cache)

| Field | Value |
|---|---|
| **Trigger condition** | The executor's local revocation cache (derived from C6) is corrupted — missing entries, wrong watermark, or tampered sequence. |
| **Detection mechanism** | C6 `cache_age` exceeds `max_revocation_cache_age`; watermark verification against C6 stream fails; hash mismatch. |
| **Immediate action** | Fail-closed (ADR §2.10): continuation not permitted. |
| **Recovery action** | Re-fetch revocation stream from C6; rebuild watermark; resume normal operation. |
| **Final state** | `EXPIRED → ABORTED` for in-flight commands. |
| **Data integrity guarantee** | Stale/corrupt revocation data blocks continuation (Invariant 13). |
| **Audit requirement** | Cache-corruption event; fail-closed decision event. |
| **Components** | C2, C6, C12 |
| **Invariants** | 13 |

### FM-IMPL-12 — Journal loss (C8 continuation journal)

| Field | Value |
|---|---|
| **Trigger condition** | The continuation journal (C8) for a continuation is lost — e.g., executor disk failure before the journal is sealed and reported. |
| **Detection mechanism** | C10 receives a completion report (or detects effects) but the journal blob is missing or fails hash-chain verification; C9 receipt references a journal that cannot be produced. |
| **Immediate action** | C10 flags the continuation; freeze effects; security event. |
| **Recovery action** | Manual review (C11); reconstruct what is possible from C13 effect records and C12 audit events; the continuation cannot be classified as `VALID_CONTINUATION` without the journal. |
| **Final state** | `INVALID → REVIEW` or `MANUAL_REVIEW_REQUIRED`. |
| **Data integrity guarantee** | Without the journal, the continuation's per-operation record is incomplete; effects are frozen rather than silently accepted. |
| **Audit requirement** | Journal-loss event; security event; manual-review enqueue event. |
| **Components** | C8, C9, C10, C11, C12, C13 |
| **Invariants** | 6, 8, 11 |

### FM-IMPL-13 — Receipt forgery (C9)

| Field | Value |
|---|---|
| **Trigger condition** | A forged or tampered completion receipt is submitted to C10 (e.g., wrong signature, altered `result_digest`, mismatched `capability_id`). |
| **Detection mechanism** | C9 `verify_receipt` fails signature verification; C10 cross-checks receipt against C8 journal hash chain, C2 capability validity, C4 outage evidence, and C6 watermark. |
| **Immediate action** | C10 rejects the receipt; freeze effects; security event. |
| **Recovery action** | Manual review (C11); executor investigated; legitimate continuations reconciled from their own valid receipts. |
| **Final state** | `INVALID → REVIEW`. |
| **Data integrity guarantee** | Forged receipts are detectable via signature verification and cross-checks (Invariant 6); no effects applied on a forged receipt. |
| **Audit requirement** | Receipt-forgery event; security event; manual-review enqueue event. |
| **Components** | C2, C4, C6, C8, C9, C10, C11, C12 |
| **Invariants** | 6, 8, 11 |

### FM-IMPL-14 — Policy snapshot registry unavailable (C7)

| Field | Value |
|---|---|
| **Trigger condition** | C7 policy snapshot registry is unavailable; capabilities cannot reference or validate pinned snapshots. |
| **Detection mechanism** | C2 capability validation cannot verify `policy_snapshot_hash`; C7 `validate_hash` fails. |
| **Immediate action** | C2 cannot issue or validate capabilities referencing snapshots; continuation eligibility fails ("Policy snapshot pinned" criterion, ADR §2.3). Executors STOP. |
| **Recovery action** | Restore C7; re-validate in-flight capabilities; resume. |
| **Final state** | `EXPIRED → ABORTED` for in-flight commands. |
| **Data integrity guarantee** | No continuation without a verifiable pinned policy snapshot (Invariant 12). |
| **Audit requirement** | C7-unavailability event; fail-closed decisions; recovery event. |
| **Components** | C2, C7, C12 |
| **Invariants** | 12 |

### FM-IMPL-15 — Time-anchor service unavailable (C14)

| Field | Value |
|---|---|
| **Trigger condition** | C14 signed time-anchor service is unavailable; no fresh signed anchors can be issued or validated. |
| **Detection mechanism** | C14 `issue_anchor`/`validate_anchor` fails; C1, C2, C6 cannot sign or validate timestamps. |
| **Immediate action** | All authority issuance halts (no signed timestamps → no valid leases/capabilities/revocations). Executors with active continuations must STOP (time bounds cannot be verified — ADR §2.8). |
| **Recovery action** | Restore C14; re-anchor time; executors refresh signed anchors before new work (ADR §2.15 step 8). |
| **Final state** | `EXPIRED → ABORTED` for in-flight; system resumes after C14 restored. |
| **Data integrity guarantee** | No continuation under disputed time (Invariant 14); monotonic bounds still apply to in-flight continuations (they stop at their bound). |
| **Audit requirement** | C14-unavailability event; stop decisions; recovery event. |
| **Components** | C1, C2, C3, C4, C6, C12, C14 |
| **Invariants** | 14 |

### FM-IMPL-16 — Downstream effect identity layer unavailable (C13)

| Field | Value |
|---|---|
| **Trigger condition** | C13 downstream effect identity layer is unavailable; effects cannot be validated or deduplicated. |
| **Detection mechanism** | C13 `check_effect`/`record_effect` fails; downstream systems cannot confirm deduplication. |
| **Immediate action** | Executors must not produce external effects (effect identity cannot be verified — idempotency guarantee lost). STOP continuation. |
| **Recovery action** | Restore C13; reconcile any in-flight effects; resume. |
| **Final state** | `EXPIRED → ABORTED` or `RECONCILING` for effects already committed. |
| **Data integrity guarantee** | No effects applied without identity validation (Invariant 10); pending effects held. |
| **Audit requirement** | C13-unavailability event; stop decisions; recovery event. |
| **Components** | C8, C9, C10, C12, C13 |
| **Invariants** | 10 |

### FM-IMPL-17 — Reconciliation engine unavailable (C10)

| Field | Value |
|---|---|
| **Trigger condition** | C10 reconciliation engine is unavailable at recovery time (Brain recovered but C10 cannot process reports). |
| **Detection mechanism** | C10 `submit_report`/`reconcile_command` fails; reports queue unprocessed past `completion_report_deadline`. |
| **Immediate action** | Reports are held (not lost); commands remain in `RECONCILING` state; no terminal classification issued. |
| **Recovery action** | Restore C10; process queued reports; reconcile. Late reports (past deadline) are still accepted but flagged. |
| **Final state** | `RECONCILING → terminal classification` (delayed). |
| **Data integrity guarantee** | No terminal state without reconciliation (Invariant 7); reports preserved. |
| **Audit requirement** | C10-unavailability event; delayed-reconciliation event; recovery event. |
| **Components** | C10, C11, C12 |
| **Invariants** | 7, 8 |

### FM-IMPL-18 — Conflict review queue unavailable (C11)

| Field | Value |
|---|---|
| **Trigger condition** | C11 conflict review queue is unavailable; conflicts cannot be enqueued or surfaced to operators. |
| **Detection mechanism** | C10 cannot enqueue; C11 `enqueue`/`list_pending` fails. |
| **Immediate action** | Conflicting commands remain frozen in `MANUAL_REVIEW_REQUIRED`; no silent resolution (Invariant 8). |
| **Recovery action** | Restore C11; enqueue pending conflicts; operators resolve. |
| **Final state** | `MANUAL_REVIEW_REQUIRED` (held) until C11 restored and operator resolves. |
| **Data integrity guarantee** | Frozen effects remain frozen; no silent conflict resolution. |
| **Audit requirement** | C11-unavailability event; held-conflict record; recovery event. |
| **Components** | C10, C11, C12 |
| **Invariants** | 8 |

### FM-IMPL-19 — Capability service unavailable (C2)

| Field | Value |
|---|---|
| **Trigger condition** | C2 continuation capability service is unavailable; capabilities cannot be issued, validated, or revoked. |
| **Detection mechanism** | C2 `issue_capability`/`validate_capability` fails; C1 lease issuance (which references capabilities) is blocked. |
| **Immediate action** | No new continuations can be authorized. Executors with existing valid capabilities may continue if all other eligibility criteria hold (the capability was already issued). New work is paused. |
| **Recovery action** | Restore C2; re-validate in-flight capabilities; resume. |
| **Final state** | `EXPIRED → ABORTED` for new commands; existing continuations proceed or stop per eligibility. |
| **Data integrity guarantee** | No new continuations without capability service; existing capabilities remain valid until their bounds. |
| **Audit requirement** | C2-unavailability event; recovery event. |
| **Components** | C1, C2, C10, C12 |
| **Invariants** | 3, 3a, 4 |

### FM-IMPL-20 — Lease token service unavailable (C1)

| Field | Value |
|---|---|
| **Trigger condition** | C1 signed lease token service is unavailable; leases cannot be issued, renewed, or revoked. |
| **Detection mechanism** | C1 `issue_lease`/`renew_lease` fails; executors cannot acquire or renew leases. |
| **Immediate action** | No new commands dispatched. Existing leases continue until expiry. Executors with active continuations proceed per eligibility (lease already expired; capability governs). |
| **Recovery action** | Restore C1; resume dispatch; reconcile any continuations. |
| **Final state** | Existing leases expire normally; new work paused. |
| **Data integrity guarantee** | No new leases without C1; existing lease authority bounded by signed expiry. |
| **Audit requirement** | C1-unavailability event; recovery event. |
| **Components** | C1, C2, C12 |
| **Invariants** | 1, 2 |

---

## 7. Component × Failure-Mode Impact Map

This matrix shows which components are involved in each failure mode. "X" = directly affected (detection, action, or recovery). Components not marked are not directly involved in that failure mode.

| Failure Mode | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | C10 | C11 | C12 | C13 | C14 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FM-LED-1 | X | | | | X | | | | | | | X | X | |
| FM-LED-2 | X | X | X | | | | | | | | | X | | |
| FM-LED-3 | X | X | X | | | | | | | | | X | | |
| FM-LED-4 | X | X | X | X | X | X | X | X | X | X | | X | X | X |
| FM-LED-5 | X | X | | | X | X | X | | | | | X | | X |
| FM-LED-6 | X | X | X | X | | | | | | | | X | | |
| FM-LED-7 | X | | | | | X | | | | | | X | X | |
| FM-LED-8 | | | | | | X | | | | | | X | | |
| FM-CO-1 | | | | | | | | | X | X | | X | X | |
| FM-CO-2 | | | | | | | | | X | X | X | X | X | |
| FM-CO-3 | | | | | | | | | X | X | | X | X | |
| FM-CO-4 | | | | | | | | | X | X | X | X | X | |
| FM-CO-5 | | | | | | | | | X | X | X | X | X | |
| FM-CO-6 | | | | | | | | X | X | X | X | X | X | |
| FM-CO-7 | | X | | | | X | | | X | X | X | X | X | |
| FM-CO-8 | | | | | | | | | X | X | X | X | X | |
| FM-CO-9 | | X | | | | | | X | X | X | X | X | X | |
| FM-SB-1 | | | | | | | | | X | X | | X | X | |
| FM-SB-2 | | | | | | | | | X | X | X | X | X | |
| FM-SB-3 | | | | | | | | | X | X | X | X | X | |
| FM-SB-4 | | | X | | | | | X | X | X | X | X | X | X |
| FM-SB-5 | | X | | | | | | X | X | X | X | X | | X |
| FM-TM-1 | | X | | | | | | | X | X | X | X | X | |
| FM-TM-2 | | | X | X | | | | | X | X | X | X | | |
| FM-TM-3 | | | | | X | | | | | | | X | | |
| FM-TM-4 | X | X | | | | | | | X | X | X | X | X | |
| FM-TM-5 | | | | | | | | X | X | | | X | X | |
| FM-TM-6 | | | | | | | | X | X | X | X | X | X | |
| FM-TM-7 | | | X | | | | | X | X | X | | X | X | X |
| FM-TM-8 | X | X | X | X | | X | X | | | X | X | X | X | |
| FM-TM-9 | | X | | | | | | X | X | X | X | X | X | X |
| FM-TM-10 | | X | | | | X | | | | | | X | | |
| FM-TM-11 | | X | | | | | X | | | | | X | X | |
| FM-TM-12 | | X | | | | | | | | | | X | | X |
| FM-TM-13 | | | | | | | | | X | X | X | X | X | |
| FM-TM-14 | | | | X | | | | | X | X | X | X | | |
| FM-IMPL-1 | | | X | | X | | | X | X | X | | X | X | |
| FM-IMPL-2 | X | X | X | X | | X | | | | X | | X | | X |
| FM-IMPL-3 | | | X | X | | X | | | | X | | X | X | |
| FM-IMPL-4 | | | X | X | | | | | | | | X | | |
| FM-IMPL-5 | X | X | | | | X | | X | X | X | | X | | |
| FM-IMPL-6 | | X | | | | X | | | | | | X | | |
| FM-IMPL-7 | | X | | | | | | | | | | X | | X |
| FM-IMPL-8 | X | X | | | | X | | | | X | X | X | | X |
| FM-IMPL-9 | | | | X | | | | | X | X | X | X | | |
| FM-IMPL-10 | | | | | X | | | | | | | X | | |
| FM-IMPL-11 | | X | | | | X | | | | | | X | | |
| FM-IMPL-12 | | | | | | | | X | X | X | X | X | X | |
| FM-IMPL-13 | | X | | X | | X | | X | X | X | X | X | | |
| FM-IMPL-14 | | X | | | | | X | | | | | X | | |
| FM-IMPL-15 | X | X | X | X | | X | | | | | | X | | X |
| FM-IMPL-16 | | | | | | | | X | X | X | | X | X | |
| FM-IMPL-17 | | | | | | | | | | X | X | X | | |
| FM-IMPL-18 | | | | | | | | | | X | X | X | | |
| FM-IMPL-19 | X | X | | | | | | | | X | | X | | |
| FM-IMPL-20 | X | X | | | | | | | | | | X | | |

**Most-impacted components (by failure-mode count):** C12 (audit pipeline) is touched by every failure mode — it is the universal observer and must be the most available. C10 (reconciliation engine) and C13 (downstream effect identity layer) are touched by the majority of outcome-level failure modes. C2 (continuation capability service) is the most-impacted authority component, reflecting its role as the authority hub.

---

## 8. Invariant × Failure-Mode Map

This matrix shows which ADR invariants (1–15) are exercised or at risk in each failure mode. "X" = the failure mode directly tests or threatens this invariant.

| Failure Mode | I1 | I2 | I3 | I3a | I4 | I5 | I6 | I7 | I8 | I9 | I10 | I11 | I12 | I13 | I14 | I15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FM-LED-1 | X | X | | | X | | | | | | | | | | | |
| FM-LED-2 | | X | X | X | X | | | | | | | | | | | |
| FM-LED-3 | | X | X | X | X | | | | | | | | | | | |
| FM-LED-4 | | X | X | | X | X | X | X | | | X | | | X | X | |
| FM-LED-5 | | | | | X | | | | | | | | X | X | X | |
| FM-LED-6 | | | | | X | | | | | | | | | | | |
| FM-LED-7 | X | | | | | | | | | | | | X | | | |
| FM-LED-8 | | | | | | | | | | | | | X | | | |
| FM-CO-1 | | | | | | | X | X | | | X | X | | | | |
| FM-CO-2 | | | | | | | | X | X | | X | | | | | |
| FM-CO-3 | | | | | | | X | X | | | X | X | | | | |
| FM-CO-4 | | | | | | | | X | X | | X | | | | | |
| FM-CO-5 | | | | | | | X | X | X | | X | X | | | | |
| FM-CO-6 | | | | | | | X | X | | | X | | | | | |
| FM-CO-7 | | X | X | | X | | | | X | | X | | | X | | |
| FM-CO-8 | | | | | | | X | | X | | | | | | | |
| FM-CO-9 | | | | | | | | | X | | | | | | | X |
| FM-SB-1 | | | | | | | X | X | | | X | X | | | | |
| FM-SB-2 | | | | | | | | X | X | | X | | | | | |
| FM-SB-3 | | | | | | | X | X | X | | X | X | | | | |
| FM-SB-4 | | | | | | X | X | X | | | X | | | | X | |
| FM-SB-5 | | | X | | | X | | X | | | | | | | X | |
| FM-TM-1 | | X | X | | | | | | X | | | | | | | |
| FM-TM-2 | | | | | X | | | | X | | | | | | | |
| FM-TM-3 | | | | | X | | | | | | | | | | | |
| FM-TM-4 | | | | | | | | X | X | | X | | | | | |
| FM-TM-5 | | | | | | | | | | | X | | | | | |
| FM-TM-6 | | | | | | | X | | X | | | X | | | | |
| FM-TM-7 | | | | | | X | X | X | | | X | | | | X | |
| FM-TM-8 | | | | | | | | | | X | | | | | | |
| FM-TM-9 | | | X | | | X | | | | | | | | | X | |
| FM-TM-10 | | | | | | | | | | | | | | X | | |
| FM-TM-11 | | | | | | | | | | | | | X | | | |
| FM-TM-12 | | | | | | | | | | | | | | | X | |
| FM-TM-13 | | | | | | | X | | X | | | | | | | |
| FM-TM-14 | | | | | X | | | | X | | | | | | | |
| FM-IMPL-1 | | | | | | | X | X | | | X | X | | | | |
| FM-IMPL-2 | | | | | | | | X | | | | X | | X | X | |
| FM-IMPL-3 | | | | | X | | | | | | X | | | X | | |
| FM-IMPL-4 | | | | | X | | | | | | | | | | | |
| FM-IMPL-5 | | | | | | | X | X | | | | X | | | | |
| FM-IMPL-6 | | | | | | | | | | | | | | X | | |
| FM-IMPL-7 | | | | | | | | | | | | | | | X | |
| FM-IMPL-8 | X | X | X | | | | | | | | | | | | X | |
| FM-IMPL-9 | | | | | X | | | | X | | | | | | | |
| FM-IMPL-10 | | | | | X | | | | | | | | | | | |
| FM-IMPL-11 | | | | | | | | | | | | | | X | | |
| FM-IMPL-12 | | | | | | | X | | X | | | X | | | | |
| FM-IMPL-13 | | | | | | | X | | X | | | X | | | | |
| FM-IMPL-14 | | | | | | | | | | | | | X | | | |
| FM-IMPL-15 | | | | | | | | | | | | | | | X | |
| FM-IMPL-16 | | | | | | | | | | | X | | | | | |
| FM-IMPL-17 | | | | | | | | X | | | | | | | | |
| FM-IMPL-18 | | | | | | | | | X | | | | | | | |
| FM-IMPL-19 | | | X | X | X | | | | | | | | | | | |
| FM-IMPL-20 | X | X | | | | | | | | | | | | | | |

**Most-exercised invariants:** I4 (default STOP), I8 (no silent conflict resolution), I10 (idempotency), and I14 (time non-manipulability) appear across the widest range of failure modes. Any acceptance test plan must cover these invariants under multiple failure-mode scenarios.

---

## 9. Recovery Decision Tree

This decision tree is followed by the Brain (C10, with C3/C14) upon recovery detection. It implements ADR §2.15 (10-step recovery protocol) as a branching procedure. Each leaf produces a terminal classification and command state.

```
START: Brain recovery detected (C3 OK for brain_recovery_confirmation_period, signed by C14)
  │
  ▼
[Step 1] Recovery confirmed & signed? ──no──► wait; re-check
  │yes
  ▼
[Step 2] For each executor with active continuation:
         apply OPERATION ATOMICITY RULE (§2.12.2):
           operation committed/irreversible? ──yes──► FINISH + report
           operation uncommitted? ───────────yes──► ABORT
           (never both for the same operation)
  │
  ▼
[Step 3] Collect completion reports within completion_report_deadline (C9 → C10)
  │
  ▼
[Step 4] Report received for command_id?
  │
  ├─no──► [FM-CO-8 / FM-TM-13] INVALID_CONTINUATION
  │        freeze effects (C13); security event; manual review (C11)
  │        → MANUAL_REVIEW_REQUIRED
  │
  └─yes─► [Step 5] Receipt valid? (C9 verify_receipt; C2 capability; C4 outage evidence; C6 watermark)
           │
           ├─no──► [FM-IMPL-13] Receipt forgery / invalid
           │        freeze; security event; manual review (C11)
           │        → INVALID → REVIEW
           │
           └─yes─► [Step 6] Continuation was eligible at time of continuation? (C10 validates)
                    │
                    ├─no──► [FM-CO-7] INVALID_CONTINUATION
                    │        discard result; flag executor; freeze effects; manual review (C11)
                    │        → INVALID → REVIEW
                    │
                    └─yes─► [Step 7] Number of continuation reports for command_id?
                             │
                             ├─one──► [Step 8a] Single-report path
                             │         │
                             │         ├─ result matches Brain expectation? ──yes──► [FM-CO-1]
                             │         │   apply authoritative effects (C13); classification VALID_CONTINUATION
                             │         │   → SUCCEEDED
                             │         │
                             │         └─ result diverges? ────────────────────yes──► [FM-CO-2]
                             │             reconcile effects; compensation if reversible; manual review if not
                             │             classification VALID_BUT_RECONCILED
                             │             → RECONCILED → SUCCEEDED  or  MANUAL_REVIEW_REQUIRED
                             │
                             └─many─► [Step 8b] Multi-report (split-brain) path
                                      │
                                      ├─ result_digest values agree? ──no──► [FM-SB-3 / FM-CO-5]
                                      │   freeze all affected effects; manual review (C11)
                                      │   classification CONFLICTING_REPORTS
                                      │   → MANUAL_REVIEW_REQUIRED
                                      │
                                      └─yes──► effects idempotent? (C13)
                                               │
                                               ├─yes──► [FM-SB-1 / FM-CO-3]
                                               │   select first by trusted signed time (tie-break: lowest executor_id)
                                               │   others DUPLICATE_AGREED; deduplicate by stable identity
                                               │   classification VALID_CONTINUATION
                                               │   → SUCCEEDED
                                               │
                                               └─no───► [FM-SB-2 / FM-CO-4]
                                                   select first by trusted signed time; others DUPLICATE_AGREED
                                                   FREEZE effects (non-reversible); manual review (C11)
                                                   classification VALID_BUT_RECONCILED
                                                   → MANUAL_REVIEW_REQUIRED
  │
  ▼
[Step 9] For every command reaching a non-terminal or review state:
         - freeze conflicting/non-reversible downstream effects (C13)
         - enqueue manual-review items (C11)
         - no silent conflict resolution (Invariant 8)
  │
  ▼
[Step 10] Replay authorization (C10 authorize_replay):
          - all continuations reconciled? ──no──► block replay; remain in review
          - effects resolved? ──────────────no──► block replay; remain in review
          - yes──► authorize replay with new lease; preserve root_command_id in effect identities (ADR §2.7)
  │
  ▼
[Step 11] Policy refresh: all executors refresh policy snapshots (C7) and revocation watermarks (C6)
          before accepting new work (ADR §2.15 step 8)
  │
  ▼
[Step 12] Audit completion: all continuation events finalized in immutable ledger (C12)
          (ADR §2.15 step 9; Invariant 11 — never truncated)
  │
  ▼
[Step 13] Gate evaluation: only after full implementation certification may
          SIGMA_LEASE_EXPIRY_CONTINUATION_GATE be evaluated for unblocking (ADR §2.15 step 10)
  │
  ▼
END
```

### 9.1 Decision-Tree Notes

1. **Operation atomicity (Step 2)** is applied per operation, not per continuation. A single continuation may have some operations finished and others aborted. Each determination is recorded in C8 and surfaced in C9.
2. **Trusted comparable signed time** (ADR §2.6.3.1, §2.8) is the only basis for cross-executor timestamp comparison. Executor-local monotonic clocks are never compared across machines. Where signed time agrees or is unavailable, the deterministic tie-breaker (lowest `executor_id`) applies.
3. **No silent resolution**: every leaf that produces a non-`SUCCEEDED` state records a conflict/freeze/invalid event in C12 and, where applicable, enqueues to C11. Invariant 8 holds at every leaf.
4. **Replay is gated**: replay (Step 10) is authorized only after all continuations for a command are reconciled and effects are resolved. Replay preserves `root_command_id` in effect identities (ADR §2.7) so deduplication against prior effects is maintained.
5. **Default is STOP**: if at any point a determination cannot be made (ambiguous signals, missing evidence, unavailable component), the path resolves to STOP / `ABORTED` / `MANUAL_REVIEW_REQUIRED` rather than proceeding.

---

## 10. Recovery Protocol Step Mapping

This section maps the ADR §2.15 10-step recovery protocol to the failure modes and decision-tree steps above, to confirm complete coverage.

| ADR §2.15 Step | Description | Decision-Tree Step | Failure Modes Exercised |
|---|---|---|---|
| 1 | Recovery detection | Step 1 | FM-SB-4, FM-TM-7, FM-IMPL-2 |
| 2 | In-progress operation atomicity | Step 2 | FM-SB-4, FM-TM-7, FM-IMPL-1, FM-IMPL-2, FM-IMPL-3 |
| 3 | Report collection | Step 3–4 | FM-CO-8, FM-TM-13 |
| 4 | Reconciliation | Steps 5–8 | FM-CO-1 through FM-CO-9, FM-SB-1 through FM-SB-3 |
| 5 | Conflict freeze | Step 9 | FM-CO-4, FM-CO-5, FM-CO-9, FM-SB-2, FM-SB-3, FM-TM-4 |
| 6 | Manual review queue | Step 9 | FM-CO-2, FM-CO-4, FM-CO-5, FM-CO-7, FM-CO-8, FM-CO-9, FM-SB-2, FM-SB-3, FM-SB-5, FM-TM-1, FM-TM-2, FM-TM-6, FM-TM-8, FM-TM-13, FM-IMPL-12, FM-IMPL-13 |
| 7 | Replay authorization | Step 10 | FM-LED-1, FM-LED-5, FM-LED-6, FM-CO-6 |
| 8 | Policy refresh | Step 11 | FM-IMPL-6, FM-IMPL-14, FM-IMPL-15 |
| 9 | Audit completion | Step 12 | All failure modes (C12 universal) |
| 10 | Gate evaluation | Step 13 | (post-implementation certification) |

Every ADR §2.15 step is covered by at least one failure mode and at least one decision-tree step.

---

## 11. Acceptance Test Coverage Notes

This section is informational only — it points implementers to where test scenarios should be derived. It does not define tests.

- **Lease expiry decisions (FM-LED-1 through FM-LED-8):** each row of ADR §6.1 should have a test that drives the executor to the specified decision and next state.
- **Continuation outcomes (FM-CO-1 through FM-CO-9):** each row of ADR §6.2 should have a test that produces the specified classification and command state.
- **Split-brain (FM-SB-1 through FM-SB-5):** each row of ADR §2.12.2 should have a test, including the operation-atomicity rule for FM-SB-4.
- **Threat model (FM-TM-1 through FM-TM-14):** each ADR §6.3 threat should have a test demonstrating the mitigation fires.
- **Implementation-level (FM-IMPL-1 through FM-IMPL-20):** each component-availability and integrity failure should have a test demonstrating fail-closed behavior and recovery.
- **Operation atomicity rule:** a dedicated test must verify that for a single in-progress operation, the executor applies exactly one of {finish, abort} — never both — and records the determination.
- **Recovery decision tree:** an end-to-end test should drive the full decision tree from recovery detection through terminal classification, covering at least one path to each leaf.

---

## 12. Open Questions for Implementation Phase

These are planning-level questions to be resolved during implementation, not gaps in this document:

1. **C8 journal durability:** What is the required durability guarantee for the continuation journal before the receipt is submitted? Must it be fsync'd per operation, or is batched durability acceptable given the operation atomicity rule?
2. **C12 ledger replication:** How many durable replicas of the audit ledger are required before an `append` is acknowledged? This affects FM-IMPL-5 recovery semantics.
3. **C4 witness topology:** How are witnesses deployed and partitioned relative to Brain and executor regions? This affects FM-IMPL-3 and FM-IMPL-4 detection timing.
4. **C14 anchor frequency:** How frequently must the Brain issue signed time anchors during normal operation to bound the skew-detection window? This affects FM-IMPL-7.
5. **C13 downstream coupling:** Is C13 a library linked into downstream systems, or a separate service? This affects FM-IMPL-16 availability model.

These questions do not block this planning document. They are to be resolved in component-level design and subsequent ADRs per ADR-MC-001 Section 10.

---

## 13. Relationship to Other Planning Documents

| Document | Relationship |
|---|---|
| `01_IMPLEMENTATION_ARCHITECTURE.md` | Source of the C1–C14 component definitions and dependency analysis used in Sections 7–8. |
| `02_COMPONENT_DEPENDENCY_GRAPH.md` | Source of component IDs (C01–C14) and dependency structure; this document uses C1–C14 shorthand. |
| `03_INTERFACE_SPECIFICATIONS.md` | Defines the data models (e.g., `CompletionReport`, `OutageEvidenceBundle`, `StableEffectIdentity`) referenced by detection and recovery actions. |
| `04_STATE_MACHINES.md` | Defines the states (`CONTINUING`, `RECONCILING`, `MANUAL_REVIEW_REQUIRED`, etc.) referenced as final states in this matrix. |
| `05_SEQUENCE_DIAGRAMS.md` | Defines the message orderings that detection and recovery actions must follow. |
| `06_THREAT_MODEL.md` | Companion expansion of ADR §6.3 into a full STRIDE threat model. The threat-model failure modes in Section 5 of this document are the recovery-matrix view of the same threats; `06` owns the attack-vector and residual-risk detail, this document owns the trigger/detection/recovery actions and decision tree. |
| `10_ROLLOUT_ROLLBACK_PLAN.md` | Owns deployment rollout and rollback procedures. The recovery actions in this matrix are runtime recovery, not deployment rollback; the two are complementary and should be cross-referenced during incident runbook authoring. |

This document is consistent with all companion documents (01–06, 10) and with ADR-MC-001. Where any conflict appears, ADR-MC-001 is the source of truth.

---

## 14. Status

| Item | State |
|---|---|
| This document | PLANNING ARTIFACT — no runtime code |
| ADR-MC-001 | ACCEPTED — ratified 2026-08-05 |
| `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE` | BLOCKED — implementation not yet certified |
| Implementation | NOT AUTHORIZED — planning only |
| Deployment | NOT AUTHORIZED |