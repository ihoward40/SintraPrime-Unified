# Phase 5A — Provider Routing Matrix

## Design Principle

Do not hardcode Claude or Codex. Use SintraPrime's provider
abstraction (`governed_inference/`). The orchestrator resolves the
actual provider/model from workflow-level classes.

## Provider Classes

| Class | Purpose | Phase 5A |
|---|---|---|
| `economy` | cheap deterministic chores | reserved |
| `balanced` | standard agent work | default |
| `reasoning` | hard reasoning tasks | reserved |
| `frontier` | hardest problems | reserved |
| `local` | local models | reserved |

## Model Classes

| Class | Phase 5A |
|---|---|
| `economy` | reserved |
| `balanced` | default (stub) |
| `reasoning` | reserved |
| `frontier` | reserved |
| `local` | reserved |

## Escalation Ladder

```
model_strategy:
  initial: economy
  escalate_after_failures: 2
  escalation: [balanced, reasoning, frontier]
```

Implemented as configuration in workflow definitions. The runner
executes within the strategy; escalation enforcement is Phase B+
(requires provider telemetry from the governed_inference layer).

## Phase 5A Implementation

`AgentNodeExecutor(provider_factory=...)` accepts a factory that maps
`(provider_class, agent_role) → provider` — proven by
`test_agent_executor_uses_provider_factory`. The default factory
returns a deterministic stub (no model calls) for certification.

## Budget Interaction

- Every agent call consumes from the workflow budget
  (`max_agent_calls`, `max_tokens`, `max_provider_cost`).
- Budget exhaustion → BLOCKED, never silently downgraded in Phase 5A
  (adaptive downgrade is the GOD Mode Adaptive Budget Governor —
  Phase H+).
