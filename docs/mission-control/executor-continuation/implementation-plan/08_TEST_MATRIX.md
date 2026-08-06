# 08 — Test Matrix: Executor Continuation

**Package:** Executor Continuation Implementation Planning
**Source ADR:** ADR-MC-001 (ACCEPTED, ratified 2026-08-05)
**Scope:** PLANNING ONLY — no runtime code, no deployment, no authority activation. This document defines the comprehensive test matrix for the executor continuation implementation. It enumerates every test case required to certify that the implementation satisfies ADR-MC-001, maps tests to ADR acceptance criteria (Section 11) and invariants (Section 7), and defines pass/fail criteria for each test.
**Codebase conventions:** Python 3.11+, pytest, SQLite (unit) and PostgreSQL (integration) backends, async test support. Existing markers: `integration`, `postgresql`, `slow`, `smoke`, `experimental`. New markers proposed: `resilience`, `chaos`, `security`, `certification`, `continuation`.

---

## 1. Document Purpose

This document is the test blueprint for implementing the executor continuation capability defined by ADR-MC-001. It is a planning artifact only — it authorizes no runtime code, no test execution, no deployment, and no authority activation. Implementation requires separate ADRs, branches, and authorizations per ADR-MC-001 Section 10.

The document serves three audiences:

1. **Implementers** — who need to know what tests to write, what each test verifies, and what pass/fail criteria must be met.
2. **Reviewers** — who need to verify that the test suite covers all 16 ADR-MC-001 Section 9.3 required tests, all 14 Section 9.1 components, all 15 Section 7 invariants, and all 20 Section 11 acceptance criteria.
3. **Certifiers** — who need a complete, traceable matrix from test cases to ADR acceptance criteria and invariants before recommending that `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE` be evaluated for unblocking.

---

## 2. Conventions

### 2.1 Test ID Scheme

| Prefix | Category | Source |
|---|---|---|
| `RT-##` | Required tests from ADR-MC-001 Section 9.3 | ADR §9.3 (16 tests) |
| `UT-C##-###` | Unit tests per component | ADR §9.1 (14 components) |
| `INT-###` | Integration tests for component interactions | Derived from ADR §2.1–§2.15 |
| `RES-###` | Resilience tests (crash, partition, clock drift) | Derived from ADR §2.8, §2.12, §2.15 |
| `CHS-###` | Chaos tests (random failures, Byzantine, split-brain) | Derived from ADR §2.2.4, §2.12 |
| `SEC-###` | Security tests (forgery, replay, cross-tenant, audit tampering) | Derived from ADR §6.3, §2.14 |
| `REC-###` | Replay and recovery tests | Derived from ADR §2.7, §2.15 |
| `MT-###` | Multi-tenant isolation tests | Derived from ADR §2.14 |
| `CERT-###` | Certification tests (gate unblocking prerequisites) | Derived from ADR §11, §13 |

### 2.2 Test Types

| Type | Definition | Backend | Marker |
|---|---|---|---|
| unit | Isolated test of a single component's logic; no external services, no cross-component calls; uses mocks/fakes | SQLite (in-memory) | none (default) |
| integration | Two or more components tested together with real interactions; may use PostgreSQL | PostgreSQL | `integration`, `postgresql` |
| resilience | Tests system behavior under infrastructure failure (crash, partition, clock drift); may use PostgreSQL + fault injection | PostgreSQL | `resilience`, `slow` |
| chaos | Tests system behavior under random or adversarial component failures; extended runtime, non-deterministic fault injection | PostgreSQL | `chaos`, `slow` |
| security | Tests that attack vectors are blocked; negative tests asserting rejection/failure | SQLite or PostgreSQL | `security` |
| certification | End-to-end tests that validate acceptance criteria for gate unblocking; run only after all other categories pass | PostgreSQL | `certification`, `slow` |

### 2.3 Component IDs

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

### 2.4 Invariant IDs

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

### 2.5 Acceptance Criteria IDs

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

---

## 3. Test Environment and Prerequisites

### 3.1 Test Backends

| Backend | Usage | Components |
|---|---|---|
| SQLite (in-memory) | Unit tests; fast iteration; no I/O latency | All unit tests (UT-*) |
| PostgreSQL (disposable) | Integration, resilience, chaos, certification tests; row-level security, async SQLAlchemy 2.0 | INT-*, RES-*, CHS-*, CERT-* |
| Mock/fake services | Simulated Brain, executor, downstream, witness nodes | SEC-*, CHS-*, RES-* |
| Fault injection harness | Process kill, network partition, clock skew simulation | RES-*, CHS-* |

### 3.2 Test Fixtures (planned, not implemented)

| Fixture | Purpose | Scope |
|---|---|---|
| `brain_context` | Mock Brain with lease, capability, heartbeat, revocation, policy services | All tests |
| `executor_context` | Mock executor with local state cache, journal, receipt service | All executor-side tests |
| `witness_set` | Set of N witness nodes with configurable fault behavior | C04, RT-04, CHS-* |
| `downstream_mock` | Mock downstream system with effect identity validation | C13, RT-08, INT-* |
| `time_anchor_source` | Mock signed time-anchor service with controllable clock | C14, RT-15, RES-* |
| `audit_ledger_spy` | Read-only spy on audit event pipeline | C12, RT-14, all |
| `fault_injector` | Controls process kill, network partition, clock skew | RES-*, CHS-* |
| `tenant_context` | Creates isolated tenant contexts with distinct policies | MT-*, SEC-* |

### 3.3 Configuration Settings Coverage

All 18 settings from ADR-MC-001 §9.2 must be exercised by at least one test. The coverage matrix in Section 15 maps settings to tests.

---

## 4. Required Tests (ADR-MC-001 Section 9.3)

The ADR enumerates 16 required tests in Section 9.3. Each is expanded below into specific test cases with full metadata.

### RT-01: Lease Lifecycle

**ADR ref:** §2.1.1–§2.1.3, §9.3
**Components tested:** C01, C14, C12
**Invariants verified:** I1, I2
**Acceptance criteria:** AC1
**Test type:** unit + integration

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| RT-01.1 | Lease acquisition issues signed token | Brain issues a lease with all required fields (`command_id`, `executor_id`, `tenant_id`, `issued_at`, `expires_at`, `lease_token`, `policy_snapshot_id`, `continuation_class`, `continuation_capability_id`); token is cryptographically signed; audit event emitted with causation link to dispatch event | Token signature verifies; all fields present and correctly typed; audit event recorded with causation link; lease status is `LEASE_ISSUED` | C01, C14, C12 |
| RT-01.2 | Lease renewal extends expiry and rotates token | Executor requests renewal before expiry; Brain grants renewal if command not cancelled, executor still holder, max duration not exceeded, policy not superseded, Brain available; new signed token issued; previous token revoked; new continuation capability issued; prior capability revoked | New `expires_at` > old; new token signature verifies; old token rejected by downstream; old capability ID rejected; supersession audit event recorded; capability rotation auditable (issuance, supersession, revocation) | C01, C02, C14, C12 |
| RT-01.3 | Lease expiry revokes all authority | When `expires_at` is reached, lease token immediately loses all authority; executor cannot use expired token to prove authority to downstream systems; expiry logged as immutable audit event | Expired token rejected by all validators; audit event recorded with expiry timestamp; no work or effects accepted after expiry | C01, C12 |
| RT-01.4 | Lease revocation by Brain | Brain explicitly revokes lease; token loses authority immediately; revocation published in revocation stream; audit event recorded | Revoked token rejected; revocation stream entry published with sequence number; audit event recorded | C01, C06, C12 |
| RT-01.5 | Renewal rejected when command cancelled | Executor requests renewal after command cancellation; Brain rejects renewal | Renewal rejected with `COMMAND_CANCELLED`; no new token issued; original token remains expired/revoked | C01, C06 |
| RT-01.6 | Renewal rejected when executor not lease holder | A different executor requests renewal for the same command; Brain rejects | Renewal rejected with `NOT_LEASE_HOLDER`; original lease unaffected | C01 |
| RT-01.7 | Renewal rejected when max execution duration exceeded | Executor requests renewal after exceeding max execution duration; Brain rejects | Renewal rejected with `MAX_DURATION_EXCEEDED`; no new token issued | C01 |
| RT-01.8 | Renewal rejected when policy snapshot superseded | Policy snapshot has been superseded; executor requests renewal; Brain rejects | Renewal rejected with `POLICY_SUPERSEDED`; no new token issued | C01, C07 |
| RT-01.9 | Renewal rejected when Brain unavailable | Executor requests renewal during Brain outage; renewal rejected with `BRAIN_UNAVAILABLE` | Renewal rejected with `BRAIN_UNAVAILABLE`; rejection counted toward `lease_rejection_threshold` outage signal | C01, C03 |
| RT-01.10 | Capability supersession survives later not_valid_after | Prior capability has later `not_valid_after` than new capability; downstream systems must still reject the prior capability ID after renewal | Prior capability ID rejected by downstream even though its `not_valid_after` is later; only latest-lease capability accepted | C01, C02, C13 |

### RT-02: Capability Issuance and Validation

**ADR ref:** §2.1.4, §9.3
**Components tested:** C02, C14, C07, C12
**Invariants verified:** I3, I3a, I4
**Acceptance criteria:** AC2
**Test type:** unit + integration

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| RT-02.1 | Capability issued at dispatch with all fields | Brain issues continuation capability at dispatch time with all 15 fields populated; capability is cryptographically signed; audit event recorded | All 15 fields present and valid; signature verifies; `not_valid_before` >= lease `expires_at`; audit event recorded | C02, C14, C07, C12 |
| RT-02.2 | Capability unusable before lease expiry | Executor attempts to use capability while lease is still active; capability `not_valid_before` not yet reached; all validators reject | Capability rejected with `CAPABILITY_NOT_YET_VALID`; no effects produced; no continuation started | C02, C13 |
| RT-02.3 | Capability unusable after its own expiry | Current time exceeds `not_valid_after`; executor attempts to use capability; all validators reject | Capability rejected with `CAPABILITY_EXPIRED`; no effects produced; executor enters safe-hold | C02, C14, C13 |
| RT-02.4 | Capability scope: command binding | Capability used for a different `command_id` than the one it was issued for; validators reject | Capability rejected with `CAPABILITY_COMMAND_MISMATCH` | C02, C13 |
| RT-02.5 | Capability scope: executor binding | Capability used by a different `executor_id` than the one it was issued for; validators reject | Capability rejected with `CAPABILITY_EXECUTOR_MISMATCH` | C02, C13 |
| RT-02.6 | Capability scope: tenant binding | Capability used in a different tenant context than the one it was issued for; validators reject | Capability rejected with `CAPABILITY_TENANT_MISMATCH`; security event logged | C02, C13, C12 |
| RT-02.7 | Capability revocation through revocation stream | Brain revokes capability via signed revocation stream entry; executor that has not observed the required watermark must not continue; executor that observes revocation during outage must stop immediately | Capability rejected after revocation; continuation forbidden if watermark below required; executor stops on revocation receipt during outage | C02, C06 |
| RT-02.8 | Capability not issued when Brain does not allow continuation | Brain determines continuation is not allowed for a command; no capability issued; `continuation_capability_id` is null in lease | No capability token exists; `continuation_capability_id` is null; executor cannot continue after expiry | C01, C02 |
| RT-02.9 | Capability `policy_snapshot_not_valid_after` enforced | Current time exceeds `policy_snapshot_not_valid_after`; executor must not continue; defaults to capability `not_valid_after` if absent | Continuation forbidden; executor enters safe-hold; audit event recorded | C02, C07, C14 |
| RT-02.10 | Capability `revocation_watermark_required` enforced | Executor's observed watermark is below `revocation_watermark_required` in the capability; continuation forbidden | Continuation forbidden with `WATERMARK_BELOW_REQUIRED`; executor enters safe-hold | C02, C06 |

### RT-03: Brain Outage Declaration

**ADR ref:** §2.2.1–§2.2.3, §9.3
**Components tested:** C03, C04, C14, C05
**Invariants verified:** I4, I14
**Acceptance criteria:** AC3
**Test type:** unit + integration

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| RT-03.1 | Two-signal rule: heartbeat + lease rejection | Heartbeat missing for `brain_heartbeat_miss_threshold` consecutive intervals AND lease renewal rejected as `BRAIN_UNAVAILABLE` for `lease_rejection_threshold` attempts; outage declared after grace period | Outage declared; outage record persisted with both signals, timestamps, lease token fingerprint, signed time anchor; grace period elapsed before declaration | C03, C01, C14, C05 |
| RT-03.2 | Two-signal rule: heartbeat + status query failure | Heartbeat missing AND command status query failed with timeout/`UNAVAILABLE` for `status_query_threshold` attempts; outage declared | Outage declared with both signals recorded; grace period respected | C03, C14, C05 |
| RT-03.3 | Two-signal rule: lease rejection + policy silence | Lease renewal rejected AND no policy broadcast for `policy_silence_threshold`; outage declared | Outage declared; both signals recorded | C01, C07, C14 |
| RT-03.4 | One signal insufficient: heartbeat only | Only heartbeat missing; no other signal crosses threshold; outage must NOT be declared | No outage declared; executor remains in waiting state | C03 |
| RT-03.5 | One signal insufficient: witnesses only | Only witness quorum reports unavailability; no direct-Brain signal; outage must NOT be declared | No outage declared; witness statements recorded but not sufficient | C04 |
| RT-03.6 | Direct-Brain signal required | Two non-direct signals cross thresholds (e.g., witness + policy silence); outage must NOT be declared because no direct-Brain signal | No outage declared; error logged | C03, C04, C07 |
| RT-03.7 | Grace period enforced | Two signals cross thresholds but grace period has not elapsed; outage must NOT be declared yet | No outage until `brain_outage_grace_period` elapses; outage declared immediately after | C14, C05 |
| RT-03.8 | Outage record persisted with all required fields | After outage declaration, local record contains: timestamp, signals observed, lease token fingerprint, signed time anchor, `monotonic_outage_start`, `wall_outage_declared_at`, `grace_period_end` | All fields present and correctly typed; record is durable across process restart | C05, C14 |
| RT-03.9 | Clock rollback rejected during detection | Time value rolls backward more than `max_clock_rollback_tolerance` relative to last signed anchor; executor rejects the time value | Time value rejected; rollback logged as security event; no outage declared using rolled-back time | C14, C05 |
| RT-03.10 | Policy broadcast silence signal | No policy broadcast received for `policy_silence_threshold`; signal crosses threshold; combined with a direct-Brain signal, outage declared | Policy silence signal recorded; outage declared when combined with direct signal | C07, C03 |

### RT-04: Witness Statement Validation

