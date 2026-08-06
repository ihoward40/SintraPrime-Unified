# 01 — Implementation Architecture: Executor Continuation

**Package:** Executor Continuation Implementation Planning
**Source ADR:** ADR-MC-001 (ACCEPTED, ratified 2026-08-05)
**Scope:** PLANNING ONLY — no runtime code, no API changes, no persistence changes. This document decomposes the executor continuation capability into implementation components, defines the component architecture, describes inter-component interactions, defines the implementation order with dependencies, and maps to the 14 required components enumerated in ADR-MC-001 Section 9.1.
**Codebase conventions:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 async, structlog, PostgreSQL with row-level security. Async/await throughout. Type annotations required.

---

## 1. Document Purpose

This document is the architecture blueprint for implementing the executor continuation capability defined by ADR-MC-001. It is a planning artifact only — it authorizes no runtime code, no API changes, no persistence migrations, and no deployment. Implementation requires separate ADRs, branches, and authorizations per ADR-MC-001 Section 10.

The document serves three audiences:

1. **Implementers** — who need to know what to build, in what order, and how components interact.
2. **Reviewers** — who need to verify that the architecture satisfies all 14 ADR-MC-001 Section 9.1 components and all 15 ADR invariants.
3. **Operators** — who need to understand the system shape for deployment, monitoring, and incident response planning.

Companion documents in this planning package:

| Document | Scope |
|---|---|
| `01_IMPLEMENTATION_ARCHITECTURE.md` (this document) | Component decomposition, architecture, dependency analysis, implementation phases, technology choices |
| `03_INTERFACE_SPECIFICATIONS.md` | Pydantic v2 data models and Protocol interfaces for all 14 components |
| (future) `02_*` | Implementation plan, task breakdown, and phase deliverables |
| (future) `04_*` | Persistence schema and migration plan |
| (future) `05_*` | Test strategy and acceptance test mapping |

---

## 2. Component Overview

ADR-MC-001 Section 9.1 enumerates 14 required components. Each is listed below with its ADR reference, purpose, and the side of the system it belongs to (Brain-side, executor-side, or shared/cross-cutting).

| # | Component | ADR Ref | Purpose | Side |
|---|---|---|---|---|
| C1 | Signed lease token service | 2.1.1–2.1.3 | Issue, renew, and revoke cryptographically signed lease tokens binding one executor to one command under a time-bounded authority envelope | Brain |
| C2 | Continuation capability service | 2.1.4 | Issue, validate, and revoke signed continuation capabilities; manage capability supersession | Brain |
| C3 | Brain heartbeat endpoint | 2.2.1 | Allow executors to detect Brain availability via heartbeat acknowledgements; deliver signed time anchors and revocation watermarks | Brain |
| C4 | Witness statement service | 2.2.4 | Publish and validate signed witness statements about Brain availability from independent control-plane identities | Shared (Brain-adjacent witnesses) |
| C5 | Executor local state cache | 2.3 | Store inputs, configuration, and prior step outputs; self-check local state sufficiency before continuing | Executor |
| C6 | Revocation stream | 2.10 | Publish a signed, monotonic, tenant-partitioned stream of lease revocations, command cancellations, capability revocations, and emergency denies | Brain (read by executor) |
| C7 | Policy snapshot registry | 2.11 | Pin and validate policy snapshots by cryptographic hash; enforce snapshot validity bounds | Brain (read by executor) |
| C8 | Continuation journal store | 2.5.3 | Maintain an immutable per-continuation operation log recording every operation, its input, output, status, timestamp, and stable external-effect identity | Executor |
| C9 | Completion receipt service | 2.6.2, 2.13 | Generate and verify signed continuation receipts; assemble outage evidence bundles; enforce mandatory reporting | Executor (verified by Brain) |
| C10 | Reconciliation engine | 2.6, 2.12 | Classify and resolve continuation reports with result selection, effect reconciliation, compensation, and manual review routing | Brain |
| C11 | Conflict review queue | 2.6.3.4, 2.12 | Surface conflicting continuation results, invalid continuations, and non-reversible effects for operator resolution | Brain |
| C12 | Audit event pipeline | 2.13 | Append continuation events to the immutable audit ledger; provide causation chain projections (never truncate authoritative storage) | Shared (all components) |
| C13 | Downstream effect identity layer | 2.5 | Validate `(root_command_id, operation_id, side_effect_slot)` before applying effects; provide duplicate suppression at the downstream boundary | Downstream systems |
| C14 | Signed time-anchor service | 2.8 | Issue and validate signed wall-clock anchors; check clock skew and rollback; enforce monotonic time bounds | Brain (consumed by executor) |

### 2.1 Architecture Sides

The system has four logical sides, each with distinct trust boundaries:

- **Brain side** — the central command authority. Owns lease issuance, capability issuance, revocation, heartbeat, reconciliation, and conflict review. Components: C1, C2, C3, C6, C7, C10, C11, C14.
- **Executor side** — the worker process performing command work. Owns local state cache, continuation journal, and receipt generation. Components: C5, C8, C9.
- **Witness plane** — independent control-plane identities that observe Brain availability. Not executors, not the Brain. Component: C4.
- **Downstream systems** — external effect sinks (databases, APIs, notification services). Owns effect identity validation and duplicate suppression. Component: C13.
- **Cross-cutting** — the audit pipeline spans all sides. Component: C12.

The trust boundary is critical: an executor cannot bootstrap its own authority. Capabilities, leases, time anchors, and revocation entries are all Brain-signed. Witnesses supplement but never replace direct-Brain signals. Downstream systems validate Brain-signed tokens, not executor claims.

---

## 3. Component Architecture

### 3.1 Layered Architecture

The 14 components form five layers. Each layer depends only on components in its own layer or layers below it. No upward dependencies exist.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Layer 4: Reconciliation & Recovery                    │
│   C10 Reconciliation Engine    C11 Conflict Review Queue                 │
└────────────────────────┬────────────────────────────────────────────────┘
                         │ depends on
┌────────────────────────┴────────────────────────────────────────────────┐
│                  Layer 3: Continuation Execution                        │
│   C8 Continuation Journal    C9 Completion Receipt Service              │
│   C13 Downstream Effect Identity Layer                                   │
└────────────────────────┬────────────────────────────────────────────────┘
                         │ depends on
