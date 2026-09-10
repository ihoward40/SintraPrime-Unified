# Phase 5A — Security Model

## Authority Model

- No workflow acquires more authority than the initiating principal/agent.
- AgentNode = computation abstraction, not authority grant.
- Capability intersection: workflow requested ∩ agent permissions ∩ tenant permissions ∩ principal policy.
- Deterministic nodes cannot be silently skipped by AgentNodes.

## Tenant Isolation

- Every WorkflowRun carries `tenant_id` and `principal_id`.
- Checkpoint and receipt stores are keyed by `run_id`.
- No cross-tenant artifact leakage: receipt chains are per-run.
- State serialization includes tenant/principal context.

## Capability Enforcement

- Workflow definitions declare `capabilities: [github.read, repository.write_worktree, tests.execute]`.
- AgentNode receives scoped `ContextPackage.permissions` from run context.
- Permission escalation is impossible: agent output cannot mutate the run's permission set.
- Phase 5A enforcement: run context permissions are immutable after start.

## Fresh-Context Evaluator

- `fresh_context: true` nodes receive a ContextPackage scoped to artifacts, not implementation reasoning.
- Evaluators never inherit the implementer's conversational history.
- Context package includes only: run_id, agent_role, task, relevant artifacts, constraints, permissions, provenance.

## Budget Hard-Stop

- Workflow-level budgets: max_tokens, max_provider_cost, max_wall_time, max_agent_calls.
- Budget exhaustion produces BLOCKED status (not retried, not circuit-broken).
- Circuit breaker halts on repeated identical failures (BLOCKED_SAFETY).

## Immutable Receipts

- Every completed node emits a WorkflowReceipt.
- Receipts are hash-chained: each receipt stores `previous_hash`.
- Receipt verification detects any tampering.
- Receipt data: run_id, node_id, output_hash, provider, model, tokens, cost, timestamp.

## Untrusted Content Separation

- Retrieved web/email/document content is marked as untrusted artifacts.
- Agent instructions from retrieved content cannot override system/workflow policy.
- Context package `constraints` field enforces workflow-level guards.
