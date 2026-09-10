# Phase 5A — Governed Workflow Runtime Architecture

## Target Architecture

```
Principal
  → Mission Control
    → Governed Orchestrator
      → Workflow Runtime
        → Workflow Nodes
          → Agent/Provider Adapter
          → Tool/Capability Layer
        → Evidence + Audit Ledger
```

## Boundaries

- **SintraPrime = Control Plane**: workflows are configuration, not authority grants.
- **Agents = Computation Providers**: AgentNode is a bounded session with scoped context. No authority escalation.
- **Mission Control = Command Surface**: approval nodes, pause/resume, guard enforcement.
- **Principal = Final Authority**: consequential actions require Principal approval.

## Reused Existing Abstractions

| New Module | Reuses |
|---|---|
| `validator.py` | `portal/services/orchestration/execution_graph.py` — Kahn's cycle detection pattern |
| `budgets.py` | `portal/services/orchestration/budget_policy.py` + `schemas.py` — BudgetLimits/BudgetUsageSnapshot |
| `receipts.py` | `portal/services/mission_control_command_service.py` — SHA-256 hash-chain pattern |
| `retries.py` | `orchestration/durable_execution.py` — RetryPolicy dataclass |
| `node_executor.py` (agent) | `governed_inference/` — provider abstraction (BaseConfiguredProvider) |
| `state_machine.py` | `portal/services/mission_control_run_control_service.py` — transition enforcement pattern |

## Phase 5A Scope (This PR Only)

- Workflow schema/models
- Parser + validator (DAG, cycles, version pinning)
- Runtime state machine
- Deterministic node execution (registered operations)
- AgentNode abstraction (provider routing, fresh context)
- Checkpoint persistence (disk-backed JSON)
- Budget enforcement (tokens/cost/time/agent calls)
- Immutable receipts (hash-chained JSONL)
- Default workflows: proof_workflow, repository_issue_fix
- 39 certification tests

## Excluded from Phase 5A

- Mission Control workflow UI
- OmniBrain integration beyond Phase 5A interfaces
- Council swarm, research swarm, build swarm
- GOD-0 Principal Brief, GOD-1
- Canary rollout, provider arena
- Production deployment, auto-merge
- PostgreSQL migrations (Phase B+)
