# Collaborative Agent Fabric — Phase CF-1

## Purpose

Persistent collaboration spaces where humans and agents share
operational context; agents wake on relevant structured events;
SintraPrime remains the control plane. Agents compute — they do not
create authority.

The hierarchy:

```text
Principal
   ↓
Mission Control
   ↓
Governed Orchestrator
   ↓
Collaborative Agent Fabric   ← this subsystem
   ↓
Workflow Runtime
   ↓
Scoped Agents / Providers / Capabilities
```

## Phase CF-1 Scope (Foundation)

- `CollaborationChannel` — persistent governed operational space
- `ChannelMembership` — human/agent/service participation with roles
- `AgentChannelBinding` — scoped agent participation (response modes,
  event allowlists, parallelism, budgets)
- Canonical channel events (structured envelope, validated before
  dispatch)
- Event router with fail-closed policy engine (deterministic filters
  before any model invocation)
- Agent activation abstraction with concurrency control and queueing
- Stop control (`STOP_AGENT`) and tenant kill switch
- Anti-loop protection (causal chains, `max_agent_hops=4`,
  `BLOCKED_LOOP_GUARD`)
- Event deduplication (consumption keys, re-entry protection)
- Structured agent-to-agent handoffs
- Execution receipts (event/activation/handoff, hash-chained)
- Backend APIs (CF-1E), POC engineering-lab channel, tests

## Out of Scope (Phase CF-2+)

Full frontend, public communities, mobile, voice, social network
federation, Nostr, trading/health agents, public anonymous access,
GOD-1 Council UI, production remote worker fleet.

## Existing Components Reused

| Fabric component | Reuses |
|---|---|
| Receipt hash-chaining | `portal/services/mission_control_command_service.py` SHA-256 chain pattern |
| JSON persistence | `workflow_runtime/checkpoint.py` disk-backed pattern |
| Event policy determinism | `orchestration/durable_execution.py` bounded execution pattern |
| Authority model | `governance/blackstone` capability intersection concept |

## No New Authority

No workflow, channel, or agent acquires authority beyond the
initiating principal. No auto-merge, no auto-deploy, no legal/tax
filing, no money movement, no consequential external communication,
no deletion of protected records. All remain gated by existing
SintraPrime governance.
