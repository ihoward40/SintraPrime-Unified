# 09 — Certification Matrix: Executor Continuation

**Package:** Executor Continuation Implementation Planning
**Source of truth:** ADR-MC-001 (ACCEPTED, ratified 2026-08-05, merged to main)
**Scope:** PLANNING ONLY — no runtime code, no deployment, no authority activation, no Sigma gate unblock. This document defines the certification matrix that must be satisfied before `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE` may be evaluated for unblocking. It authorizes no implementation, no test execution, and no gate state change. Implementation requires separate ADRs, branches, and authorizations per ADR-MC-001 Section 10.
**Companion documents:**
- `../ADR_MC_001_EXECUTOR_CONTINUATION.md` — source ADR
- `01_IMPLEMENTATION_ARCHITECTURE.md` — component decomposition, phases, technology choices
- `02_COMPONENT_DEPENDENCY_GRAPH.md` — build-time dependency graph, layered build order
- `03_INTERFACE_SPECIFICATIONS.md` — Pydantic v2 models and Protocol interfaces
- `04_STATE_MACHINES.md` — component and lifecycle state machines
- `05_SEQUENCE_DIAGRAMS.md` — runtime protocol sequencing
- `06_THREAT_MODEL.md` — 23-threat model (T1–T23) with STRIDE analysis
- `07_FAILURE_MODE_RECOVERY_MATRIX.md` — failure modes and recovery procedures
- `08_TEST_MATRIX.md` — 396 test cases across 9 categories; CERT-001 through CERT-018
- `10_ROLLOUT_ROLLBACK_PLAN.md` — phased rollout, go/no-go gates, Sigma gate unblock procedure

---

## 1. Document Purpose

This document is the certification blueprint for the executor continuation capability defined by ADR-MC-001. It is a planning artifact only — it authorizes no runtime code, no API changes, no persistence migrations, no test execution, and no deployment. Implementation requires separate ADRs, branches, and authorizations per ADR-MC-001 Section 10.

The document defines the complete set of certification gates that must pass before `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE` may transition from BLOCKED to SATISFIED. It is the authoritative reference for the certification process: what must be verified, what evidence is required, who certifies, how gates are sequenced, and what happens on failure.

The document serves three audiences:

1. **Implementers** — who need to know what each component must demonstrate before it can be certified, and what evidence the certification process will demand.
2. **Certifiers and reviewers** — who need a complete, traceable matrix from certification gates to ADR acceptance criteria (Section 11), invariants (Section 7), required components (Section 9.1), required tests (Section 9.3), and the threat model (Section 6.3 / document 06).
3. **Operators and the Principal** — who need to understand the operational readiness gates and the final authorization steps before the Sigma gate is unblocked.

### 1.1 Planning Status

- ADR-MC-001 is ACCEPTED and merged to main.
- The 14 required components (ADR-MC-001 §9.1) are NOT IMPLEMENTED.
- The implementation is NOT AUTHORIZED. Implementation requires separate ADRs, branches, and authorizations per ADR-MC-001 Section 10.
- The Sigma gate (`SIGMA_LEASE_EXPIRY_CONTINUATION_GATE`) remains BLOCKED. `portal/services/sigma_gate.py` is unchanged; `is_cancellation_blocked()` continues to return `True`.
- This document describes the certification matrix that would be executed IF and WHEN implementation is authorized and completed. It is a plan, not an execution.

### 1.2 Relationship to Sibling Documents

This document is the certification authority layer. It consumes the outputs of the other planning documents:

| Source document | Certification input |
|---|---|
| 01 Implementation Architecture | Component decomposition, phases, technology choices to verify against |
| 02 Component Dependency Graph | Build order and dependency relationships that integration gates must respect |
| 03 Interface Specifications | Interface contracts that component and integration gates must verify |
| 04 State Machines | State transitions that component and integration gates must verify |
| 05 Sequence Diagrams | Protocol sequences that integration gates must verify |
| 06 Threat Model | 23 threats (T1–T23) that security gates must verify are mitigated and tested |
| 07 Failure Mode Recovery Matrix | Failure modes that resilience and operational gates must verify are handled |
| 08 Test Matrix | 396 test cases; CERT-001 through CERT-018 are the test-level certification gates |
| 10 Rollout/Rollback Plan | Phase go/no-go gates, Sigma gate unblock procedure, operational readiness criteria |

### 1.3 Key Constraints

- **No partial certification.** The Sigma gate transitions to SATISFIED only after ALL blocking certification gates pass. No subset of gates is sufficient.
- **No self-certification.** The implementing team proposes evidence; an independent certification authority reviews and certifies. The Principal authorizes the final gate transition.
- **No test-only unblock.** Passing tests is necessary but not sufficient. Certification also requires threat-model acceptance, invariant enforcement verification, documentation completeness, and operational readiness sign-off.
- **Evidence is immutable.** All certification evidence (test results, audit logs, review records, sign-offs) is appended to the immutable audit ledger and never truncated, consistent with ADR-MC-001 invariant 11.
- **Fail-closed on missing evidence.** If evidence for a blocking gate is missing, incomplete, or contested, the gate FAILS. The Sigma gate remains BLOCKED.

---

## 2. Conventions

### 2.1 Certification Gate ID Scheme

| Prefix | Category | Source |
|---|---|---|
| `CG-C##` | Component certification gates | ADR §9.1 (14 components) |
| `CG-INT-##` | Integration certification gates | ADR §2.1–§2.15; document 02 dependency graph |
| `CG-SEC-T##` | Security certification gates (one per threat) | ADR §6.3; document 06 (23 threats) |
| `CG-INV-I##` | Invariant verification gates | ADR §7 (15 invariants + I3a = 16) |
| `CG-AC-##` | Acceptance criteria verification gates | ADR §11 (20 criteria) |
| `CG-PERF-##` | Performance and scalability gates | ADR §2.4 limits; operational requirements |
| `CG-DOC-##` | Documentation completeness gates | ADR §8, §9, §10; planning package |
| `CG-OPS-##` | Operational readiness gates | ADR §2.15; document 10 |

### 2.2 Component IDs

From ADR-MC-001 §9.1 and companion document `02_COMPONENT_DEPENDENCY_GRAPH.md`:

| ID | Component | Side |
|---|---|---|
| C01 | Signed lease token service | Brain |
| C02 | Continuation capability service | Brain |
| C03 | Brain heartbeat endpoint | Brain |
| C04 | Witness statement service | Shared (witness plane) |
| C05 | Executor local state cache | Executor |
| C06 | Revocation stream | Brain (read by executor) |
| C07 | Policy snapshot registry | Brain (read by executor) |
| C08 | Continuation journal store | Executor |
| C09 | Completion receipt service | Executor (verified by Brain) |
| C10 | Reconciliation engine | Brain |
| C11 | Conflict review queue | Brain |
| C12 | Audit event pipeline | Shared (cross-cutting) |
| C13 | Downstream effect identity layer | Downstream |
| C14 | Signed time-anchor service | Brain (consumed by executor) |

### 2.3 Invariant IDs

From ADR-MC-001 §7:

| Inv | Invariant (abbreviated) |
|---|---|
| I1 | No authoritative effects without valid lease |
| I2 | Expired lease cannot authorize continuation or effects |
| I3 | Capability cannot be used before lease expiry or after its own expiry |
| I3a | Only latest-lease capability may be exercised; prior capabilities superseded |
| I4 | Continuation is never the default behavior |
| I5 | Continuation cannot exceed its bounded envelope |
| I6 | Every continuation produces an immutable, signed receipt |
| I7 | Every continuation is reconciled before terminal state |
| I8 | Conflicting results or non-reversible effects never resolve silently |
| I9 | Cross-tenant continuation is impossible |
| I10 | Idempotency preserved across continuation, replay, and normal execution |
| I11 | Authoritative audit storage is complete and never truncated |
| I12 | Policy snapshot validity bounded to exact pinned snapshot |
| I13 | Revocation/cancellation knowledge must be fresh; absence is not permission |
| I14 | Time cannot be manipulated to extend authority |
| I15 | High-risk or irreversible side effects cannot be produced during continuation |

### 2.4 Acceptance Criteria IDs

From ADR-MC-001 §11:

| AC | Criterion (abbreviated) |
|---|---|
| AC1 | Lease lifecycle and continuation capability lifecycle fully specified and separated |
| AC2 | Continuation capability unusable before lease expiry; bounded by time, operations, scope |
| AC3 | Brain outage detection uses ≥2 independent signals including one direct-Brain signal, with grace period |
| AC4 | Witness trust model fully defined: identity, quorum, replay resistance, self-exclusion |
| AC5 | Continuation eligibility criteria explicit; default STOP |
| AC6 | Continuation limits defined with platform and tenant bounds |
| AC7 | Stable external-effect identity defined and used for duplicate suppression |
| AC8 | Replay semantics preserve effect identity; require reconciliation before authorization |
| AC9 | Reconciliation protocol separates result selection, effect reconciliation, compensation, manual review |
| AC10 | Completion receipts mandatory, signed, immutable |
| AC11 | Split-brain handling detects conflicts, freezes effects, routes to manual review |
| AC12 | Audit chain includes all continuation events; authoritative storage never truncated |
| AC13 | Tenant isolation guaranteed throughout continuation and reconciliation |
| AC14 | Recovery protocol defines recovery detection, report collection, reconciliation, policy refresh |
| AC15 | Trusted time, clock skew, monotonic time, signed time anchors specified |
| AC16 | Policy snapshot pinned by hash and bounded by validity time |
| AC17 | Revocation watermark and cache-age rules are fail-closed |
| AC18 | Side effects classified; Class 3 prohibited during continuation |
| AC19 | Threat model, invariants, glossary, implementation prerequisites complete |
| AC20 | Non-goals explicitly exclude implementation, deployment, authority activation |

### 2.5 Threat IDs

From ADR-MC-001 §6.3 (T1–T14) and document 06 (T1–T23, with T15–T23 as implementation-level threats):

| Threat | Description (abbreviated) | Source |
|---|---|---|
| T1 | Executor continues without capability | ADR §6.3 |
| T2 | Executor continues without Brain outage | ADR §6.3 |
| T3 | Executor continues without local state sufficiency | ADR §6.3 |
| T4 | Multiple executors continue same command | ADR §6.3 |
| T5 | Executor produces duplicate external effects | ADR §6.3 |
| T6 | Executor lies about continuation outcome | ADR §6.3 |
| T7 | Brain recovers during continuation | ADR §6.3 |
| T8 | Cross-tenant continuation | ADR §6.3 |
| T9 | Continuation runs unbounded | ADR §6.3 |
| T10 | Stale revocation/cancellation knowledge | ADR §6.3 |
| T11 | Pinned policy exploited | ADR §6.3 |
| T12 | Clock skew/rollback extends authority | ADR §6.3 |
| T13 | Silent continuation | ADR §6.3 |
| T14 | Witness quorum compromised | ADR §6.3 |
| T15 | Key compromise | Document 06 §2.2 |
| T16 | Database corruption | Document 06 §2.2 |
| T17 | Network partition scenarios | Document 06 §2.2 |
| T18 | Clock manipulation (NTP, monotonic discontinuity) | Document 06 §2.2 |
| T19 | Capability token replay | Document 06 §2.2 |
| T20 | Witness collusion | Document 06 §2.2 |
| T21 | Audit ledger tampering | Document 06 §2.2 |
| T22 | Configuration drift | Document 06 §2.2 |
| T23 | Multi-tenant data leakage | Document 06 §2.2 |

### 2.6 Responsible Parties

| Role | Abbreviation | Responsibilities |
|---|---|---|
| Component Owner | CO | The implementing team owning a specific component. Proposes evidence, runs tests, fixes failures. |
| Architecture Review | AR | Architecture review board (Isiah Howard for ADR-MC-001 ratification). Verifies design conformance, invariant enforcement at boundaries, residual risk acceptance. |
| Security Review | SR | Security review team. Verifies threat mitigation, attack-vector testing, STRIDE coverage, key management, RLS enforcement. |
| Certification Authority | CA | Independent certification body (not the implementing team). Reviews all evidence, runs independent verification, issues certification decision. |
| Operations Review | OR | SRE / operations team. Verifies monitoring, alerting, runbooks, incident response, rollback procedures, on-call readiness. |
| Principal | P | Principal authority (per ADR-MC-001 §10). Authorizes the final Sigma gate state transition and the unblock ADR. |

### 2.7 Gate Status Values

| Status | Meaning |
|---|---|
| BLOCKED | Gate not yet evaluated; prerequisites not met or evidence not submitted |
| IN-REVIEW | Evidence submitted; certification authority reviewing |
| PASSED | Gate satisfied; evidence accepted and recorded |
| FAILED | Gate not satisfied; evidence rejected or verification failed |
| WAIVED | Non-blocking gate intentionally waived with documented justification and AR approval |

---

## 3. Certification Gate Summary

