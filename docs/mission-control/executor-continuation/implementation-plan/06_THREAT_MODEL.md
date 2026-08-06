# 06 — Threat Model: Executor Continuation

**Status:** PLANNING ONLY — no runtime code
**Scope:** Implementation planning artifact for ADR-MC-001 (Executor Continuation After Lease Expiry)
**Source of truth:** ADR-MC-001 (ACCEPTED, ratified 2026-08-05), Section 6.3 (threat model), Section 7 (invariants), Section 9.1 (required components), Section 2.9 (side-effect classes)
**Related docs:** `../ADR_MC_001_EXECUTOR_CONTINUATION.md`, `01_IMPLEMENTATION_ARCHITECTURE.md`, `02_COMPONENT_DEPENDENCY_GRAPH.md`, `03_INTERFACE_SPECIFICATIONS.md`, `04_STATE_MACHINES.md`, `05_SEQUENCE_DIAGRAMS.md`

## 1. Purpose

This document expands the 14-threat summary in ADR-MC-001 Section 6.3 into a full implementation-level threat model. It is a planning artifact only — it authorizes no runtime code, no API changes, no persistence migrations, and no deployment. Implementation requires separate ADRs, branches, and authorizations per ADR-MC-001 Section 10.

The document serves three audiences:

1. **Implementers** — who need to know which controls each component must enforce and which tests must verify them.
2. **Reviewers** — who need to verify that the threat coverage is complete, that every ADR-MC-001 Section 9.1 component and every Section 7 invariant is protected, and that residual risks are documented.
3. **Operators** — who need to understand the residual risk surface for monitoring, incident response, and acceptance gating.

### 1.1 Scope and Method

This threat model covers the executor continuation lifecycle: lease acquisition, renewal, expiry, outage detection, continuation eligibility, continuation execution, completion reporting, reconciliation, replay, and recovery. It covers all 14 components enumerated in ADR-MC-001 Section 9.1 and all 15 invariants in Section 7 (including invariant 3a).

The model uses two complementary methods:

- **ADR threat expansion** — each of the 14 threats in ADR-MC-001 Section 6.3 is expanded to implementation-level detail (threat ID, description, attack vector, likelihood, impact, affected components, affected invariants, mitigation controls, residual risk, test verification).
- **STRIDE analysis** — the six STRIDE categories (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) are mapped to the 14 components to ensure category-complete coverage.

Threats are classified by likelihood and impact using the following scales:

| Rating | Likelihood definition | Impact definition |
|---|---|---|
| Low | Unlikely given existing controls; requires significant attacker capability or a rare confluence of failures | Limited blast radius; recoverable; no irreversible external effects |
| Medium | Plausible under realistic operational conditions; a determined attacker or a common failure mode could trigger it | Significant blast radius; partial recovery possible; may require manual review |
| High | Likely under realistic operational conditions if controls are absent or misconfigured | Broad blast radius; difficult or impossible to recover; may include irreversible external effects |
| Critical | (Impact only) | Irreversible external effects, safety-critical authority leakage, or tenant-wide compromise |

### 1.2 Component and Invariant References

Throughout this document, components are referenced by their Section 9.1 identifiers (C1–C14) as expanded in `01_IMPLEMENTATION_ARCHITECTURE.md` Section 2. Invariants are referenced by their Section 7 numbers (1–15, including 3a). Side-effect classes are referenced by their Section 2.9 identifiers (Class 0–Class 3).

| # | Component | Side |
|---|---|---|
| C1 | Signed lease token service | Brain |
| C2 | Continuation capability service | Brain |
| C3 | Brain heartbeat endpoint | Brain |
| C4 | Witness statement service | Shared (witness plane) |
| C5 | Executor local state cache | Executor |
| C6 | Revocation stream | Brain (read by executor) |
| C7 | Policy snapshot registry | Brain (read by executor) |
| C8 | Continuation journal store | Executor |
| C9 | Completion receipt service | Executor (verified by Brain) |
| C10 | Reconciliation engine | Brain |
| C11 | Conflict review queue | Brain |
| C12 | Audit event pipeline | Shared (all components) |
| C13 | Downstream effect identity layer | Downstream systems |
| C14 | Signed time-anchor service | Brain (consumed by executor) |

---

## 2. Threat Catalog

This section catalogs 23 threats. Threats T1–T14 are the expansion of the 14 threats in ADR-MC-001 Section 6.3. Threats T15–T23 are new implementation-level threats identified during this planning analysis: key compromise, database corruption, network partition scenarios, clock manipulation, capability token replay, witness collusion, audit ledger tampering, configuration drift, and multi-tenant data leakage.

Each threat is specified with the following fields:

- **Threat ID** — stable identifier for cross-referencing.
- **Description** — what the threat is and why it matters.
- **Attack vector** — how the threat could be realized, including the actor or failure mode.
- **Likelihood** — probability of occurrence given the mitigation controls.
- **Impact** — severity of consequences if the threat is realized.
- **Affected components** — which of C1–C14 are involved.
- **Affected invariants** — which of invariants 1–15 (including 3a) are at risk.
- **Mitigation controls** — the design and implementation controls that prevent or limit the threat.
- **Residual risk** — the risk that remains after controls are applied.
- **Test verification** — the test or test class that verifies the control.

### 2.1 Existing Threats (T1–T14, expanded from ADR-MC-001 Section 6.3)

---

#### T1 — Executor continues without capability

**Description:** An executor performs continuation work without holding a valid, signed continuation capability. The executor either never received a capability, uses a forged or expired capability, or attempts to bootstrap authority from the expired lease token alone.

**Attack vector:** The executor (or an attacker controlling the executor process) presents an expired lease token, a fabricated capability, or no capability at all to a downstream system, claiming authority to continue. The downstream system fails to validate the capability independently and honors the effect.

**Likelihood:** Medium
**Impact:** Critical

**Affected components:** C2 (continuation capability service), C5 (executor local state cache), C13 (downstream effect identity layer)

**Affected invariants:** 2 (expired lease cannot authorize), 3 (capability temporal bounds), 4 (continuation is never default)

**Mitigation controls:**
- The continuation capability is cryptographically separate from the lease token and signed by the Brain (Section 2.1.4).
- The capability is unusable before lease expiry (`not_valid_before` set to lease `expires_at` or later).
- Downstream systems must validate the signed continuation capability token — not the expired lease — before honoring any effect produced during continuation (Section 2.1.4).
- Downstream systems must also receive and verify replay-resistant outage evidence bound to the capability via `capability_id` and `command_id` (Section 2.1.4).
- Capability validation is mandatory at the downstream boundary (C13), not just at the executor boundary.

**Residual risk:** If a downstream system does not implement C13 validation, it may honor effects from an executor without a valid capability. This residual risk is mitigated by making C13 a hard dependency for any system that accepts continuation effects and by documenting that downstream systems that skip C13 are out of compliance with the ADR.

**Test verification:** ADR-MC-001 Section 9.3 "Capability issuance and validation" test: verify capability cannot be used before lease expiry or after its own expiry. Additional test: verify downstream effect identity layer (C13) rejects effects lacking a valid capability token and matching outage evidence.

---

#### T2 — Executor continues without Brain outage

**Description:** An executor declares a Brain outage and initiates continuation when the Brain is actually available, either due to transient failures misread as an outage or due to intentional authority bootstrapping.

**Attack vector:** The executor experiences transient network delays or partial failures and interprets them as a Brain outage. Alternatively, a compromised executor deliberately suppresses or ignores Brain responses to manufacture outage conditions and unlock continuation authority.

**Likelihood:** Medium
**Impact:** High

**Affected components:** C3 (brain heartbeat endpoint), C4 (witness statement service), C5 (executor local state cache)

**Affected invariants:** 4 (continuation is never default)

**Mitigation controls:**
- Brain outage is declared only when at least two independent signals cross their thresholds (Section 2.2.2).
- One of the two signals must be a direct-Brain signal: heartbeat acknowledgement, lease renewal rejection, or command status query failure (Section 2.2.2).
- Witness statements alone are never sufficient to declare outage (Section 2.2.2).
- A grace period of at least `brain_outage_grace_period` (default 30 seconds) must elapse before outage declaration (Section 2.2.2).
- The executor must persist the outage declaration locally with timestamp, signals observed, lease token fingerprint, and signed time anchor (Section 2.2.2).
- A network partition that isolates the executor from the Brain but not from witnesses must still satisfy the direct-Brain-signal requirement (Section 2.2.4).

**Residual risk:** If both the heartbeat endpoint and the lease/status endpoints are simultaneously unreachable due to a network issue local to the executor (not a Brain outage), the executor may still declare an outage. This is partially mitigated by the witness signal requirement and the grace period, but a partition that affects all direct-Brain paths while the Brain is healthy could produce a false-positive outage. The residual risk is that continuation begins under a false outage, but the reconciliation engine (C10) will classify the continuation as `INVALID_CONTINUATION` if the Brain was actually available, and the executor may be flagged.