┌────────────────────────┴────────────────────────────────────────────────┐
│                  Layer 2: Outage Detection                              │
│   C3 Brain Heartbeat Endpoint    C4 Witness Statement Service           │
└────────────────────────┬────────────────────────────────────────────────┘
                         │ depends on
┌────────────────────────┴────────────────────────────────────────────────┐
│                  Layer 1: Authority & Revocation                       │
│   C1 Signed Lease Token Service    C6 Revocation Stream                 │
│   C2 Continuation Capability Service                                     │
└────────────────────────┬────────────────────────────────────────────────┘
                         │ depends on
┌────────────────────────┴────────────────────────────────────────────────┐
│                  Layer 0: Foundation                                   │
│   C5 Executor Local State Cache    C7 Policy Snapshot Registry           │
│   C12 Audit Event Pipeline         C14 Signed Time-Anchor Service        │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Interaction Diagram

The following diagram shows the primary data flow and dependencies across the full continuation lifecycle. Arrows indicate "depends on" or "produces for" relationships.

```
                         ┌──────────┐
                         │  Brain   │
                         └────┬─────┘
                              │ dispatch
                              v
                    ┌─────────────────┐
                    │  C1 Lease Token  │
                    │    Service       │
                    └────────┬────────┘
                             │ issue lease + capability
                             v
                    ┌─────────────────┐         ┌──────────────┐
                    │  C2 Capability   │◄────────│  C7 Policy   │
                    │    Service       │  hash   │  Snapshot    │
                    └────────┬────────┘         │  Registry    │
                             │                  └──────────────┘
                             │ capability
                             v
     ┌───────────┐    ┌─────────────────┐
     │  C14 Time  │───►│  C3 Heartbeat    │
     │  Anchor    │    │    Endpoint      │
     │  Service   │    └────────┬────────┘
     └─────┬─────┘             │ heartbeat
           │                   v
           │    ┌──────────────────────────────────┐
           │    │           Executor                │
           │    │                                    │
           │    │  ┌────────┐   ┌────────┐          │
           │    │  │ C5 Loc │   │ C6 Rev │          │
           │    │  │ State  │   │ Stream │          │
           │    │  │ Cache  │   │ (read) │          │
           │    │  └───┬────┘   └───┬────┘          │
           │    │      │            │               │
           │    │      v            v               │
           │    │  ┌──────────────────────┐          │
           │    │  │  Outage Detection    │          │
           │    │  │  (C3 + C4 signals)   │          │
           │    │  └──────────┬──────────┘          │
           │    │             │ declare             │
           │    │             v                     │
           │    │  ┌──────────────────────┐          │
           │    │  │  C8 Continuation     │          │
           │    │  │  Journal Store       │          │
           │    │  └──────────┬──────────┘          │
           │    │             │ seal                 │
           │    │             v                     │
           │    │  ┌──────────────────────┐          │
           │    │  │  C9 Completion       │          │
           │    │  │  Receipt Service     │          │
           │    │  └──────────┬──────────┘          │
           │    └─────────────┼────────────────────┘
           │                  │ report
           │    ┌──────────────┐
           │    │  C4 Witness  │
           │    │  Statement   │
           │    │  Service     │
           │    └──────┬───────┘
           │           │ witness statements
           │           v
           │    ┌──────────────────────┐
           │    │  C10 Reconciliation   │
           │    │  Engine               │
           │    └──────────┬──────────┘
           │               │ conflicts
           │               v
           │    ┌──────────────────────┐
           │    │  C11 Conflict Review │
           │    │  Queue               │
           │    └──────────────────────┘
           │
           │    ┌──────────────────────┐
           │    │  C13 Downstream       │
           │    │  Effect Identity     │
           │    │  Layer               │
           │    └──────────────────────┘
           │
           │    ┌──────────────────────┐
           └───►│  C12 Audit Event     │
                │  Pipeline (all)      │
                └──────────────────────┘
```

### 3.3 Interaction Patterns

Components interact through three patterns:

**Pattern 1: Signed-token exchange.** Authority flows are mediated by cryptographically signed tokens (lease tokens, capability tokens, witness statements, time anchors, revocation entries). The producer signs; the consumer verifies. No component trusts an unsigned claim. This pattern is used by C1→C2, C2→C9, C3→executor, C4→C9, C6→executor, C14→all.

**Pattern 2: Append-only logging.** Every state transition is recorded as an immutable, hash-chained audit event through C12. Components do not log directly to the audit ledger; they call C12's `append` interface. C12 is the sole writer to the authoritative audit storage. This pattern is used by all components.

**Pattern 3: Watermark-gated decisions.** The revocation stream (C6) publishes a monotonic sequence. Consumers record the highest sequence number they have observed (the watermark) and use it as a freshness gate. If the watermark is stale, missing, or below the required threshold, the decision is fail-closed. This pattern is used by C2 (capability validation), C9 (receipt generation), and the executor's outage detection logic.

---

## 4. Responsibility Matrix

This matrix maps each ADR-MC-001 requirement area to the component(s) that own or participate in its enforcement. "O" = owner (primary responsibility), "P" = participant (contributes but does not own), "R" = reader/consumer.