| Category | Gate count | Blocking | Non-blocking |
|---|---|---|---|
| Component certification (CG-C##) | 14 | 14 | 0 |
| Integration certification (CG-INT-##) | 12 | 12 | 0 |
| Security certification (CG-SEC-T##) | 23 | 23 | 0 |
| Invariant verification (CG-INV-I##) | 16 | 16 | 0 |
| Acceptance criteria verification (CG-AC-##) | 20 | 20 | 0 |
| Performance and scalability (CG-PERF-##) | 8 | 6 | 2 |
| Documentation completeness (CG-DOC-##) | 7 | 7 | 0 |
| Operational readiness (CG-OPS-##) | 8 | 7 | 1 |
| **Total** | **108** | **105** | **3** |

All 105 blocking gates must PASS before the Sigma gate may be evaluated for unblocking. The 3 non-blocking gates may be WAIVED with documented justification and Architecture Review approval, but waiver does not reduce the evidence required for blocking gates.

---

## 4. Component Certification Gates (CG-C01 through CG-C14)

Each of the 14 required components from ADR-MC-001 §9.1 has a dedicated certification gate. A component is certified only when its unit tests pass, its interface conforms to document 03, its state machine conforms to document 04, and it enforces the invariants assigned to it at its boundary.

### CG-C01 — Signed Lease Token Service

| Field | Value |
|---|---|
| Gate ID | CG-C01 |
| Component | C01 — Signed lease token service (Brain) |
| Description | Certify that the lease token service correctly issues, renews, revokes, and validates signed lease tokens with all required fields, and that lease expiry and revocation immediately revoke all authority. |
| Evidence required | (1) Unit test results: UT-C01-* all pass. (2) Required test results: RT-01.1–RT-01.10 pass. (3) Interface conformance report against document 03 §C01. (4) State machine conformance report against document 04 §4.1 (LEASE ISSUED → ACTIVE → RENEWED → EXPIRED). (5) Token signature verification report. (6) Audit event emission report (lease issuance, renewal, expiry, revocation with causation links). |
| Verification method | Automated test execution (pytest, SQLite backend); independent CA review of test artifacts and interface conformance; signature verification spot-check. |
| Pass criteria | All UT-C01-* pass; all RT-01.* pass; token signature verifies for issued and renewed tokens; expired and revoked tokens rejected by all validators; audit events recorded with causation links; interface matches document 03; state machine matches document 04. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), AR (design conformance) |
| Invariants enforced | I1, I2 |
| ADR refs | §2.1.1–§2.1.3, §9.1 |
| Test refs | UT-C01-*, RT-01.*, CERT-008 |

### CG-C02 — Continuation Capability Service

| Field | Value |
|---|---|
| Gate ID | CG-C02 |
| Component | C02 — Continuation capability service (Brain) |
| Description | Certify that the continuation capability service issues, validates, and revokes signed continuation capabilities with all 15 fields, that capabilities are unusable before lease expiry and after their own expiry, that capability supersession is enforced (only latest-lease capability exercisable), and that capability bounds (duration, operations, scope) are enforced. |
| Evidence required | (1) Unit test results: UT-C02-* all pass. (2) Required test results: RT-02.1–RT-02.10, RT-06.1–RT-06.10 pass. (3) Interface conformance report against document 03 §C02. (4) Capability field completeness report (all 15 fields present and valid). (5) Capability supersession report (prior capabilities rejected even with later not_valid_after). (6) Bounds enforcement report (duration, operations, concurrency, rate, validity). (7) Platform maximum enforcement report. |
| Verification method | Automated test execution; independent CA review; capability token signature verification; supersession and replay attack verification. |
| Pass criteria | All UT-C02-* pass; all RT-02.*, RT-06.* pass; capability rejected before not_valid_before and after not_valid_after; capability rejected for wrong command/executor/tenant; superseded capabilities rejected; all bounds enforced; platform maximums not bypassed; break-glass reduces but never increases. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), AR (design conformance) |
| Invariants enforced | I3, I3a, I4, I5 |
| ADR refs | §2.1.4, §2.4, §9.1 |
| Test refs | UT-C02-*, RT-02.*, RT-06.*, CERT-008 |

### CG-C03 — Brain Heartbeat Endpoint

| Field | Value |
|---|---|
| Gate ID | CG-C03 |
| Component | C03 — Brain heartbeat endpoint (Brain) |
| Description | Certify that the heartbeat endpoint allows executors to detect Brain availability, that missed heartbeats are counted toward the outage detection signal, and that the heartbeat channel carries signed time anchors and recovery notifications. |
| Evidence required | (1) Unit test results: UT-C03-* all pass. (2) Required test results: RT-03.1, RT-03.2, RT-03.7 pass. (3) Interface conformance report against document 03 §C03. (4) Heartbeat miss threshold enforcement report. (5) Recovery notification delivery report. |
| Verification method | Automated test execution; CA review of heartbeat threshold logic and recovery notification path. |
| Pass criteria | All UT-C03-* pass; heartbeat misses counted correctly; recovery notification delivered via heartbeat channel; threshold configurable per tenant within platform bounds. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| Invariants enforced | I4 |
| ADR refs | §2.2.1, §2.6.1, §9.1 |
| Test refs | UT-C03-*, RT-03.*, CERT-008 |

### CG-C04 — Witness Statement Service

| Field | Value |
|---|---|
| Gate ID | CG-C04 |
| Component | C04 — Witness statement service (Shared / witness plane) |
| Description | Certify that the witness statement service publishes and validates signed witness statements with identity, quorum, replay resistance, self-exclusion, tenant partitioning, and compromised-witness handling, per the BFT or documented CFT fault model. |
| Evidence required | (1) Unit test results: UT-C04-* all pass. (2) Required test results: RT-04.1–RT-04.12 pass. (3) Interface conformance report against document 03 §C04. (4) Fault model documentation (BFT or explicitly-documented CFT with upgrade plan). (5) Quorum calculation report (N >= 3f+1, quorum >= 2f+1 for BFT; or N >= 2f+1, quorum >= f+1 for CFT with witness_quorum_size < N). (6) Self-exclusion enforcement report. (7) Compromised/revoked witness handling report. |
| Verification method | Automated test execution; CA review of fault model documentation; SR review of witness identity and key revocation. |
| Pass criteria | All UT-C04-* pass; all RT-04.* pass; witness identity validated (control-plane only); quorum enforced; replay resistance via nonce; max age enforced; tenant partitioning enforced; self-exclusion enforced; revoked witness statements rejected; CFT model explicitly documented as not BFT if used. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (security), AR (fault model acceptance) |
| Invariants enforced | I4 |
| ADR refs | §2.2.4, §9.1 |
| Test refs | UT-C04-*, RT-04.*, CERT-008 |

### CG-C05 — Executor Local State Cache

| Field | Value |
|---|---|
| Gate ID | CG-C05 |
| Component | C05 — Executor local state cache (Executor) |
| Description | Certify that the executor local state cache stores inputs, configuration, and prior step outputs with checksums, that the self-check against the task manifest correctly determines local state sufficiency, and that the default decision is STOP. |
| Evidence required | (1) Unit test results: UT-C05-* all pass. (2) Required test results: RT-05.7, RT-05.14 pass. (3) Interface conformance report against document 03 §C05. (4) Cache checksum verification report. (5) Self-check report (insufficient state → safe-hold). (6) Default-STOP verification report. (7) Outage record persistence report (durable across process restart). |
| Verification method | Automated test execution; CA review of self-check logic and cache durability. |
| Pass criteria | All UT-C05-* pass; self-check fails on insufficient state → safe-hold; default decision is STOP; outage record persisted with all required fields (timestamp, signals, lease token fingerprint, signed time anchor, monotonic_outage_start, wall_outage_declared_at, grace_period_end); cache corruption detected by checksum. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| Invariants enforced | I4 |
| ADR refs | §2.2.2, §2.3, §9.1 |
| Test refs | UT-C05-*, RT-05.*, CERT-008 |

### CG-C06 — Revocation Stream

| Field | Value |
|---|---|
| Gate ID | CG-C06 |
| Component | C06 — Revocation stream (Brain, read by executor) |
| Description | Certify that the revocation stream publishes signed, monotonic, tenant-partitioned revocation/cancellation entries with sequence numbers, that the executor records the highest observed watermark, and that fail-closed behavior is enforced when the watermark is missing, stale, or below the capability requirement. |
| Evidence required | (1) Unit test results: UT-C06-* all pass. (2) Required test results: RT-07.1–RT-07.6 pass. (3) Interface conformance report against document 03 §C06. (4) Watermark enforcement report. (5) Cache-age enforcement report (max_revocation_cache_age). (6) Fail-closed verification report (missing/stale/below-required watermark → continuation forbidden). (7) Revocation-during-outage stop report. (8) Cancellation-observed stop report. |
| Verification method | Automated test execution; CA review of watermark and cache-age logic; SR review of fail-closed enforcement. |
| Pass criteria | All UT-C06-* pass; all RT-07.* pass; watermark enforced; cache age enforced; fail-closed on missing/stale/below-required watermark; revocation during outage causes immediate stop; cancellation at or before watermark forbids continuation; high-risk classes default to STOP. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (security) |
| Invariants enforced | I13 |
| ADR refs | §2.10, §9.1 |
| Test refs | UT-C06-*, RT-07.*, CERT-008 |

### CG-C07 — Policy Snapshot Registry

| Field | Value |
|---|---|
| Gate ID | CG-C07 |
| Component | C07 — Policy snapshot registry (Brain, read by executor) |
| Description | Certify that the policy snapshot registry pins and validates policy snapshots by hash, that the executor trusts only the exact pinned snapshot, that policy_snapshot_not_valid_after is enforced, and that the emergency deny channel is honored. |
| Evidence required | (1) Unit test results: UT-C07-* all pass. (2) Required test results: RT-02.9, RT-05.09 pass. (3) Interface conformance report against document 03 §C07. (4) Snapshot hash verification report. (5) not_valid_after enforcement report. (6) Emergency deny channel report. (7) Pinned-snapshot-cannot-authorize-unpermitted-operations report. |
| Verification method | Automated test execution; CA review of hash pinning and validity bounds; SR review of emergency deny channel. |
| Pass criteria | All UT-C07-* pass; snapshot hash mismatch → continuation forbidden; not_valid_after enforced; emergency deny channel honored; pinned snapshot cannot authorize operations not in permitted_operation_ids; policy_silence_threshold signal exercised. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (security) |
| Invariants enforced | I12 |
| ADR refs | §2.11, §9.1 |
| Test refs | UT-C07-*, RT-02.09, RT-05.09, CERT-008 |

### CG-C08 — Continuation Journal Store

| Field | Value |
|---|---|
| Gate ID | CG-C08 |
| Component | C08 — Continuation journal store (Executor) |
| Description | Certify that the continuation journal store records every operation attempted with input, output, success/failure, timestamp, and stable external-effect identity, that the journal is persisted to durable storage before any external effect is produced, and that the journal is included in the completion report as an encrypted blob. |
| Evidence required | (1) Unit test results: UT-C08-* all pass. (2) Required test results: RT-08.* (idempotency tests exercising journal) pass. (3) Interface conformance report against document 03 §C08. (4) Journal durability report (persisted before external effects). (5) Journal completeness report (every operation recorded with stable effect identity). (6) Encrypted blob inclusion report. |
| Verification method | Automated test execution; CA review of journal durability and completeness; SR review of encryption. |
| Pass criteria | All UT-C08-* pass; journal persisted before external effects; every operation recorded with (command_id, operation_id, side_effect_slot); journal included as encrypted blob in completion report; journal never truncated. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (encryption review) |
| Invariants enforced | I10 |
| ADR refs | §2.5.3, §9.1 |
| Test refs | UT-C08-*, RT-08.*, CERT-008 |

### CG-C09 — Completion Receipt Service

| Field | Value |
|---|---|
| Gate ID | CG-C09 |
| Component | C09 — Completion receipt service (Executor, verified by Brain) |
| Description | Certify that the completion receipt service generates and verifies immutable, signed continuation receipts with all required fields, that receipts are mandatory, and that tampered or forged receipts are rejected. |
| Evidence required | (1) Unit test results: UT-C09-* all pass. (2) Required test results: RT-09.* pass. (3) Interface conformance report against document 03 §C09. (4) Receipt signature verification report. (5) Receipt immutability report. (6) Tampered-receipt rejection report. (7) Forged-receipt rejection report (non-registered executor key). |
| Verification method | Automated test execution; CA review of signature and immutability; SR review of key management. |
| Pass criteria | All UT-C09-* pass; all RT-09.* pass; every continuation produces a signed receipt; receipt signature verifies; tampered receipt rejected; forged receipt (wrong key) rejected; receipt includes all required fields (command_id, executor_id, continuation_id, capability_id, final_state, operations_performed, result_digest, evidence_refs, continuation_journal, audit_receipt_id, outage_evidence, revocation_watermark_observed). |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (key management) |
| Invariants enforced | I6 |
| ADR refs | §2.6.2, §9.1 |
| Test refs | UT-C09-*, RT-09.*, CERT-008 |

### CG-C10 — Reconciliation Engine

| Field | Value |
|---|---|
| Gate ID | CG-C10 |
| Component | C10 — Reconciliation engine (Brain) |
| Description | Certify that the reconciliation engine performs result selection, effect reconciliation, compensation, and manual-review routing per ADR §2.6.3, that it detects conflicts and divergent results, that it blocks replay while continuations are unreconciled, and that replay uses root_command_id for effect identities. |
| Evidence required | (1) Unit test results: UT-C10-* all pass. (2) Required test results: RT-10.*, RT-11.* pass. (3) Interface conformance report against document 03 §C10. (4) Result selection report (single, duplicate-agreed, divergent, invalid). (5) Effect reconciliation report (duplicate, new, conflict, non-reversible). (6) Compensation report (reversible/idempotent only; irreversible not auto-compensated). (7) Manual-review routing report. (8) Replay authorization report (blocks while unreconciled; root_command_id used). (9) Classification report (VALID_CONTINUATION, VALID_BUT_RECONCILED, INVALID_CONTINUATION, CONFLICTING_REPORTS, MANUAL_REVIEW_REQUIRED). |
| Verification method | Automated test execution; CA review of all four reconciliation concerns; AR review of result selection tie-breaker (trusted comparable signed time, lowest executor_id). |
| Pass criteria | All UT-C10-* pass; all RT-10.*, RT-11.* pass; result selection by timestamp only when effects provably idempotent and equivalent; divergent results → MANUAL_REVIEW_REQUIRED; effect conflicts frozen; compensation only for reversible/idempotent; replay blocked while unreconciled; replay uses root_command_id; all five classifications produced correctly. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), AR (reconciliation rules) |
| Invariants enforced | I7, I8, I10 |
| ADR refs | §2.6, §2.7, §2.12, §9.1 |
| Test refs | UT-C10-*, RT-10.*, RT-11.*, CERT-008 |

### CG-C11 — Conflict Review Queue

| Field | Value |
|---|---|
| Gate ID | CG-C11 |
| Component | C11 — Conflict review queue (Brain) |
| Description | Certify that the conflict review queue surfaces conflicting continuation results for operator resolution, that the command remains in MANUAL_REVIEW_REQUIRED until resolved, and that no silent conflict resolution is permitted. |
| Evidence required | (1) Unit test results: UT-C11-* all pass. (2) Required test results: RT-11.* pass. (3) Interface conformance report against document 03 §C11. (4) Conflict enqueue report (from C10). (5) Manual-review-hold report (command remains until operator resolves). (6) Resolution audit report (no silent resolution). |
| Verification method | Automated test execution; CA review of queue and resolution audit; OR review of operator workflow. |
| Pass criteria | All UT-C11-* pass; all RT-11.* pass; conflicts enqueued from C10; command remains in MANUAL_REVIEW_REQUIRED until operator resolves; resolution recorded as audit event; no silent conflict resolution. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), OR (operator workflow) |
| Invariants enforced | I8 |
| ADR refs | §2.6.3.4, §2.12.2, §9.1 |
| Test refs | UT-C11-*, RT-11.*, CERT-008 |

### CG-C12 — Audit Event Pipeline

| Field | Value |
|---|---|
| Gate ID | CG-C12 |
| Component | C12 — Audit event pipeline (Shared, cross-cutting) |
| Description | Certify that the audit event pipeline appends all continuation events to an immutable, append-only, hash-chained audit ledger that is never truncated, that projection APIs may truncate but the authoritative ledger does not, and that the ledger records all ADR §2.13 events. |
| Evidence required | (1) Unit test results: UT-C12-* all pass. (2) Required test results: RT-14.* pass. (3) Interface conformance report against document 03 §C12. (4) Append-only enforcement report (no update/delete at storage layer). (5) Hash-chain integrity report (gaps detected). (6) Completeness report (all §2.13 events recorded: lease expiry, capability issuance, outage declaration, eligibility decision, each operation, completion, recovery detection, reconciliation, terminal state). (7) Projection-truncation report (projection may truncate; ledger does not). (8) Tampering detection report. |
| Verification method | Automated test execution; CA review of append-only and hash-chain; SR review of tampering detection and access controls. |
| Pass criteria | All UT-C12-* pass; all RT-14.* pass; ledger append-only (update/delete rejected); hash-chain gaps detected; all §2.13 events recorded; projection may truncate with metadata but ledger never truncated; tampering detected and flagged as security event. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (tampering detection) |
| Invariants enforced | I11 |
| ADR refs | §2.13, §9.1 |
| Test refs | UT-C12-*, RT-14.*, CERT-008, CERT-010 |

### CG-C13 — Downstream Effect Identity Layer

| Field | Value |
|---|---|
| Gate ID | CG-C13 |
| Component | C13 — Downstream effect identity layer (Downstream) |
| Description | Certify that the downstream effect identity layer validates (command_id, operation_id, side_effect_slot) before applying effects, that it validates the signed continuation capability token and matching outage evidence (not the expired lease), that it rejects duplicate effects, and that it enforces Class 3 prohibition and tenant scope. |
| Evidence required | (1) Unit test results: UT-C13-* all pass. (2) Required test results: RT-08.*, RT-16.* pass. (3) Interface conformance report against document 03 §C13. (4) Stable effect identity validation report. (5) Duplicate suppression report. (6) Capability token + outage evidence validation report. (7) Class 3 prohibition report. (8) Tenant scope validation report. (9) Downstream compliance list (all downstream systems accepting continuation effects implement C13). |
| Verification method | Automated test execution; CA review of effect identity and duplicate suppression; SR review of capability and outage evidence validation; AR review of downstream compliance list. |
| Pass criteria | All UT-C13-* pass; all RT-08.*, RT-16.* pass; effects without valid capability + outage evidence rejected; duplicate (command_id, operation_id, side_effect_slot) rejected; Class 3 effects rejected during continuation; tenant scope validated; all downstream systems accepting continuation effects implement C13 (documented). |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (security), AR (downstream compliance) |
| Invariants enforced | I10, I15 |
| ADR refs | §2.1.4, §2.5, §2.9, §9.1 |
| Test refs | UT-C13-*, RT-08.*, RT-16.*, CERT-008, CERT-016 |

### CG-C14 — Signed Time-Anchor Service

| Field | Value |
|---|---|
| Gate ID | CG-C14 |
| Component | C14 — Signed time-anchor service (Brain, consumed by executor) |
| Description | Certify that the signed time-anchor service issues and validates signed wall-clock anchors, that monotonic time is used for duration measurement, that clock skew and rollback tolerances are enforced, and that the executor stops on monotonic clock discontinuity or wall-clock drift beyond tolerance. |
| Evidence required | (1) Unit test results: UT-C14-* all pass. (2) Required test results: RT-15.*, RT-03.9 pass. (3) Interface conformance report against document 03 §C14. (4) Signed anchor verification report. (5) Monotonic clock enforcement report (duration not extendable by rollback). (6) Skew tolerance report (max_clock_skew_tolerance). (7) Rollback tolerance report (max_clock_rollback_tolerance). (8) Monotonic discontinuity stop report. (9) Timezone-immunity report (UTC comparison). |
| Verification method | Automated test execution; CA review of time authority; SR review of clock manipulation defenses. |
| Pass criteria | All UT-C14-* pass; all RT-15.* pass; signed anchors verified; monotonic time used for duration; skew beyond tolerance → security event and stop; rollback beyond tolerance → rejected; monotonic discontinuity (restart/suspend) → stop; timezone changes do not affect not_valid_before/not_valid_after comparison; capability validity evaluated against signed Brain anchors. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (clock manipulation) |
| Invariants enforced | I14 |
| ADR refs | §2.8, §9.1 |
| Test refs | UT-C14-*, RT-15.*, RT-03.9, CERT-008, CERT-015 |

---

## 5. Integration Certification Gates (CG-INT-01 through CG-INT-12)

Integration gates verify that components interact correctly across their boundaries, following the dependency graph in document 02 and the sequence diagrams in document 05. These gates run on PostgreSQL (disposable) with real component interactions.

### CG-INT-01 — Lease and Capability Lifecycle Integration

| Field | Value |
|---|---|
| Gate ID | CG-INT-01 |
| Description | Certify that C01 (lease) and C02 (capability) integrate correctly: lease issuance triggers capability issuance, renewal rotates both token and capability, expiry revokes lease but capability becomes usable at not_valid_before, and supersession is enforced across both. |
| Evidence required | INT-001, INT-002 test results pass; cross-component audit event chain report. |
| Verification method | Automated integration test execution (PostgreSQL); CA review of interaction traces. |
| Pass criteria | INT-001, INT-002 pass; lease and capability lifecycles synchronized; supersession enforced across both; audit chain complete across both components. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §2.1.1–§2.1.4 |
| Test refs | INT-001, INT-002, CERT-001 |

### CG-INT-02 — Outage Detection Integration

| Field | Value |
|---|---|
| Gate ID | CG-INT-02 |
| Description | Certify that C03 (heartbeat), C04 (witness), C01 (lease rejection), C07 (policy silence), and C14 (time anchor) integrate to produce outage declarations following the two-signal rule, direct-Brain-signal requirement, and grace period. |
| Evidence required | INT-003, INT-004 test results pass; outage declaration record report with all required fields. |
| Verification method | Automated integration test execution; CA review of signal combination logic. |
| Pass criteria | INT-003, INT-004 pass; two-signal rule enforced; direct-Brain signal required; grace period enforced; outage record persisted with all fields. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §2.2.1–§2.2.3 |
| Test refs | INT-003, INT-004, CERT-001 |

### CG-INT-03 — Eligibility Decision Integration

| Field | Value |
|---|---|
| Gate ID | CG-INT-03 |
| Description | Certify that the eligibility decision integrates C01, C02, C03, C04, C05, C06, C07, and C14 to evaluate all 11 eligibility criteria and default to STOP. |
| Evidence required | INT-005 test result passes; eligibility decision event audit report. |
| Verification method | Automated integration test execution; CA review of all 11 criteria evaluation. |
| Pass criteria | INT-005 passes; all 11 criteria evaluated; default STOP; each criterion failure produces correct rejection reason. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §2.3 |
| Test refs | INT-005, CERT-001 |

### CG-INT-04 — Continuation Execution and Journal Integration

| Field | Value |
|---|---|
| Gate ID | CG-INT-04 |
| Description | Certify that C05 (state cache), C08 (journal), C13 (effect identity), and C02 (capability bounds) integrate to execute bounded continuation with journaled operations and stable effect identities. |
| Evidence required | INT-006, INT-007 test results pass; continuation journal completeness report. |
| Verification method | Automated integration test execution; CA review of journal and effect identity. |
| Pass criteria | INT-006, INT-007 pass; operations bounded; journal persisted before effects; stable effect identity used; duplicate suppression works. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §2.4, §2.5 |
| Test refs | INT-006, INT-007, CERT-001 |

### CG-INT-05 — Completion Reporting Integration

| Field | Value |
|---|---|
| Gate ID | CG-INT-05 |
| Description | Certify that C09 (receipt), C08 (journal), and C12 (audit) integrate to produce mandatory, signed completion reports with all required fields within the completion_report_deadline. |
| Evidence required | INT-008 test result passes; completion report field completeness report. |
| Verification method | Automated integration test execution; CA review of report completeness and deadline. |
| Pass criteria | INT-008 passes; report submitted within deadline; all fields present; receipt signed; journal included as encrypted blob; audit event recorded. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §2.6.2 |
| Test refs | INT-008, CERT-001 |

### CG-INT-06 — Reconciliation Integration

| Field | Value |
|---|---|
| Gate ID | CG-INT-06 |
| Description | Certify that C10 (reconciliation), C11 (conflict queue), C13 (effect identity), and C12 (audit) integrate to perform all four reconciliation concerns and route conflicts to manual review. |
| Evidence required | INT-009 through INT-013 test results pass; reconciliation classification report. |
| Verification method | Automated integration test execution; CA review of all four concerns; AR review of result selection rules. |
| Pass criteria | INT-009–INT-013 pass; result selection, effect reconciliation, compensation, manual review all performed; classifications correct; conflicts enqueued; no silent resolution. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), AR (reconciliation rules) |
| ADR refs | §2.6.3 |
| Test refs | INT-009–INT-013, CERT-001 |

### CG-INT-07 — Split-Brain Detection and Resolution Integration

| Field | Value |
|---|---|
| Gate ID | CG-INT-07 |
| Description | Certify that C10, C11, C13, C09, C14, and C12 integrate to detect split-brain (multiple continuation reports for the same command_id with different continuation_id values), freeze effects, and route to manual review. |
| Evidence required | CHS-007, CHS-008 test results pass; split-brain detection and freeze report. |
| Verification method | Automated chaos test execution; CA review of conflict detection and freeze. |
| Pass criteria | CHS-007, CHS-008 pass; split-brain detected; effects frozen; manual review routed; no silent resolution. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §2.12 |
| Test refs | CHS-007, CHS-008, CERT-003 |

### CG-INT-08 — Recovery Protocol Integration

| Field | Value |
|---|---|
| Gate ID | CG-INT-08 |
| Description | Certify that the full recovery protocol (ADR §2.15) integrates all components: recovery detection, in-progress operation atomicity, report collection, reconciliation, conflict freeze, manual review queue, replay authorization, policy refresh, audit completion, and gate evaluation. |
| Evidence required | INT-008, RES-013 test results pass; full recovery protocol end-to-end report. |
| Verification method | Automated integration and resilience test execution; CA review of full protocol; OR review of operational steps. |
| Pass criteria | INT-008, RES-013 pass; all 10 recovery protocol steps executed in order; operation atomicity rule enforced (committed finished, uncommitted aborted, never both); reports collected within deadline; reconciliation complete; policy refreshed; audit completed. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), OR (operational steps) |
| ADR refs | §2.15 |
| Test refs | INT-008, RES-013, CERT-001 |

### CG-INT-09 — Replay Authorization Integration

| Field | Value |
|---|---|
| Gate ID | CG-INT-09 |
| Description | Certify that replay authorization integrates C10, C01, C13, and C12: replay blocked while continuations unreconciled, replay uses new lease and execution identity but root_command_id for effect identities, and original command marked REPLAYED. |
| Evidence required | INT-013, REC-001 through REC-007 test results pass; replay effect identity report. |
| Verification method | Automated integration and replay test execution; CA review of root_command_id usage. |
| Pass criteria | INT-013, REC-001–REC-007 pass; replay blocked while unreconciled; replay uses root_command_id; dedup works against original/continuation effects; original command marked REPLAYED with causation link. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §2.7 |
| Test refs | INT-013, REC-001–REC-007, CERT-004 |

### CG-INT-10 — Revocation and Policy Integration

| Field | Value |
|---|---|
| Gate ID | CG-INT-10 |
| Description | Certify that C06 (revocation stream), C07 (policy snapshot), and C02 (capability) integrate to enforce revocation watermark, cache age, policy snapshot pinning, and emergency deny channel. |
| Evidence required | INT-014, INT-015 test results pass; revocation and policy enforcement report. |
| Verification method | Automated integration test execution; CA review of watermark and snapshot integration. |
| Pass criteria | INT-014, INT-015 pass; watermark enforced across C06 and C02; cache age enforced; policy snapshot hash verified; emergency deny channel honored. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (security) |
| ADR refs | §2.10, §2.11 |
| Test refs | INT-014, INT-015, CERT-001 |

### CG-INT-11 — Tenant Isolation Integration

| Field | Value |
|---|---|
| Gate ID | CG-INT-11 |
| Description | Certify that tenant isolation is maintained across all components for the full lifecycle: tenant-scoped capabilities, revocation streams, witness statements, audit events, journals, and reports; cross-tenant continuation treated as security event. |
| Evidence required | INT-018, MT-001 through MT-012 test results pass; tenant isolation report. |
| Verification method | Automated integration and multi-tenant test execution; CA review; SR review of RLS enforcement. |
| Pass criteria | INT-018, MT-001–MT-012 pass; no cross-tenant data access; RLS enforced; cross-tenant continuation rejected as security event; all tenant-scoped resources isolated. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (RLS) |
| ADR refs | §2.14 |
| Test refs | INT-018, MT-001–MT-012, CERT-011 |

### CG-INT-12 — Side-Effect Class Enforcement Integration

| Field | Value |
|---|---|
| Gate ID | CG-INT-12 |
| Description | Certify that C02 (capability continuation_class), C13 (downstream effect identity), C10 (reconciliation), and C11 (conflict queue) integrate to enforce side-effect class rules: Class 0–2 permitted under conditions, Class 3 prohibited during continuation. |
| Evidence required | INT-017, RT-16.* test results pass; class enforcement report. |
| Verification method | Automated integration test execution; CA review of class enforcement across components. |
| Pass criteria | INT-017, RT-16.* pass; Class 0 permitted with capability and journal; Class 1 permitted with rollback plan; Class 2 permitted with downstream duplicate suppression; Class 3 prohibited and rejected as security event. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (security) |
| ADR refs | §2.9 |
| Test refs | INT-017, RT-16.*, CERT-016 |

---

## 6. Security Certification Gates (CG-SEC-T01 through CG-SEC-T23)

Each of the 23 threats from the threat model (document 06) has a dedicated security certification gate. A threat is certified only when its mitigation controls are implemented, its test verifications pass, and its residual risk is documented and accepted by the architecture review.

### CG-SEC-T01 — Executor Continues Without Capability

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T01 |
| Threat | T1 — Executor continues without capability (Medium / Critical) |
| Description | Certify that an executor cannot continue without a valid, signed continuation capability, that downstream systems validate the capability token (not the expired lease), and that outage evidence is bound to the capability. |
| Evidence required | SEC-004, SEC-005, SEC-006 test results pass; RT-02.* pass; C13 downstream validation report; residual risk acceptance (AR sign-off). |
| Verification method | Automated security test execution (negative tests asserting rejection); SR review of capability validation at downstream boundary. |
| Pass criteria | SEC-004, SEC-005, SEC-006 pass; RT-02.* pass; executor without capability rejected; downstream validates capability + outage evidence; residual risk documented and accepted. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), SR (security review), CA (certification), AR (residual risk acceptance) |
| ADR refs | §2.1.4, §6.3 |
| Test refs | SEC-004, SEC-005, SEC-006, RT-02.*, CERT-012 |

### CG-SEC-T02 — Executor Continues Without Brain Outage

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T02 |
| Threat | T2 — Executor continues without Brain outage (Medium / High) |
| Description | Certify that continuation cannot occur without a declared Brain outage satisfying the two-signal rule, direct-Brain-signal requirement, and grace period. |
| Evidence required | SEC-019, SEC-021, SEC-022 test results pass; RT-03.* pass; outage detection control report. |
| Verification method | Automated security test execution; SR review of signal combination and grace period. |
| Pass criteria | SEC-019, SEC-021, SEC-022 pass; RT-03.* pass; single signal insufficient; witnesses alone insufficient; direct-Brain signal required; grace period enforced. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), SR (security review), CA (certification) |
| ADR refs | §2.2.2, §6.3 |
| Test refs | SEC-019, SEC-021, SEC-022, RT-03.*, CERT-012 |

