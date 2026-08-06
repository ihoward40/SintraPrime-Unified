# 10 — Rollout and Rollback Plan

**Package:** Executor Continuation Implementation Planning
**Source of truth:** ADR-MC-001 (ACCEPTED, merged to main), Section 9.1 "Required Components"
**Artifact type:** Planning only — no runtime code, no deployment, no authority activation, no Sigma gate unblock
**Scope:** This document defines the phased rollout and rollback strategy for the 14 required components of the executor continuation capability. It covers implementation phases, feature flags, go/no-go gates, rollback procedures, database migration strategy, deployment strategy, monitoring and alerting, incident response, Sigma gate unblocking, and emergency freeze procedures. It does not implement, deploy, or unblock `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE`.
**Companion documents:**
- `01_IMPLEMENTATION_ARCHITECTURE.md` — component decomposition, phases, technology choices
- `02_COMPONENT_DEPENDENCY_GRAPH.md` — build-time dependency graph, layered build order
- `03_INTERFACE_SPECIFICATIONS.md` — Pydantic v2 models and Protocol interfaces
- `04_STATE_MACHINES.md` — component and lifecycle state machines
- `05_SEQUENCE_DIAGRAMS.md` — runtime protocol sequencing

---

## 1. Document Purpose

This document is the rollout and rollback blueprint for the executor continuation capability defined by ADR-MC-001. It is a planning artifact only — it authorizes no runtime code, no API changes, no persistence migrations, and no deployment. Implementation requires separate ADRs, branches, and authorizations per ADR-MC-001 Section 10.

The document serves three audiences:

1. **Release engineers** — who need to know the deployment sequence, feature flag structure, and rollback mechanics.
2. **Operators and SREs** — who need to know the monitoring, alerting, and incident response procedures.
3. **Reviewers and certifiers** — who need to verify that the rollout plan respects the component dependency graph, that each phase has a reversible rollback, and that the Sigma gate cannot be unblocked until all certification gates pass.

### 1.1 Planning Status

- ADR-MC-001 is ACCEPTED and merged to main.
- The 14 required components (ADR-MC-001 §9.1) are NOT IMPLEMENTED.
- The implementation is NOT AUTHORIZED. Implementation requires separate ADRs, branches, and authorizations per ADR-MC-001 Section 10.
- The Sigma gate (`SIGMA_LEASE_EXPIRY_CONTINUATION_GATE`) remains BLOCKED. `portal/services/sigma_gate.py` is unchanged; `is_cancellation_blocked()` continues to return `True`.
- This document describes the rollout and rollback plan that would be executed IF and WHEN implementation is authorized. It is a plan, not an execution.

### 1.2 Key Constraints

- **No upward phase dependencies.** Each phase depends only on phases below it in the dependency graph (document 02, Section 5). Rollout must respect this ordering.
- **No partial Sigma gate unblock.** The Sigma gate transitions to SATISFIED only after all 14 components are implemented AND all certification gates pass (ADR-MC-001 §13). No phase may unblock the gate.
- **Additive only.** The rollout adds a new `portal/continuation/` package. It does not modify existing Mission Control Foundation code (`sigma_gate.py`, `mission_control_command_service.py`, `mission_control.py` router, `mission_control_command.py` model) until the final certification phase.
- **Tenant isolation is mandatory at every phase.** Every component enforces tenant isolation at its boundary. A rollout that breaks tenant isolation is an automatic rollback trigger (Section 8).
- **Fail-closed by default.** Every feature flag defaults to OFF. Every component fails closed when its dependencies are unavailable. No component enters a permissive mode without explicit operator action.

---

## 2. Implementation Phases

The rollout proceeds in five phases, aligned with the component dependency graph (document 02, Section 5) and the implementation architecture (document 01, Section 6). Each phase produces a testable, deployable (in staging) increment. No phase unblocks the Sigma gate.

### 2.1 Phase Summary

| Phase | Name | Components | Depends On | Rollout Target |
|---|---|---|---|---|
| 0 | Foundation | C14, C12, C7, C5 | (nothing) | Staging only |
| 1 | Authority & Revocation | C1, C6, C2 | Phase 0 | Staging only |
| 2 | Outage Detection | C3, C4 | Phase 1 | Staging only |
| 3 | Continuation Execution | C8, C9, C13 | Phase 2 | Staging only |
| 4 | Reconciliation & Recovery | C10, C11 | Phase 3 | Staging → Canary → Production (certification-gated) |

### 2.2 Phase Detail

Each phase below specifies: components, build order, feature flags, go/no-go gate criteria, and rollback procedure. The detailed rollback procedures are consolidated in Section 5; this section focuses on phase entry and exit criteria.

#### Phase 0 — Foundation

**Goal:** Build the foundational services that all other components depend on.

**Components:** C14 (Signed Time-Anchor Service), C12 (Audit Event Pipeline), C7 (Policy Snapshot Registry), C5 (Executor Local State Cache).

**Build order:** All four can be built in parallel. None depends on another Phase 0 component.

**Feature flags:**
- `CONTINUATION_FOUNDATION_ENABLED` — master flag for Phase 0 components. Default: `false`.
- `CONTINUATION_TIME_ANCHOR_ENABLED` — enables C14 endpoints. Default: `false`.
- `CONTINUATION_AUDIT_PIPELINE_ENABLED` — enables C12 append path. Default: `false`.
- `CONTINUATION_POLICY_SNAPSHOT_ENABLED` — enables C7 registry. Default: `false`.
- `CONTINUATION_LOCAL_STATE_CACHE_ENABLED` — enables C5 cache. Default: `false`.

**Go/No-Go gate (Phase 0 → Phase 1):**
- All four components pass unit tests covering their interface contracts.
- All four components enforce tenant isolation at their boundaries.
- C14 issues and validates signed time anchors; skew and rollback checks produce correct security events.
- C12 appends hash-chained events; causation chain projection paginates without truncating authoritative storage.
- C7 pins and validates policy snapshots by hash; expired snapshots are rejected.
- C5 stores and retrieves command inputs and step outputs; sufficiency check correctly reports missing inputs.
- No existing CI checks regress (all 12 checks pass).
- No production traffic is routed to Phase 0 components (staging only).

#### Phase 1 — Authority & Revocation

**Goal:** Build the authority chain that gates all continuation: leases, revocation, and capabilities.

**Components:** C1 (Signed Lease Token Service), C6 (Revocation Stream), C2 (Continuation Capability Service).

**Build order:** C1 and C6 in parallel; C2 after both (C2 depends on C1 and C6).

**Feature flags:**
- `CONTINUATION_AUTHORITY_ENABLED` — master flag for Phase 1 components. Default: `false`.
- `CONTINUATION_LEASE_SERVICE_ENABLED` — enables C1 endpoints. Default: `false`.
- `CONTINUATION_REVOCATION_STREAM_ENABLED` — enables C6 publish/read. Default: `false`.
- `CONTINUATION_CAPABILITY_SERVICE_ENABLED` — enables C2 endpoints. Default: `false`.

