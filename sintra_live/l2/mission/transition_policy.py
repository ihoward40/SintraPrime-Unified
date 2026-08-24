"""Pure deterministic L2-I2 transition-policy evaluator."""

from __future__ import annotations

from typing import Dict, Iterable, Mapping, Sequence, Tuple

from sintra_live.l2.mission import MissionAggregate, MissionState, canonical_bytes

from .transition_contract import (
    DECISION_SCHEMA_VERSION,
    FAILURE_INDICATORS,
    POLICY_VERSION,
    PredicateValue,
    TransitionPolicyDecision,
    TransitionPolicyRequest,
    _parse_time,
)
from .transition_errors import PolicyOutcome, PolicyReason

FORWARD_EDGES: Dict[Tuple[MissionState, MissionState], Tuple[str, ...]] = {
    (MissionState.RECEIVED, MissionState.PRINCIPAL_IDENTIFIED): ("principal_identity_current", "principal_identity_unambiguous"),
    (MissionState.PRINCIPAL_IDENTIFIED, MissionState.MISSION_SCOPED): ("mission_scope_valid",),
    (MissionState.MISSION_SCOPED, MissionState.MEMORY_RESOLVED): ("memory_record_complete",),
    (MissionState.MEMORY_RESOLVED, MissionState.WORKFORCE_SELECTED): ("workforce_selection_complete",),
    (MissionState.WORKFORCE_SELECTED, MissionState.SPECIALISTS_DISPATCHED): ("specialists_dispatch_complete",),
    (MissionState.SPECIALISTS_DISPATCHED, MissionState.SPECIALISTS_RECONCILED): ("specialist_outputs_reconciled",),
    (MissionState.SPECIALISTS_RECONCILED, MissionState.MODEL_SELECTION_RESOLVED): ("model_decision_complete",),
    (MissionState.MODEL_SELECTION_RESOLVED, MissionState.POLICY_RESOLVED): ("policy_decision_complete",),
    (MissionState.POLICY_RESOLVED, MissionState.AUTHORITY_RESOLVED): ("policy_decision_permits", "authority_snapshot_valid"),
    (MissionState.AUTHORITY_RESOLVED, MissionState.ACTION_PROPOSED): ("action_proposal_complete",),
    (MissionState.ACTION_PROPOSED, MissionState.APPROVAL_REQUIRED): ("approval_required",),
    (MissionState.APPROVAL_REQUIRED, MissionState.APPROVED): ("approval_valid", "approval_unexpired", "approval_unused"),
    (MissionState.APPROVED, MissionState.CAPABILITY_RESOLVED): ("capability_resolution_exact",),
    (MissionState.CAPABILITY_RESOLVED, MissionState.READY): ("capability_resolution_exact", "execution_identity_bound", "preflight_complete"),
    (MissionState.READY, MissionState.EXECUTING): ("execution_identity_bound", "preflight_complete", "provider_attempt_recorded"),
    (MissionState.EXECUTING, MissionState.VERIFYING): ("provider_outcome_known",),
    (MissionState.VERIFYING, MissionState.EVIDENCE_RECONCILIATION): ("independent_readback_complete",),
    (MissionState.EVIDENCE_RECONCILIATION, MissionState.BRIEF_GENERATED): ("evidence_complete", "evidence_sealed"),
    (MissionState.BRIEF_GENERATED, MissionState.COMPLETE): ("evidence_complete", "evidence_sealed", "principal_brief_complete"),
}

