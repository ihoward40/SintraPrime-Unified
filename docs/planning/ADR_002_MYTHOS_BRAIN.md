# Architecture Decision Record (ADR): Mythos Brain — Central Execution Authority

**Status:** Proposed  
**Date:** 2026-08-04  
**Author:** Manus AI  
**Decision ID:** ADR-002  
**Scope:** Phase 3 Operational Intelligence — Central Orchestration

---

## 1. Context

Currently, `SintraPrime-Unified` suffers from fragmented execution authority. Commands and workflows originate from multiple independent modules:
- **`portal/`**: Handles direct synchronous API requests.
- **`scheduler/`**: Manages background and recurring tasks.
- **`agents/`**: (Nova, Sigma, Zero) Execute autonomous reasoning and actions.
- **`workflow_builder/`**: Orchestrates multi-step durable workflows.

This fragmentation leads to "perfect governance without a steering wheel." There is no single protocol for command dispatch, state tracking, cancellation, or human-in-the-loop (HITL) escalation across these surfaces. To achieve "Mythos Brain" level autonomy, a unified operational intelligence layer is required.

---

## 2. Decision

Establish the **Mythos Brain** as the authoritative central execution orchestrator for the entire platform. 

### 2.1 Unified Execution Protocol (UEP)
All execution requests, regardless of origin, must implement the UEP, which enforces:
- **Deterministic Identity:** Every execution must be bound to a verified `actor_id` and `tenant_id` via the `portal/auth` layer.
- **Correlation Propagation:** Mandatory use of `X-Request-ID` and causation chains for cross-module auditability.
- **Idempotency Keys:** All state-changing operations must provide an idempotency key to prevent duplicate execution in distributed environments.

### 2.2 Authority Boundaries
- **Mythos Brain (Orchestrator):** Owns the "intent" ledger, execution state machine, and HITL escalation gates.
- **Executors (Workers):** Modules like `workflow_builder` or `agents/nova` act as stateless execution engines that receive instructions from the Brain.
- **Mission Control:** Serves as the read-only visual projection of the Brain's active state.

### 2.3 Operational Control Primitives
The Brain will provide standardized interfaces for:
- **Cancellation:** Global signal to halt active workflows or agent actions.
- **Escalation:** Automatic pausing of execution when a "High Stakes" policy is triggered, requiring human authorization via the `portal`.
- **Dissent Recording:** In multi-agent scenarios (Parliament), the Brain must record minority opinions and reasoning conflicts before finalizing a state.

---

## 3. Consequences

### Positive
- **Single Source of Truth:** One ledger for all system actions (sync, async, autonomous).
- **Hardened Governance:** Centralized enforcement of "Refusal-Only" and "HITL" policies.
- **Unified Observability:** Simplifies the implementation of the Mission Control dashboard.
- **Audit Integrity:** Guarantees that every side effect in the system is correlated to a high-level intent.

### Negative / Risks
- **Centralized Complexity:** The orchestrator becomes a complex "god module" if not carefully designed.
- **Performance Bottleneck:** Synchronous calls through the Brain may add latency; requires an async-first architecture.
- **Single Point of Failure:** If the Brain's state store (Redis/Postgres) fails, all system execution stops.

### Mitigations
- Use a **micro-kernel architecture** for the Brain, where domain-specific logic is offloaded to sub-agents.
- Implement **idempotent retries** and durable state persistence using the existing PostgreSQL backbone.
- Maintain **stateless executors** to allow for horizontal scaling.

---

## 4. Alternatives Considered

| Option | Pros | Cons | Verdict |
| :--- | :--- | :--- | :--- |
| **Distributed Authority** | No single bottleneck; faster local execution. | Impossible to enforce global governance; audit gaps. | ❌ Rejected |
| **Portal-Only Authority** | Leverages existing API security. | Cannot handle background tasks or autonomous agent loops. | ❌ Rejected |
| **Mythos Brain (Central)** | Unified control; audit integrity; scalable governance. | Higher initial design complexity. | ✅ Approved |

---

## 5. Architecture

```mermaid
graph TD
    User((User/Client)) -->|API Request| Portal[Portal API]
    System[System Events] -->|Trigger| Scheduler[Scheduler]
    Agent[Autonomous Loop] -->|Intent| Agents[Agent Swarm]

    subgraph Mythos Brain (Central Authority)
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

The Mythos Brain does **NOT** authorize:
- Autonomous legal conclusions or filings without professional review.
- Automatic modification of its own core governance policies.
- Execution of code outside of the pre-defined "Safe-Zone" (Airlock).

---

## 8. Signatures

| Role | Name | Date | Decision |
| :--- | :--- | :--- | :--- |
| **Project Owner** | Isiah Howard | 2026-08-04 | Proposed |
| **Architect** | Manus AI | 2026-08-04 | Proposed |
| **Security Reviewer** | Sigma Agent | 2026-08-04 | Pending |