**Go/No-Go gate (Phase 1 → Phase 2):**
- C1 issues, renews, and revokes signed lease tokens; `validate_lease` rejects expired, revoked, tenant-mismatched, and clock-skewed tokens.
- C1 renewal supersedes prior continuation capabilities (Invariant 3a); superseded capability IDs are recorded.
- C6 publishes a signed, monotonic, tenant-partitioned revocation stream; `latest_watermark` and `cache_age` are correct.
- C2 issues, validates, and revokes signed continuation capabilities; `validate_capability` rejects before `not_valid_before`, after `not_valid_after`, superseded, revoked, tenant-mismatched, or lease-still-active capabilities.
- C2 rejects `CLASS_3` capability issuance at issue time (Invariant 15).
- All ADR invariants 1, 2, 3, 3a, 4, 12, 13, 15 are enforced at the interface boundary.
- Integration tests cover C1↔C2 and C6↔C2 interactions.
- No existing CI checks regress.

#### Phase 2 — Outage Detection

**Goal:** Build the mechanisms that allow executors to detect Brain unavailability robustly.

**Components:** C3 (Brain Heartbeat Endpoint), C4 (Witness Statement Service).

**Build order:** C3 and C4 in parallel. Both depend only on Phase 0 and Phase 1 components.

**Feature flags:**
- `CONTINUATION_OUTAGE_DETECTION_ENABLED` — master flag for Phase 2. Default: `false`.
- `CONTINUATION_HEARTBEAT_ENABLED` — enables C3 endpoint. Default: `false`.
- `CONTINUATION_WITNESS_STATEMENTS_ENABLED` — enables C4 publish/validate. Default: `false`.

**Go/No-Go gate (Phase 2 → Phase 3):**
- C3 returns `OK`, `DEGRADED`, or `UNAVAILABLE` status with a fresh `SignedTimeAnchor` and current `revocation_watermark`.
- C3 heartbeat responses are tenant-scoped; cross-tenant probing is a security event.
- C4 publishes and validates signed witness statements; `validate_statement` rejects stale, replayed, revoked-key, self-exclusion-violating, and tenant-mismatched statements.
- C4 `collect_quorum` assembles quorum with BFT or CFT fault model; `witness_quorum_size < N` is enforced.
- The two-signal outage detection rule (ADR 2.2.2) is testable using C3 and C4 outputs.
- Witness statements alone are never sufficient to declare outage (ADR 2.2.2).
- No existing CI checks regress.

#### Phase 3 — Continuation Execution

**Goal:** Build the executor-side components that perform and record continuation work, plus downstream effect validation.

**Components:** C8 (Continuation Journal Store), C9 (Completion Receipt Service), C13 (Downstream Effect Identity Layer).

**Build order:** C8 → C9 → C13 (serial, due to direct dependencies).

**Feature flags:**
- `CONTINUATION_EXECUTION_ENABLED` — master flag for Phase 3. Default: `false`.
- `CONTINUATION_JOURNAL_ENABLED` — enables C8. Default: `false`.
- `CONTINUATION_RECEIPT_ENABLED` — enables C9. Default: `false`.
- `CONTINUATION_EFFECT_IDENTITY_ENABLED` — enables C13. Default: `false`.

**Go/No-Go gate (Phase 3 → Phase 4):**
- C8 appends immutable, hash-chained journal entries; `seal` produces a tamper-evident seal signature; append after seal is rejected.
- C8 journal entries always use `root_command_id` in `StableEffectIdentity`, never a replay-attempt command ID (ADR 2.5.1).
- C9 generates signed receipts with valid outage evidence bundles; `verify_receipt` rejects missing, mismatched, or watermark-below-required evidence.
- C9 enforces mandatory reporting regardless of `final_state` (ADR 2.6.2).
- C13 `check_effect` identifies duplicates by `(root_command_id, operation_id, side_effect_slot)`.
- C13 refuses Class 3 effects during continuation (ADR 2.9, Invariant 15).
- C13 requires valid matching outage evidence; a capability alone is not sufficient (ADR 2.1.4).
- All ADR invariants 5, 6, 10, 15 are enforced at the interface boundary.
- No existing CI checks regress.

#### Phase 4 — Reconciliation & Recovery

**Goal:** Build the Brain-side components that reconcile continuation reports, resolve conflicts, and authorize replays.

**Components:** C10 (Reconciliation Engine), C11 (Conflict Review Queue).

**Build order:** C10 → C11 (serial; C11 depends on C10 to populate the queue).

**Feature flags:**
- `CONTINUATION_RECONCILIATION_ENABLED` — master flag for Phase 4. Default: `false`.
- `CONTINUATION_RECONCILIATION_ENGINE_ENABLED` — enables C10. Default: `false`.
- `CONTINUATION_CONFLICT_QUEUE_ENABLED` — enables C11. Default: `false`.

**Go/No-Go gate (Phase 4 → Certification):**
- C10 `submit_report` accepts completion reports and rejects duplicates by `(command_id, continuation_id)`.
- C10 `reconcile_command` performs result selection, effect reconciliation, compensation, and manual-review routing per ADR 2.6.3.
- C10 result selection by timestamp is permitted only when all reported effects are provably idempotent and equivalent (ADR 2.6.3.1).
- C10 `detect_conflicts` identifies divergent result digests and conflicting effect identities.
- C10 `authorize_replay` blocks replay while continuations are unreconciled or effects are unresolved; replay uses `root_command_id` for effect identities (ADR 2.7).
- C11 enqueues conflicts from C10; the command remains in `MANUAL_REVIEW_REQUIRED` until an authorized operator resolves it.
- C11 resolution is recorded as an audit event; no silent conflict resolution.
- All ADR invariants 7, 8 are enforced at the interface boundary.
- The full recovery protocol (ADR 2.15) is testable end-to-end.
- No existing CI checks regress.

---

## 3. Feature Flags and Configuration Controls

### 3.1 Flag Hierarchy

Feature flags are organized in a three-level hierarchy. A parent flag must be ON before any child flag has effect. All flags default to `false` (fail-closed).

```
CONTINUATION_MASTER_ENABLED (global kill switch)
├── CONTINUATION_FOUNDATION_ENABLED
│   ├── CONTINUATION_TIME_ANCHOR_ENABLED      (C14)
│   ├── CONTINUATION_AUDIT_PIPELINE_ENABLED   (C12)
│   ├── CONTINUATION_POLICY_SNAPSHOT_ENABLED  (C7)
│   └── CONTINUATION_LOCAL_STATE_CACHE_ENABLED (C5)
├── CONTINUATION_AUTHORITY_ENABLED
│   ├── CONTINUATION_LEASE_SERVICE_ENABLED     (C1)
│   ├── CONTINUATION_REVOCATION_STREAM_ENABLED (C6)
│   └── CONTINUATION_CAPABILITY_SERVICE_ENABLED (C2)
├── CONTINUATION_OUTAGE_DETECTION_ENABLED
│   ├── CONTINUATION_HEARTBEAT_ENABLED         (C3)
│   └── CONTINUATION_WITNESS_STATEMENTS_ENABLED (C4)
├── CONTINUATION_EXECUTION_ENABLED
│   ├── CONTINUATION_JOURNAL_ENABLED            (C8)
│   ├── CONTINUATION_RECEIPT_ENABLED            (C9)
│   └── CONTINUATION_EFFECT_IDENTITY_ENABLED    (C13)
└── CONTINUATION_RECONCILIATION_ENABLED
    ├── CONTINUATION_RECONCILIATION_ENGINE_ENABLED (C10)
    └── CONTINUATION_CONFLICT_QUEUE_ENABLED        (C11)
```

### 3.2 Flag Semantics