**Test verification:** ADR-MC-001 Section 9.3 "Brain outage declaration" test: verify two-signal rule, direct-Brain-signal requirement, and grace period. Additional test: verify that a single failed request does not trigger outage declaration.

---

#### T3 — Executor continues without local state sufficiency

**Description:** An executor initiates continuation without having all the required inputs, configuration, or prior step outputs needed to perform the work deterministically, leading to incorrect or divergent results.

**Attack vector:** The executor's local state cache (C5) is incomplete due to a prior crash, cache eviction, or incomplete dispatch. The executor proceeds with continuation despite missing inputs, producing a result that diverges from what the Brain would have produced.

**Likelihood:** Medium
**Impact:** High

**Affected components:** C5 (executor local state cache), C8 (continuation journal store)

**Affected invariants:** 4 (continuation is never default)

**Mitigation controls:**
- Continuation eligibility requires a self-check against the task manifest confirming all required inputs and a deterministic path are available (Section 2.3, "Local state sufficient" criterion).
- If the self-check fails, the executor must stop and enter safe-hold state (Section 2.3).
- The continuation journal (C8) records every operation attempted, its input, output, success/failure, and timestamp, enabling post-hoc detection of state-sufficiency failures (Section 2.5.3).

**Residual risk:** The self-check may pass if the local state cache contains stale or subtly inconsistent data (e.g., a prior step output from a different execution attempt). This is mitigated by the result digest comparison during reconciliation (C10), which will detect divergent results and route to manual review. The residual risk is a false-positive continuation that produces a divergent result, caught at reconciliation.

**Test verification:** ADR-MC-001 Section 9.3 "Continuation eligibility" test: verify all criteria must be met; default is STOP. Additional test: verify that an executor with incomplete local state cache enters safe-hold rather than continuing.

---

#### T4 — Multiple executors continue same command

**Description:** Two or more executors independently continue the same command after lease expiry, producing split-brain continuation with potentially divergent results and conflicting external effects.

**Attack vector:** The Brain dispatches the same command to a second executor after the first executor's lease expires but before the first executor detects the Brain outage (or before the first executor's continuation is reconciled). Both executors hold (or believe they hold) valid continuation capabilities and both continue.

**Likelihood:** Low
**Impact:** Critical

**Affected components:** C1 (signed lease token service), C2 (continuation capability service), C10 (reconciliation engine), C11 (conflict review queue)

**Affected invariants:** 7 (every continuation reconciled before terminal state), 8 (conflicts never resolve silently), 10 (idempotency preserved)

**Mitigation controls:**
- Lease exclusivity: the Brain issues a lease to exactly one executor per command at a time (Section 2.1.1).
- Each executor receives a distinct continuation capability scoped to that executor (Section 2.1.4).
- The reconciliation engine (C10) detects multiple continuation reports for the same `command_id` with different `continuation_id` values (Section 2.12.1).
- Conflicting results are frozen and routed to the conflict review queue (C11) for manual review (Section 2.12.2).
- No silent conflict resolution is permitted; all conflicts are recorded and surfaced (Section 2.12.2).

**Residual risk:** If the Brain re-dispatches the command to a second executor during the outage (which should not happen if the Brain is truly unavailable, but could happen during a partial recovery or flapping outage), both executors may continue. The reconciliation engine will detect the conflict, but if the effects are non-reversible (Class 3, which should be prohibited during continuation), the effects may already be committed downstream. The residual risk is limited by the Class 3 prohibition and the downstream effect identity layer (C13) deduplication for idempotent effects.

**Test verification:** ADR-MC-001 Section 9.3 "Split-brain conflict" test: verify conflict detection, freeze, and manual review. Additional test: verify that two executors with distinct capabilities produce `CONFLICTING_REPORTS` classification when results diverge.

---

#### T5 — Executor produces duplicate external effects

**Description:** An executor produces an externally visible effect that duplicates an effect already produced by the original execution, a prior continuation, or a concurrent continuation, violating idempotency.

**Attack vector:** The executor re-performs an operation whose external effect was already applied (e.g., due to a retry, a crash-recovery loop, or a continuation that overlaps with the original execution). The downstream system applies the duplicate effect because it does not check the stable external-effect identity.

**Likelihood:** Medium
**Impact:** High

**Affected components:** C8 (continuation journal store), C13 (downstream effect identity layer)

**Affected invariants:** 10 (idempotency preserved across continuation, replay, and normal execution)

**Mitigation controls:**
- Stable external-effect identity: `(command_id, operation_id, side_effect_slot)` identifies the business operation, not the execution attempt (Section 2.5.1).
- The `command_id` in the effect identity must always refer to the `root_command_id`, never the replay-attempt command record (Section 2.5.1, 2.7).
- Duplicate suppression layers at the executor operation level and the downstream system level (Section 2.5.2).
- The continuation journal (C8) records the stable effect identity for every operation, enabling deduplication (Section 2.5.3).
- The downstream effect identity layer (C13) validates `(command_id, operation_id, side_effect_slot)` before applying effects (Section 2.5.2).

**Residual risk:** If a downstream system does not implement C13, duplicate effects may be applied. This is the same residual risk as T1: downstream systems that skip C13 are out of compliance. For Class 2 effects (idempotent external writes), the downstream system must validate the stable identity; for Class 3 effects, continuation is prohibited entirely.

**Test verification:** ADR-MC-001 Section 9.3 "Idempotency across continuation/replay" test: verify stable effect identity deduplication. Additional test: verify that the downstream effect identity layer (C13) rejects duplicate effects matching the same `(command_id, operation_id, side_effect_slot)`.

---

#### T6 — Executor lies about continuation outcome

**Description:** An executor reports a false continuation outcome — claiming success when the continuation failed, omitting operations it performed, or fabricating a result digest — to avoid accountability or to force an incorrect reconciliation.

**Attack vector:** A compromised executor modifies its completion report before submitting it to the Brain, altering the `final_state`, `operations_performed`, `result_digest`, or `continuation_journal` fields. The Brain accepts the false report and reconciles based on it.

**Likelihood:** Low
**Impact:** High

**Affected components:** C8 (continuation journal store), C9 (completion receipt service), C12 (audit event pipeline)

**Affected invariants:** 6 (every continuation produces an immutable, signed receipt), 11 (authoritative audit storage is complete and never truncated)

**Mitigation controls:**
- Every continuation produces an immutable, signed receipt (Section 2.6.2, invariant 6).
- The completion report includes a `result_digest` (hash of the completion result) and `evidence_refs` (references to produced artifacts) (Section 2.6.2).
- The continuation journal (C8) is an encrypted blob included in the report (Section 2.6.2).
- The audit event pipeline (C12) appends every continuation event to the immutable audit ledger, creating an independent record of what the executor claimed and what was observed (Section 2.13).
- The reconciliation engine (C10) can cross-check the reported outcome against the audit chain and the downstream effect records.
- Receipts are signed and verified; signature verification detects tampering (invariant 6).

**Residual risk:** A sophisticated attacker who controls the executor process and its signing keys could fabricate a self-consistent false report. This is mitigated by the fact that the Brain holds the executor's public key and can detect key compromise, and by the audit chain which records the outage declaration, eligibility decision, and each operation independently. The residual risk is low because fabricating a consistent lie across the receipt, journal, and audit chain requires compromising multiple independent controls.

**Test verification:** ADR-MC-001 Section 9.3 "Completion receipt" test: verify signature and immutability. Additional test: verify that a tampered receipt is rejected by the Brain and that the audit chain records the tampering attempt.

---

#### T7 — Brain recovers during continuation

**Description:** The Brain recovers while one or more executors are actively continuing, creating a window where both the Brain and the executors may produce effects for the same command.

**Attack vector:** The Brain recovers and begins processing the command (e.g., re-dispatching or marking it as failed) while executors are still performing continuation work. The Brain and the executors produce conflicting effects.

**Likelihood:** Medium
**Impact:** Medium

**Affected components:** C3 (brain heartbeat endpoint), C10 (reconciliation engine)

**Affected invariants:** 7 (every continuation reconciled before terminal state)

**Mitigation controls:**
- Recovery detection requires the Brain to be available and responsive for at least `brain_recovery_confirmation_period` (default 10 seconds) (Section 2.6.1).
- Executors are notified of recovery through the heartbeat channel (Section 2.6.1).
- When the Brain recovers during continuation, active continuations must stop (Section 2.12.2).
- For each in-progress operation, the atomicity rule applies: if the operation has already committed or is irreversible, finish it and report; if it has not committed, abort it (Section 2.12.2, 2.15).
- The same operation is never both finished and aborted (Section 2.15).
- The reconciliation engine (C10) reconciles all continuation reports before the command reaches a terminal state (Section 2.6).

