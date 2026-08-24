import ast
from dataclasses import replace
from pathlib import Path

import pytest

from sintra_live.l2.mission import MissionAggregate, MissionIdentity, MissionScope, MissionState
from sintra_live.l2.mission.transition_contract import ALL_PREDICATES, POLICY_VERSION, PredicateValue, TransitionPolicyRequest, TransitionPredicateRecord
from sintra_live.l2.mission.transition_errors import PolicyOutcome, PolicyReason
from sintra_live.l2.mission.transition_policy import evaluate_transition

H = "b" * 64
CREATED = "2026-08-24T10:00:00.000000Z"
NOW = "2026-08-24T10:30:00.000000Z"
EXPIRES = "2026-08-24T11:00:00.000000Z"


def aggregate(state=MissionState.RECEIVED):
    identity = MissionIdentity("SP-LIVE-001", "L2-I2", "mission-adversarial", "request-adversarial", H, "principal-ref", H, "authority-ref")
    scope = MissionScope("policy", ("read",), ("write",), "LOW", (("tokens", 1),), 0, ("evidence",), EXPIRES, "cancel-ref")
    base = MissionAggregate.genesis(identity, scope, CREATED)
    if state is MissionState.RECEIVED: return base
    return MissionAggregate(base.schema_version, base.identity, base.scope, base.created_at, state, 0, base.previous_event_sha256, (), (), state in {MissionState.CANCELLED, MissionState.COMPLETE, MissionState.IDENTITY_AMBIGUOUS}, state is MissionState.CANCELLED)


def record(agg, **changes):
    values = {name: PredicateValue.UNKNOWN for name in ALL_PREDICATES}; values.update(changes)
    return TransitionPredicateRecord.create(agg, created_at=CREATED, expires_at=EXPIRES, values=values)


def request(agg, target, predicates=None, **changes):
    base = TransitionPolicyRequest(POLICY_VERSION, agg.current_state, target, agg.version, agg.aggregate_sha256, agg.previous_event_sha256, NOW, predicates or record(agg))
    return replace(base, **changes)


@pytest.mark.parametrize("field,bad", [
    ("expected_aggregate_version", 99), ("expected_aggregate_sha256", "0" * 64),
    ("expected_previous_event_sha256", "1" * 64), ("proposed_from_state", MissionState.MISSION_SCOPED),
])
def test_binding_substitution_denied(field, bad):
    agg = aggregate(); result = evaluate_transition(agg, request(agg, MissionState.PRINCIPAL_IDENTIFIED, **{field: bad}))
    assert (result.outcome, result.reason_code) == (PolicyOutcome.DENY, PolicyReason.BINDING_FAILURE)


@pytest.mark.parametrize("target", [MissionState.MISSION_SCOPED, MissionState.RECEIVED, MissionState.READY, MissionState.COMPLETE])
def test_invalid_skip_backward_self_edges_denied(target):
    agg = aggregate(); result = evaluate_transition(agg, request(agg, target))
    assert result.outcome is PolicyOutcome.DENY


def test_terminal_reopen_denied():
    agg = aggregate(MissionState.CANCELLED)
    result = evaluate_transition(agg, request(agg, MissionState.RECEIVED))
    assert (result.outcome, result.reason_code) == (PolicyOutcome.DENY, PolicyReason.TERMINAL_STATE_PROHIBITION)


def test_kill_switch_and_cancellation_precedence():
    agg = aggregate()
    both = record(agg, kill_switch_active=PredicateValue.TRUE, cancellation_requested=PredicateValue.TRUE)
    allowed = evaluate_transition(agg, request(agg, MissionState.CANCELLED, both))
    assert (allowed.outcome, allowed.reason_code) == (PolicyOutcome.ALLOW, PolicyReason.KILL_SWITCH_CANCELLATION)
    denied = evaluate_transition(agg, request(agg, MissionState.PRINCIPAL_IDENTIFIED, both))
    assert denied.reason_code is PolicyReason.KILL_SWITCH_REQUIRES_CANCELLATION


def test_cancel_without_request_denied():
    agg = aggregate(); decision = evaluate_transition(agg, request(agg, MissionState.CANCELLED))
    assert decision.reason_code is PolicyReason.CANCELLATION_NOT_REQUESTED


