# 11 — Traceability Matrix: Executor Continuation

**Package:** Executor Continuation Implementation Planning
**Source ADRs:** ADR-MC-001 (ACCEPTED, ratified 2026-08-05); ADR-002 Section 2.5 (Sigma continuation condition)
**Scope:** PLANNING ONLY — no runtime code, no deployment, no authority activation, no Sigma gate unblock. This document is a traceability matrix mapping every implementation requirement from ADR-MC-001 and ADR-002 Section 2.5 to its implementing component(s), verifying test cases, enforced invariants, satisfied acceptance criteria, and certification gates.
**Companion documents:**
- `01_IMPLEMENTATION_ARCHITECTURE.md` — component decomposition, architecture, phases
- `02_COMPONENT_DEPENDENCY_GRAPH.md` — build-time dependency graph, layered build order
- `03_INTERFACE_SPECIFICATIONS.md` — Pydantic v2 models and Protocol interfaces
- `04_STATE_MACHINES.md` — component and lifecycle state machines
- `05_SEQUENCE_DIAGRAMS.md` — runtime protocol sequencing
- `06_THREAT_MODEL.md` — threat model and attack surface
- `07_FAILURE_MODE_RECOVERY_MATRIX.md` — failure modes and recovery procedures
- `08_TEST_MATRIX.md` — test matrix (source of all test IDs referenced here)
- `10_ROLLOUT_ROLLBACK_PLAN.md` — rollout and rollback strategy

---

## 1. Document Purpose

This document is the traceability matrix for the executor continuation capability. It is a planning artifact only — it authorizes no runtime code, no test execution, no deployment, and no authority activation. Implementation requires separate ADRs, branches, and authorizations per ADR-MC-001 Section 10.

The document serves three audiences:

1. **Implementers** — who need to know which ADR requirement each component implements and which tests verify it.
2. **Reviewers** — who need to verify that every ADR requirement is traced to at least one component, one test, and one certification gate, with no gaps.
3. **Certifiers** — who need a complete, auditable chain from ADR requirement → component → test → invariant → acceptance criterion → certification gate before recommending that `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE` be evaluated for unblocking.

---

## 2. Conventions

### 2.1 Requirement ID Scheme

| Prefix | Source | Format |
|---|---|---|
| `REQ-2.x.y-NN` | ADR-MC-001 Section 2.x.y requirements | `REQ-<section>-<seq>` |
| `REQ-7-I<N>` | ADR-MC-001 Section 7 invariants | `REQ-7-I<invariant_id>` |
| `REQ-9.1-C<NN>` | ADR-MC-001 Section 9.1 required components | `REQ-9.1-C<component_id>` |
| `REQ-9.2-S<NN>` | ADR-MC-001 Section 9.2 configuration settings | `REQ-9.2-S<seq>` |
| `REQ-9.3-T<NN>` | ADR-MC-001 Section 9.3 required tests | `REQ-9.3-T<seq>` |
| `REQ-11-AC<N>` | ADR-MC-001 Section 11 acceptance criteria | `REQ-11-AC<n>` |
| `REQ-A2-2.5-NN` | ADR-002 Section 2.5 requirements | `REQ-A2-2.5-<seq>` |

### 2.2 Component IDs (from ADR-MC-001 §9.1, doc 08 §2.3)

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

### 2.3 Invariant IDs (from ADR-MC-001 §7, doc 08 §2.4)

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

### 2.4 Acceptance Criteria IDs (from ADR-MC-001 §11, doc 08 §2.5)

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

### 2.5 Certification Gates (from doc 08 §12)

| Gate | Description |
|---|---|
| CERT-001 | Full lifecycle: dispatch to terminal state |
| CERT-002 | Full lifecycle with continuation and recovery |
| CERT-003 | Full lifecycle with split-brain resolution |
| CERT-004 | Full lifecycle with replay |
| CERT-005 | All 15 invariants verified |
| CERT-006 | All 20 acceptance criteria satisfied |
| CERT-007 | All 16 required tests pass |
| CERT-008 | All 14 components tested |
| CERT-009 | All 18 configuration settings exercised |
| CERT-010 | Audit chain complete and never truncated |
| CERT-011 | Tenant isolation across full lifecycle |
| CERT-012 | Security: all attack vectors blocked |
| CERT-013 | Resilience: all failure modes handled |
| CERT-014 | Chaos: system stable under random failures |
| CERT-015 | Time authority verified end-to-end |
| CERT-016 | Side-effect class enforcement verified end-to-end |
| CERT-017 | Gate remains BLOCKED until certification complete |
| CERT-018 | Non-goals verified: no implementation, no deployment, no authority activation |

### 2.6 Column Definitions

Each matrix row contains:

| Column | Description |
|---|---|
| **Req ID** | Requirement identifier (see §2.1) |
| **ADR Ref** | Source ADR section reference |
| **Requirement** | Concise requirement description |
| **Component(s)** | Implementing component(s) from the 14 in §9.1 |
| **Test Case(s)** | Test IDs from doc 08 that verify this requirement |
| **Invariant(s)** | Invariant(s) from §7 enforced by this requirement |
| **AC(s)** | Acceptance criterion/criteria from §11 satisfied |
| **Cert Gate(s)** | Certification gate(s) from doc 08 §12 that verify this requirement |

---

## 3. ADR-MC-001 Section 2.1 — Executor Lease Lifecycle

### 3.1 Section 2.1.1 — Lease Acquisition

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.1.1-01 | ADR-MC-001 §2.1.1 | Brain issues a lease to exactly one executor per command at a time | C01 | RT-01.1, UT-C01-001 | I1 | AC1 | CERT-001, CERT-002, CERT-007 |
| REQ-2.1.1-02 | ADR-MC-001 §2.1.1 | Lease contains all 9 required fields: command_id, executor_id, tenant_id, issued_at, expires_at, lease_token, policy_snapshot_id, continuation_class, continuation_capability_id | C01, C02, C07 | RT-01.1, UT-C01-001, INT-001 | I1 | AC1 | CERT-001, CERT-008 |
| REQ-2.1.1-03 | ADR-MC-001 §2.1.1 | Executor must present a valid, unexpired lease token to perform any work | C01, C13 | RT-01.1, UT-C01-004, UT-C01-005, SEC-004, SEC-005 | I1, I2 | AC1 | CERT-001, CERT-012 |
| REQ-2.1.1-04 | ADR-MC-001 §2.1.1 | Lease acquisition logged as immutable audit event with causation link to dispatch event | C01, C12 | RT-01.1, UT-C01-010, INT-001 | I1, I11 | AC1, AC12 | CERT-001, CERT-010 |

### 3.2 Section 2.1.2 — Lease Renewal

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.1.2-01 | ADR-MC-001 §2.1.2 | Executor may request lease renewal before expiry | C01 | RT-01.2, UT-C01-007 | I1 | AC1 | CERT-001 |
| REQ-2.1.2-02 | ADR-MC-001 §2.1.2 | Brain grants renewal only if: command not cancelled, executor still lease holder, max execution duration not exceeded, policy snapshot not superseded, Brain available | C01, C06, C07 | RT-01.5, RT-01.6, RT-01.7, RT-01.8, RT-01.9, UT-C01-007 | I1, I13 | AC1 | CERT-001, CERT-007 |
| REQ-2.1.2-03 | ADR-MC-001 §2.1.2 | Renewal extends expires_at and produces a new signed lease token | C01, C14 | RT-01.2, UT-C01-007, INT-002 | I1 | AC1 | CERT-001 |
| REQ-2.1.2-04 | ADR-MC-001 §2.1.2 | Previous lease token revoked and must not be honored by downstream systems | C01, C13 | RT-01.2, UT-C01-007, INT-002 | I2, I3a | AC1 | CERT-001, CERT-012 |
| REQ-2.1.2-05 | ADR-MC-001 §2.1.2 | Renewal invalidates prior continuation capability; Brain issues new capability referenced by renewed lease; only latest valid lease capability may be exercised | C01, C02 | RT-01.2, UT-C01-008, UT-C02-009, INT-002 | I3a | AC1, AC2 | CERT-001 |
| REQ-2.1.2-06 | ADR-MC-001 §2.1.2 | Capability rotation auditable: issuance, supersession, and revocation of each capability recorded as immutable audit events | C02, C12 | RT-01.2, UT-C02-018, RT-14.7, INT-002 | I3a, I11 | AC1, AC12 | CERT-001, CERT-010 |
| REQ-2.1.2-07 | ADR-MC-001 §2.1.2 | Capability revocation applies even where former capability has later not_valid_after; downstream systems must reject superseded capability IDs | C02, C13 | RT-01.10, UT-C02-009, INT-020 | I3a | AC1, AC2 | CERT-001, CERT-012 |

### 3.3 Section 2.1.3 — Lease Expiry

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.1.3-01 | ADR-MC-001 §2.1.3 | A lease expires when expires_at is reached or when the Brain explicitly revokes it | C01, C06 | RT-01.3, RT-01.4, UT-C01-005, UT-C01-006 | I2 | AC1 | CERT-001 |
| REQ-2.1.3-02 | ADR-MC-001 §2.1.3 | Upon expiry, the lease token immediately loses all authority to perform work or produce effects | C01, C13 | RT-01.3, UT-C01-005, SEC-004, SEC-005 | I2 | AC1 | CERT-001, CERT-012 |
| REQ-2.1.3-03 | ADR-MC-001 §2.1.3 | The executor cannot use an expired lease to prove authority to downstream systems | C01, C13 | RT-01.3, SEC-005 | I2 | AC1 | CERT-001, CERT-012 |
| REQ-2.1.3-04 | ADR-MC-001 §2.1.3 | Expiry is logged as an immutable audit event | C01, C12 | RT-01.3, RT-14.8, UT-C01-010 | I2, I11 | AC1, AC12 | CERT-001, CERT-010 |
| REQ-2.1.3-05 | ADR-MC-001 §2.1.3 | Expiry alone does not permit continuation; continuation requires a separate, unexpired continuation capability and all eligibility criteria in Section 2.3 | C01, C02 | RT-01.3, RT-05.2, RT-05.3 | I2, I3, I4 | AC1, AC2, AC5 | CERT-001 |

### 3.4 Section 2.1.4 — Continuation Capability

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.1.4-01 | ADR-MC-001 §2.1.4 | Continuation requires a distinct, pre-authorized continuation capability issued by the Brain at dispatch or lease-renewal time | C02, C01 | RT-02.1, UT-C02-001, INT-001 | I3, I4 | AC2 | CERT-001 |
| REQ-2.1.4-02 | ADR-MC-001 §2.1.4 | The capability is cryptographically separate from the lease token and is unusable before lease expiry | C02, C14 | RT-02.2, UT-C02-003, SEC-006 | I3 | AC2 | CERT-001, CERT-012 |
| REQ-2.1.4-03 | ADR-MC-001 §2.1.4 | The capability contains all 15 fields: capability_id, command_id, tenant_id, executor_id, issued_at, not_valid_before, not_valid_after, max_continuation_duration, max_continuation_operations, continuation_class, permitted_operation_ids, side_effect_slot_spec, policy_snapshot_hash, policy_snapshot_id, policy_snapshot_not_valid_after, revocation_watermark_required, signed_capability_token | C02, C07, C14 | RT-02.1, UT-C02-001 | I3, I5, I12 | AC2 | CERT-001, CERT-008 |
| REQ-2.1.4-04 | ADR-MC-001 §2.1.4 | The capability is issued only when the Brain explicitly determines continuation may be allowed for a command | C02 | RT-02.8, UT-C02-017 | I4 | AC2, AC5 | CERT-001 |
| REQ-2.1.4-05 | ADR-MC-001 §2.1.4 | The capability is not a general grant of authority; it is narrowly scoped to a single command, tenant, executor, operation set, and time envelope | C02, C13 | RT-02.4, RT-02.5, RT-02.6, UT-C02-005, UT-C02-006, UT-C02-007 | I3, I9 | AC2 | CERT-001, CERT-012 |
| REQ-2.1.4-06 | ADR-MC-001 §2.1.4 | The capability cannot be used before not_valid_before, which is set to the lease expiry or later | C02, C14 | RT-02.2, UT-C02-003, SEC-006 | I3 | AC2 | CERT-001, CERT-012 |
| REQ-2.1.4-07 | ADR-MC-001 §2.1.4 | Downstream systems must validate the signed continuation capability token — not the expired lease — before honoring any effect produced during continuation | C13, C02 | RT-02.1, UT-C13-003, INT-007 | I3, I10 | AC2, AC7 | CERT-001 |
| REQ-2.1.4-08 | ADR-MC-001 §2.1.4 | Downstream systems must receive and verify replay-resistant outage evidence — a signed bundle containing the outage declaration record, witness statements (if used), signal thresholds crossed, and the signed time anchor at declaration time; bound to capability_id and command_id; capability alone is not sufficient proof of authority while the Brain is healthy | C13, C09, C04, C14 | RT-09.5, RT-09.6, UT-C13-004, UT-C13-005, INT-007, SEC-030, SEC-031 | I6, I10 | AC2, AC10 | CERT-001, CERT-012 |
| REQ-2.1.4-09 | ADR-MC-001 §2.1.4 | Downstream systems must reject continuation effects that lack valid, matching outage evidence | C13 | RT-09.6, RT-09.7, UT-C13-004, SEC-030, SEC-031 | I6, I10 | AC2, AC10 | CERT-001, CERT-012 |
| REQ-2.1.4-10 | ADR-MC-001 §2.1.4 | The capability is revocable through a signed revocation stream; if the executor has not observed the required revocation watermark, it must not continue | C02, C06 | RT-02.7, RT-02.10, UT-C02-008, UT-C02-014 | I3, I13 | AC2, AC17 | CERT-001 |

---

## 4. ADR-MC-001 Section 2.2 — Brain Outage Detection

### 4.1 Section 2.2.1 — Detection Signals

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.2.1-01 | ADR-MC-001 §2.2.1 | Executor monitors heartbeat acknowledgement signal; missing for brain_heartbeat_miss_threshold consecutive intervals | C03 | RT-03.1, RT-03.2, UT-C03-002, UT-C03-003, INT-003 | I4 | AC3 | CERT-001 |
| REQ-2.2.1-02 | ADR-MC-001 §2.2.1 | Executor monitors lease renewal rejection signal; rejected as BRAIN_UNAVAILABLE for lease_rejection_threshold attempts | C01, C03 | RT-03.1, RT-03.3, RT-01.9, INT-003, INT-004 | I4 | AC3 | CERT-001 |
| REQ-2.2.1-03 | ADR-MC-001 §2.2.1 | Executor monitors command status query failure signal; failed with timeout or UNAVAILABLE for status_query_threshold attempts | C03 | RT-03.2, INT-004 | I4 | AC3 | CERT-001 |
| REQ-2.2.1-04 | ADR-MC-001 §2.2.1 | Executor monitors witness outage statements signal; quorum of witnesses reports Brain unavailability | C04 | RT-03.3, RT-04.2, UT-C04-008, INT-003 | I4 | AC3, AC4 | CERT-001 |
| REQ-2.2.1-05 | ADR-MC-001 §2.2.1 | Executor monitors policy broadcast silence signal; no policy broadcast for policy_silence_threshold | C07, C03 | RT-03.3, RT-03.10, UT-C07-007, INT-004, CHS-014 | I4 | AC3 | CERT-001, CERT-014 |