### CG-SEC-T03 — Executor Continues Without Local State Sufficiency

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T03 |
| Threat | T3 — Executor continues without local state sufficiency (Medium / High) |
| Description | Certify that the self-check against the task manifest prevents continuation when required inputs or deterministic path are unavailable. |
| Evidence required | RT-05.7 test result passes; self-check failure → safe-hold report. |
| Verification method | Automated test execution; CA review of self-check logic. |
| Pass criteria | RT-05.7 passes; insufficient state → safe-hold; no continuation attempted. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §2.3, §6.3 |
| Test refs | RT-05.7, CERT-012 |

### CG-SEC-T04 — Multiple Executors Continue Same Command

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T04 |
| Threat | T4 — Multiple executors continue same command (Low / Critical) |
| Description | Certify that lease exclusivity, distinct per-executor capabilities, conflict detection, and manual review prevent uncontrolled split-brain continuation. |
| Evidence required | RT-11.* test results pass; CHS-007, CHS-008 pass; conflict detection and freeze report. |
| Verification method | Automated chaos test execution; SR review of conflict detection. |
| Pass criteria | RT-11.* pass; CHS-007, CHS-008 pass; multiple reports detected; conflicts frozen; manual review routed; no silent resolution. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), SR (security review), CA (certification) |
| ADR refs | §2.12, §6.3 |
| Test refs | RT-11.*, CHS-007, CHS-008, CERT-003, CERT-012 |

### CG-SEC-T05 — Executor Produces Duplicate External Effects

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T05 |
| Threat | T5 — Executor produces duplicate external effects (Medium / High) |
| Description | Certify that stable (command_id, operation_id, side_effect_slot) identity and downstream duplicate suppression prevent duplicate external effects across normal execution, continuation, and replay. |
| Evidence required | SEC-009, SEC-010 test results pass; RT-08.* pass; C13 duplicate suppression report. |
| Verification method | Automated security test execution; SR review of duplicate suppression layers. |
| Pass criteria | SEC-009, SEC-010 pass; RT-08.* pass; duplicate effects rejected by C13; root_command_id used for replay identity. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), SR (security review), CA (certification) |
| ADR refs | §2.5, §6.3 |
| Test refs | SEC-009, SEC-010, RT-08.*, CERT-012 |

### CG-SEC-T06 — Executor Lies About Continuation Outcome

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T06 |
| Threat | T6 — Executor lies about continuation outcome (Low / High) |
| Description | Certify that signed receipts, continuation journals, result digests, and the audit chain prevent false continuation reports. |
| Evidence required | SEC-028, SEC-029, SEC-030, SEC-031 test results pass; RT-09.* pass; tampered receipt rejection report. |
| Verification method | Automated security test execution; SR review of receipt signing and audit cross-check. |
| Pass criteria | SEC-028–SEC-031 pass; RT-09.* pass; tampered receipt rejected; false report detected by audit cross-check. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), SR (security review), CA (certification) |
| ADR refs | §2.6.2, §2.13, §6.3 |
| Test refs | SEC-028–SEC-031, RT-09.*, CERT-012 |