**Residual risk:** There is a brief window between Brain recovery and executor notification during which the executor may perform one additional operation. This is mitigated by the operation atomicity rule (committed operations are finished, uncommitted are aborted) and by the `max_continuation_operations` limit (default 1), which bounds the window. The residual risk is a single in-flight operation that may need reconciliation, which the reconciliation engine is designed to handle.

**Test verification:** ADR-MC-001 Section 9.3 "Recovery protocol" test: verify full recovery sequence. Additional test: verify that an executor stops continuation upon receiving the recovery signal and that in-progress operations follow the atomicity rule.

---

#### T8 — Cross-tenant continuation

**Description:** An executor continues a command belonging to a different tenant, violating tenant isolation and potentially exposing or corrupting another tenant's data.

**Attack vector:** A compromised or misconfigured executor presents a continuation capability scoped to tenant A but performs work that affects tenant B's resources. Alternatively, a capability is issued with the wrong `tenant_id` due to a Brain-side bug.

**Likelihood:** Low
**Impact:** Critical

**Affected components:** C2 (continuation capability service), C5 (executor local state cache)

**Affected invariants:** 9 (cross-tenant continuation is impossible)

**Mitigation controls:**
- Continuation capabilities are tenant-scoped: the capability carries `tenant_id` and the executor's execution context must match (Section 2.3, "Tenant isolation" criterion).
- The executor may only continue commands within its own tenant scope (Section 2.14).
- Revocation streams and witness statements are tenant-scoped (Section 2.14).
- Cross-tenant continuation is treated as a security event (Section 2.14).
- Tenant-level policies may disable continuation entirely (`continuation_class = STOP`) (Section 2.14).
- The downstream effect identity layer (C13) validates the tenant scope of the effect before applying it.

**Residual risk:** If the executor's execution context is misconfigured to report the wrong tenant, or if the capability service issues a capability with the wrong `tenant_id`, the executor may continue under the wrong tenant. This is mitigated by the Brain-side validation of tenant context at capability issuance and by the downstream effect identity layer's tenant validation. The residual risk is low and would require a Brain-side bug in the capability service.

**Test verification:** ADR-MC-001 Section 9.3 "Cross-tenant isolation" test: verify tenant boundary enforcement. Additional test: verify that a capability scoped to tenant A is rejected when the executor's context is tenant B.

---

#### T9 — Continuation runs unbounded

**Description:** An executor continues for longer than permitted, performing more operations than allowed, or continuing past the capability's validity window, consuming resources and producing unbounded effects.

**Attack vector:** A compromised executor ignores the capability's `max_continuation_duration` and `max_continuation_operations` limits, or a clock manipulation makes the executor believe the validity window has not expired. The executor continues indefinitely.

**Likelihood:** Low
**Impact:** High

**Affected components:** C2 (continuation capability service), C8 (continuation journal store)

**Affected invariants:** 5 (continuation cannot exceed its bounded envelope)

**Mitigation controls:**
- The capability carries `max_continuation_duration` and `max_continuation_operations` (Section 2.1.4).
- `max_continuation_duration` is measured with monotonic time, preventing extension via clock rollback (Section 2.8).
- Per-tenant rate limits (`tenant_max_continuation_rate`, default 10 per minute) act as a circuit breaker (Section 2.4).
- `max_concurrent_continuations_per_executor` (default 3) limits simultaneous continuations (Section 2.4).
- `max_continuation_attempts_per_command` (default 1) prevents repeated attempts (Section 2.4).
- `continuation_capability_max_validity` (default 24 hours) is the absolute upper bound (Section 2.4).
- The continuation journal (C8) records every operation, enabling post-hoc detection of bound violations.

**Residual risk:** A compromised executor that controls its own monotonic clock could underreport elapsed time. This is mitigated by the Brain-side reconciliation which checks the continuation journal against the capability bounds and by the signed time anchors which provide an independent time reference. The residual risk is that the executor performs one extra operation before the Brain detects the violation during reconciliation, but the effect is bounded by the downstream duplicate suppression (C13).

**Test verification:** ADR-MC-001 Section 9.3 "Continuation bounds" test: verify duration, operation, and concurrency limits. Additional test: verify that the reconciliation engine flags continuations that exceed capability bounds.

---

#### T10 — Stale revocation/cancellation knowledge

**Description:** An executor continues based on a stale revocation cache, unaware that the command or capability has been revoked or cancelled during the outage, performing work that should have been stopped.

**Attack vector:** The executor's revocation cache (C6) is older than `max_revocation_cache_age` (default 5 seconds) at the moment of lease expiry, or the revocation watermark is below the capability's `revocation_watermark_required`. The executor continues because it has not observed the revocation or cancellation.

**Likelihood:** Medium
**Impact:** Critical

**Affected components:** C6 (revocation stream)

**Affected invariants:** 13 (revocation/cancellation knowledge must be fresh enough; absence of evidence is not permission)

**Mitigation controls:**
- The executor records the highest revocation sequence number it has observed (the watermark) (Section 2.10).
- Continuation requires the watermark to be at least `revocation_watermark_required` from the capability (Section 2.10).
- The local revocation cache must be no older than `max_revocation_cache_age` at the moment of lease expiry (Section 2.10).
- If the revocation watermark is missing, stale, or below the capability requirement, continuation is not permitted (fail-closed) (Section 2.10).
- High-risk, legal, financial, destructive, or irreversible commands default to `STOP` and may not continue without fresh revocation knowledge (Section 2.10).
- If the executor receives a revocation entry during outage, it must stop immediately (Section 2.10).
- A cancellation command observed at or before the revocation watermark is authoritative; continuation is forbidden (Section 2.10).

**Residual risk:** During a complete network partition, the executor cannot receive revocation entries and its cache will age out, triggering the fail-closed behavior. The residual risk is that continuation is blocked even when it would have been safe — but this is the intended fail-closed behavior, not a security risk. The security risk is that the cache is fresh but the revocation was issued after the cache was last refreshed; this is covered by the watermark requirement: if the watermark is below the required value, continuation is blocked.

**Test verification:** ADR-MC-001 Section 9.3 "Revocation watermark" test: verify fail-closed when watermark is stale or missing. Additional test: verify that a revocation received during outage causes the executor to stop immediately.

---

#### T11 — Pinned policy exploited

**Description:** An executor exploits a pinned policy snapshot to perform operations that would be prohibited under the current (superseded) policy, using the stale policy as authority for effects that should not be permitted.

**Attack vector:** The Brain updates the policy during the outage, revoking or restricting certain operations. The executor, holding a capability with a pinned (older) policy snapshot, continues to perform operations that are now prohibited under the updated policy.

**Likelihood:** Low
**Impact:** High

**Affected components:** C7 (policy snapshot registry)

**Affected invariants:** 12 (policy snapshot validity is bounded to the exact pinned snapshot in the capability)

**Mitigation controls:**
- The capability carries `policy_snapshot_hash` and `policy_snapshot_id`; the executor may rely only on that exact policy version (Section 2.11).
- The capability defines `policy_snapshot_not_valid_after`; after that time, the executor must not continue (Section 2.11).
- Critical policy denies/revocations must travel through a survivable channel (signed revocation stream, witness broadcast) (Section 2.11).
- If the executor cannot verify the required revocation watermark, it stops (Section 2.11).
- A pinned policy snapshot cannot authorize side-effect classes or operations not explicitly permitted by the capability (Section 2.11).

**Residual risk:** If a critical policy deny is issued during the outage but does not reach the executor through the survivable channel (e.g., the revocation stream is also partitioned), the executor may continue under the stale policy. This is mitigated by the `policy_snapshot_not_valid_after` bound, which limits the window, and by the revocation watermark requirement. The residual risk is that the executor performs operations permitted under the old policy but prohibited under the new policy, within the bounded validity window. These operations will be caught during reconciliation if they conflict with the new policy.

**Test verification:** ADR-MC-001 Section 9.3 test coverage: verify that the executor stops when `policy_snapshot_not_valid_after` is reached and that the emergency deny channel is honored. Additional test: verify that a pinned policy snapshot cannot authorize operations not in the capability's `permitted_operation_ids`.

---

#### T12 — Clock skew/rollback extends authority

**Description:** An attacker manipulates the executor's clock (or exploits natural clock skew) to extend the continuation authority beyond its valid time window, or to make an expired capability appear valid.

**Attack vector:** The executor's wall-clock is manipulated (via NTP poisoning, timezone changes, or direct system clock modification) to report a time within the capability's validity window when the actual time is outside it. Alternatively, the clock is rolled back to make an expired capability appear valid.

**Likelihood:** Low
**Impact:** Critical

**Affected components:** C14 (signed time-anchor service)