**ADR ref:** §2.2.4, §9.3
**Components tested:** C04, C14, C12
**Invariants verified:** I4, I14
**Acceptance criteria:** AC4
**Test type:** unit + integration

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| RT-04.1 | Witness identity: control-plane only | Witness statement from an executor participating in the command; rejected | Statement rejected with `WITNESS_NOT_INDEPENDENT`; self-exclusion enforced | C04 |
| RT-04.2 | Witness quorum: N >= 3f+1, quorum >= 2f+1 (BFT) | N=4 witnesses, f=1 faulty; quorum=3; 3 valid statements from distinct witnesses; outage signal accepted | Quorum satisfied; witness signal crosses threshold | C04 |
| RT-04.3 | Witness quorum: CFT model N >= 2f+1 | N=3 witnesses, f=1 faulty; quorum=2; 2 valid statements; outage signal accepted; model documented as CFT | Quorum satisfied; CFT model explicitly documented | C04 |
| RT-04.4 | Witness quorum: insufficient | N=4, quorum=3, only 2 valid statements; witness signal does NOT cross threshold | Signal not counted; outage not declared on witness signal alone | C04 |
| RT-04.5 | Witness statement: replay resistance | Stale witness statement with old nonce replayed; rejected | Statement rejected with `WITNESS_STATEMENT_STALE`; nonce monotonicity enforced | C04, C14 |
| RT-04.6 | Witness statement: max age | Witness statement older than `witness_statement_max_age`; ignored | Statement ignored; not counted toward quorum | C04, C14 |
| RT-04.7 | Witness statement: tenant partitioning | Witness for tenant A issues statement about tenant B's Brain partition; rejected | Statement rejected with `WITNESS_TENANT_MISMATCH` | C04 |
| RT-04.8 | Witness statement: signed with identity key | Unsigned witness statement; rejected. Statement with invalid signature; rejected | Both rejected with `WITNESS_SIGNATURE_INVALID` | C04 |
| RT-04.9 | Compromised witness key revocation | Witness key revoked; subsequent statements from that witness invalid; threshold of valid witnesses must still be met | Revoked witness statements rejected; quorum recalculated excluding revoked witness | C04, C06 |
| RT-04.10 | Self-exclusion: executor cannot count peers | Executor attempts to count its peers or controlled processes toward witness quorum; rejected | Peer/controlled-process statements rejected; only independent control-plane witnesses counted | C04 |
| RT-04.11 | Network partition: executor isolated from Brain but not witnesses | Executor can reach witnesses but not Brain; witness quorum achieved; but no direct-Brain signal; outage must NOT be declared | No outage declared; direct-Brain signal requirement holds even under partition | C03, C04 |
| RT-04.12 | Witness statement fields | Each statement includes `tenant_id`, `brain_region`, `witness_id`, `statement_id`, timestamp, nonce, signature | All fields present; missing field causes rejection | C04, C14 |

### RT-05: Continuation Eligibility

**ADR ref:** §2.3, §9.3
**Components tested:** C01, C02, C03, C04, C05, C06, C07, C14
**Invariants verified:** I1, I2, I3, I3a, I4, I5, I9, I12, I13, I14, I15
**Acceptance criteria:** AC5
**Test type:** unit + integration

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| RT-05.1 | All criteria met: continuation permitted | All 11 eligibility criteria satisfied; executor may continue (optional) | Continuation permitted; eligibility decision event recorded in audit | C01–C07, C14 |
| RT-05.2 | Lease not expired: continuation forbidden | Lease `expires_at` not reached; continuation forbidden | Continuation forbidden with `LEASE_NOT_EXPIRED` | C01, C02 |
| RT-05.3 | No outage declared: continuation forbidden | No Brain outage declared; continuation forbidden even if capability valid | Continuation forbidden with `NO_OUTAGE_DECLARED` | C03, C04 |
| RT-05.4 | Capability invalid: continuation forbidden | Capability expired, revoked, or scope mismatch; continuation forbidden | Continuation forbidden with `CAPABILITY_INVALID` | C02 |
| RT-05.5 | Revocation watermark below required: continuation forbidden | Watermark < `revocation_watermark_required`; continuation forbidden | Continuation forbidden with `WATERMARK_BELOW_REQUIRED` | C02, C06 |
| RT-05.6 | Cancellation observed: continuation forbidden | Cancellation command in cached ledger events at or before watermark; continuation forbidden | Continuation forbidden with `CANCELLATION_OBSERVED` | C06 |
| RT-05.7 | Local state insufficient: continuation forbidden | Self-check against task manifest fails; required inputs or deterministic path unavailable; continuation forbidden | Continuation forbidden with `LOCAL_STATE_INSUFFICIENT` | C05 |
| RT-05.8 | Side-effect class not permitted: continuation forbidden | Command's `continuation_class` or capability `permitted_operation_ids` does not permit the operation; continuation forbidden | Continuation forbidden with `CLASS_NOT_PERMITTED` | C02 |
| RT-05.9 | Policy snapshot not pinned: continuation forbidden | Capability missing `policy_snapshot_hash` or hash mismatch; continuation forbidden | Continuation forbidden with `POLICY_SNAPSHOT_MISMATCH` | C02, C07 |
| RT-05.10 | Bounded continuation exceeded: continuation forbidden | Estimated completion exceeds `max_continuation_duration` or `max_continuation_operations`; continuation forbidden | Continuation forbidden with `BOUNDS_EXCEEDED` | C02 |
| RT-05.11 | Tenant mismatch: continuation forbidden | Executor tenant != command tenant; continuation forbidden; security event | Continuation forbidden with `TENANT_MISMATCH`; security event logged | C02, C12 |
| RT-05.12 | Audit capability missing: continuation forbidden | Executor cannot emit continuation audit events or receipts; continuation forbidden | Continuation forbidden with `AUDIT_CAPABILITY_MISSING` | C08, C09, C12 |
| RT-05.13 | Time bounds not satisfied: continuation forbidden | Current signed wall-clock time outside capability validity window; continuation forbidden | Continuation forbidden with `TIME_BOUNDS_NOT_SATISFIED` | C02, C14 |
| RT-05.14 | Default is STOP | No eligibility check performed; default decision is STOP | Executor stops; no continuation attempted | C05 |

### RT-06: Continuation Bounds

**ADR ref:** §2.4, §9.3
**Components tested:** C02, C05, C08
**Invariants verified:** I5
**Acceptance criteria:** AC6
**Test type:** unit + integration

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| RT-06.1 | Max continuation duration enforced | Continuation exceeds `max_continuation_duration` (default 5 min); executor must stop | Continuation stops at duration bound; audit event recorded; safe-hold entered | C02, C08, C14 |
| RT-06.2 | Max continuation operations enforced | Continuation exceeds `max_continuation_operations` (default 1); executor must stop | Continuation stops after operation count bound; no further operations performed | C02, C08 |
| RT-06.3 | Max continuation attempts per command | Second continuation attempt for same command/lease; rejected | Second attempt rejected with `MAX_ATTEMPTS_EXCEEDED` | C02, C05 |
| RT-06.4 | Max concurrent continuations per executor | Executor attempts to exceed `max_concurrent_continuations_per_executor` (default 3); rejected | Excess continuation rejected with `MAX_CONCURRENT_EXCEEDED` | C02, C05 |
| RT-06.5 | Side-effect cooldown after continuation | After continuation, executor attempts additional external effects before Brain reconciliation; rejected | Effects rejected with `COOLDOWN_ACTIVE`; cooldown persists until reconciliation | C02, C13 |
| RT-06.6 | Tenant max continuation rate | Tenant exceeds `tenant_max_continuation_rate` (default 10/min); circuit breaker trips | Rate limit enforced; continuations rejected with `TENANT_RATE_LIMIT_EXCEEDED` | C02 |
| RT-06.7 | Capability max validity | Capability lifetime exceeds `continuation_capability_max_validity` (default 24h); capability expired | Capability rejected with `CAPABILITY_MAX_VALIDITY_EXCEEDED` | C02, C14 |
| RT-06.8 | Duration measured by monotonic clock | `max_continuation_duration` measured with monotonic clock; executor attempts to extend via wall-clock rollback; extension prevented | Monotonic clock used; wall-clock rollback does not extend duration; continuation stops at monotonic bound | C02, C14 |
| RT-06.9 | Platform maximums enforced | Tenant attempts to configure limits beyond platform maximums; configuration rejected | Configuration rejected with `PLATFORM_MAX_EXCEEDED`; platform maximums not bypassed | C02 |
| RT-06.10 | Break-glass reduces but never increases | Platform break-glass policy reduces limits; attempt to increase beyond platform max rejected | Reduced limits accepted; increased limits rejected | C02 |

### RT-07: Revocation Watermark

**ADR ref:** §2.10, §9.3
**Components tested:** C06, C02, C05
**Invariants verified:** I13
**Acceptance criteria:** AC17
**Test type:** unit + integration

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| RT-07.1 | Watermark meets requirement | Executor watermark >= `revocation_watermark_required`; continuation permitted (for this criterion) | Watermark check passes | C06, C02 |
| RT-07.2 | Watermark below requirement | Executor watermark < `revocation_watermark_required`; continuation forbidden (fail-closed) | Continuation forbidden with `WATERMARK_BELOW_REQUIRED` | C06, C02 |
| RT-07.3 | Watermark missing | No revocation watermark recorded; continuation forbidden (fail-closed) | Continuation forbidden with `WATERMARK_MISSING` | C06 |
| RT-07.4 | Revocation cache stale | Local revocation cache older than `max_revocation_cache_age` (default 5s) at lease expiry; continuation forbidden | Continuation forbidden with `REVOCATION_CACHE_STALE` | C06, C14 |
| RT-07.5 | Revocation received during outage | Executor receives revocation entry during outage; must stop immediately | Continuation stops; revocation applied; audit event recorded | C06, C08 |
| RT-07.6 | Cancellation in cache at watermark | Cancellation command observed at or before watermark; continuation forbidden | Continuation forbidden with `CANCELLATION_OBSERVED` | C06 |
| RT-07.7 | High-risk command defaults to STOP | High-risk, legal, financial, destructive, or irreversible command; continuation forbidden without fresh revocation knowledge | Continuation forbidden with `HIGH_RISK_STOP` | C06, C02 |
| RT-07.8 | Revocation stream monotonicity | Revocation stream entries have monotonically increasing sequence numbers; out-of-order entry rejected | Out-of-order entry rejected; sequence monotonicity enforced | C06 |
| RT-07.9 | Revocation stream tenant partitioning | Revocation entry for tenant A visible to tenant B executor; rejected/not delivered | Cross-tenant revocation entry not visible; tenant partition enforced | C06 |
| RT-07.10 | Emergency deny channel | Critical policy deny/revocation travels through survivable channel (signed revocation stream or witness broadcast); executor receives and stops | Emergency deny received; continuation stopped; deny recorded in audit | C06, C04, C07 |

### RT-08: Idempotency Across Continuation/Replay

**ADR ref:** §2.5, §9.3
**Components tested:** C08, C13, C10
**Invariants verified:** I10
**Acceptance criteria:** AC7
**Test type:** unit + integration

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| RT-08.1 | Stable effect identity format | Effect identity is `(command_id, operation_id, side_effect_slot)`; stable across normal execution, continuation, replay, and multiple executors | Identity key matches expected format; stable across all execution modes | C13 |
| RT-08.2 | Duplicate suppression: executor operation layer | Executor attempts operation with same `(command_id, operation_id, side_effect_slot)` as already-performed operation; skipped | Operation skipped; no duplicate effect produced; journal records skip | C08, C13 |
| RT-08.3 | Duplicate suppression: downstream system | Downstream receives two effects with same identity from different executors; second rejected | Second effect rejected with `DUPLICATE_EFFECT`; first effect applied | C13 |
| RT-08.4 | Duplicate suppression: Brain dispatch | Brain receives duplicate dispatch for active lease; rejected | Duplicate dispatch rejected with `DUPLICATE_DISPATCH` | C01 |
| RT-08.5 | Duplicate suppression: continuation capability | Duplicate or reused continuation capability; rejected | Reused capability rejected with `CAPABILITY_ALREADY_USED` | C02 |
| RT-08.6 | Duplicate suppression: Brain reconciliation | Duplicate continuation report for same `(command_id, continuation_id)`; rejected | Duplicate report rejected with `DUPLICATE_REPORT` | C10 |
| RT-08.7 | Replay identity: root_command_id | Replay creates new command record; effect identity uses `root_command_id`, not replay command ID | Effect identity uses `root_command_id`; replay command ID not in effect identity | C13, C10 |
| RT-08.8 | Continuation journal records effect identity | Journal entry includes stable external-effect identity for every operation | All journal entries contain `(command_id, operation_id, side_effect_slot)` | C08 |
| RT-08.9 | Execution metadata not in effect identity | `continuation_id`, `executor_id`, `lease_token`, replay attempt number are metadata only; not part of effect identity | Metadata fields not in effect identity key; downstream ignores them for dedup | C13 |
| RT-08.10 | Replay authorization dedup | Replay authorized only after reconciliation; unreconciled effects block replay | Replay blocked with `RECONCILIATION_REQUIRED` until effects reconciled | C10, C13 |

### RT-09: Completion Receipt

**ADR ref:** §2.6.2, §2.13, §9.3
**Components tested:** C09, C12, C14
**Invariants verified:** I6
**Acceptance criteria:** AC10
**Test type:** unit + integration

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| RT-09.1 | Receipt generated for every continuation | Every continuation attempt produces a signed receipt; no silent continuation | Receipt exists for every continuation; receipt signature verifies | C09, C14 |
| RT-09.2 | Receipt contains all required fields | Receipt contains: `command_id`, `executor_id`, `continuation_id`, `capability_id`, `lease_token_fingerprint`, `continuation_started_at`, `continuation_ended_at`, `final_state`, `operations_performed`, `result_digest`, `evidence_refs`, `continuation_journal`, `audit_receipt_id`, `outage_evidence`, `revocation_watermark_observed` | All 14 fields present and correctly typed | C09 |
| RT-09.3 | Receipt signature verification | Receipt signed by executor; Brain verifies signature; tampered receipt rejected | Valid signature accepted; tampered receipt rejected with `RECEIPT_SIGNATURE_INVALID` | C09, C14 |
| RT-09.4 | Receipt immutability | Receipt modified after creation; Brain detects modification; rejected | Modified receipt rejected with `RECEIPT_MODIFIED`; hash mismatch detected | C09, C12 |
| RT-09.5 | Outage evidence bundle bound to capability | Outage evidence bundle contains: outage declaration record, witness statements, signal thresholds, signed time anchor; bound to `capability_id` and `command_id` | All bundle components present; binding verified; mismatched capability_id rejected | C09, C04, C14 |
| RT-09.6 | Outage evidence required for downstream | Downstream receives continuation effect without outage evidence; rejected | Effect rejected with `OUTAGE_EVIDENCE_MISSING` | C09, C13 |
| RT-09.7 | Outage evidence mismatch | Outage evidence `capability_id` does not match effect's capability; rejected | Effect rejected with `OUTAGE_EVIDENCE_MISMATCH` | C09, C13 |
| RT-09.8 | Receipt for failed continuation | Continuation fails; receipt still generated with `final_state = FAILED`; reporting mandatory regardless of outcome | Receipt exists with `FAILED` state; all fields populated | C09 |
| RT-09.9 | Receipt for aborted continuation | Continuation aborted (e.g., recovery detected mid-operation); receipt generated with `final_state = ABORTED` | Receipt exists with `ABORTED` state | C09 |
| RT-09.10 | Receipt for timeout continuation | Continuation times out at `max_continuation_duration`; receipt generated with `final_state = TIMEOUT` | Receipt exists with `TIMEOUT` state | C09, C02 |