| Flag | Type | Default | Effect when `false` |
|---|---|---|---|
| `CONTINUATION_MASTER_ENABLED` | Boolean | `false` | All continuation endpoints return `503 Service Unavailable`. All component code paths short-circuit. This is the global kill switch. |
| `CONTINUATION_FOUNDATION_ENABLED` | Boolean | `false` | Phase 0 endpoints return `503`. C14, C12, C7, C5 are inert. |
| `CONTINUATION_AUTHORITY_ENABLED` | Boolean | `false` | Phase 1 endpoints return `503`. C1, C6, C2 are inert. |
| `CONTINUATION_OUTAGE_DETECTION_ENABLED` | Boolean | `false` | Phase 2 endpoints return `503`. C3, C4 are inert. |
| `CONTINUATION_EXECUTION_ENABLED` | Boolean | `false` | Phase 3 endpoints return `503`. C8, C9, C13 are inert. |
| `CONTINUATION_RECONCILIATION_ENABLED` | Boolean | `false` | Phase 4 endpoints return `503`. C10, C11 are inert. |
| Per-component flags | Boolean | `false` | The specific component's endpoints return `503`; other components in the same phase may continue if their flags are ON. |

### 3.3 Configuration Transport

Feature flags are delivered via the existing `portal/config.py` `Settings` class (Pydantic v2 `BaseSettings`), sourced from environment variables. This is consistent with the existing portal configuration pattern and requires no new infrastructure.

- **Environment variable naming:** `CONTINUATION_MASTER_ENABLED`, `CONTINUATION_FOUNDATION_ENABLED`, etc. (uppercase, underscore-separated, matching `pydantic-settings` convention).
- **Runtime update:** Flags are read at request time from the `Settings` instance, not cached at startup. This allows flag changes to take effect without a restart, supporting rapid rollback.
- **Audit:** Every flag read is logged via structlog with the flag name, value, and request correlation ID. Flag changes are themselves audit events via C12.
- **Tenant scoping:** Flags are platform-global in the initial rollout. Per-tenant flag overrides are a future enhancement, not part of this plan.

### 3.4 Platform Maximums (ADR-MC-001 §9.2)

The 18 Section 9.2 configuration settings (e.g., `max_continuation_duration`, `max_revocation_watermark_age`, `witness_quorum_size`) are delivered as `Settings` fields with platform maximums enforced in code. A tenant-configured value that exceeds the platform maximum is clamped, and the clamping is logged as a security event. These settings are NOT feature flags; they are runtime parameters that govern component behavior when the corresponding feature flag is ON.

---

## 4. Rollout Sequence with Go/No-Go Gates

### 4.1 Rollout Timeline

The timeline below shows phase dependencies and the serial gating between phases. Within a phase, parallel components may overlap. Phases do not overlap: Phase N+1 cannot begin until Phase N passes its go/no-go gate.

```
Week  1   2   3   4   5   6   7   8   9  10  11  12  13  14  15  16
      |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
P0:   [======= Phase 0 (Foundation) =======]
                                      GATE 0→1
P1:                                   [=== Phase 1 (Authority) ===]
                                                  GATE 1→2
P2:                                                [== Phase 2 ==]
                                                           GATE 2→3
P3:                                                         [=== Phase 3 ===]
                                                                     GATE 3→4
P4:                                                                   [== Phase 4 ==]
                                                                               GATE 4→CERT
CERT:                                                                              [== Certification ==]
                                                                                            SIGMA GATE UNBLOCK
```

**Notes on the timeline:**
- Durations are planning estimates for a single-engineer sequential implementation. Parallelism within a phase compresses the timeline proportionally.
- The timeline is staging-only through Phase 4. Production rollout begins only after certification (Section 9).
- Gates are hard stops: Phase N+1 does not begin until the gate is passed. A failed gate triggers either remediation (stay in the current phase) or rollback (Section 5).

### 4.2 Go/No-Go Gate Procedure

Each go/no-go gate follows this procedure:

1. **Pre-gate review (T-2 days):** The implementation team presents the phase exit criteria evidence to the review board. Evidence includes: test results, invariant enforcement matrix, tenant isolation test results, and a regression report for all 12 CI checks.
2. **Gate decision (T-0):** The review board issues one of three decisions:
   - **GO** — all exit criteria met, proceed to next phase.
   - **HOLD** — one or more exit criteria not met, remediate and re-present. The phase does not advance.
   - **ROLLBACK** — a critical defect is found that cannot be remediated in-phase. Execute the phase rollback procedure (Section 5).
3. **Post-gate record:** The gate decision, evidence, and signatures are recorded as an audit event via C12 (once C12 is operational) or in the planning record (before C12 is operational).

### 4.3 Gate Authority

Gate decisions require authorization from:
- The implementation lead (technical readiness).
- The review board representative (ADR compliance).
- The operator/SRE representative (operational readiness, from Phase 1 onward).

No single role may unilaterally advance a phase. No automated check may unilaterally advance a phase; automation provides evidence, humans make the decision.

---

## 5. Rollback Procedures

### 5.1 Rollback Principles

1. **Feature-flag-first rollback.** The first rollback action for any phase is to set the phase's master feature flag to `false`. This takes effect at the next request (no restart required) and renders all phase components inert.
2. **Data preservation by default.** Rollback does not delete data. Immutable stores (C12 audit ledger, C8 journal) are never truncated. Mutable stores (C5 cache, C7 registry) are retained for forensic analysis. Database migrations are rolled back via the backward migration (Section 7), not by deleting tables.
3. **No silent rollback.** Every rollback is recorded as an audit event (via C12 if operational, or in the incident record otherwise). The rollback reason, scope, timestamp, and authorizer are recorded.
4. **Dependency-aware rollback.** Rolling back Phase N requires rolling back Phases N+1..4 first, because higher phases depend on lower phases. The rollback order is reverse-phase: 4 → 3 → 2 → 1 → 0.
5. **Existing code is untouched.** Rollback of continuation components does not affect existing Mission Control Foundation code. `sigma_gate.py`, `mission_control_command_service.py`, and the existing router/models continue to operate unchanged.

### 5.2 Per-Phase Rollback Procedures

#### Phase 0 Rollback

- **Disable:** Set `CONTINUATION_FOUNDATION_ENABLED=false`. Set all four child flags to `false`.
- **Effect:** C14, C12, C7, C5 endpoints return `503`. No phase-1+ component can function (they depend on Phase 0), so all higher phases are implicitly disabled.
- **Data to preserve:** C12 audit ledger (immutable, never truncated), C7 policy snapshots (retained for forensic analysis), C5 cache contents (retained until explicit cleanup).
- **Database:** Run the Phase 0 backward migration (Section 7.3) to drop the Phase 0 tables. This is optional — tables may be retained in a dormant state if preferred.
- **Cleanup:** No automatic cleanup. Tables and data are retained for forensic analysis. Explicit cleanup requires operator authorization and is recorded as an audit event.
- **Estimated time to effect:** < 1 minute (flag change propagates at next request).

#### Phase 1 Rollback

- **Prerequisite:** Phase 2, 3, 4 must be rolled back first (reverse-phase order).
- **Disable:** Set `CONTINUATION_AUTHORITY_ENABLED=false`. Set all three child flags to `false`.
- **Effect:** C1, C6, C2 endpoints return `503`. No new leases, revocations, or capabilities are issued. Existing signed tokens remain valid until their natural expiry (they are cryptographically signed and self-validating); the rollback prevents issuance, not validation of already-issued tokens.
- **Data to preserve:** C1 lease token records, C6 revocation stream entries (immutable, monotonic — never truncated), C2 capability records.
- **Database:** Run the Phase 1 backward migration. Optional table retention is permitted.
- **Estimated time to effect:** < 1 minute.