### CG-SEC-T07 — Brain Recovers During Continuation

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T07 |
| Threat | T7 — Brain recovers during continuation (Medium / Medium) |
| Description | Certify that the recovery protocol stops active continuations, applies the operation atomicity rule, and reconciles all reports. |
| Evidence required | RT-13.* test results pass; RES-013 passes; recovery atomicity report. |
| Verification method | Automated resilience test execution; CA review of atomicity rule. |
| Pass criteria | RT-13.* pass; RES-013 passes; active continuations stopped; committed operations finished, uncommitted aborted, never both; reports reconciled. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §2.12.2, §2.15, §6.3 |
| Test refs | RT-13.*, RES-013, CERT-012 |

### CG-SEC-T08 — Cross-Tenant Continuation

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T08 |
| Threat | T8 — Cross-tenant continuation (Low / Critical) |
| Description | Certify that tenant-scoped capabilities, tenant isolation enforcement, and security event logging prevent cross-tenant continuation. |
| Evidence required | SEC-011, SEC-012, SEC-013, SEC-014 test results pass; RT-12.* pass; cross-tenant rejection report. |
| Verification method | Automated security test execution; SR review of tenant scoping. |
| Pass criteria | SEC-011–SEC-014 pass; RT-12.* pass; cross-tenant capability rejected; security event logged. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), SR (security review), CA (certification) |
| ADR refs | §2.14, §6.3 |
| Test refs | SEC-011–SEC-014, RT-12.*, CERT-011, CERT-012 |

### CG-SEC-T09 — Continuation Runs Unbounded

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T09 |
| Threat | T9 — Continuation runs unbounded (Low / High) |
| Description | Certify that capability time bounds, operation count limits, concurrency limits, and per-tenant rate limits prevent unbounded continuation. |
| Evidence required | RT-06.* test results pass; SEC-023, SEC-024 pass; bounds enforcement report. |
| Verification method | Automated test execution; SR review of bounds and rate limits. |
| Pass criteria | RT-06.* pass; SEC-023, SEC-024 pass; duration, operation, concurrency, rate, and validity bounds all enforced; monotonic clock prevents extension. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), SR (security review), CA (certification) |
| ADR refs | §2.4, §6.3 |
| Test refs | RT-06.*, SEC-023, SEC-024, CERT-012 |

### CG-SEC-T10 — Stale Revocation/Cancellation Knowledge

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T10 |
| Threat | T10 — Stale revocation/cancellation knowledge (Medium / Critical) |
| Description | Certify that the revocation watermark, cache-age limit, and fail-closed behavior prevent continuation with stale revocation knowledge. |
| Evidence required | SEC-027 test result passes; RT-07.* pass; fail-closed verification report. |
| Verification method | Automated security test execution; SR review of fail-closed logic. |
| Pass criteria | SEC-027 passes; RT-07.* pass; missing/stale/below-required watermark → continuation forbidden; revocation during outage → immediate stop. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), SR (security review), CA (certification) |
| ADR refs | §2.10, §6.3 |
| Test refs | SEC-027, RT-07.*, CERT-012 |

### CG-SEC-T11 — Pinned Policy Exploited

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T11 |
| Threat | T11 — Pinned policy exploited (Low / High) |
| Description | Certify that policy snapshot hash pinning, not_valid_after bounds, and the emergency deny channel prevent exploitation of stale policy. |
| Evidence required | SEC-026 test result passes; RT-02.09, RT-05.09 pass; snapshot pinning report. |
| Verification method | Automated security test execution; SR review of snapshot pinning and deny channel. |
| Pass criteria | SEC-026 passes; RT-02.09, RT-05.09 pass; hash mismatch → continuation forbidden; not_valid_after enforced; emergency deny channel honored; pinned snapshot cannot authorize unpermitted operations. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), SR (security review), CA (certification) |
| ADR refs | §2.11, §6.3 |
| Test refs | SEC-026, RT-02.09, RT-05.09, CERT-012 |

### CG-SEC-T12 — Clock Skew/Rollback Extends Authority

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T12 |
| Threat | T12 — Clock skew/rollback extends authority (Low / Critical) |
| Description | Certify that signed time anchors, monotonic time bounds, skew tolerance, and rollback tolerance prevent clock manipulation from extending authority. |
| Evidence required | SEC-023 test result passes; RT-15.* pass; RT-03.9 passes; clock manipulation defense report. |
| Verification method | Automated security test execution; SR review of clock defenses. |
| Pass criteria | SEC-023 passes; RT-15.* pass; RT-03.9 passes; signed anchors verified; monotonic time used for duration; skew beyond tolerance → security event; rollback beyond tolerance → rejected. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), SR (security review), CA (certification) |
| ADR refs | §2.8, §6.3 |
| Test refs | SEC-023, RT-15.*, RT-03.9, CERT-015, CERT-012 |

### CG-SEC-T13 — Silent Continuation

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T13 |
| Threat | T13 — Silent continuation (Medium / High) |
| Description | Certify that mandatory completion reporting, receipt requirements, reconciliation deadline, and audit chain prevent silent continuation. |
| Evidence required | RT-09.*, RT-10.* test results pass; missing report → INVALID_CONTINUATION report. |
| Verification method | Automated test execution; CA review of mandatory reporting. |
| Pass criteria | RT-09.*, RT-10.* pass; report mandatory regardless of outcome; missing report within deadline → INVALID_CONTINUATION; audit chain records continuation independently. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §2.6.2, §2.13, §6.3 |
| Test refs | RT-09.*, RT-10.*, CERT-012 |

### CG-SEC-T14 — Witness Quorum Compromised

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T14 |
| Threat | T14 — Witness quorum compromised (Low / Critical) |
| Description | Certify that independent control-plane witnesses, self-exclusion, replay-resistant signed statements, and key revocation prevent compromised witness quorum from enabling false outage. |
| Evidence required | SEC-020 test result passes; RT-04.* pass; fault model documentation (BFT or documented CFT). |
| Verification method | Automated security test execution; SR review of witness model; AR acceptance of fault model and residual risk. |
| Pass criteria | SEC-020 passes; RT-04.* pass; witness identity validated; self-exclusion enforced; revoked witness statements rejected; quorum recalculated; CFT model documented as not BFT if used. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), SR (security review), CA (certification), AR (fault model acceptance) |
| ADR refs | §2.2.4, §6.3 |
| Test refs | SEC-020, RT-04.*, CERT-012 |

### CG-SEC-T15 — Key Compromise

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T15 |
| Threat | T15 — Key compromise (Low / Critical) |
| Description | Certify that key management (HSM/vault), key rotation, key revocation via revocation stream, distinct keys per token type, and audit of key events mitigate key compromise. |
| Evidence required | Key rotation test results; key revocation test results; receipt forgery rejection test; key management infrastructure documentation; residual risk acceptance (AR sign-off). |
| Verification method | Automated security test execution; SR review of key management; AR residual risk acceptance. |
| Pass criteria | Tokens signed with rotated key rejected after watermark; revoked witness statements rejected; receipts signed with non-registered key rejected; key events audited; residual risk documented and accepted. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), SR (security review), CA (certification), AR (residual risk acceptance) |
| ADR refs | §2.1.4, §2.8 (document 06 §2.2) |
| Test refs | Key rotation, key revocation, receipt forgery tests; CERT-012 |

### CG-SEC-T16 — Database Corruption

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T16 |
| Threat | T16 — Database corruption (Medium / High) |
| Description | Certify that hash-chaining, durable replicated storage, journal persistence before effects, cache checksums, and fail-closed on corruption mitigate database corruption. |
| Evidence required | Hash-chain gap detection test; journal durability test; cache corruption → safe-hold test; fail-closed on unreadable ledger test. |
| Verification method | Automated resilience test execution; SR review of corruption detection. |
| Pass criteria | Hash-chain gaps detected and flagged; journal persisted before external effects; corrupted cache → self-check failure → safe-hold; unreadable ledger → fail-closed; residual risk documented. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), SR (security review), CA (certification) |
| ADR refs | §2.5.3, §2.13 (document 06 §2.2) |
| Test refs | RES-018, hash-chain, journal durability, cache corruption tests; CERT-013 |

### CG-SEC-T17 — Network Partition Scenarios

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T17 |
| Threat | T17 — Network partition scenarios (Medium / High) |
| Description | Certify that all four partition scenarios (A: executor isolated from Brain; B: isolated from Brain and witnesses; C: total isolation; D: isolated from downstream only) are handled correctly with fail-closed behavior. |
| Evidence required | Partition A, B, C, D test results; fail-closed on revocation cache aging test. |
| Verification method | Automated resilience test execution; SR review of partition handling. |
| Pass criteria | Partition A: direct-Brain signals fail, outage declared only with watermark sufficient; Partition B: two direct-Brain signals, no witnesses, fail-closed on cache aging; Partition C: safe-hold, no external effects; Partition D: no outage, no continuation. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), SR (security review), CA (certification) |
| ADR refs | §2.2.4, §2.8, §2.10 (document 06 §2.2) |
| Test refs | RES-* partition tests; CERT-013 |

### CG-SEC-T18 — Clock Manipulation (NTP, Monotonic Discontinuity)

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T18 |
| Threat | T18 — Clock manipulation (Low / Critical) |
| Description | Certify that NTP poisoning, monotonic clock discontinuity (suspend/resume), and timezone manipulation do not extend continuation authority. |
| Evidence required | NTP poisoning test; monotonic discontinuity → stop test; timezone change immutability test. |
| Verification method | Automated security and resilience test execution; SR review of clock infrastructure. |
| Pass criteria | NTP drift within tolerance does not extend capability window; drift beyond tolerance → security event; monotonic discontinuity → stop; timezone changes do not affect UTC comparison. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), SR (security review), CA (certification) |
| ADR refs | §2.8 (document 06 §2.2) |
| Test refs | RES-009–RES-012, SEC-023, CERT-015 |

### CG-SEC-T19 — Capability Token Replay

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T19 |
| Threat | T19 — Capability token replay (Low / Critical) |
| Description | Certify that capability binding to command/executor/tenant, supersession, revocation watermark, outage evidence binding, and C13 validation prevent capability token replay. |
| Evidence required | Capability replay across commands test; superseded capability rejection test; outage evidence binding test. |
| Verification method | Automated security test execution; SR review of replay defenses. |
| Pass criteria | Capability for command A rejected for command B; superseded capability rejected; capability without matching outage evidence rejected; residual risk (single duplicate before revocation propagates) documented. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), SR (security review), CA (certification) |
| ADR refs | §2.1.4, §2.5 (document 06 §2.2) |
| Test refs | SEC-006, SEC-007, RT-01.10, CERT-012 |

### CG-SEC-T20 — Witness Collusion

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T20 |
| Threat | T20 — Witness collusion (Low / Critical) |
| Description | Certify that the BFT fault model (or documented CFT model with direct-Brain-signal requirement) prevents witness collusion from enabling false outage. |
| Evidence required | Witness collusion BFT test (f+1 honest outvote f colluding); CFT documentation and direct-Brain-signal test; revoked witness test. |
| Verification method | Automated chaos test execution; SR review; AR acceptance of CFT residual risk if used. |
| Pass criteria | BFT: f+1 honest witnesses outvote f colluding; CFT: documented as not BFT, direct-Brain signal required; revoked witness statements do not count toward quorum. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), SR (security review), CA (certification), AR (CFT residual risk acceptance) |
| ADR refs | §2.2.4 (document 06 §2.2) |
| Test refs | CHS-003, CHS-004, RT-04.*, CERT-012 |

### CG-SEC-T21 — Audit Ledger Tampering

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T21 |
| Threat | T21 — Audit ledger tampering (Low / Critical) |
| Description | Certify that append-only enforcement, hash-chaining, replicated storage, restricted database access, and periodic integrity checks prevent and detect audit ledger tampering. |
| Evidence required | SEC-015, SEC-016, SEC-017, SEC-018 test results pass; hash-chain integrity test; append-only enforcement test; projection truncation test. |
| Verification method | Automated security test execution; SR review of access controls and integrity checks. |
| Pass criteria | SEC-015–SEC-018 pass; update/delete on ledger rejected; hash-chain modification detected; projection may truncate but ledger does not; tampering flagged as security event. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), SR (security review), CA (certification) |
| ADR refs | §2.13 (document 06 §2.2) |
| Test refs | SEC-015–SEC-018, RT-14.*, CERT-010, CERT-012 |

### CG-SEC-T22 — Configuration Drift

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T22 |
| Threat | T22 — Configuration drift (Medium / High) |
| Description | Certify that policy snapshot pinning, configuration versioning, platform maximum enforcement, and configuration validation prevent configuration drift from creating security gaps. |
| Evidence required | Configuration consistency test; policy snapshot pinning test; platform maximum enforcement test. |
| Verification method | Automated test execution; SR review of configuration management; OR review of deployment practices. |
| Pass criteria | All Brain instances report same configuration for a given tenant; executor with drifted local config uses capability's policy snapshot; tenant config exceeding platform maximums rejected at capability issuance. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), SR (security review), CA (certification), OR (deployment practices) |
| ADR refs | §2.4, §2.11 (document 06 §2.2) |
| Test refs | Configuration consistency, snapshot pinning, platform max tests; CERT-009 |

### CG-SEC-T23 — Multi-Tenant Data Leakage

| Field | Value |
|---|---|
| Gate ID | CG-SEC-T23 |
| Threat | T23 — Multi-tenant data leakage (Low / Critical) |
| Description | Certify that RLS, tenant-partitioned revocation streams, tenant-scoped audit, cache key isolation, and tenant-scoped journals prevent multi-tenant data leakage. |
| Evidence required | RLS enforcement test; cache key isolation test; revocation stream partitioning test; audit partitioning test. |
| Verification method | Automated security and multi-tenant test execution; SR review of RLS and partitioning. |
| Pass criteria | RLS enforced (tenant A session returns only tenant A rows); cache keys isolated by tenant_id; revocation stream partitioned by tenant; audit queries tenant-scoped; no cross-tenant data access. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), SR (security review), CA (certification) |
| ADR refs | §2.14 (document 06 §2.2) |
| Test refs | SEC-011–SEC-014, MT-001–MT-012, CERT-011, CERT-012 |

---

## 7. Invariant Verification Gates (CG-INV-I01 through CG-INV-I15 plus CG-INV-I3a)

Each of the 16 invariants from ADR-MC-001 §7 (15 numbered invariants plus invariant 3a) has a dedicated verification gate. An invariant is certified only when it is proven by at least one passing test and enforced at the component boundary.

### CG-INV-I01 — No Authoritative Effects Without Valid Lease

| Field | Value |
|---|---|
| Gate ID | CG-INV-I01 |
| Invariant | I1 — An executor without a valid lease cannot produce authoritative command effects during normal execution. |
| Description | Certify that lease token validation prevents any authoritative effect without a valid lease. |
| Evidence required | UT-C01-001, UT-C01-004–UT-C01-006, SEC-004, SEC-005 pass; RT-01.* pass; invariant enforcement at C01/C13 boundary report. |
| Verification method | Automated test execution; CA review of boundary enforcement. |
| Pass criteria | All listed tests pass; no effect accepted without valid lease token; enforcement at C01 (issuance) and C13 (downstream validation). |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §7 (inv 1) |
| Test refs | UT-C01-001, UT-C01-004–UT-C01-006, SEC-004, SEC-005, RT-01.*, CERT-005 |

### CG-INV-I02 — Expired Lease Cannot Authorize

| Field | Value |
|---|---|
| Gate ID | CG-INV-I02 |
| Invariant | I2 — An executor cannot use an expired lease to authorize continuation or effects. |
| Description | Certify that lease expiry immediately revokes all authority and expired tokens are rejected. |
| Evidence required | UT-C01-005, SEC-004, SEC-005 pass; RT-01.3, RT-05.2, RES-004 pass. |
| Verification method | Automated test execution; CA review. |
| Pass criteria | All listed tests pass; expired token rejected by all validators; no continuation or effects after expiry. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §7 (inv 2) |
| Test refs | UT-C01-005, SEC-004, SEC-005, RT-01.3, RT-05.2, RES-004, CERT-005 |