**Affected invariants:** 14 (time cannot be manipulated to extend authority)

**Mitigation controls:**
- The Brain is the authoritative clock source; all lease, capability, and revocation timestamps are signed by the Brain (Section 2.8).
- Capability `not_valid_before` and `not_valid_after` are evaluated against signed Brain anchors, not executor wall-clock alone (Section 2.8).
- `max_continuation_duration` and grace periods are measured with monotonic time, preventing extension via clock rollback (Section 2.8).
- The executor rejects any signed timestamp that rolls backward more than `max_clock_rollback_tolerance` (default 1 second) relative to the last anchor (Section 2.8).
- Maximum skew between executor wall-clock and Brain time is `max_clock_skew_tolerance` (default 5 seconds); exceeding skew is a security event (Section 2.8).
- If executor and Brain time disagree beyond tolerance, the executor must stop and wait for a fresh signed anchor (Section 2.8).
- If the monotonic clock loses continuity (process restart, suspend/resume), the executor must STOP (Section 2.8).

**Residual risk:** A sophisticated attacker who can simultaneously manipulate the executor's wall-clock and suppress the signed time-anchor service could create a window of ambiguity. This is mitigated by the monotonic clock requirement for duration measurement and by the fact that the capability's `not_valid_after` is evaluated against signed Brain anchors. The residual risk is low and bounded by the monotonic clock, which cannot be rolled back.

**Test verification:** ADR-MC-001 Section 9.3 "Time authority" test: verify signed anchors, monotonic bounds, skew/rollback handling. Additional test: verify that an executor with a rolled-back wall-clock stops when the signed anchor rollback exceeds tolerance.

---

#### T13 — Silent continuation

**Description:** An executor continues a command after lease expiry but does not report the continuation to the Brain, leaving the reconciliation engine unaware that continuation occurred and that effects may have been produced.

**Attack vector:** A compromised executor performs continuation work (producing external effects) but does not submit a completion report within `completion_report_deadline` of recovery. The Brain never learns of the continuation and cannot reconcile the effects.

**Likelihood:** Medium
**Impact:** High

**Affected components:** C9 (completion receipt service), C12 (audit event pipeline)

**Affected invariants:** 6 (every continuation produces an immutable, signed receipt), 7 (every continuation is reconciled before terminal state), 11 (authoritative audit storage is complete and never truncated)

**Mitigation controls:**
- Reporting is mandatory regardless of outcome; silent continuation is forbidden (Section 2.6.2).
- Every continuation produces an immutable, signed receipt (invariant 6).
- The completion report deadline (`completion_report_deadline`) bounds the time after recovery within which the report must be submitted (Section 2.6.2).
- The audit event pipeline (C12) appends continuation events to the immutable audit ledger, creating an independent record (Section 2.13).
- The reconciliation engine (C10) expects a report for every command that entered the `CONTINUING` state; a missing report is classified as `INVALID_CONTINUATION` (Section 2.6.4).
- The continuation journal (C8) and the outage declaration record are persisted locally, providing evidence even if the executor does not report.

**Residual risk:** If the executor crashes before submitting the report and the local journal is lost (e.g., due to disk failure), the Brain may not learn of the continuation. This is mitigated by the requirement that the journal be persisted to durable storage and by the downstream effect identity layer (C13), which records the effects independently. The residual risk is that effects were produced but the Brain has no report to reconcile; the C13 records allow the Brain to detect unexplained effects during reconciliation.

**Test verification:** ADR-MC-001 Section 9.3 "Completion receipt" and "Reconciliation" tests. Additional test: verify that a command in `CONTINUING` state with no report within `completion_report_deadline` is classified as `INVALID_CONTINUATION`.

---

#### T14 — Witness quorum compromised

**Description:** A sufficient number of witnesses are compromised or collude to produce false outage statements, enabling an executor to declare a Brain outage that did not occur.

**Attack vector:** An attacker compromises enough witness keys to meet the quorum threshold and produces false witness statements declaring a Brain outage. The executor uses these statements (combined with a direct-Brain signal that is also faked or misread) to declare an outage and continue.

**Likelihood:** Low
**Impact:** Critical

**Affected components:** C4 (witness statement service)

**Affected invariants:** 4 (continuation is never default)

**Mitigation controls:**
- Witnesses are independent control-plane identities, not executors (Section 2.2.4).
- The fault model requires `N >= 3f + 1` and `witness_quorum_size >= 2f + 1` for Byzantine fault tolerance, or `N >= 2f + 1` and `quorum >= f + 1` for crash-fault tolerance (Section 2.2.4).
- `witness_quorum_size` must be strictly less than `N` in either model (Section 2.2.4).
- Witness statements are signed with witness identity keys and include `tenant_id`, `brain_region`, `witness_id`, `statement_id`, and timestamp (Section 2.2.4).
- Each statement includes a monotonically increasing nonce and a signed anchor; stale or replayed statements are rejected (Section 2.2.4).
- Witness statements older than `witness_statement_max_age` are ignored (Section 2.2.4).
- If a witness key is revoked, its statements are invalid; a threshold of valid witnesses must remain (Section 2.2.4).
- An executor cannot count itself, its peers, or any process it controls toward witness quorum (self-exclusion) (Section 2.2.4).
- Witness statements alone are never sufficient to declare outage; a direct-Brain signal is also required (Section 2.2.2).

**Residual risk:** In the CFT model (first implementation), the system is not Byzantine-fault tolerant; a single faulty witness could produce a false statement. This is mitigated by the requirement that witness statements are only supplementary and a direct-Brain signal is also required. In the BFT model, the residual risk is that more than `f` witnesses are compromised simultaneously, which requires significant attacker capability. The residual risk is low in the BFT model and medium in the CFT model (documented as not Byzantine-fault tolerant).

**Test verification:** ADR-MC-001 Section 9.3 "Witness statement validation" test: verify witness identity, quorum, replay resistance, self-exclusion. Additional test: verify that a revoked witness's statements are rejected and that the quorum is recalculated.

---

### 2.2 New Implementation-Level Threats (T15–T23)

The following threats are not in ADR-MC-001 Section 6.3 but are identified during this implementation-level analysis. They address threats that arise from the concrete implementation of the 14 components: cryptographic key management, persistent storage integrity, network behavior, clock infrastructure, token lifecycle, witness coordination, audit integrity, configuration management, and multi-tenant data isolation.

---

#### T15 — Key compromise

**Description:** The private signing keys used by the Brain (for lease tokens, capabilities, time anchors, and revocation entries), by witnesses (for witness statements), or by executors (for receipts) are compromised, allowing an attacker to forge authoritative tokens.

**Attack vector:** An attacker gains access to the Brain's signing key material through a host compromise, a secrets-management breach, a side-channel attack, or an insider threat. With the Brain's private key, the attacker can forge lease tokens, continuation capabilities, time anchors, and revocation entries. With a witness's private key, the attacker can forge witness statements. With an executor's private key, the attacker can forge completion receipts.

**Likelihood:** Low
**Impact:** Critical

**Affected components:** C1 (signed lease token service), C2 (continuation capability service), C4 (witness statement service), C9 (completion receipt service), C14 (signed time-anchor service), C6 (revocation stream)

**Affected invariants:** 1 (valid lease required), 2 (expired lease cannot authorize), 3 (capability temporal bounds), 3a (only latest capability may be exercised), 6 (signed receipts), 11 (audit storage complete), 14 (time cannot be manipulated)

**Mitigation controls:**
- All signing keys are stored in a dedicated secrets-management system (e.g., HSM, vault) with access logging and rotation policies.
- Key rotation is supported and documented; rotated keys are revoked and their revocation is published through the revocation stream (C6).
- The Brain's signing key is distinct from other keys; compromise of one key does not compromise all token types.
- Capability tokens are signed with a key distinct from lease tokens, reducing the blast radius of a single key compromise (Section 2.1.4).
- Witness keys are distinct from Brain keys and from each other (Section 2.2.4).
- Receipt verification uses the executor's public key, which is registered with the Brain at dispatch time; a key change mid-continuation is a security event.
- The audit event pipeline (C12) records all key issuance, rotation, and revocation events, enabling detection of anomalous key usage.
- Downstream systems validate tokens against the Brain's published public keys; a key rotation invalidates tokens signed with the old key after a revocation watermark.

**Residual risk:** If the Brain's primary signing key is compromised and the attacker acts before the key is rotated and revoked, the attacker can forge capabilities and time anchors. The residual risk is bounded by the key rotation procedure and by the revocation stream, which allows the Brain to invalidate all tokens signed with the compromised key. The window between compromise and detection is the primary residual risk. This is mitigated by access logging and anomaly detection on key usage.

**Test verification:** Test key rotation: verify that tokens signed with a rotated key are rejected after the revocation watermark is published. Test key revocation: verify that a revoked witness's statements are rejected. Test receipt forgery: verify that a receipt signed with a non-registered executor key is rejected.