#### Phase 2 Rollback

- **Prerequisite:** Phase 3, 4 must be rolled back first.
- **Disable:** Set `CONTINUATION_OUTAGE_DETECTION_ENABLED=false`. Set both child flags to `false`.
- **Effect:** C3 heartbeat endpoint returns `503`. C4 witness statement endpoints return `503`. Executors can no longer detect outages via the continuation subsystem (they fall back to existing behavior — no continuation is attempted while the Sigma gate is BLOCKED).
- **Data to preserve:** C4 witness statements (retained for forensic analysis).
- **Database:** Run the Phase 2 backward migration. Optional table retention is permitted.
- **Estimated time to effect:** < 1 minute.

#### Phase 3 Rollback

- **Prerequisite:** Phase 4 must be rolled back first.
- **Disable:** Set `CONTINUATION_EXECUTION_ENABLED=false`. Set all three child flags to `false`.
- **Effect:** C8, C9, C13 endpoints return `503`. No new journal entries, receipts, or effect identity checks occur. Existing journals and receipts remain valid (they are immutable and hash-chained).
- **Data to preserve:** C8 journal store (immutable, hash-chained — never truncated), C9 completion receipts (retained for forensic analysis), C13 effect records (retained to prevent duplicate effects on re-enable).
- **Database:** Run the Phase 3 backward migration. C13 effect records should be retained if there is any chance of re-enabling, to prevent duplicate external effects.
- **Estimated time to effect:** < 1 minute.

#### Phase 4 Rollback

- **Disable:** Set `CONTINUATION_RECONCILIATION_ENABLED=false`. Set both child flags to `false`.
- **Effect:** C10, C11 endpoints return `503`. No new reconciliation or conflict review occurs. Existing conflict queue entries remain in `MANUAL_REVIEW_REQUIRED` state.
- **Data to preserve:** C10 reconciliation records, C11 conflict queue entries (retained for forensic analysis and for manual resolution on re-enable).
- **Database:** Run the Phase 4 backward migration. Optional table retention is permitted.
- **Estimated time to effect:** < 1 minute.

### 5.3 Full Rollback (All Phases)

A full rollback returns the system to its pre-continuation state. Procedure:

1. Set `CONTINUATION_MASTER_ENABLED=false`. This is the global kill switch. All continuation endpoints return `503` immediately.
2. Set all phase master flags to `false` (defensive — in case the master flag is bypassed).
3. Verify all 12 CI checks pass on the rolled-back state.
4. Verify `sigma_gate.py` is unchanged and `is_cancellation_blocked()` returns `True`.
5. Database: run backward migrations in reverse phase order (4 → 3 → 2 → 1 → 0). This is optional if tables are retained dormant.
6. Record the full rollback as an incident (Section 8).

### 5.4 Rollback Decision Tree

```
                        ┌─────────────────────────────┐
                        │  Incident or defect detected │
                        │  in continuation subsystem   │
                        └──────────────┬──────────────┘
                                       │
                        ┌──────────────▼──────────────┐
                        │  Is the defect in a single   │
                        │  component within a phase?   │
                        └──────┬───────────────┬──────┘
                               │ Yes           │ No
                               ▼               ▼
              ┌────────────────────┐  ┌────────────────────┐
              │  Disable the single │  │  Is data integrity  │
              │  component flag     │  │  or tenant isolation│
              │  (child flag)       │  │  compromised?      │
              └────────┬───────────┘  └────┬───────────┬────┘
                       │                   │ Yes       │ No
                       ▼                   ▼           ▼
          ┌────────────────────┐  ┌──────────────┐  ┌────────────────┐
          │  Monitor for 15    │  │  EMERGENCY   │  │  Disable the   │
          │  minutes. Defect   │  │  FREEZE:     │  │  phase master  │
          │  resolved?         │  │  Set MASTER  │  │  flag for the  │
          └──┬────────┬────────┘  │  = false     │  │  affected phase│
             │ Yes    │ No        └──────┬───────┘  └───────┬────────┘
             ▼        ▼                  ▼                  ▼
    ┌────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
    │ Re-enable  │ │ Escalate to  │ │ Full rollback│ │ Monitor for 30   │
    │ the child  │ │ phase master │ │ procedure    │ │ min. Defect      │
    │ flag       │ │ flag rollback│ │ (Section 5.3)│ │ resolved?        │
    └────────────┘ └──────┬───────┘ └──────────────┘ └──┬────────┬──────┘
                          │                            │ Yes    │ No
                          ▼                            ▼        ▼
                ┌──────────────────┐          ┌──────────┐ ┌──────────────┐
                │  Disable the     │          │ Re-enable│ │ Escalate to  │
                │  phase master    │          │ the phase│ │ full rollback│
                │  flag. Monitor   │          │  master  │ │ (Section 5.3)│
                │  for 30 minutes. │          │  flag    │ └──────────────┘
                │  Defect resolved?│          └──────────┘
                └──┬────────┬───────┘
                   │ Yes    │ No
                   ▼        ▼
            ┌──────────┐ ┌──────────────┐
            │ Re-enable│ │ Escalate to  │
            │ the phase│ │ full rollback│
            │  master  │ │ (Section 5.3)│
            │  flag    │ └──────────────┘
            └──────────┘
```

**Decision tree reading guide:**
- Start at the top when any incident or defect is detected in the continuation subsystem.
- The tree prioritizes the smallest-blast-radius rollback first (single component flag), then escalates to phase-level, then to full rollback.
- Data integrity or tenant isolation compromise triggers an immediate emergency freeze (Section 10) regardless of scope.
- "Monitor for N minutes" means: watch the monitoring dashboards (Section 6) for error rate, latency, and invariant violation alerts. If any alert fires, treat as "defect not resolved."

---

## 6. Database Migration Strategy

### 6.1 Migration Principles

1. **Forward-only within a phase, backward-capable across phases.** Each phase has a forward migration (up) and a backward migration (down). The backward migration is tested and verified before the forward migration is applied.
2. **Additive schema changes.** Forward migrations add new tables in the `portal/continuation/` schema namespace. They do not modify existing tables (`mission_control_command`, `audit_log`, etc.). This ensures that rollback of continuation migrations does not affect existing data.
3. **No data migration of existing rows.** The continuation subsystem does not read from or write to existing Mission Control tables. It creates its own tables. Existing data is untouched.
4. **Hash-chained immutable tables are never truncated by migration.** C12 (audit ledger) and C8 (journal store) tables are append-only. The backward migration for these tables drops the table entirely (optional) or leaves it dormant. It never deletes individual rows.
5. **Migrations are gated by feature flags.** A migration may be applied (schema change) while the corresponding feature flag is `false` (no runtime effect). This decouples schema deployment from feature activation.

### 6.2 Migration Tooling

The existing codebase uses SQLAlchemy 2.0 async with Alembic-style migrations (the portal uses `portal/database.py` with `Base` declarative models). Migrations for the continuation subsystem follow the same pattern:

- **Migration files:** `portal/continuation/migrations/versions/NNN_phase_N_description.py`
- **Naming convention:** `NNN` is a zero-padded sequence number. Phase 0 migrations are `001`–`004`, Phase 1 are `005`–`007`, etc.
- **Testing:** Each migration is tested forward and backward in CI as part of the PostgreSQL bootstrap certification check. A migration that cannot be reversed is a gate failure.