FAILURE_EDGES: Dict[Tuple[MissionState, MissionState], str] = {
    (MissionState.RECEIVED, MissionState.IDENTITY_AMBIGUOUS): "identity_ambiguous",
    (MissionState.PRINCIPAL_IDENTIFIED, MissionState.MISSION_SCOPE_INVALID): "mission_scope_invalid",
    (MissionState.PRINCIPAL_IDENTIFIED, MissionState.AUTHORITY_MISSING): "authority_missing",
    (MissionState.MEMORY_RESOLVED, MissionState.MEMORY_POLICY_DENIED): "memory_policy_violation",
    (MissionState.SPECIALISTS_DISPATCHED, MissionState.SPECIALIST_SCOPE_VIOLATION): "specialist_scope_violation",
    (MissionState.MODEL_SELECTION_RESOLVED, MissionState.MODEL_POLICY_DENIED): "model_policy_violation",
    (MissionState.POLICY_RESOLVED, MissionState.POLICY_DENIED): "policy_denied",
    (MissionState.AUTHORITY_RESOLVED, MissionState.AUTHORITY_MISSING): "authority_missing",
    (MissionState.APPROVAL_REQUIRED, MissionState.APPROVAL_INVALID): "approval_invalid",
    (MissionState.APPROVAL_REQUIRED, MissionState.APPROVAL_EXPIRED): "approval_expired",
    (MissionState.APPROVED, MissionState.CAPABILITY_UNAVAILABLE): "capability_unavailable",
    (MissionState.READY, MissionState.EXECUTION_AMBIGUOUS): "execution_ambiguous",
    (MissionState.EXECUTING, MissionState.EXECUTION_FAILED): "execution_failed",
    (MissionState.EXECUTING, MissionState.EXECUTION_AMBIGUOUS): "execution_ambiguous",
    (MissionState.VERIFYING, MissionState.VERIFICATION_FAILED): "verification_failed",
    (MissionState.EVIDENCE_RECONCILIATION, MissionState.EVIDENCE_INCOMPLETE): "evidence_incomplete",
}


def _sorted(values: Iterable[str]) -> Tuple[str, ...]:
    return tuple(sorted(set(values)))


def _decision(aggregate: MissionAggregate, request: TransitionPolicyRequest, outcome: PolicyOutcome, reason: PolicyReason, *, required: Sequence[str] = (), active_failures: Sequence[str] = ()) -> TransitionPolicyDecision:
    values = request.predicates
    required_sorted = _sorted(required)
    satisfied = _sorted(name for name in required_sorted if values.value(name) is PredicateValue.TRUE)
    missing = _sorted(name for name in required_sorted if values.value(name) is PredicateValue.UNKNOWN)
    false = _sorted(name for name in required_sorted if values.value(name) is PredicateValue.FALSE)
    return TransitionPolicyDecision(
        schema_version=DECISION_SCHEMA_VERSION, policy_version=POLICY_VERSION,
        mission_id=aggregate.identity.mission_id, aggregate_version=aggregate.version,
        aggregate_sha256=aggregate.aggregate_sha256, request_sha256=aggregate.identity.request_sha256,
        mission_scope_sha256=aggregate.identity.mission_scope_sha256,
        authority_snapshot_reference=aggregate.identity.authority_snapshot_reference,
        previous_event_sha256=aggregate.previous_event_sha256,
        from_state=request.proposed_from_state, to_state=request.proposed_to_state,
        predicate_set_sha256=values.predicate_set_sha256, evaluation_time=request.evaluation_time,
        outcome=outcome, reason_code=reason, required_predicates=required_sorted,
        satisfied_predicates=satisfied, missing_predicates=missing, false_predicates=false,
        active_failure_indicators=_sorted(active_failures), authority_delta=0,
    )