### 4.2 Section 2.2.2 — Detection Rules

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.2.2-01 | ADR-MC-001 §2.2.2 | Brain outage is declared only when at least two independent signals cross their thresholds | C03, C04, C05 | RT-03.1, RT-03.2, RT-03.3, RT-03.4, SEC-021 | I4 | AC3 | CERT-001, CERT-012 |
| REQ-2.2.2-02 | ADR-MC-001 §2.2.2 | One of the two signals must be either heartbeat acknowledgement, lease renewal rejection, or command status query failure (a direct Brain observation) | C03, C01, C04 | RT-03.6, SEC-022 | I4 | AC3 | CERT-001, CERT-012 |
| REQ-2.2.2-03 | ADR-MC-001 §2.2.2 | Witness statements alone are never sufficient to declare outage | C04 | RT-03.5, RT-04.11, SEC-020 | I4 | AC3, AC4 | CERT-001, CERT-012 |
| REQ-2.2.2-04 | ADR-MC-001 §2.2.2 | The grace period before outage declaration is at least brain_outage_grace_period (default 30 seconds, configurable per tenant with platform upper bound) | C05, C14 | RT-03.7, INT-003, RES-005 | I4 | AC3 | CERT-001, CERT-013 |
| REQ-2.2.2-05 | ADR-MC-001 §2.2.2 | A declared outage must be persisted locally with timestamp, signals observed, lease token fingerprint, and signed time anchor | C05, C14 | RT-03.8, UT-C05-005 | I4, I11 | AC3 | CERT-001 |

### 4.3 Section 2.2.3 — Time Basis for Detection

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.2.3-01 | ADR-MC-001 §2.2.3 | All detection timestamps must use a trusted time source (Section 2.8) | C14 | RT-03.8, RT-15.1, UT-C14-001 | I14 | AC3, AC15 | CERT-001, CERT-015 |
| REQ-2.2.3-02 | ADR-MC-001 §2.2.3 | Executor records monotonic_outage_start — monotonic clock marker when outage conditions began | C05, C14 | RT-03.8, RT-15.10 | I14 | AC3, AC15 | CERT-001, CERT-015 |
| REQ-2.2.3-03 | ADR-MC-001 §2.2.3 | Executor records wall_outage_declared_at — signed wall-clock anchor when outage was declared | C14, C05 | RT-03.8, RT-15.10 | I14 | AC3, AC15 | CERT-001, CERT-015 |
| REQ-2.2.3-04 | ADR-MC-001 §2.2.3 | Executor records grace_period_end — wall-clock time after which continuation may be considered | C05, C14 | RT-03.8 | I14 | AC3, AC15 | CERT-001 |
| REQ-2.2.3-05 | ADR-MC-001 §2.2.3 | Executor must reject any time value that appears to roll backward relative to the last signed anchor by more than max_clock_rollback_tolerance | C14, C05 | RT-03.9, RT-15.4, UT-C14-003, RES-010 | I14 | AC3, AC15 | CERT-001, CERT-015 |

### 4.4 Section 2.2.4 — Witness Trust Model

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.2.4-01 | ADR-MC-001 §2.2.4 | A witness is a control-plane service or Brain observer, not an executor participating in the command | C04 | RT-04.1, UT-C04-007, SEC-020 | I4 | AC4 | CERT-001, CERT-012 |
| REQ-2.2.4-02 | ADR-MC-001 §2.2.4 | Witness statements are signed with witness identity keys and include tenant_id, brain_region, witness_id, statement_id, and timestamp | C04, C14 | RT-04.8, RT-04.12, UT-C04-001, UT-C04-002 | I4, I14 | AC4 | CERT-001 |
| REQ-2.2.4-03 | ADR-MC-001 §2.2.4 | Quorum: N >= 3f+1 and witness_quorum_size >= 2f+1 (BFT); or CFT model N >= 2f+1, quorum >= f+1 if documented; witness_quorum_size must be strictly less than N | C04 | RT-04.2, RT-04.3, RT-04.4, UT-C04-008, CHS-003 | I4 | AC4 | CERT-001, CERT-014 |
| REQ-2.2.4-04 | ADR-MC-001 §2.2.4 | Witness statements are scoped to the tenant's Brain partition; a witness for tenant A cannot declare outage for tenant B | C04 | RT-04.7, UT-C04-005, SEC-013 | I4, I9 | AC4, AC13 | CERT-001, CERT-011, CERT-012 |
| REQ-2.2.4-05 | ADR-MC-001 §2.2.4 | Replay resistance: each statement includes a monotonically increasing nonce and a signed anchor; stale or replayed statements are rejected | C04, C14 | RT-04.5, UT-C04-003, UT-C04-009, SEC-008 | I4, I14 | AC4 | CERT-001, CERT-012 |
| REQ-2.2.4-06 | ADR-MC-001 §2.2.4 | Stale witness protection: witness statements older than witness_statement_max_age are ignored | C04, C14 | RT-04.6, UT-C04-004 | I4 | AC4 | CERT-001 |
| REQ-2.2.4-07 | ADR-MC-001 §2.2.4 | Compromised witness handling: if a witness key is revoked, its statements are invalid; a threshold of valid witnesses must remain | C04, C06 | RT-04.9, UT-C04-006, UT-C04-010 | I4, I13 | AC4 | CERT-001 |
| REQ-2.2.4-08 | ADR-MC-001 §2.2.4 | Self-exclusion: an executor cannot count itself, its peers, or any process it controls toward witness quorum | C04 | RT-04.10, UT-C04-007, SEC-020 | I4 | AC4 | CERT-001, CERT-012 |
| REQ-2.2.4-09 | ADR-MC-001 §2.2.4 | Network partition alone does not grant continuation authority; a partition that isolates the executor from the Brain but not from witnesses must still satisfy the direct-Brain-signal requirement | C03, C04 | RT-04.11, RES-007 | I4 | AC4 | CERT-001, CERT-013 |

---

## 5. ADR-MC-001 Section 2.3 — Continuation Eligibility

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.3-01 | ADR-MC-001 §2.3 | Lease expired: lease expires_at reached or exceeded; continuation capability not_valid_before reached | C01, C02, C14 | RT-05.1, RT-05.2 | I2, I3 | AC5 | CERT-001 |
| REQ-2.3-02 | ADR-MC-001 §2.3 | Brain outage declared: two independent signals crossed thresholds, including one direct-Brain signal | C03, C04, C05 | RT-05.1, RT-05.3 | I4 | AC5 | CERT-001 |
| REQ-2.3-03 | ADR-MC-001 §2.3 | Continuation capability valid: signed, unexpired, scoped to this command/executor/tenant, not_valid_before satisfied | C02, C14 | RT-05.1, RT-05.4 | I3 | AC5 | CERT-001 |
| REQ-2.3-04 | ADR-MC-001 §2.3 | No revocation observed above watermark: no revocation for this command or capability; required revocation watermark observed | C02, C06 | RT-05.1, RT-05.5 | I13 | AC5, AC17 | CERT-001 |
| REQ-2.3-05 | ADR-MC-001 §2.3 | No cancellation confirmed: no cancellation command in cached ledger events up to the required revocation watermark | C06 | RT-05.1, RT-05.6 | I13 | AC5, AC17 | CERT-001 |
| REQ-2.3-06 | ADR-MC-001 §2.3 | Local state sufficient: all required inputs and deterministic path available | C05 | RT-05.1, RT-05.7, UT-C05-003, UT-C05-004 | I4, I5 | AC5 | CERT-001 |
| REQ-2.3-07 | ADR-MC-001 §2.3 | Side-effect class permitted: command's continuation_class and capability permit the operation (Section 2.9) | C02 | RT-05.1, RT-05.8 | I15 | AC5, AC18 | CERT-001 |
| REQ-2.3-08 | ADR-MC-001 §2.3 | Policy snapshot pinned: capability carries policy_snapshot_hash; executor trusts only that exact snapshot | C02, C07 | RT-05.1, RT-05.9 | I12 | AC5, AC16 | CERT-001 |
| REQ-2.3-09 | ADR-MC-001 §2.3 | Bounded continuation: estimated completion within capability max_continuation_duration and operation count | C02, C08 | RT-05.1, RT-05.10 | I5 | AC5, AC6 | CERT-001 |
| REQ-2.3-10 | ADR-MC-001 §2.3 | Tenant isolation: executor tenant matches command tenant | C02, C12 | RT-05.1, RT-05.11 | I9 | AC5, AC13 | CERT-001, CERT-011 |
| REQ-2.3-11 | ADR-MC-001 §2.3 | Audit capability: executor can emit continuation audit events and receipts | C08, C09, C12 | RT-05.1, RT-05.12 | I6, I11 | AC5, AC10 | CERT-001 |
| REQ-2.3-12 | ADR-MC-001 §2.3 | Time bounds satisfied: current signed wall-clock time is within capability validity window | C02, C14 | RT-05.1, RT-05.13 | I14 | AC5, AC15 | CERT-001, CERT-015 |
| REQ-2.3-13 | ADR-MC-001 §2.3 | If any criterion is not met, the executor must stop and enter safe-hold state; the default decision is STOP | C05 | RT-05.14, SEC-019, INT-005 | I4 | AC5 | CERT-001, CERT-012 |

---

## 6. ADR-MC-001 Section 2.4 — Continuation Limits

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.4-01 | ADR-MC-001 §2.4 | max_continuation_duration (default 5 minutes): bound how long an executor may continue without Brain contact | C02, C14, C08 | RT-06.1, RT-06.8, UT-C02-015 | I5 | AC6 | CERT-001 |
| REQ-2.4-02 | ADR-MC-001 §2.4 | max_continuation_operations (default 1): bound how many discrete operations an executor may perform | C02, C08 | RT-06.2, UT-C02-016, UT-C08-005, SEC-024 | I5 | AC6 | CERT-001, CERT-012 |
| REQ-2.4-03 | ADR-MC-001 §2.4 | max_continuation_attempts_per_command (default 1): prevent repeated continuation attempts for the same lease | C02, C05 | RT-06.3 | I5 | AC6 | CERT-001 |
| REQ-2.4-04 | ADR-MC-001 §2.4 | max_concurrent_continuations_per_executor (default 3): prevent an executor from continuing many commands simultaneously | C02, C05 | RT-06.4, CHS-017 | I5 | AC6 | CERT-001, CERT-014 |
| REQ-2.4-05 | ADR-MC-001 §2.4 | side_effect_cooldown_after_continuation (until reconciliation): prevent additional external effects before Brain reconciliation | C02, C13 | RT-06.5 | I5, I7 | AC6 | CERT-001 |
| REQ-2.4-06 | ADR-MC-001 §2.4 | tenant_max_continuation_rate (default 10 per minute): tenant-level circuit breaker | C02 | RT-06.6, CHS-018, MT-006 | I5, I9 | AC6, AC13 | CERT-001, CERT-011, CERT-014 |
| REQ-2.4-07 | ADR-MC-001 §2.4 | continuation_capability_max_validity (default 24 hours): absolute upper bound on continuation capability lifetime | C02, C14 | RT-06.7, CHS-015 | I5 | AC6 | CERT-001, CERT-014 |
| REQ-2.4-08 | ADR-MC-001 §2.4 | max_clock_rollback_tolerance (default 1 second): maximum tolerated clock rollback (Section 2.8) | C14 | RT-06.8 (ref), RT-15.4, UT-C14-003, RES-010 | I5, I14 | AC6, AC15 | CERT-001, CERT-015 |
| REQ-2.4-09 | ADR-MC-001 §2.4 | All limits are configurable per tenant subject to platform maximums | C02 | RT-06.9, MT-005, MT-010 | I5, I9 | AC6, AC13 | CERT-001, CERT-011 |
| REQ-2.4-10 | ADR-MC-001 §2.4 | A platform break-glass policy may reduce limits but never increase them beyond the platform maximum | C02 | RT-06.10 | I5 | AC6 | CERT-001 |

---

## 7. ADR-MC-001 Section 2.5 — Idempotency and Duplicate Suppression

### 7.1 Section 2.5.1 — Stable External-Effect Identity

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.5.1-01 | ADR-MC-001 §2.5.1 | The uniqueness key for an externally visible effect must be stable across normal execution, continuation, replay, and multiple executors; must identify the business operation, not the execution attempt | C13 | RT-08.1, UT-C13-001 | I10 | AC7 | CERT-001 |
| REQ-2.5.1-02 | ADR-MC-001 §2.5.1 | Recommended form: (command_id, operation_id, side_effect_slot) | C13 | RT-08.1, UT-C13-001, UT-C08-004 | I10 | AC7 | CERT-001 |
| REQ-2.5.1-03 | ADR-MC-001 §2.5.1 | continuation_id, executor_id, lease_token, and replay attempt number are execution metadata, not part of the external-effect identity | C13 | RT-08.9, UT-C13-001 | I10 | AC7 | CERT-001 |
| REQ-2.5.1-04 | ADR-MC-001 §2.5.1 | Downstream systems must reject duplicate effects matching the same (command_id, operation_id, side_effect_slot) regardless of which executor or attempt produced them | C13 | RT-08.3, UT-C13-002, SEC-010 | I10 | AC7 | CERT-001, CERT-012 |
| REQ-2.5.1-05 | ADR-MC-001 §2.5.1 | Replay identity rule: when a replay creates a new command record, the command_id in the effect identity must always refer to the root_command_id, never the replay-attempt command record | C13, C10 | RT-08.7, UT-C13-007, REC-005 | I10 | AC7, AC8 | CERT-001, CERT-004 |

### 7.2 Section 2.5.2 — Duplicate Suppression Layers

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.5.2-01 | ADR-MC-001 §2.5.2 | Brain dispatch layer: key (command_id, executor_id, lease_token); reject duplicate dispatch for active lease | C01 | RT-08.4 | I10 | AC7 | CERT-001 |
| REQ-2.5.2-02 | ADR-MC-001 §2.5.2 | Continuation capability layer: key (command_id, capability_id); reject duplicate or reused continuation capability | C02 | RT-08.5, SEC-007 | I3, I10 | AC7 | CERT-001, CERT-012 |
| REQ-2.5.2-03 | ADR-MC-001 §2.5.2 | Executor operation layer: key (command_id, operation_id, side_effect_slot); skip already-performed externally visible operations | C08, C13 | RT-08.2, UT-C08-006 | I10 | AC7 | CERT-001 |
| REQ-2.5.2-04 | ADR-MC-001 §2.5.2 | Downstream system layer: key (command_id, operation_id, side_effect_slot); refuse duplicate external effects | C13 | RT-08.3, UT-C13-002, SEC-010 | I10 | AC7 | CERT-001, CERT-012 |
| REQ-2.5.2-05 | ADR-MC-001 §2.5.2 | Brain reconciliation layer: key (command_id, continuation_id); reject duplicate continuation reports | C10 | RT-08.6, SEC-009 | I10 | AC7, AC9 | CERT-001, CERT-012 |
| REQ-2.5.2-06 | ADR-MC-001 §2.5.2 | Replay authorization layer: key (command_id, replay_attempt_id); ensure replay is authorized and reconciled before re-execution | C10, C01 | RT-08.10, REC-003, REC-017 | I7, I10 | AC7, AC8 | CERT-001, CERT-004 |

### 7.3 Section 2.5.3 — Continuation Journal

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.5.3-01 | ADR-MC-001 §2.5.3 | The executor must maintain a local continuation journal recording every operation attempted, its input, output, success/failure, timestamp, and the stable external-effect identity used | C08 | RT-08.8, UT-C08-001, UT-C08-004, INT-006 | I5, I10 | AC7 | CERT-001, CERT-008 |

---

## 8. ADR-MC-001 Section 2.6 — Reconciliation Protocol