| ADR Requirement | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | C10 | C11 | C12 | C13 | C14 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2.1.1 Lease acquisition | O | P | | | | | P | | | | | P | | P |
| 2.1.2 Lease renewal | O | P | | | | P | P | | | | | P | | P |
| 2.1.3 Lease expiry | O | | | | | P | | | | | | P | | P |
| 2.1.4 Continuation capability | P | O | | | | P | P | | | | | P | | P |
| 2.2.1–2.2.3 Outage detection | | | O | P | P | P | | | | | | P | | P |
| 2.2.4 Witness trust model | | | | O | | P | | | P | P | P | P | | P |
| 2.3 Continuation eligibility | R | O | R | R | O | R | R | R | R | | | R | R | R |
| 2.4 Continuation limits | P | O | | | | | | P | P | P | | P | | |
| 2.5.1 Stable effect identity | | P | | | | | | O | P | P | P | P | O | |
| 2.5.2 Duplicate suppression | P | P | | | | | | P | P | P | | P | O | |
| 2.5.3 Continuation journal | | | | | | | | O | P | P | P | P | R | |
| 2.6 Reconciliation protocol | R | R | | R | | R | | R | P | O | P | P | P | R |
| 2.6.3.4 Manual review | | | | | | | | | P | P | O | P | | |
| 2.7 Replay semantics | P | P | | | | P | | | R | O | R | P | P | |
| 2.8 Time authority | R | R | P | P | | | | | P | | | P | | O |
| 2.9 Side-effect classification | P | O | | | | | | R | R | P | P | P | O | |
| 2.10 Revocation watermark | P | P | P | | | O | | | P | P | | P | P | |
| 2.11 Policy snapshot model | P | P | | | | P | O | | | | | P | | |
| 2.12 Split-brain handling | P | P | | P | | P | | P | P | O | P | P | P | |
| 2.13 Audit chain | P | P | P | P | P | P | P | P | P | P | P | O | P | P |
| 2.14 Tenant isolation | O | O | O | O | O | O | O | O | O | O | O | O | O | O |
| 2.15 Recovery protocol | R | R | O | P | R | R | R | R | P | O | P | P | P | P |

### 4.1 Tenant Isolation Ownership

Every component owns tenant isolation within its own boundary (row 2.14 above shows "O" for all). This is non-negotiable: cross-tenant continuation is forbidden and treated as a security event (ADR 2.14). Each component must validate `tenant_id` at its interface boundary and reject cross-tenant access. The existing portal pattern of returning 404 (not 403) for cross-tenant access to avoid leaking resource existence applies to all read endpoints.

---

## 5. Dependency Analysis

### 5.1 Dependency Graph

The following directed graph shows build-time dependencies (component A depends on component B if A's implementation requires B's interface to be available). Arrows point from dependent to dependency.

```
C14 (Time Anchor)     C12 (Audit Pipeline)    C7 (Policy Snapshot)   C5 (Local State Cache)
  ^                      ^                       ^                      ^
  |                      |                       |                      |
  +----+----+----+       +----+----+----+        +----+----+            |
       |    |    |            |    |    |             |                |
       v    v    v            v    v    v             v                |
      C1 (Lease)  C6 (Revocation)  C2 (Capability)    |               |
         ^              ^                ^            |               |
         |              |                |            |               |
         +--------------+----+-----------+            |               |
                              |                       |               |
                              v                       |               |
                         C3 (Heartbeat)               |               |
                         C4 (Witness)                 |               |
                              ^                       |               |
                              |                       |               |
                              v                       v               |
                         C9 (Receipt) <---- C8 (Journal)              |
                              ^                                       |
                              |                                       |
                              v                                       |
                         C13 (Effect Identity)                        |
                              ^                                       |
                              |                                       |
                              v                                       |
                         C10 (Reconciliation) <------------------------+
                              ^
                              |
                              v
                         C11 (Conflict Queue)
```

### 5.2 Dependency Matrix

The matrix below shows direct dependencies only. "D" = depends on (row depends on column). Transitive dependencies are implied.

|  | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | C10 | C11 | C12 | C13 | C14 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **C1** Lease | — | | | | | | D | | | | | D | | D |
| **C2** Capability | D | — | | | | D | D | | | | | D | | D |
| **C3** Heartbeat | | | — | | | D | | | | | | D | | D |
| **C4** Witness | | | | — | | | | | | | | D | | D |
| **C5** State Cache | | | | | — | | | | | | | | | |
| **C6** Revocation | | | | | | — | | | | | | D | | D |
| **C7** Policy Snapshot | | | | | | | — | | | | | D | | |
| **C8** Journal | | | | | | | | — | | | | D | | |
| **C9** Receipt | | | | D | | D | | D | — | | | D | | D |
| **C10** Reconciliation | D | | | | | | | | D | — | | D | D | |
| **C11** Conflict Queue | | | | | | | | | | D | — | D | | |
| **C12** Audit | | | | | | | | | | | | — | | |
| **C13** Effect Identity | | D | | | | | | | D | | | D | — | |
| **C14** Time Anchor | | | | | | | | | | | | D | | — |

### 5.3 Key Dependency Notes

1. **C14 (Time Anchor) and C12 (Audit Pipeline) are the most depended-upon components.** C14 is a dependency of C1, C2, C3, C4, C6, C9. C12 is a dependency of every component. These two must be built first or mocked first.

2. **C5 (Local State Cache) and C7 (Policy Snapshot Registry) have no dependencies on other continuation components.** They can be built in parallel with any layer. C5 is executor-local; C7 is Brain-local but read-only from the executor's perspective.

3. **C2 (Continuation Capability Service) has the most dependencies (C1, C6, C7, C12, C14).** It is the authority hub of the system. It cannot be built until C1 and C6 are available (or mocked).

4. **C13 (Downstream Effect Identity Layer) depends on C2 and C9.** It validates capabilities and outage evidence before applying effects. This creates a dependency chain: C14 → C1 → C2 → C9 → C13.

5. **C10 (Reconciliation Engine) depends on C1, C9, C12, C13.** It is the terminal component in the continuation lifecycle — it consumes reports, validates effect records, and may issue replay leases. It also feeds C11 (Conflict Review Queue).

6. **No circular dependencies exist.** The dependency graph is a DAG. The topological order is defined in Section 6.

### 5.4 Shared Data Model Dependencies

Beyond service-level dependencies, components share data model definitions. These are defined once in `03_INTERFACE_SPECIFICATIONS.md` and referenced across components. The shared models form their own dependency layer:

| Shared Model | Defined In | Referenced By |
|---|---|---|
| `SignedToken` | 03 §1 (shared primitives) | C1, C2, C4, C6, C8, C9, C12, C14 |
| `Fingerprint` | 03 §1 | C1, C9 |
| `SignedTimeAnchor` | 03 §1 | C1, C2, C3, C4, C9, C14 |
| `ContinuationCapabilityPayload` | 03 §3.2 (C2) | C8, C9, C10, C13 |
| `WitnessStatement` | 03 §5.2 (C4) | C9 (outage evidence), C10, C12 |
| `RevocationStreamEntry` | 03 §7.2 (C6) | C1, C2, C9, C10 |
| `StableEffectIdentity` | 03 §9.2 (C8) | C9, C10, C11, C13 |
| `CompletionReport` / `OutageEvidenceBundle` | 03 §10.2 (C9) | C10, C11, C13 |
| `AuditEvent` | 03 §13.2 (C12) | All components (causation chain) |