### CG-INV-I03 — Capability Temporal Bounds

| Field | Value |
|---|---|
| Gate ID | CG-INV-I03 |
| Invariant | I3 — A continuation capability cannot be used before lease expiry or after its own expiry. |
| Description | Certify that not_valid_before and not_valid_after are enforced via signed time anchors. |
| Evidence required | UT-C02-003, UT-C02-004, SEC-006, SEC-007 pass; RT-02.2, RT-02.3 pass. |
| Verification method | Automated test execution; CA review. |
| Pass criteria | All listed tests pass; capability rejected before not_valid_before and after not_valid_after. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §7 (inv 3) |
| Test refs | UT-C02-003, UT-C02-004, SEC-006, SEC-007, RT-02.2, RT-02.3, CERT-005 |

### CG-INV-I3a — Only Latest-Lease Capability Exercisable

| Field | Value |
|---|---|
| Gate ID | CG-INV-I3a |
| Invariant | I3a — Only the continuation capability referenced by the latest valid lease may be exercised. Prior capabilities are superseded at renewal, even if their not_valid_after is later. |
| Description | Certify that capability supersession is enforced at renewal and that downstream systems reject superseded capability IDs. |
| Evidence required | UT-C02-009, RT-01.10 pass; INT-002, INT-020, CHS-016 pass. |
| Verification method | Automated test execution; CA review of supersession and downstream validation. |
| Pass criteria | All listed tests pass; prior capability rejected even with later not_valid_after; only latest-lease capability accepted; capability rotation auditable. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §7 (inv 3a) |
| Test refs | UT-C02-009, RT-01.10, INT-002, INT-020, CHS-016, CERT-005 |

### CG-INV-I04 — Continuation Never Default

| Field | Value |
|---|---|
| Gate ID | CG-INV-I04 |
| Invariant | I4 — Continuation is never the default behavior. |
| Description | Certify that the eligibility check and default STOP class prevent continuation as default. |
| Evidence required | UT-C05-004, RT-05.14, SEC-019, SEC-020, SEC-021, SEC-022 pass; RT-03.*, RT-04.*, RT-05.* pass. |
| Verification method | Automated test execution; CA review. |
| Pass criteria | All listed tests pass; default decision is STOP; continuation only when all criteria met. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §7 (inv 4) |
| Test refs | UT-C05-004, RT-05.14, SEC-019–SEC-022, RT-03.*, RT-04.*, RT-05.*, CERT-005 |

### CG-INV-I05 — Continuation Within Bounded Envelope

| Field | Value |
|---|---|
| Gate ID | CG-INV-I05 |
| Invariant | I5 — Continuation cannot exceed its bounded envelope. |
| Description | Certify that max_continuation_duration, max_continuation_operations, and monotonic clock enforce the bounded envelope. |
| Evidence required | RT-06.*, UT-C02-015, UT-C02-016, UT-C08-005 pass; RES-011, SEC-023, SEC-024, CHS-017 pass. |
| Verification method | Automated test execution; CA review. |
| Pass criteria | All listed tests pass; duration, operation, and concurrency bounds enforced; monotonic clock prevents extension. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §7 (inv 5) |
| Test refs | RT-06.*, UT-C02-015, UT-C02-016, UT-C08-005, RES-011, SEC-023, SEC-024, CHS-017, CERT-005 |

### CG-INV-I06 — Every Continuation Produces Signed Receipt

| Field | Value |
|---|---|
| Gate ID | CG-INV-I06 |
| Invariant | I6 — Every continuation produces an immutable, signed receipt. |
| Description | Certify that receipt generation and signature verification enforce immutable signed receipts. |
| Evidence required | RT-09.*, UT-C09-001–UT-C09-003 pass; SEC-028–SEC-031 pass. |
| Verification method | Automated test execution; CA review. |
| Pass criteria | All listed tests pass; every continuation produces a signed receipt; signature verifies; tampered receipt rejected. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §7 (inv 6) |
| Test refs | RT-09.*, UT-C09-001–UT-C09-003, SEC-028–SEC-031, CERT-005 |

### CG-INV-I07 — Every Continuation Reconciled Before Terminal

| Field | Value |
|---|---|
| Gate ID | CG-INV-I07 |
| Invariant | I7 — Every continuation is reconciled before the command reaches terminal state. |
| Description | Certify that the reconciliation protocol enforces reconciliation before terminal state. |
| Evidence required | RT-10.*, RT-13.*, UT-C10-* pass; INT-008–INT-013, REC-008–REC-016 pass. |
| Verification method | Automated test execution; CA review. |
| Pass criteria | All listed tests pass; no command reaches terminal state without reconciliation. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §7 (inv 7) |
| Test refs | RT-10.*, RT-13.*, UT-C10-*, INT-008–INT-013, REC-008–REC-016, CERT-005 |

### CG-INV-I08 — Conflicts Never Resolve Silently

| Field | Value |
|---|---|
| Gate ID | CG-INV-I08 |
| Invariant | I8 — Conflicting continuation results or non-reversible effects never resolve silently. |
| Description | Certify that conflict records, effect freezes, and manual review queue prevent silent conflict resolution. |
| Evidence required | RT-11.*, UT-C11-*, UT-C10-004, UT-C10-006 pass; CHS-005, CHS-008, CHS-009, SEC-032 pass. |
| Verification method | Automated test execution; CA review. |
| Pass criteria | All listed tests pass; conflicts recorded; effects frozen; manual review routed; no silent resolution. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §7 (inv 8) |
| Test refs | RT-11.*, UT-C11-*, UT-C10-004, UT-C10-006, CHS-005, CHS-008, CHS-009, SEC-032, CERT-005 |

### CG-INV-I09 — Cross-Tenant Continuation Impossible

| Field | Value |
|---|---|
| Gate ID | CG-INV-I09 |
| Invariant | I9 — Cross-tenant continuation is impossible. |
| Description | Certify that tenant-scoped capabilities and policies prevent cross-tenant continuation. |
| Evidence required | RT-12.*, MT-001–MT-012, SEC-011–SEC-014 pass; INT-018 passes. |
| Verification method | Automated test execution; CA review; SR review of RLS. |
| Pass criteria | All listed tests pass; cross-tenant continuation impossible; treated as security event. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (RLS) |
| ADR refs | §7 (inv 9) |
| Test refs | RT-12.*, MT-001–MT-012, SEC-011–SEC-014, INT-018, CERT-005, CERT-011 |

### CG-INV-I10 — Idempotency Preserved

| Field | Value |
|---|---|
| Gate ID | CG-INV-I10 |
| Invariant | I10 — Idempotency is preserved across continuation, replay, and normal execution. |
| Description | Certify that stable (command_id, operation_id, side_effect_slot) identity and duplicate suppression layers preserve idempotency. |
| Evidence required | RT-08.*, UT-C13-001, UT-C13-002, UT-C08-001, UT-C08-004 pass; INT-007, INT-013, SEC-009, SEC-010, REC-001–REC-007 pass. |
| Verification method | Automated test execution; CA review. |
| Pass criteria | All listed tests pass; duplicate effects rejected; root_command_id used for replay; idempotency across all execution modes. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §7 (inv 10) |
| Test refs | RT-08.*, UT-C13-001, UT-C13-002, UT-C08-001, UT-C08-004, INT-007, INT-013, SEC-009, SEC-010, REC-001–REC-007, CERT-005 |

### CG-INV-I11 — Audit Storage Complete and Never Truncated

| Field | Value |
|---|---|
| Gate ID | CG-INV-I11 |
| Invariant | I11 — Authoritative audit storage is complete and never truncated. |
| Description | Certify that the immutable audit ledger stores every event and is never truncated (projection may truncate). |
| Evidence required | RT-14.*, UT-C12-001–UT-C12-007 pass; INT-016, SEC-015–SEC-018, RES-018 pass. |
| Verification method | Automated test execution; CA review; SR review of append-only enforcement. |
| Pass criteria | All listed tests pass; ledger append-only; never truncated; projection may truncate with metadata. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (append-only) |
| ADR refs | §7 (inv 11) |
| Test refs | RT-14.*, UT-C12-001–UT-C12-007, INT-016, SEC-015–SEC-018, RES-018, CERT-005, CERT-010 |

### CG-INV-I12 — Policy Snapshot Bounded to Pinned Hash

| Field | Value |
|---|---|
| Gate ID | CG-INV-I12 |
| Invariant | I12 — Policy snapshot validity is bounded to the exact pinned snapshot in the capability. |
| Description | Certify that policy_snapshot_hash and policy_snapshot_not_valid_after enforce exact snapshot pinning. |
| Evidence required | UT-C07-001–UT-C07-004, RT-02.09, RT-05.09 pass; INT-015, SEC-026 pass. |
| Verification method | Automated test execution; CA review. |
| Pass criteria | All listed tests pass; hash mismatch → continuation forbidden; not_valid_after enforced. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §7 (inv 12) |
| Test refs | UT-C07-001–UT-C07-004, RT-02.09, RT-05.09, INT-015, SEC-026, CERT-005 |

### CG-INV-I13 — Revocation Knowledge Fresh; Absence Not Permission

| Field | Value |
|---|---|
| Gate ID | CG-INV-I13 |
| Invariant | I13 — Revocation/cancellation knowledge must be fresh enough; absence of evidence is not permission. |
| Description | Certify that revocation watermark, max_revocation_cache_age, and fail-closed behavior enforce fresh revocation knowledge. |
| Evidence required | RT-07.*, UT-C06-001–UT-C06-008 pass; INT-014, RES-015, SEC-027, CHS-013 pass. |
| Verification method | Automated test execution; CA review; SR review of fail-closed. |
| Pass criteria | All listed tests pass; fail-closed on missing/stale/below-required watermark; absence of evidence does not permit continuation. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (fail-closed) |
| ADR refs | §7 (inv 13) |
| Test refs | RT-07.*, UT-C06-001–UT-C06-008, INT-014, RES-015, SEC-027, CHS-013, CERT-005 |

### CG-INV-I14 — Time Not Manipulable to Extend Authority

| Field | Value |
|---|---|
| Gate ID | CG-INV-I14 |
| Invariant | I14 — Time cannot be manipulated to extend authority. |
| Description | Certify that signed time anchors, monotonic clocks, skew tolerance, and rollback tolerance prevent time manipulation. |
| Evidence required | RT-15.*, UT-C14-001–UT-C14-008 pass; RES-009–RES-012, SEC-023, CHS-011 pass. |
| Verification method | Automated test execution; CA review; SR review of clock defenses. |
| Pass criteria | All listed tests pass; signed anchors verified; monotonic time used; skew/rollback beyond tolerance → stop; time manipulation does not extend authority. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (clock defenses) |
| ADR refs | §7 (inv 14) |
| Test refs | RT-15.*, UT-C14-001–UT-C14-008, RES-009–RES-012, SEC-023, CHS-011, CERT-005, CERT-015 |

### CG-INV-I15 — High-Risk Effects Prohibited During Continuation

| Field | Value |
|---|---|
| Gate ID | CG-INV-I15 |
| Invariant | I15 — High-risk or irreversible side effects cannot be produced during continuation. |
| Description | Certify that Class 3 prohibition and downstream class validation prevent high-risk effects during continuation. |
| Evidence required | RT-16.*, UT-C13-006 pass; INT-017, SEC-025, RES-014 pass. |
| Verification method | Automated test execution; CA review; SR review of class enforcement. |
| Pass criteria | All listed tests pass; Class 3 effects rejected during continuation; downstream validates class; security event logged. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (class enforcement) |
| ADR refs | §7 (inv 15), §2.9 |
| Test refs | RT-16.*, UT-C13-006, INT-017, SEC-025, RES-014, CERT-005, CERT-016 |

---

## 8. Acceptance Criteria Verification Gates (CG-AC-01 through CG-AC-20)

Each of the 20 acceptance criteria from ADR-MC-001 §11 has a dedicated verification gate. An acceptance criterion is certified when the tests mapped to it pass and the certifier confirms the criterion is satisfied.

### CG-AC-01 — Lease and Capability Lifecycle Separated

| Field | Value |
|---|---|
| Gate ID | CG-AC-01 |
| Criterion | AC1 — Lease lifecycle and continuation capability lifecycle are fully specified and separated. |
| Description | Certify that lease and capability lifecycles are fully specified and separated (distinct tokens, distinct signing, distinct validation). |
| Evidence required | RT-01.*, UT-C01-*, UT-C02-* pass; INT-001, INT-002 pass; lifecycle separation report. |
| Verification method | Automated test execution; CA review of separation. |
| Pass criteria | All listed tests pass; lease and capability tokens cryptographically separate; lifecycles independently specified and enforced. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), AR (specification review) |
| ADR refs | §11 (AC1) |
| Test refs | RT-01.*, UT-C01-*, UT-C02-*, INT-001, INT-002, CERT-001, CERT-006 |

### CG-AC-02 — Capability Unusable Before Expiry; Bounded

| Field | Value |
|---|---|
| Gate ID | CG-AC-02 |
| Criterion | AC2 — Continuation capability is unusable before lease expiry and bounded by time, operations, and scope. |
| Description | Certify that capability is unusable before lease expiry and bounded by time, operations, and scope. |
| Evidence required | RT-02.*, UT-C02-001–UT-C02-003 pass; SEC-006, INT-001 pass. |
| Verification method | Automated test execution; CA review. |
| Pass criteria | All listed tests pass; capability rejected before not_valid_before; bounded by not_valid_after, max_continuation_duration, max_continuation_operations, command/executor/tenant scope. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §11 (AC2) |
| Test refs | RT-02.*, UT-C02-001–UT-C02-003, SEC-006, INT-001, CERT-001, CERT-006 |

### CG-AC-03 — Outage Detection: 2 Signals + Direct + Grace

| Field | Value |
|---|---|
| Gate ID | CG-AC-03 |
| Criterion | AC3 — Brain outage detection uses at least two independent signals including one direct-Brain signal, with a grace period. |
| Description | Certify that outage detection uses ≥2 independent signals including one direct-Brain signal, with a grace period. |
| Evidence required | RT-03.*, UT-C03-*, UT-C04-* pass; INT-003, INT-004, SEC-021, SEC-022 pass. |
| Verification method | Automated test execution; CA review. |
| Pass criteria | All listed tests pass; two-signal rule enforced; direct-Brain signal required; grace period enforced. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §11 (AC3) |
| Test refs | RT-03.*, UT-C03-*, UT-C04-*, INT-003, INT-004, SEC-021, SEC-022, CERT-001, CERT-006 |

### CG-AC-04 — Witness Trust Model Fully Defined

| Field | Value |
|---|---|
| Gate ID | CG-AC-04 |
| Criterion | AC4 — Witness trust model is fully defined with identity, quorum, replay resistance, and self-exclusion. |
| Description | Certify that the witness trust model is fully defined with identity, quorum, replay resistance, and self-exclusion. |
| Evidence required | RT-04.*, UT-C04-* pass; CHS-003, CHS-004, SEC-020 pass. |
| Verification method | Automated test execution; CA review; SR review; AR fault model acceptance. |
| Pass criteria | All listed tests pass; witness identity, quorum, replay resistance, self-exclusion all enforced. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (security), AR (fault model) |
| ADR refs | §11 (AC4) |
| Test refs | RT-04.*, UT-C04-*, CHS-003, CHS-004, SEC-020, CERT-001, CERT-006 |

### CG-AC-05 — Eligibility Explicit; Default STOP

| Field | Value |
|---|---|
| Gate ID | CG-AC-05 |
| Criterion | AC5 — Continuation eligibility criteria are explicit and default to STOP. |
| Description | Certify that eligibility criteria are explicit and default to STOP. |
| Evidence required | RT-05.*, UT-C05-003, UT-C05-004 pass; INT-005, SEC-019 pass. |
| Verification method | Automated test execution; CA review. |
| Pass criteria | All listed tests pass; all 11 criteria explicit; default STOP. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §11 (AC5) |
| Test refs | RT-05.*, UT-C05-003, UT-C05-004, INT-005, SEC-019, CERT-001, CERT-006 |