### RT-10: Reconciliation

**ADR ref:** §2.6, §2.6.3, §9.3
**Components tested:** C10, C11, C13, C09, C12
**Invariants verified:** I7, I8, I10
**Acceptance criteria:** AC9
**Test type:** integration

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| RT-10.1 | Single valid continuation: VALID_CONTINUATION | One valid continuation report; no conflict; effects applied by stable identity | Classification: `VALID_CONTINUATION`; effects applied; command state `SUCCEEDED` | C10, C13 |
| RT-10.2 | Multiple continuations, same result: DUPLICATE_AGREED | Two executors continue same command; results agree; effects idempotent; first by trusted comparable signed time wins; other marked `DUPLICATE_AGREED` | First completed by signed time selected; other marked `DUPLICATE_AGREED`; effects deduplicated | C10, C14 |
| RT-10.3 | Multiple continuations, same result, tie-breaker | Two executors with same signed time; deterministic tie-breaker: lowest `executor_id` wins | Lowest `executor_id` selected; other marked `DUPLICATE_AGREED` | C10 |
| RT-10.4 | Multiple continuations, divergent results: MANUAL_REVIEW | Two executors continue same command; results diverge; no automatic selection; manual review | Classification: `CONFLICTING_REPORTS`; effects frozen; command state `MANUAL_REVIEW_REQUIRED` | C10, C11 |
| RT-10.5 | Invalid continuation discarded | Continuation report fails eligibility validation; result discarded; executor flagged | Classification: `INVALID_CONTINUATION`; result discarded; executor flagged | C10, C11 |
| RT-10.6 | Effect reconciliation: duplicate identity | Effect identity matches already-applied effect; marked duplicate; not re-applied | Effect marked `DUPLICATE`; no re-application | C10, C13 |
| RT-10.7 | Effect reconciliation: new identity, valid result | New effect identity; selected result is authoritative; effect applied | Effect applied; audit event recorded | C10, C13 |
| RT-10.8 | Effect reconciliation: identity conflict | Effect identity conflicts with another effect; freeze affected resource; manual review | Resource frozen; manual review queued | C10, C11, C13 |
| RT-10.9 | Effect reconciliation: non-reversible, multiple executors | Non-reversible effect attempted by multiple executors; freeze; manual review; no automatic application | Effects frozen; manual review; no auto-apply | C10, C11, C13 |
| RT-10.10 | Compensation: reversible effect | Effect is reversible; Brain authorizes compensation; compensation is itself a command with lease, idempotency key, audit chain | Compensation command issued; original effect reversed; compensation audited | C10, C01, C13 |
| RT-10.11 | Compensation: irreversible effect | Effect is irreversible; no automatic compensation; manual review | No auto-compensation; manual review queued | C10, C11 |
| RT-10.12 | Class 3 effect: freeze and manual review | High-risk/irreversible (Class 3) effect involved; freeze and manual review regardless of result selection | Effects frozen; manual review; classification `MANUAL_REVIEW_REQUIRED` | C10, C11, C13 |
| RT-10.13 | Result selection by timestamp only when idempotent | Timestamp-based selection used only when all effects provably idempotent and equivalent; non-idempotent effects do not use timestamp selection | Timestamp selection used for idempotent effects; not used for non-idempotent | C10, C13 |
| RT-10.14 | Reconciliation classification: VALID_BUT_RECONCILED | All criteria met but effects required reconciliation or compensation; classified `VALID_BUT_RECONCILED` | Classification correct; effects reconciled | C10, C13 |
| RT-10.15 | Completion report deadline enforced | Executor does not report within `completion_report_deadline` of recovery; flagged | Late/missing report flagged; audit event recorded | C10, C09 |

### RT-11: Split-Brain Conflict

**ADR ref:** §2.12, §9.3
**Components tested:** C10, C11, C13, C09, C12
**Invariants verified:** I8, I10
**Acceptance criteria:** AC11
**Test type:** integration + chaos

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| RT-11.1 | Multiple continuation reports detected | Two reports for same `command_id` with different `continuation_id` values; conflict detected | Conflict detected; both reports retained; audit event recorded | C10, C12 |
| RT-11.2 | Reports arrive while Brain considers command active | Continuation reports arrive while Brain considers command still active; detected as split-brain | Split-brain detected; command state transitioned to `RECONCILING` | C10 |
| RT-11.3 | Divergent result_digest values | Two reports with different `result_digest`; conflict; freeze; manual review | Effects frozen; `MANUAL_REVIEW_REQUIRED`; no silent resolution | C10, C11, C13 |
| RT-11.4 | Conflicting effect identity claims | Two reports with conflicting `(command_id, operation_id, side_effect_slot)` claims; freeze; manual review | Effects frozen; manual review; no silent resolution | C10, C11, C13 |
| RT-11.5 | Results agree, effects idempotent: deduplicate | Two executors continued; results agree; effects idempotent; first by signed time wins; others `DUPLICATE_AGREED`; effects deduplicated | First selected; others `DUPLICATE_AGREED`; effects deduplicated; state `SUCCEEDED` | C10, C13, C14 |
| RT-11.6 | Results agree, effects non-reversible: freeze | Two executors continued; results agree; effects non-reversible; first by signed time wins; others `DUPLICATE_AGREED`; effects frozen; manual review | First selected; effects frozen; `MANUAL_REVIEW_REQUIRED` | C10, C11, C13 |
| RT-11.7 | Brain recovers during continuation: atomicity rule | Brain recovers while continuation active; in-progress operations: committed/irreversible finished and reported; uncommitted aborted; never both finish and abort same operation | Committed ops finished and reported; uncommitted ops aborted; no double-action; state `RECONCILING` | C10, C08, C09 |
| RT-11.8 | Brain never recovers within capability window | Capability `not_valid_after` reached; executor stops; partial results recorded; manual recovery | Executor stops at `not_valid_after`; partial results recorded; `MANUAL_REVIEW_REQUIRED` | C02, C09, C10 |
| RT-11.9 | No silent conflict resolution | All conflicts recorded and surfaced; no silent resolution path | All conflicts in audit; all conflicts in review queue; no silent auto-resolve | C10, C11, C12 |

### RT-12: Cross-Tenant Isolation

**ADR ref:** §2.14, §9.3
**Components tested:** C02, C06, C04, C10, C12
**Invariants verified:** I9
**Acceptance criteria:** AC13
**Test type:** unit + integration + security

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| RT-12.1 | Executor continues only within own tenant | Executor for tenant A attempts to continue command for tenant B; rejected | Rejected with `TENANT_MISMATCH`; security event logged | C02, C12 |
| RT-12.2 | Tenant-scoped continuation capabilities | Capability for tenant A used in tenant B context; rejected | Rejected with `CAPABILITY_TENANT_MISMATCH` | C02 |
| RT-12.3 | Tenant-scoped revocation streams | Revocation stream for tenant A visible to tenant B executor; not delivered | Cross-tenant revocation not visible; partition enforced | C06 |
| RT-12.4 | Tenant-scoped witness statements | Witness for tenant A issues statement about tenant B; rejected | Rejected with `WITNESS_TENANT_MISMATCH` | C04 |
| RT-12.5 | Per-tenant continuation limits | Tenant A has `max_continuation_duration = 5m`; tenant B has `max_continuation_duration = 2m`; limits enforced independently | Each tenant's limits enforced separately; no cross-tenant influence | C02 |
| RT-12.6 | Per-tenant rate limits | Tenant A exceeds rate limit; tenant B unaffected | Tenant A rate-limited; tenant B continuations proceed normally | C02 |
| RT-12.7 | Continuation reports routed to correct partition | Report from tenant A executor routed to tenant A Brain partition; not to tenant B | Report routed to correct partition; cross-tenant routing rejected | C10 |
| RT-12.8 | Tenant policy disables continuation | Tenant policy sets `continuation_class = STOP`; no continuations permitted for that tenant | All continuation attempts rejected with `TENANT_POLICY_STOP` | C02, C07 |
| RT-12.9 | Cross-tenant continuation is security event | Any cross-tenant continuation attempt logged as security event | Security event logged with full context; alert raised | C12 |

### RT-13: Recovery Protocol

**ADR ref:** §2.15, §2.6.1, §9.3
**Components tested:** C03, C10, C11, C06, C07, C12, C09
**Invariants verified:** I7, I8
**Acceptance criteria:** AC14
**Test type:** integration

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| RT-13.1 | Recovery detection: confirmation period | Brain available and responsive for `brain_recovery_confirmation_period` (default 10s); recovery declared | Recovery declared after confirmation period; recovery time-anchored and signed | C03, C14 |
| RT-13.2 | Recovery notification via heartbeat | Executors notified of recovery through heartbeat channel | Executors receive recovery notification; notification signed | C03 |
| RT-13.3 | In-progress operation atomicity: committed ops finished | Operation has already committed or is irreversible; finished and reported | Committed ops finished; results reported; audit recorded | C10, C08, C09 |
| RT-13.4 | In-progress operation atomicity: uncommitted ops aborted | Operation has not yet committed; aborted | Uncommitted ops aborted; no effect produced; audit recorded | C10, C08 |
| RT-13.5 | No double-action: never both finish and abort | Same operation never both finished and aborted | No operation has both finish and abort actions | C10, C08 |
| RT-13.6 | Report collection within deadline | All executors that continued submit reports within `completion_report_deadline` | All reports received within deadline; late reports flagged | C09, C10 |
| RT-13.7 | Reconciliation after recovery | Brain performs result selection, effect reconciliation, compensation, manual-review routing | All four reconciliation concerns addressed in order | C10, C11, C13 |
| RT-13.8 | Conflict freeze after recovery | Conflicting results freeze downstream effects until resolved | Effects frozen; manual review queued | C10, C11, C13 |
| RT-13.9 | Manual review queue populated | Conflicts, invalid continuations, non-reversible effects enqueued for operator review | Queue entries created with full evidence, receipts, journals | C11 |
| RT-13.10 | Replay authorization after reconciliation | Valid commands that did not complete receive Brain-authorized replay only after reconciliation | Replay authorized only post-reconciliation; pre-reconciliation replay rejected | C10, C01 |
| RT-13.11 | Policy refresh after recovery | All executors refresh policy snapshots and revocation watermarks before accepting new work | Executors refresh; no new work accepted until refresh complete | C07, C06 |
| RT-13.12 | Audit completion after recovery | All continuation events finalized in immutable audit ledger | All events in ledger; ledger complete; no gaps | C12 |
| RT-13.13 | Gate evaluation only after certification | `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE` evaluated only after implementation certified | Gate remains BLOCKED until all certification tests pass | C12 |

### RT-14: Audit Ledger Completeness

**ADR ref:** §2.13, §9.3
**Components tested:** C12
**Invariants verified:** I11
**Acceptance criteria:** AC12
**Test type:** unit + integration

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| RT-14.1 | All continuation events in audit chain | Audit chain includes: lease expiry, capability issuance, outage declaration, eligibility decision, each operation, completion event + receipt, recovery detection, reconciliation, terminal state | All 9 event types present in ledger; no missing events | C12 |
| RT-14.2 | Authoritative storage never truncated | Immutable audit ledger stores every event; no truncation of authoritative storage | Ledger entries count == events produced; no entries removed | C12 |
| RT-14.3 | Projection truncation allowed with metadata | Read-only projection APIs (e.g., Mission Control causation chain) may paginate/cap at `MAX_CAUSATION_LINKS` with truncation metadata | Projection caps with metadata; authoritative ledger unaffected | C12 |
| RT-14.4 | Causation chain hash-linked | Each event hash-linked to previous; chain integrity verifiable | Hash chain verifies; tampering detected | C12 |
| RT-14.5 | Audit events immutable | Audit event modified after append; detected; rejected | Modification detected; hash mismatch; event rejected | C12 |
| RT-14.6 | Audit events span all components | Events from C01, C02, C03, C04, C06, C07, C08, C09, C10, C11, C13, C14 all appear in ledger | Events from all components present | C12, all |
| RT-14.7 | Capability rotation audit chain | Issuance, supersession, and revocation of each capability recorded as immutable audit events | All three event types present for each capability rotation | C02, C12 |
| RT-14.8 | Lease expiry audit event | Lease expiry logged as immutable audit event | Expiry event present with timestamp and lease token fingerprint | C01, C12 |

### RT-15: Time Authority

**ADR ref:** §2.8, §9.3
**Components tested:** C14, C01, C02, C06
**Invariants verified:** I14
**Acceptance criteria:** AC15
**Test type:** unit + integration + resilience

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| RT-15.1 | Signed time anchors at dispatch, renewal, recovery | Brain issues signed time anchors at dispatch, renewal, and recovery; anchors verified by executor | Anchors present at all three points; signatures verify | C14, C01, C02, C03 |
| RT-15.2 | Lease expiry derived from anchor + monotonic elapsed | Latest pre-outage signed anchor establishes wall-clock reference; executor derives lease expiry locally from anchor + monotonic elapsed time; no fresh signature at expiry required | Expiry derived correctly; no fresh signature needed; monotonic clock advances elapsed time | C14, C01, C05 |
| RT-15.3 | Clock skew tolerance | Executor wall-clock and Brain time differ by more than `max_clock_skew_tolerance` (default 5s); security event; executor stops | Skew detected; security event logged; executor stops | C14 |
| RT-15.4 | Clock rollback rejection | Signed timestamp rolls backward more than `max_clock_rollback_tolerance` (default 1s) relative to last anchor; rejected | Rollback rejected; operator intervention required | C14 |
| RT-15.5 | Monotonic time for duration bounds | `max_continuation_duration` and grace periods measured with monotonic clock; wall-clock rollback does not extend | Monotonic clock used; wall-clock rollback does not extend duration | C14, C02 |
| RT-15.6 | Monotonic clock continuity loss | Process restart or suspend/resume causes monotonic clock to lose continuity; executor must STOP | Executor stops; no continuation after continuity loss | C14, C05 |
| RT-15.7 | Wall-clock drift exceeds tolerance | Wall-clock drift exceeds `max_clock_skew_tolerance`; executor must STOP | Executor stops; waits for fresh signed anchor | C14 |
| RT-15.8 | Time disagreement: no continuation | Executor and Brain time disagree beyond tolerance; continuation not permitted | Continuation forbidden; executor waits for fresh anchor | C14, C02 |
| RT-15.9 | Capability validity evaluated against signed anchors | `not_valid_before` and `not_valid_after` evaluated against signed Brain anchors, not executor wall-clock alone | Anchors used for evaluation; executor wall-clock not sufficient | C14, C02 |
| RT-15.10 | Signed anchor at outage declaration | `wall_outage_declared_at` is a signed wall-clock anchor; `monotonic_outage_start` is monotonic marker | Both fields present and correctly typed | C14, C05 |