---

#### T16 — Database corruption

**Description:** The persistent storage backing the audit ledger (C12), the continuation journal (C8), the executor local state cache (C5), or the Brain's authoritative state (leases, capabilities, revocation entries) is corrupted, leading to data loss, inconsistent state, or inability to reconcile.

**Attack vector:** A storage failure (disk corruption, database crash, filesystem error) corrupts the data backing one or more components. Alternatively, a bug in the persistence layer writes inconsistent or partial data. The corruption may affect the audit ledger (losing events), the continuation journal (losing operation records), or the local state cache (losing inputs needed for continuation).

**Likelihood:** Medium
**Impact:** High

**Affected components:** C5 (executor local state cache), C8 (continuation journal store), C12 (audit event pipeline), C10 (reconciliation engine)

**Affected invariants:** 6 (signed receipts), 7 (every continuation reconciled), 11 (audit storage complete and never truncated)

**Mitigation controls:**
- The audit ledger (C12) is append-only and backed by a durable, replicated storage system (e.g., PostgreSQL with WAL, or a dedicated append-only log). Corruption of the ledger is detected by hash-chaining: each event links to the previous event's hash.
- The continuation journal (C8) is persisted to durable storage before any external effect is produced, ensuring that the journal is available for reconciliation even if the executor crashes.
- The executor local state cache (C5) is checksummed; corruption is detected by the self-check against the task manifest (Section 2.3, "Local state sufficient" criterion).
- The reconciliation engine (C10) detects missing or corrupted reports by cross-checking the audit chain against the expected continuation events.
- Database corruption triggers a fail-closed behavior: if the audit ledger or continuation journal cannot be read, the system stops and requires operator intervention.
- Regular backups and point-in-time recovery for the audit ledger ensure that corruption does not result in permanent data loss.

**Residual risk:** If the corruption affects both the primary and replica of the audit ledger simultaneously (e.g., a correlated storage failure), events may be lost. This is mitigated by hash-chaining (which detects gaps) and by backups. The residual risk is that a corruption event between the last backup and the failure could lose recent events, but the hash-chain gap will be detected and flagged as a security event. For the continuation journal, if the journal is corrupted before the report is submitted, the Brain may not have the full operation log; this is mitigated by the requirement that the journal be flushed before external effects are produced.

**Test verification:** Test audit ledger integrity: verify that hash-chain gaps are detected and flagged. Test journal durability: verify that the continuation journal is persisted before external effects are produced. Test cache corruption: verify that a corrupted local state cache triggers the self-check failure and the executor enters safe-hold.

---

#### T17 — Network partition scenarios

**Description:** A network partition isolates the executor from the Brain, from witnesses, from downstream systems, or from some combination thereof, creating ambiguity about outage detection, continuation eligibility, and effect delivery.

**Attack vector:** A network failure (router outage, DNS failure, firewall misconfiguration, cloud provider partition) isolates the executor from one or more system components. The partition may be:
- **Partition A:** Executor isolated from Brain but not from witnesses or downstream systems.
- **Partition B:** Executor isolated from Brain and witnesses but not from downstream systems.
- **Partition C:** Executor isolated from Brain, witnesses, and downstream systems (total isolation).
- **Partition D:** Executor isolated from downstream systems but not from Brain (reverse partition).

**Likelihood:** Medium
**Impact:** High

**Affected components:** C3 (brain heartbeat endpoint), C4 (witness statement service), C6 (revocation stream), C13 (downstream effect identity layer), C14 (signed time-anchor service)

**Affected invariants:** 4 (continuation is never default), 13 (revocation knowledge must be fresh), 14 (time cannot be manipulated)

**Mitigation controls:**
- **Partition A (executor isolated from Brain, not witnesses/downstream):** The executor can obtain witness statements but must still satisfy the direct-Brain-signal requirement (Section 2.2.4). Since the executor cannot reach the Brain, the heartbeat, lease renewal, and status query signals will all fail, satisfying the direct-Brain-signal requirement. The revocation cache will age out, triggering fail-closed behavior if it exceeds `max_revocation_cache_age`. The executor may continue only if the revocation watermark is sufficient and all other eligibility criteria are met.
- **Partition B (executor isolated from Brain and witnesses, not downstream):** The executor cannot obtain witness statements, so the witness signal is unavailable. The executor must still have two independent signals, one of which is a direct-Brain signal. The direct-Brain signals (heartbeat, lease, status) will fail due to the partition. A second signal (e.g., policy broadcast silence) may also be available. If two signals cross thresholds, the executor may declare an outage. The revocation cache will age out, triggering fail-closed.
- **Partition C (total isolation):** The executor cannot reach the Brain, witnesses, or downstream systems. It cannot produce external effects (no downstream connectivity), so continuation is effectively a no-op. The executor should enter safe-hold. No external effects are produced, so no harm is done.
- **Partition D (executor isolated from downstream, not Brain):** The executor can reach the Brain, so no outage is declared. Continuation is not triggered. This is the safest partition scenario.
- The revocation stream (C6) is consumed via a pull-based or push-based mechanism with a cache; if the cache ages out, continuation is blocked (fail-closed).
- The signed time-anchor service (C14) provides time anchors via the heartbeat channel; if the heartbeat is unavailable, the executor must rely on the last signed anchor plus monotonic time, and must STOP if the monotonic clock loses continuity (Section 2.8).

**Residual risk:** In Partition B, the executor may declare an outage and continue without witness confirmation, relying solely on direct-Brain signals and policy silence. This is permitted by the ADR (witnesses are supplementary, not required). The residual risk is that the executor continues during a partition that also affects the Brain's ability to receive reports after recovery; the report will be delayed but the `completion_report_deadline` provides a bound. If the partition persists beyond the capability's `not_valid_after`, the executor must stop.

**Test verification:** Test partition A: verify that the executor can declare an outage with direct-Brain signals and witness statements, and that continuation proceeds only if the revocation watermark is sufficient. Test partition B: verify that the executor can declare an outage with two direct-Brain signals (no witnesses) and that the revocation cache aging triggers fail-closed. Test partition C: verify that the executor enters safe-hold and produces no external effects. Test partition D: verify that no outage is declared and continuation is not triggered.

---

#### T18 — Clock manipulation

**Description:** The executor's clock infrastructure is manipulated to affect time-based decisions, distinct from the signed-anchor rollback covered in T12. This includes NTP poisoning, monotonic clock discontinuity, and timezone manipulation.

**Attack vector:** An attacker poisons the NTP server the executor uses for wall-clock synchronization, causing the executor's wall-clock to drift or jump. Alternatively, the executor process is suspended (e.g., VM pause) and resumed, causing a discontinuity in the monotonic clock. Or the timezone is changed to shift the interpretation of `not_valid_before` or `not_valid_after`.

**Likelihood:** Low
**Impact:** Critical

**Affected components:** C14 (signed time-anchor service), C5 (executor local state cache)

**Affected invariants:** 5 (continuation cannot exceed bounded envelope), 14 (time cannot be manipulated to extend authority)

**Mitigation controls:**
- `max_continuation_duration` and grace periods are measured with monotonic time, which is not affected by NTP poisoning or timezone changes (Section 2.8).
- The executor rejects any signed timestamp that rolls backward more than `max_clock_rollback_tolerance` (Section 2.8).
- If the monotonic clock loses continuity (process restart, suspend/resume), the executor must STOP (Section 2.8).
- Capability `not_valid_before` and `not_valid_after` are evaluated against signed Brain anchors, not executor wall-clock alone (Section 2.8).
- Timezone-relative fields are stored and compared in UTC; timezone changes do not affect the comparison.
- The executor maintains a wall-clock corrected by signed Brain anchors, not by NTP alone (Section 2.8).

**Residual risk:** NTP poisoning could cause the executor's wall-clock to drift within the `max_clock_skew_tolerance` (5 seconds) without triggering a stop. This is within the designed tolerance and does not extend authority meaningfully. A larger drift would trigger a security event. The monotonic clock is not affected by NTP, so duration bounds are preserved. The residual risk is a small (within tolerance) wall-clock drift that does not extend the capability validity window because that window is evaluated against signed Brain anchors.

**Test verification:** Test NTP poisoning: verify that a wall-clock drift within tolerance does not extend the capability window and that a drift beyond tolerance triggers a security event. Test monotonic discontinuity: verify that a process suspend/resume causes the executor to STOP. Test timezone change: verify that timezone changes do not affect `not_valid_before`/`not_valid_after` comparison.

---

#### T19 — Capability token replay

**Description:** A valid continuation capability token is captured and replayed in a different context — a different executor, a different command, or after the capability has been superseded — to authorize unauthorized continuation.