These shared models must be defined in a common `schemas` module before any component that references them. They are planning artifacts today (defined in `03_INTERFACE_SPECIFICATIONS.md`); at implementation time they will live in a shared Python package.

---

## 6. Implementation Phases and Order

### 6.1 Phase Summary

Implementation proceeds in five phases. Each phase produces a testable, deployable (in a staging environment) increment. No phase unblocks the Sigma gate; only full certification of all 14 components plus all ADR acceptance criteria does.

| Phase | Name | Components | Depends On | Key Deliverable |
|---|---|---|---|---|
| 0 | Foundation | C14, C12, C7, C5 | (nothing) | Time anchors, audit pipeline, policy snapshots, local state cache |
| 1 | Authority & Revocation | C1, C6, C2 | Phase 0 | Lease issuance, revocation stream, capability issuance |
| 2 | Outage Detection | C3, C4 | Phase 1 | Heartbeat endpoint, witness statements, outage declaration |
| 3 | Continuation Execution | C8, C9, C13 | Phase 2 | Continuation journal, completion receipts, effect identity validation |
| 4 | Reconciliation & Recovery | C10, C11 | Phase 3 | Reconciliation engine, conflict review queue, replay authorization |

### 6.2 Phase 0 — Foundation

**Goal:** Build the foundational services that all other components depend on.

**Components:**

| Component | What to Build | Why First |
|---|---|---|
| C14 — Signed Time-Anchor Service | `issue_anchor`, `validate_anchor`, `check_skew`, `check_rollback` | Every signed token, lease, capability, and revocation entry carries a Brain-signed timestamp. Without time anchors, no authority can be validated. |
| C12 — Audit Event Pipeline | `append`, `get`, `query`, `causation_chain` with hash-chained immutable storage | Every other component must emit audit events. C12 is the sole writer to the authoritative audit ledger. |
| C7 — Policy Snapshot Registry | `register`, `get_by_id`, `validate_hash`, `is_expired` | Capabilities (C2) carry pinned policy snapshot hashes. The registry must exist before capabilities can reference snapshots. |
| C5 — Executor Local State Cache | `store_inputs`, `store_step_output`, `get_inputs`, `get_step_output`, `check_sufficiency`, `evict` | The executor's self-check for continuation eligibility requires local state. This cache is executor-local and has no cross-component dependencies. |

**Phase 0 Exit Criteria:**

- C14 issues and validates signed time anchors; skew and rollback checks produce correct security events.
- C12 appends hash-chained events; causation chain projection paginates without truncating authoritative storage.
- C7 pins and validates policy snapshots by hash; expired snapshots are rejected.
- C5 stores and retrieves command inputs and step outputs; sufficiency check correctly reports missing inputs.
- All four components have unit tests covering their interface contracts.
- All four components enforce tenant isolation at their boundaries.

**Estimated complexity:** Medium. C12 and C14 have cryptographic signing requirements. C7 and C5 are straightforward data stores.

### 6.3 Phase 1 — Authority & Revocation

**Goal:** Build the authority chain that gates all continuation: leases, revocation, and capabilities.

**Components:**

| Component | What to Build | Dependencies |
|---|---|---|
| C1 — Signed Lease Token Service | `issue_lease`, `renew_lease`, `revoke_lease`, `validate_lease`, `fingerprint` | C14 (time anchors), C12 (audit), C7 (policy snapshot reference) |
| C6 — Revocation Stream | `publish`, `read`, `latest_watermark`, `cache_age` | C12 (audit), C14 (signed timestamps) |
| C2 — Continuation Capability Service | `issue_capability`, `validate_capability`, `revoke_capability`, `supersede_capability`, `is_superseded` | C1 (lease reference), C6 (revocation watermark), C7 (policy snapshot hash), C12 (audit), C14 (time anchors) |

**Build order within Phase 1:**

1. C1 and C6 can be built in parallel. C1 depends on C14, C12, C7 (all from Phase 0). C6 depends on C12, C14 (both from Phase 0).
2. C2 depends on C1 and C6, so it must follow them.

**Phase 1 Exit Criteria:**

- C1 issues, renews, and revokes signed lease tokens; `validate_lease` correctly rejects expired, revoked, tenant-mismatched, and clock-skewed tokens.
- C1 renewal supersedes prior continuation capabilities (Invariant 3a); superseded capability IDs are recorded.
- C6 publishes a signed, monotonic, tenant-partitioned revocation stream; `latest_watermark` and `cache_age` are correct.
- C2 issues, validates, and revokes signed continuation capabilities; `validate_capability` correctly rejects capabilities that are before `not_valid_before`, after `not_valid_after`, superseded, revoked, tenant-mismatched, or where the lease is still active.
- C2 rejects `CLASS_3` capability issuance at issue time (Invariant 15 enforcement).
- All three components have unit tests and integration tests covering their interactions.
- All ADR invariants 1, 2, 3, 3a, 4, 12, 13, 15 are enforced at the interface boundary.

**Estimated complexity:** High. C2 is the most complex component in the system — it has the most dependencies, the most validation rules, and the most invariants to enforce.

### 6.4 Phase 2 — Outage Detection

**Goal:** Build the mechanisms that allow executors to detect Brain unavailability robustly.

**Components:**

| Component | What to Build | Dependencies |
|---|---|---|
| C3 — Brain Heartbeat Endpoint | `heartbeat`, `last_heartbeat` (FastAPI endpoint) | C14 (signed anchors in response), C6 (revocation watermark in response) |
| C4 — Witness Statement Service | `publish_statement`, `validate_statement`, `collect_quorum`, `revoke_witness_key` | C14 (signed timestamps), C12 (audit) |

**Build order within Phase 2:**

1. C3 and C4 can be built in parallel. Both depend only on Phase 0 and Phase 1 components.

**Phase 2 Exit Criteria:**