### RT-16: Side-Effect Class Enforcement

**ADR ref:** §2.9, §9.3
**Components tested:** C02, C13, C10
**Invariants verified:** I15
**Acceptance criteria:** AC18
**Test type:** unit + integration + security

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| RT-16.1 | Class 0: local computation only | Class 0 continuation produces no external effects; eligible with capability and journal | No external effects produced; only local computation | C02, C08 |
| RT-16.2 | Class 1: reversible internal writes | Class 1 continuation produces reversible internal writes; eligible with capability, journal, and rollback plan | Internal writes produced; rollback plan available | C02, C08 |
| RT-16.3 | Class 2: idempotent external writes | Class 2 continuation produces idempotent external writes; eligible only if downstream validates `(command_id, operation_id, side_effect_slot)` | External writes produced; downstream validates identity | C02, C13 |
| RT-16.4 | Class 3: prohibited during continuation | Class 3 (irreversible/destructive/financial/legal) effect attempted during continuation; prohibited; security event | Effect rejected with `CLASS_3_PROHIBITED`; security event logged; manual review | C02, C13, C11, C12 |
| RT-16.5 | Default class is STOP | No `continuation_class` assigned; defaults to STOP; no continuation permitted | Continuation forbidden with `CLASS_DEFAULT_STOP` | C02 |
| RT-16.6 | Class assigned at dispatch | `continuation_class` assigned by Brain at dispatch based on command type, tenant policy, side-effect risk | Class assigned at dispatch; not modifiable by executor | C01, C02 |
| RT-16.7 | Downstream class validation | Downstream system validates effect class; Class 3 effect during continuation rejected by downstream | Downstream rejects Class 3 with `CLASS_3_DOWNSTREAM_REJECT` | C13 |
| RT-16.8 | Pinned policy cannot authorize new classes | Pinned policy snapshot cannot authorize side-effect classes or operations not explicitly permitted by capability | New class/operation rejected with `NOT_PERMITTED_BY_CAPABILITY` | C02, C07 |
| RT-16.9 | Class 3 effect: freeze and manual review | Class 3 effect attempted; effects frozen; manual review; classification `INVALID_CONTINUATION` | Effects frozen; `INVALID_CONTINUATION`; manual review | C10, C11, C13 |
| RT-16.10 | Permitted operation IDs enforced | Capability `permitted_operation_ids` does not include the attempted operation; rejected | Operation rejected with `OPERATION_NOT_PERMITTED` | C02, C13 |

---

## 5. Unit Tests Per Component (ADR-MC-001 Section 9.1)

Each of the 14 required components has dedicated unit tests covering its internal logic, edge cases, and error handling.

### C01: Signed Lease Token Service

**ADR ref:** §2.1.1–§2.1.3
**Invariants:** I1, I2

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| UT-C01-001 | Issue lease with all required fields | Lease token contains all 9 required fields; signature valid | All fields present; signature verifies | C14 |
| UT-C01-002 | Reject lease issuance for unknown command | Command ID not found; issuance rejected | Rejected with `COMMAND_NOT_FOUND` | — |
| UT-C01-003 | Reject lease issuance for cancelled command | Command already cancelled; issuance rejected | Rejected with `COMMAND_CANCELLED` | C06 |
| UT-C01-004 | Lease token signature verification | Valid signature accepted; invalid signature rejected | Valid accepted; invalid rejected with `SIGNATURE_INVALID` | C14 |
| UT-C01-005 | Expired lease token rejected | `expires_at` in past; token rejected | Rejected with `LEASE_EXPIRED` | C14 |
| UT-C01-006 | Revoked lease token rejected | Lease revoked via revocation stream; token rejected | Rejected with `LEASE_REVOKED` | C06 |
| UT-C01-007 | Renewal produces new token with extended expiry | Renewal succeeds; new `expires_at` > old; new signature | New token valid; old token invalid | C14, C02 |
| UT-C01-008 | Renewal invalidates prior continuation capability | Renewal revokes prior capability; new capability issued | Prior capability rejected; new capability valid | C02 |
| UT-C01-009 | Lease token tenant scoping | Token scoped to `tenant_id`; cross-tenant use rejected | Cross-tenant use rejected with `TENANT_MISMATCH` | — |
| UT-C01-010 | Lease audit event with causation link | Lease issuance event has causation link to dispatch event | Causation link present and verifiable | C12 |

### C02: Continuation Capability Service

**ADR ref:** §2.1.4, §2.11
**Invariants:** I3, I3a, I4, I12

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| UT-C02-001 | Issue capability with all 15 fields | All fields populated; `not_valid_before` >= lease `expires_at` | All fields present; time bound correct | C14, C07 |
| UT-C02-002 | Capability signature verification | Valid signature accepted; invalid rejected | Valid accepted; invalid rejected | C14 |
| UT-C02-003 | Capability not valid before `not_valid_before` | Current time < `not_valid_before`; capability rejected | Rejected with `CAPABILITY_NOT_YET_VALID` | C14 |
| UT-C02-004 | Capability expired after `not_valid_after` | Current time > `not_valid_after`; capability rejected | Rejected with `CAPABILITY_EXPIRED` | C14 |
| UT-C02-005 | Capability scope: command binding | `command_id` mismatch; rejected | Rejected with `COMMAND_MISMATCH` | — |
| UT-C02-006 | Capability scope: executor binding | `executor_id` mismatch; rejected | Rejected with `EXECUTOR_MISMATCH` | — |
| UT-C02-007 | Capability scope: tenant binding | `tenant_id` mismatch; rejected | Rejected with `TENANT_MISMATCH` | — |
| UT-C02-008 | Capability revocation | Capability revoked via revocation stream; rejected | Rejected with `CAPABILITY_REVOKED` | C06 |
| UT-C02-009 | Capability supersession at renewal | Prior capability superseded; only latest-lease capability valid | Prior capability rejected; latest accepted | C01, C06 |
| UT-C02-010 | `policy_snapshot_hash` validation | Hash mismatch; rejected | Rejected with `POLICY_HASH_MISMATCH` | C07 |
| UT-C02-011 | `policy_snapshot_not_valid_after` enforcement | Time exceeds `policy_snapshot_not_valid_after`; capability invalid | Rejected with `POLICY_SNAPSHOT_EXPIRED` | C07, C14 |
| UT-C02-012 | `permitted_operation_ids` enforcement | Operation not in permitted list; rejected | Rejected with `OPERATION_NOT_PERMITTED` | — |
| UT-C02-013 | `side_effect_slot_spec` enforcement | Side-effect slot not in spec; rejected | Rejected with `SLOT_NOT_PERMITTED` | — |
| UT-C02-014 | `revocation_watermark_required` enforcement | Watermark below required; rejected | Rejected with `WATERMARK_BELOW_REQUIRED` | C06 |
| UT-C02-015 | `max_continuation_duration` bound | Duration exceeds bound; rejected | Rejected with `DURATION_EXCEEDED` | C14 |
| UT-C02-016 | `max_continuation_operations` bound | Operation count exceeds bound; rejected | Rejected with `OPERATION_COUNT_EXCEEDED` | — |
| UT-C02-017 | Capability not issued when continuation disallowed | Brain does not issue capability; `continuation_capability_id` null | No capability; continuation impossible | — |
| UT-C02-018 | Capability audit events | Issuance, supersession, revocation all audited | All three event types in audit | C12 |

### C03: Brain Heartbeat Endpoint

**ADR ref:** §2.2.1, §2.6.1
**Invariants:** I4, I14

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| UT-C03-001 | Heartbeat acknowledgement received | Brain responds to heartbeat; executor records acknowledgement | Acknowledgement recorded; timestamp signed | C14 |
| UT-C03-002 | Heartbeat miss counted | Brain does not respond; miss counted toward `brain_heartbeat_miss_threshold` | Miss count incremented | — |
| UT-C03-003 | Heartbeat miss threshold crossed | Misses reach `brain_heartbeat_miss_threshold`; signal crosses threshold | Signal threshold crossed; signal recorded | — |
| UT-C03-004 | Recovery notification via heartbeat | Brain sends recovery notification through heartbeat channel; signed | Notification received; signature verifies | C14 |
| UT-C03-005 | Heartbeat delivers signed time anchor | Heartbeat response includes signed time anchor | Anchor present; signature verifies | C14 |
| UT-C03-006 | Heartbeat delivers revocation watermark | Heartbeat response includes current revocation watermark | Watermark present; watermark updated | C06 |

### C04: Witness Statement Service

**ADR ref:** §2.2.4
**Invariants:** I4, I14

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| UT-C04-001 | Witness statement signed with identity key | Statement signed; signature verifies; `witness_id` present | Signature verifies; `witness_id` present | C14 |
| UT-C04-002 | Witness statement fields | Statement includes `tenant_id`, `brain_region`, `witness_id`, `statement_id`, timestamp, nonce | All fields present; missing field rejected | C14 |
| UT-C04-003 | Witness nonce monotonicity | Nonce monotonically increasing; stale nonce rejected | Stale nonce rejected with `NONCE_STALE` | — |
| UT-C04-004 | Witness statement max age | Statement older than `witness_statement_max_age`; ignored | Statement ignored; not counted | C14 |
| UT-C04-005 | Witness tenant partitioning | Statement for tenant A about tenant B; rejected | Rejected with `TENANT_MISMATCH` | — |
| UT-C04-006 | Witness key revocation | Witness key revoked; statements invalid | Statements rejected with `WITNESS_KEY_REVOKED` | C06 |
| UT-C04-007 | Witness self-exclusion | Executor counts itself as witness; rejected | Rejected with `SELF_EXCLUSION_VIOLATION` | — |
| UT-C04-008 | Witness quorum calculation | N witnesses, f faulty; quorum = 2f+1 (BFT) or f+1 (CFT); quorum correctly computed | Quorum count correct; model documented | — |
| UT-C04-009 | Witness statement replay | Replayed statement with old nonce; rejected | Rejected with `REPLAY_DETECTED` | — |
| UT-C04-010 | Compromised witness threshold | f witnesses compromised; quorum still achievable with honest witnesses | Quorum achievable; compromised witnesses excluded | C06 |

### C05: Executor Local State Cache

**ADR ref:** §2.3
**Invariants:** I4, I5

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| UT-C05-001 | Store and retrieve inputs | Cache stores command inputs; retrieved on continuation | Inputs stored and retrieved correctly | — |
| UT-C05-002 | Store and retrieve prior step outputs | Cache stores outputs of prior steps; retrieved for continuation | Outputs stored and retrieved | — |
| UT-C05-003 | State sufficiency self-check | Self-check against task manifest; all required inputs and deterministic path available | Self-check passes; all required inputs present | — |
| UT-C05-004 | State insufficiency detected | Missing required input or non-deterministic path; self-check fails | Self-check fails with `LOCAL_STATE_INSUFFICIENT` | — |
| UT-C05-005 | Outage record persistence | Outage record persisted locally; survives process restart | Record present after restart; all fields intact | C14 |
| UT-C05-006 | Configuration storage | Executor configuration stored in cache; retrieved for eligibility checks | Configuration stored and retrieved | — |
| UT-C05-007 | Cache invalidation on policy refresh | After recovery, cache invalidated; policy refreshed | Cache invalidated; fresh policy loaded | C07 |

### C06: Revocation Stream

**ADR ref:** §2.10
**Invariants:** I13

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| UT-C06-001 | Revocation stream entry signed | Each entry signed by Brain; signature verifies | Signature verifies | C14 |
| UT-C06-002 | Sequence number monotonicity | Sequence numbers monotonically increasing; out-of-order rejected | Out-of-order entry rejected | — |
| UT-C06-003 | Tenant partitioning | Stream partitioned by tenant; cross-tenant entries not visible | Cross-tenant entry not visible | — |
| UT-C06-004 | Revocation entry types: lease, capability, cancellation, emergency deny | All four entry types supported; each correctly typed | All types processed correctly | C01, C02 |
| UT-C06-005 | Watermark tracking | Executor records highest observed sequence number | Watermark updated correctly | — |
| UT-C06-006 | Cache age tracking | Executor tracks revocation cache age; stale cache detected | Cache age tracked; stale detected at `max_revocation_cache_age` | C14 |
| UT-C06-007 | Fail-closed on missing watermark | No watermark recorded; continuation forbidden | Continuation forbidden | — |
| UT-C06-008 | Emergency deny channel | Emergency deny travels through survivable channel; received and processed | Deny received; executor stops | C04, C07 |

### C07: Policy Snapshot Registry

**ADR ref:** §2.11
**Invariants:** I12

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| UT-C07-001 | Pin policy snapshot by hash | Snapshot pinned by cryptographic hash; hash verifies | Hash matches; snapshot valid | — |
| UT-C07-002 | Snapshot validity time bound | `policy_snapshot_not_valid_after` enforced; expired snapshot rejected | Rejected with `POLICY_SNAPSHOT_EXPIRED` | C14 |
| UT-C07-003 | Snapshot supersession detection | Policy snapshot superseded; renewal rejected | Rejected with `POLICY_SUPERSEDED` | — |
| UT-C07-004 | Pinned snapshot cannot authorize new classes | Pinned snapshot cannot authorize classes/operations not in capability | New class/operation rejected | C02 |
| UT-C07-005 | Emergency deny channel integration | Critical deny/revocation travels through survivable channel; executor receives | Deny received; executor stops | C06, C04 |
| UT-C07-006 | Snapshot hash mismatch | Capability `policy_snapshot_hash` does not match registry; rejected | Rejected with `POLICY_HASH_MISMATCH` | C02 |
| UT-C07-007 | Policy broadcast silence detection | No policy broadcast for `policy_silence_threshold`; signal crosses threshold | Signal threshold crossed | — |

### C08: Continuation Journal Store

**ADR ref:** §2.5.3
**Invariants:** I5, I10

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| UT-C08-001 | Journal records every operation | Each operation logged with input, output, success/failure, timestamp, stable effect identity | All fields present for each operation | C13 |
| UT-C08-002 | Journal immutability | Journal entry modified after append; detected; rejected | Modification detected; hash mismatch | — |
| UT-C08-003 | Journal encrypted blob | Journal serialized as encrypted blob for completion report | Blob encrypted; decryptable by Brain | — |
| UT-C08-004 | Journal stable effect identity | Each entry includes `(command_id, operation_id, side_effect_slot)` | Identity present and stable | C13 |
| UT-C08-005 | Journal operation count tracking | Journal tracks operation count; `max_continuation_operations` enforced | Count tracked; excess operations blocked | C02 |
| UT-C08-006 | Journal skip recording | Duplicate operation skipped; skip recorded in journal | Skip recorded with reason | C13 |
| UT-C08-007 | Journal timestamp monotonicity | Journal timestamps monotonically increasing within a continuation | Timestamps monotonic | C14 |

### C09: Completion Receipt Service