### 6.3 Per-Phase Migration Plan

#### Phase 0 Migrations

| Migration | Tables Created | Forward | Backward |
|---|---|---|---|
| 001 | `continuation_time_anchors` | Create table for C14 signed time anchors | Drop table (data lost — acceptable for staging; for production, export first) |
| 002 | `continuation_audit_events` | Create table for C12 audit ledger (append-only, hash-chained) | Drop table (or rename to `continuation_audit_events_archived` for retention) |
| 003 | `continuation_policy_snapshots` | Create table for C7 policy snapshot registry | Drop table |
| 004 | `continuation_local_state_cache` | Create table for C5 executor local state cache | Drop table (cache data is non-critical) |

#### Phase 1 Migrations

| Migration | Tables Created | Forward | Backward |
|---|---|---|---|
| 005 | `continuation_lease_tokens` | Create table for C1 lease token records | Drop table (issued tokens become invalid; acceptable during rollback) |
| 006 | `continuation_revocation_stream` | Create table for C6 revocation stream (append-only, monotonic) | Drop table (or rename for retention) |
| 007 | `continuation_capabilities` | Create table for C2 capability records | Drop table |

#### Phase 2 Migrations

| Migration | Tables Created | Forward | Backward |
|---|---|---|---|
| 008 | `continuation_witness_statements` | Create table for C4 witness statements | Drop table (or rename for retention) |

**Note:** C3 (heartbeat endpoint) is stateless and requires no migration.

#### Phase 3 Migrations

| Migration | Tables Created | Forward | Backward |
|---|---|---|---|
| 009 | `continuation_journal_entries` | Create table for C8 journal store (append-only, hash-chained) | Drop table (or rename for retention — journal is forensic evidence) |
| 010 | `continuation_completion_receipts` | Create table for C9 completion receipts | Drop table (or rename for retention) |
| 011 | `continuation_effect_records` | Create table for C13 downstream effect identity records | **Retain if possible** — dropping this table risks duplicate external effects on re-enable. If drop is required, export the table first and re-import on re-enable. |

#### Phase 4 Migrations

| Migration | Tables Created | Forward | Backward |
|---|---|---|---|
| 012 | `continuation_reconciliation_records` | Create table for C10 reconciliation records | Drop table (or rename for retention) |
| 013 | `continuation_conflict_queue` | Create table for C11 conflict review queue | Drop table (or rename for retention — unresolved conflicts should be preserved for manual resolution) |

### 6.4 Migration Rollback Procedure

To roll back migrations for Phase N (after the feature flag is disabled):

1. Verify the phase feature flag is `false` (no runtime traffic to the tables).
2. Run the backward migration for the highest-numbered migration in the phase.
3. Verify the backward migration succeeded (CI check: `alembic downgrade --sql`).
4. Repeat for each migration in the phase, in reverse order.
5. Record the migration rollback as an audit event.

**Important:** Migration rollback is OPTIONAL. If tables are retained dormant (feature flag `false`, no runtime traffic), the system is in a safe state. Migration rollback is only required if the schema itself must be reverted (e.g., to remove the `portal/continuation/` package entirely).

---

## 7. Deployment Strategy

### 7.1 Strategy Selection: Phased with Canary

The deployment strategy is **phased rollout with canary validation**. This is selected over blue-green because:

- The continuation subsystem is additive (new package, new tables), not a replacement for existing code. Blue-green's primary benefit (instant traffic switch between two versions of the same code) does not apply.
- The component dependency graph requires sequential phase deployment. Phased rollout naturally aligns with this.
- Canary validation at each phase provides early defect detection before broader exposure.

### 7.2 Deployment Stages

Each phase passes through three deployment stages:

```
Staging  →  Canary  →  Production (gradual ramp)
```

**Stage 1: Staging**
- Deploy to the staging environment.
- Run the full CI suite (all 12 checks) against the staging deployment.
- Execute the phase's go/no-go gate (Section 4.2).
- No real traffic. All testing is synthetic (test suite, integration tests, end-to-end protocol tests).

**Stage 2: Canary**
- Deploy to a single production canary instance (or a small canary tenant).
- Enable the phase feature flag ONLY for the canary instance/tenant.
- Monitor for 72 hours (Section 6 monitoring requirements).
- Canary success criteria: zero invariant violations, zero tenant isolation violations, error rate below threshold, no rollback triggers fired.
- Canary failure: disable the phase feature flag for the canary, investigate, and either remediate or roll back.

**Stage 3: Production Ramp**
- After canary success, enable the phase feature flag for production with a gradual ramp:
  - 5% of tenants for 24 hours.
  - 25% of tenants for 24 hours.
  - 50% of tenants for 24 hours.
  - 100% of tenants.
- At each ramp step, monitor for the same criteria as the canary. Any failure at a ramp step triggers a ramp-down to the previous step or a full phase rollback.

### 7.3 Deployment Timeline

The deployment timeline assumes the implementation timeline (Section 4.1) is complete. Deployment begins only after Phase 4 passes its go/no-go gate and certification begins.

```
Deployment stage   Duration    Gate
Staging (all)      12 weeks    (implementation timeline, Section 4.1)
Canary (Phase 0)   72 hours    Canary success criteria
Canary (Phase 1)   72 hours    Canary success criteria
Canary (Phase 2)   72 hours    Canary success criteria
Canary (Phase 3)   72 hours    Canary success criteria
Canary (Phase 4)   72 hours    Canary success criteria
Production ramp    4 days/phase (5% → 25% → 50% → 100%)
Certification      1-2 weeks   All 12 CI checks + ADR acceptance criteria
Sigma gate unblock 1 day       (Section 9)
```

**Note:** Canary stages may overlap if lower-phase canaries are stable. For example, Phase 1 canary may begin while Phase 0 is in production ramp, IF Phase 0 production ramp is at 100% and stable. This is at the review board's discretion.

### 7.4 Rollout Ordering Constraints

- **No phase skipping.** Phase N+1 cannot deploy to any stage until Phase N is at 100% production and stable for 24 hours.
- **No cross-phase canary.** A canary instance may only run one new phase at a time. Phases do not stack on a single canary.
- **Dependency verification.** Before deploying Phase N+1, verify that all Phase N components are operational and their monitoring shows no alerts. A Phase N alert blocks Phase N+1 deployment.

---

## 8. Monitoring and Alerting Requirements

### 8.1 Monitoring Principles

1. **Every component emits structured logs via structlog.** Log events include: component ID, tenant ID, correlation ID, event type, and relevant fields. All logs flow to the existing log aggregation infrastructure.
2. **Every component emits audit events via C12.** Once C12 is operational (Phase 0), all components append audit events for every state transition. C12 is the authoritative audit sink.
3. **Every component exposes health and readiness endpoints.** Health endpoints report liveness; readiness endpoints report dependency availability (e.g., C2 readiness checks C1, C6, C7, C14 availability).
4. **Metrics are emitted via the existing metrics infrastructure.** The portal already uses structlog for structured logging; metrics follow the same convention with a `metrics` event type.

### 8.2 Per-Phase Monitoring Requirements