def test_multiple_failure_indicators_conflict():
    agg = aggregate()
    rec = record(agg, identity_ambiguous=PredicateValue.TRUE, policy_denied=PredicateValue.TRUE)
    decision = evaluate_transition(agg, request(agg, MissionState.IDENTITY_AMBIGUOUS, rec))
    assert (decision.outcome, decision.reason_code) == (PolicyOutcome.DENY, PolicyReason.CONFLICTING_FAILURE_EVIDENCE)


def test_failure_indicator_cannot_select_wrong_failure_state():
    agg = aggregate(MissionState.APPROVAL_REQUIRED)
    rec = record(agg, approval_expired=PredicateValue.TRUE)
    decision = evaluate_transition(agg, request(agg, MissionState.APPROVAL_INVALID, rec))
    assert decision.reason_code is PolicyReason.FAILURE_EDGE_MISMATCH


def test_positive_progress_blocked_by_failure_indicator():
    agg = aggregate()
    rec = record(agg, identity_ambiguous=PredicateValue.TRUE, principal_identity_current=PredicateValue.TRUE, principal_identity_unambiguous=PredicateValue.TRUE)
    decision = evaluate_transition(agg, request(agg, MissionState.PRINCIPAL_IDENTIFIED, rec))
    assert decision.reason_code is PolicyReason.FAILURE_INDICATOR_BLOCKS_PROGRESS


@pytest.mark.parametrize("evaluated,reason", [
    ("2026-08-24T09:59:59.999999Z", PolicyReason.PREDICATE_NOT_YET_VALID),
    (EXPIRES, PolicyReason.PREDICATE_EXPIRED),
    ("2026-08-24T11:00:00.000001Z", PolicyReason.PREDICATE_EXPIRED),
])
def test_time_boundaries_deny(evaluated, reason):
    agg = aggregate(); req = request(agg, MissionState.PRINCIPAL_IDENTIFIED, evaluation_time=evaluated)
    assert evaluate_transition(agg, req).reason_code is reason


def test_invalid_validity_window_denied():
    agg = aggregate(); values = {name: PredicateValue.UNKNOWN for name in ALL_PREDICATES}
    rec = TransitionPredicateRecord.create(agg, created_at=EXPIRES, expires_at=CREATED, values=values)
    assert evaluate_transition(agg, request(agg, MissionState.PRINCIPAL_IDENTIFIED, rec)).reason_code is PolicyReason.INVALID_VALIDITY_WINDOW


def test_no_store_filesystem_network_provider_or_credential_imports_and_no_clock_reads():
    files = [Path("sintra_live/l2/mission/transition_contract.py"), Path("sintra_live/l2/mission/transition_policy.py"), Path("sintra_live/l2/mission/transition_errors.py")]
    imports = []
    calls = []
    for path in files:
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import): imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module: imports.append(node.module)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute): calls.append(node.func.attr)
                elif isinstance(node.func, ast.Name): calls.append(node.func.id)
    forbidden = ("store", "socket", "requests", "httpx", "urllib", "provider", "credential", "github", "subprocess")
    assert not [name for name in imports if any(item in name.lower() for item in forbidden)]
    assert not {"open", "write_text", "write_bytes", "replace", "transition", "create", "utc_now", "now", "time"}.intersection(calls)


def test_no_force_admin_apply_or_execute_api():
    from sintra_live.l2.mission import transition_policy
    for name in ("force_state", "admin_bypass", "apply", "execute", "persist"):
        assert not hasattr(transition_policy, name)


def test_i1_bytes_are_not_mutated_by_repeated_evaluation():
    agg = aggregate(); before = agg.canonical_bytes(); rec = record(agg, principal_identity_current=PredicateValue.TRUE, principal_identity_unambiguous=PredicateValue.TRUE)
    for _ in range(10): assert evaluate_transition(agg, request(agg, MissionState.PRINCIPAL_IDENTIFIED, rec)).outcome is PolicyOutcome.ALLOW
    assert agg.canonical_bytes() == before


def test_hash_tamper_is_rejected_at_contract_boundary():
    agg = aggregate(); data = record(agg).to_dict(); data["mission_id"] = "other"
    with pytest.raises(ValueError): TransitionPredicateRecord.from_dict(data)


def test_policy_never_persists_second_mission_truth(tmp_path):
    agg = aggregate(); before = list(tmp_path.rglob("*")); evaluate_transition(agg, request(agg, MissionState.PRINCIPAL_IDENTIFIED)); assert list(tmp_path.rglob("*")) == before