**ADR ref:** §2.6.2, §2.13
**Invariants:** I6

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| UT-C09-001 | Receipt generation with all 14 fields | All fields populated correctly | All fields present and valid | C08, C14 |
| UT-C09-002 | Receipt signature | Receipt signed by executor; signature verifies | Signature verifies | C14 |
| UT-C09-003 | Receipt immutability | Receipt modified; hash mismatch detected | Modification detected | — |
| UT-C09-004 | Outage evidence bundle assembly | Bundle contains outage declaration, witness statements, signal thresholds, signed time anchor | All components present; bound to `capability_id` and `command_id` | C04, C14 |
| UT-C09-005 | Receipt for each final state | Receipts generated for `SUCCEEDED`, `FAILED`, `ABORTED`, `TIMEOUT` | All four states produce valid receipts | — |
| UT-C09-006 | Receipt audit chain link | Receipt linked to audit chain; causation verifiable | Causation link present and verifiable | C12 |
| UT-C09-007 | Receipt `operations_performed` list | List contains each operation with `(operation_id, side_effect_slot, stable_effect_identity, result_digest)` | All four sub-fields per operation | C13 |
| UT-C09-008 | Receipt `revocation_watermark_observed` | Field populated with observed watermark | Watermark present and correct | C06 |

### C10: Reconciliation Engine

**ADR ref:** §2.6, §2.12
**Invariants:** I7, I8, I10

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| UT-C10-001 | Result selection: single valid | Single report; no conflict; selected | Result selected; classification `VALID_CONTINUATION` | C09 |
| UT-C10-002 | Result selection: multiple agree, idempotent | Multiple reports agree; effects idempotent; first by signed time wins | First selected; others `DUPLICATE_AGREED` | C14, C13 |
| UT-C10-003 | Result selection: tie-breaker | Same signed time; lowest `executor_id` wins | Lowest `executor_id` selected | — |
| UT-C10-004 | Result selection: divergent | Divergent results; no auto-selection; manual review | `MANUAL_REVIEW_REQUIRED` | C11 |
| UT-C10-005 | Effect reconciliation: duplicate | Duplicate identity; not re-applied | Marked `DUPLICATE`; no re-apply | C13 |
| UT-C10-006 | Effect reconciliation: conflict | Identity conflict; freeze; manual review | Resource frozen; manual review | C11, C13 |
| UT-C10-007 | Compensation: reversible | Reversible effect; compensation authorized | Compensation command issued | C01, C13 |
| UT-C10-008 | Compensation: irreversible | Irreversible effect; no auto-compensation | No auto-compensation; manual review | C11 |
| UT-C10-009 | Classification: VALID_BUT_RECONCILED | Effects required reconciliation; classified correctly | Classification correct | C13 |
| UT-C10-010 | Classification: INVALID_CONTINUATION | Eligibility not met; classified invalid | Classification correct; executor flagged | C11 |
| UT-C10-011 | Classification: CONFLICTING_REPORTS | Irreconcilable differences; classified correctly | Classification correct | C11 |
| UT-C10-012 | Timestamp selection only when idempotent | Timestamp-based selection only for provably idempotent effects | Timestamp used only for idempotent | C13 |
| UT-C10-013 | Completion report deadline | Late report flagged | Late report flagged; audit recorded | C09, C12 |

### C11: Conflict Review Queue

**ADR ref:** §2.6.3.4, §2.12
**Invariants:** I8

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| UT-C11-001 | Queue entry for divergent results | Divergent results enqueued with full evidence | Entry created with evidence, receipts, journals | C09, C10 |
| UT-C11-002 | Queue entry for non-reversible effects | Non-reversible effects enqueued | Entry created; effects frozen | C10, C13 |
| UT-C11-003 | Queue entry for invalid continuation | Invalid continuation enqueued; executor flagged | Entry created; executor flagged | C10 |
| UT-C11-004 | Queue entry for disputed capability validity | Capability validity disputed; enqueued | Entry created with capability evidence | C02 |
| UT-C11-005 | Queue entry for non-deterministic reconciliation | Reconciliation cannot produce deterministic outcome; enqueued | Entry created with reconciliation context | C10 |
| UT-C11-006 | Operator resolution | Operator resolves conflict; command exits `MANUAL_REVIEW_REQUIRED` | Command state updated; resolution audited | C12 |
| UT-C11-007 | All evidence surfaced | All evidence, receipts, and journals surfaced in queue entry | All evidence accessible from queue entry | C08, C09 |

### C12: Audit Event Pipeline

**ADR ref:** §2.13
**Invariants:** I11

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| UT-C12-001 | Append event to immutable ledger | Event appended; ledger entry created | Entry created; hash-linked | — |
| UT-C12-002 | Ledger immutability | Entry modified after append; detected | Modification detected; hash mismatch | — |
| UT-C12-003 | Causation chain hash linking | Each event hash-linked to previous; chain verifiable | Chain verifies end-to-end | — |
| UT-C12-004 | Projection pagination with metadata | Projection caps at `MAX_CAUSATION_LINKS`; truncation metadata present | Projection caps; metadata present; ledger unaffected | — |
| UT-C12-005 | All 9 event types supported | Lease expiry, capability issuance, outage declaration, eligibility decision, each operation, completion, recovery, reconciliation, terminal state | All types accepted and stored | C01–C11, C13, C14 |
| UT-C12-006 | Ledger never truncated | Authoritative storage entries count == events produced | No entries removed; count matches | — |
| UT-C12-007 | Event ordering preservation | Events stored in causal order; ordering preserved | Causal order maintained | — |

### C13: Downstream Effect Identity Layer

**ADR ref:** §2.5
**Invariants:** I10, I15

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| UT-C13-001 | Validate effect identity format | `(command_id, operation_id, side_effect_slot)` format validated | Valid format accepted; invalid rejected | — |
| UT-C13-002 | Reject duplicate effect | Same identity already applied; second rejected | Rejected with `DUPLICATE_EFFECT` | — |
| UT-C13-003 | Validate continuation capability token | Downstream validates signed capability token, not expired lease | Capability token validated; expired lease rejected | C02 |
| UT-C13-004 | Validate outage evidence | Downstream validates outage evidence bundle; rejects without it | Evidence validated; missing evidence rejected | C09 |
| UT-C13-005 | Outage evidence binding check | Evidence `capability_id` and `command_id` match effect; mismatch rejected | Mismatch rejected with `EVIDENCE_MISMATCH` | C09 |
| UT-C13-006 | Class 3 rejection | Class 3 effect during continuation; rejected | Rejected with `CLASS_3_PROHIBITED` | C02 |
| UT-C13-007 | Root command ID for replay effects | Replay effect identity uses `root_command_id`; not replay command ID | `root_command_id` used; dedup against original effects | C10 |
| UT-C13-008 | Side-effect slot spec validation | Slot not in capability `side_effect_slot_spec`; rejected | Rejected with `SLOT_NOT_PERMITTED` | C02 |

### C14: Signed Time-Anchor Service

**ADR ref:** §2.8
**Invariants:** I14

| Test ID | Test Name | Description | Pass/Fail Criteria | Dependencies |
|---|---|---|---|---|
| UT-C14-001 | Issue signed time anchor | Anchor signed by Brain; signature verifies | Signature verifies | — |
| UT-C14-002 | Clock skew detection | Skew > `max_clock_skew_tolerance`; security event | Skew detected; event logged | — |
| UT-C14-003 | Clock rollback detection | Rollback > `max_clock_rollback_tolerance`; rejected | Rollback rejected; operator intervention | — |
| UT-C14-004 | Monotonic clock for durations | Duration measured with monotonic clock; not wall-clock | Monotonic used; wall-clock rollback ineffective | — |
| UT-C14-005 | Monotonic continuity loss detection | Process restart/suspend; continuity lost; executor stops | Executor stops; no continuation | C05 |
| UT-C14-006 | Anchor at dispatch, renewal, recovery | Anchors issued at all three points | All three anchors present | C01, C02, C03 |
| UT-C14-007 | Capability time bounds evaluated against anchors | `not_valid_before`/`not_valid_after` checked against signed anchors | Anchors used; wall-clock alone insufficient | C02 |
| UT-C14-008 | Time disagreement handling | Executor and Brain disagree beyond tolerance; executor stops | Executor stops; waits for fresh anchor | — |

---

## 6. Integration Tests

Integration tests exercise interactions between two or more components with real (non-mocked) interfaces.

| Test ID | Test Name | Description | ADR Ref | Components | Invariants | Pass/Fail Criteria | Type | Dependencies |
|---|---|---|---|---|---|---|---|---|
| INT-001 | Lease issuance + capability issuance at dispatch | Brain dispatches command; lease and capability issued together; both signed; audit events recorded | §2.1.1, §2.1.4 | C01, C02, C07, C12, C14 | I1, I3 | Both tokens valid; audit events present | integration | UT-C01-*, UT-C02-* |
| INT-002 | Lease renewal + capability rotation | Renewal extends lease; rotates capability; old capability superseded; downstream rejects old | §2.1.2 | C01, C02, C13, C14, C12 | I3a | Old capability rejected; new valid; rotation audited | integration | INT-001 |
| INT-003 | Outage detection with heartbeat + witness | Heartbeat miss + witness quorum; outage declared; grace period respected | §2.2.1–§2.2.4 | C03, C04, C14, C05 | I4 | Outage declared; both signals recorded; grace period elapsed | integration | UT-C03-*, UT-C04-* |
| INT-004 | Outage detection with lease rejection + policy silence | Lease rejection + policy silence; outage declared | §2.2.1–§2.2.2 | C01, C07, C14, C05 | I4 | Outage declared; both signals recorded | integration | INT-003 |
| INT-005 | Full eligibility check | All 11 eligibility criteria evaluated; all must pass for continuation | §2.3 | C01–C07, C14 | I1–I5, I9, I12–I15 | All criteria pass; continuation permitted | integration | INT-001–INT-004 |
| INT-006 | Continuation execution with journal | Executor continues; journal records each operation; receipt generated | §2.5.3, §2.6.2 | C05, C08, C09, C13, C14 | I5, I6, I10 | Journal complete; receipt valid; effects applied | integration | INT-005 |
| INT-007 | Downstream effect validation | Downstream validates capability token + outage evidence + effect identity | §2.5, §2.1.4 | C02, C09, C13 | I10, I15 | All validations pass; effect applied | integration | INT-006 |
| INT-008 | Recovery detection + report collection | Brain recovers; recovery detected; reports collected within deadline | §2.6.1, §2.6.2, §2.15 | C03, C09, C10, C14 | I7 | Recovery declared; reports collected; deadline met | integration | INT-006 |
| INT-009 | Reconciliation: single valid continuation | One report; no conflict; effects applied; classification VALID | §2.6.3 | C10, C13, C12 | I7, I10 | Classification correct; effects applied | integration | INT-008 |
| INT-010 | Reconciliation: multiple agreeing | Two reports agree; idempotent; first by signed time wins; other DUPLICATE_AGREED | §2.6.3.1, §2.12.2 | C10, C13, C14, C12 | I8, I10 | First selected; other marked; effects deduplicated | integration | INT-008 |
| INT-011 | Reconciliation: divergent results | Two reports diverge; manual review; effects frozen | §2.6.3.1, §2.12.2 | C10, C11, C13, C12 | I8 | Manual review; effects frozen; no silent resolution | integration | INT-008 |
| INT-012 | Compensation flow | Reversible effect; compensation authorized; compensation command issued with lease + idempotency + audit | §2.6.3.3 | C10, C01, C13, C12 | I7, I10 | Compensation command issued; original reversed; audited | integration | INT-009 |
| INT-013 | Replay after reconciliation | Reconciliation complete; Brain authorizes replay; new lease; effect identity uses root_command_id | §2.7 | C10, C01, C13, C12 | I10 | Replay authorized; root_command_id used; dedup works | integration | INT-009 |
| INT-014 | Revocation stream + watermark + eligibility | Revocation stream updated; watermark checked; eligibility enforced | §2.10 | C06, C02, C05 | I13 | Watermark checked; fail-closed when stale | integration | UT-C06-*, INT-005 |
| INT-015 | Policy snapshot pinning + validation | Capability carries policy snapshot hash; executor validates against registry | §2.11 | C02, C07, C14 | I12 | Hash matches; mismatch rejected | integration | UT-C07-*, INT-001 |
| INT-016 | Audit chain completeness across lifecycle | Full lifecycle: dispatch → lease → expiry → outage → continuation → receipt → recovery → reconciliation → terminal; all events in ledger | §2.13 | C12, all | I11 | All 9 event types in ledger; chain intact | integration | INT-001–INT-013 |
| INT-017 | Side-effect class enforcement end-to-end | Class 0/1/2 continuations succeed; Class 3 rejected; downstream validates | §2.9 | C02, C13, C10, C11 | I15 | Class 0–2 succeed; Class 3 rejected; security event | integration | INT-006 |
| INT-018 | Tenant isolation end-to-end | Tenant A and B continuations fully isolated; cross-tenant rejected | §2.14 | C02, C06, C04, C10, C12 | I9 | Cross-tenant rejected; security events logged | integration | INT-005, INT-009 |
| INT-019 | Heartbeat delivers time anchor + watermark | Heartbeat response includes signed anchor and revocation watermark | §2.2.1, §2.8, §2.10 | C03, C14, C06 | I13, I14 | Anchor and watermark present; signatures verify | integration | UT-C03-*, UT-C14-* |
| INT-020 | Capability supersession with downstream validation | Renewal rotates capability; downstream rejects prior capability ID even with later not_valid_after | §2.1.2, §2.1.4 | C01, C02, C13 | I3a | Prior capability rejected; latest accepted | integration | INT-002 |

---

## 7. Resilience Tests

Resilience tests verify system behavior under infrastructure failure conditions.