### CG-AC-06 — Continuation Limits with Platform/Tenant Bounds

| Field | Value |
|---|---|
| Gate ID | CG-AC-06 |
| Criterion | AC6 — Continuation limits are defined with platform and tenant bounds. |
| Description | Certify that continuation limits are defined with platform and tenant bounds. |
| Evidence required | RT-06.*, UT-C02-015, UT-C02-016 pass; MT-005, MT-006, CHS-017, CHS-018 pass. |
| Verification method | Automated test execution; CA review. |
| Pass criteria | All listed tests pass; all 8 limits defined; platform maximums enforced; tenant bounds enforced; break-glass reduces but never increases. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §11 (AC6) |
| Test refs | RT-06.*, UT-C02-015, UT-C02-016, MT-005, MT-006, CHS-017, CHS-018, CERT-001, CERT-006 |

### CG-AC-07 — Stable Effect Identity for Dedup

| Field | Value |
|---|---|
| Gate ID | CG-AC-07 |
| Criterion | AC7 — Stable external-effect identity is defined and used for duplicate suppression across normal execution, continuation, and replay. |
| Description | Certify that stable external-effect identity is defined and used for duplicate suppression. |
| Evidence required | RT-08.*, UT-C13-001, UT-C13-002 pass; INT-007, SEC-010 pass. |
| Verification method | Automated test execution; CA review. |
| Pass criteria | All listed tests pass; (command_id, operation_id, side_effect_slot) used; dedup across normal, continuation, replay. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §11 (AC7) |
| Test refs | RT-08.*, UT-C13-001, UT-C13-002, INT-007, SEC-010, CERT-001, CERT-006 |

### CG-AC-08 — Replay Semantics: Effect Identity + Reconciliation First

| Field | Value |
|---|---|
| Gate ID | CG-AC-08 |
| Criterion | AC8 — Replay semantics preserve effect identity and require reconciliation before authorization. |
| Description | Certify that replay semantics preserve effect identity and require reconciliation before authorization. |
| Evidence required | REC-001–REC-007, RT-08.07, RT-08.10 pass; INT-013 passes. |
| Verification method | Automated test execution; CA review. |
| Pass criteria | All listed tests pass; replay uses root_command_id; reconciliation required before replay authorization. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §11 (AC8) |
| Test refs | REC-001–REC-007, RT-08.07, RT-08.10, INT-013, CERT-004, CERT-006 |

### CG-AC-09 — Reconciliation: 4 Concerns Separated

| Field | Value |
|---|---|
| Gate ID | CG-AC-09 |
| Criterion | AC9 — Reconciliation protocol separates result selection, effect reconciliation, compensation, and manual review. |
| Description | Certify that the reconciliation protocol separates the four concerns. |
| Evidence required | RT-10.*, UT-C10-* pass; INT-009–INT-013 pass. |
| Verification method | Automated test execution; CA review; AR review of separation. |
| Pass criteria | All listed tests pass; result selection, effect reconciliation, compensation, manual review all separated and performed in order. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), AR (reconciliation design) |
| ADR refs | §11 (AC9) |
| Test refs | RT-10.*, UT-C10-*, INT-009–INT-013, CERT-001, CERT-006 |

### CG-AC-10 — Receipts Mandatory, Signed, Immutable

| Field | Value |
|---|---|
| Gate ID | CG-AC-10 |
| Criterion | AC10 — Completion receipts are mandatory, signed, and immutable. |
| Description | Certify that completion receipts are mandatory, signed, and immutable. |
| Evidence required | RT-09.*, UT-C09-* pass; SEC-028, SEC-029 pass. |
| Verification method | Automated test execution; CA review. |
| Pass criteria | All listed tests pass; receipts mandatory; signed; immutable; tampered receipts rejected. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §11 (AC10) |
| Test refs | RT-09.*, UT-C09-*, SEC-028, SEC-029, CERT-001, CERT-006 |

### CG-AC-11 — Split-Brain: Detect, Freeze, Manual Review

| Field | Value |
|---|---|
| Gate ID | CG-AC-11 |
| Criterion | AC11 — Split-brain handling detects conflicts, freezes effects, and routes to manual review. |
| Description | Certify that split-brain handling detects conflicts, freezes effects, and routes to manual review. |
| Evidence required | RT-11.*, UT-C11-* pass; CHS-007–CHS-010 pass. |
| Verification method | Automated chaos test execution; CA review. |
| Pass criteria | All listed tests pass; conflicts detected; effects frozen; manual review routed; no silent resolution. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §11 (AC11) |
| Test refs | RT-11.*, UT-C11-*, CHS-007–CHS-010, CERT-003, CERT-006 |

### CG-AC-12 — Audit Chain Complete; Never Truncated

| Field | Value |
|---|---|
| Gate ID | CG-AC-12 |
| Criterion | AC12 — Audit chain includes all continuation events; authoritative storage is never truncated. |
| Description | Certify that the audit chain includes all continuation events and authoritative storage is never truncated. |
| Evidence required | RT-14.*, UT-C12-* pass; INT-016, SEC-015–SEC-018 pass. |
| Verification method | Automated test execution; CA review; SR review. |
| Pass criteria | All listed tests pass; all §2.13 events recorded; ledger never truncated; projection may truncate with metadata. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (append-only) |
| ADR refs | §11 (AC12) |
| Test refs | RT-14.*, UT-C12-*, INT-016, SEC-015–SEC-018, CERT-010, CERT-006 |

### CG-AC-13 — Tenant Isolation Throughout

| Field | Value |
|---|---|
| Gate ID | CG-AC-13 |
| Criterion | AC13 — Tenant isolation is guaranteed throughout continuation and reconciliation. |
| Description | Certify that tenant isolation is guaranteed throughout continuation and reconciliation. |
| Evidence required | RT-12.*, MT-001–MT-012, SEC-011–SEC-014 pass; INT-018 passes. |
| Verification method | Automated test execution; CA review; SR review of RLS. |
| Pass criteria | All listed tests pass; tenant isolation throughout; cross-tenant continuation impossible. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (RLS) |
| ADR refs | §11 (AC13) |
| Test refs | RT-12.*, MT-001–MT-012, SEC-011–SEC-014, INT-018, CERT-011, CERT-006 |

### CG-AC-14 — Recovery Protocol: Detection, Collection, Reconciliation, Refresh

| Field | Value |
|---|---|
| Gate ID | CG-AC-14 |
| Criterion | AC14 — Recovery protocol defines recovery detection, report collection, reconciliation, and policy refresh. |
| Description | Certify that the recovery protocol defines recovery detection, report collection, reconciliation, and policy refresh. |
| Evidence required | RT-13.*, REC-008–REC-016 pass; INT-008, RES-013 pass. |
| Verification method | Automated test execution; CA review; OR review. |
| Pass criteria | All listed tests pass; all 10 recovery protocol steps defined and testable end-to-end. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), OR (operational steps) |
| ADR refs | §11 (AC14) |
| Test refs | RT-13.*, REC-008–REC-016, INT-008, RES-013, CERT-001, CERT-006 |

### CG-AC-15 — Trusted Time: Skew, Monotonic, Signed Anchors

| Field | Value |
|---|---|
| Gate ID | CG-AC-15 |
| Criterion | AC15 — Trusted time, clock skew, monotonic time, and signed time anchors are specified. |
| Description | Certify that trusted time, clock skew, monotonic time, and signed time anchors are specified and enforced. |
| Evidence required | RT-15.*, UT-C14-* pass; RES-009–RES-012, SEC-023 pass. |
| Verification method | Automated test execution; CA review; SR review. |
| Pass criteria | All listed tests pass; signed anchors; monotonic time for duration; skew tolerance; rollback tolerance; disagreement → stop. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (clock defenses) |
| ADR refs | §11 (AC15) |
| Test refs | RT-15.*, UT-C14-*, RES-009–RES-012, SEC-023, CERT-015, CERT-006 |

### CG-AC-16 — Policy Snapshot Pinned by Hash, Bounded by Time

| Field | Value |
|---|---|
| Gate ID | CG-AC-16 |
| Criterion | AC16 — Policy snapshot is pinned by hash and bounded by validity time. |
| Description | Certify that policy snapshot is pinned by hash and bounded by validity time. |
| Evidence required | UT-C07-*, RT-02.09, RT-05.09 pass; INT-015, SEC-026 pass. |
| Verification method | Automated test execution; CA review. |
| Pass criteria | All listed tests pass; hash pinning enforced; not_valid_after enforced. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §11 (AC16) |
| Test refs | UT-C07-*, RT-02.09, RT-05.09, INT-015, SEC-026, CERT-001, CERT-006 |

### CG-AC-17 — Revocation Watermark + Cache-Age Fail-Closed

| Field | Value |
|---|---|
| Gate ID | CG-AC-17 |
| Criterion | AC17 — Revocation watermark and cache-age rules are fail-closed. |
| Description | Certify that revocation watermark and cache-age rules are fail-closed. |
| Evidence required | RT-07.*, UT-C06-* pass; INT-014, RES-015, SEC-027 pass. |
| Verification method | Automated test execution; CA review; SR review. |
| Pass criteria | All listed tests pass; fail-closed on missing/stale/below-required watermark; cache age enforced. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (fail-closed) |
| ADR refs | §11 (AC17) |
| Test refs | RT-07.*, UT-C06-*, INT-014, RES-015, SEC-027, CERT-001, CERT-006 |

### CG-AC-18 — Side Effects Classified; Class 3 Prohibited

| Field | Value |
|---|---|
| Gate ID | CG-AC-18 |
| Criterion | AC18 — Side effects are classified and Class 3 effects are prohibited during continuation. |
| Description | Certify that side effects are classified and Class 3 effects are prohibited during continuation. |
| Evidence required | RT-16.*, UT-C13-006 pass; INT-017, SEC-025 pass. |
| Verification method | Automated test execution; CA review; SR review. |
| Pass criteria | All listed tests pass; Class 0–2 permitted under conditions; Class 3 prohibited and rejected. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (class enforcement) |
| ADR refs | §11 (AC18) |
| Test refs | RT-16.*, UT-C13-006, INT-017, SEC-025, CERT-016, CERT-006 |

### CG-AC-19 — Threat Model, Invariants, Glossary, Prerequisites Complete

| Field | Value |
|---|---|
| Gate ID | CG-AC-19 |
| Criterion | AC19 — Threat model, invariants, glossary, implementation prerequisites are complete. |
| Description | Certify that the threat model (23 threats), invariants (16 including I3a), glossary, and implementation prerequisites (14 components, 18 settings, 16 tests) are complete. |
| Evidence required | CERT-005, CERT-006, CERT-008, CERT-009 pass; completeness report covering all ADR §8, §9, §7, §6.3, and document 06. |
| Verification method | CA review of completeness; AR review. |
| Pass criteria | All listed certification tests pass; threat model complete (23 threats); invariants complete (16); glossary complete; prerequisites complete (14 components, 18 settings, 16 tests). |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), AR (completeness review) |
| ADR refs | §11 (AC19) |
| Test refs | CERT-005, CERT-006, CERT-008, CERT-009 |

### CG-AC-20 — Non-Goals: No Implementation, No Deployment, No Authority

| Field | Value |
|---|---|
| Gate ID | CG-AC-20 |
| Criterion | AC20 — Non-goals explicitly exclude implementation, deployment, and authority activation. |
| Description | Certify that non-goals explicitly exclude implementation, deployment, and authority activation, and that the planning package does not implement, deploy, or activate authority. |
| Evidence required | CERT-018 passes; non-goals verification report confirming no runtime code deployed, no authority activated, gate still BLOCKED. |
| Verification method | CA review; AR review. |
| Pass criteria | CERT-018 passes; no runtime code deployed; no authority activated; Sigma gate still BLOCKED; non-goals documented in ADR §10. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), AR (non-goals review) |
| ADR refs | §11 (AC20), §10 |
| Test refs | CERT-018 |

---

## 9. Performance and Scalability Gates (CG-PERF-01 through CG-PERF-08)

Performance gates verify that the implementation meets the performance and scalability requirements implied by the ADR's continuation limits and operational requirements. Six gates are blocking; two are non-blocking (may be waived with AR approval).

### CG-PERF-01 — Outage Detection Latency

| Field | Value |
|---|---|
| Gate ID | CG-PERF-01 |
| Description | Certify that outage detection completes within the grace period plus signal threshold time, and that the outage record is persisted within 1 second of declaration. |
| Evidence required | Outage detection latency benchmark report; persistence latency report. |
| Verification method | Performance benchmark on staging (PostgreSQL); CA review. |
| Pass criteria | Outage declared no earlier than grace period end; outage record persisted within 1 second of declaration; detection latency measured and within acceptable bounds. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), OR (staging) |
| ADR refs | §2.2.2, §2.4 |

### CG-PERF-02 — Continuation Start Latency

| Field | Value |
|---|---|
| Gate ID | CG-PERF-02 |
| Description | Certify that the eligibility decision and continuation start complete within 2 seconds of all criteria being met. |
| Evidence required | Eligibility decision latency benchmark report. |
| Verification method | Performance benchmark; CA review. |
| Pass criteria | Eligibility decision within 2 seconds; continuation start within 2 seconds of eligibility. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §2.3 |

### CG-PERF-03 — Reconciliation Throughput

| Field | Value |
|---|---|
| Gate ID | CG-PERF-03 |
| Description | Certify that the reconciliation engine can process at least 100 continuation reports per minute without degradation, and that conflict detection does not introduce unbounded latency. |
| Evidence required | Reconciliation throughput benchmark report; conflict detection latency report. |
| Verification method | Performance benchmark on staging (PostgreSQL); CA review. |
| Pass criteria | ≥100 reports/minute; conflict detection latency bounded; no unbounded growth in conflict queue. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), OR (staging) |
| ADR refs | §2.6 |

### CG-PERF-04 — Audit Pipeline Throughput

| Field | Value |
|---|---|
| Gate ID | CG-PERF-04 |
| Description | Certify that the audit event pipeline can append at least 1000 events per second without blocking continuation execution, and that hash-chain verification does not degrade append latency. |
| Evidence required | Audit pipeline throughput benchmark report; hash-chain append latency report. |
| Verification method | Performance benchmark; CA review; SR review. |
| Pass criteria | ≥1000 events/second; append latency <10ms p99; hash-chain verification does not block appends. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (audit integrity) |
| ADR refs | §2.13 |

### CG-PERF-05 — Tenant Concurrency

| Field | Value |
|---|---|
| Gate ID | CG-PERF-05 |
| Description | Certify that the system supports at least 50 concurrent tenants with active continuations without cross-tenant interference or performance degradation beyond 20%. |
| Evidence required | Multi-tenant concurrency benchmark report; isolation-under-load report. |
| Verification method | Performance benchmark on staging; CA review; SR review of RLS under load. |
| Pass criteria | ≥50 concurrent tenants; no cross-tenant interference; performance degradation <20% under load. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), SR (RLS under load) |
| ADR refs | §2.14 |

### CG-PERF-06 — Capability Validation Latency

| Field | Value |
|---|---|
| Gate ID | CG-PERF-06 |
| Description | Certify that capability token validation (including signature verification and outage evidence validation) completes within 50ms p99 at the downstream boundary. |
| Evidence required | Capability validation latency benchmark report. |
| Verification method | Performance benchmark; CA review. |
| Pass criteria | Validation latency <50ms p99; signature verification within budget. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §2.1.4 |

### CG-PERF-07 — Recovery Protocol Completion Time

| Field | Value |
|---|---|
| Gate ID | CG-PERF-07 |
| Description | Certify that the full recovery protocol completes within 5 minutes of recovery detection for up to 100 pending continuation reports. |
| Evidence required | Recovery protocol completion time benchmark report. |
| Verification method | Performance benchmark on staging; CA review; OR review. |
| Pass criteria | Recovery protocol completes within 5 minutes for ≤100 reports; no unbounded reconciliation latency. |
| Blocking status | NON-BLOCKING (may be waived with AR approval and documented justification) |
| Responsible party | CO (evidence), CA (certification), OR (staging) |
| ADR refs | §2.15 |

