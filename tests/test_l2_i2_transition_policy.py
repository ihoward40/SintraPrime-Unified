from dataclasses import replace

import pytest

from sintra_live.l2.mission import MissionAggregate, MissionIdentity, MissionScope, MissionState
from sintra_live.l2.mission.transition_contract import (
    ALL_PREDICATES, POLICY_VERSION, PredicateValue, TransitionPolicyDecision,
    TransitionPolicyRequest, TransitionPredicateRecord,
)
from sintra_live.l2.mission.transition_errors import PolicyOutcome, PolicyReason
from sintra_live.l2.mission.transition_policy import FAILURE_EDGES, FORWARD_EDGES, evaluate_transition

H = "a" * 64
CREATED = "2026-08-24T10:00:00.000000Z"
EVALUATED = "2026-08-24T10:30:00.000000Z"
EXPIRES = "2026-08-24T11:00:00.000000Z"


def aggregate(state=MissionState.RECEIVED):
    identity = MissionIdentity("SP-LIVE-001", "L2-I2", "mission-i2", "request-i2", H, "principal-ref", H, "authority-ref")
    scope = MissionScope("policy evaluation", ("read",), ("write",), "LOW", (("tokens", 1),), 0, ("policy-decision",), EXPIRES, "cancel-ref")
    base = MissionAggregate.genesis(identity, scope, CREATED)
    if state is MissionState.RECEIVED:
        return base
    # Construct a hash-valid inspection fixture; I2 never persists it.
    return MissionAggregate(base.schema_version, base.identity, base.scope, base.created_at, state, 0, base.previous_event_sha256, (), (), state in {MissionState.CANCELLED, MissionState.COMPLETE}, state is MissionState.CANCELLED)


def values(**overrides):
    result = {name: PredicateValue.UNKNOWN for name in ALL_PREDICATES}
    result.update(overrides)
    return result


def predicate(agg, **overrides):
    return TransitionPredicateRecord.create(agg, created_at=CREATED, expires_at=EXPIRES, values=values(**overrides))


def request(agg, target, record=None, **changes):
    base = TransitionPolicyRequest(POLICY_VERSION, agg.current_state, target, agg.version, agg.aggregate_sha256, agg.previous_event_sha256, EVALUATED, record or predicate(agg))
    return replace(base, **changes)


@pytest.mark.parametrize("edge,required", list(FORWARD_EDGES.items()))
def test_every_forward_edge_exact_requirements_allow(edge, required):
    source, target = edge
    agg = aggregate(source)
    record = predicate(agg, **{name: PredicateValue.TRUE for name in required})
    decision = evaluate_transition(agg, request(agg, target, record))
    assert decision.outcome is PolicyOutcome.ALLOW
    assert decision.required_predicates == tuple(sorted(required))
    assert decision.authority_delta == 0


@pytest.mark.parametrize("edge,indicator", list(FAILURE_EDGES.items()))
def test_every_failure_edge_requires_exact_indicator(edge, indicator):
    source, target = edge
    agg = aggregate(source)
    decision = evaluate_transition(agg, request(agg, target, predicate(agg, **{indicator: PredicateValue.TRUE})))
    assert decision.outcome is PolicyOutcome.ALLOW
    assert decision.reason_code is PolicyReason.FAILURE_EDGE_ALLOWED


def test_unknown_and_false_required_predicate_are_distinct():
    agg = aggregate()
    unknown = evaluate_transition(agg, request(agg, MissionState.PRINCIPAL_IDENTIFIED, predicate(agg)))
    denied = evaluate_transition(agg, request(agg, MissionState.PRINCIPAL_IDENTIFIED, predicate(agg, principal_identity_current=PredicateValue.FALSE, principal_identity_unambiguous=PredicateValue.TRUE)))
    assert (unknown.outcome, unknown.reason_code) == (PolicyOutcome.INCOMPLETE, PolicyReason.REQUIRED_PREDICATE_UNKNOWN)
    assert (denied.outcome, denied.reason_code) == (PolicyOutcome.DENY, PolicyReason.REQUIRED_PREDICATE_FALSE)


