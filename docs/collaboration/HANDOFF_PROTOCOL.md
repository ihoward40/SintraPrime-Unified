# Handoff Protocol

## Structured Handoff (directive §XXVIII–§XXIX)

```text
Agent A
  ↓ creates AgentHandoff (task, input_artifacts, expected_output_schema)
  ↓ policy validation
Agent B
  ↓ returns structured result
Agent A / Workflow
```

Never depend on prose tagging for task transfer.

## Handoff Model

```text
handoff_id, source_agent, target_agent, channel_id, tenant_id
task, input_artifacts, expected_output_schema
deadline, budget
status: pending → accepted → completed | failed | cancelled | rejected
correlation_id, workflow_run_id
```

## Constraints

- An agent cannot recruit another agent unless its contract allows
  `agent.handoff.request` (directive §LXIV). Orchestrator creates the
  handoff; agents cannot spawn privileged workers.
- Tenant is preserved end-to-end.
- Capability boundaries preserved: target agent runs under its own
  contract.
- Every handoff emits a hash-chained receipt.

## POC Handoff Chain (CF-1F)

```text
Hermes Coordinator → Engineer → Auditor → Hermes consolidation
```

Verified: unique activation IDs, correlation preserved, handoff IDs
preserved, tenant preserved, no infinite event loop.
