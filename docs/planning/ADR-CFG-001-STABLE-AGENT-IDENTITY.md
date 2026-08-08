# Architecture Decision Record (ADR): ADR-CFG-001 — Stable Agent Identity

**Status:** Approved  
**Date:** 2026-08-08  
**Author:** Hermes Agent  
**Decision ID:** ADR-CFG-001  
**Scope:** Phase CF-1 / Governance Expansion — Collaborative Agent Fabric + Governance Foundation

---

## 1. Context

Agents may execute across different hosts, providers, and LLMs over
time. The source material (Buzz collaboration patterns) ties agent
identity to a physical machine, creating fragility and audit gaps.

SintraPrime requires agents to remain the same logical entity
regardless of execution infrastructure, because:

- execution receipts must reference a stable agent ID;
- capability leases bind to agent identity;
- quarantine acts on agent identity;
- Mission Control tracks agent presence by identity;
- reputation and trust decay (Phase CF-5) require stable identity.

## 2. Decision

Implement `AgentIdentity` as a first-class entity independent of
execution host. Identity is SintraPrime-owned and persists in the
collaboration store; `ExecutionHost` is infrastructure metadata.

```text
AgentIdentity:
  agent_id, name, role, allowed_domains
  provider_profile, model_profile, authority_class
  status, registered_at

ExecutionHost:
  host_id, name, host_type, status
  capabilities, last_heartbeat, trust_level
  current_load
```

Agent activation receipts and behavior contracts reference the
stable `agent_id`; host references are metadata only.

## 3. Consequences

- Positive: quarantine, capability leases, reputation, handoff, and
  causal records all reference a stable entity. No identity churn
  across host/provider changes.
- Positive: the same agent can run on WORKSTATION-A today and
  GPU_WORKER-02 tomorrow without losing continuity.
- Negative: host-aware scheduling (CF-3) must resolve host
  independently — this is the intended design, not a gap.
- Positive: the governance expansion (quarantine, budget governor,
  effect receipts) all attach to the stable agent_id, making the
  governance plane host-agnostic.