- C3 returns `OK`, `DEGRADED`, or `UNAVAILABLE` status with a fresh `SignedTimeAnchor` and current `revocation_watermark`.
- C3 heartbeat responses are tenant-scoped; cross-tenant probing is a security event.
- C4 publishes and validates signed witness statements; `validate_statement` correctly rejects stale, replayed, revoked-key, self-exclusion-violating, and tenant-mismatched statements.
- C4 `collect_quorum` correctly assembles quorum with BFT or CFT fault model; `witness_quorum_size < N` is enforced.
- The two-signal outage detection rule (ADR 2.2.2) is testable using C3 and C4 outputs: at least two independent signals, one of which is a direct-Brain signal.
- Witness statements alone are never sufficient to declare outage (ADR 2.2.2).
- All ADR invariants related to witness trust (Section 2.2.4) are enforced.

**Estimated complexity:** Medium. C3 is a standard FastAPI endpoint. C4 has cryptographic validation and quorum assembly logic.

### 6.5 Phase 3 — Continuation Execution

**Goal:** Build the executor-side components that perform and record continuation work, plus the downstream effect validation that prevents duplicate external effects.

**Components:**

| Component | What to Build | Dependencies |
|---|---|---|
| C8 — Continuation Journal Store | `open`, `append`, `read`, `seal` | C12 (audit); uses `StableEffectIdentity` shared model |
| C9 — Completion Receipt Service | `generate_receipt`, `verify_receipt`, `store_receipt`, `get_receipt` | C8 (journal blob), C4 (witness statements for outage evidence), C6 (revocation watermark), C12 (audit), C14 (time anchors) |
| C13 — Downstream Effect Identity Layer | `check_effect`, `record_effect`, `query_effect` | C2 (capability validation), C9 (outage evidence validation), C12 (audit) |

**Build order within Phase 3:**

1. C8 can be built first (depends only on C12 and shared models).
2. C9 depends on C8 (journal blob in completion report) and C4 (witness statements in outage evidence).
3. C13 depends on C2 (Phase 1) and C9 (Phase 3), so it must follow C9.

**Phase 3 Exit Criteria:**

- C8 appends immutable, hash-chained journal entries; `seal` produces a tamper-evident seal signature; append after seal is rejected.
- C8 journal entries always use `root_command_id` in `StableEffectIdentity`, never a replay-attempt command ID (ADR 2.5.1 replay identity rule).
- C9 generates signed receipts with valid outage evidence bundles; `verify_receipt` correctly rejects missing, mismatched, or watermark-below-required evidence.
- C9 enforces mandatory reporting regardless of `final_state` (ADR 2.6.2).
- C13 `check_effect` correctly identifies duplicates by `(root_command_id, operation_id, side_effect_slot)`.
- C13 refuses Class 3 effects during continuation (ADR 2.9, Invariant 15).
- C13 requires valid matching outage evidence; a capability alone is not sufficient (ADR 2.1.4).
- All ADR invariants 5, 6, 10, 15 are enforced at the interface boundary.

**Estimated complexity:** High. C9 assembles the outage evidence bundle, which is the most complex data structure in the system. C13 has critical safety properties — it is the last line of defense against duplicate external effects.

### 6.6 Phase 4 — Reconciliation & Recovery

**Goal:** Build the Brain-side components that reconcile continuation reports after recovery, resolve conflicts, and authorize replays.

**Components:**

| Component | What to Build | Dependencies |
|---|---|---|
| C10 — Reconciliation Engine | `submit_report`, `reconcile_command`, `detect_conflicts`, `authorize_replay` | C1 (replay lease issuance), C9 (completion reports), C12 (audit), C13 (effect records) |
| C11 — Conflict Review Queue | `enqueue`, `list_pending`, `resolve`, `get` | C10 (enqueue from reconciliation), C12 (audit) |

**Build order within Phase 4:**

1. C10 must be built first (C11 depends on C10 to populate the queue).

**Phase 4 Exit Criteria:**

- C10 `submit_report` accepts completion reports and rejects duplicates by `(command_id, continuation_id)`.
- C10 `reconcile_command` performs result selection, effect reconciliation, compensation, and manual-review routing per ADR 2.6.3.
- C10 result selection by timestamp is permitted only when all reported effects are provably idempotent and equivalent (ADR 2.6.3.1).
- C10 `detect_conflicts` correctly identifies divergent result digests and conflicting effect identities.
- C10 `authorize_replay` blocks replay while continuations are unreconciled or effects are unresolved; replay uses `root_command_id` for effect identities (ADR 2.7).
- C11 enqueues conflicts from C10; the command remains in `MANUAL_REVIEW_REQUIRED` until an authorized operator resolves it.
- C11 resolution is recorded as an audit event; no silent conflict resolution.
- All ADR invariants 7, 8 are enforced at the interface boundary.
- The full recovery protocol (ADR 2.15) is testable end-to-end.

**Estimated complexity:** High. C10 is the second most complex component after C2. It implements four distinct reconciliation concerns (result selection, effect reconciliation, compensation, manual review) and the replay authorization logic.

### 6.7 Full Topological Build Order

The complete build order, respecting all dependencies, is:

```
Phase 0 (parallel):  C14, C12, C7, C5
Phase 1 (parallel):  C1, C6
Phase 1 (serial):    C2 (after C1 and C6)
Phase 2 (parallel):  C3, C4
Phase 3 (serial):    C8 → C9 → C13
Phase 4 (serial):    C10 → C11
```

Within each phase, components listed as parallel can be developed simultaneously by different engineers. Components listed as serial must be developed in the listed order due to direct dependencies.

### 6.8 Implementation Order Rationale

The order is driven by three principles:

1. **Foundations first.** C14 (time) and C12 (audit) are depended on by nearly everything. Building them first eliminates the need for pervasive mocking later.

2. **Authority before detection.** Outage detection (C3, C4) requires revocation watermarks (C6) and time anchors (C14) to be meaningful. The heartbeat endpoint returns a revocation watermark; witness statements carry signed timestamps. These dependencies are in Phase 0 and Phase 1, so Phase 2 can use real implementations.

3. **Execution before reconciliation.** Reconciliation (C10) consumes completion reports (C9) and effect records (C13). These must exist before reconciliation can be tested with real data. Building C10 before C9 would require extensive mocking of the report format, which is the most complex data structure in the system.

