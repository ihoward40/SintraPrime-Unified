# ADR 002: Mythos Brain — Unified Execution Coordination

## 1. Context and Problem Statement
The SintraPrime platform has evolved into a multi-agent, multi-module system. Currently, authority is distributed across the `portal`, `agents/`, and `workflow_builder/`, leading to fragmented audit trails, inconsistent governance enforcement, and the lack of a "kill switch" for autonomous actions. We need a central **Execution Coordinator** to manage the lifecycle of all system intents.

---

## 2. Proposed Architecture: The Mythos Brain
The Mythos Brain is defined as the **Central Execution Coordinator** for the entire platform. It does not own domain state (e.g., it doesn't own "Matter" data), but it owns the **lifecycle of intent**—from ingestion to terminal state (Success/Failure/Cancelled).

### 2.1 Unified Execution Protocol (UEP)
All execution requests, regardless of origin, must implement the UEP, which enforces:
- **Deterministic Identity:** Every execution must be bound to a verified `actor_id` and `tenant_id` via the `portal/auth` layer.
- **Correlation Propagation:** Mandatory use of `X-Request-ID` and causation chains for cross-module auditability.
- **Idempotency Keys:** All state-changing operations must provide a client-generated idempotency key to prevent duplicate execution in distributed environments.

### 2.2 Authority Boundaries
- **Mythos Brain (Coordinator):** Owns the "intent" ledger, execution state machine (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED), and HITL escalation gates.
- **Executors (Workers):** Modules like `workflow_builder` or `agents/nova` act as stateless execution engines that receive instructions from the Brain and report progress.
- **Mission Control:** Serves as the read-only visual projection of the Brain's active state.

### 2.3 Delivery, Idempotency, and Retries
- **At-Least-Once Delivery:** The Brain guarantees that every authorized intent is dispatched to an executor at least once.
- **Idempotency Requirement:** All executors MUST be idempotent. Re-running a command with the same `idempotency_key` must result in the same side effects as the first successful execution.
- **Exponential Backoff:** The Brain manages retries with jittered exponential backoff for transient failures, ensuring system stability during high-load or partial outage scenarios.
- **Failure Isolation:** The Coordinator (Brain) is strictly isolated from the Executors. Failure of an executor does not impact the stability or state of the coordinator.

### 2.4 Cancellation Primitives
The Brain provides scoped cancellation to ensure system safety and low-latency response:
- **Global Halt:** Immediate suspension of all non-critical execution across the entire system or a specific tenant.
- **Workstream Cancellation:** Halts a specific logical grouping of tasks or a causation chain (e.g., "Stop this specific legal research loop").
- **Executor Revocation:** Signals a specific agent or worker to checkpoint and terminate immediately.
- **Prioritized Delivery:** Cancellation signals are prioritized in the message bus, bypassing standard execution queues to ensure immediate effect.

### 2.5 Security and Failure Boundaries
- **Policy Enforcement Point (PEP):** The Brain acts as the PEP, validating every intent against the `governed_inference` layer before dispatch.
- **Failure Isolation:** A failure in an executor (e.g., an agent crash) must not corrupt the Brain's intent ledger.
- **Panic Mode:** In the event of a detected governance breach, the Brain enters a "Panic Mode," locking all outbound API connectors and requiring administrative reset.

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
| **Mythos Brain (Central)** | Unified control; audit integrity; scalable governance. | Higher initial design complexity. | 🟡 Proposed |

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
- [ ] **One Protocol:** A single Python base class or Protocol that all executors must implement.
- [ ] **Authority Boundary:** `agents/` and `workflow_builder/` no longer manage their own persistence; they report to the Brain.
- [ ] **Idempotency:** 100% of Brain-dispatched actions pass a "double-submit" test.
- [ ] **Cancellation:** A "Stop All" command in the Portal successfully halts a running Nova agent action within 2 seconds.
- [ ] **Human Escalation:** Any action with `risk_level > threshold` creates a blocking `ApprovalRequest` in the database.

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
