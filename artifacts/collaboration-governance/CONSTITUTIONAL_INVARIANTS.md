# Constitutional Invariants

Machine-enforceable rules (directive §2, §20, §140). A prompt, agent,
workflow, or plugin cannot override an invariant. Fail closed.

## Implemented (20 of 22 named — §2)

| Invariant | Enforcement | Proof test |
|---|---|---|
| NO_AGENT_SELF_APPROVAL | `InvariantEngine` action=approve, approver==actor, actor_type=agent | `test_agent_cannot_self_approve` |
| NO_AGENT_SELF_PERMISSION_GRANT | action=grant_capability, target==actor, agent | `test_agent_cannot_grant_capability` |
| NO_CONSEQUENTIAL_ACTION_WITHOUT_AUTHORITY | A3/A4 + non-human + no approver | `test_consequential_action_requires_authority` |
| NO_CROSS_TENANT_IMPLICIT_ACCESS | source_tenant != tenant_id | `test_cross_tenant_blocked`, `test_event_injection_blocked` |
| NO_CROSS_MATTER_IMPLICIT_ACCESS | source_matter != matter_id | `test_cross_matter_blocked`, `test_matter_isolation` |
| NO_UNBOUNDED_AUTONOMOUS_LOOP | hop_count > max_hop_count or unbound | `test_unbounded_loop_rejected` |
| NO_UNBOUNDED_RETRY | retry without max_retries | static check |
| NO_UNBOUNDED_PROVIDER_SPEND | budget_defined=False | `test_no_budget_rejected` |
| NO_SECRET_IN_PROMPT_LOG | secret_in_payload + log_prompt | static check |
| NO_SECRET_IN_CHANNEL_MESSAGE | secret_in_payload + channel_message | static check |
| NO_CERTIFICATION_BY_IMPLEMENTER | certify + implementer==actor | `test_implementer_cannot_certify` |
| NO_UNVERIFIED_AUTHORITY_ESCALATION | escalate_authority + not verified | static check |
| NO_PRODUCTION_DEPLOY_WITHOUT_GATE | deploy + production + no approver | static check |
| NO_PROTECTED_BRANCH_AUTO_MERGE | merge + protected_branch | static check |
| NO_CANONICAL_MEMORY_SELF_MODIFICATION | memory_write + canonical + agent | static check |
| NO_UNREGISTERED_TOOL_EXECUTION | tool_execute + not registered | `test_unregistered_tool_rejected` |
| NO_UNHASHED_WORKFLOW_EXECUTION | workflow_execute + no hash | `test_unhashed_workflow_rejected` |
| NO_UNVERSIONED_POLICY_EXECUTION | policy_execute + no version | `test_unversioned_policy_rejected` |
| NO_PRIVILEGED_PUBLIC_AGENT | public agent + A2/A3/A4 | `test_public_agent_high_authority_rejected` |
| NO_SILENT_EXTERNAL_WRITE | external_write + not audited | `test_silent_external_write_rejected` |

## Design Notes

- `ActionContext` is the single evaluation input: action, actor,
  authority class, tenant, matter, capability, hashes, budget,
  external write, public flag, hop bound.
- `static_check_workflow()` enforces the governance-linter-style
  structural rules (§86): unbounded loops, missing budgets, missing
  hashes/versions, high authority without approval.
- The engine is injected into `EventPolicyEngine` as step 3b of the
  deterministic dispatch chain — before any model invocation.
- Invariants never grant authority; they only block.

## Boundary

Directive §2 also names NO_CROSS_TENANT_IMPLICIT_ACCESS at the DB
layer and NO_SECRET_* at prompt-assembly time; those enforcement
points are Phase CF-2/CF-4 concerns where the surfaces exist.