def evaluate_transition(aggregate: MissionAggregate, request: TransitionPolicyRequest) -> TransitionPolicyDecision:
    """Evaluate policy without persistence, system-clock reads, or store calls."""
    active = _sorted(name for name in FAILURE_INDICATORS if request.predicates.value(name) is PredicateValue.TRUE)

    # 1–2: strict input and aggregate integrity.
    try:
        canonical_bytes(aggregate.to_dict())
        if request.policy_version != POLICY_VERSION:
            return _decision(aggregate, request, PolicyOutcome.DENY, PolicyReason.INVALID_INPUT, active_failures=active)
    except Exception:
        return _decision(aggregate, request, PolicyOutcome.DENY, PolicyReason.INVALID_INPUT, active_failures=active)

    # 3: terminal state cannot reopen or self-transition.
    if aggregate.terminal:
        return _decision(aggregate, request, PolicyOutcome.DENY, PolicyReason.TERMINAL_STATE_PROHIBITION, active_failures=active)

    # 4: aggregate and predicate binding.
    predicates = request.predicates
    bindings_ok = (
        request.expected_aggregate_version == aggregate.version
        and request.expected_aggregate_sha256 == aggregate.aggregate_sha256
        and request.expected_previous_event_sha256 == aggregate.previous_event_sha256
        and request.proposed_from_state is aggregate.current_state
        and predicates.mission_id == aggregate.identity.mission_id
        and predicates.aggregate_version == aggregate.version
        and predicates.aggregate_sha256 == aggregate.aggregate_sha256
        and predicates.request_sha256 == aggregate.identity.request_sha256
        and predicates.mission_scope_sha256 == aggregate.identity.mission_scope_sha256
        and predicates.authority_snapshot_reference == aggregate.identity.authority_snapshot_reference
    )
    if not bindings_ok:
        return _decision(aggregate, request, PolicyOutcome.DENY, PolicyReason.BINDING_FAILURE, active_failures=active)

    # 5: explicit deterministic time.
    try:
        created = _parse_time(predicates.created_at); expires = _parse_time(predicates.expires_at); evaluated = _parse_time(request.evaluation_time)
    except ValueError:
        return _decision(aggregate, request, PolicyOutcome.DENY, PolicyReason.INVALID_TIMESTAMP, active_failures=active)
    if expires <= created:
        return _decision(aggregate, request, PolicyOutcome.DENY, PolicyReason.INVALID_VALIDITY_WINDOW, active_failures=active)
    if evaluated < created:
        return _decision(aggregate, request, PolicyOutcome.DENY, PolicyReason.PREDICATE_NOT_YET_VALID, active_failures=active)
    if evaluated >= expires:
        return _decision(aggregate, request, PolicyOutcome.DENY, PolicyReason.PREDICATE_EXPIRED, active_failures=active)

    kill = predicates.value("kill_switch_active") is PredicateValue.TRUE
    cancel = predicates.value("cancellation_requested") is PredicateValue.TRUE
    if kill:
        if request.proposed_to_state is MissionState.CANCELLED:
            return _decision(aggregate, request, PolicyOutcome.ALLOW, PolicyReason.KILL_SWITCH_CANCELLATION, active_failures=active)
        return _decision(aggregate, request, PolicyOutcome.DENY, PolicyReason.KILL_SWITCH_REQUIRES_CANCELLATION, active_failures=active)
    if cancel:
        if request.proposed_to_state is MissionState.CANCELLED:
            return _decision(aggregate, request, PolicyOutcome.ALLOW, PolicyReason.CANCELLATION_REQUESTED, active_failures=active)
        return _decision(aggregate, request, PolicyOutcome.DENY, PolicyReason.CANCELLATION_REQUIRES_CANCELLED_EDGE, active_failures=active)
    if request.proposed_to_state is MissionState.CANCELLED:
        return _decision(aggregate, request, PolicyOutcome.DENY, PolicyReason.CANCELLATION_NOT_REQUESTED, active_failures=active)

    edge = (request.proposed_from_state, request.proposed_to_state)
    if edge not in FORWARD_EDGES and edge not in FAILURE_EDGES:
        return _decision(aggregate, request, PolicyOutcome.DENY, PolicyReason.INVALID_GRAPH_EDGE, active_failures=active)

    if len(active) > 1:
        return _decision(aggregate, request, PolicyOutcome.DENY, PolicyReason.CONFLICTING_FAILURE_EVIDENCE, active_failures=active)

    if edge in FORWARD_EDGES and active:
        return _decision(aggregate, request, PolicyOutcome.DENY, PolicyReason.FAILURE_INDICATOR_BLOCKS_PROGRESS, required=FORWARD_EDGES[edge], active_failures=active)

    if edge in FAILURE_EDGES:
        required_failure = FAILURE_EDGES[edge]
        if active == (required_failure,):
            return _decision(aggregate, request, PolicyOutcome.ALLOW, PolicyReason.FAILURE_EDGE_ALLOWED, active_failures=active)
        return _decision(aggregate, request, PolicyOutcome.DENY, PolicyReason.FAILURE_EDGE_MISMATCH, active_failures=active)

    required = FORWARD_EDGES[edge]
    if any(predicates.value(name) is PredicateValue.FALSE for name in required):
        return _decision(aggregate, request, PolicyOutcome.DENY, PolicyReason.REQUIRED_PREDICATE_FALSE, required=required, active_failures=active)
    if any(predicates.value(name) is PredicateValue.UNKNOWN for name in required):
        return _decision(aggregate, request, PolicyOutcome.INCOMPLETE, PolicyReason.REQUIRED_PREDICATE_UNKNOWN, required=required, active_failures=active)
    return _decision(aggregate, request, PolicyOutcome.ALLOW, PolicyReason.ALLOWED, required=required, active_failures=active)


__all__ = ["FAILURE_EDGES", "FORWARD_EDGES", "evaluate_transition"]