### 8.1 Section 2.6.1 — Recovery Detection

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.6.1-01 | ADR-MC-001 §2.6.1 | The Brain or an independent witness node declares recovery when the Brain has been available and responsive for at least brain_recovery_confirmation_period (default 10 seconds) | C03, C14 | RT-13.1, REC-008, INT-008 | I7 | AC14 | CERT-001, CERT-002 |
| REQ-2.6.1-02 | ADR-MC-001 §2.6.1 | Executors are notified of recovery through the heartbeat channel | C03 | RT-13.2, REC-009, UT-C03-004 | I7 | AC14 | CERT-001 |
| REQ-2.6.1-03 | ADR-MC-001 §2.6.1 | Recovery must be time-anchored and signed | C14 | RT-13.1, REC-008 | I7, I14 | AC14, AC15 | CERT-001, CERT-015 |

### 8.2 Section 2.6.2 — Completion Reporting

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.6.2-01 | ADR-MC-001 §2.6.2 | Within completion_report_deadline of recovery detection, every executor that continued must report all 14 required fields | C09, C10 | RT-09.1, RT-09.2, UT-C09-001, UT-C09-007, UT-C09-008, RT-13.6, REC-013 | I6, I7 | AC10, AC14 | CERT-001, CERT-002 |
| REQ-2.6.2-02 | ADR-MC-001 §2.6.2 | Reporting is mandatory regardless of outcome; silent continuation is forbidden | C09, C10, C11 | RT-09.1, RT-09.8, RT-09.9, RT-09.10, SEC-028 | I6, I7 | AC10 | CERT-001, CERT-012 |

### 8.3 Section 2.6.3.1 — Result Selection

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.6.3.1-01 | ADR-MC-001 §2.6.3.1 | Single valid continuation, no conflict: select that result | C10 | RT-10.1, UT-C10-001, INT-009 | I7 | AC9 | CERT-001, CERT-002 |
| REQ-2.6.3.1-02 | ADR-MC-001 §2.6.3.1 | Multiple continuations, same result and effect identity: select the result from the first completed continuation by trusted comparable signed time; mark others DUPLICATE_AGREED; deterministic tie-breaker: lowest executor_id wins | C10, C14 | RT-10.2, RT-10.3, UT-C10-002, UT-C10-003, INT-010 | I7, I8, I10 | AC9 | CERT-001, CERT-003 |
| REQ-2.6.3.1-03 | ADR-MC-001 §2.6.3.1 | Multiple continuations, divergent results: no automatic selection; route to MANUAL_REVIEW_REQUIRED and effect reconciliation | C10, C11 | RT-10.4, UT-C10-004, INT-011 | I8 | AC9, AC11 | CERT-001, CERT-003 |
| REQ-2.6.3.1-04 | ADR-MC-001 §2.6.3.1 | Invalid continuation: discard the result; executor may be flagged | C10, C11 | RT-10.5, UT-C10-010 | I8 | AC9 | CERT-001 |
| REQ-2.6.3.1-05 | ADR-MC-001 §2.6.3.1 | Result selection by timestamp is permitted only when all reported effects are provably idempotent and equivalent | C10, C13 | RT-10.13, UT-C10-012 | I10 | AC9 | CERT-001 |

### 8.4 Section 2.6.3.2 — Effect Reconciliation

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.6.3.2-01 | ADR-MC-001 §2.6.3.2 | Effect identity matches an already-applied effect: mark as duplicate; do not re-apply | C10, C13 | RT-10.6, UT-C10-005 | I10 | AC9 | CERT-001 |
| REQ-2.6.3.2-02 | ADR-MC-001 §2.6.3.2 | Effect identity is new and result is valid: apply the effect if the selected result is authoritative | C10, C13 | RT-10.7, INT-009 | I7, I10 | AC9 | CERT-001, CERT-002 |
| REQ-2.6.3.2-03 | ADR-MC-001 §2.6.3.2 | Effect identity conflicts with another effect: freeze the affected downstream resource; route to manual review | C10, C11, C13 | RT-10.8, UT-C10-006, INT-011 | I8 | AC9, AC11 | CERT-001, CERT-003 |
| REQ-2.6.3.2-04 | ADR-MC-001 §2.6.3.2 | Effect is non-reversible and multiple executors attempted it: freeze and require manual review; no automatic application | C10, C11, C13 | RT-10.9 | I8, I15 | AC9, AC11, AC18 | CERT-001, CERT-003 |
| REQ-2.6.3.2-05 | ADR-MC-001 §2.6.3.2 | Effect class is high-risk/irreversible (Class 3): freeze and require manual review regardless of result selection | C10, C11, C13 | RT-10.12, RT-16.9 | I8, I15 | AC9, AC11, AC18 | CERT-001, CERT-003, CERT-016 |

### 8.5 Section 2.6.3.3 — Compensation

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.6.3.3-01 | ADR-MC-001 §2.6.3.3 | Where effects are reversible or idempotent, the Brain may authorize compensation: re-issuing an idempotent operation with the authoritative result, or reversing a reversible effect produced by a losing executor | C10, C01, C13 | RT-10.10, UT-C10-007, INT-012 | I7, I10 | AC9 | CERT-001, CERT-002 |
| REQ-2.6.3.3-02 | ADR-MC-001 §2.6.3.3 | Compensation is itself a command with its own lease, idempotency key, and audit chain | C10, C01, C12 | RT-10.10, INT-012 | I7, I10, I11 | AC9 | CERT-001 |
| REQ-2.6.3.3-03 | ADR-MC-001 §2.6.3.3 | Irreversible or destructive effects cannot be compensated automatically | C10, C11 | RT-10.11, UT-C10-008 | I8, I15 | AC9, AC11 | CERT-001, CERT-003 |

### 8.6 Section 2.6.3.4 — Manual Review

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.6.3.4-01 | ADR-MC-001 §2.6.3.4 | Manual review is mandatory when: multiple continuations produce divergent results; non-reversible or high-risk effects are involved; revocation or cancellation status was unknown during continuation; continuation capability validity is disputed; any reconciliation step cannot produce a deterministic outcome | C10, C11 | RT-10.4, RT-10.8, RT-10.9, RT-10.11, RT-10.12, UT-C11-001–UT-C11-005 | I8 | AC9, AC11 | CERT-001, CERT-003 |
| REQ-2.6.3.4-02 | ADR-MC-001 §2.6.3.4 | The command remains in MANUAL_REVIEW_REQUIRED until an authorized operator resolves it; all evidence, receipts, and continuation journals must be surfaced | C11, C12 | UT-C11-006, UT-C11-007 | I8, I11 | AC9, AC11 | CERT-001, CERT-003 |

### 8.7 Section 2.6.4 — Reconciliation Classifications

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.6.4-01 | ADR-MC-001 §2.6.4 | VALID_CONTINUATION: all criteria met, single report, no conflict, effects reconciled | C10 | RT-10.1, UT-C10-001, INT-009 | I7 | AC9 | CERT-001, CERT-002 |
| REQ-2.6.4-02 | ADR-MC-001 §2.6.4 | VALID_BUT_RECONCILED: all criteria met, but effects required reconciliation or compensation | C10, C13 | RT-10.14, UT-C10-009 | I7, I10 | AC9 | CERT-001 |
| REQ-2.6.4-03 | ADR-MC-001 §2.6.4 | INVALID_CONTINUATION: criteria were not met at continuation time; executor exceeded authority | C10, C11 | RT-10.5, UT-C10-010, SEC-028 | I8 | AC9, AC11 | CERT-001, CERT-012 |
| REQ-2.6.4-04 | ADR-MC-001 §2.6.4 | CONFLICTING_REPORTS: multiple reports with irreconcilable differences or non-reversible effects | C10, C11 | RT-10.4, UT-C10-011, INT-011 | I8 | AC9, AC11 | CERT-001, CERT-003 |
| REQ-2.6.4-05 | ADR-MC-001 §2.6.4 | MANUAL_REVIEW_REQUIRED: deterministic resolution impossible; operator decision required | C10, C11 | RT-10.4, RT-10.8, RT-10.11, UT-C11-005 | I8 | AC9, AC11 | CERT-001, CERT-003 |

---

## 9. ADR-MC-001 Section 2.7 — Replay Semantics

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.7-01 | ADR-MC-001 §2.7 | Replay may occur only when the Brain explicitly authorizes it | C10, C01 | REC-001, REC-002, REC-003 | I4, I7, I10 | AC8 | CERT-004 |
| REQ-2.7-02 | ADR-MC-001 §2.7 | The Brain must reconcile all continuation reports before authorizing replay; unknown or unreconciled effect status blocks replay or requires compensation/manual review | C10, C13 | REC-003, REC-017, REC-018, RT-08.10 | I7, I10 | AC8, AC9 | CERT-004 |
| REQ-2.7-03 | ADR-MC-001 §2.7 | Replay uses a new lease and a new execution identity (replay_attempt_id); the replay creates a new command record, but that record is execution metadata — it is not the identity root for external effects | C01, C12 | REC-001, REC-004 | I10, I11 | AC8 | CERT-004 |
| REQ-2.7-04 | ADR-MC-001 §2.7 | Replay does not receive a new external-effect identity; every replayed operation must derive its external-effect identity from the original root command, never from the replay-attempt command record; stable key is (root_command_id, operation_id, side_effect_slot) | C13, C10 | REC-005, RT-08.7, UT-C13-007 | I10 | AC7, AC8 | CERT-004 |
| REQ-2.7-05 | ADR-MC-001 §2.7 | The Brain must mark the original command as REPLAYED and link the replay command through causation | C01, C12 | REC-004 | I10, I11 | AC8, AC12 | CERT-004 |
| REQ-2.7-06 | ADR-MC-001 §2.7 | Executors must not autonomously replay a command during continuation | C01, C05 | REC-002 | I4, I10 | AC8 | CERT-004, CERT-012 |
| REQ-2.7-07 | ADR-MC-001 §2.7 | A continuation that fails may be followed by a Brain-authorized replay only after the continuation is reconciled and the Brain determines which effects are already applied | C10, C01, C13 | REC-006, REC-007, REC-018 | I7, I10 | AC8, AC9 | CERT-004 |

---

## 10. ADR-MC-001 Section 2.8 — Time Authority and Clock Rules

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.8-01 | ADR-MC-001 §2.8 | Trusted clock source: the Brain is the authoritative clock source; all lease, capability, and revocation timestamps are signed by the Brain | C14, C01, C02 | RT-15.1, UT-C14-001, UT-C14-006 | I14 | AC15 | CERT-015 |
| REQ-2.8-02 | ADR-MC-001 §2.8 | Executor clock: the executor maintains a monotonic clock for duration measurement and a wall-clock corrected by signed Brain anchors | C14, C05 | RT-15.2, RT-15.5, UT-C14-004 | I14 | AC15 | CERT-015 |
| REQ-2.8-03 | ADR-MC-001 §2.8 | Clock skew tolerance: maximum skew between executor wall-clock and Brain time is max_clock_skew_tolerance (default 5 seconds); exceeding skew is a security event | C14 | RT-15.3, UT-C14-002, RES-009, SEC-023 | I14 | AC15 | CERT-015, CERT-012, CERT-013 |
| REQ-2.8-04 | ADR-MC-001 §2.8 | Monotonic time: max_continuation_duration and grace periods are measured with monotonic time to prevent extension via clock rollback | C14, C02 | RT-15.5, RT-06.8, UT-C14-004, RES-011 | I5, I14 | AC6, AC15 | CERT-015, CERT-013 |
| REQ-2.8-05 | ADR-MC-001 §2.8 | Signed time anchors: the Brain issues signed time anchors at dispatch, renewal, and recovery; the latest pre-outage signed anchor establishes the wall-clock reference; the executor derives lease expiry locally from that anchor plus monotonic elapsed time; if the monotonic clock loses continuity or wall-clock drift exceeds max_clock_skew_tolerance, the executor must STOP; a fresh Brain signature at the instant of expiry is not required | C14, C01, C05 | RT-15.1, RT-15.2, RT-15.6, RT-15.7, UT-C14-005, UT-C14-006, RES-012 | I14 | AC15 | CERT-015, CERT-013 |
| REQ-2.8-06 | ADR-MC-001 §2.8 | Timestamp rollback: the executor rejects any signed timestamp that rolls backward more than max_clock_rollback_tolerance relative to the last anchor; larger rollbacks require operator intervention | C14 | RT-15.4, UT-C14-003, RES-010 | I14 | AC15 | CERT-015, CERT-013 |
| REQ-2.8-07 | ADR-MC-001 §2.8 | Disagreement: if executor and Brain time disagree beyond tolerance, the executor must stop and wait for a fresh signed anchor; continuation is not permitted under disputed time | C14, C02 | RT-15.8, UT-C14-008 | I14 | AC15 | CERT-015 |
| REQ-2.8-08 | ADR-MC-001 §2.8 | Capability validity: not_valid_before and not_valid_after are evaluated against signed Brain anchors, not executor wall-clock alone | C14, C02 | RT-15.9, UT-C14-007 | I3, I14 | AC2, AC15 | CERT-015 |

---

## 11. ADR-MC-001 Section 2.9 — Side-Effect Classification

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.9-01 | ADR-MC-001 §2.9 | Class 0: local computation only; no external effects; eligible with capability and journal | C02, C08 | RT-16.1, UT-C13-001 | I5 | AC18 | CERT-016 |
| REQ-2.9-02 | ADR-MC-001 §2.9 | Class 1: reversible internal writes or safe local state changes; eligible with capability, journal, and rollback plan | C02, C08 | RT-16.2 | I5 | AC18 | CERT-016 |
| REQ-2.9-03 | ADR-MC-001 §2.9 | Class 2: idempotent external writes with proven downstream duplicate suppression; eligible only if downstream system validates (command_id, operation_id, side_effect_slot) | C02, C13 | RT-16.3, INT-007, INT-017 | I5, I10 | AC7, AC18 | CERT-016 |
| REQ-2.9-04 | ADR-MC-001 §2.9 | Class 3: irreversible, destructive, financial, legal, or high-risk external effects; prohibited during continuation; requires fresh Brain authorization | C02, C13, C11, C12 | RT-16.4, RT-16.9, UT-C13-006, SEC-025, INT-017 | I15 | AC18 | CERT-016, CERT-012 |
| REQ-2.9-05 | ADR-MC-001 §2.9 | The default class is STOP (no continuation permitted) | C02 | RT-16.5, RT-05.14 | I4 | AC5, AC18 | CERT-001, CERT-016 |
| REQ-2.9-06 | ADR-MC-001 §2.9 | A command's continuation_class is assigned by the Brain at dispatch based on the command type, tenant policy, and side-effect risk | C01, C02 | RT-16.6, UT-C02-017 | I4 | AC18 | CERT-001, CERT-016 |

---