### CG-PERF-08 — Witness Statement Validation Throughput

| Field | Value |
|---|---|
| Gate ID | CG-PERF-08 |
| Description | Certify that witness statement validation (signature, nonce, max age, tenant) completes within 20ms p99 per statement, and that quorum assembly for N=7 witnesses completes within 200ms. |
| Evidence required | Witness validation latency benchmark report; quorum assembly latency report. |
| Verification method | Performance benchmark; CA review. |
| Pass criteria | Per-statement validation <20ms p99; quorum assembly (N=7) <200ms. |
| Blocking status | NON-BLOCKING (may be waived with AR approval and documented justification) |
| Responsible party | CO (evidence), CA (certification) |
| ADR refs | §2.2.4 |

---

## 10. Documentation Completeness Gates (CG-DOC-01 through CG-DOC-07)

Documentation gates verify that all planning and implementation documentation is complete, consistent, and traceable to the ADR.

### CG-DOC-01 — ADR Consistency

| Field | Value |
|---|---|
| Gate ID | CG-DOC-01 |
| Description | Certify that all planning documents (01–10) are consistent with ADR-MC-001 and with each other, with no contradictions in component definitions, interface specifications, state machines, or invariants. |
| Evidence required | Cross-document consistency review report; contradiction resolution log. |
| Verification method | AR review of all planning documents against ADR; CA review. |
| Pass criteria | No unresolved contradictions; all documents reference the same component IDs, invariant IDs, and ADR sections consistently. |
| Blocking status | BLOCKING |
| Responsible party | AR (review), CA (certification) |
| ADR refs | §8, §9, §11 |

### CG-DOC-02 — Interface Specifications Complete

| Field | Value |
|---|---|
| Gate ID | CG-DOC-02 |
| Description | Certify that interface specifications (document 03) cover all 14 components with Pydantic v2 models and Protocol interfaces, and that they match the implementation. |
| Evidence required | Interface completeness report (14/14 components); interface-implementation conformance report. |
| Verification method | AR review; CA review. |
| Pass criteria | All 14 components have complete interface specifications; implementation conforms to specifications. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), AR (review), CA (certification) |
| ADR refs | §9.1 |

### CG-DOC-03 — State Machine Documentation Complete

| Field | Value |
|---|---|
| Gate ID | CG-DOC-03 |
| Description | Certify that state machine documentation (document 04) covers all component and lifecycle state machines and matches the implementation. |
| Evidence required | State machine completeness report; state machine-implementation conformance report. |
| Verification method | AR review; CA review. |
| Pass criteria | All state machines documented; implementation conforms; all transitions covered by tests. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), AR (review), CA (certification) |
| ADR refs | §4 (ADR), §9.1 |

### CG-DOC-04 — Threat Model Complete

| Field | Value |
|---|---|
| Gate ID | CG-DOC-04 |
| Description | Certify that the threat model (document 06) covers all 23 threats with STRIDE analysis, residual risk documentation, and test verification mapping, and that the STRIDE-to-component matrix has no empty cells. |
| Evidence required | Threat model completeness report (23 threats); STRIDE coverage report (no empty cells); residual risk acceptance log (AR sign-off for all Critical-impact threats). |
| Verification method | SR review; AR review of residual risks; CA review. |
| Pass criteria | 23 threats documented; STRIDE matrix complete (no empty cells); all Critical-impact residual risks accepted by AR; CFT model documented as not BFT if used. |
| Blocking status | BLOCKING |
| Responsible party | SR (review), AR (residual risk acceptance), CA (certification) |
| ADR refs | §6.3, §7 |

### CG-DOC-05 — Test Matrix Complete

| Field | Value |
|---|---|
| Gate ID | CG-DOC-05 |
| Description | Certify that the test matrix (document 08) covers all 16 required tests, all 14 components, all 18 configuration settings, all 16 invariants, and all 20 acceptance criteria, with traceable mappings. |
| Evidence required | Test matrix completeness report; coverage report (16/16 required tests, 14/14 components, 18/18 settings, 16/16 invariants, 20/20 ACs). |
| Verification method | CA review; AR review. |
| Pass criteria | All coverage targets met (100%); all mappings traceable; no gaps in coverage. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), CA (certification), AR (review) |
| ADR refs | §7, §9, §11 |

### CG-DOC-06 — Operational Runbooks Complete

| Field | Value |
|---|---|
| Gate ID | CG-DOC-06 |
| Description | Certify that operational runbooks exist for: outage declaration, continuation monitoring, reconciliation, conflict review, recovery protocol, emergency freeze, rollback, and key rotation. |
| Evidence required | Runbook completeness report; runbook review sign-off (OR). |
| Verification method | OR review; CA review. |
| Pass criteria | All 8 runbooks exist, are reviewed, and are accessible to on-call operators. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), OR (review), CA (certification) |
| ADR refs | §2.15 (document 10) |

### CG-DOC-07 — Certification Evidence Package Complete

| Field | Value |
|---|---|
| Gate ID | CG-DOC-07 |
| Description | Certify that the certification evidence package is complete: all gate evidence, test results, review sign-offs, residual risk acceptances, and the invariant enforcement matrix are compiled and appended to the immutable audit ledger. |
| Evidence required | Evidence package completeness report; audit ledger append confirmation. |
| Verification method | CA review; audit ledger verification. |
| Pass criteria | Evidence package complete; all 108 gates have evidence; package appended to immutable audit ledger; never truncated. |
| Blocking status | BLOCKING |
| Responsible party | CA (certification), CO (evidence) |
| ADR refs | §2.13, §13 |

---

## 11. Operational Readiness Gates (CG-OPS-01 through CG-OPS-08)

Operational readiness gates verify that the system is ready for production operation, including monitoring, alerting, incident response, and rollback capability.

### CG-OPS-01 — Monitoring and Alerting

| Field | Value |
|---|---|
| Gate ID | CG-OPS-01 |
| Description | Certify that monitoring and alerting cover all 14 components, all continuation lifecycle events, all invariant violations, and all security events, with dashboards and alerts configured. |
| Evidence required | Monitoring coverage report (14/14 components); alert configuration report; dashboard review sign-off (OR). |
| Verification method | OR review; CA review. |
| Pass criteria | All components monitored; alerts for invariant violations, security events, outage declarations, continuation starts, reconciliation failures, conflict queue growth; dashboards accessible. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), OR (review), CA (certification) |
| ADR refs | §2.13, §2.15 (document 10) |

### CG-OPS-02 — Incident Response Procedures

| Field | Value |
|---|---|
| Gate ID | CG-OPS-02 |
| Description | Certify that incident response procedures exist for: false outage, unauthorized continuation, split-brain conflict, audit ledger corruption, key compromise, tenant isolation violation, and emergency freeze. |
| Evidence required | Incident response procedure documentation; tabletop exercise completion report. |
| Verification method | OR review; CA review. |
| Pass criteria | All 7 incident scenarios have procedures; tabletop exercise completed; incident commander authority documented (no Sigma gate modification authority). |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), OR (review), CA (certification) |
| ADR refs | §2.15 (document 10 §11) |

### CG-OPS-03 — Rollback Capability

| Field | Value |
|---|---|
| Gate ID | CG-OPS-03 |
| Description | Certify that rollback procedures exist for each phase and that the emergency freeze procedure can disable the entire continuation subsystem immediately. |
| Evidence required | Rollback procedure documentation (document 10); emergency freeze test report; feature flag default-OFF verification. |
| Verification method | OR review; CA review; emergency freeze drill. |
| Pass criteria | All phase rollbacks documented and tested; emergency freeze disables continuation within 30 seconds; all feature flags default OFF. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), OR (review), CA (certification) |
| ADR refs | §2.4 (document 10 §11) |

### CG-OPS-04 — Key Management Operations

| Field | Value |
|---|---|
| Gate ID | CG-OPS-04 |
| Description | Certify that key management operations (rotation, revocation, backup) are documented and tested for Brain, witness, and executor signing keys. |
| Evidence required | Key management runbook; key rotation test report; key revocation test report. |
| Verification method | SR review; OR review; CA review. |
| Pass criteria | Key rotation documented and tested; key revocation propagates via revocation stream; key backup tested; access logging enabled. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), SR (review), OR (review), CA (certification) |
| ADR refs | §2.1.4, §2.8 (document 06 T15) |

### CG-OPS-05 — Database Migration Reversibility

| Field | Value |
|---|---|
| Gate ID | CG-OPS-05 |
| Description | Certify that all database migrations are reversible (tested forward and backward in CI) and that the PostgreSQL bootstrap certification check passes. |
| Evidence required | Migration reversibility test report; PostgreSQL bootstrap certification report. |
| Verification method | OR review; CA review. |
| Pass criteria | All migrations reversible; bootstrap certification passes; no irreversible migrations. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), OR (review), CA (certification) |
| ADR refs | (document 10 §7) |

### CG-OPS-06 — On-Call Readiness

| Field | Value |
|---|---|
| Gate ID | CG-OPS-06 |
| Description | Certify that on-call operators are trained on continuation subsystem operations, including conflict review, manual review queue, and emergency procedures. |
| Evidence required | Training completion report; on-call rotation documentation. |
| Verification method | OR review. |
| Pass criteria | On-call operators trained; rotation documented; runbooks accessible. |
| Blocking status | BLOCKING |
| Responsible party | OR (review), CA (certification) |
| ADR refs | §2.6.3.4, §2.15 (document 10) |

### CG-OPS-07 — Staging End-to-End Validation

| Field | Value |
|---|---|
| Gate ID | CG-OPS-07 |
| Description | Certify that the full recovery protocol (ADR §2.15) is testable end-to-end in staging, including all 10 steps, with no manual intervention required for the happy path. |
| Evidence required | Staging end-to-end recovery protocol test report; CERT-001, CERT-002 pass on staging. |
| Verification method | OR review; CA review. |
| Pass criteria | Full recovery protocol executes end-to-end in staging; all 10 steps; happy path requires no manual intervention. |
| Blocking status | BLOCKING |
| Responsible party | CO (evidence), OR (staging), CA (certification) |
| ADR refs | §2.15, §13 |

### CG-OPS-08 — Canary Readiness

| Field | Value |
|---|---|
| Gate ID | CG-OPS-08 |
| Description | Certify that canary deployment procedures are documented and that canary success criteria (72 hours, no alerts) are defined. |
| Evidence required | Canary procedure documentation; canary success criteria report. |
| Verification method | OR review. |
| Pass criteria | Canary procedures documented; success criteria defined (72 hours, no SEV-1/SEV-2 alerts); rollback from canary tested. |
| Blocking status | NON-BLOCKING (may be waived with OR approval if canary is deferred, but production ramp requires this gate) |
| Responsible party | OR (review), CA (certification) |
| ADR refs | (document 10 §12) |

---

## 12. Certification Process

### 12.1 Who Certifies

| Role | Certification responsibility |
|---|---|
| Component Owner (CO) | Implements components, writes and runs tests, compiles evidence, submits evidence to the CA. The CO does NOT self-certify. |
| Certification Authority (CA) | Independent body that reviews all evidence, runs independent verification where feasible, issues the certification decision for each gate. The CA must not be the implementing team. |
| Architecture Review (AR) | Verifies design conformance, accepts residual risks for Critical-impact threats, accepts fault model (BFT/CFT), reviews non-goals, approves non-blocking gate waivers. |
| Security Review (SR) | Verifies threat mitigation, attack-vector testing, STRIDE coverage, key management, RLS enforcement, clock defenses, append-only enforcement. |
| Operations Review (OR) | Verifies monitoring, alerting, runbooks, incident response, rollback, key management operations, staging validation, on-call readiness, canary procedures. |
| Principal (P) | Authorizes the final Sigma gate state transition and the unblock ADR. The Principal is the final authority per ADR-MC-001 §10. |

### 12.2 Evidence Requirements

Evidence for each gate must include:

1. **Test results** — automated test execution output (pytest) showing pass/fail status for all tests referenced by the gate. Results must be reproducible (same commit, same environment).
2. **Conformance reports** — interface conformance (document 03), state machine conformance (document 04), sequence conformance (document 05).
3. **Review sign-offs** — AR, SR, OR sign-off where required by the gate.
4. **Residual risk acceptance** — for all Critical-impact threats (T1, T4, T8, T10, T12, T14, T15, T18, T19, T20, T21, T23), AR must explicitly accept the documented residual risk.
5. **Completeness reports** — coverage reports confirming 100% coverage of components, invariants, acceptance criteria, threats, and configuration settings.
6. **Audit ledger append** — all certification evidence is appended to the immutable audit ledger and never truncated (invariant 11).

All evidence is immutable once submitted. Evidence is versioned by commit hash. If the implementation changes after evidence is submitted, the affected gates must be re-evaluated.

### 12.3 Gate Sequencing

Certification gates are sequenced in dependency order. A later gate may not be evaluated until all its prerequisite gates have PASSED. The sequence mirrors the test execution order in document 08 §16 and the phase go/no-go gates in document 10.

```
Phase 1: Component Certification (CG-C01 – CG-C14)
  │  All 14 component gates PASS
  ▼
Phase 2: Integration Certification (CG-INT-01 – CG-INT-12)
  │  All 12 integration gates PASS
  ▼
Phase 3: Security Certification (CG-SEC-T01 – CG-SEC-T23)
  │  All 23 security gates PASS
  ▼
Phase 4: Invariant Verification (CG-INV-I01 – CG-INV-I15, CG-INV-I3a)
  │  All 16 invariant gates PASS
  ▼
Phase 5: Acceptance Criteria Verification (CG-AC-01 – CG-AC-20)
  │  All 20 acceptance criteria gates PASS
  ▼
Phase 6: Performance and Scalability (CG-PERF-01 – CG-PERF-08)
  │  All 6 blocking performance gates PASS; 2 non-blocking gates PASS or WAIVED
  ▼
Phase 7: Documentation Completeness (CG-DOC-01 – CG-DOC-07)
  │  All 7 documentation gates PASS
  ▼
Phase 8: Operational Readiness (CG-OPS-01 – CG-OPS-08)
  │  All 7 blocking operational gates PASS; 1 non-blocking gate PASS or WAIVED
  ▼
Phase 9: Certification Evidence Package (CG-DOC-07)
  │  Evidence package complete and appended to immutable audit ledger
  ▼
Phase 10: Unblock ADR (separate ADR, authored, reviewed, accepted)
  │  Documents certification evidence, invariant enforcement matrix, review board sign-off
  ▼
Phase 11: Principal Authorization
  │  Explicit Principal authorization for Sigma gate state transition
  ▼
Phase 12: Sigma Gate Transition
  │  PR modifies sigma_gate.py: GATE_STATE = "SATISFIED"
  │  is_cancellation_blocked() returns False
  │  Cancellation controls transition to ENABLED
  ▼
Phase 13: Sigma Quality Gate CI Check
  │  CI verifies SATISFIED state
  ▼
SIGMA LEASE EXPIRY CONTINUATION GATE: UNBLOCKED
```

### 12.4 What Happens on Failure

When a blocking gate FAILS, the following procedure applies:

1. **Immediate halt.** The certification process halts at the failing gate. No subsequent gates in the sequence are evaluated until the failing gate is resolved.
2. **Root cause analysis.** The CO performs root cause analysis and documents the failure in the certification evidence package.
3. **Remediation.** The CO fixes the underlying issue (code, configuration, documentation, or test).
4. **Re-evaluation.** The CA re-evaluates the gate with new evidence. If the gate references tests, the tests must be re-run on the updated commit.
5. **Upstream re-evaluation.** If the failure affects a prior gate (e.g., a component fix changes integration behavior), the CA determines which prior gates must be re-evaluated.
6. **Sigma gate remains BLOCKED.** The Sigma gate remains BLOCKED until ALL blocking gates PASS. No partial unblock is permitted.
7. **Failure logging.** All failures, root cause analyses, and remediations are appended to the immutable audit ledger.