**Attack vector:** An attacker intercepts a valid capability token (e.g., from a compromised network path, a log file, or a crashed executor's disk) and presents it to a downstream system or to the Brain's reconciliation endpoint, claiming authority for a different command or executor. Alternatively, a superseded capability (from a prior lease renewal) is replayed after a new capability has been issued.

**Likelihood:** Low
**Impact:** Critical

**Affected components:** C2 (continuation capability service), C13 (downstream effect identity layer)

**Affected invariants:** 3 (capability temporal bounds), 3a (only latest capability may be exercised), 10 (idempotency preserved)

**Mitigation controls:**
- The capability token binds `command_id`, `executor_id`, and `tenant_id`; a token presented for a different command, executor, or tenant is rejected (Section 2.1.4).
- Capability supersession: when a lease is renewed, the prior capability is revoked and downstream systems must reject superseded capability IDs (Section 2.1.2).
- The capability's `revocation_watermark_required` field ensures the executor has observed revocations up to a minimum sequence number; a replayed token that references a superseded watermark will be rejected if the downstream system has observed a later revocation (Section 2.1.4).
- The downstream effect identity layer (C13) validates the capability token against the `command_id` and `executor_id` in the effect identity; a mismatch is rejected.
- Outage evidence is bound to the capability via `capability_id` and `command_id`; a replayed token without matching outage evidence is rejected (Section 2.1.4).
- Capability tokens include `not_valid_before` and `not_valid_after`; a token presented outside its validity window is rejected (Section 2.1.4).
- The audit event pipeline (C12) records capability issuance, supersession, and revocation, enabling detection of replay attempts.

**Residual risk:** If an attacker captures a valid, unsuperseded capability token and the matching outage evidence, and presents it to a downstream system before the Brain revokes the capability, the downstream system may honor it. This is mitigated by the binding to `command_id` and `executor_id` (the effect identity must match) and by the downstream duplicate suppression (C13). The residual risk is that a single duplicate effect is produced before the Brain's revocation propagates, but the stable effect identity ensures the duplicate is detected during reconciliation.

**Test verification:** Test capability replay across commands: verify that a capability token for command A is rejected when presented for command B. Test superseded capability: verify that a superseded capability (from a prior renewal) is rejected by downstream systems. Test outage evidence binding: verify that a capability token without matching outage evidence is rejected.

---

#### T20 — Witness collusion

**Description:** Multiple witnesses collude to produce coordinated false outage statements, exceeding the fault tolerance threshold and enabling a false outage declaration. This is distinct from T14 (witness quorum compromised) in that it focuses on coordinated collusion rather than individual key compromise.

**Attack vector:** A group of witnesses (more than `f` in the BFT model, or more than 0 in the CFT model) collude to produce false outage statements for the same tenant and Brain region, with coordinated timestamps and nonces, to make the statements appear independent and non-replayed.

**Likelihood:** Low
**Impact:** Critical

**Affected components:** C4 (witness statement service)

**Affected invariants:** 4 (continuation is never default)

**Mitigation controls:**
- The BFT fault model requires `N >= 3f + 1` and `witness_quorum_size >= 2f + 1`, ensuring that any quorum contains at least `f + 1` honest witnesses (Section 2.2.4).
- Witnesses are independent control-plane identities, not executors; collusion requires compromising multiple independent services (Section 2.2.4).
- Witness statements are scoped to the tenant's Brain partition; a witness for tenant A cannot declare outage for tenant B (Section 2.2.4).
- Each statement includes a monotonically increasing nonce and a signed anchor; coordinated statements must still have valid nonces and anchors (Section 2.2.4).
- Self-exclusion: an executor cannot count itself, its peers, or any process it controls toward witness quorum (Section 2.2.4).
- Witness statements alone are never sufficient to declare outage; a direct-Brain signal is also required (Section 2.2.2).
- Compromised witness handling: if a witness key is revoked, its statements are invalid and a threshold of valid witnesses must remain (Section 2.2.4).
- The first implementation may use a CFT model but must explicitly document that it is not Byzantine-fault tolerant (Section 2.2.4).

**Residual risk:** In the BFT model, collusion of more than `f` witnesses is required to forge a quorum, which requires significant attacker capability across independent services. In the CFT model, even a single faulty witness could contribute to a false quorum, but the direct-Brain-signal requirement provides an independent check. The residual risk in the CFT model is medium (documented as not BFT); in the BFT model, it is low. The residual risk is further mitigated by the fact that a false outage declaration still requires a direct-Brain signal, which the attacker must also produce or exploit.

**Test verification:** Test witness collusion (BFT): verify that `f + 1` honest witnesses outvote `f` colluding witnesses. Test witness collusion (CFT): verify that the CFT model is documented as not BFT and that the direct-Brain-signal requirement is enforced. Test revoked witness: verify that a revoked witness's statements do not count toward quorum.

---

#### T21 — Audit ledger tampering

**Description:** An attacker with access to the audit ledger storage modifies, deletes, or inserts audit events to conceal unauthorized continuation, fabricate reconciliation outcomes, or break the causation chain.

**Attack vector:** An attacker with database access (via SQL injection, direct database access, or compromised backup restoration) modifies the audit ledger table: deleting events that record an unauthorized continuation, inserting fake events to support a false reconciliation, or modifying event hashes to break the causation chain detection.

**Likelihood:** Low
**Impact:** Critical

**Affected components:** C12 (audit event pipeline)

**Affected invariants:** 11 (authoritative audit storage is complete and never truncated)

**Mitigation controls:**
- The audit ledger is append-only; no update or delete operations are permitted at the storage layer (enforced by database permissions and schema constraints).
- Each audit event is hash-linked to the previous event, forming a causation chain; any modification breaks the chain and is detectable by verification (Section 2.13).
- The audit ledger is backed by durable, replicated storage with regular backups; corruption or tampering is detectable by comparing replicas.
- Database access is restricted to the audit pipeline service account; no human or application account has write access to the ledger.
- Read-only projection APIs (such as Mission Control causation chain) may paginate or cap displayed links, but the authoritative ledger is never truncated (Section 2.13).
- The audit pipeline signs each event (or the event chain) with a Brain key, providing cryptographic integrity independent of the storage layer.
- Periodic integrity checks verify the hash chain from genesis to the latest event; any gap or hash mismatch is a security event.

**Residual risk:** If an attacker compromises both the database and the Brain's signing key, they could modify the ledger and re-sign the modified events. This is mitigated by separating the signing key (in an HSM or vault) from the database access. The residual risk is low and requires compromising two independent controls. Additionally, off-site backups provide a recovery path if tampering is detected.

**Test verification:** Test hash-chain integrity: verify that modifying an event in the ledger breaks the hash chain and is detected. Test append-only enforcement: verify that update and delete operations on the ledger table are rejected by the database permissions. Test projection truncation: verify that the projection may truncate but the authoritative ledger does not.

---

#### T22 — Configuration drift

**Description:** The configuration settings (Section 9.2) drift across Brain instances, executor instances, or tenants, leading to inconsistent enforcement of continuation limits, outage detection thresholds, or clock tolerances.

**Attack vector:** An operator changes a configuration setting on one Brain instance but not others, or a tenant's configuration is updated but the change does not propagate to all executors. The inconsistency may cause one executor to have looser continuation limits, lower outage detection thresholds, or higher clock skew tolerance than intended, creating a security gap.

**Likelihood:** Medium
**Impact:** High

**Affected components:** C1 (signed lease token service), C2 (continuation capability service), C3 (brain heartbeat endpoint), C6 (revocation stream), C14 (signed time-anchor service)

**Affected invariants:** 5 (continuation cannot exceed bounded envelope), 12 (policy snapshot validity), 13 (revocation knowledge must be fresh), 14 (time cannot be manipulated)

**Mitigation controls:**
- All configuration settings are defined in ADR-MC-001 Section 9.2 and are subject to platform maximums; a platform break-glass policy may reduce limits but never increase them beyond the platform maximum (Section 2.4).
- Configuration changes are versioned and published through the policy snapshot registry (C7); executors pin a specific policy snapshot in their capability (Section 2.11).
- The policy snapshot hash ensures the executor uses the exact policy version intended; configuration drift is detected by hash mismatch (Section 2.11).
- Tenant-level configuration is scoped to the tenant; cross-tenant configuration drift is prevented by tenant isolation (Section 2.14).
- Configuration changes are audited through the audit event pipeline (C12).
- A configuration validation service (planning-level: to be specified in the implementation plan) verifies that all instances have consistent configuration within the allowed variance.
- Platform maximums are enforced at the capability issuance level (C2); even if an executor's local configuration drifts, the capability's bounds are authoritative.

**Residual risk:** If the configuration validation service is not implemented or is itself misconfigured, drift may go undetected. This is mitigated by the policy snapshot pinning, which ensures the executor uses the exact policy version from the capability, not its local configuration. The residual risk is that the Brain's own configuration (e.g., outage detection thresholds) drifts across instances, but this is an operational concern addressed by deployment practices and monitoring, not by the continuation protocol itself.

**Test verification:** Test configuration consistency: verify that all Brain instances report the same configuration for a given tenant. Test policy snapshot pinning: verify that an executor with drifted local configuration still uses the policy snapshot from the capability. Test platform maximum enforcement: verify that a tenant configuration exceeding platform maximums is rejected at capability issuance.

---

#### T23 — Multi-tenant data leakage

**Description:** Data from one tenant leaks to another through shared infrastructure (shared database, shared cache, shared log streams, shared revocation stream partitions), violating tenant isolation beyond the capability-level isolation covered in T8.

**Attack vector:** A shared database table does not enforce row-level security, allowing an executor or Brain query to return data from another tenant. A shared cache key does not include the tenant ID, causing cross-tenant cache collisions. A shared log stream does not partition by tenant, allowing one tenant's audit events to be visible to another tenant's operators. A shared revocation stream partition leaks one tenant's revocation entries to another tenant's executor.

**Likelihood:** Low
**Impact:** Critical

**Affected components:** C5 (executor local state cache), C6 (revocation stream), C8 (continuation journal store), C12 (audit event pipeline)

**Affected invariants:** 9 (cross-tenant continuation is impossible)

**Mitigation controls:**
- The codebase uses PostgreSQL with row-level security (RLS) as a baseline convention (`01_IMPLEMENTATION_ARCHITECTURE.md` Section 1); all tenant-scoped tables enforce RLS policies that filter by `tenant_id`.
- The executor local state cache (C5) is keyed by `(tenant_id, command_id, executor_id)`; cross-tenant cache access is prevented by key isolation.
- The revocation stream (C6) is partitioned by tenant (Section 2.10); an executor for tenant A cannot read tenant B's revocation entries.
- The continuation journal (C8) is scoped to the executor's tenant; journals are not shared across tenants.
- The audit event pipeline (C12) partitions events by `tenant_id`; audit queries are tenant-scoped and enforced by RLS.
- Cross-tenant continuation is forbidden and treated as a security event (Section 2.14).
- Continuation capabilities, revocation streams, and witness statements are tenant-scoped (Section 2.14).
- Continuation reports are routed to the tenant's Brain partition (Section 2.14).

**Residual risk:** If a database query bypasses RLS (e.g., a raw SQL query without tenant filtering, or a superuser connection that bypasses RLS), data may leak across tenants. This is mitigated by the codebase convention of using SQLAlchemy 2.0 async with tenant-scoped sessions and by code review enforcement. The residual risk is low and depends on operational discipline (no superuser queries in application code, RLS policies tested).

**Test verification:** Test RLS enforcement: verify that a query with tenant A's session returns only tenant A's rows. Test cache key isolation: verify that a cache key for tenant A does not collide with tenant B. Test revocation stream partitioning: verify that an executor for tenant A cannot read tenant B's revocation entries. Test audit partitioning: verify that audit queries are tenant-scoped.

---

## 3. STRIDE Analysis

This section maps the six STRIDE categories to the 14 components. Each cell identifies the relevant threats from Section 2 and the primary controls.

### 3.1 STRIDE Category Definitions

| Category | Question | Relevance to executor continuation |
|---|---|---|
| **S**poofing | Can an attacker impersonate a trusted identity? | Executor impersonating the Brain; forged capability tokens; false witness identities; key compromise |
| **T**ampering | Can an attacker modify data or code? | Audit ledger tampering; continuation journal corruption; configuration drift; database corruption |
| **R**epudiation | Can an actor deny an action? | Silent continuation; false completion reports; missing receipts; audit gaps |
| **I**nformation Disclosure | Can an attacker access data they should not see? | Multi-tenant data leakage; cross-tenant continuation; journal exposure |
| **D**enial of Service | Can an attacker disrupt service availability? | Network partitions; unbounded continuation; resource exhaustion; Brain outage (real or induced) |
| **E**levation of Privilege | Can an attacker gain unauthorized authority? | Continuation without capability; continuation without outage; clock manipulation; capability replay; stale revocation exploitation |

### 3.2 STRIDE-to-Component Matrix

| Component | S — Spoofing | T — Tampering | R — Repudiation | I — Info Disclosure | D — Denial of Service | E — Elevation of Privilege |
|---|---|---|---|---|---|---|
| C1 Signed lease token service | T15 (forged lease tokens via key compromise) | T16 (corrupted lease state), T22 (config drift in lease settings) | T13 (missing lease expiry event) | T23 (cross-tenant lease data) | T17 (partition prevents lease renewal) | T1 (continue without capability using forged lease) |
| C2 Continuation capability service | T15 (forged capabilities via key compromise), T19 (capability replay) | T16 (corrupted capability state), T22 (config drift in capability bounds) | T13 (missing capability issuance event) | T23 (cross-tenant capability data) | T9 (unbounded continuation if bounds not enforced) | T1 (continue without capability), T8 (cross-tenant capability), T19 (capability replay) |
| C3 Brain heartbeat endpoint | T15 (forged heartbeat responses) | T22 (config drift in heartbeat threshold) | T13 (missing heartbeat events) | T23 (cross-tenant heartbeat data) | T17 (partition prevents heartbeat), T2 (false outage from missed heartbeats) | T2 (continue without outage via missed heartbeats) |
| C4 Witness statement service | T15 (forged witness statements), T20 (witness collusion) | T22 (config drift in quorum settings) | T13 (missing witness statements) | T23 (cross-tenant witness data) | T17 (partition prevents witness communication) | T2 (false outage via witness collusion), T14 (witness quorum compromised) |
| C5 Executor local state cache | T15 (forged state via key compromise) | T16 (corrupted cache), T22 (config drift) | T13 (missing state records) | T23 (cross-tenant cache data) | T17 (partition prevents state sync) | T3 (continue without state sufficiency), T8 (cross-tenant state) |
| C6 Revocation stream | T15 (forged revocation entries) | T16 (corrupted revocation state), T21 (audit tampering affecting revocation records), T22 (config drift in cache age) | T13 (missing revocation events) | T23 (cross-tenant revocation data) | T17 (partition prevents revocation updates) | T10 (stale revocation knowledge), T19 (replay with stale watermark) |
| C7 Policy snapshot registry | T15 (forged policy snapshot) | T16 (corrupted policy state), T22 (config drift in policy) | T13 (missing policy events) | T23 (cross-tenant policy data) | T17 (partition prevents policy refresh) | T11 (pinned policy exploited) |
| C8 Continuation journal store | T15 (forged journal entries) | T16 (corrupted journal), T21 (journal tampering) | T6 (false journal in report), T13 (missing journal) | T23 (cross-tenant journal data) | T9 (unbounded operations if journal not checked) | T3 (continue without state sufficiency if journal incomplete) |
| C9 Completion receipt service | T15 (forged receipts via key compromise) | T16 (corrupted receipt data) | T6 (false receipt), T13 (missing receipt) | T23 (cross-tenant receipt data) | T17 (partition prevents report submission) | T1 (continue without capability, produce false receipt) |
| C10 Reconciliation engine | T15 (forged reconciliation outcome) | T16 (corrupted reconciliation state), T22 (config drift in reconciliation rules) | T13 (missing reconciliation event) | T23 (cross-tenant reconciliation data) | T7 (Brain recovers during reconciliation) | T4 (multiple executors, conflicting reconciliation) |
| C11 Conflict review queue | T15 (forged conflict resolution) | T16 (corrupted conflict queue), T21 (audit tampering affecting conflict records) | T13 (missing conflict event) | T23 (cross-tenant conflict data) | T4 (conflict queue overflow) | T4 (conflict resolution manipulation) |
| C12 Audit event pipeline | T15 (forged audit events via key compromise) | T16 (corrupted ledger), T21 (ledger tampering) | T13 (missing audit events), T6 (false audit records) | T23 (cross-tenant audit data) | T17 (partition prevents audit append) | T1, T10, T11, T19 (audit gaps enable authority escalation) |
| C13 Downstream effect identity layer | T15 (forged effect identity) | T16 (corrupted effect state) | T13 (missing effect records) | T23 (cross-tenant effect data) | T17 (partition prevents effect validation) | T1 (continue without capability), T5 (duplicate effects), T19 (capability replay) |
| C14 Signed time-anchor service | T15 (forged time anchors via key compromise), T18 (clock manipulation) | T16 (corrupted time state), T22 (config drift in clock tolerances) | T13 (missing time anchor events) | T23 (cross-tenant time data) | T17 (partition prevents time anchor delivery) | T12 (clock skew/rollback extends authority), T18 (clock manipulation) |

### 3.3 STRIDE Coverage Summary

| STRIDE category | Threats covered | Primary controls |
|---|---|---|
| Spoofing | T1, T2, T14, T15, T19, T20 | Cryptographic signatures; distinct keys per token type; witness identity validation; key rotation and revocation; capability binding to command/executor/tenant |
| Tampering | T16, T21, T22 | Append-only audit ledger with hash-chaining; durable replicated storage; RLS; configuration versioning via policy snapshots; database permissions |
| Repudiation | T6, T13 | Mandatory signed receipts; immutable audit ledger; completion report deadline; continuation journal; reconciliation classification of missing reports |
| Information Disclosure | T8, T23 | Tenant-scoped capabilities and policies; RLS; tenant-partitioned revocation streams and audit; cache key isolation; cross-tenant continuation as security event |
| Denial of Service | T7, T9, T17 | Continuation bounds (duration, operations, concurrency); per-tenant rate limits; fail-closed on partition; recovery protocol; grace period |
| Elevation of Privilege | T1, T2, T3, T10, T11, T12, T18, T19 | Separate signed capability; two-signal outage detection; self-check; revocation watermark; policy snapshot pinning; signed time anchors; monotonic clocks; capability supersession; downstream validation |

---

## 4. Risk Summary

### 4.1 Threat Risk Matrix

| Threat | Likelihood | Impact | Residual risk level |
|---|---|---|---|
| T1 — Continue without capability | Medium | Critical | Medium (mitigated by C13 downstream validation; residual if C13 not implemented) |
| T2 — Continue without outage | Medium | High | Medium (mitigated by two-signal rule; residual false-positive from local network issues) |
| T3 — Continue without state sufficiency | Medium | High | Low (mitigated by self-check; divergent results caught at reconciliation) |
| T4 — Multiple executors continue | Low | Critical | Low (mitigated by lease exclusivity and conflict detection; residual for non-reversible effects, blocked by Class 3 prohibition) |
| T5 — Duplicate external effects | Medium | High | Low (mitigated by stable effect identity and C13; residual if C13 not implemented) |
| T6 — Executor lies about outcome | Low | High | Low (mitigated by signed receipts and audit chain; residual for sophisticated key compromise) |
| T7 — Brain recovers during continuation | Medium | Medium | Low (mitigated by recovery protocol and atomicity rule; residual single in-flight operation) |
| T8 — Cross-tenant continuation | Low | Critical | Low (mitigated by tenant-scoped capabilities; residual for Brain-side bugs) |
| T9 — Continuation runs unbounded | Low | High | Low (mitigated by monotonic time bounds and rate limits; residual single extra operation) |
| T10 — Stale revocation knowledge | Medium | Critical | Low (mitigated by fail-closed; residual is intended behavior, not a security gap) |
| T11 — Pinned policy exploited | Low | High | Low (mitigated by snapshot validity bounds and revocation watermark; residual within bounded window) |
| T12 — Clock skew/rollback | Low | Critical | Low (mitigated by signed anchors and monotonic time; residual for simultaneous anchor suppression) |
| T13 — Silent continuation | Medium | High | Low (mitigated by mandatory reporting and audit; residual for crash + disk failure) |
| T14 — Witness quorum compromised | Low | Critical | Low (BFT) / Medium (CFT, documented) |
| T15 — Key compromise | Low | Critical | Low (mitigated by key rotation and revocation; residual window between compromise and detection) |
| T16 — Database corruption | Medium | High | Low (mitigated by hash-chaining and replication; residual for correlated failures) |
| T17 — Network partition | Medium | High | Low (mitigated by fail-closed and partition-specific rules; residual false-positive outage in partition B) |
| T18 — Clock manipulation | Low | Critical | Low (mitigated by monotonic time and signed anchors; residual within skew tolerance) |
| T19 — Capability token replay | Low | Critical | Low (mitigated by capability binding and supersession; residual single duplicate effect) |
| T20 — Witness collusion | Low | Critical | Low (BFT) / Medium (CFT, documented) |
| T21 — Audit ledger tampering | Low | Critical | Low (mitigated by append-only, hash-chaining, and key separation; residual for dual compromise) |
| T22 — Configuration drift | Medium | High | Low (mitigated by policy snapshot pinning; residual for Brain-side operational drift) |
| T23 — Multi-tenant data leakage | Low | Critical | Low (mitigated by RLS and tenant partitioning; residual for RLS bypass) |

### 4.2 Residual Risk Concentration

The residual risks cluster around three themes:

1. **Downstream compliance (T1, T5, T19):** The security of the continuation protocol depends on downstream systems implementing C13 (the downstream effect identity layer). If a downstream system does not validate the capability token and the stable effect identity, the residual risk is medium. This is addressed by making C13 a hard dependency and documenting that downstream systems that skip C13 are out of compliance.

2. **CFT vs BFT witness model (T14, T20):** The first implementation may use a CFT witness model, which is not Byzantine-fault tolerant. The residual risk for witness-related threats is medium in the CFT model and low in the BFT model. The CFT model must be explicitly documented as not BFT (Section 2.2.4). Upgrading to BFT is a future implementation goal.

3. **Correlated failures (T15, T16, T21):** Threats that require compromising two independent controls (e.g., key compromise + database access for audit tampering) have low residual risk but high impact if the correlation occurs. These are mitigated by defense-in-depth (separate key storage, separate database access, off-site backups) and by anomaly detection.

### 4.3 Acceptance Gate Criteria

Before `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE` may be evaluated for unblocking, the following threat-model acceptance criteria must be met:

1. All 23 threats have corresponding test verifications (Section 9.3 tests plus the additional tests specified in this document).
2. The STRIDE-to-component matrix (Section 3.2) has no empty cells — every component is analyzed against every STRIDE category.
3. The residual risk for every Critical-impact threat is documented and accepted by the architecture review.
4. The CFT witness model (if used) is explicitly documented as not Byzantine-fault tolerant, with an upgrade plan to BFT.
5. The C13 downstream effect identity layer is implemented and tested for every downstream system that accepts continuation effects.

---

## 5. Cross-References

| ADR-MC-001 Section | This document |
|---|---|
| 2.1.1–2.1.3 (lease lifecycle) | T1, T15, T19 |
| 2.1.4 (continuation capability) | T1, T15, T19 |
| 2.2.1–2.2.3 (outage detection) | T2, T17, T18 |
| 2.2.4 (witness trust model) | T14, T20 |
| 2.3 (continuation eligibility) | T3, T8, T10, T11 |
| 2.4 (continuation limits) | T9 |
| 2.5 (idempotency) | T5, T19 |
| 2.6 (reconciliation) | T4, T7, T13 |
| 2.7 (replay semantics) | T5, T19 |
| 2.8 (time authority) | T12, T18 |
| 2.9 (side-effect classification) | T4, T5 (Class 3 prohibition) |
| 2.10 (revocation watermark) | T10 |
| 2.11 (policy snapshot) | T11, T22 |
| 2.12 (split-brain) | T4 |
| 2.13 (audit chain) | T6, T13, T21 |
| 2.14 (tenant isolation) | T8, T23 |
| 2.15 (recovery protocol) | T7 |
| 6.3 (threat model) | T1–T14 (expansion) |
| 7 (invariants) | All threats reference affected invariants |
| 9.1 (required components) | All threats reference affected components |

---

## 6. Open Questions for Implementation

The following questions are identified by this threat model and should be resolved during implementation planning:

1. **Witness model selection:** Will the first implementation use CFT or BFT? If CFT, what is the upgrade path to BFT? (Affects T14, T20.)
2. **C13 deployment scope:** Which downstream systems will implement the downstream effect identity layer? Are there downstream systems that cannot implement C13, and if so, how are continuation effects to those systems prohibited? (Affects T1, T5, T19.)
3. **Key management infrastructure:** What secrets-management system will be used for Brain, witness, and executor signing keys? What is the key rotation schedule? (Affects T15.)
4. **Audit ledger storage:** What storage backend will be used for the audit ledger? How are hash-chain integrity checks scheduled? (Affects T16, T21.)
5. **Configuration management:** How are configuration changes validated and propagated across Brain instances? Is there a configuration validation service? (Affects T22.)
6. **Multi-tenant RLS testing:** How are RLS policies tested in CI? Are there integration tests that verify tenant isolation at the database level? (Affects T23.)

These questions are planning-level and do not require resolution in this document. They are flagged for the implementation plan and subsequent ADRs.

---

## 7. Document Status

| Item | State |
|---|---|
| Threat model (23 threats) | Complete |
| STRIDE analysis | Complete |
| Component coverage (C1–C14) | Complete |
| Invariant coverage (1–15, including 3a) | Complete |
| Residual risk documentation | Complete |
| Test verification mapping | Complete |
| Runtime code | NOT AUTHORIZED |
| Deployment | NOT AUTHORIZED |