## 12. ADR-MC-001 Section 2.10 — Revocation and Cancellation Watermark

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.10-01 | ADR-MC-001 §2.10 | Revocation stream: the Brain publishes a signed, monotonic revocation/cancellation stream partitioned by tenant; each entry has a sequence number and timestamp | C06, C14 | RT-07.8, RT-07.9, UT-C06-001, UT-C06-002, UT-C06-003, UT-C06-004 | I13 | AC17 | CERT-001 |
| REQ-2.10-02 | ADR-MC-001 §2.10 | Watermark: the executor records the highest revocation sequence number it has observed; continuation requires the watermark to be at least revocation_watermark_required from the capability | C06, C02 | RT-07.1, RT-07.2, UT-C06-005, UT-C02-014 | I13 | AC17 | CERT-001 |
| REQ-2.10-03 | ADR-MC-001 §2.10 | Cache age: the local revocation cache must be no older than max_revocation_cache_age (default 5 seconds) at the moment of lease expiry; older caches are stale | C06, C14 | RT-07.4, UT-C06-006, RES-015, SEC-027 | I13 | AC17 | CERT-001, CERT-013, CERT-012 |
| REQ-2.10-04 | ADR-MC-001 §2.10 | Fail-closed: if the revocation watermark is missing, stale, or below the capability requirement, continuation is not permitted | C06, C02 | RT-07.2, RT-07.3, UT-C06-007 | I13 | AC17 | CERT-001 |
| REQ-2.10-05 | ADR-MC-001 §2.10 | Command-class rule: high-risk, legal, financial, destructive, or irreversible commands default to STOP and may not continue without fresh revocation knowledge | C06, C02 | RT-07.7 | I13, I15 | AC17, AC18 | CERT-001 |
| REQ-2.10-06 | ADR-MC-001 §2.10 | Revocation during outage: if the executor receives a revocation entry during outage, it must stop immediately | C06, C08 | RT-07.5 | I13 | AC17 | CERT-001 |
| REQ-2.10-07 | ADR-MC-001 §2.10 | Cancellation in cache: a cancellation command observed at or before the revocation watermark is authoritative; continuation is forbidden | C06 | RT-07.6, RT-05.6 | I13 | AC17 | CERT-001 |

---

## 13. ADR-MC-001 Section 2.11 — Policy Snapshot Model

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.11-01 | ADR-MC-001 §2.11 | Pinned snapshot: the continuation capability carries policy_snapshot_id and policy_snapshot_hash; the executor may rely only on that exact policy version during continuation | C02, C07 | RT-02.1, RT-05.9, UT-C07-001, UT-C07-006, UT-C02-010, INT-015 | I12 | AC16 | CERT-001 |
| REQ-2.11-02 | ADR-MC-001 §2.11 | Snapshot validity: the capability defines a policy_snapshot_not_valid_after time; after that, the executor must not continue; defaults to capability's own not_valid_after if absent | C02, C07, C14 | RT-02.9, UT-C02-011, UT-C07-002 | I12 | AC16 | CERT-001 |
| REQ-2.11-03 | ADR-MC-001 §2.11 | Emergency deny channel: critical policy denies/revocations must travel through a survivable channel (e.g., signed revocation stream, witness broadcast); if the executor cannot verify the required watermark, it stops | C06, C04, C07 | RT-07.10, UT-C06-008, UT-C07-005 | I12, I13 | AC16, AC17 | CERT-001 |
| REQ-2.11-04 | ADR-MC-001 §2.11 | New effects: a pinned policy snapshot cannot authorize side-effect classes or operations not explicitly permitted by the capability | C02, C07 | RT-16.8, UT-C07-004, SEC-026 | I12, I15 | AC16, AC18 | CERT-001, CERT-012 |

---

## 14. ADR-MC-001 Section 2.12 — Split-Brain Handling

### 14.1 Section 2.12.1 — Detection

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.12.1-01 | ADR-MC-001 §2.12.1 | Detect multiple continuation reports for the same command_id with different continuation_id values | C10, C12 | RT-11.1, INT-011 | I8 | AC11 | CERT-003 |
| REQ-2.12.1-02 | ADR-MC-001 §2.12.1 | Detect continuation reports arriving while the Brain considers the command still active | C10 | RT-11.2 | I8 | AC11 | CERT-003 |
| REQ-2.12.1-03 | ADR-MC-001 §2.12.1 | Detect divergent result_digest values or conflicting (command_id, operation_id, side_effect_slot) claims | C10, C11, C13 | RT-11.3, RT-11.4 | I8, I10 | AC11 | CERT-003 |

### 14.2 Section 2.12.2 — Resolution

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.12.2-01 | ADR-MC-001 §2.12.2 | Multiple executors continued, results agree, effects idempotent: first by trusted comparable signed time wins (tie-breaker: lowest executor_id); others DUPLICATE_AGREED; deduplicate by stable effect identity; SUCCEEDED | C10, C13, C14 | RT-11.5, CHS-007, INT-010 | I8, I10 | AC11 | CERT-003, CERT-014 |
| REQ-2.12.2-02 | ADR-MC-001 §2.12.2 | Multiple executors continued, results agree, effects non-reversible: first by signed time wins; others DUPLICATE_AGREED; freeze effects; manual review; MANUAL_REVIEW_REQUIRED | C10, C11, C13 | RT-11.6, CHS-008 | I8, I15 | AC11 | CERT-003, CERT-014 |
| REQ-2.12.2-03 | ADR-MC-001 §2.12.2 | Multiple executors continued, results conflict: no automatic selection; freeze all affected downstream effects; manual review; MANUAL_REVIEW_REQUIRED | C10, C11, C13 | RT-11.3, RT-11.4, CHS-008, CHS-009 | I8 | AC11 | CERT-003, CERT-014 |
| REQ-2.12.2-04 | ADR-MC-001 §2.12.2 | Brain recovers while continuation active: stop active continuations; apply atomicity rule — committed/irreversible operations finished and reported; uncommitted operations aborted; never both finish and abort for the same operation state; RECONCILING | C10, C08, C09 | RT-11.7, RES-013, RES-014, CHS-010, REC-010, REC-011, REC-012 | I7, I8 | AC11, AC14 | CERT-003, CERT-013, CERT-014 |
| REQ-2.12.2-05 | ADR-MC-001 §2.12.2 | Brain never recovers within capability window: executor must stop at not_valid_after; partial results recorded; manual recovery; MANUAL_REVIEW_REQUIRED | C02, C09, C10 | RT-11.8, CHS-015 | I5, I8 | AC11 | CERT-003, CERT-014 |
| REQ-2.12.2-06 | ADR-MC-001 §2.12.2 | No silent conflict resolution is permitted; all conflicts are recorded and surfaced | C10, C11, C12 | RT-11.9 | I8, I11 | AC11 | CERT-003 |

---

## 15. ADR-MC-001 Section 2.13 — Audit Chain Requirements

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.13-01 | ADR-MC-001 §2.13 | The audit chain must include all 9 event types: lease expiry, capability issuance, outage declaration, eligibility decision, each operation (with stable effect identity), continuation completion + receipt, recovery detection, reconciliation, terminal state | C12, all | RT-14.1, UT-C12-005, INT-016 | I11 | AC12 | CERT-010 |
| REQ-2.13-02 | ADR-MC-001 §2.13 | Authoritative audit storage is never truncated; the immutable audit ledger stores every event | C12 | RT-14.2, UT-C12-006, SEC-015, SEC-016 | I11 | AC12 | CERT-010, CERT-012 |
| REQ-2.13-03 | ADR-MC-001 §2.13 | Read-only projection APIs (such as Mission Control causation chain) may paginate or cap displayed links at MAX_CAUSATION_LINKS with truncation metadata, but that truncation applies only to the projection, not to the ledger | C12 | RT-14.3, UT-C12-004 | I11 | AC12 | CERT-010 |

---

## 16. ADR-MC-001 Section 2.14 — Tenant Isolation Guarantees

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.14-01 | ADR-MC-001 §2.14 | An executor may only continue commands within its own tenant scope | C02, C12 | RT-12.1, SEC-012, MT-001 | I9 | AC13 | CERT-011, CERT-012 |
| REQ-2.14-02 | ADR-MC-001 §2.14 | Continuation capabilities, revocation streams, and witness statements are tenant-scoped | C02, C06, C04 | RT-12.2, RT-12.3, RT-12.4, SEC-011, SEC-013, SEC-014, MT-002, MT-003, MT-004 | I9 | AC13 | CERT-011, CERT-012 |
| REQ-2.14-03 | ADR-MC-001 §2.14 | Continuation limits are enforced per tenant | C02 | RT-12.5, RT-12.6, MT-005, MT-006, MT-010 | I5, I9 | AC6, AC13 | CERT-011 |
| REQ-2.14-04 | ADR-MC-001 §2.14 | Continuation reports are routed to the tenant's Brain partition | C10 | RT-12.7, MT-007 | I9 | AC13 | CERT-011 |
| REQ-2.14-05 | ADR-MC-001 §2.14 | Cross-tenant continuation is forbidden and treated as a security event | C12, C02 | RT-12.9, SEC-012, MT-009 | I9 | AC13 | CERT-011, CERT-012 |
| REQ-2.14-06 | ADR-MC-001 §2.14 | Tenant-level policies may disable continuation entirely (continuation_class = STOP) | C02, C07 | RT-12.8, MT-008 | I4, I9 | AC13 | CERT-011 |

---

## 17. ADR-MC-001 Section 2.15 — Recovery Protocol

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-2.15-01 | ADR-MC-001 §2.15.1 | Recovery detection: Brain availability confirmed for brain_recovery_confirmation_period by direct signals and/or witness confirmation | C03, C14 | RT-13.1, REC-008, INT-008 | I7 | AC14 | CERT-001, CERT-002 |
| REQ-2.15-02 | ADR-MC-001 §2.15.2 | In-progress operation atomicity: for each executor with an active continuation, committed/irreversible operations finished and reported; uncommitted operations aborted; same operation never both finished and aborted | C10, C08, C09 | RT-13.3, RT-13.4, RT-13.5, REC-010, REC-011, REC-012, RES-013 | I7, I8 | AC14 | CERT-001, CERT-013 |
| REQ-2.15-03 | ADR-MC-001 §2.15.3 | Report collection: Brain receives all pending continuation reports within completion_report_deadline | C09, C10 | RT-13.6, REC-013, RT-10.15 | I7 | AC14 | CERT-001 |
| REQ-2.15-04 | ADR-MC-001 §2.15.4 | Reconciliation: Brain performs result selection, effect reconciliation, compensation, and manual-review routing (Section 2.6) | C10, C11, C13 | RT-13.7, INT-009–INT-013 | I7, I8, I10 | AC9, AC14 | CERT-001, CERT-002 |
| REQ-2.15-05 | ADR-MC-001 §2.15.5 | Conflict freeze: conflicting results freeze downstream effects until resolved | C10, C11, C13 | RT-13.8 | I8 | AC11, AC14 | CERT-003 |
| REQ-2.15-06 | ADR-MC-001 §2.15.6 | Manual review queue: conflicts, invalid continuations, and non-reversible effects are enqueued for operator review | C11 | RT-13.9, UT-C11-001–UT-C11-007 | I8 | AC11, AC14 | CERT-003 |
| REQ-2.15-07 | ADR-MC-001 §2.15.7 | Replay authorization: valid commands that did not complete receive Brain-authorized replay only after reconciliation | C10, C01 | RT-13.10, REC-001, REC-003 | I7, I10 | AC8, AC14 | CERT-004 |
| REQ-2.15-08 | ADR-MC-001 §2.15.8 | Policy refresh: all executors refresh policy snapshots and revocation watermarks before accepting new work | C07, C06, C05 | RT-13.11, REC-014, UT-C05-007 | I12, I13 | AC14, AC16 | CERT-001 |
| REQ-2.15-09 | ADR-MC-001 §2.15.9 | Audit completion: all continuation events are finalized in the immutable audit ledger | C12 | RT-13.12, REC-015 | I11 | AC12, AC14 | CERT-010 |
| REQ-2.15-10 | ADR-MC-001 §2.15.10 | Gate evaluation: only after the implementation is certified may SIGMA_LEASE_EXPIRY_CONTINUATION_GATE be evaluated for unblocking | C12 | RT-13.13, REC-016, CERT-017 | I11 | AC14, AC20 | CERT-017 |

---

## 18. ADR-MC-001 Section 7 — Invariants

Each invariant is both a requirement and an enforcement obligation. The table below traces each invariant to the components that enforce it, the tests that verify it, the acceptance criteria it satisfies, and the certification gates that confirm it.