| Test ID | Test Name | Description | ADR Ref | Components | Invariants | Pass/Fail Criteria | Type | Dependencies |
|---|---|---|---|---|---|---|---|---|
| RES-001 | Executor crash during continuation | Executor process killed mid-continuation; on restart, executor detects incomplete continuation; enters safe-hold; does not resume | §2.3, §2.8 | C05, C08, C14 | I5, I14 | Executor stops after restart; no resume; partial journal preserved | resilience | INT-006 |
| RES-002 | Executor crash before receipt | Executor crashes before generating receipt; no receipt; Brain flags missing receipt on reconciliation | §2.6.2 | C09, C10, C11 | I6 | Missing receipt detected; flagged; `INVALID_CONTINUATION` | resilience | INT-006 |
| RES-003 | Brain crash during dispatch | Brain crashes mid-dispatch; lease issued but capability not; executor has lease but no capability; cannot continue | §2.1.1, §2.1.4 | C01, C02, C05 | I1, I3 | No capability; continuation impossible; executor stops | resilience | INT-001 |
| RES-004 | Brain crash during renewal | Brain crashes during renewal; old token revoked, new not issued; executor has no valid token; stops | §2.1.2 | C01, C14 | I2 | No valid token; executor stops | resilience | INT-002 |
| RES-005 | Network partition: executor isolated from Brain | Executor cannot reach Brain; heartbeat misses; lease rejections; outage declared after grace period if second signal present | §2.2.1, §2.2.2 | C03, C01, C05, C14 | I4 | Outage declared only with 2 signals + grace; otherwise stops | resilience | INT-003 |
| RES-006 | Network partition: executor isolated from Brain and witnesses | Executor isolated from both Brain and witnesses; only direct-Brain signals; outage declared if 2 direct signals | §2.2.2, §2.2.4 | C03, C04, C05 | I4 | Outage declared with 2 direct signals; witnesses unavailable | resilience | RES-005 |
| RES-007 | Network partition: executor isolated from Brain but not witnesses | Executor can reach witnesses but not Brain; witness quorum achieved; but no direct-Brain signal; outage NOT declared | §2.2.4 | C03, C04 | I4 | No outage; direct-Brain signal required | resilience | RES-005 |
| RES-008 | Network partition: split-brain (two executors, both continue) | Two executors isolated from Brain and each other; both declare outage and continue; reports diverge; manual review | §2.12 | C10, C11, C13, C09 | I8 | Both reports collected; conflict detected; manual review | resilience | INT-011 |
| RES-009 | Clock drift forward | Executor clock drifts forward beyond `max_clock_skew_tolerance`; executor stops; security event | §2.8 | C14, C05 | I14 | Skew detected; executor stops; event logged | resilience | UT-C14-* |
| RES-010 | Clock drift backward | Executor clock drifts backward beyond `max_clock_rollback_tolerance`; rollback rejected; operator intervention | §2.8 | C14, C05 | I14 | Rollback rejected; operator intervention required | resilience | UT-C14-* |
| RES-011 | Clock drift extends duration | Executor attempts to extend `max_continuation_duration` via clock rollback; monotonic clock prevents extension | §2.4, §2.8 | C14, C02, C08 | I5, I14 | Monotonic clock used; extension prevented | resilience | UT-C14-*, RT-06.8 |
| RES-012 | Monotonic clock continuity loss (process suspend) | Process suspended/resumed; monotonic clock loses continuity; executor stops | §2.8 | C14, C05 | I14 | Executor stops; no continuation | resilience | UT-C14-005 |
| RES-013 | Brain recovery during continuation | Brain recovers mid-continuation; in-progress operations: committed finished, uncommitted aborted; no double-action | §2.12.2, §2.15 | C10, C08, C09, C03 | I7, I8 | Atomicity rule applied; no double-action; `RECONCILING` | resilience | INT-008, RT-11.7 |
| RES-014 | Brain recovery during Class 2 operation | Brain recovers during idempotent external write; committed write finished and reported; uncommitted aborted | §2.12.2, §2.9 | C10, C08, C13 | I7, I10, I15 | Committed write finished; uncommitted aborted; dedup works | resilience | RES-013 |
| RES-015 | Revocation stream lag | Revocation stream delayed; executor's cache age exceeds `max_revocation_cache_age`; continuation forbidden | §2.10 | C06, C02, C14 | I13 | Continuation forbidden; fail-closed | resilience | INT-014 |
| RES-016 | Witness node failure during outage detection | Some witness nodes fail; quorum still achievable with remaining honest witnesses | §2.2.4 | C04 | I4 | Quorum achieved with remaining witnesses | resilience | UT-C04-* |
| RES-017 | Witness node failure: quorum lost | Too many witnesses fail; quorum not achievable; witness signal not crossed; outage not declared on witness signal alone | §2.2.4 | C04 | I4 | No witness quorum; signal not crossed | resilience | RES-016 |
| RES-018 | Audit ledger write failure | Audit ledger temporarily unavailable; events buffered; no events lost; ledger eventually consistent | §2.13 | C12 | I11 | No events lost; ledger complete after recovery | resilience | UT-C12-* |
| RES-019 | Downstream system unavailable | Downstream system unavailable during continuation; Class 2 effect cannot be applied; executor stops | §2.9 | C13, C05 | I15 | Executor stops; effect not applied; audit recorded | resilience | INT-007 |
| RES-020 | Policy snapshot registry unavailable | Registry unavailable during continuation; executor uses pinned snapshot from capability; continues if valid | §2.11 | C07, C02 | I12 | Pinned snapshot used; continuation proceeds if valid | resilience | INT-015 |

---

## 8. Chaos Tests

Chaos tests inject random or adversarial failures across multiple components simultaneously.

| Test ID | Test Name | Description | ADR Ref | Components | Invariants | Pass/Fail Criteria | Type | Dependencies |
|---|---|---|---|---|---|---|---|---|
| CHS-001 | Random component kill (single executor) | Randomly kill executor components (journal, receipt, state cache) during continuation; system must stop safely | §2.3, §2.15 | C05, C08, C09 | I5, I6 | Executor stops safely; no unauthorized effects; partial state preserved | chaos | RES-001, RES-002 |
| CHS-002 | Random Brain component kill | Randomly kill Brain components (lease, capability, heartbeat, revocation, reconciliation) during outage; system must degrade safely | §2.1, §2.2, §2.6 | C01, C02, C03, C06, C10 | I1–I4, I7 | Safe degradation; no unauthorized continuation; recovery after restart | chaos | RES-003, RES-004 |
| CHS-003 | Byzantine witnesses: f faulty | f witnesses send false statements; quorum requires 2f+1; false quorum cannot form; honest quorum still achievable | §2.2.4 | C04 | I4 | False statements rejected; honest quorum works; BFT bound holds | chaos | UT-C04-* |
| CHS-004 | Byzantine witnesses: colluding minority | Minority of witnesses collude to declare false outage; quorum not achievable without honest witnesses; outage not declared on witness signal alone | §2.2.4 | C04, C03 | I4 | False outage not declared; direct-Brain signal still required | chaos | CHS-003 |
| CHS-005 | Byzantine executor: false continuation report | Executor submits false continuation report; signature valid but content fabricated; reconciliation detects divergence; manual review | §2.6.3, §2.12 | C09, C10, C11, C13 | I8 | False report detected via divergence; manual review; executor flagged | chaos | INT-011 |
| CHS-006 | Byzantine executor: claims no outage | Executor claims it did not continue but actually did; effects detected via downstream identity; reconciliation flags | §2.6.3, §2.5 | C10, C13, C11 | I8, I10 | Unreported effects detected; executor flagged; manual review | chaos | INT-007 |
| CHS-007 | Split-brain: two executors, both continue, results agree | Two executors continue same command; results agree; effects idempotent; first by signed time wins; other DUPLICATE_AGREED | §2.12.2 | C10, C13, C14, C09 | I8, I10 | First selected; other DUPLICATE_AGREED; effects deduplicated | chaos | INT-010 |
| CHS-008 | Split-brain: two executors, both continue, results diverge | Two executors continue; results diverge; manual review; effects frozen | §2.12.2 | C10, C11, C13, C09 | I8 | Manual review; effects frozen; no silent resolution | chaos | INT-011 |
| CHS-009 | Split-brain: three executors, mixed agreement | Three executors continue; two agree, one diverges; two-agree group reconciled; divergent one to manual review | §2.12.2 | C10, C11, C13, C14 | I8 | Two-agree group reconciled; divergent to manual review | chaos | CHS-007, CHS-008 |
| CHS-010 | Split-brain: Brain recovers mid-continuation | Brain recovers while multiple executors continuing; atomicity rule applied per executor; no double-action | §2.12.2, §2.15 | C10, C08, C09, C03 | I7, I8 | Atomicity per executor; no double-action; `RECONCILING` | chaos | RES-013 |
| CHS-011 | Network partition + clock drift | Simultaneous network partition and clock drift; executor must handle both; stops if either prevents safe continuation | §2.2, §2.8 | C03, C04, C14, C05 | I4, I14 | Executor stops; neither condition exploited | chaos | RES-005, RES-009 |
| CHS-012 | Cascading failures: Brain + witnesses + downstream | Brain, some witnesses, and downstream all fail; executor must stop safely; no unauthorized effects | §2.3, §2.9 | C03, C04, C13, C05 | I4, I15 | Executor stops; no effects; safe-hold | chaos | RES-005, RES-019 |
| CHS-013 | Random revocation stream delays | Revocation stream entries delayed randomly; executor must handle stale cache; fail-closed when cache age exceeded | §2.10 | C06, C02, C14 | I13 | Fail-closed when stale; no continuation with stale revocation | chaos | RES-015 |
| CHS-014 | Random policy broadcast gaps | Policy broadcasts randomly delayed; policy silence signal may cross threshold; combined with other signals | §2.2.1, §2.11 | C07, C03 | I4 | Signal correctly counted; outage only with 2 signals | chaos | INT-004 |
| CHS-015 | Sustained outage: capability window expires | Brain unavailable beyond `continuation_capability_max_validity`; executor stops at `not_valid_after`; partial results; manual recovery | §2.4, §2.12.2 | C02, C09, C10, C11 | I5, I8 | Executor stops at `not_valid_after`; partial results; manual review | chaos | RT-11.8 |
| CHS-016 | Rapid renewal + expiry cycles | Lease rapidly renewed and expired; capability rotation stress; no capability reuse; all supersession audited | §2.1.2 | C01, C02, C12, C14 | I3a | No capability reuse; all rotations audited; no authority leakage | chaos | INT-002 |
| CHS-017 | Concurrent continuations from multiple executors | Multiple executors continue different commands simultaneously; per-executor concurrency limit enforced | §2.4 | C02, C05 | I5 | Concurrency limit enforced; excess rejected | chaos | RT-06.4 |
| CHS-018 | Tenant rate limit under load | High continuation rate from single tenant; circuit breaker trips; other tenants unaffected | §2.4, §2.14 | C02 | I5, I9 | Rate limit enforced; other tenants unaffected | chaos | RT-06.6, INT-018 |

---

## 9. Security Tests

Security tests verify that attack vectors are blocked. All are negative tests asserting rejection.

| Test ID | Test Name | Description | ADR Ref | Components | Invariants | Pass/Fail Criteria | Type | Dependencies |
|---|---|---|---|---|---|---|---|---|
| SEC-001 | Capability forgery: fabricated signature | Forged capability with fake signature; all validators reject | §2.1.4, §6.3 | C02, C13, C14 | I3 | Rejected with `SIGNATURE_INVALID`; security event | security | UT-C02-002 |
| SEC-002 | Capability forgery: valid signature, wrong issuer | Capability signed by non-Brain key; rejected | §2.1.4 | C02, C14 | I3 | Rejected with `SIGNER_NOT_AUTHORIZED` | security | SEC-001 |
| SEC-003 | Capability forgery: all fields valid, signature wrong | All fields correct but signature tampered; rejected | §2.1.4 | C02, C14 | I3 | Rejected with `SIGNATURE_INVALID` | security | SEC-001 |
| SEC-004 | Expired lease used for continuation | Executor uses expired lease token to authorize continuation; rejected | §2.1.3, §6.3 | C01, C02, C13 | I2 | Rejected with `LEASE_EXPIRED`; security event | security | UT-C01-005 |
| SEC-005 | Expired lease used for downstream effects | Executor uses expired lease to prove authority to downstream; rejected | §2.1.3 | C01, C13 | I2 | Rejected with `LEASE_EXPIRED` | security | SEC-004 |
| SEC-006 | Capability used before lease expiry | Executor attempts to use capability while lease active; `not_valid_before` not reached; rejected | §2.1.4 | C02, C13 | I3 | Rejected with `CAPABILITY_NOT_YET_VALID` | security | UT-C02-003 |
| SEC-007 | Replay attack: old capability reused | Previously used/revoked capability reused; rejected | §2.1.4, §2.5 | C02, C13 | I3, I10 | Rejected with `CAPABILITY_REVOKED` or `CAPABILITY_ALREADY_USED` | security | UT-C02-008 |
| SEC-008 | Replay attack: old witness statement replayed | Stale witness statement with old nonce replayed; rejected | §2.2.4 | C04, C14 | I4 | Rejected with `REPLAY_DETECTED` | security | UT-C04-009 |
| SEC-009 | Replay attack: old continuation report replayed | Duplicate continuation report for same `(command_id, continuation_id)`; rejected | §2.5, §2.6 | C10 | I10 | Rejected with `DUPLICATE_REPORT` | security | RT-08.6 |
| SEC-010 | Replay attack: old effect replayed | Duplicate effect with same identity; rejected by downstream | §2.5 | C13 | I10 | Rejected with `DUPLICATE_EFFECT` | security | UT-C13-002 |
| SEC-011 | Cross-tenant capability use | Capability for tenant A used in tenant B context; rejected; security event | §2.14, §6.3 | C02, C13, C12 | I9 | Rejected with `TENANT_MISMATCH`; security event | security | UT-C02-007 |
| SEC-012 | Cross-tenant continuation attempt | Executor for tenant A continues command for tenant B; rejected; security event | §2.14 | C02, C12 | I9 | Rejected; security event logged | security | RT-12.1 |
| SEC-013 | Cross-tenant witness statement | Witness for tenant A issues statement about tenant B; rejected | §2.14, §2.2.4 | C04 | I9 | Rejected with `WITNESS_TENANT_MISMATCH` | security | UT-C04-005 |
| SEC-014 | Cross-tenant revocation stream access | Executor for tenant B reads tenant A's revocation stream; not delivered | §2.14 | C06 | I9 | Cross-tenant entry not visible | security | UT-C06-003 |
| SEC-015 | Audit tampering: modify event | Audit event modified after append; detected; rejected | §2.13, §6.3 | C12 | I11 | Modification detected; hash mismatch; rejected | security | UT-C12-002 |
| SEC-016 | Audit tampering: delete event | Audit event deleted from ledger; detected; gap in hash chain | §2.13 | C12 | I11 | Deletion detected; chain gap; alert | security | UT-C12-003 |
| SEC-017 | Audit tampering: insert fake event | Fake event inserted into ledger; hash chain breaks; detected | §2.13 | C12 | I11 | Insertion detected; chain break; rejected | security | UT-C12-003 |
| SEC-018 | Audit tampering: reorder events | Events reordered; causal order violated; detected | §2.13 | C12 | I11 | Reordering detected; causal order violation | security | UT-C12-007 |
| SEC-019 | Executor bootstraps own authority | Executor attempts to continue without Brain-issued capability; rejected | §2.1.4, §6.3 | C02, C13 | I3, I4 | Rejected; no self-issued authority | security | RT-05.4 |
| SEC-020 | Executor bootstraps via friendly peer votes | Executor counts peers as witnesses; rejected | §2.2.4, §6.3 | C04 | I4 | Rejected with `SELF_EXCLUSION_VIOLATION` | security | UT-C04-007 |
| SEC-021 | Outage declared without two signals | Only one signal crosses threshold; outage not declared; continuation forbidden | §2.2.2, §6.3 | C03, C04, C05 | I4 | No outage; continuation forbidden | security | RT-03.4, RT-03.5 |
| SEC-022 | Outage declared without direct-Brain signal | Two non-direct signals; outage not declared; continuation forbidden | §2.2.2 | C03, C04, C07 | I4 | No outage; continuation forbidden | security | RT-03.6 |
| SEC-023 | Continuation exceeds duration via clock rollback | Executor manipulates clock to extend `max_continuation_duration`; monotonic clock prevents | §2.8, §6.3 | C14, C02 | I5, I14 | Extension prevented; monotonic clock used | security | RES-011 |
| SEC-024 | Continuation exceeds operation count | Executor attempts more than `max_continuation_operations`; rejected | §2.4 | C02, C08 | I5 | Rejected with `OPERATION_COUNT_EXCEEDED` | security | RT-06.2 |
| SEC-025 | Class 3 effect during continuation | Class 3 effect attempted during continuation; rejected; security event; manual review | §2.9, §6.3 | C02, C13, C11, C12 | I15 | Rejected; security event; manual review | security | RT-16.4 |
| SEC-026 | Pinned policy exploited for new classes | Pinned policy snapshot used to authorize class/operation not in capability; rejected | §2.11, §6.3 | C02, C07 | I12 | Rejected with `NOT_PERMITTED_BY_CAPABILITY` | security | UT-C07-004 |
| SEC-027 | Stale revocation knowledge exploited | Executor uses stale revocation cache to continue; watermark below required; rejected | §2.10, §6.3 | C06, C02 | I13 | Rejected with `WATERMARK_BELOW_REQUIRED` or `REVOCATION_CACHE_STALE` | security | RT-07.4 |
| SEC-028 | Silent continuation (no report) | Executor continues but does not report; Brain detects missing report; flagged | §2.6.2, §6.3 | C09, C10, C11 | I6, I7 | Missing report detected; executor flagged; `INVALID_CONTINUATION` | security | RT-09.1 |
| SEC-029 | Receipt tampering | Receipt modified after creation; Brain detects; rejected | §2.6.2, §2.13 | C09, C12 | I6 | Modification detected; rejected | security | UT-C09-003 |
| SEC-030 | Outage evidence missing | Effect produced without outage evidence; downstream rejects | §2.1.4, §6.3 | C09, C13 | I6 | Rejected with `OUTAGE_EVIDENCE_MISSING` | security | RT-09.6 |
| SEC-031 | Outage evidence mismatch | Outage evidence `capability_id` does not match effect; rejected | §2.1.4 | C09, C13 | I6 | Rejected with `OUTAGE_EVIDENCE_MISMATCH` | security | RT-09.7 |
| SEC-032 | Executor lies about continuation outcome | Executor fabricates result; result digest mismatch with journal; detected | §2.6.3, §6.3 | C09, C10, C08 | I6, I8 | Mismatch detected; manual review; executor flagged | security | CHS-005 |