| Phase | Metrics | Alerts |
|---|---|---|
| 0 | C14: anchor issuance rate, validation failure rate, skew detection count. C12: append latency, hash chain verification failures, query latency. C7: snapshot registration count, validation failure rate. C5: cache hit/miss ratio, eviction count. | C14 skew detection > 0. C12 hash chain verification failure > 0. C7 expired snapshot accepted > 0. C5 cache corruption detected. |
| 1 | C1: lease issuance/renewal/revocation rates, validation failure rate. C6: publish rate, watermark lag, cache age. C2: capability issuance/revocation/supersession rates, validation failure rate, CLASS_3 rejection count. | C1 validation failure rate > 1%. C6 watermark lag > `max_revocation_watermark_age`. C2 CLASS_3 issuance attempted > 0. C2 supersession failure. |
| 2 | C3: heartbeat request rate, status distribution (OK/DEGRADED/UNAVAILABLE), cross-tenant probe count. C4: statement publish/validate rates, quorum assembly failure rate, revoked-key usage count. | C3 cross-tenant probe > 0. C3 UNAVAILABLE status sustained > 5 min. C4 quorum assembly failure rate > 5%. C4 revoked-key usage > 0. |
| 3 | C8: journal append rate, seal failure count, post-seal append attempt count. C9: receipt generation rate, verification failure rate, missing evidence count. C13: effect check rate, duplicate detection count, CLASS_3 refusal count. | C8 post-seal append attempt > 0. C8 root_command_id mismatch > 0. C9 verification failure rate > 1%. C9 missing evidence > 0. C13 duplicate detection anomaly (unexpected spike or drop). C13 CLASS_3 effect attempted > 0. |
| 4 | C10: report submission rate, duplicate rejection count, conflict detection count, replay authorization count/blocked count. C11: queue depth, resolution rate, unresolved age. | C10 duplicate rejection spike (possible replay attack). C10 conflict detection rate > threshold. C10 replay authorization blocked while continuations unreconciled. C11 queue depth > threshold. C11 unresolved conflict age > SLA. |

### 8.3 Cross-Cutting Alerts

These alerts apply across all phases and trigger immediate investigation:

| Alert | Condition | Severity |
|---|---|---|
| Tenant isolation violation | Any component accepts a cross-tenant request | CRITICAL — immediate rollback |
| Invariant violation | Any ADR invariant (1–15) is violated at any component boundary | CRITICAL — immediate rollback |
| Feature flag tampering | A feature flag is changed without an audit event | HIGH — investigate and revert |
| Audit pipeline failure | C12 append fails or hash chain verification fails | CRITICAL — immediate rollback (audit integrity is non-negotiable) |
| Sigma gate tampering | `sigma_gate.py` or `GATE_STATE` is modified outside an authorized ADR | CRITICAL — immediate rollback and security incident |
| Error rate spike | Any component error rate exceeds 5% over 5 minutes | HIGH — investigate, prepare for rollback |
| Latency spike | Any component p99 latency exceeds 2x baseline over 5 minutes | MEDIUM — investigate |

### 8.4 Dashboards

A dedicated "Continuation Subsystem" dashboard is required before Phase 0 canary. It must display:

- Per-component health and readiness status.
- Per-component request rate, error rate, latency (p50, p95, p99).
- Feature flag states (all 16 flags).
- Active alerts (cross-cutting and per-phase).
- Sigma gate state (must show BLOCKED until certification).
- Tenant isolation violation count (must be 0 at all times).
- Invariant violation count (must be 0 at all times).

---

## 9. Incident Response Procedures

### 9.1 Incident Severity Levels

| Level | Definition | Response Time | Escalation |
|---|---|---|---|
| SEV-1 | Data integrity compromise, tenant isolation violation, audit pipeline failure, or Sigma gate tampering | Immediate | On-call SRE → Implementation lead → Review board → Security team |
| SEV-2 | Invariant violation, error rate > 5%, latency > 5x baseline, canary failure | 15 minutes | On-call SRE → Implementation lead |
| SEV-3 | Error rate 1–5%, latency 2–5x baseline, non-critical alert | 1 hour | On-call SRE |
| SEV-4 | Informational, no user impact | Next business day | On-call SRE (log only) |

### 9.2 Incident Response Procedure

1. **Detect:** Alert fires (monitoring) or report is received (operator or user).
2. **Triage:** On-call SRE determines severity level (SEV-1 through SEV-4).
3. **Stabilize:** For SEV-1 and SEV-2, the first action is to disable the affected component or phase feature flag (Section 5). This stops the bleeding. Investigation happens after stabilization.
4. **Investigate:** Determine root cause using logs, audit events (C12), and metrics.
5. **Remediate:** Fix the defect, or confirm that rollback is sufficient.
6. **Resolve:** Re-enable the feature flag after remediation, or declare a full rollback (Section 5.3).
7. **Record:** File an incident report. Record the incident as an audit event via C12 (if operational). Include: severity, detection time, stabilization time, root cause, remediation, and lessons learned.
8. **Review:** SEV-1 and SEV-2 incidents require a post-mortem review within 5 business days. The review board must sign off on the post-mortem.

### 9.3 Communication Plan

- **SEV-1:** Notify the review board and security team immediately (within 15 minutes of detection). Provide a status update every 30 minutes until stabilized.
- **SEV-2:** Notify the implementation lead within 15 minutes. Provide a status update every hour until stabilized.
- **SEV-3/4:** Log in the incident tracking system. No real-time notification required.

### 9.4 Incident Command

For SEV-1 incidents, the on-call SRE is the incident commander. The incident commander has authority to:
- Disable any feature flag (including `CONTINUATION_MASTER_ENABLED`).
- Initiate a full rollback (Section 5.3).
- Declare a security incident (if Sigma gate tampering or tenant isolation violation is confirmed).

The incident commander does NOT have authority to:
- Modify the Sigma gate state.
- Re-enable a feature flag after rollback (requires review board sign-off).
- Delete data (immutable stores are never deleted).

---

## 10. Sigma Gate Unblocking Procedure

### 10.1 Current State

The Sigma gate (`SIGMA_LEASE_EXPIRY_CONTINUATION_GATE`) is BLOCKED. This is enforced by `portal/services/sigma_gate.py`:

- `GATE_STATE = "BLOCKED"` (constant).
- `is_cancellation_blocked()` returns `True`.
- `get_gate_status()` returns `SigmaGateStatus(state="BLOCKED", cancellation_controls="DISABLED", blocking_phase_3b=True)`.
- Cancellation controls (execution-scoped, tenant-scoped, platform break-glass) are all `DISABLED`.

The gate is a constant — it does not transition at runtime. Transition requires an ADR amendment and explicit Principal authorization, not a code path.

### 10.2 Preconditions for Unblocking

The Sigma gate may transition to SATISFIED only when ALL of the following are true:

1. **All 14 components are implemented** (C01–C14, ADR-MC-001 §9.1).
2. **All five phases have passed their go/no-go gates** (Section 4).
3. **All 12 CI checks pass** on the fully implemented codebase:
   - Full test suite
   - Repo truth smoke check
   - PostgreSQL concurrency test
   - PostgreSQL bootstrap certification
   - Lint
   - Claims validation / validator tests
   - Auth/tenant/RBAC certification suite
   - Audit correlation and non-HTTP certification suite
   - HTTP correlation and WebSocket hardening certification suite
   - Security lint (bandit — baseline mode)
   - Dependency vulnerability scan (safety)
   - Sigma Quality Gate (this check itself must pass — it verifies the gate state)