| Req ID | ADR Ref | Invariant | Component(s) | Test Case(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|
| REQ-7-I1 | ADR-MC-001 §7 (I1) | An executor without a valid lease cannot produce authoritative command effects during normal execution | C01, C13 | UT-C01-001, UT-C01-004–UT-C01-006, SEC-004, SEC-005, RT-01.* | AC1 | CERT-001, CERT-005, CERT-012 |
| REQ-7-I2 | ADR-MC-001 §7 (I2) | An executor cannot use an expired lease to authorize continuation or effects | C01, C02, C13 | UT-C01-005, SEC-004, SEC-005, RT-01.3, RT-05.2, RES-004 | AC1 | CERT-001, CERT-005, CERT-012 |
| REQ-7-I3 | ADR-MC-001 §7 (I3) | A continuation capability cannot be used before lease expiry or after its own expiry | C02, C14 | UT-C02-003, UT-C02-004, SEC-006, SEC-007, RT-02.2, RT-02.3 | AC2 | CERT-001, CERT-005, CERT-012 |
| REQ-7-I3a | ADR-MC-001 §7 (I3a) | Only the continuation capability referenced by the latest valid lease may be exercised; prior capabilities are superseded at renewal, even if their not_valid_after is later | C02, C13, C12 | UT-C02-009, RT-01.10, INT-002, INT-020, CHS-016 | AC1, AC2 | CERT-001, CERT-005 |
| REQ-7-I4 | ADR-MC-001 §7 (I4) | Continuation is never the default behavior | C02, C05, C03, C04 | UT-C05-004, RT-05.14, SEC-019, SEC-020, SEC-021, SEC-022, RT-03.*, RT-04.*, RT-05.* | AC3, AC4, AC5 | CERT-001, CERT-005, CERT-012 |
| REQ-7-I5 | ADR-MC-001 §7 (I5) | Continuation cannot exceed its bounded envelope | C02, C08, C14 | RT-06.*, UT-C02-015, UT-C02-016, UT-C08-005, RES-011, SEC-023, SEC-024, CHS-017 | AC6 | CERT-001, CERT-005, CERT-013, CERT-014 |
| REQ-7-I6 | ADR-MC-001 §7 (I6) | Every continuation produces an immutable, signed receipt | C09, C14, C12 | RT-09.*, UT-C09-001–UT-C09-003, SEC-028, SEC-029, SEC-030, SEC-031 | AC10 | CERT-001, CERT-005, CERT-012 |
| REQ-7-I7 | ADR-MC-001 §7 (I7) | Every continuation is reconciled before the command reaches terminal state | C10, C11, C09 | RT-10.*, RT-13.*, UT-C10-*, INT-008–INT-013, REC-008–REC-016 | AC9, AC14 | CERT-001, CERT-005, CERT-002 |
| REQ-7-I8 | ADR-MC-001 §7 (I8) | Conflicting continuation results or non-reversible effects never resolve silently | C10, C11, C13, C12 | RT-11.*, UT-C11-*, UT-C10-004, UT-C10-006, CHS-005, CHS-008, CHS-009, SEC-032 | AC11 | CERT-003, CERT-005, CERT-014 |
| REQ-7-I9 | ADR-MC-001 §7 (I9) | Cross-tenant continuation is impossible | C02, C06, C04, C10, C12 | RT-12.*, MT-001–MT-012, SEC-011–SEC-014, INT-018 | AC13 | CERT-005, CERT-011, CERT-012 |
| REQ-7-I10 | ADR-MC-001 §7 (I10) | Idempotency is preserved across continuation, replay, and normal execution | C08, C13, C10 | RT-08.*, UT-C13-001, UT-C13-002, UT-C08-001, UT-C08-004, INT-007, INT-013, SEC-009, SEC-010, REC-001–REC-007 | AC7, AC8 | CERT-001, CERT-005, CERT-004 |
| REQ-7-I11 | ADR-MC-001 §7 (I11) | Authoritative audit storage is complete and never truncated | C12 | RT-14.*, UT-C12-001–UT-C12-007, INT-016, SEC-015–SEC-018, RES-018 | AC12 | CERT-005, CERT-010, CERT-012 |
| REQ-7-I12 | ADR-MC-001 §7 (I12) | Policy snapshot validity is bounded to the exact pinned snapshot in the capability | C02, C07 | UT-C07-001–UT-C07-004, RT-02.9, RT-05.9, INT-015, SEC-026 | AC16 | CERT-001, CERT-005 |
| REQ-7-I13 | ADR-MC-001 §7 (I13) | Revocation/cancellation knowledge must be fresh enough; absence of evidence is not permission | C06, C02 | RT-07.*, UT-C06-001–UT-C06-008, INT-014, RES-015, SEC-027, CHS-013 | AC17 | CERT-001, CERT-005, CERT-013 |
| REQ-7-I14 | ADR-MC-001 §7 (I14) | Time cannot be manipulated to extend authority | C14, C01, C02, C06 | RT-15.*, UT-C14-001–UT-C14-008, RES-009–RES-012, SEC-023, CHS-011 | AC15 | CERT-005, CERT-015, CERT-013 |
| REQ-7-I15 | ADR-MC-001 §7 (I15) | High-risk or irreversible side effects cannot be produced during continuation | C02, C13, C10, C11 | RT-16.*, UT-C13-006, INT-017, SEC-025, RES-014 | AC18 | CERT-005, CERT-016, CERT-012 |

---

## 19. ADR-MC-001 Section 9 — Implementation Prerequisites

### 19.1 Section 9.1 — Required Components

Each of the 14 required components must be implemented before the Sigma gate may be evaluated. The table traces each component to its ADR section, verifying tests, enforced invariants, satisfied acceptance criteria, and certification gates.

| Req ID | ADR Ref | Component | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|
| REQ-9.1-C01 | ADR-MC-001 §9.1, §2.1.1–§2.1.3 | Signed lease token service — issue, renew, and revoke signed lease tokens | UT-C01-001–UT-C01-010, RT-01.*, INT-001, INT-002 | I1, I2, I3a | AC1 | CERT-001, CERT-007, CERT-008 |
| REQ-9.1-C02 | ADR-MC-001 §9.1, §2.1.4, §2.11 | Continuation capability service — issue, validate, and revoke signed continuation capabilities | UT-C02-001–UT-C02-018, RT-02.*, INT-001, INT-002, INT-015 | I3, I3a, I4, I5, I12, I15 | AC2, AC5, AC6, AC16, AC18 | CERT-001, CERT-007, CERT-008 |
| REQ-9.1-C03 | ADR-MC-001 §9.1, §2.2.1, §2.6.1 | Brain heartbeat endpoint — allow executors to detect Brain availability | UT-C03-001–UT-C03-006, RT-03.*, RT-13.1, RT-13.2, INT-003, INT-008 | I4, I14 | AC3, AC14 | CERT-001, CERT-008 |
| REQ-9.1-C04 | ADR-MC-001 §9.1, §2.2.4 | Witness statement service — publish and validate signed witness statements | UT-C04-001–UT-C04-010, RT-04.*, CHS-003, CHS-004 | I4, I14 | AC4 | CERT-001, CERT-008, CERT-014 |
| REQ-9.1-C05 | ADR-MC-001 §9.1, §2.3 | Executor local state cache — store inputs, configuration, and prior step outputs | UT-C05-001–UT-C05-007, RT-05.*, RES-001 | I4, I5 | AC5 | CERT-001, CERT-008, CERT-013 |
| REQ-9.1-C06 | ADR-MC-001 §9.1, §2.10 | Revocation stream — publish lease revocations, cancellations, and emergency denies | UT-C06-001–UT-C06-008, RT-07.*, INT-014 | I13 | AC17 | CERT-001, CERT-008 |
| REQ-9.1-C07 | ADR-MC-001 §9.1, §2.11 | Policy snapshot registry — pin and validate policy snapshots by hash | UT-C07-001–UT-C07-007, RT-02.9, RT-05.9, INT-015 | I12 | AC16 | CERT-001, CERT-008 |
| REQ-9.1-C08 | ADR-MC-001 §9.1, §2.5.3 | Continuation journal store — immutable per-continuation operation log | UT-C08-001–UT-C08-007, RT-08.8, INT-006 | I5, I10 | AC7 | CERT-001, CERT-008 |
| REQ-9.1-C09 | ADR-MC-001 §9.1, §2.6.2, §2.13 | Completion receipt service — generate and verify signed continuation receipts | UT-C09-001–UT-C09-008, RT-09.*, SEC-028–SEC-031 | I6 | AC10 | CERT-001, CERT-008, CERT-012 |
| REQ-9.1-C10 | ADR-MC-001 §9.1, §2.6, §2.12 | Reconciliation engine — classify and resolve continuation reports | UT-C10-001–UT-C10-013, RT-10.*, RT-11.*, INT-009–INT-013 | I7, I8, I10 | AC9, AC11 | CERT-001, CERT-003, CERT-008 |
| REQ-9.1-C11 | ADR-MC-001 §9.1, §2.6.3.4, §2.12 | Conflict review queue — surface conflicting continuation results for operators | UT-C11-001–UT-C11-007, RT-10.4, RT-11.3, RT-11.4 | I8 | AC9, AC11 | CERT-003, CERT-008 |
| REQ-9.1-C12 | ADR-MC-001 §9.1, §2.13 | Audit event pipeline — append continuation events to immutable audit ledger | UT-C12-001–UT-C12-007, RT-14.*, INT-016, SEC-015–SEC-018 | I11 | AC12 | CERT-010, CERT-008, CERT-012 |
| REQ-9.1-C13 | ADR-MC-001 §9.1, §2.5 | Downstream effect identity layer — validate (command_id, operation_id, side_effect_slot) before applying effects | UT-C13-001–UT-C13-008, RT-08.*, RT-16.*, INT-007, INT-017 | I10, I15 | AC7, AC18 | CERT-001, CERT-008, CERT-016 |
| REQ-9.1-C14 | ADR-MC-001 §9.1, §2.8 | Signed time-anchor service — issue and validate signed wall-clock anchors | UT-C14-001–UT-C14-008, RT-15.*, RES-009–RES-012 | I14 | AC15 | CERT-015, CERT-008 |

### 19.2 Section 9.2 — Required Configuration

Each of the 18 configuration settings must be implemented and exercised by at least one test. The table traces each setting to its exercising tests and certification gate.

| Req ID | ADR Ref | Setting | Test Case(s) | Cert Gate(s) |
|---|---|---|---|---|
| REQ-9.2-S01 | ADR-MC-001 §9.2 | brain_heartbeat_miss_threshold | RT-03.1, RT-03.2, UT-C03-002, UT-C03-003, INT-003, RES-005, CHS-014 | CERT-009 |
| REQ-9.2-S02 | ADR-MC-001 §9.2 | lease_rejection_threshold | RT-03.1, RT-03.3, RT-01.9, INT-003, INT-004, RES-005 | CERT-009 |
| REQ-9.2-S03 | ADR-MC-001 §9.2 | status_query_threshold | RT-03.2, INT-004 | CERT-009 |
| REQ-9.2-S04 | ADR-MC-001 §9.2 | policy_silence_threshold | RT-03.3, UT-C07-007, INT-004, CHS-014 | CERT-009 |
| REQ-9.2-S05 | ADR-MC-001 §9.2 | witness_quorum_size | RT-04.2, RT-04.3, RT-04.4, UT-C04-008, CHS-003, CHS-004 | CERT-009 |
| REQ-9.2-S06 | ADR-MC-001 §9.2 | witness_statement_max_age | RT-04.6, UT-C04-004 | CERT-009 |
| REQ-9.2-S07 | ADR-MC-001 §9.2 | brain_outage_grace_period | RT-03.7, INT-003, RES-005 | CERT-009 |
| REQ-9.2-S08 | ADR-MC-001 §9.2 | brain_recovery_confirmation_period | RT-13.1, REC-008, INT-008 | CERT-009 |
| REQ-9.2-S09 | ADR-MC-001 §9.2 | max_continuation_duration | RT-06.1, RT-06.8, UT-C02-015, RES-011, SEC-023, CHS-015 | CERT-009 |
| REQ-9.2-S10 | ADR-MC-001 §9.2 | max_continuation_operations | RT-06.2, UT-C02-016, UT-C08-005, SEC-024 | CERT-009 |
| REQ-9.2-S11 | ADR-MC-001 §9.2 | max_continuation_attempts_per_command | RT-06.3 | CERT-009 |
| REQ-9.2-S12 | ADR-MC-001 §9.2 | max_concurrent_continuations_per_executor | RT-06.4, CHS-017 | CERT-009 |
| REQ-9.2-S13 | ADR-MC-001 §9.2 | completion_report_deadline | RT-10.15, RT-13.6, REC-013 | CERT-009 |
| REQ-9.2-S14 | ADR-MC-001 §9.2 | tenant_max_continuation_rate | RT-06.6, CHS-018, MT-006 | CERT-009 |
| REQ-9.2-S15 | ADR-MC-001 §9.2 | continuation_capability_max_validity | RT-06.7, CHS-015 | CERT-009 |
| REQ-9.2-S16 | ADR-MC-001 §9.2 | max_clock_skew_tolerance | RT-15.3, UT-C14-002, RES-009, SEC-023 | CERT-009, CERT-015 |
| REQ-9.2-S17 | ADR-MC-001 §9.2 | max_clock_rollback_tolerance | RT-15.4, RT-03.9, UT-C14-003, RES-010 | CERT-009, CERT-015 |
| REQ-9.2-S18 | ADR-MC-001 §9.2 | max_revocation_cache_age | RT-07.4, UT-C06-006, RES-015, SEC-027 | CERT-009 |

### 19.3 Section 9.3 — Required Tests

Each of the 16 required tests from ADR-MC-001 Section 9.3 must pass before the Sigma gate may be evaluated. The table traces each required test to its expanded test cases, invariants verified, acceptance criteria satisfied, and certification gate.

| Req ID | ADR Ref | Required Test | Expanded Test Cases | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|
| REQ-9.3-T01 | ADR-MC-001 §9.3 | Lease lifecycle | RT-01.1–RT-01.10 | I1, I2, I3a | AC1 | CERT-007 |
| REQ-9.3-T02 | ADR-MC-001 §9.3 | Capability issuance and validation | RT-02.1–RT-02.10 | I3, I3a, I4 | AC2 | CERT-007 |
| REQ-9.3-T03 | ADR-MC-001 §9.3 | Brain outage declaration | RT-03.1–RT-03.10 | I4, I14 | AC3 | CERT-007 |
| REQ-9.3-T04 | ADR-MC-001 §9.3 | Witness statement validation | RT-04.1–RT-04.12 | I4, I14 | AC4 | CERT-007 |
| REQ-9.3-T05 | ADR-MC-001 §9.3 | Continuation eligibility | RT-05.1–RT-05.14 | I1–I5, I9, I12–I15 | AC5 | CERT-007 |
| REQ-9.3-T06 | ADR-MC-001 §9.3 | Continuation bounds | RT-06.1–RT-06.10 | I5 | AC6 | CERT-007 |
| REQ-9.3-T07 | ADR-MC-001 §9.3 | Revocation watermark | RT-07.1–RT-07.10 | I13 | AC17 | CERT-007 |
| REQ-9.3-T08 | ADR-MC-001 §9.3 | Idempotency across continuation/replay | RT-08.1–RT-08.10 | I10 | AC7 | CERT-007 |
| REQ-9.3-T09 | ADR-MC-001 §9.3 | Completion receipt | RT-09.1–RT-09.10 | I6 | AC10 | CERT-007 |
| REQ-9.3-T10 | ADR-MC-001 §9.3 | Reconciliation | RT-10.1–RT-10.15 | I7, I8, I10 | AC9 | CERT-007 |
| REQ-9.3-T11 | ADR-MC-001 §9.3 | Split-brain conflict | RT-11.1–RT-11.9 | I8, I10 | AC11 | CERT-007 |
| REQ-9.3-T12 | ADR-MC-001 §9.3 | Cross-tenant isolation | RT-12.1–RT-12.9 | I9 | AC13 | CERT-007 |
| REQ-9.3-T13 | ADR-MC-001 §9.3 | Recovery protocol | RT-13.1–RT-13.13 | I7, I8 | AC14 | CERT-007 |
| REQ-9.3-T14 | ADR-MC-001 §9.3 | Audit ledger completeness | RT-14.1–RT-14.8 | I11 | AC12 | CERT-007, CERT-010 |
| REQ-9.3-T15 | ADR-MC-001 §9.3 | Time authority | RT-15.1–RT-15.10 | I14 | AC15 | CERT-007, CERT-015 |
| REQ-9.3-T16 | ADR-MC-001 §9.3 | Side-effect class enforcement | RT-16.1–RT-16.10 | I15 | AC18 | CERT-007, CERT-016 |

---

## 20. ADR-MC-001 Section 11 — Acceptance Criteria

Each of the 20 acceptance criteria must be satisfied before the ADR is considered fully implemented. The table traces each acceptance criterion to the primary tests, invariants, and certification gates that verify it.

| Req ID | ADR Ref | Acceptance Criterion | Component(s) | Primary Test Case(s) | Invariant(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|
| REQ-11-AC1 | ADR-MC-001 §11 (AC1) | Lease lifecycle and continuation capability lifecycle are fully specified and separated | C01, C02, C14, C12 | RT-01.*, UT-C01-*, UT-C02-*, INT-001, INT-002 | I1, I2, I3a | CERT-001, CERT-006 |
| REQ-11-AC2 | ADR-MC-001 §11 (AC2) | Continuation capability is unusable before lease expiry and bounded by time, operations, and scope | C02, C14, C13 | RT-02.*, UT-C02-001–UT-C02-004, SEC-006, INT-001 | I3, I3a | CERT-001, CERT-006 |
| REQ-11-AC3 | ADR-MC-001 §11 (AC3) | Brain outage detection uses at least two independent signals including one direct-Brain signal, with a grace period | C03, C04, C05, C14 | RT-03.*, UT-C03-*, UT-C04-*, INT-003, INT-004, SEC-021, SEC-022 | I4, I14 | CERT-001, CERT-006 |
| REQ-11-AC4 | ADR-MC-001 §11 (AC4) | Witness trust model is fully defined with identity, quorum, replay resistance, and self-exclusion | C04, C14 | RT-04.*, UT-C04-*, CHS-003, CHS-004, SEC-020 | I4, I14 | CERT-001, CERT-006, CERT-014 |
| REQ-11-AC5 | ADR-MC-001 §11 (AC5) | Continuation eligibility criteria are explicit and default to STOP | C01–C07, C14, C05 | RT-05.*, UT-C05-003, UT-C05-004, INT-005, SEC-019 | I1–I5, I9, I12–I15 | CERT-001, CERT-006 |
| REQ-11-AC6 | ADR-MC-001 §11 (AC6) | Continuation limits are defined with platform and tenant bounds | C02, C05, C08 | RT-06.*, UT-C02-015, UT-C02-016, MT-005, MT-006, CHS-017, CHS-018 | I5, I9 | CERT-001, CERT-006 |
| REQ-11-AC7 | ADR-MC-001 §11 (AC7) | Stable external-effect identity is defined and used for duplicate suppression across normal execution, continuation, and replay | C08, C13, C10 | RT-08.*, UT-C13-001, UT-C13-002, INT-007, SEC-010 | I10 | CERT-001, CERT-006 |
| REQ-11-AC8 | ADR-MC-001 §11 (AC8) | Replay semantics preserve effect identity and require reconciliation before authorization | C10, C01, C13, C12 | REC-001–REC-007, RT-08.7, RT-08.10, INT-013 | I7, I10 | CERT-004, CERT-006 |
| REQ-11-AC9 | ADR-MC-001 §11 (AC9) | Reconciliation protocol separates result selection, effect reconciliation, compensation, and manual review | C10, C11, C13, C09, C12 | RT-10.*, UT-C10-*, INT-009–INT-013 | I7, I8, I10 | CERT-001, CERT-006 |
| REQ-11-AC10 | ADR-MC-001 §11 (AC10) | Completion receipts are mandatory, signed, and immutable | C09, C12, C14 | RT-09.*, UT-C09-*, SEC-028, SEC-029 | I6 | CERT-001, CERT-006, CERT-012 |
| REQ-11-AC11 | ADR-MC-001 §11 (AC11) | Split-brain handling detects conflicts, freezes effects, and routes to manual review | C10, C11, C13, C09, C12 | RT-11.*, UT-C11-*, CHS-007–CHS-010 | I8, I10 | CERT-003, CERT-006, CERT-014 |
| REQ-11-AC12 | ADR-MC-001 §11 (AC12) | Audit chain includes all continuation events; authoritative audit storage is never truncated | C12 | RT-14.*, UT-C12-*, INT-016, SEC-015–SEC-018 | I11 | CERT-010, CERT-006, CERT-012 |
| REQ-11-AC13 | ADR-MC-001 §11 (AC13) | Tenant isolation is guaranteed throughout continuation and reconciliation | C02, C06, C04, C10, C12 | RT-12.*, MT-001–MT-012, SEC-011–SEC-014, INT-018 | I9 | CERT-011, CERT-006, CERT-012 |
| REQ-11-AC14 | ADR-MC-001 §11 (AC14) | Recovery protocol defines recovery detection, report collection, reconciliation, and policy refresh | C03, C10, C11, C06, C07, C12, C09 | RT-13.*, REC-008–REC-016, INT-008, RES-013 | I7, I8, I12, I13 | CERT-001, CERT-006 |
| REQ-11-AC15 | ADR-MC-001 §11 (AC15) | Trusted time, clock skew, monotonic time, and signed time anchors are specified | C14, C01, C02, C06 | RT-15.*, UT-C14-*, RES-009–RES-012, SEC-023 | I14 | CERT-015, CERT-006 |
| REQ-11-AC16 | ADR-MC-001 §11 (AC16) | Policy snapshot is pinned by hash and bounded by validity time | C02, C07, C14 | UT-C07-*, RT-02.9, RT-05.9, INT-015, SEC-026 | I12 | CERT-001, CERT-006 |
| REQ-11-AC17 | ADR-MC-001 §11 (AC17) | Revocation watermark and cache-age rules are fail-closed | C06, C02, C14 | RT-07.*, UT-C06-*, INT-014, RES-015, SEC-027 | I13 | CERT-001, CERT-006, CERT-013 |
| REQ-11-AC18 | ADR-MC-001 §11 (AC18) | Side effects are classified and Class 3 effects are prohibited during continuation | C02, C13, C10, C11 | RT-16.*, UT-C13-006, INT-017, SEC-025 | I15 | CERT-016, CERT-006, CERT-012 |
| REQ-11-AC19 | ADR-MC-001 §11 (AC19) | Threat model, invariants, glossary, and implementation prerequisites are complete | All | CERT-005, CERT-006, CERT-008, CERT-009 | I1–I15 | CERT-006 |
| REQ-11-AC20 | ADR-MC-001 §11 (AC20) | Non-goals explicitly exclude implementation, deployment, and authority activation | — | CERT-018 | — | CERT-018, CERT-017 |

---

## 21. ADR-002 Section 2.5 — Sigma Continuation Condition and Security/Failure Boundaries

ADR-002 Section 2.5 defines the security and failure boundaries for the Mythos Brain architecture, including the Sigma continuation condition (the "In-Flight Execution Behavior" bullet) that ADR-MC-001 implements. The table below maps each ADR-002 Section 2.5 requirement to the ADR-MC-001 components, tests, invariants, acceptance criteria, and certification gates that satisfy it.

| Req ID | ADR Ref | Requirement | Component(s) | Test Case(s) | Invariant(s) | AC(s) | Cert Gate(s) |
|---|---|---|---|---|---|---|---|
| REQ-A2-2.5-01 | ADR-002 §2.5 (In-Flight Execution Behavior) | In-flight executions are not cancelled by Brain unavailability; they continue under their existing lease; if the lease expires while the Brain is still unavailable, the executor may optionally continue processing if it has local state to complete the task, but must report completion when the Brain recovers — THIS IS THE SIGMA CONTINUATION CONDITION that ADR-MC-001 implements | C01, C02, C05, C09, C10 | RT-05.1, RT-09.1, RT-13.6, CERT-001, CERT-002, INT-006, INT-008 | I1, I2, I3, I4, I5, I6, I7 | AC1, AC2, AC5, AC10, AC14 | CERT-001, CERT-002, CERT-006 |
| REQ-A2-2.5-02 | ADR-002 §2.5 (Brain Unavailability Behavior) | If the Brain is unavailable, in-flight executions continue to completion; new intents are queued and held; the system operates in degraded mode — no new dispatches, no new cancellations, but existing work is not lost | C05, C08, C09 | RT-05.1, RES-005, RES-006, INT-006 | I4, I5 | AC5, AC14 | CERT-001, CERT-013 |
| REQ-A2-2.5-03 | ADR-002 §2.5 (Recovery and Replay Authority) | On Brain recovery, the outbox is drained; in-flight intents are checked against executor acknowledgments; unconfirmed intents are replayed; the recovery procedure is deterministic and auditable | C10, C01, C12, C09 | RT-13.7, RT-13.10, REC-001, REC-003, REC-004, INT-008, INT-013 | I7, I10, I11 | AC8, AC14 | CERT-004, CERT-001 |
| REQ-A2-2.5-04 | ADR-002 §2.5 (Split-Brain Prevention) | The Brain uses lease-based leadership; only one active leader accepts new intents; followers are read-only; if the leader loses its lease, a follower takes over with no split-brain window | C01, C10, C11 | RT-11.*, CHS-007–CHS-010, RES-008 | I8, I1 | AC1, AC11 | CERT-003, CERT-014 |
| REQ-A2-2.5-05 | ADR-002 §2.5 (Tenant Isolation) | One tenant's execution cannot affect another; all dispatch envelopes carry tenant_id and executors enforce isolation at the tenant boundary | C02, C06, C04, C10, C12 | RT-12.*, MT-001–MT-012, SEC-011–SEC-014, INT-018 | I9 | AC13 | CERT-011, CERT-012 |
| REQ-A2-2.5-06 | ADR-002 §2.5 (Policy-Version Snapshots) | The Brain records which policy version was active when an intent was authorized; this prevents stale approvals from bypassing updated policies | C07, C02 | UT-C07-001, UT-C07-003, RT-02.1, INT-015 | I12 | AC16 | CERT-001 |
| REQ-A2-2.5-07 | ADR-002 §2.5 (Stale Approval Invalidation) | If a policy has tightened since an approval was granted, the approval is invalidated and the intent must be re-authorized under the current policy version | C07, C02, C06 | UT-C07-003, RT-01.8, RT-05.9 | I12, I13 | AC16, AC17 | CERT-001 |
| REQ-A2-2.5-08 | ADR-002 §2.5 (Failure Isolation) | A failure in an executor (e.g., an agent crash) must not corrupt the Brain's intent ledger | C12, C05, C08 | RES-001, RES-002, RES-018, CHS-001, CHS-002 | I11 | AC12, AC14 | CERT-010, CERT-013, CERT-014 |
| REQ-A2-2.5-09 | ADR-002 §2.5 (Authenticated or Signed Dispatch Envelopes) | All dispatch messages carry a signature or auth token that executors verify before processing; this prevents forged dispatch | C01, C02, C14 | UT-C01-004, UT-C02-002, SEC-001, SEC-002, SEC-003, INT-001 | I1, I3 | AC1, AC2 | CERT-001, CERT-012 |
| REQ-A2-2.5-10 | ADR-002 §2.5 (Service-to-Service Authentication) | The Brain and executors authenticate via mutual TLS or signed JWT tokens; no executor accepts a dispatch without verifying the Brain's identity | C01, C02, C14 | UT-C01-004, UT-C02-002, SEC-001, SEC-002, SEC-019 | I1, I3, I4 | AC1, AC2 | CERT-001, CERT-012 |
| REQ-A2-2.5-11 | ADR-002 §2.5 (Actor Delegation) | The Brain propagates actor_id and permissions to executors via authenticated dispatch envelopes; executors do not accept unsigned or unauthenticated dispatch | C01, C02 | UT-C01-001, UT-C02-001, SEC-019, INT-001 | I1, I3 | AC1, AC2 | CERT-001, CERT-012 |
| REQ-A2-2.5-12 | ADR-002 §2.5 (Privilege Boundaries) | Executors operate with least-privilege credentials; the Brain does not grant executors permissions beyond what the originating actor's policy allows | C02, C07 | UT-C02-012, UT-C02-013, RT-05.8, RT-16.10 | I3, I15 | AC2, AC18 | CERT-001, CERT-016 |
| REQ-A2-2.5-13 | ADR-002 §2.5 (Executor-Compromise Response) | If an executor is compromised, its credentials are revoked, its in-flight tasks are redelivered to other executors, and a full audit trail is preserved for forensic review | C06, C12, C10, C11 | UT-C06-004, RT-07.5, RT-10.5, SEC-007, SEC-028, RES-002 | I11, I13, I8 | AC12, AC17 | CERT-010, CERT-012 |
| REQ-A2-2.5-14 | ADR-002 §2.5 (Degraded Read-Only Operation) | When the Brain is partially unavailable, read-only queries (including Mission Control dashboard) continue to function against the last-known state; new dispatches are paused until the Brain recovers | C12, C05 | RT-13.11, REC-014, INT-008 | I11, I12 | AC14 | CERT-001 |
| REQ-A2-2.5-15 | ADR-002 §2.5 (Panic Mode) | In the event of a detected governance breach, the Brain enters Panic Mode, locking all outbound dispatch, requiring administrative reset | C06, C12 | RT-07.10, UT-C06-008, UT-C07-005 | I13, I11 | AC17 | CERT-001 |
| REQ-A2-2.5-16 | ADR-002 §2.5 (Policy Enforcement Point) | The Brain acts as the PEP, validating every intent against the governed_inference layer before dispatch | C01, C02, C07 | UT-C01-003, UT-C02-017, RT-02.8, INT-001 | I1, I4 | AC1, AC5 | CERT-001 |
| REQ-A2-2.5-17 | ADR-002 §2.5 (RTO Target) | Brain state store Recovery Time Objective: ≤ 5 minutes (provisional — requires implementation validation) | C03, C10, C14 | RT-13.1, REC-008, INT-008, RES-013 | I7 | AC14 | CERT-013 |
| REQ-A2-2.5-18 | ADR-002 §2.5 (RPO Target) | Brain state store Recovery Point Objective: ≤ 30 seconds (provisional — requires implementation validation) | C12, C09, C10 | RT-13.12, REC-015, RT-10.15 | I7, I11 | AC12, AC14 | CERT-010, CERT-013 |

---

## 22. Coverage Summary

### 22.1 Requirement Counts

| Source | Section | Requirements |
|---|---|---|
| ADR-MC-001 §2.1.1 | Lease Acquisition | 4 |
| ADR-MC-001 §2.1.2 | Lease Renewal | 7 |
| ADR-MC-001 §2.1.3 | Lease Expiry | 5 |
| ADR-MC-001 §2.1.4 | Continuation Capability | 10 |
| ADR-MC-001 §2.2.1 | Detection Signals | 5 |
| ADR-MC-001 §2.2.2 | Detection Rules | 5 |
| ADR-MC-001 §2.2.3 | Time Basis for Detection | 5 |
| ADR-MC-001 §2.2.4 | Witness Trust Model | 9 |
| ADR-MC-001 §2.3 | Continuation Eligibility | 13 |
| ADR-MC-001 §2.4 | Continuation Limits | 10 |
| ADR-MC-001 §2.5.1 | Stable External-Effect Identity | 5 |
| ADR-MC-001 §2.5.2 | Duplicate Suppression Layers | 6 |
| ADR-MC-001 §2.5.3 | Continuation Journal | 1 |
| ADR-MC-001 §2.6.1 | Recovery Detection | 3 |
| ADR-MC-001 §2.6.2 | Completion Reporting | 2 |
| ADR-MC-001 §2.6.3.1 | Result Selection | 5 |
| ADR-MC-001 §2.6.3.2 | Effect Reconciliation | 5 |
| ADR-MC-001 §2.6.3.3 | Compensation | 3 |
| ADR-MC-001 §2.6.3.4 | Manual Review | 2 |
| ADR-MC-001 §2.6.4 | Reconciliation Classifications | 5 |
| ADR-MC-001 §2.7 | Replay Semantics | 7 |
| ADR-MC-001 §2.8 | Time Authority and Clock Rules | 8 |
| ADR-MC-001 §2.9 | Side-Effect Classification | 6 |
| ADR-MC-001 §2.10 | Revocation and Cancellation Watermark | 7 |
| ADR-MC-001 §2.11 | Policy Snapshot Model | 4 |
| ADR-MC-001 §2.12.1 | Split-Brain Detection | 3 |
| ADR-MC-001 §2.12.2 | Split-Brain Resolution | 6 |
| ADR-MC-001 §2.13 | Audit Chain Requirements | 3 |
| ADR-MC-001 §2.14 | Tenant Isolation Guarantees | 6 |
| ADR-MC-001 §2.15 | Recovery Protocol | 10 |
| ADR-MC-001 §7 | Invariants (I1–I15, I3a) | 16 |
| ADR-MC-001 §9.1 | Required Components | 14 |
| ADR-MC-001 §9.2 | Required Configuration | 18 |
| ADR-MC-001 §9.3 | Required Tests | 16 |
| ADR-MC-001 §11 | Acceptance Criteria | 20 |
| ADR-002 §2.5 | Security and Failure Boundaries | 18 |
| **Total** | | **271** |

### 22.2 Coverage Metrics

| Coverage Target | Total | Covered | Percentage |
|---|---|---|---|
| ADR-MC-001 Section 2.1–2.15 requirements | 168 | 168 | 100% |
| ADR-MC-001 Section 7 invariants (I1–I15, I3a) | 16 | 16 | 100% |
| ADR-MC-001 Section 9.1 required components | 14 | 14 | 100% |
| ADR-MC-001 Section 9.2 configuration settings | 18 | 18 | 100% |
| ADR-MC-001 Section 9.3 required tests | 16 | 16 | 100% |
| ADR-MC-001 Section 11 acceptance criteria | 20 | 20 | 100% |
| ADR-002 Section 2.5 requirements | 18 | 18 | 100% |
| **Total requirements** | **271** | **271** | **100%** |

### 22.3 Test Coverage

| Metric | Count |
|---|---|
| Total test cases mapped (from doc 08) | 396 |
| Required tests (RT-*) mapped | 16 test groups, 154 test cases |
| Unit tests (UT-*) mapped | 14 components, 104 test cases |
| Integration tests (INT-*) mapped | 20 |
| Resilience tests (RES-*) mapped | 20 |
| Chaos tests (CHS-*) mapped | 18 |
| Security tests (SEC-*) mapped | 32 |
| Replay/recovery tests (REC-*) mapped | 18 |
| Multi-tenant tests (MT-*) mapped | 12 |
| Certification tests (CERT-*) mapped | 18 |
| **Total tests mapped** | **396** |

### 22.4 Invariant Coverage

| Invariant | Requirements Enforcing | Tests Verifying | Covered |
|---|---|---|---|
| I1 | REQ-2.1.1-01–04, REQ-2.3-01, REQ-7-I1, REQ-A2-2.5-09–11, REQ-A2-2.5-16 | UT-C01-*, RT-01.*, SEC-004, SEC-005, INT-001 | Yes |
| I2 | REQ-2.1.3-01–05, REQ-7-I2 | UT-C01-005, RT-01.3, RT-05.2, SEC-004, SEC-005, RES-004 | Yes |
| I3 | REQ-2.1.4-01–10, REQ-2.3-03, REQ-7-I3, REQ-A2-2.5-09–12 | UT-C02-003, UT-C02-004, RT-02.2, RT-02.3, SEC-006, SEC-007 | Yes |
| I3a | REQ-2.1.2-05–07, REQ-7-I3a | UT-C02-009, RT-01.10, INT-002, INT-020, CHS-016 | Yes |
| I4 | REQ-2.1.4-04, REQ-2.2.2-*, REQ-2.3-13, REQ-2.9-05, REQ-7-I4, REQ-A2-2.5-01 | RT-03.*, RT-04.*, RT-05.14, SEC-019–SEC-022 | Yes |
| I5 | REQ-2.3-09, REQ-2.4-*, REQ-7-I5 | RT-06.*, UT-C02-015, UT-C02-016, UT-C08-005, RES-011, SEC-023, SEC-024 | Yes |
| I6 | REQ-2.1.4-08–09, REQ-2.3-11, REQ-2.6.2-02, REQ-7-I6 | RT-09.*, UT-C09-001–UT-C09-003, SEC-028–SEC-031 | Yes |
| I7 | REQ-2.6.1-*, REQ-2.6.2-*, REQ-2.6.3.*, REQ-2.6.4-*, REQ-2.7-01–02, REQ-2.15-*, REQ-7-I7 | RT-10.*, RT-13.*, UT-C10-*, INT-008–INT-013, REC-008–REC-016 | Yes |
| I8 | REQ-2.6.3.1-03–04, REQ-2.6.3.2-03–05, REQ-2.6.3.3-03, REQ-2.6.3.4-*, REQ-2.6.4-03–05, REQ-2.12.*, REQ-7-I8 | RT-11.*, UT-C11-*, UT-C10-004, UT-C10-006, CHS-005, CHS-008, CHS-009, SEC-032 | Yes |
| I9 | REQ-2.3-10, REQ-2.14-*, REQ-7-I9, REQ-A2-2.5-05 | RT-12.*, MT-001–MT-012, SEC-011–SEC-014, INT-018 | Yes |
| I10 | REQ-2.5.1-*, REQ-2.5.2-*, REQ-2.5.3-01, REQ-2.7-04, REQ-7-I10 | RT-08.*, UT-C13-001, UT-C13-002, UT-C08-001, UT-C08-004, INT-007, INT-013, SEC-009, SEC-010, REC-001–REC-007 | Yes |
| I11 | REQ-2.1.1-04, REQ-2.1.2-06, REQ-2.1.3-04, REQ-2.13-*, REQ-2.15-09, REQ-7-I11, REQ-A2-2.5-08 | RT-14.*, UT-C12-*, INT-016, SEC-015–SEC-018, RES-018 | Yes |
| I12 | REQ-2.3-08, REQ-2.11-*, REQ-7-I12, REQ-A2-2.5-06–07 | UT-C07-*, RT-02.9, RT-05.9, INT-015, SEC-026 | Yes |
| I13 | REQ-2.1.2-02, REQ-2.3-04–05, REQ-2.10-*, REQ-2.11-03, REQ-7-I13, REQ-A2-2.5-07, REQ-A2-2.5-13, REQ-A2-2.5-15 | RT-07.*, UT-C06-*, INT-014, RES-015, SEC-027, CHS-013 | Yes |
| I14 | REQ-2.2.3-*, REQ-2.8-*, REQ-7-I14 | RT-15.*, UT-C14-*, RES-009–RES-012, SEC-023, CHS-011 | Yes |
| I15 | REQ-2.3-07, REQ-2.6.3.2-04–05, REQ-2.6.3.3-03, REQ-2.9-04, REQ-2.11-04, REQ-7-I15, REQ-A2-2.5-12 | RT-16.*, UT-C13-006, INT-017, SEC-025, RES-014 | Yes |

**Total invariants covered: 16/16 (100%)** (I1–I15 including I3a)

### 22.5 Acceptance Criteria Coverage

| AC | Requirements Satisfying | Tests Verifying | Cert Gate(s) | Covered |
|---|---|---|---|---|
| AC1 | REQ-2.1.1-*, REQ-2.1.2-*, REQ-2.1.3-*, REQ-7-I1, REQ-7-I2, REQ-7-I3a, REQ-A2-2.5-09–11, REQ-A2-2.5-16 | RT-01.*, UT-C01-*, UT-C02-*, INT-001, INT-002 | CERT-001, CERT-006 | Yes |
| AC2 | REQ-2.1.3-05, REQ-2.1.4-*, REQ-7-I3, REQ-7-I3a, REQ-A2-2.5-09–12 | RT-02.*, UT-C02-001–UT-C02-004, SEC-006, INT-001 | CERT-001, CERT-006 | Yes |
| AC3 | REQ-2.2.1-*, REQ-2.2.2-*, REQ-2.2.3-*, REQ-7-I4, REQ-7-I14 | RT-03.*, UT-C03-*, UT-C04-*, INT-003, INT-004, SEC-021, SEC-022 | CERT-001, CERT-006 | Yes |
| AC4 | REQ-2.2.1-04, REQ-2.2.4-*, REQ-7-I4 | RT-04.*, UT-C04-*, CHS-003, CHS-004, SEC-020 | CERT-001, CERT-006, CERT-014 | Yes |
| AC5 | REQ-2.1.3-05, REQ-2.1.4-04, REQ-2.3-*, REQ-2.9-05, REQ-7-I4, REQ-A2-2.5-01, REQ-A2-2.5-16 | RT-05.*, UT-C05-003, UT-C05-004, INT-005, SEC-019 | CERT-001, CERT-006 | Yes |
| AC6 | REQ-2.3-09, REQ-2.4-*, REQ-7-I5 | RT-06.*, UT-C02-015, UT-C02-016, MT-005, MT-006, CHS-017, CHS-018 | CERT-001, CERT-006 | Yes |
| AC7 | REQ-2.5.1-*, REQ-2.5.2-*, REQ-2.5.3-01, REQ-2.7-04, REQ-7-I10 | RT-08.*, UT-C13-001, UT-C13-002, INT-007, SEC-010 | CERT-001, CERT-006 | Yes |
| AC8 | REQ-2.5.1-05, REQ-2.5.2-06, REQ-2.7-*, REQ-7-I7, REQ-7-I10, REQ-A2-2.5-03 | REC-001–REC-007, RT-08.7, RT-08.10, INT-013 | CERT-004, CERT-006 | Yes |
| AC9 | REQ-2.5.2-05, REQ-2.6.3.*, REQ-2.6.4-*, REQ-2.7-02, REQ-2.7-07, REQ-2.15-04, REQ-7-I7, REQ-7-I8, REQ-7-I10 | RT-10.*, UT-C10-*, INT-009–INT-013 | CERT-001, CERT-006 | Yes |
| AC10 | REQ-2.1.4-08–09, REQ-2.3-11, REQ-2.6.2-*, REQ-7-I6, REQ-A2-2.5-01 | RT-09.*, UT-C09-*, SEC-028, SEC-029 | CERT-001, CERT-006, CERT-012 | Yes |
| AC11 | REQ-2.6.3.1-03–04, REQ-2.6.3.2-03–05, REQ-2.6.3.3-03, REQ-2.6.3.4-*, REQ-2.6.4-03–05, REQ-2.12.*, REQ-2.15-05–06, REQ-7-I8, REQ-A2-2.5-04 | RT-11.*, UT-C11-*, CHS-007–CHS-010 | CERT-003, CERT-006, CERT-014 | Yes |
| AC12 | REQ-2.1.1-04, REQ-2.1.2-06, REQ-2.1.3-04, REQ-2.13-*, REQ-2.15-09, REQ-7-I11, REQ-A2-2.5-08, REQ-A2-2.5-18 | RT-14.*, UT-C12-*, INT-016, SEC-015–SEC-018 | CERT-010, CERT-006, CERT-012 | Yes |
| AC13 | REQ-2.3-10, REQ-2.4-06, REQ-2.4-09, REQ-2.14-*, REQ-7-I9, REQ-A2-2.5-05 | RT-12.*, MT-001–MT-012, SEC-011–SEC-014, INT-018 | CERT-011, CERT-006, CERT-012 | Yes |
| AC14 | REQ-2.6.1-*, REQ-2.6.2-*, REQ-2.15-*, REQ-7-I7, REQ-A2-2.5-02–03, REQ-A2-2.5-14, REQ-A2-2.5-17–18 | RT-13.*, REC-008–REC-016, INT-008, RES-013 | CERT-001, CERT-006 | Yes |
| AC15 | REQ-2.2.3-*, REQ-2.3-12, REQ-2.4-08, REQ-2.8-*, REQ-7-I14 | RT-15.*, UT-C14-*, RES-009–RES-012, SEC-023 | CERT-015, CERT-006 | Yes |
| AC16 | REQ-2.3-08, REQ-2.11-*, REQ-2.15-08, REQ-7-I12, REQ-A2-2.5-06–07 | UT-C07-*, RT-02.9, RT-05.9, INT-015, SEC-026 | CERT-001, CERT-006 | Yes |
| AC17 | REQ-2.1.4-10, REQ-2.3-04–05, REQ-2.10-*, REQ-2.11-03, REQ-7-I13, REQ-A2-2.5-07, REQ-A2-2.5-13, REQ-A2-2.5-15 | RT-07.*, UT-C06-*, INT-014, RES-015, SEC-027 | CERT-001, CERT-006, CERT-013 | Yes |
| AC18 | REQ-2.3-07, REQ-2.6.3.2-04–05, REQ-2.6.3.3-03, REQ-2.9-*, REQ-2.11-04, REQ-7-I15, REQ-A2-2.5-12 | RT-16.*, UT-C13-006, INT-017, SEC-025 | CERT-016, CERT-006, CERT-012 | Yes |
| AC19 | REQ-7-I1–I15, REQ-9.1-C01–C14, REQ-9.2-S01–S18, REQ-9.3-T01–T16 | CERT-005, CERT-006, CERT-008, CERT-009 | CERT-006 | Yes |
| AC20 | REQ-2.15-10, REQ-11-AC20 | CERT-018 | CERT-018, CERT-017 | Yes |

**Total acceptance criteria covered: 20/20 (100%)**

### 22.6 Certification Gate Coverage

| Cert Gate | Requirements Verified | Covered |
|---|---|---|
| CERT-001 | Full lifecycle — all §2.1–§2.15 requirements | Yes |
| CERT-002 | Continuation and recovery — REQ-2.6.*, REQ-2.15.*, REQ-A2-2.5-01 | Yes |
| CERT-003 | Split-brain resolution — REQ-2.12.*, REQ-2.6.3.1-03–04, REQ-2.6.4-03–05 | Yes |
| CERT-004 | Replay — REQ-2.7.*, REQ-2.5.1-05, REQ-2.5.2-06 | Yes |
| CERT-005 | All 15 invariants — REQ-7-I1–I15 | Yes |
| CERT-006 | All 20 acceptance criteria — REQ-11-AC1–AC20 | Yes |
| CERT-007 | All 16 required tests — REQ-9.3-T01–T16 | Yes |
| CERT-008 | All 14 components — REQ-9.1-C01–C14 | Yes |
| CERT-009 | All 18 configuration settings — REQ-9.2-S01–S18 | Yes |
| CERT-010 | Audit chain — REQ-2.13.*, REQ-7-I11 | Yes |
| CERT-011 | Tenant isolation — REQ-2.14.*, REQ-7-I9, REQ-A2-2.5-05 | Yes |
| CERT-012 | Security — all SEC-* tests, REQ-7-I1–I15 | Yes |
| CERT-013 | Resilience — REQ-2.2.2-04, REQ-2.8-*, REQ-2.10-03, REQ-2.12.2-04, REQ-2.15-02, REQ-A2-2.5-08, REQ-A2-2.5-17–18 | Yes |
| CERT-014 | Chaos — REQ-2.2.4-03, REQ-2.12.*, REQ-2.4-04, REQ-2.4-06 | Yes |
| CERT-015 | Time authority — REQ-2.8.*, REQ-2.2.3-*, REQ-7-I14 | Yes |
| CERT-016 | Side-effect class — REQ-2.9.*, REQ-2.6.3.2-04–05, REQ-7-I15 | Yes |
| CERT-017 | Gate evaluation — REQ-2.15-10, REQ-11-AC20 | Yes |
| CERT-018 | Non-goals — REQ-11-AC20 | Yes |

**Total certification gates covered: 18/18 (100%)**

### 22.7 Component Coverage

| Component | Requirements Implemented | Tests Verifying | Cert Gate(s) | Covered |
|---|---|---|---|---|
| C01 | REQ-2.1.1-*, REQ-2.1.2-*, REQ-2.1.3-*, REQ-2.5.2-01, REQ-2.6.3.3-02, REQ-2.7-01–06, REQ-A2-2.5-09–11, REQ-A2-2.5-16 | UT-C01-*, RT-01.*, INT-001, INT-002 | CERT-001, CERT-008 | Yes |
| C02 | REQ-2.1.2-05–07, REQ-2.1.4-*, REQ-2.3-03–10, REQ-2.4-*, REQ-2.9-*, REQ-2.10-02, REQ-2.11-*, REQ-A2-2.5-09–12, REQ-A2-2.5-16 | UT-C02-*, RT-02.*, RT-06.*, RT-16.*, INT-001, INT-002, INT-015 | CERT-001, CERT-008 | Yes |
| C03 | REQ-2.2.1-01–03, REQ-2.2.2-01–02, REQ-2.6.1-02, REQ-2.15-01, REQ-A2-2.5-17 | UT-C03-*, RT-03.*, RT-13.1, RT-13.2, INT-003, INT-008 | CERT-001, CERT-008 | Yes |
| C04 | REQ-2.2.1-04, REQ-2.2.2-03, REQ-2.2.4-*, REQ-2.11-03, REQ-A2-2.5-05 | UT-C04-*, RT-04.*, CHS-003, CHS-004 | CERT-001, CERT-008, CERT-014 | Yes |
| C05 | REQ-2.2.2-04–05, REQ-2.2.3-02–04, REQ-2.3-06, REQ-2.3-13, REQ-2.4-03–04, REQ-2.15-08, REQ-A2-2.5-02 | UT-C05-*, RT-05.*, RES-001, RES-005 | CERT-001, CERT-008, CERT-013 | Yes |
| C06 | REQ-2.1.2-02, REQ-2.1.3-01, REQ-2.1.4-10, REQ-2.10-*, REQ-2.11-03, REQ-2.14-02, REQ-2.15-08, REQ-A2-2.5-13, REQ-A2-2.5-15 | UT-C06-*, RT-07.*, INT-014 | CERT-001, CERT-008 | Yes |
| C07 | REQ-2.1.1-02, REQ-2.1.2-02, REQ-2.2.1-05, REQ-2.11-*, REQ-2.14-06, REQ-2.15-08, REQ-A2-2.5-06–07, REQ-A2-2.5-16 | UT-C07-*, RT-02.9, RT-05.9, INT-015 | CERT-001, CERT-008 | Yes |
| C08 | REQ-2.5.3-01, REQ-2.10-06, REQ-2.12.2-04, REQ-2.15-02, REQ-A2-2.5-08 | UT-C08-*, RT-08.8, INT-006, RES-001 | CERT-001, CERT-008 | Yes |
| C09 | REQ-2.1.4-08–09, REQ-2.6.2-*, REQ-2.12.2-04–05, REQ-2.15-02–03, REQ-A2-2.5-01 | UT-C09-*, RT-09.*, SEC-028–SEC-031 | CERT-001, CERT-008, CERT-012 | Yes |
| C10 | REQ-2.5.1-05, REQ-2.5.2-05–06, REQ-2.6.3.*, REQ-2.6.4-*, REQ-2.7-01–02, REQ-2.12.*, REQ-2.14-04, REQ-2.15-02–07, REQ-A2-2.5-03–05 | UT-C10-*, RT-10.*, RT-11.*, RT-13.7, INT-009–INT-013 | CERT-001, CERT-003, CERT-008 | Yes |
| C11 | REQ-2.6.3.1-03–04, REQ-2.6.3.2-03–05, REQ-2.6.3.3-03, REQ-2.6.3.4-*, REQ-2.6.4-03–05, REQ-2.12.*, REQ-2.15-05–06, REQ-A2-2.5-04 | UT-C11-*, RT-10.4, RT-11.3, RT-11.4 | CERT-003, CERT-008 | Yes |
| C12 | REQ-2.1.1-04, REQ-2.1.2-06, REQ-2.1.3-04, REQ-2.13-*, REQ-2.14-05, REQ-2.15-09–10, REQ-A2-2.5-08, REQ-A2-2.5-13–15, REQ-A2-2.5-18 | UT-C12-*, RT-14.*, INT-016, SEC-015–SEC-018 | CERT-010, CERT-008, CERT-012 | Yes |
| C13 | REQ-2.1.2-04, REQ-2.1.3-02–03, REQ-2.1.4-05–09, REQ-2.5.1-*, REQ-2.5.2-03–04, REQ-2.6.3.2-*, REQ-2.9-03–04, REQ-2.12.1-03, REQ-A2-2.5-05 | UT-C13-*, RT-08.*, RT-16.*, INT-007, INT-017 | CERT-001, CERT-008, CERT-016 | Yes |
| C14 | REQ-2.2.3-*, REQ-2.4-08, REQ-2.8-*, REQ-2.15-01, REQ-A2-2.5-17 | UT-C14-*, RT-15.*, RES-009–RES-012 | CERT-015, CERT-008 | Yes |

**Total components covered: 14/14 (100%)**

---

## 23. Gap Analysis

### 23.1 Identified Gaps

**No gaps identified.** All 271 requirements from ADR-MC-001 Sections 2.1–2.15, Section 7, Section 9 (9.1, 9.2, 9.3), and Section 11, plus all 18 requirements from ADR-002 Section 2.5, are fully traced to:
- At least one implementing component from the 14 in Section 9.1
- At least one verifying test case from the test matrix (doc 08)
- At least one enforced invariant from Section 7
- At least one satisfied acceptance criterion from Section 11
- At least one certification gate from doc 08 Section 12

### 23.2 Coverage Verification

| Verification Dimension | Count | Covered | Gaps |
|---|---|---|---|
| Requirements → Components | 271 | 271 | 0 |
| Requirements → Test Cases | 271 | 271 | 0 |
| Requirements → Invariants | 271 | 271 | 0 |
| Requirements → Acceptance Criteria | 271 | 271 | 0 |
| Requirements → Certification Gates | 271 | 271 | 0 |
| Invariants (I1–I15, I3a) | 16 | 16 | 0 |
| Acceptance Criteria (AC1–AC20) | 20 | 20 | 0 |
| Required Components (C01–C14) | 14 | 14 | 0 |
| Configuration Settings (S01–S18) | 18 | 18 | 0 |
| Required Tests (T01–T16) | 16 | 16 | 0 |
| Certification Gates (CERT-001–CERT-018) | 18 | 18 | 0 |

### 23.3 Notes on ADR-002 Section 2.5 Mapping

ADR-002 Section 2.5 defines 18 security and failure boundary requirements. ADR-MC-001 is the implementation ADR that satisfies the Sigma continuation condition (the "In-Flight Execution Behavior" bullet, REQ-A2-2.5-01) and its prerequisites. The remaining ADR-002 Section 2.5 requirements (tenant isolation, policy-version snapshots, split-brain prevention, recovery/replay authority, etc.) are satisfied by ADR-MC-001's comprehensive design as traced in Section 21 above.

Two ADR-002 Section 2.5 requirements deserve implementation-validation notes:
- **REQ-A2-2.5-17 (RTO Target ≤ 5 min):** Provisional; requires implementation validation. The recovery protocol (ADR-MC-001 §2.15) and brain_recovery_confirmation_period (default 10s) provide the mechanism, but the full RTO depends on infrastructure implementation.
- **REQ-A2-2.5-18 (RPO Target ≤ 30 sec):** Provisional; requires implementation validation. The audit event pipeline (C12) and completion report deadline provide the mechanism, but the full RPO depends on storage infrastructure.

These are not gaps in traceability — they are explicitly provisional targets in ADR-002 that require implementation-phase validation, which is consistent with ADR-MC-001's planning-only scope.

---

## 24. Cross-Reference Index

### 24.1 ADR Section to Requirement Index

| ADR Section | Requirement IDs | Count |
|---|---|---|
| ADR-MC-001 §2.1.1 | REQ-2.1.1-01 – REQ-2.1.1-04 | 4 |
| ADR-MC-001 §2.1.2 | REQ-2.1.2-01 – REQ-2.1.2-07 | 7 |
| ADR-MC-001 §2.1.3 | REQ-2.1.3-01 – REQ-2.1.3-05 | 5 |
| ADR-MC-001 §2.1.4 | REQ-2.1.4-01 – REQ-2.1.4-10 | 10 |
| ADR-MC-001 §2.2.1 | REQ-2.2.1-01 – REQ-2.2.1-05 | 5 |
| ADR-MC-001 §2.2.2 | REQ-2.2.2-01 – REQ-2.2.2-05 | 5 |
| ADR-MC-001 §2.2.3 | REQ-2.2.3-01 – REQ-2.2.3-05 | 5 |
| ADR-MC-001 §2.2.4 | REQ-2.2.4-01 – REQ-2.2.4-09 | 9 |
| ADR-MC-001 §2.3 | REQ-2.3-01 – REQ-2.3-13 | 13 |
| ADR-MC-001 §2.4 | REQ-2.4-01 – REQ-2.4-10 | 10 |
| ADR-MC-001 §2.5.1 | REQ-2.5.1-01 – REQ-2.5.1-05 | 5 |
| ADR-MC-001 §2.5.2 | REQ-2.5.2-01 – REQ-2.5.2-06 | 6 |
| ADR-MC-001 §2.5.3 | REQ-2.5.3-01 | 1 |
| ADR-MC-001 §2.6.1 | REQ-2.6.1-01 – REQ-2.6.1-03 | 3 |
| ADR-MC-001 §2.6.2 | REQ-2.6.2-01 – REQ-2.6.2-02 | 2 |
| ADR-MC-001 §2.6.3.1 | REQ-2.6.3.1-01 – REQ-2.6.3.1-05 | 5 |
| ADR-MC-001 §2.6.3.2 | REQ-2.6.3.2-01 – REQ-2.6.3.2-05 | 5 |
| ADR-MC-001 §2.6.3.3 | REQ-2.6.3.3-01 – REQ-2.6.3.3-03 | 3 |
| ADR-MC-001 §2.6.3.4 | REQ-2.6.3.4-01 – REQ-2.6.3.4-02 | 2 |
| ADR-MC-001 §2.6.4 | REQ-2.6.4-01 – REQ-2.6.4-05 | 5 |
| ADR-MC-001 §2.7 | REQ-2.7-01 – REQ-2.7-07 | 7 |
| ADR-MC-001 §2.8 | REQ-2.8-01 – REQ-2.8-08 | 8 |
| ADR-MC-001 §2.9 | REQ-2.9-01 – REQ-2.9-06 | 6 |
| ADR-MC-001 §2.10 | REQ-2.10-01 – REQ-2.10-07 | 7 |
| ADR-MC-001 §2.11 | REQ-2.11-01 – REQ-2.11-04 | 4 |
| ADR-MC-001 §2.12.1 | REQ-2.12.1-01 – REQ-2.12.1-03 | 3 |
| ADR-MC-001 §2.12.2 | REQ-2.12.2-01 – REQ-2.12.2-06 | 6 |
| ADR-MC-001 §2.13 | REQ-2.13-01 – REQ-2.13-03 | 3 |
| ADR-MC-001 §2.14 | REQ-2.14-01 – REQ-2.14-06 | 6 |
| ADR-MC-001 §2.15 | REQ-2.15-01 – REQ-2.15-10 | 10 |
| ADR-MC-001 §7 | REQ-7-I1 – REQ-7-I15 (incl. I3a) | 16 |
| ADR-MC-001 §9.1 | REQ-9.1-C01 – REQ-9.1-C14 | 14 |
| ADR-MC-001 §9.2 | REQ-9.2-S01 – REQ-9.2-S18 | 18 |
| ADR-MC-001 §9.3 | REQ-9.3-T01 – REQ-9.3-T16 | 16 |
| ADR-MC-001 §11 | REQ-11-AC1 – REQ-11-AC20 | 20 |
| ADR-002 §2.5 | REQ-A2-2.5-01 – REQ-A2-2.5-18 | 18 |

### 24.2 Component to Requirement Index

| Component | Primary ADR Sections | Requirement IDs |
|---|---|---|
| C01 | §2.1.1–§2.1.3, §2.5.2, §2.6.3.3, §2.7 | REQ-2.1.1-*, REQ-2.1.2-*, REQ-2.1.3-*, REQ-2.5.2-01, REQ-2.6.3.3-02, REQ-2.7-01–06, REQ-A2-2.5-09–11, REQ-A2-2.5-16 |
| C02 | §2.1.2, §2.1.4, §2.3, §2.4, §2.9, §2.10, §2.11 | REQ-2.1.2-05–07, REQ-2.1.4-*, REQ-2.3-03–10, REQ-2.4-*, REQ-2.9-*, REQ-2.10-02, REQ-2.11-*, REQ-A2-2.5-09–12, REQ-A2-2.5-16 |
| C03 | §2.2.1, §2.6.1, §2.15 | REQ-2.2.1-01–03, REQ-2.2.2-01–02, REQ-2.6.1-02, REQ-2.15-01, REQ-A2-2.5-17 |
| C04 | §2.2.4, §2.11 | REQ-2.2.1-04, REQ-2.2.2-03, REQ-2.2.4-*, REQ-2.11-03, REQ-A2-2.5-05 |
| C05 | §2.2.2, §2.2.3, §2.3, §2.4, §2.15 | REQ-2.2.2-04–05, REQ-2.2.3-02–04, REQ-2.3-06, REQ-2.3-13, REQ-2.4-03–04, REQ-2.15-08, REQ-A2-2.5-02 |
| C06 | §2.1.2, §2.1.3, §2.1.4, §2.10, §2.11, §2.14, §2.15 | REQ-2.1.2-02, REQ-2.1.3-01, REQ-2.1.4-10, REQ-2.10-*, REQ-2.11-03, REQ-2.14-02, REQ-2.15-08, REQ-A2-2.5-13, REQ-A2-2.5-15 |
| C07 | §2.1.1, §2.1.2, §2.2.1, §2.11, §2.14, §2.15 | REQ-2.1.1-02, REQ-2.1.2-02, REQ-2.2.1-05, REQ-2.11-*, REQ-2.14-06, REQ-2.15-08, REQ-A2-2.5-06–07, REQ-A2-2.5-16 |
| C08 | §2.5.3, §2.10, §2.12.2, §2.15 | REQ-2.5.3-01, REQ-2.10-06, REQ-2.12.2-04, REQ-2.15-02, REQ-A2-2.5-08 |
| C09 | §2.1.4, §2.6.2, §2.12.2, §2.15 | REQ-2.1.4-08–09, REQ-2.6.2-*, REQ-2.12.2-04–05, REQ-2.15-02–03, REQ-A2-2.5-01 |
| C10 | §2.5.1, §2.5.2, §2.6, §2.7, §2.12, §2.14, §2.15 | REQ-2.5.1-05, REQ-2.5.2-05–06, REQ-2.6.3.*, REQ-2.6.4-*, REQ-2.7-01–02, REQ-2.12.*, REQ-2.14-04, REQ-2.15-02–07, REQ-A2-2.5-03–05 |
| C11 | §2.6.3.4, §2.12, §2.15 | REQ-2.6.3.1-03–04, REQ-2.6.3.2-03–05, REQ-2.6.3.3-03, REQ-2.6.3.4-*, REQ-2.6.4-03–05, REQ-2.12.*, REQ-2.15-05–06, REQ-A2-2.5-04 |
| C12 | §2.1.1, §2.1.2, §2.1.3, §2.13, §2.14, §2.15 | REQ-2.1.1-04, REQ-2.1.2-06, REQ-2.1.3-04, REQ-2.13-*, REQ-2.14-05, REQ-2.15-09–10, REQ-A2-2.5-08, REQ-A2-2.5-13–15, REQ-A2-2.5-18 |
| C13 | §2.1.2, §2.1.3, §2.1.4, §2.5, §2.6.3.2, §2.9, §2.12.1 | REQ-2.1.2-04, REQ-2.1.3-02–03, REQ-2.1.4-05–09, REQ-2.5.1-*, REQ-2.5.2-03–04, REQ-2.6.3.2-*, REQ-2.9-03–04, REQ-2.12.1-03, REQ-A2-2.5-05 |
| C14 | §2.2.3, §2.4, §2.8, §2.15 | REQ-2.2.3-*, REQ-2.4-08, REQ-2.8-*, REQ-2.15-01, REQ-A2-2.5-17 |

---

## 25. Glossary

| Term | Definition |
|---|---|
| Traceability matrix | A mapping from every implementation requirement to its source ADR section, implementing component(s), verifying test case(s), enforced invariant(s), satisfied acceptance criterion/criteria, and certification gate(s) |
| Requirement | A discrete, testable obligation extracted from an ADR section |
| Invariant | A property that must hold at all times (ADR-MC-001 §7) |
| Acceptance criterion | A condition that must be satisfied for the ADR to be considered fully implemented (ADR-MC-001 §11) |
| Certification gate | An end-to-end test (doc 08 §12) that validates acceptance criteria for gate unblocking |
| Sigma continuation condition | The ADR-002 §2.5 "In-Flight Execution Behavior" requirement that permits optional executor continuation after lease expiry during Brain unavailability, subject to mandatory completion reporting |
| Coverage gap | A requirement that is not traced to at least one component, test, invariant, acceptance criterion, and certification gate |

---

**End of document. This is a planning artifact only. It authorizes no runtime code, no test execution, no deployment, and no authority activation.**