---

## 10. Replay and Recovery Tests

| Test ID | Test Name | Description | ADR Ref | Components | Invariants | Pass/Fail Criteria | Type | Dependencies |
|---|---|---|---|---|---|---|---|---|
| REC-001 | Brain-authorized replay after reconciliation | Reconciliation complete; Brain authorizes replay; new lease; new execution identity; effect identity uses root_command_id | §2.7 | C10, C01, C13, C12 | I10 | Replay authorized; root_command_id used; dedup works | integration | INT-013 |
| REC-002 | Replay not authorized during continuation | Executor attempts autonomous replay during continuation; rejected | §2.7 | C01, C05 | I4, I10 | Replay rejected with `REPLAY_NOT_AUTHORIZED` | unit | — |
| REC-003 | Replay not authorized before reconciliation | Replay attempted before reconciliation complete; rejected | §2.7 | C10, C01 | I7, I10 | Rejected with `RECONCILIATION_REQUIRED` | integration | INT-013 |
| REC-004 | Replay creates new command record | Replay creates new command record; linked to original via causation; original marked `REPLAYED` | §2.7 | C01, C12 | I10, I11 | New record created; causation link present; original marked `REPLAYED` | integration | REC-001 |
| REC-005 | Replay effect identity uses root_command_id | Replay operation derives identity from `root_command_id`, not replay command ID | §2.7, §2.5 | C13 | I10 | `root_command_id` used; dedup against original effects | integration | REC-001 |
| REC-006 | Replay after failed continuation | Continuation failed; reconciled; Brain authorizes replay; replay succeeds | §2.7 | C10, C01, C13 | I7, I10 | Replay succeeds; effects applied with dedup | integration | REC-001 |
| REC-007 | Replay after conflicting continuations | Conflicting continuations; manual review resolves; Brain authorizes replay; replay with correct effect identity | §2.7, §2.12 | C10, C11, C01, C13 | I8, I10 | Manual review resolves; replay authorized; dedup works | integration | INT-011, REC-001 |
| REC-008 | Recovery detection: confirmation period | Brain available for `brain_recovery_confirmation_period`; recovery declared | §2.6.1, §2.15 | C03, C14 | I7 | Recovery declared after confirmation; signed | integration | INT-008 |
| REC-009 | Recovery notification via heartbeat | Executors notified via heartbeat; notification signed | §2.6.1, §2.15 | C03, C14 | I7 | Notification received; signature verifies | integration | REC-008 |
| REC-010 | In-progress operation atomicity: committed | Committed/irreversible operation finished and reported | §2.15 | C10, C08, C09 | I7, I8 | Committed op finished; reported; audited | integration | RES-013 |
| REC-011 | In-progress operation atomicity: uncommitted | Uncommitted operation aborted; no effect | §2.15 | C10, C08 | I7 | Uncommitted op aborted; no effect; audited | integration | RES-013 |
| REC-012 | No double-action on recovery | Same operation never both finished and aborted | §2.15 | C10, C08 | I7, I8 | No double-action for any operation | integration | REC-010, REC-011 |
| REC-013 | Report collection within deadline | All reports collected within `completion_report_deadline` | §2.6.2, §2.15 | C09, C10 | I7 | All reports received; late reports flagged | integration | REC-008 |
| REC-014 | Policy refresh after recovery | Executors refresh policy snapshots and revocation watermarks before new work | §2.15 | C07, C06, C05 | I12, I13 | Refresh complete; no new work until refreshed | integration | REC-008 |
| REC-015 | Audit completion after recovery | All continuation events finalized in ledger | §2.15, §2.13 | C12 | I11 | All events in ledger; no gaps | integration | REC-008 |
| REC-016 | Gate evaluation after certification | Gate remains BLOCKED until all certification tests pass | §2.15, §13 | C12 | I11 | Gate BLOCKED until certification complete | certification | All CERT-* |
| REC-017 | Replay with unreconciled effects blocks | Unknown or unreconciled effect status blocks replay | §2.7 | C10, C13 | I7, I10 | Replay blocked with `RECONCILIATION_REQUIRED` | integration | INT-013 |
| REC-018 | Replay requires compensation first | Some effects already applied; replay requires compensation for reversible effects first | §2.7, §2.6.3.3 | C10, C13 | I10 | Compensation before replay; dedup works | integration | INT-012, REC-001 |

---

## 11. Multi-Tenant Isolation Tests

| Test ID | Test Name | Description | ADR Ref | Components | Invariants | Pass/Fail Criteria | Type | Dependencies |
|---|---|---|---|---|---|---|---|---|
| MT-001 | Tenant A continuation does not affect tenant B | Tenant A continues; tenant B operations unaffected | §2.14 | C02, C10, C13 | I9 | Tenant B unaffected; no cross-tenant effects | integration | INT-018 |
| MT-002 | Tenant A capability rejected in tenant B | Capability for tenant A used in tenant B; rejected | §2.14 | C02, C13 | I9 | Rejected with `TENANT_MISMATCH` | security | SEC-011 |
| MT-003 | Tenant A revocation not visible to tenant B | Revocation stream partitioned; tenant B cannot see tenant A entries | §2.14 | C06 | I9 | Cross-tenant entries not visible | security | SEC-014 |
| MT-004 | Tenant A witness cannot declare for tenant B | Witness for tenant A issues statement about tenant B; rejected | §2.14 | C04 | I9 | Rejected with `WITNESS_TENANT_MISMATCH` | security | SEC-013 |
| MT-005 | Per-tenant continuation limits independent | Tenant A: 5m duration; tenant B: 2m; limits enforced independently | §2.14, §2.4 | C02 | I5, I9 | Each tenant's limits enforced separately | integration | RT-06.1 |
| MT-006 | Per-tenant rate limits independent | Tenant A rate-limited; tenant B unaffected | §2.14, §2.4 | C02 | I5, I9 | Tenant A limited; tenant B proceeds | integration | RT-06.6 |
| MT-007 | Continuation reports routed to correct partition | Tenant A report routed to tenant A partition; not tenant B | §2.14 | C10 | I9 | Correct routing; cross-tenant routing rejected | integration | INT-018 |
| MT-008 | Tenant policy disables continuation | Tenant sets `continuation_class = STOP`; no continuations | §2.14 | C02, C07 | I9, I4 | All continuations rejected with `TENANT_POLICY_STOP` | integration | RT-12.8 |
| MT-009 | Cross-tenant continuation is security event | Any cross-tenant attempt logged as security event | §2.14 | C12 | I9 | Security event logged with full context | security | SEC-012 |
| MT-010 | Per-tenant configuration of all 18 settings | Each tenant configures all 18 settings independently; no cross-tenant influence | §2.4, §2.14, §9.2 | C02, C03, C04, C06, C07, C14 | I5, I9 | All settings per-tenant; no cross-tenant influence | integration | All RT-06.* |
| MT-011 | Concurrent continuations across tenants | Multiple tenants continue simultaneously; isolation maintained | §2.14 | C02, C10, C13 | I5, I9 | All tenants isolated; no cross-tenant effects | integration | MT-001 |
| MT-012 | Tenant-scoped audit events | Audit events scoped to tenant; cross-tenant audit access rejected | §2.14, §2.13 | C12 | I9, I11 | Audit events tenant-scoped; cross-tenant access rejected | security | UT-C12-* |

---

## 12. Certification Tests

Certification tests are end-to-end tests that validate acceptance criteria for gate unblocking. They run only after all other test categories pass.

| Test ID | Test Name | Description | ADR Ref | Components | Invariants | Pass/Fail Criteria | Type | Dependencies |
|---|---|---|---|---|---|---|---|---|
| CERT-001 | Full lifecycle: dispatch to terminal state | Complete lifecycle: dispatch → lease → work → expiry → outage → continuation → receipt → recovery → reconciliation → terminal state; all events audited | §2.1–§2.15 | All | I1–I15 | All states transitioned correctly; all events in audit; terminal state reached | certification | All RT-*, INT-* |
| CERT-002 | Full lifecycle with continuation and recovery | Lifecycle with successful continuation; recovery; reconciliation; VALID_CONTINUATION classification | §2.1–§2.15 | All | I1–I15 | Continuation succeeds; recovery works; classification correct | certification | CERT-001, INT-006–INT-013 |
| CERT-003 | Full lifecycle with split-brain resolution | Two executors continue; split-brain detected; conflict resolution; manual review or dedup | §2.12 | C10, C11, C13, C09, C14, C12 | I8, I10 | Split-brain detected; resolved correctly; no silent resolution | certification | CHS-007, CHS-008 |
| CERT-004 | Full lifecycle with replay | Continuation fails; reconciliation; replay authorized; replay succeeds; effect identity preserved | §2.7 | C10, C01, C13, C12 | I7, I10 | Replay succeeds; root_command_id used; dedup works | certification | REC-001–REC-007 |
| CERT-005 | All 15 invariants verified | Every invariant (I1–I15) verified by at least one passing test | §7 | All | I1–I15 | All invariants verified; no violations | certification | All tests |
| CERT-006 | All 20 acceptance criteria satisfied | Every acceptance criterion (AC1–AC20) verified by at least one passing test | §11 | All | I1–I15 | All ACs satisfied | certification | All tests |
| CERT-007 | All 16 required tests pass | All 16 Section 9.3 required tests pass | §9.3 | All | I1–I15 | All 16 required tests pass | certification | All RT-* |
| CERT-008 | All 14 components tested | All 14 Section 9.1 components have passing unit tests | §9.1 | All | I1–I15 | All 14 components tested | certification | All UT-* |
| CERT-009 | All 18 configuration settings exercised | All 18 Section 9.2 settings exercised by at least one test | §9.2 | C02, C03, C04, C06, C07, C14 | I5, I13, I14 | All settings exercised | certification | All tests |
| CERT-010 | Audit chain complete and never truncated | Full lifecycle audit chain verified; authoritative storage never truncated | §2.13 | C12 | I11 | Chain complete; no truncation | certification | RT-14.*, INT-016 |
| CERT-011 | Tenant isolation across full lifecycle | Full lifecycle for two tenants; isolation maintained throughout | §2.14 | All | I9 | Isolation maintained; no cross-tenant effects | certification | All MT-* |
| CERT-012 | Security: all attack vectors blocked | All security tests pass; no attack vector succeeds | §6.3 | All | I1–I15 | All security tests pass | certification | All SEC-* |
| CERT-013 | Resilience: all failure modes handled | All resilience tests pass; safe behavior under failure | §2.8, §2.12, §2.15 | All | I5, I7, I8, I14 | All resilience tests pass | certification | All RES-* |
| CERT-014 | Chaos: system stable under random failures | All chaos tests pass; system degrades safely | §2.2.4, §2.12 | All | I4, I8 | All chaos tests pass | certification | All CHS-* |
| CERT-015 | Time authority verified end-to-end | Signed anchors, monotonic bounds, skew/rollback handling all verified | §2.8 | C14, C01, C02, C06 | I14 | All time authority tests pass | certification | RT-15.*, RES-009–RES-012 |
| CERT-016 | Side-effect class enforcement verified end-to-end | Class 0–2 succeed; Class 3 prohibited; downstream validates | §2.9 | C02, C13, C10, C11 | I15 | All class enforcement tests pass | certification | RT-16.*, INT-017 |
| CERT-017 | Gate remains BLOCKED until certification complete | `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE` remains BLOCKED until all CERT tests pass | §13 | C12 | I11 | Gate BLOCKED; unblocking only after all CERT pass | certification | All CERT-* |
| CERT-018 | Non-goals verified: no implementation, no deployment, no authority activation | Verify that no runtime code was deployed, no authority activated, no gate unblocked by tests alone | §10, §13 | — | — | No deployment; no authority activation; gate still BLOCKED | certification | All tests |

---

## 13. Test Coverage Matrix: Tests to Acceptance Criteria (Section 11)

This matrix maps each acceptance criterion to the tests that verify it.

