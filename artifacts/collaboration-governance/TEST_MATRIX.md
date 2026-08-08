# Test Matrix — Phase CF-1 / Governance Expansion

133 tests pass: 61 fabric (PR #276) + 72 governance (this PR).

## §140 Constitutional

| Test | Condition |
|---|---|
| test_agent_cannot_self_approve | NO_AGENT_SELF_APPROVAL |
| test_agent_cannot_grant_capability | NO_AGENT_SELF_PERMISSION_GRANT |
| test_consequential_action_requires_authority | A3 no approver |
| test_cross_tenant_blocked | NO_CROSS_TENANT_IMPLICIT_ACCESS |
| test_cross_matter_blocked | NO_CROSS_MATTER_IMPLICIT_ACCESS |
| test_unbounded_loop_rejected / test_bounded_loop_ok | loop bound |
| test_implementer_cannot_certify | NO_CERTIFICATION_BY_IMPLEMENTER |
| test_no_budget_rejected | NO_UNBOUNDED_PROVIDER_SPEND |
| test_unregistered_tool_rejected | NO_UNREGISTERED_TOOL_EXECUTION |
| test_unhashed_workflow_rejected / test_unversioned_policy_rejected | hash/version |
| test_public_agent_high_authority_rejected | NO_PRIVILEGED_PUBLIC_AGENT |
| test_silent_external_write_rejected / test_audited_external_write_ok | DLP audit |
| test_static_workflow_check / test_static_workflow_compliant | §86 static |

## §140 Events

| Test | Condition |
|---|---|
| fabric suite | correct trigger, incorrect ignored, duplicate ignored, unauthorized blocked (61 tests) |
| test_quarantine_blocks_activation / test_clean_agent_not_quarantined | quarantine gate |

## §140 Dead Letter

| Test | Condition |
|---|---|
| test_failure_persisted | persisted immediately |
| test_retry_bounded | exhausted at max_retries |
| test_poison_event_quarantined | QUARANTINED_EVENT |

## §140 Agent Quarantine

| Test | Condition |
|---|---|
| test_quarantine_blocks_activation | no new activation |
| test_release_restores | release path |
| test_quarantine_survives_restart | §141 persistence |
| test_list_active | inspection |

## §140 Capability Lease

| Test | Condition |
|---|---|
| test_valid_lease | valid grant |
| test_expired_lease_rejected | expiry |
| test_wrong_purpose_rejected | purpose |
| test_wrong_scope_rejected | scope |
| test_revoked_lease_rejected | revocation |
| test_list_for_agent | listing |

## §140 Data Taint

| Test | Condition |
|---|---|
| test_external_unverified_persists | taint survives downstream |
| test_combine_weakest | weakest-lineage combine |
| test_evidence_scorer | §64 score |

## §140 Cross-Tenant / Matter

| Test | Condition |
|---|---|
| test_event_injection_blocked | cross-tenant event |
| test_matter_isolation | matter A vs B |

## §140 Concurrency

Fabric proof (PR #276): `TestConcurrency` + `TestActivationService` —
20 events, max_parallelism=3, never >3 active.

## §140 Kill Switch

Fabric: `TestKillSwitch` — new activations blocked, humans unaffected.

## §140 Goal Drift

| Test | Condition |
|---|---|
| test_unauthorized_repo_detected | repo expansion |
| test_unauthorized_matter_detected | matter expansion |
| test_authorized_repo_ok | no false positive |
| test_budget_exceeded (scope creep) | token budget |

## §140 Budget

| Test | Condition |
|---|---|
| test_hard_token_limit | max_tokens |
| test_hard_call_limit | max_calls |
| test_hard_cost_limit | max_cost |
| test_snapshot | state export |

## §140 Receipts

| Test | Condition |
|---|---|
| test_apply_first_time | effect receipt created |
| test_idempotent_retry | same key → same receipt |
| test_hash_verify | tamper detection |
| fabric TestReceipts | event/activation/handoff hash chains |

## §140 Causal Explanation

| Test | Condition |
|---|---|
| test_record_and_explain | Why-did-this-happen |
| test_missing_action | not found |

## §141 Persistence / Restart

| Test | Condition |
|---|---|
| test_quarantine_survives | agent quarantine |
| test_dead_letter_survives | dead letters |
| test_lease_survives | leases |
| test_effect_receipt_survives | effect receipts |
| test_causal_survives | causal records |
| test_uncertainty_survives | uncertainties |
| test_assumption_survives | assumptions |
| fabric TestPersistence | channel/binding/stop |

## §144–145 Linters

| Test | Condition |
|---|---|
| test_unbounded_loop_detected | workflow lint |
| test_missing_budget_detected | workflow lint |
| test_self_certification_detected | workflow lint |
| test_high_authority_no_approval | workflow lint |
| test_public_agent_high_authority | contract lint |
| test_binding_unauthorized_all_messages | binding lint |
| test_compliant_workflow | clean pass |
| test_architecture_linter / test_architecture_linter_clean | arch lint |

## §142 Security Matrix (mapped)

| Attack | Gate | Status |
|---|---|---|
| prompt injection | fabric context firewall doc + DLP scan | covered by design + tests |
| cross-tenant spoof | invariant + fabric tenant gate | covered |
| cross-matter spoof | invariant | covered |
| agent identity spoof | fabric actor policy | covered |
| event spoof | fabric envelope validation + dedup | covered |
| forged approval | invariant NO_AGENT_SELF_APPROVAL | covered |
| permission escalation | invariant NO_AGENT_SELF_PERMISSION_GRANT | covered |
| secret exfiltration | DLP scanner | covered |
| outbound DLP | DLP scanner | covered |
| loop attack | fabric loop guard + invariant | covered |
| event replay | fabric dedup | covered |
| budget bypass | BudgetGovernor hard limits | covered |
| kill-switch bypass | fabric kill switch + policy chain | covered |
| quarantine bypass | policy step 3a | covered |
