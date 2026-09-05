# CF-1 Test Matrix

Source: `collaboration/tests/test_collaboration.py` — 61 tests, all passing.

## Models

| Test | Condition |
|---|---|
| test_channel_type_enum | 9 channel types |
| test_event_type_enum | canonical events |
| test_agent_identity_independent_of_host | §XX identity ≠ host |
| test_behavior_contract_hash | §XIV hashed/versioned contract |
| test_message_content_types | §LI content types |
| test_channel_brief_do_not_do_list | §XXVI do-not-do list |

## Channels / Membership / Bindings

| Test | Condition |
|---|---|
| test_create_and_reload | persistence |
| test_list_by_tenant | tenant scoping |
| test_member_join_and_leave | membership lifecycle |
| test_role_of | role lookup |
| test_binding_crud | bind/stop/resume |
| test_tenant_isolation | cross-tenant query isolation |

## Policies

| Test | Condition |
|---|---|
| test_within_limit / test_exceeds_limit | loop guard hop bound |
| test_cycle_in_causal_chain | cycle detection |
| test_next_hop_event | chain propagation |
| test_not_consumed / test_mark_consumed | dedup keys |
| test_reentry_protection | re-join no retrigger |
| test_different_agents_not_confused | per-agent keys |
| test_allows_first_call / test_blocks_after_limit | rate limit |
| test_independent_agents | per-agent windows |
| test_acquire_release / test_inflight_count | concurrency |
| test_activate_blocks / test_deactivate_restores | kill switch |
| test_channel_specific | scoped kill switch |
| test_human_messages_unaffected | humans stay online |
| test_allowlist_blocks_unknown / test_system_only / test_principal_only | actor policy |
| test_kill_switch_blocks / test_no_binding_no_activation | fail closed |
| test_stopped_binding_blocked | stop control |
| test_tenant_mismatch | tenant gate |
| test_event_type_not_allowed | subscription gate |
| test_loop_guard_integration / test_dedup_integration / test_rate_limit_integration | engine composition |

## Dispatcher

| Test | Condition |
|---|---|
| test_dispatch_to_matching_bindings | multi-agent dispatch |
| test_dispatch_blocked_event_type | skip + reason |

## Services

| Test | Condition |
|---|---|
| test_request_and_complete | activation lifecycle |
| test_queue_when_at_capacity | bounded parallelism |
| test_fail | failure path |
| test_list_by_channel | activity projection |
| test_create_accept_complete | handoff lifecycle |
| test_set_and_get / test_default_offline | presence |
| test_stop_agent / test_stop_all_in_channel | shutdown control |

## Receipts

| Test | Condition |
|---|---|
| test_event_receipt_chain | hash chain integrity |
| test_activation_receipt_chain | hash chain integrity |
| test_handoff_receipt_chain | hash chain integrity |
| test_tampered_receipt_detected | tamper detection |

## Persistence

| Test | Condition |
|---|---|
| test_restart_preserves_channel | restart recovery |
| test_restart_preserves_binding | subscription survives restart |
| test_stop_persists | no resurrection |

## POC engineering-lab

| Test | Condition |
|---|---|
| test_setup | 3 agents ready |
| test_full_proof | wakeup → handoff chain → loop guard → kill switch |
| test_dedup_blocks_second_event | replay protection |