| AC | Description (abbreviated) | Primary Tests | Supporting Tests |
|---|---|---|---|
| AC1 | Lease + capability lifecycle separated | RT-01.*, UT-C01-*, UT-C02-* | INT-001, INT-002, CERT-001 |
| AC2 | Capability unusable before expiry; bounded | RT-02.*, UT-C02-001–UT-C02-003 | SEC-006, INT-001, CERT-001 |
| AC3 | Outage detection: 2 signals + direct + grace | RT-03.*, UT-C03-*, UT-C04-* | INT-003, INT-004, SEC-021, SEC-022, CERT-001 |
| AC4 | Witness trust model: identity, quorum, replay, self-exclusion | RT-04.*, UT-C04-* | CHS-003, CHS-004, SEC-020, CERT-001 |
| AC5 | Eligibility explicit; default STOP | RT-05.*, UT-C05-003, UT-C05-004 | INT-005, SEC-019, CERT-001 |
| AC6 | Continuation limits with platform/tenant bounds | RT-06.*, UT-C02-015, UT-C02-016 | MT-005, MT-006, CHS-017, CHS-018, CERT-001 |
| AC7 | Stable effect identity for dedup | RT-08.*, UT-C13-001, UT-C13-002 | INT-007, SEC-010, CERT-001 |
| AC8 | Replay semantics: effect identity + reconciliation first | REC-001–REC-007, RT-08.07, RT-08.10 | INT-013, CERT-004 |
| AC9 | Reconciliation: 4 concerns separated | RT-10.*, UT-C10-* | INT-009–INT-013, CERT-001 |
| AC10 | Receipts mandatory, signed, immutable | RT-09.*, UT-C09-* | SEC-028, SEC-029, CERT-001 |
| AC11 | Split-brain: detect, freeze, manual review | RT-11.*, UT-C11-* | CHS-007–CHS-010, CERT-003 |
| AC12 | Audit chain complete; never truncated | RT-14.*, UT-C12-* | INT-016, SEC-015–SEC-018, CERT-010 |
| AC13 | Tenant isolation throughout | RT-12.*, MT-001–MT-012 | SEC-011–SEC-014, INT-018, CERT-011 |
| AC14 | Recovery protocol: detection, collection, reconciliation, refresh | RT-13.*, REC-008–REC-016 | INT-008, RES-013, CERT-001 |
| AC15 | Trusted time: skew, monotonic, signed anchors | RT-15.*, UT-C14-* | RES-009–RES-012, SEC-023, CERT-015 |
| AC16 | Policy snapshot pinned by hash, bounded by time | UT-C07-*, RT-02.09, RT-05.09 | INT-015, SEC-026, CERT-001 |
| AC17 | Revocation watermark + cache-age fail-closed | RT-07.*, UT-C06-* | INT-014, RES-015, SEC-027, CERT-001 |
| AC18 | Side effects classified; Class 3 prohibited | RT-16.*, UT-C13-006 | INT-017, SEC-025, CERT-016 |
| AC19 | Threat model, invariants, glossary, prerequisites complete | CERT-005, CERT-006, CERT-008, CERT-009 | All tests (coverage) |
| AC20 | Non-goals: no implementation, no deployment, no authority | CERT-018 | — |

---

## 14. Test Coverage Matrix: Tests to Invariants (Section 7)

This matrix maps each invariant to the tests that verify it.

| Inv | Invariant (abbreviated) | Primary Tests | Supporting Tests |
|---|---|---|---|
| I1 | No effects without valid lease | UT-C01-001, UT-C01-004–UT-C01-006, SEC-004, SEC-005 | RT-01.*, INT-001, CERT-001 |
| I2 | Expired lease cannot authorize continuation/effects | UT-C01-005, SEC-004, SEC-005 | RT-01.3, RT-05.2, RES-004, CERT-001 |
| I3 | Capability not usable before/after expiry | UT-C02-003, UT-C02-004, SEC-006, SEC-007 | RT-02.2, RT-02.3, CERT-001 |
| I3a | Only latest-lease capability exercisable | UT-C02-009, RT-01.10 | INT-002, INT-020, CHS-016, CERT-001 |
| I4 | Continuation never default | UT-C05-004, RT-05.14, SEC-019, SEC-020, SEC-021, SEC-022 | RT-03.*, RT-04.*, RT-05.*, CERT-001 |
| I5 | Continuation within bounded envelope | RT-06.*, UT-C02-015, UT-C02-016, UT-C08-005 | RES-011, SEC-023, SEC-024, CHS-017, CERT-001 |
| I6 | Every continuation produces signed receipt | RT-09.*, UT-C09-001–UT-C09-003 | SEC-028, SEC-029, SEC-030, SEC-031, CERT-001 |
| I7 | Every continuation reconciled before terminal | RT-10.*, RT-13.*, UT-C10-* | INT-008–INT-013, REC-008–REC-016, CERT-001 |
| I8 | Conflicts/non-reversible never resolve silently | RT-11.*, UT-C11-*, UT-C10-004, UT-C10-006 | CHS-005, CHS-008, CHS-009, SEC-032, CERT-003 |
| I9 | Cross-tenant continuation impossible | RT-12.*, MT-001–MT-012, SEC-011–SEC-014 | INT-018, CERT-011 |
| I10 | Idempotency across continuation/replay/normal | RT-08.*, UT-C13-001, UT-C13-002, UT-C08-001, UT-C08-004 | INT-007, INT-013, SEC-009, SEC-010, REC-001–REC-007, CERT-001 |
| I11 | Audit storage complete, never truncated | RT-14.*, UT-C12-001–UT-C12-007 | INT-016, SEC-015–SEC-018, RES-018, CERT-010 |
| I12 | Policy snapshot bounded to pinned hash | UT-C07-001–UT-C07-004, RT-02.09, RT-05.09 | INT-015, SEC-026, CERT-001 |
| I13 | Revocation knowledge fresh; absence not permission | RT-07.*, UT-C06-001–UT-C06-008 | INT-014, RES-015, SEC-027, CHS-013, CERT-001 |
| I14 | Time not manipulable to extend authority | RT-15.*, UT-C14-001–UT-C14-008 | RES-009–RES-012, SEC-023, CHS-011, CERT-015 |
| I15 | High-risk/irreversible effects prohibited during continuation | RT-16.*, UT-C13-006 | INT-017, SEC-025, RES-014, CERT-016 |

---

## 15. Configuration Settings Coverage Matrix

This matrix maps each of the 18 configuration settings from ADR-MC-001 §9.2 to the tests that exercise it.

| Setting | Tests | Default Value |
|---|---|---|
| `brain_heartbeat_miss_threshold` | RT-03.1, RT-03.2, UT-C03-002, UT-C03-003, INT-003, RES-005, CHS-014 | — |
| `lease_rejection_threshold` | RT-03.1, RT-03.3, RT-01.9, INT-003, INT-004, RES-005 | — |
| `status_query_threshold` | RT-03.2, INT-004 | — |
| `policy_silence_threshold` | RT-03.3, UT-C07-007, INT-004, CHS-014 | — |
| `witness_quorum_size` | RT-04.2, RT-04.3, RT-04.4, UT-C04-008, CHS-003, CHS-004 | — |
| `witness_statement_max_age` | RT-04.6, UT-C04-004 | — |
| `brain_outage_grace_period` | RT-03.7, INT-003, RES-005 | 30s |
| `brain_recovery_confirmation_period` | RT-13.1, REC-008, INT-008 | 10s |
| `max_continuation_duration` | RT-06.1, RT-06.8, UT-C02-015, RES-011, SEC-023, CHS-015 | 5min |
| `max_continuation_operations` | RT-06.2, UT-C02-016, UT-C08-005, SEC-024 | 1 |
| `max_continuation_attempts_per_command` | RT-06.3 | 1 |
| `max_concurrent_continuations_per_executor` | RT-06.4, CHS-017 | 3 |
| `completion_report_deadline` | RT-10.15, RT-13.6, REC-013 | — |
| `tenant_max_continuation_rate` | RT-06.6, CHS-018, MT-006 | 10/min |
| `continuation_capability_max_validity` | RT-06.7, CHS-015 | 24h |
| `max_clock_skew_tolerance` | RT-15.3, UT-C14-002, RES-009, SEC-023 | 5s |
| `max_clock_rollback_tolerance` | RT-15.4, RT-03.9, UT-C14-003, RES-010 | 1s |
| `max_revocation_cache_age` | RT-07.4, UT-C06-006, RES-015, SEC-027 | 5s |

---

## 16. Test Execution Order

Tests must be executed in dependency order. Execution of a later phase requires all prior phases to pass.

| Phase | Category | Tests | Gate |
|---|---|---|---|
| 1 | Unit tests (all components) | All UT-* | All UT-* pass |
| 2 | Required tests (Section 9.3) | All RT-* | All RT-* pass |
| 3 | Integration tests | All INT-* | All INT-* pass |
| 4 | Security tests | All SEC-* | All SEC-* pass |
| 5 | Multi-tenant isolation tests | All MT-* | All MT-* pass |
| 6 | Replay and recovery tests | All REC-* | All REC-* pass |
| 7 | Resilience tests | All RES-* | All RES-* pass |
| 8 | Chaos tests | All CHS-* | All CHS-* pass |
| 9 | Certification tests | All CERT-* | All CERT-* pass → gate evaluation eligible |

---

## 17. Test Summary Statistics

| Category | Test Count |
|---|---|
| Required tests (RT) | 16 tests, 154 test cases |
| Unit tests (UT) | 14 components, 104 test cases |
| Integration tests (INT) | 20 tests |
| Resilience tests (RES) | 20 tests |
| Chaos tests (CHS) | 18 tests |
| Security tests (SEC) | 32 tests |
| Replay and recovery tests (REC) | 18 tests |
| Multi-tenant isolation tests (MT) | 12 tests |
| Certification tests (CERT) | 18 tests |
| **Total** | **396 test cases** |

### Coverage Summary

| Coverage Target | Count | Covered |
|---|---|---|
| ADR §9.3 required tests | 16 | 16/16 (100%) |
| ADR §9.1 required components | 14 | 14/14 (100%) |
| ADR §9.2 configuration settings | 18 | 18/18 (100%) |
| ADR §7 invariants | 15 (16 with I3a) | 16/16 (100%) |
| ADR §11 acceptance criteria | 20 | 20/20 (100%) |

---

## 18. Test Infrastructure Notes

### 18.1 Proposed pytest markers

The following markers should be registered in `pytest.ini` before implementation:

```ini
markers =
    continuation: tests for executor continuation (ADR-MC-001)
    resilience: tests for infrastructure failure scenarios
    chaos: tests for random/adversarial failure scenarios
    security: tests for attack vector prevention
    certification: end-to-end tests for gate unblocking certification
```

### 18.2 Test directory structure (planned)

```
tests/
  continuation/
    __init__.py
    conftest.py                    # Shared fixtures (brain_context, executor_context, etc.)
    unit/
      test_c01_lease_token.py      # UT-C01-*
      test_c02_capability.py       # UT-C02-*
      test_c03_heartbeat.py        # UT-C03-*
      test_c04_witness.py          # UT-C04-*
      test_c05_state_cache.py      # UT-C05-*
      test_c06_revocation.py       # UT-C06-*
      test_c07_policy_snapshot.py  # UT-C07-*
      test_c08_journal.py          # UT-C08-*
      test_c09_receipt.py          # UT-C09-*
      test_c10_reconciliation.py   # UT-C10-*
      test_c11_conflict_queue.py   # UT-C11-*
      test_c12_audit.py            # UT-C12-*
      test_c13_effect_identity.py  # UT-C13-*
      test_c14_time_anchor.py      # UT-C14-*
    required/
      test_rt01_lease_lifecycle.py       # RT-01.*
      test_rt02_capability.py            # RT-02.*
      test_rt03_outage.py               # RT-03.*
      test_rt04_witness.py              # RT-04.*
      test_rt05_eligibility.py          # RT-05.*
      test_rt06_bounds.py               # RT-06.*
      test_rt07_revocation.py           # RT-07.*
      test_rt08_idempotency.py          # RT-08.*
      test_rt09_receipt.py              # RT-09.*
      test_rt10_reconciliation.py        # RT-10.*
      test_rt11_split_brain.py          # RT-11.*
      test_rt12_tenant_isolation.py     # RT-12.*
      test_rt13_recovery.py             # RT-13.*
      test_rt14_audit_completeness.py   # RT-14.*
      test_rt15_time_authority.py       # RT-15.*
      test_rt16_side_effect_class.py    # RT-16.*
    integration/
      test_int01_dispatch.py            # INT-001–INT-020
      ...
    resilience/
      test_res01_crash.py               # RES-001–RES-020
      ...
    chaos/
      test_chs01_random_kill.py        # CHS-001–CHS-018
      ...
    security/
      test_sec01_capability_forgery.py # SEC-001–SEC-032
      ...
    replay_recovery/
      test_rec01_replay.py              # REC-001–REC-018
      ...
    multi_tenant/
      test_mt01_isolation.py           # MT-001–MT-012
      ...
    certification/
      test_cert01_full_lifecycle.py    # CERT-001–CERT-018
      ...
```

### 18.3 Fixture dependencies

```
brain_context
  ├── C01 lease token service (mock)
  ├── C02 capability service (mock)
  ├── C03 heartbeat endpoint (mock)
  ├── C06 revocation stream (mock)
  ├── C07 policy snapshot registry (mock)
  ├── C10 reconciliation engine (mock)
  ├── C11 conflict review queue (mock)
  └── C14 time-anchor service (mock)

executor_context
  ├── C05 local state cache (mock)
  ├── C08 continuation journal (mock)
  └── C09 completion receipt service (mock)

witness_set
  └── N witness nodes (configurable fault behavior)

downstream_mock
  └── C13 effect identity layer (mock)

fault_injector
  ├── process kill
  ├── network partition
  └── clock skew simulation

audit_ledger_spy
  └── C12 audit pipeline (read-only spy)
```

---

## 19. Traceability to Companion Documents

| Companion Document | Relationship |
|---|---|
| `01_IMPLEMENTATION_ARCHITECTURE.md` | Component decomposition, layering, implementation phases — tests map to components defined here |
| `02_COMPONENT_DEPENDENCY_GRAPH.md` | Component dependencies — test dependencies derived from this graph |
| `03_INTERFACE_SPECIFICATIONS.md` | Interface contracts and data models — test assertions check these contracts |
| `04_STATE_MACHINES.md` | State transitions and guards — tests verify state transitions and guard conditions |
| `05_SEQUENCE_DIAGRAMS.md` | Interaction sequences — integration tests follow these sequences |
| `ADR_MC_001_EXECUTOR_CONTINUATION.md` | Source of truth — all tests trace to ADR sections, invariants, and acceptance criteria |

---

## 20. Glossary

| Term | Definition |
|---|---|
| Test case | A single, atomic test with a unique test ID, verifying one or more invariants |
| Test type | The category of test: unit, integration, resilience, chaos, security, certification |
| Invariant | A property that must hold at all times (ADR §7) |
| Acceptance criterion | A condition that must be satisfied for the ADR to be accepted (ADR §11) |
| Pass/fail criteria | The specific conditions that determine whether a test passes or fails |
| Test dependency | A test or component that must exist and pass before this test can run |
| Coverage matrix | A mapping from tests to acceptance criteria or invariants |
| Certification | The process of verifying that all acceptance criteria are met before gate evaluation |
| Fault injection | The deliberate introduction of failures (crash, partition, clock skew) for testing |
| Byzantine fault | A fault where a component behaves arbitrarily, including sending incorrect information |

---

**End of document. This is a planning artifact only. It authorizes no runtime code, no test execution, no deployment, and no authority activation.**