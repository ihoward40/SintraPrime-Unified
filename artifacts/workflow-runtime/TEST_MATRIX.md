# Phase 5A — Test Matrix

All tests: `python -m pytest workflow_runtime/tests/ --basetemp=.pytest-tmp`

Result: **39 passed, 0 failed** (2026-08-07)

## Parser

| Test | Verifies |
|---|---|
| test_parses_default_workflow | YAML → WorkflowDefinition |
| test_parse_missing_name_raises | fail closed on missing fields |
| test_parse_unknown_node_type_raises | unknown node types rejected |

## Validator

| Test | Verifies |
|---|---|
| test_valid_workflow | valid definition passes |
| test_missing_dependency | unknown dependency rejected |
| test_cyclic_graph_rejected | DAG cycles rejected |
| test_deterministic_node_requires_action | fail closed |
| test_agent_node_requires_role | fail closed |
| test_unbounded_loop_rejected | loops capped at 100 |
| test_missing_source_hash_rejected | version pinning required |

## Registry

| Test | Verifies |
|---|---|
| test_load_defaults | defaults dir loads |
| test_register_rejects_invalid | invalid defs rejected at registration |
| test_register_version_conflict | same version + different hash rejected |

## State Machine

| Test | Verifies |
|---|---|
| test_pending_to_ready_to_running | legal lifecycle |
| test_illegal_transition_raises | illegal transitions blocked |
| test_terminal_superseded_only | terminal → SUPERSEDED only |

## Execution

| Test | Verifies |
|---|---|
| test_proof_workflow_runs_to_completion | full proof workflow executes |
| test_deterministic_nodes_cannot_be_skipped | determinism enforced |
| test_persistence_across_restart | crash recovery from disk |
| test_checkpoint_written_after_material_nodes | checkpoint persistence |
| test_pause_resume | governed pause/resume |
| test_cancel | governed cancel |

## Budgets

| Test | Verifies |
|---|---|
| test_token_ceiling_hard_stop | token ceiling → BLOCKED |
| test_agent_call_ceiling | agent-call ceiling → BLOCKED |
| test_cost_ceiling | cost ceiling enforced |
| test_time_ceiling | wall-time ceiling enforced |

## Retries + Circuit Breaker

| Test | Verifies |
|---|---|
| test_bounded_retry | fails after max_attempts, no infinite loop |
| test_retry_succeeds_on_second_attempt | retry recovery |
| test_circuit_breaker_opens_on_identical_failures | repeated identical failure halts |
| test_circuit_breaker_resets_on_different_error | different errors reset count |

## Tenant Isolation

| Test | Verifies |
|---|---|
| test_tenant_isolation | run state isolated per tenant |
| test_tenant_scoped_receipts | receipt chains per run, no leakage |

## Fresh Context

| Test | Verifies |
|---|---|
| test_fresh_context_package | evaluator gets artifacts, not implementer history |

## Provider Abstraction

| Test | Verifies |
|---|---|
| test_agent_executor_uses_provider_factory | provider routing is abstracted |

## Receipts

| Test | Verifies |
|---|---|
| test_receipt_chain_integrity | full chain verifies |
| test_tampered_receipt_detected | tampering detected |
| test_node_run_links_receipt | node runs link to receipts |

## No Authority Escalation

| Test | Verifies |
|---|---|
| test_no_authority_escalation | permission set immutable |
| test_agent_node_is_not_authority_grant | agent output cannot escalate |