4. **All ADR-MC-001 acceptance criteria are met** (ADR §13). This includes all 15 invariants enforced at component boundaries.
5. **The full recovery protocol (ADR §2.15) is testable end-to-end** in staging.
6. **A separate unblock ADR is authored, reviewed, and accepted.** The unblock ADR documents the certification evidence, the invariant enforcement matrix, and the review board sign-off. This ADR is the authority to modify `sigma_gate.py`.
7. **Explicit Principal authorization** for the gate state transition, per ADR-MC-001 Section 10.

### 10.3 Unblock Procedure

```
┌──────────────────────────────────────────────────────────┐
│  1. All 14 components implemented (Phases 0–4 complete)  │
└──────────────────────────┬───────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────┐
│  2. All 5 phase go/no-go gates passed                    │
└──────────────────────────┬───────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────┐
│  3. All 12 CI checks pass on main (including Sigma       │
│     Quality Gate, which verifies gate state)            │
└──────────────────────────┬───────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────┐
│  4. All ADR-MC-001 §13 acceptance criteria met           │
│     (all 15 invariants enforced at boundaries)           │
└──────────────────────────┬───────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────┐
│  5. Full recovery protocol (ADR §2.15) passes            │
│     end-to-end in staging                                │
└──────────────────────────┬───────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────┐
│  6. Unblock ADR authored, reviewed, and accepted         │
│     (documents certification evidence + sign-off)        │
└──────────────────────────┬───────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────┐
│  7. Explicit Principal authorization for gate transition │
│     (ADR-MC-001 §10)                                    │
└──────────────────────────┬───────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────┐
│  8. PR modifies sigma_gate.py:                           │
│     GATE_STATE = "SATISFIED"                             │
│     is_cancellation_blocked() returns False              │
│     Cancellation controls transition to ENABLED          │
└──────────────────────────┬───────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────┐
│  9. Sigma Quality Gate CI check passes (verifies         │
│     SATISFIED state)                                     │
└──────────────────────────┬───────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────┐
│  10. Sigma gate is UNBLOCKED. Cancellation controls are  │
│      ENABLED. Continuation is authorized at runtime.     │
└──────────────────────────────────────────────────────────┘
```

### 10.4 What This Plan Does NOT Do

- This plan does NOT unblock the Sigma gate.
- This plan does NOT modify `sigma_gate.py`.
- This plan does NOT authorize implementation.
- This plan does NOT authorize deployment.
- This plan describes the procedure that would be followed IF and WHEN implementation is authorized and completed. It is a plan, not an execution.

---

## 11. Emergency Freeze and Disable Procedures

### 11.1 Emergency Freeze

An emergency freeze is the immediate, unconditional disable of the entire continuation subsystem. It is the highest-priority rollback action.

**When to invoke:**
- Tenant isolation violation detected.
- Audit pipeline (C12) failure detected.
- Sigma gate tampering detected.
- Data integrity compromise detected.
- Any SEV-1 incident involving the continuation subsystem.
- At the discretion of the on-call SRE or incident commander.

**Procedure:**
1. Set `CONTINUATION_MASTER_ENABLED=false`. This is the global kill switch. All continuation endpoints return `503` immediately. No restart required.
2. Verify all continuation endpoints return `503` (health check sweep).
3. Verify `sigma_gate.py` is unchanged and `is_cancellation_blocked()` returns `True`.
4. Verify all 12 CI checks pass on the frozen state (run CI against the current main branch to confirm no regressions).
5. Notify the review board and security team (SEV-1 communication plan, Section 9.3).
6. Record the emergency freeze as a SEV-1 incident.
7. Do NOT re-enable until root cause is identified, remediated, and the review board signs off.

**Authority:** The on-call SRE and incident commander have unconditional authority to invoke an emergency freeze. No approval is required to freeze; approval is required to re-enable.

### 11.2 Emergency Disable (Single Component)

A single-component disable is used when a defect is isolated to one component and does not compromise data integrity or tenant isolation.

**Procedure:**
1. Set the component's child feature flag to `false` (e.g., `CONTINUATION_CAPABILITY_SERVICE_ENABLED=false` for C2).
2. Monitor dependent components for 15 minutes. If a dependent component degrades (e.g., C5 depends on C2 and begins failing), disable the dependent component's flag as well.
3. If cascading disable occurs (more than 2 components affected), escalate to phase-level disable (set the phase master flag to `false`).
4. If phase-level disable does not stabilize the system, escalate to emergency freeze (Section 11.1).

### 11.3 Re-enable Procedure

Re-enabling after a freeze or disable requires:

1. **Root cause identified and remediated.** The defect that triggered the freeze/disable is fixed, tested, and passes CI.
2. **Review board sign-off.** The review board reviews the remediation and authorizes re-enable.
3. **Phased re-enable.** Re-enable follows the phase order (0 → 1 → 2 → 3 → 4). Each phase is re-enabled one at a time, with monitoring between phases. No phase is re-enabled until the previous phase is stable.
4. **Canary re-validation.** If the freeze lasted more than 24 hours, re-run the canary stage (Section 7.2, Stage 2) before production re-enable.
5. **Audit record.** The re-enable is recorded as an audit event with the remediation summary and review board sign-off.

### 11.4 Emergency Freeze Decision Tree

```
                    ┌──────────────────────────────┐
                    │  SEV-1 incident detected in  │
                    │  continuation subsystem      │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │  Is data integrity, tenant    │
                    │  isolation, or audit pipeline │
                    │  compromised?                │
                    └──────┬───────────────┬───────┘
                           │ Yes           │ No
                           ▼               ▼
              ┌────────────────────┐  ┌────────────────────┐
              │  EMERGENCY FREEZE  │  │  Is the defect     │
              │  MASTER = false    │  │  isolated to a      │
              │  Notify review     │  │  single component?  │
              │  board + security  │  └──┬────────────┬────┘
              │  File SEV-1         │     │ Yes       │ No
              └────────────────────┘     ▼           ▼
                              ┌──────────────┐  ┌────────────────┐
                              │  Single-     │  │  Phase-level   │
                              │  component   │  │  disable       │
                              │  disable     │  │  (phase master │
                              │  (child flag)│  │  flag = false) │
                              └──────┬───────┘  └───────┬────────┘
                                     │                  │
                                     ▼                  ▼
                              ┌─────────────────────────────┐
                              │  Monitor for 15 minutes.    │
                              │  Stabilized?                │
                              └──────┬────────────┬────────┘
                                     │ Yes        │ No
                                     ▼            ▼
                              ┌──────────┐  ┌────────────────┐
                              │  File    │  │  EMERGENCY     │
                              │  SEV-2,  │  │  FREEZE        │
                              │  invest- │  │  (MASTER=false)│
                              │  igate   │  └────────────────┘
                              └──────────┘
```

---

## 12. Rollout Timeline Summary

### 12.1 Phase Dependency Diagram