---

## 7. Technology Choices

### 7.1 Consistency with Existing Stack

The implementation uses the same technology stack as the existing portal, ensuring that new code integrates with existing patterns, tooling, and deployment infrastructure.

| Layer | Technology | Existing Usage | Rationale |
|---|---|---|---|
| Language | Python 3.11+ | Entire codebase | Required by `pyproject.toml`; matches existing portal, services, and agents |
| Web framework | FastAPI | `portal/main.py`, all `portal/routers/` | Existing portal uses FastAPI with async lifespan, middleware, and Pydantic v2 schemas |
| Data validation | Pydantic v2 | `portal/schemas/`, `portal/config.py` | Existing schemas use `BaseModel` with `Field(...)`; `pydantic-settings` for configuration |
| ORM | SQLAlchemy 2.0 async | `portal/database.py`, `portal/models/` | Existing `AsyncEngine`, `async_sessionmaker`, `DeclarativeBase`; RLS via `SET LOCAL` |
| Database | PostgreSQL (asyncpg) | `portal/database.py` | Existing `DATABASE_URL` uses `postgresql+asyncpg://`; RLS for tenant isolation |
| Structured logging | structlog | `portal/services/audit_service.py`, all services | Existing convention for structured log events |
| HTTP client | httpx | `pyproject.toml` dependency | For executor-to-Brain and executor-to-witness communication |
| WebSocket | FastAPI WebSocket | `portal/websocket/connection_manager.py` | Existing `ConnectionManager` for real-time updates; heartbeat may use WebSocket or HTTP polling |
| Background tasks | Celery + Redis | `pyproject.toml` dependencies | Existing async task infrastructure; used for revocation stream polling, reconciliation processing |
| Testing | pytest, pytest-asyncio | `portal/tests/`, `tests/` | Existing test framework; `pytest-asyncio` for async test functions |
| Security scanning | bandit | `pyproject.toml` dev dependency, `.bandit-baseline.json` | Existing security baseline |

### 7.2 Cryptographic Signing

All signed tokens (lease tokens, capability tokens, witness statements, revocation entries, time anchors, journal seals, completion receipts) use detached signatures over canonical JSON payloads. The `SignedToken` envelope defined in `03_INTERFACE_SPECIFICATIONS.md` §1 specifies:

- `payload_b64` — base64url-encoded canonical JSON
- `signature_b64` — base64url-encoded detached signature
- `signer_id` — key identity
- `algorithm` — `Ed25519` or `ECDSA-P256-SHA256`

**Implementation choice:** Ed25519 is the preferred algorithm for all Brain-side and executor-side signatures. It is fast, compact, and deterministic. The `cryptography` Python library (already a transitive dependency via `python-jose`) provides Ed25519 support.

**Witness keys:** Witness identity keys are separate from Brain signing keys. Each witness has its own key pair. Witness key revocation is handled through C6 (revocation stream) with `entry_type = WITNESS_KEY_REVOCATION`.

**Key management:** Deferred to implementation planning (open question in `03_INTERFACE_SPECIFICATIONS.md` §18.2). The architecture does not prescribe HSM/KMS; it defines the `signer_id` field that allows any key management system to be plugged in.

### 7.3 Hash Chaining

The existing `portal/services/audit_service.py` already implements SHA-256 hash chaining for audit log entries. C12 (Audit Event Pipeline) will follow the same pattern:

- Each event carries a `hash_link` computed over the canonical serialization of the event payload plus the previous event's `hash_link`.
- The first event in a chain has `hash_link = SHA256(canonical_payload)`.
- Verification walks the chain and checks that each `hash_link` matches the recomputed hash.

C8 (Continuation Journal Store) uses the same hash-chaining pattern for journal entries, with the seal signature providing an additional tamper-evidence layer.

### 7.4 Tenant Isolation

The existing portal enforces tenant isolation at two levels:

1. **Database level** — PostgreSQL row-level security via `SET LOCAL` in `portal/database.py` `get_tenant_db` / `tenant_session`.
2. **Query level** — all SQLAlchemy queries filter on `tenant_id`.

The continuation components follow the same pattern:

- Brain-side components (C1, C2, C3, C6, C7, C10, C11, C12, C14) use `tenant_session` for database access.
- Executor-side components (C5, C8, C9) carry `tenant_id` in every data structure and validate it at every boundary.
- C4 (Witness Statement Service) is tenant-scoped: witness statements for tenant A cannot cover tenant B (ADR 2.2.4).
- C13 (Downstream Effect Identity Layer) validates `tenant_id` match before applying any effect.

### 7.5 Async Patterns

All components use async/await throughout, consistent with the existing portal:

- Service functions are `async def` and accept `AsyncSession` where database access is needed.
- FastAPI endpoints use `async def` with `Depends(get_db)` or `Depends(get_tenant_db)`.
- Background tasks (revocation stream polling, reconciliation processing) use Celery with async support or `asyncio` tasks.
- The `httpx` async client is used for executor-to-Brain and executor-to-witness HTTP calls.

### 7.6 Configuration

ADR-MC-001 Section 9.2 enumerates 18 required configuration settings. These will be added to the existing `portal/config.py` `Settings` class as Pydantic fields with defaults matching the ADR. The existing `get_settings()` cached accessor pattern applies.

Configuration transport to executors (how settings are delivered and capped by platform maximums) is deferred to implementation planning (open question in `03_INTERFACE_SPECIFICATIONS.md` §18.4).

### 7.7 No New External Dependencies

The implementation does not require any new external Python packages beyond what is already in `pyproject.toml`. The `cryptography` library (transitive dependency via `python-jose[cryptography]`) provides Ed25519 and ECDSA support. All other needs (FastAPI, SQLAlchemy, Pydantic, structlog, httpx, Celery, Redis) are already declared dependencies.

---

## 8. Proposed Module Structure

This section proposes a package layout for the implementation. It is a planning recommendation, not a committed structure. The layout follows existing portal conventions (`portal/services/`, `portal/models/`, `portal/routers/`, `portal/schemas/`).

