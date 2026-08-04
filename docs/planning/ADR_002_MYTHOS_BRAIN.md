# ADR 002: Mythos Brain — Unified Execution Coordination

**Status:** Proposed
**Date:** 2026-08-04
**Author:** Manus AI
**Decision ID:** ADR-002
**Scope:** Phase 3 Operational Intelligence — Central Orchestration

> The ADR remains **Proposed** until the Project Owner and Security Reviewer formally record their decisions in Section 8. No part of this document should be read as Accepted.

---

## 1. Context and Problem Statement
The SintraPrime platform has evolved into a multi-agent, multi-module system. Currently, authority is distributed across the `portal`, `agents/`, and `workflow_builder/`, leading to fragmented audit trails, inconsistent governance enforcement, and the lack of a "kill switch" for autonomous actions. We need a central **Execution Coordinator** to manage the lifecycle of all system intents.

---

## 2. Proposed Architecture: The Mythos Brain
The Mythos Brain is defined as the **Central Execution Coordinator** for the entire platform. It does not own domain state (e.g., it doesn't own "Matter" data), but it owns the **lifecycle of execution**.

### 2.1 Unified Execution Protocol (UEP)
All execution requests, regardless of origin, must implement the UEP, which enforces:
- **Deterministic Identity:** Every execution must be bound to a verified `actor_id` and `tenant_id` via the `portal/auth` layer.
- **Correlation Propagation:** Mandatory use of `X-Request-ID` and causation chains for cross-module auditability.
- **Idempotency Keys:** All state-changing operations must provide a client-generated idempotency key to prevent duplicate execution in distributed environments.

### 2.2 Authority Boundaries
- **Mythos Brain (Coordinator):** Owns execution coordination, intent state, dispatch state, and control-plane policy evaluation. Specifically, it owns the "intent" ledger, the execution state machine (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED), and HITL escalation gates. The Brain dispatches and tracks execution but does not own domain entities.
- **Domain Services (Authoritative Records):** Services such as `portal`, `trust_law`, `legal_authority`, and `governed_inference` retain authoritative domain records. The Brain does not replicate or override domain data; it correlates and governs the execution lifecycle around it.
- **Read-Only Queries:** Read-only queries need not route through the Brain unless policy enforcement or correlation requires it. Synchronous portal reads, cached lookups, and domain-service queries proceed directly against their owning services.
- **Executors (Workers):** Modules like `workflow_builder` or `agents/nova` act as execution engines that receive instructions from the Brain and report progress. Executors are operationally stateless where practical, but may retain domain-owned state under defined boundaries (e.g., a legal-authority executor retains legal-jurisdiction records it is authoritative for). The Brain does not own that state; it only governs the execution envelope around it.
- **Mission Control:** Serves as the read-only visual projection of the Brain's active state.

### 2.3 Delivery Semantics
The Brain and executors cooperate on a reliable delivery model with the following explicit guarantees:

- **At-Least-Once Delivery:** The Brain dispatches each intent at least once. Because the network may duplicate messages, executors must tolerate redelivery and must not assume exactly-once transport.
- **Idempotent Side Effects:** An executor must produce exactly one externally observable effect for repeated delivery of the same idempotency key. Idempotency is defined at the effect boundary, not merely at the key boundary — re-delivery with the same key must not create a duplicate external record, send a duplicate message, or charge a duplicate payment.
- **Transactional Outbox:** The Brain writes intent dispatch records to a transactional outbox in the same database transaction as the state change that triggered them. This guarantees that a state change and its corresponding dispatch are atomically committed; there is no window in which a state change is visible without its dispatch record.
- **Inbox / Deduplication:** Executors maintain an inbox of processed idempotency keys to deduplicate redelivered intents. An executor that has already recorded a given key skips re-execution and returns the original result.
- **Replay:** The Brain can replay an intent from the outbox. Executors must treat replay identically to original delivery — the same idempotency key, the same side-effect contract, and the same audit chain apply. Replay is not a special path; it is a re-dispatch.
- **Lease Ownership:** An executor acquires a time-bounded lease on a task before processing. No other executor processes the same task while the lease is valid. This prevents duplicate concurrent execution without requiring distributed locks held for the full task duration.
- **Heartbeat and Lease Expiry:** Executors send heartbeats to renew leases for long-running tasks. If heartbeats stop, the lease expires and the task becomes eligible for redelivery to another executor. Expiry does not imply failure — the original executor may simply have lost leadership — but redelivery is safe because side effects are idempotent.
- **Bounded Retries:** The Brain retries failed dispatches with exponential backoff up to a configurable maximum. The backoff schedule and retry cap are policy-driven, not hard-coded, so that noisy-neighbor and thundering-herd pathologies can be tuned without code changes.
- **Dead-Letter Handling:** After the maximum number of retries is exhausted, the intent is moved to a dead-letter queue for manual intervention. Dead-lettered intents are not silently dropped; they surface in Mission Control and require an operator action to re-dispatch, permanently fail, or discard.
- **Poison-Message Handling:** Messages that repeatedly fail validation — as distinct from transient execution failures — are quarantined and alerted. A poison message is a structural defect (e.g., a dispatch envelope that cannot be deserialized), not a retryable runtime error, and it must not consume retry budget indefinitely.
- **Causation and Correlation Chains:** Every dispatch carries the originating intent ID and the full causal chain (parent intent, triggering event, actor) for auditability. An executor that fans out sub-intents propagates the chain so that any leaf action can be traced back to its root intent without ambiguity.

### 2.4 Cancellation Scopes
The Brain provides three scoped cancellation controls. A universal, unscoped kill switch is explicitly rejected — each control is bounded by scope, permissioned, audited, and recoverable.

Every cancellation control, regardless of scope, must satisfy the following invariants:
- **Explicit permission:** The caller must hold the role required for that scope; no anonymous or implicit cancellation is permitted.
- **Immutable audit event:** Each cancellation writes an immutable audit event recording the caller, scope, target, timestamp, and reason.
- **Reason:** The caller must supply a human-readable reason; reasonless cancellation is rejected.
- **Blast-radius display:** Before confirmation, the Brain returns the set of executions that will be affected so the caller understands the scope of the action.
- **Confirmation:** The caller must explicitly confirm after seeing the blast radius; a single-step fire-and-forget cancellation is not permitted for tenant or platform scopes.
- **Recovery procedure:** Each cancellation records or links to a recovery procedure so affected executions can be resumed, re-dispatched, or permanently retired with intent.

The three scopes are:

1. **Execution-Scoped Cancellation.** Stops a specific execution by ID. Permissioned to the execution owner or a tenant admin. The audit event records the execution ID, caller, and reason. Blast-radius is the single execution. Confirmation may be inline (single execution). Recovery: the intent may be re-dispatched by the owner if the cancellation was corrective rather than terminal.
2. **Tenant-Scoped Emergency Stop.** Stops all executions for a specific tenant. Permissioned to tenant admins only. The audit event records the tenant ID, caller, reason, and the full list of halted executions. Blast-radius display enumerates every active execution under the tenant. Confirmation is a second explicit action after the blast-radius display is shown. Recovery: a documented restart procedure must be linked; halted executions are re-queued for re-dispatch unless explicitly retired.
3. **Platform Emergency Stop.** Stops all executions platform-wide. Permissioned to platform operators only. The audit event is mandatory and must reference an incident report. Blast-radius display enumerates all active executions across all tenants. Confirmation is a second explicit action and requires an incident-report reference. Recovery: a mandatory recovery procedure must be linked and executed before new intents are accepted; the Brain remains in degraded read-only mode until the operator formally clears the emergency state.

Cancellation signals are prioritized on the message bus so they bypass execution queues, but they are never unscoped, unpermissioned, or unaudited.

### 2.5 Security and Failure Boundaries

#### Tenant Isolation and Identity
- **Tenant Isolation:** One tenant's execution cannot affect another. All dispatch envelopes carry `tenant_id`, and executors enforce isolation at the data and execution boundary — a dispatch for tenant A must never read or mutate tenant B's records, and an executor must not share mutable in-memory state across tenants.
- **Actor Delegation:** The Brain propagates `actor_id` and the actor's effective permissions to executors via signed dispatch envelopes. Executors do not re-derive permissions from ambient context; they honor the delegation in the envelope and reject envelopes whose delegation is missing, stale, or unsigned.
- **Service-to-Service Authentication:** The Brain and executors authenticate via mutual TLS or signed JWT tokens. A dispatch from an unauthenticated or unknown executor identity is rejected; an executor that cannot verify the Brain's identity rejects the dispatch.
- **Signed or Authenticated Dispatch Envelopes:** All dispatch messages carry a signature or auth token that executors verify before processing. An executor that receives an unsigned or tampered envelope quarantines it and alerts — it does not process it speculatively.

#### Policy Versioning and Stale Approvals
- **Policy-Version Snapshots:** The Brain records which policy version was active when an intent was authorized. The authorization decision is bound to that version, not to a floating "current policy" pointer, so that a later policy change does not retroactively rewrite the basis of an in-flight decision.
- **Stale Approval Invalidation:** If a policy has tightened since an approval was granted, the approval is invalidated and the intent must be re-authorized under the current policy before dispatch. The Brain compares the approval's policy-version snapshot against the active version at dispatch time and blocks dispatch when the version has tightened in a way that affects the intent.

#### Resilience and Split-Brain
- **Split-Brain Prevention:** The Brain uses lease-based leadership. Only one active leader accepts new intents; followers are read-only. If the leader loses its lease (e.g., network partition, process death), a follower acquires leadership only after the previous lease expires, preventing two simultaneous leaders.
- **Brain Unavailability Behavior:** If the Brain becomes unavailable, in-flight executions continue to completion against their already-acquired leases; new intents are queued, not rejected; the system operates in degraded mode. The platform does not hard-stop all execution because the coordinator is unreachable.
- **Degraded Read-Only Operation:** When the Brain is partially unavailable, read-only queries and already-dispatched executions continue; new dispatches are paused until the Brain recovers. Mission Control reflects the degraded state explicitly so operators are not misled into believing the system is fully healthy.
- **Executor Compromise Handling:** If an executor is compromised, its credentials are revoked immediately, its in-flight tasks are redelivered to other executors via lease expiry and outbox replay, and an audit trail is preserved for forensic review. Compromise of one executor does not grant access to other executors' credentials or tenant data.

#### Recovery Objectives
- **RTO and RPO Targets:** Brain state store Recovery Time Objective (RTO) ≤ 5 minutes; Recovery Point Objective (RPO) ≤ 30 seconds. These targets assume synchronous replication of the intent ledger and transactional outbox to a standby.
- **Recovery and Replay Procedure:** On Brain recovery, the outbox is drained, in-flight intents are checked against executor acknowledgments, and unconfirmed intents are replayed. The recovery procedure is deterministic: drain outbox → reconcile acknowledgments → replay unconfirmed → resume accepting new intents. No operator judgment is required for the standard recovery path.

#### Governance Enforcement
- **Policy Enforcement Point (PEP):** The Brain acts as the PEP, validating every intent against the `governed_inference` layer before dispatch. The Brain does not bypass the PEP for its own internal dispatches.
- **Failure Isolation:** A failure in an executor (e.g., an agent crash) must not corrupt the Brain's intent ledger. Executor failures are observed as lease expiry or negative acknowledgment, never as ledger mutation.
- **Panic Mode:** In the event of a detected governance breach, the Brain enters a "Panic Mode," locking all outbound API connectors and requiring administrative reset. Panic Mode is the platform emergency stop triggered by the Brain itself; it follows the same audit and recovery rules as Section 2.4 scope 3.

---

## 3. Consequences
### Positive
- **Single Source of Truth:** One ledger for all system actions (sync, async, autonomous).
- **Hardened Governance:** Centralized enforcement of "Refusal-Only" and "HITL" policies.
- **Unified Observability:** Simplifies the implementation of the Mission Control dashboard.
- **Audit Integrity:** Guarantees that every side effect in the system is correlated to a high-level intent.

### Negative / Risks
- **Centralized Complexity:** The coordinator could become a bottleneck if it attempts to manage domain-specific logic.
- **Performance:** Synchronous coordination adds latency; requires a robust async-first message bus (Redis/Celery).
- **Single Point of Failure:** If the Brain's state store fails, all system execution stops.

---

## 4. Alternatives Considered
| Option | Pros | Cons | Verdict |
| :--- | :--- | :--- | :--- |
| **Distributed Authority** | No single bottleneck; faster local execution. | Impossible to enforce global governance; audit gaps. | ❌ Rejected |
| **Portal-Only Authority** | Leverages existing API security. | Cannot handle background tasks or autonomous agent loops. | ❌ Rejected |
| **Mythos Brain (Central)** | Unified control; audit integrity; scalable governance. | Higher initial design complexity. | Preferred — Pending Governance Approval |

---

## 5. Architecture Diagram
```mermaid
graph TD
    User((User/Client)) -->|API Request| Portal[Portal API]
    System[System Events] -->|Trigger| Scheduler[Scheduler]
    Agent[Autonomous Loop] -->|Intent| Agents[Agent Swarm]
    subgraph Mythos Brain (Coordinator)
        UEP[Unified Execution Protocol]
        Ledger[(Intent Ledger)]
        Policy[Governance Policy Engine]
        Escalation[HITL Gateway]
    end
    Portal --> UEP
    Scheduler --> UEP
    Agents --> UEP
    UEP --> Policy
    Policy -->|Requires Review| Escalation
    Policy -->|Authorized| Ledger
    subgraph Executors (Stateless)
        WF[Workflow Engine]
        Nova[Nova Executor]
        Inference[Governed Inference]
    end
    Ledger -->|Dispatch| WF
    Ledger -->|Dispatch| Nova
    Ledger -->|Dispatch| Inference
```

---

## 6. Acceptance Criteria for Phase 3
- [ ] **One Protocol:** A single Python base class or Protocol that all executors must implement, covering dispatch, acknowledgment, heartbeat, and lease semantics.
- [ ] **Authority Boundary:** `agents/` and `workflow_builder/` no longer manage their own execution persistence or dispatch state; they report to the Brain. Domain services retain authoritative domain records as specified in Section 2.2.
- [ ] **Idempotent Side Effects:** All state-changing executor contracts must pass duplicate-delivery tests proving one externally observable effect for repeated delivery of the same idempotency key. Each executor contract ships a duplicate-delivery test case; a contract without a passing duplicate-delivery test does not meet the bar.
- [ ] **Scoped Cancellation Latency:** Cancellation latency is measured by execution class, not by a universal two-second target:
  - Execution-scoped cancellation: the target execution transitions to CANCELLED within 2 seconds of a confirmed, permissioned cancellation request.
  - Tenant-scoped emergency stop: all active executions for the tenant transition to CANCELLED within 5 seconds of a confirmed, permissioned stop; blast-radius display and confirmation are not counted toward the latency budget.
  - Platform emergency stop: all active executions platform-wide transition to CANCELLED within 10 seconds of a confirmed, permissioned stop and mandatory incident-report reference; blast-radius display, confirmation, and incident-report linking are not counted toward the latency budget.
  - Each cancellation class produces an immutable audit event with caller, scope, reason, and recovery-procedure reference.
- [ ] **Human Escalation:** Any action with `risk_level > threshold` creates a blocking `ApprovalRequest` in the database, bound to the policy-version snapshot active at authorization time (Section 2.5).

---

## 7. Explicit Non-Goals
The Mythos Brain does **NOT**:
- Perform autonomous legal conclusions or filings without professional review.
- Manage domain state (e.g., Matter details, Financial records) directly.
- Execute code outside of the pre-defined "Safe-Zone" (Airlock).
- Replace the `governed_inference` router, but rather consumes its outputs.

---

## 8. Signatures
| Role | Name | Date | Decision |
| :--- | :--- | :--- | :--- |
| **Project Owner** | Isiah Howard | 2026-08-04 | Proposed |
| **Architect** | Manus AI | 2026-08-04 | Proposed |
| **Security Reviewer** | Sigma Agent | 2026-08-04 | Pending |