For non-blocking gates that FAIL:

1. The failure is documented.
2. The CO may request a waiver from the AR (or OR for operational gates) with documented justification.
3. If the waiver is granted, the gate is marked WAIVED with the justification recorded.
4. If the waiver is denied, the gate is treated as blocking until it PASSES.

### 12.5 Independent Verification

The CA must perform independent verification for at least the following:

- Re-run the full test suite on the certified commit and confirm all tests pass.
- Spot-check at least 3 component interfaces against document 03.
- Spot-check at least 3 state machines against document 04.
- Verify the audit ledger hash-chain integrity from genesis to the latest event.
- Verify that the Sigma gate is still BLOCKED before the unblock ADR is accepted.
- Verify that no runtime code was deployed during the planning phase (non-goals, AC20).

### 12.6 Recertification Triggers

Recertification of affected gates is required when:

- Any component implementation changes after its gate PASSED.
- Any configuration setting (ADR §9.2) changes.
- Any interface specification (document 03) changes.
- Any threat model (document 06) threat is added or its residual risk changes.
- Any ADR amendment affecting ADR-MC-001 is accepted.
- The fault model (BFT/CFT) changes.

The CA determines the scope of recertification based on the change's blast radius.

---

## 13. Certification Checklist

The following checklist is used by the CA to certify that all gates have passed before recommending the Sigma gate for unblocking. Each item must be checked PASSED (or WAIVED for non-blocking gates with AR/OR approval) before the certification is complete.

### 13.1 Component Certification (14 gates)

- [ ] CG-C01 — Signed lease token service PASSED
- [ ] CG-C02 — Continuation capability service PASSED
- [ ] CG-C03 — Brain heartbeat endpoint PASSED
- [ ] CG-C04 — Witness statement service PASSED
- [ ] CG-C05 — Executor local state cache PASSED
- [ ] CG-C06 — Revocation stream PASSED
- [ ] CG-C07 — Policy snapshot registry PASSED
- [ ] CG-C08 — Continuation journal store PASSED
- [ ] CG-C09 — Completion receipt service PASSED
- [ ] CG-C10 — Reconciliation engine PASSED
- [ ] CG-C11 — Conflict review queue PASSED
- [ ] CG-C12 — Audit event pipeline PASSED
- [ ] CG-C13 — Downstream effect identity layer PASSED
- [ ] CG-C14 — Signed time-anchor service PASSED

### 13.2 Integration Certification (12 gates)

- [ ] CG-INT-01 — Lease and capability lifecycle integration PASSED
- [ ] CG-INT-02 — Outage detection integration PASSED
- [ ] CG-INT-03 — Eligibility decision integration PASSED
- [ ] CG-INT-04 — Continuation execution and journal integration PASSED
- [ ] CG-INT-05 — Completion reporting integration PASSED
- [ ] CG-INT-06 — Reconciliation integration PASSED
- [ ] CG-INT-07 — Split-brain detection and resolution integration PASSED
- [ ] CG-INT-08 — Recovery protocol integration PASSED
- [ ] CG-INT-09 — Replay authorization integration PASSED
- [ ] CG-INT-10 — Revocation and policy integration PASSED
- [ ] CG-INT-11 — Tenant isolation integration PASSED
- [ ] CG-INT-12 — Side-effect class enforcement integration PASSED

### 13.3 Security Certification (23 gates)

- [ ] CG-SEC-T01 — Executor continues without capability PASSED
- [ ] CG-SEC-T02 — Executor continues without Brain outage PASSED
- [ ] CG-SEC-T03 — Executor continues without local state sufficiency PASSED
- [ ] CG-SEC-T04 — Multiple executors continue same command PASSED
- [ ] CG-SEC-T05 — Executor produces duplicate external effects PASSED
- [ ] CG-SEC-T06 — Executor lies about continuation outcome PASSED
- [ ] CG-SEC-T07 — Brain recovers during continuation PASSED
- [ ] CG-SEC-T08 — Cross-tenant continuation PASSED
- [ ] CG-SEC-T09 — Continuation runs unbounded PASSED
- [ ] CG-SEC-T10 — Stale revocation/cancellation knowledge PASSED
- [ ] CG-SEC-T11 — Pinned policy exploited PASSED
- [ ] CG-SEC-T12 — Clock skew/rollback extends authority PASSED
- [ ] CG-SEC-T13 — Silent continuation PASSED
- [ ] CG-SEC-T14 — Witness quorum compromised PASSED
- [ ] CG-SEC-T15 — Key compromise PASSED
- [ ] CG-SEC-T16 — Database corruption PASSED
- [ ] CG-SEC-T17 — Network partition scenarios PASSED
- [ ] CG-SEC-T18 — Clock manipulation (NTP, monotonic discontinuity) PASSED
- [ ] CG-SEC-T19 — Capability token replay PASSED
- [ ] CG-SEC-T20 — Witness collusion PASSED
- [ ] CG-SEC-T21 — Audit ledger tampering PASSED
- [ ] CG-SEC-T22 — Configuration drift PASSED
- [ ] CG-SEC-T23 — Multi-tenant data leakage PASSED

### 13.4 Invariant Verification (16 gates)

- [ ] CG-INV-I01 — No authoritative effects without valid lease PASSED
- [ ] CG-INV-I02 — Expired lease cannot authorize PASSED
- [ ] CG-INV-I03 — Capability temporal bounds PASSED
- [ ] CG-INV-I3a — Only latest-lease capability exercisable PASSED
- [ ] CG-INV-I04 — Continuation never default PASSED
- [ ] CG-INV-I05 — Continuation within bounded envelope PASSED
- [ ] CG-INV-I06 — Every continuation produces signed receipt PASSED
- [ ] CG-INV-I07 — Every continuation reconciled before terminal PASSED
- [ ] CG-INV-I08 — Conflicts never resolve silently PASSED
- [ ] CG-INV-I09 — Cross-tenant continuation impossible PASSED
- [ ] CG-INV-I10 — Idempotency preserved PASSED
- [ ] CG-INV-I11 — Audit storage complete and never truncated PASSED
- [ ] CG-INV-I12 — Policy snapshot bounded to pinned hash PASSED
- [ ] CG-INV-I13 — Revocation knowledge fresh; absence not permission PASSED
- [ ] CG-INV-I14 — Time not manipulable to extend authority PASSED
- [ ] CG-INV-I15 — High-risk effects prohibited during continuation PASSED

### 13.5 Acceptance Criteria Verification (20 gates)

- [ ] CG-AC-01 — Lease and capability lifecycle separated PASSED
- [ ] CG-AC-02 — Capability unusable before expiry; bounded PASSED
- [ ] CG-AC-03 — Outage detection: 2 signals + direct + grace PASSED
- [ ] CG-AC-04 — Witness trust model fully defined PASSED
- [ ] CG-AC-05 — Eligibility explicit; default STOP PASSED
- [ ] CG-AC-06 — Continuation limits with platform/tenant bounds PASSED
- [ ] CG-AC-07 — Stable effect identity for dedup PASSED
- [ ] CG-AC-08 — Replay semantics: effect identity + reconciliation first PASSED
- [ ] CG-AC-09 — Reconciliation: 4 concerns separated PASSED
- [ ] CG-AC-10 — Receipts mandatory, signed, immutable PASSED
- [ ] CG-AC-11 — Split-brain: detect, freeze, manual review PASSED
- [ ] CG-AC-12 — Audit chain complete; never truncated PASSED
- [ ] CG-AC-13 — Tenant isolation throughout PASSED
- [ ] CG-AC-14 — Recovery protocol: detection, collection, reconciliation, refresh PASSED
- [ ] CG-AC-15 — Trusted time: skew, monotonic, signed anchors PASSED
- [ ] CG-AC-16 — Policy snapshot pinned by hash, bounded by time PASSED
- [ ] CG-AC-17 — Revocation watermark + cache-age fail-closed PASSED
- [ ] CG-AC-18 — Side effects classified; Class 3 prohibited PASSED
- [ ] CG-AC-19 — Threat model, invariants, glossary, prerequisites complete PASSED
- [ ] CG-AC-20 — Non-goals: no implementation, no deployment, no authority PASSED

### 13.6 Performance and Scalability (8 gates)

- [ ] CG-PERF-01 — Outage detection latency PASSED
- [ ] CG-PERF-02 — Continuation start latency PASSED
- [ ] CG-PERF-03 — Reconciliation throughput PASSED
- [ ] CG-PERF-04 — Audit pipeline throughput PASSED
- [ ] CG-PERF-05 — Tenant concurrency PASSED
- [ ] CG-PERF-06 — Capability validation latency PASSED
- [ ] CG-PERF-07 — Recovery protocol completion time PASSED or WAIVED (non-blocking)
- [ ] CG-PERF-08 — Witness statement validation throughput PASSED or WAIVED (non-blocking)

### 13.7 Documentation Completeness (7 gates)

- [ ] CG-DOC-01 — ADR consistency PASSED
- [ ] CG-DOC-02 — Interface specifications complete PASSED
- [ ] CG-DOC-03 — State machine documentation complete PASSED
- [ ] CG-DOC-04 — Threat model complete PASSED
- [ ] CG-DOC-05 — Test matrix complete PASSED
- [ ] CG-DOC-06 — Operational runbooks complete PASSED
- [ ] CG-DOC-07 — Certification evidence package complete PASSED

### 13.8 Operational Readiness (8 gates)

- [ ] CG-OPS-01 — Monitoring and alerting PASSED
- [ ] CG-OPS-02 — Incident response procedures PASSED
- [ ] CG-OPS-03 — Rollback capability PASSED
- [ ] CG-OPS-04 — Key management operations PASSED
- [ ] CG-OPS-05 — Database migration reversibility PASSED
- [ ] CG-OPS-06 — On-call readiness PASSED
- [ ] CG-OPS-07 — Staging end-to-end validation PASSED
- [ ] CG-OPS-08 — Canary readiness PASSED or WAIVED (non-blocking)

### 13.9 Final Authorization

- [ ] All 105 blocking gates PASSED
- [ ] All 3 non-blocking gates PASSED or WAIVED with AR/OR approval
- [ ] Certification evidence package appended to immutable audit ledger
- [ ] Unblock ADR authored, reviewed, and accepted (documents certification evidence, invariant enforcement matrix, review board sign-off)
- [ ] Explicit Principal authorization for Sigma gate state transition
- [ ] Sigma Quality Gate CI check passes (verifies SATISFIED state after PR)

---

## 14. Cross-Reference Summary

### 14.1 Gate-to-ADR Section Mapping

| Gate category | ADR sections | Count |
|---|---|---|
| Component (CG-C##) | §9.1 | 14 |
| Integration (CG-INT-##) | §2.1–§2.15 | 12 |
| Security (CG-SEC-T##) | §6.3; document 06 | 23 |
| Invariant (CG-INV-I##) | §7 | 16 |
| Acceptance criteria (CG-AC-##) | §11 | 20 |
| Performance (CG-PERF-##) | §2.4, §2.14 | 8 |
| Documentation (CG-DOC-##) | §8, §9, §10 | 7 |
| Operational (CG-OPS-##) | §2.15; document 10 | 8 |
| **Total** | | **108** |

### 14.2 Gate-to-Test Mapping

| Gate category | Primary test refs | Certification test refs |
|---|---|---|
| Component (CG-C##) | UT-C##-*, RT-##.* | CERT-008, CERT-010, CERT-015, CERT-016 |
| Integration (CG-INT-##) | INT-###, CHS-###, RES-###, REC-### | CERT-001, CERT-003, CERT-004, CERT-011, CERT-016 |
| Security (CG-SEC-T##) | SEC-###, RT-##.* | CERT-010, CERT-011, CERT-012, CERT-013, CERT-015, CERT-016 |
| Invariant (CG-INV-I##) | UT-*, RT-*, SEC-*, RES-* | CERT-005 |
| Acceptance criteria (CG-AC-##) | RT-*, UT-*, INT-*, SEC-*, REC-*, MT-* | CERT-001, CERT-003, CERT-004, CERT-006, CERT-010, CERT-011, CERT-015, CERT-016, CERT-018 |
| Performance (CG-PERF-##) | Performance benchmarks | — |
| Documentation (CG-DOC-##) | Coverage reports | CERT-005, CERT-006, CERT-008, CERT-009 |
| Operational (CG-OPS-##) | Staging tests, CERT-001, CERT-002 | CERT-001, CERT-002 |

### 14.3 Blocking Gate Count Summary

| Category | Blocking | Non-blocking | Total |
|---|---|---|---|
| Component | 14 | 0 | 14 |
| Integration | 12 | 0 | 12 |
| Security | 23 | 0 | 23 |
| Invariant | 16 | 0 | 16 |
| Acceptance criteria | 20 | 0 | 20 |
| Performance | 6 | 2 | 8 |
| Documentation | 7 | 0 | 7 |
| Operational | 7 | 1 | 8 |
| **Total** | **105** | **3** | **108** |

---

## 15. Traceability to ADR-MC-001

| Certification matrix element | ADR-MC-001 source |
|---|---|
| 14 component gates | §9.1 Required Components |
| 12 integration gates | §2.1–§2.15 (lease, outage, eligibility, continuation, reconciliation, replay, recovery, tenant isolation, side-effect classes) |
| 23 security gates | §6.3 Threat Model (T1–T14); document 06 (T15–T23) |
| 16 invariant gates | §7 Invariants (1–15 including 3a) |
| 20 acceptance criteria gates | §11 Acceptance Criteria |
| Performance gates | §2.4 Continuation Limits; §2.14 Tenant Isolation |
| Documentation gates | §8 Glossary; §9 Implementation Prerequisites; §10 Non-Goals |
| Operational gates | §2.15 Recovery Protocol; §13 Status |
| Certification process (unblock ADR + Principal authorization) | §10 Non-Goals (authorization model); §13 Status |
| Sigma gate remains BLOCKED until all blocking gates pass | §13 Status; §12 Consequences |
| Evidence appended to immutable audit ledger | §2.13 Audit Chain; invariant 11 |

---

## 16. Document Status

| Item | State |
|---|---|
| Certification matrix (108 gates) | Complete |
| Component certification gates (14) | Complete |
| Integration certification gates (12) | Complete |
| Security certification gates (23) | Complete |
| Invariant verification gates (16) | Complete |
| Acceptance criteria verification gates (20) | Complete |
| Performance and scalability gates (8) | Complete |
| Documentation completeness gates (7) | Complete |
| Operational readiness gates (8) | Complete |
| Certification process | Complete |
| Certification checklist | Complete |
| Cross-references to ADR and sibling documents | Complete |
| Runtime code | NOT AUTHORIZED |
| Test execution | NOT AUTHORIZED |
| Sigma gate unblock | NOT AUTHORIZED — gate remains BLOCKED |
| Deployment | NOT AUTHORIZED |

---

## 17. Open Questions for Implementation

The following questions are identified by this certification matrix and should be resolved during implementation:

1. **Certification Authority composition.** Who exactly constitutes the independent CA? Is it a standing review board, an ad-hoc committee, or a designated external party? (Affects all gates.)
2. **Independent verification scope.** How much independent re-testing does the CA perform versus evidence review? What tooling does the CA use? (Affects §12.5.)
3. **Performance benchmark environment.** What staging environment is used for performance gates, and how is it kept representative of production? (Affects CG-PERF-*.)
4. **Non-blocking gate waiver process.** What is the formal waiver request and approval process for CG-PERF-07, CG-PERF-08, and CG-OPS-08? (Affects §12.4.)
5. **Recertification scope determination.** What tooling or process helps the CA determine the blast radius of a change for recertification? (Affects §12.6.)
6. **Evidence package format.** What is the canonical format for the certification evidence package, and how is it appended to the immutable audit ledger? (Affects CG-DOC-07.)

These questions are planning-level and do not require resolution in this document. They are flagged for the implementation plan and subsequent ADRs.

---

*End of document.*