```
portal/
  continuation/                      # New package for continuation components
    __init__.py
    shared/                          # Shared models and primitives
      __init__.py
      tokens.py                      # SignedToken, Fingerprint
      time_anchor.py                 # SignedTimeAnchor model
      enums.py                       # ContinuationClass, FinalState, etc.
      effect_identity.py             # StableEffectIdentity
    services/
      __init__.py
      time_anchor_service.py         # C14
      audit_event_pipeline.py        # C12
      policy_snapshot_registry.py    # C7
      local_state_cache.py           # C5
      lease_token_service.py         # C1
      revocation_stream.py           # C6
      capability_service.py          # C2
      heartbeat_endpoint.py          # C3
      witness_statement_service.py   # C4
      journal_store.py               # C8
      receipt_service.py             # C9
      effect_identity_layer.py       # C13
      reconciliation_engine.py       # C10
      conflict_review_queue.py       # C11
    models/                          # SQLAlchemy ORM models
      __init__.py
      time_anchor.py
      audit_event.py
      policy_snapshot.py
      lease.py
      revocation.py
      capability.py
      heartbeat.py
      witness.py
      journal.py
      receipt.py
      effect_record.py
      reconciliation.py
      conflict_review.py
    routers/                         # FastAPI routers (Brain-side endpoints)
      __init__.py
      heartbeat.py                   # C3 endpoint
      witness.py                     # C4 publish endpoint
      revocation.py                  # C6 stream endpoint
      reconciliation.py             # C10/C11 operator endpoints
    schemas/                         # Pydantic v2 request/response schemas
      __init__.py
      (mirrors services/ structure)
```

### 8.1 Rationale

- **`portal/continuation/`** — a new top-level package under `portal/` keeps continuation code separate from existing portal code. This respects the ADR-MC-001 Section 10 non-goal of not modifying Mission Control Foundation code. The existing `portal/services/mission_control_*.py` files remain unchanged.
- **`shared/`** — shared data models are defined once and imported by all services. This avoids circular imports and ensures consistency.
- **`services/`** — one file per component, matching the existing `portal/services/` convention.
- **`models/`** — SQLAlchemy ORM models, one file per domain aggregate, matching the existing `portal/models/` convention.
- **`routers/`** — FastAPI routers for Brain-side HTTP endpoints. Executor-side components (C5, C8, C9) do not have routers; they are library code called by the executor process.
- **`schemas/`** — Pydantic v2 request/response schemas for API endpoints, matching the existing `portal/schemas/` convention.

### 8.2 Test Structure

Tests follow the existing `portal/tests/` convention:

```
portal/
  continuation/
    tests/
      __init__.py
      test_time_anchor_service.py    # C14
      test_audit_event_pipeline.py   # C12
      test_policy_snapshot_registry.py  # C7
      test_local_state_cache.py      # C5
      test_lease_token_service.py    # C1
      test_revocation_stream.py      # C6
      test_capability_service.py     # C2
      test_heartbeat_endpoint.py     # C3
      test_witness_statement_service.py  # C4
      test_journal_store.py          # C8
      test_receipt_service.py        # C9
      test_effect_identity_layer.py  # C13
      test_reconciliation_engine.py  # C10
      test_conflict_review_queue.py   # C11
      test_integration_lifecycle.py   # End-to-end continuation lifecycle
      test_integration_recovery.py    # End-to-end recovery protocol
      test_tenant_isolation.py        # Cross-tenant access returns 404
      test_invariants.py              # All 15 ADR invariants
```

---

## 9. Cross-Cutting Concerns

### 9.1 Error Handling

All components follow the existing portal error handling pattern:

- Service-layer functions raise domain exceptions (e.g., `DuplicateCommandConflictError` in the existing command service).
- Routers catch domain exceptions and convert them to HTTP responses with appropriate status codes.
- The default decision is always STOP (ADR 2.3). Any unhandled error, unknown state, or validation failure causes the executor to stop and enter safe-hold state.
- Fail-closed is the universal policy for revocation (ADR 2.10), time (ADR 2.8), and policy (ADR 2.11).

### 9.2 Observability

All components emit structured log events via structlog, following the existing convention:

```python
log = structlog.get_logger(__name__)
log.info("continuation.capability_issued", capability_id=..., command_id=..., tenant_id=...)
```

C12 (Audit Event Pipeline) is the authoritative record; structlog logs are operational telemetry, not authoritative. The distinction is critical: structlog logs may be truncated or lost; C12 audit events are never truncated (ADR Invariant 11).

### 9.3 Correlation and Causation

The existing `portal/middleware/correlation_middleware.py` provides `request_id`, `correlation_id`, and `causation_id` context. Continuation components extend this:

- Every audit event (C12) carries a `causation_event_id` linking it to the prior event in the command's lifecycle.
- The causation chain projection (C12 `causation_chain`) assembles the full lineage for a command, with pagination metadata for the projection (the authoritative ledger is never truncated).
- The existing `MAX_CAUSATION_LINKS` projection cap applies only to the projection API, not to the ledger (ADR 2.13).

### 9.4 Security Boundaries

| Boundary | Enforcement |
|---|---|
| Brain ↔ Executor | Signed tokens (C1, C2, C14); executor cannot self-authorize |
| Executor ↔ Downstream | Signed capability + outage evidence (C13); downstream validates Brain signatures |
| Witness ↔ Executor | Signed witness statements (C4); executor validates witness signatures; self-exclusion enforced |
| Tenant ↔ Tenant | `tenant_id` validation at every component boundary; RLS at database level; 404 for cross-tenant access |
| Time ↔ Manipulation | Signed time anchors (C14); monotonic clock for durations; skew and rollback tolerance enforced |

---

## 10. ADR Invariant Coverage

This section maps all 15 ADR-MC-001 Section 7 invariants to the components and phases that enforce them. This is a planning-level mapping; detailed enforcement points are in `03_INTERFACE_SPECIFICATIONS.md` §17.