```
Phase 0 (Foundation)
  │
  ├── C14 (time anchors) ──┐
  ├── C12 (audit pipeline) ─┤
  ├── C7 (policy snapshots) ─┤
  └── C5 (local state cache) ─┘
                             │
                  GATE 0 → 1 │
                             ▼
Phase 1 (Authority & Revocation)
  │
  ├── C1 (lease tokens) ──────┐
  ├── C6 (revocation stream) ─┤
  └── C2 (capabilities) ──────┘ (C2 after C1, C6)
                               │
                    GATE 1 → 2 │
                               ▼
Phase 2 (Outage Detection)
  │
  ├── C3 (heartbeat) ─────────┐
  └── C4 (witness statements) ─┘
                                 │
                      GATE 2 → 3 │
                                 ▼
Phase 3 (Continuation Execution)
  │
  ├── C8 (journal) ────────────┐
  ├── C9 (receipts) ───────────┤ (C9 after C8)
  └── C13 (effect identity) ───┘ (C13 after C9)
                                   │
                        GATE 3 → 4 │
                        ▼
Phase 4 (Reconciliation & Recovery)
  │
  ├── C10 (reconciliation engine) ──┐
  └── C11 (conflict review queue) ──┘ (C11 after C10)
                                       │
                            GATE 4 → CERT
                                       ▼
                        Certification (all 12 CI checks + ADR §13)
                                       │
                            SIGMA GATE UNBLOCK
                                       │
                            Production runtime continuation
```

### 12.2 Key Timeline Milestones

| Milestone | Prerequisite | Gate |
|---|---|---|
| Phase 0 staging deploy | Implementation authorized (separate ADR) | — |
| Phase 0 → Phase 1 | Phase 0 exit criteria met | Gate 0→1 |
| Phase 1 → Phase 2 | Phase 1 exit criteria met | Gate 1→2 |
| Phase 2 → Phase 3 | Phase 2 exit criteria met | Gate 2→3 |
| Phase 3 → Phase 4 | Phase 3 exit criteria met | Gate 3→4 |
| Phase 4 → Certification | Phase 4 exit criteria met | Gate 4→CERT |
| Certification complete | All 12 CI checks pass + ADR §13 acceptance criteria met | Certification gate |
| Sigma gate unblock | Certification complete + unblock ADR accepted + Principal authorization | Sigma gate |
| Production canary | Sigma gate unblocked | Canary gate |
| Production ramp (100%) | Canary success (72 hours, no alerts) | Production gate |

---

## 13. Traceability to ADR-MC-001

| Plan element | ADR-MC-001 source |
|---|---|
| 14 components, 5 phases | §9.1 Required Components; §9.2 Configuration; §9.3 Tests |
| Phase ordering (foundational first) | §2.8 (C14 root dependency); §2.1 (authority before detection); §2.6 (execution before reconciliation) |
| Feature flags default OFF (fail-closed) | §2.1.4 (capability validation fail-closed); §2.10 (watermark freshness gate) |
| Tenant isolation at every phase | §2.14 Tenant Isolation |
| Class 3 prohibition enforcement | §2.9 Class 3 Prohibition; Invariant 15 |
| Immutable audit ledger (never truncated) | §2.13 Audit Chain |
| Immutable journal store (never truncated) | §2.5.3 Continuation Journal |
| Sigma gate unblock requires all 14 components + certification | §13 Acceptance Criteria |
| Unblock requires separate ADR + Principal authorization | §10 Authorization Model |
| Cancellation controls DISABLED while gate BLOCKED | §2.5 Sigma condition (ADR-002 §2.5) |
| Two-signal outage detection | §2.2.2 Two-Signal Rule |
| Replay uses root_command_id | §2.7 Replay Authorization |
| Mandatory completion reporting | §2.6.2 Mandatory Reporting |
| Reconciliation: result selection, effect reconciliation, compensation, manual review | §2.6.3 Reconciliation |
| Conflict review queue | §2.6.3.4, §2.12.2 Manual Review |
| Platform maximums for §9.2 settings | §9.2 Configuration Settings |

---

## 14. Open Questions

1. **Witness topology deployment.** Concrete witness deployment, peer discovery, and BFT-vs-CFT election is deferred to a deployment planning document (ADR 2.2.4 allows CFT-first with documentation). The canary for Phase 2 must specify the witness topology under test.
2. **Signing key management.** HSM/KMS integration for Brain signing keys and witness identity keys is deferred to a separate security ADR. The canary must specify the key management configuration under test.
3. **Per-tenant feature flags.** The initial rollout uses platform-global flags. Per-tenant flag overrides (for gradual tenant-by-tenant rollout) are a future enhancement and require a separate configuration ADR.
4. **Migration retention policy.** The plan recommends retaining immutable tables (C12, C8) on rollback. The specific retention duration and archival procedure require a data retention policy ADR.
5. **Executor integration point.** How executor-side components (C5, C8, C9) integrate with the existing executor agent codebase (`agents/`) is deferred to a separate executor integration document. The rollout plan assumes the executor integration is validated during the Phase 3 canary.

---

## 15. Relationship to Existing Code

This plan is additive. It does not modify existing Mission Control Foundation code:

- `portal/services/sigma_gate.py` — unchanged until the Sigma gate unblock procedure (Section 10) is executed. The gate remains BLOCKED. `is_cancellation_blocked()` continues to return `True`.
- `portal/services/mission_control_command_service.py` — unchanged. The existing refusal-only command substrate continues to operate.
- `portal/routers/mission_control.py` — unchanged. The existing read-only projection endpoints continue to operate.
- `portal/models/mission_control_command.py` — unchanged. The existing command ledger models are not modified.
- `portal/services/audit_service.py` — may be extended or wrapped by C12, but the existing `audit()` function and hash chain are not modified. C12 is a new service that may delegate to the existing audit infrastructure or provide its own append path. This decision is deferred to document 04 (persistence schema).

The new `portal/continuation/` package is self-contained. It imports from `portal/database.py` (for `AsyncSession`, `Base`, `tenant_session`) and `portal/config.py` (for `Settings`), but does not modify them.

---

## 16. Summary

This document defines a phased rollout and rollback plan for the 14 executor continuation components. The plan is:

- **Dependency-ordered** — five phases aligned with the component dependency graph (document 02), foundational components first.
- **Feature-flagged** — 16 feature flags in a three-level hierarchy, all defaulting to OFF (fail-closed). Flags are read at request time, enabling rollback without restart.
- **Gate-controlled** — each phase has a go/no-go gate with explicit exit criteria. No phase advances without human decision based on evidence.
- **Reversible** — every phase has a rollback procedure. Rollback is feature-flag-first, data-preserving, and dependency-aware (reverse-phase order).
- **Migration-safe** — additive schema changes with tested backward migrations. Immutable tables are never truncated.
- **Phased with canary** — staging → canary → production ramp, with 72-hour canary validation and gradual production ramp (5% → 25% → 50% → 100%).
- **Monitored** — per-phase metrics and alerts, cross-cutting alerts for tenant isolation and invariant violations, a dedicated dashboard.
- **Incident-ready** — four severity levels, clear response procedure, incident commander authority for emergency freeze.
- **Sigma-gate-gated** — the Sigma gate remains BLOCKED until all 14 components are implemented, all 12 CI checks pass, all ADR acceptance criteria are met, a separate unblock ADR is accepted, and explicit Principal authorization is granted.
- **Emergency-ready** — global kill switch (`CONTINUATION_MASTER_ENABLED=false`) for immediate freeze, with clear escalation from single-component disable to phase disable to full freeze.

The Sigma gate remains BLOCKED. This document authorizes rollout and rollback planning, not implementation execution. Implementation requires separate ADRs, branches, and authorizations per ADR-MC-001 Section 10.

---

**End of document.** This is a planning artifact only. No runtime code is authorized by this document. Implementation requires separate ADRs, branches, and authorizations per ADR-MC-001 Section 10.