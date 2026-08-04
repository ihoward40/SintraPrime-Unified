# ADR 002: Mythos Brain — Unified Execution Coordination

**Status:** Accepted

> ADR-002 was accepted on 2026-08-04 after owner review (REQUEST_CHANGES, resolved) and Sigma security review (APPROVE_WITH_CONDITIONS). The condition — defining explicit criteria for optional executor continuation during Brain unavailability — is to be satisfied in the implementation ADR or a narrowly scoped amendment.

## 1. Context and Problem Statement
The SintraPrime platform has evolved into a multi-agent, multi-module system. Currently, authority is distributed across the `portal`, `agents/`, and `workflow_builder/`, leading to fragmented audit trails, inconsistent governance enforcement, and the lack of coordinated cancellation for autonomous actions. We need a central **Execution Coordinator** to manage the lifecycle of all system intents.

---

## 2. Proposed Architecture: The Mythos Brain
The Mythos Brain is defined as the **Central Execution Coordinator** for the entire platform. It does not own domain state (e.g., it doesn't own "Matter" data), but it owns the **lifecycle of intent**—from ingestion to terminal state (Success/Failure/Cancelled).

### 2.1 Unified Execution Protocol (UEP)
All execution requests, regardless of origin, must implement the UEP, which enforces:
- **Deterministic Identity:** Every execution must be bound to a verified `actor_id` and `tenant_id` via the `portal/auth` layer.
- **Correlation Propagation:** Mandatory use of `X-Request-ID` and causation chains for cross-module auditability.
- **Idempotency Keys:** All state-changing operations must provide a client-generated idempotency key to prevent duplicate execution in distributed environments.

### 2.2 Authority Boundaries
- **Mythos Brain (Coordinator):** Owns intent records, execution-control state, dispatch attempts, approvals, cancellation state, correlation, and causation. The Brain must not become a universal domain database.
- **Domain Services:** Modules such as `portal`, `trust_law`, `legal_authority`, and `workflow_builder` retain authoritative domain records and domain transactions. The Brain does not own or duplicate domain data.
- **Executors (Workers):** Modules like `agents/nova` act as execution engines that receive instructions from the Brain and report progress. Executors may retain governed checkpoints and domain-owned operational state under defined boundaries.
- **Read-Only Queries:** Read-only queries bypass the Brain unless policy evaluation, correlation, or audit requirements require routing through it.
- **Mission Control:** Serves as the read-only visual projection of the Brain's active state.

### 2.3 Durable Delivery Semantics
The Brain guarantees durable dispatch of authorized intents. Retry safety follows from the delivery infrastructure, not merely from declaring executors idempotent.

- **At-Least-Once Delivery:** The Brain guarantees that every authorized intent is dispatched to an executor at least once. Executors must tolerate redelivery.
- **Transactional Outbox:** Dispatch records are written to a transactional outbox in the same database transaction as the state change that triggered them. This ensures no intent is lost if the process crashes after authorization but before dispatch.
- **Executor Inbox and Deduplication:** Executors maintain an inbox of processed idempotency keys. On redelivery, the executor detects the duplicate and returns the cached result without re-executing the side effect.
- **Idempotency-Key Scope and Retention:** Idempotency keys are scoped to the tenant and the executor contract. Keys are retained for a configured retention period to handle late redelivery. After retention expiry, the key is eligible for garbage collection.
- **Lease Ownership:** An executor acquires a time-bounded lease on a task before processing. No other executor processes the same task while the lease is valid.
- **Heartbeat:** Executors send heartbeats to renew the lease while processing is active. If heartbeats stop, the lease expires and the task becomes eligible for redelivery.
- **Lease Expiration:** On lease expiry, the Brain may reassign the task to another executor. The original executor must stop processing and discard any partial results that were not committed.
- **Replay Behavior:** The Brain can replay an intent from the outbox. Executors must treat replay identically to original delivery — the inbox deduplication ensures only one side effect is produced.
- **Bounded Retry Classes:** The Brain retries failed dispatches with jittered exponential backoff. Retry classes are defined by failure type: transient (network, timeout), application (validation, business rule), and infrastructure (database, queue). Each class has a configurable maximum retry count and backoff ceiling.
- **Dead-Letter Queue:** After max retries are exhausted, the intent is moved to a dead-letter queue for manual intervention. Dead-lettered intents are alerted and require explicit operator action to requeue or discard.
- **Poison-Message Quarantine:** Messages that repeatedly fail validation (not execution) are quarantined and alerted. Poison messages are not retried automatically because the failure is deterministic, not transient.
- **Causation-Chain Preservation:** Every dispatch carries the originating intent ID and the full causal chain. This enables audit reconstruction and debugging of complex multi-step workflows.
- **Partial-Failure Handling:** If an executor completes some but not all side effects, the Brain records the partial state. Recovery is handled by the replay mechanism — the executor's inbox deduplication prevents duplicate side effects on the completed portions.
- **Failure Isolation:** The Coordinator (Brain) is strictly isolated from the Executors. Failure of an executor does not impact the stability or state of the coordinator.

### 2.4 Cancellation Controls
The Brain provides scoped cancellation to ensure system safety and low-latency response. A universal unscoped kill switch is explicitly rejected — every control must be scoped, permissioned, and audited.

- **Execution-Scoped Cancellation:** Stops a specific execution by ID. Permissioned to the execution owner or tenant admin. The control requires: explicit permission, reason, immutable audit event, blast-radius preview, confirmation, and recovery procedure.
- **Tenant-Scoped Emergency Suspension:** Suspends all executions for a specific tenant. Permissioned to tenant admins. The control requires: explicit permission, reason, immutable audit event, blast-radius preview, confirmation, and recovery procedure.
- **Platform Break-Glass Emergency Suspension:** Suspends all executions platform-wide. Permissioned to platform operators only with elevated authorization. The control requires: explicit permission, reason, immutable audit event, blast-radius preview, confirmation, recovery procedure, and a mandatory incident record. This is the most destructive control and must be used only for governance breaches or safety-critical situations.
- **Prioritized Delivery:** Cancellation and suspension signals are prioritized over standard execution dispatch, bypassing standard queues to ensure immediate effect.

### 2.5 Security and Failure Boundaries
- **Policy Enforcement Point (PEP):** The Brain acts as the PEP, validating every intent against the `governed_inference` layer before dispatch.
- **Tenant Isolation:** One tenant's execution cannot affect another. All dispatch envelopes carry `tenant_id` and executors enforce isolation at the tenant boundary.
- **Actor Delegation:** The Brain propagates `actor_id` and permissions to executors via authenticated dispatch envelopes. Executors do not accept unsigned or unauthenticated dispatch.
- **Service-to-Service Authentication:** The Brain and executors authenticate via mutual TLS or signed JWT tokens. No executor accepts a dispatch without verifying the Brain's identity.
- **Authenticated or Signed Dispatch Envelopes:** All dispatch messages carry a signature or auth token that executors verify before processing. This prevents forged dispatch.
- **Policy-Version Snapshots:** The Brain records which policy version was active when an intent was authorized. This prevents stale approvals from bypassing updated policies.
- **Stale Approval Invalidation:** If a policy has tightened since an approval was granted, the approval is invalidated and the intent must be re-authorized under the current policy version.
- **Privilege Boundaries:** Executors operate with least-privilege credentials. The Brain does not grant executors permissions beyond what the originating actor's policy allows.
- **Executor-Compromise Response:** If an executor is compromised, its credentials are revoked, its in-flight tasks are redelivered to other executors, and a full audit trail is preserved for forensic review.
- **Split-Brain Prevention:** The Brain uses lease-based leadership. Only one active leader accepts new intents. Followers are read-only. If the leader loses its lease, a follower takes over with no split-brain window.
- **Brain Unavailability Behavior:** If the Brain is unavailable, in-flight executions continue to completion. New intents are queued and held. The system operates in degraded mode — no new dispatches, no new cancellations, but existing work is not lost.
- **Degraded Read-Only Operation:** When the Brain is partially unavailable, read-only queries (including Mission Control dashboard) continue to function against the last-known state. New dispatches are paused until the Brain recovers.
- **In-Flight Execution Behavior:** In-flight executions are not cancelled by Brain unavailability. They continue under their existing lease. If the lease expires while the Brain is still unavailable, the executor may optionally continue processing if it has local state to complete the task, but must report completion when the Brain recovers.
- **Recovery and Replay Authority:** On Brain recovery, the outbox is drained. In-flight intents are checked against executor acknowledgments. Unconfirmed intents are replayed. The recovery procedure is deterministic and auditable.
- **Panic Mode:** In the event of a detected governance breach, the Brain enters "Panic Mode," locking all outbound dispatch, requiring administrative reset. This is the governance-breach equivalent of the platform break-glass suspension.
- **Failure Isolation:** A failure in an executor (e.g., an agent crash) must not corrupt the Brain's intent ledger.
- **RTO Target:** Brain state store Recovery Time Objective: ≤ 5 minutes (provisional — requires implementation validation).
- **RPO Target:** Brain state store Recovery Point Objective: ≤ 30 seconds (provisional — requires implementation validation).

---

## 3. Consequences
### Positive
- **Single Source of Truth:** One ledger for all system actions (sync, async, autonomous).
- **Hardened Governance:** Centralized enforcement of "Refusal-Only" and "HITL" policies.
- **Unified Observability:** Simplifies the implementation of the Mission Control dashboard.
- **Audit Integrity:** Guarantees that every side effect in the system is correlated to a high-level intent.

### Negative / Risks
- **Centralized Complexity:** The coordinator could become a bottleneck if it attempts to manage domain-specific logic.
- **Transport Requirements:** The Brain requires a transport layer that supports durable delivery, acknowledgments, leasing, retries, priority control messages, replay, observability, dead-letter handling, and tenant isolation. Technology selection (e.g., Redis, Celery, RabbitMQ, Kafka) belongs in a later implementation ADR — it is not predetermined by this architecture.
- **Single Point of Failure:** If the Brain's state store fails, all new system execution stops until recovery. In-flight executions continue under degraded mode. RTO/RPO targets (5 min / 30 sec) are provisional and require implementation validation.

---

## 4. Alternatives Considered
| Option | Pros | Cons | Verdict |
| :--- | :--- | :--- | :--- |
| **Distributed Authority** | No single bottleneck; faster local execution. | Impossible to enforce global governance; audit gaps. | ❌ Rejected |
| **Portal-Only Authority** | Leverages existing API security. | Cannot handle background tasks or autonomous agent loops. | ❌ Rejected |
| **Mythos Brain (Central)** | Unified control; audit integrity; scalable governance. | Higher initial design complexity. | ✅ Accepted |

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
        Outbox[(Transactional Outbox)]
        Policy[Governance Policy Engine]
        Escalation[HITL Gateway]
    end
    Portal --> UEP
    Scheduler --> UEP
    Agents --> UEP
    UEP --> Policy
    Policy -->|Requires Review| Escalation
    Policy -->|Authorized| Ledger
    Ledger --> Outbox
    subgraph Executors (Stateless)
        WF[Workflow Engine]
        Nova[Nova Executor]
        Inference[Governed Inference]
    end
    Outbox -->|Dispatch| WF
    Outbox -->|Dispatch| Nova
    Outbox -->|Dispatch| Inference
    WF -.->|Heartbeat| Ledger
    Nova -.->|Heartbeat| Ledger
    Inference -.->|Heartbeat| Ledger
```

---

## 6. Acceptance Criteria for Phase 3
- [ ] **One Protocol:** A single Python base class or Protocol that all executors must implement.
- [ ] **Authority Boundary:** `agents/` and `workflow_builder/` no longer manage their own persistence; they report to the Brain. Domain services retain authoritative domain records.
- [ ] **Durable Delivery:** Every state-changing executor contract must pass duplicate-delivery certification proving one externally observable effect for repeated delivery of the same idempotency key.
- [ ] **Cancellation — Execution-Scoped:** An execution-scoped cancellation signal halts a running execution within target ≤ 2 seconds (requires implementation testing; may vary by execution class).
- [ ] **Cancellation — Tenant-Scoped:** A tenant-scoped emergency suspension halts all executions for a tenant within target ≤ 5 seconds (requires implementation testing).
- [ ] **Cancellation — Platform Break-Glass:** A platform break-glass suspension halts all executions platform-wide within target ≤ 10 seconds (requires implementation testing; requires incident record and elevated operator authorization).
- [ ] **Human Escalation:** Any action with `risk_level > threshold` creates a blocking `ApprovalRequest` in the database.
- [ ] **Stale Approval Invalidation:** If a policy version has tightened since an approval was granted, the approval is automatically invalidated and the intent requires re-authorization.

> Latency targets for cancellation are provisional and require implementation testing. They may vary by execution class, network conditions, and executor responsiveness.

---

## 7. Explicit Non-Goals
The Mythos Brain does **NOT**:
- Perform autonomous legal conclusions or filings without professional review.
- Manage domain state (e.g., Matter details, Financial records) directly.
- Execute code outside of the pre-defined "Safe-Zone" (Airlock).
- Replace the `governed_inference` router, but rather consumes its outputs.
- Predetermine the transport technology (Redis, Celery, RabbitMQ, Kafka, etc.). Technology selection belongs in a later implementation ADR.

---

## 8. Signatures
| Role | Name | Date | Decision |
| :--- | :--- | :--- | :--- |
| **Project Owner** | Isiah Howard | 2026-08-04 | APPROVED (REQUEST_CHANGES resolved) |
| **Architect** | Manus AI | 2026-08-04 | Proposed |
| **Security Reviewer** | Sigma Agent | 2026-08-04 | APPROVE_WITH_CONDITIONS |

### 8.1 Owner Review Notes (Isiah Howard, 2026-08-04)

The architecture direction is approved — a central execution coordinator is needed. The following six changes were required and have been implemented in the ADR body:

1. **Status consistency (Section 4):** Alternatives table verdict changed to "Proposed — Pending Governance Approval." Will not advance to Approved until both reviews are recorded.

2. **Authority boundaries (Section 2.2):** Expanded to clarify that the Brain owns intent records, execution-control state, dispatch attempts, approvals, cancellation state, correlation, and causation. Domain services retain authoritative domain records and domain transactions. Read-only queries bypass the Brain unless policy/correlation/audit requires it. Executors may retain governed checkpoints and domain-owned operational state. The Brain must not become a universal domain database.

3. **Durable delivery semantics (Section 2.3):** Replaced the simplified delivery section with explicit definitions for: at-least-once delivery, transactional outbox, executor inbox and deduplication, idempotency-key scope and retention, lease ownership, heartbeat, lease expiration, replay behavior, bounded retry classes, dead-letter queue, poison-message quarantine, causation-chain preservation, and partial-failure handling. Removed any implication that retry safety follows merely from declaring executors idempotent.

4. **Cancellation controls (Section 2.4):** Replaced "Global Halt," "Workstream Cancellation," and "Executor Revocation" with three scoped controls: execution-scoped cancellation, tenant-scoped emergency suspension, and platform break-glass emergency suspension. Each requires explicit permission, reason, immutable audit event, blast-radius preview, confirmation, and recovery procedure. The platform-wide control additionally requires an incident record and elevated operator authorization. A universal unscoped kill switch is explicitly rejected.

5. **Transport neutrality (Section 3):** Removed Redis/Celery as a predetermined architecture choice. Replaced with required transport capabilities: durable delivery, acknowledgments, leasing, retries, priority control messages, replay, observability, dead-letter handling, and tenant isolation. Technology selection belongs in a later implementation ADR.

6. **Security and failure boundaries (Section 2.5):** Expanded to define: tenant isolation, actor delegation, service-to-service authentication, authenticated/signed dispatch envelopes, policy-version snapshots, stale approval invalidation, privilege boundaries, executor-compromise response, split-brain prevention, brain unavailability behavior, degraded read-only operation, in-flight execution behavior, recovery and replay authority, RTO target (≤ 5 min, provisional), and RPO target (≤ 30 sec, provisional). Both targets are marked as requiring implementation validation.

7. **Acceptance criteria (Section 6):** Replaced "100% of Brain-dispatched actions pass a double-submit test" with "Every state-changing executor contract must pass duplicate-delivery certification proving one externally observable effect for repeated delivery of the same idempotency key." Replaced the universal two-second "Stop All" criterion with three scoped targets: execution-scoped ≤ 2s, tenant-scoped ≤ 5s, platform break-glass ≤ 10s. Added stale-approval-invalidation acceptance criterion. Clarified that latency targets require implementation testing and may vary by execution class.

### 8.2 Sigma Security Review Notes (Sigma Agent, 2026-08-04)

Review conducted against ADR-002 at head 345e8e71. Six security evaluation areas assessed:

1. **Tenant Isolation:** ADEQUATE — Dispatch envelopes carry tenant_id, executors enforce isolation, idempotency keys are tenant-scoped, cancellation controls are scoped to tenant boundaries.

2. **Authority Boundaries:** ADEQUATE — Brain owns intent/dispatch/cancellation state only. Domain services retain authoritative domain records. Read-only queries bypass the Brain. Universal domain database explicitly rejected.

3. **Execution Semantics:** ADEQUATE — 14 mechanisms specified (at-least-once, transactional outbox, executor inbox/dedup, idempotency-key scope/retention, lease ownership, heartbeat, lease expiration, replay, bounded retry classes, dead-letter queue, poison-message quarantine, causation-chain preservation, partial-failure handling, failure isolation). Retry safety tied to infrastructure, not declarations.

4. **Privilege Boundaries:** ADEQUATE — Actor delegation via authenticated dispatch envelopes, service-to-service auth (mTLS or signed JWT), signed dispatch to prevent forgery, least-privilege credentials, executor-compromise response with credential revocation, policy-version snapshots, stale approval invalidation.

5. **Failure Handling:** ADEQUATE WITH CONDITION — Split-brain prevention (lease-based leadership), degraded mode, recovery/replay authority, panic mode, RTO/RPO targets (provisional). **CONDITION:** The in-flight execution behavior (Section 2.5) allows optional executor continuation after lease expiry during Brain unavailability. Implementation must define explicit criteria for when optional continuation is permitted and require mandatory completion reporting on Brain recovery. This condition does not block acceptance; it is to be satisfied in the implementation ADR or a narrowly scoped amendment.

6. **Auditability:** ADEQUATE — Correlation propagation mandated, causation chains preserved on every dispatch, immutable audit events for all cancellation controls, full audit trail for executor-compromise response, deterministic and auditable recovery.

**Decision: APPROVE_WITH_CONDITIONS**

The ADR adequately specifies the architecture for acceptance. One condition (Section 2.5 in-flight continuation criteria) is deferred to implementation. The architecture is approved for merge and implementation.