| ADR Inv # | Invariant (summary) | Primary Enforcement | Phase |
|---|---|---|---|
| 1 | No authoritative effects without valid lease | C1 `validate_lease`; C13 `check_effect` | 1, 3 |
| 2 | Expired lease cannot authorize continuation/effects | C1 `validate_lease` → `EXPIRED`; C2 `validate_capability` requires `lease_state=EXPIRED` | 1 |
| 3 | Capability unusable before lease expiry or after own expiry | C2 `validate_capability` → `BEFORE_NOT_VALID_BEFORE` / `AFTER_NOT_VALID_AFTER` | 1 |
| 3a | Only latest-lease capability may be exercised; superseded rejected | C2 `is_superseded` / `supersede_capability`; C13 rejects superseded `capability_id` | 1, 3 |
| 4 | Continuation is never the default | C2 issues capabilities only on explicit request; `ContinuationClass.STOP` default | 1 |
| 5 | Continuation cannot exceed its bounded envelope | C2 `max_continuation_duration` / `max_continuation_operations`; C8 journal seq limit | 1, 3 |
| 6 | Every continuation produces an immutable signed receipt | C9 `generate_receipt` / `verify_receipt` | 3 |
| 7 | Every continuation is reconciled before terminal state | C10 `reconcile_command` | 4 |
| 8 | Conflicting results / non-reversible effects never resolve silently | C10 `detect_conflicts`; C11 enqueue | 4 |
| 9 | Cross-tenant continuation is impossible | All components enforce `tenant_id` match at boundary | 0–4 |
| 10 | Idempotency preserved across continuation, replay, normal execution | C13 `StableEffectIdentity`; C8 journal `SKIPPED_DUPLICATE` | 3 |
| 11 | Authoritative audit storage is never truncated | C12 `CausationChainProjection.truncated` (projection only) | 0 |
| 12 | Policy snapshot bounded to exact pinned hash | C7 `validate_hash`; C2 `policy_snapshot_hash` | 0, 1 |
| 13 | Revocation knowledge must be fresh; absence ≠ permission | C6 `cache_age` / watermark; C2 `revocation_watermark_required` | 1 |
| 14 | Time cannot be manipulated to extend authority | C14 `check_skew` / `check_rollback`; monotonic time bounds | 0 |
| 15 | High-risk/irreversible side effects cannot be produced during continuation | C2 rejects `CLASS_3` issuance; C13 `CLASS_3_PROHIBITED` | 1, 3 |

All 15 invariants are covered by the five-phase implementation plan. No invariant is left unenforced or deferred.

---

## 11. Open Questions and Deferrals

The following are deliberately deferred to later planning documents or implementation ADRs. They do not block this architecture document.

1. **Persistence backend selection** for C12 (audit ledger) and C8 (journal store) — append-only log vs. SQLAlchemy table with hash chaining. The existing `portal/services/audit_service.py` uses SQLAlchemy with hash chaining; C12 may follow the same pattern or adopt a dedicated append-only log. Deferred to document 04 (persistence schema).

2. **Signing key management** — HSM/KMS integration for Brain signing keys and witness identity keys. The architecture defines `signer_id` to allow any KMS to be plugged in. Deferred to a separate security ADR.

3. **Witness topology** — concrete witness deployment, peer discovery, and the BFT-vs-CFT election. ADR 2.2.4 allows a CFT first implementation with documentation. Deferred to a deployment planning document.

4. **Tenant configuration transport** — how the 18 Section 9.2 configuration settings are delivered to executors and capped by platform maximums. Deferred to document 04 or a configuration management document.

5. **Recovery notification channel** — how executors are notified of Brain recovery (heartbeat channel vs. witness broadcast). ADR 2.6.1 states "executors are notified of recovery through the heartbeat channel." The implementation may supplement with witness broadcast. Deferred to implementation.

6. **Module structure confirmation** — the `portal/continuation/` package layout proposed in Section 8 is a recommendation. The final structure may be adjusted during implementation based on import graph constraints and existing portal conventions. Deferred to the implementation plan (document 02).

7. **Executor integration** — how executor-side components (C5, C8, C9) integrate with the existing executor agent codebase (`agents/`). The Sigma agent (`agents/sigma/`) is a CI/CD gate guardian, not a command executor; the actual executor integration point depends on the Brain's dispatch implementation, which is not yet built. Deferred to a separate executor integration document.

---

## 12. Relationship to Existing Code

This architecture is additive. It does not modify existing Mission Control Foundation code:

- `portal/services/sigma_gate.py` — unchanged. The Sigma gate remains BLOCKED. `is_cancellation_blocked()` continues to return `True`. The gate transitions to SATISFIED only after all 14 components are implemented and certified per ADR-MC-001 Section 13.
- `portal/services/mission_control_command_service.py` — unchanged. The existing refusal-only command substrate continues to operate.
- `portal/routers/mission_control.py` — unchanged. The existing read-only projection endpoints continue to operate.
- `portal/models/mission_control_command.py` — unchanged. The existing command ledger models are not modified.
- `portal/services/audit_service.py` — may be extended or wrapped by C12, but the existing `audit()` function and hash chain are not modified. C12 is a new service that may delegate to the existing audit infrastructure or provide its own append path. This decision is deferred to document 04.

The new `portal/continuation/` package is self-contained. It imports from `portal/database.py` (for `AsyncSession`, `Base`, `tenant_session`) and `portal/config.py` (for `Settings`), but does not modify them.

---

## 13. Summary

This document decomposes the executor continuation capability from ADR-MC-001 into 14 implementation components organized into five layers and five phases. The architecture is:

- **Layered** — five layers with no upward dependencies; each layer builds on the one below.
- **Dependency-ordered** — the topological build order ensures that no component is built before its dependencies.
- **Consistent with the existing stack** — Python 3.11+, FastAPI, SQLAlchemy 2.0 async, Pydantic v2, structlog, PostgreSQL with RLS.
- **Additive** — no existing code is modified; all new code lives in a new `portal/continuation/` package.
- **Invariant-complete** — all 15 ADR invariants are mapped to components and phases; no invariant is deferred.
- **Planning only** — no runtime code, no API changes, no persistence changes, no deployment.

The Sigma gate remains BLOCKED. This document authorizes implementation planning, not implementation execution. Implementation requires separate ADRs, branches, and authorizations per ADR-MC-001 Section 10.

---

**End of document.** This is a planning artifact only. No runtime code is authorized by this document. Implementation requires separate ADRs, branches, and authorizations per ADR-MC-001 Section 10.