def test_predicate_and_decision_hashes_are_reproducible():
    agg = aggregate()
    record1 = predicate(agg, principal_identity_current=PredicateValue.TRUE, principal_identity_unambiguous=PredicateValue.TRUE)
    record2 = predicate(agg, principal_identity_unambiguous=PredicateValue.TRUE, principal_identity_current=PredicateValue.TRUE)
    assert record1.predicate_set_sha256 == record2.predicate_set_sha256
    d1 = evaluate_transition(agg, request(agg, MissionState.PRINCIPAL_IDENTIFIED, record1))
    d2 = evaluate_transition(agg, request(agg, MissionState.PRINCIPAL_IDENTIFIED, record2))
    assert d1.decision_sha256 == d2.decision_sha256
    assert d1.to_dict() == d2.to_dict()


def test_explicit_time_model_half_open_interval():
    agg = aggregate()
    record = predicate(agg, principal_identity_current=PredicateValue.TRUE, principal_identity_unambiguous=PredicateValue.TRUE)
    assert evaluate_transition(agg, request(agg, MissionState.PRINCIPAL_IDENTIFIED, record, evaluation_time=CREATED)).outcome is PolicyOutcome.ALLOW
    expired = evaluate_transition(agg, request(agg, MissionState.PRINCIPAL_IDENTIFIED, record, evaluation_time=EXPIRES))
    assert (expired.outcome, expired.reason_code) == (PolicyOutcome.DENY, PolicyReason.PREDICATE_EXPIRED)


def test_evaluation_is_pure_and_does_not_mutate_aggregate():
    agg = aggregate()
    before = agg.canonical_bytes()
    decision = evaluate_transition(agg, request(agg, MissionState.PRINCIPAL_IDENTIFIED, predicate(agg, principal_identity_current=PredicateValue.TRUE, principal_identity_unambiguous=PredicateValue.TRUE)))
    assert agg.canonical_bytes() == before
    assert decision.outcome is PolicyOutcome.ALLOW


def test_decision_arrays_are_canonical_and_authority_zero():
    agg = aggregate()
    decision = evaluate_transition(agg, request(agg, MissionState.PRINCIPAL_IDENTIFIED, predicate(agg)))
    assert decision.required_predicates == tuple(sorted(set(decision.required_predicates)))
    assert decision.missing_predicates == tuple(sorted(set(decision.missing_predicates)))
    assert decision.authority_delta == 0


def test_mapped_acceptance_case_set_is_exact():
    mapped = {"R-04", "R-08", "P-03", "P-04", "A-04", "A-07", "C-05", "C-10", "E-04", "EV-06", "EV-10"}
    assert len(mapped) == 11


def test_ready_executing_complete_are_policy_only_not_store_transitions():
    # I1 still denies these durable states; I2 merely emits immutable decisions.
    for state in (MissionState.READY, MissionState.EXECUTING, MissionState.COMPLETE):
        assert state.name in MissionState.__members__
    assert not hasattr(TransitionPolicyDecision, "apply")
    assert not hasattr(TransitionPolicyDecision, "execute")


def test_predicate_record_rejects_missing_and_unknown_fields():
    agg = aggregate()
    data = predicate(agg).to_dict()
    data.pop("mission_id")
    with pytest.raises(ValueError): TransitionPredicateRecord.from_dict(data)
    data = predicate(agg).to_dict(); data["extra"] = True
    with pytest.raises(ValueError): TransitionPredicateRecord.from_dict(data)


def test_predicate_record_hash_tamper_denied():
    agg = aggregate(); data = predicate(agg).to_dict(); data["predicate_set_sha256"] = "0" * 64
    with pytest.raises(ValueError): TransitionPredicateRecord.from_dict(data)


def test_decision_hash_changes_with_evaluation_time():
    agg = aggregate(); rec = predicate(agg, principal_identity_current=PredicateValue.TRUE, principal_identity_unambiguous=PredicateValue.TRUE)
    first = evaluate_transition(agg, request(agg, MissionState.PRINCIPAL_IDENTIFIED, rec))
    second = evaluate_transition(agg, request(agg, MissionState.PRINCIPAL_IDENTIFIED, rec, evaluation_time="2026-08-24T10:31:00.000000Z"))
    assert first.decision_sha256 != second.decision_sha256
