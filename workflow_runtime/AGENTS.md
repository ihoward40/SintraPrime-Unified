# workflow_runtime — Governed Workflow Runtime

## Purpose

Phase 5A foundation of the Archon-class deterministic/agentic workflow
runtime for SintraPrime. Provides declarative workflow parsing,
governed state-machine execution, deterministic node execution,
agent-node abstraction, bounded budgets, immutable receipts, and
checkpoint-based resumption.

SintraPrime remains the CONTROL PLANE. Agents are computation
providers. No workflow acquires more authority than the initiating
principal/agent possesses.

## Ownership

- `models.py` — core data contracts (WorkflowDefinition, WorkflowRun,
  WorkflowNodeRun, WorkflowCheckpoint, WorkflowReceipt, statuses,
  budget, context package)
- `parser.py` — YAML → WorkflowDefinition
- `validator.py` — DAG validation, node-type checks, cycle rejection,
  version/source-hash pinning
- `registry.py` — definition registry (load/validate/register/hash)
- `state_machine.py` — governed state transitions (workflow + node)
- `node_executor.py` — DeterministicExecutor (registered operations),
  AgentNodeExecutor (scoped context, provider abstraction),
  ApprovalNodeExecutor (Phase 5A: pause stub)
- `conditions.py` — deterministic condition evaluation for branching
- `retries.py` — bounded RetryPolicy + CircuitBreaker
- `budgets.py` — BudgetEnvelope with hard-stop enforcement
- `receipts.py` — ReceiptStore (append-only, hash-chained JSONL)
- `checkpoint.py` — CheckpointStore (disk-persisted execution state)
- `runner.py` — WorkflowRunner (orchestration loop)
- `tests/` — Phase 5A certification tests (39 tests)

## Local Contracts

- Workflows are configuration, not authority grants.
- No workflow may acquire more authority than the initiating
  principal/agent possesses.
- AgentNode is a computation abstraction, not an authority grant.
- Deterministic nodes cannot be silently skipped by AgentNodes.
- Retry/circuit limits are bounded; infinite loops are forbidden.
- Budget ceilings enforce hard stops.
- Receipts are immutable and hash-chained.
- Checkpoints persist after every material node.
- Running workflow versions are pinned via source_hash.
- Evaluator nodes receive fresh context (no implementation bias).
- All transitions are deterministic and auditable.
- Capability intersection: workflow ∩ agent ∩ tenant ∩ principal.

## Verification

- `python -m pytest workflow_runtime/tests/ --basetemp=.pytest-tmp`
- Default workflows: `workflows/defaults/`
- Certification evidence: `artifacts/workflow-runtime/`

## Child DOX Index

| Path | Scope | Controls |
|---|---|---|
| `tests/` | Phase 5A certification tests | Persistence, retry, isolation, budget, receipts, fresh-context, no-escalation, cycle rejection |
| `workflows/defaults/` | Default workflow definitions | proof_workflow.yaml, repository_issue_fix.yaml |
