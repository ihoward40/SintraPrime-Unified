"""Frozen state identifiers and the enabled L2-I1 transition subset."""

from __future__ import annotations

from enum import Enum


class MissionState(str, Enum):
    RECEIVED = "RECEIVED"
    PRINCIPAL_IDENTIFIED = "PRINCIPAL_IDENTIFIED"
    MISSION_SCOPED = "MISSION_SCOPED"
    MEMORY_RESOLVED = "MEMORY_RESOLVED"
    WORKFORCE_SELECTED = "WORKFORCE_SELECTED"
    SPECIALISTS_DISPATCHED = "SPECIALISTS_DISPATCHED"
    SPECIALISTS_RECONCILED = "SPECIALISTS_RECONCILED"
    MODEL_SELECTION_RESOLVED = "MODEL_SELECTION_RESOLVED"
    POLICY_RESOLVED = "POLICY_RESOLVED"
    AUTHORITY_RESOLVED = "AUTHORITY_RESOLVED"
    ACTION_PROPOSED = "ACTION_PROPOSED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVED = "APPROVED"
    CAPABILITY_RESOLVED = "CAPABILITY_RESOLVED"
    READY = "READY"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    EVIDENCE_RECONCILIATION = "EVIDENCE_RECONCILIATION"
    BRIEF_GENERATED = "BRIEF_GENERATED"
    COMPLETE = "COMPLETE"

    IDENTITY_AMBIGUOUS = "IDENTITY_AMBIGUOUS"
    MISSION_SCOPE_INVALID = "MISSION_SCOPE_INVALID"
    MEMORY_POLICY_DENIED = "MEMORY_POLICY_DENIED"
    SPECIALIST_SCOPE_VIOLATION = "SPECIALIST_SCOPE_VIOLATION"
    MODEL_POLICY_DENIED = "MODEL_POLICY_DENIED"
    POLICY_DENIED = "POLICY_DENIED"
    AUTHORITY_MISSING = "AUTHORITY_MISSING"
    APPROVAL_INVALID = "APPROVAL_INVALID"
    APPROVAL_EXPIRED = "APPROVAL_EXPIRED"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    EXECUTION_AMBIGUOUS = "EXECUTION_AMBIGUOUS"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    EVIDENCE_INCOMPLETE = "EVIDENCE_INCOMPLETE"
    CANCELLED = "CANCELLED"


TERMINAL_STATES = frozenset(
    {
        MissionState.IDENTITY_AMBIGUOUS,
        MissionState.MISSION_SCOPE_INVALID,
        MissionState.MEMORY_POLICY_DENIED,
        MissionState.SPECIALIST_SCOPE_VIOLATION,
        MissionState.MODEL_POLICY_DENIED,
        MissionState.POLICY_DENIED,
        MissionState.AUTHORITY_MISSING,
        MissionState.APPROVAL_INVALID,
        MissionState.APPROVAL_EXPIRED,
        MissionState.CAPABILITY_UNAVAILABLE,
        MissionState.EXECUTION_AMBIGUOUS,
        MissionState.EXECUTION_FAILED,
        MissionState.VERIFICATION_FAILED,
        MissionState.EVIDENCE_INCOMPLETE,
        MissionState.CANCELLED,
        MissionState.COMPLETE,
    }
)

# I1 intentionally enables only the foundational early transitions. Later
# operational states exist for stable serialization but remain unreachable.
I1_ENABLED_TRANSITIONS = {
    MissionState.RECEIVED: frozenset(
        {
            MissionState.PRINCIPAL_IDENTIFIED,
            MissionState.IDENTITY_AMBIGUOUS,
            MissionState.CANCELLED,
        }
    ),
    MissionState.PRINCIPAL_IDENTIFIED: frozenset(
        {
            MissionState.MISSION_SCOPED,
            MissionState.MISSION_SCOPE_INVALID,
            MissionState.AUTHORITY_MISSING,
            MissionState.CANCELLED,
        }
    ),
    MissionState.MISSION_SCOPED: frozenset({MissionState.CANCELLED}),
}


def is_i1_transition_enabled(from_state: MissionState, to_state: MissionState) -> bool:
    if from_state in TERMINAL_STATES:
        return False
    return to_state in I1_ENABLED_TRANSITIONS.get(from_state, frozenset())


def is_terminal(state: MissionState) -> bool:
    return state in TERMINAL_STATES


def reachable_in_i1(target: MissionState) -> bool:
    """Mechanical graph reachability from RECEIVED in the enabled I1 graph."""
    seen = {MissionState.RECEIVED}
    work = [MissionState.RECEIVED]
    while work:
        current = work.pop()
        for nxt in I1_ENABLED_TRANSITIONS.get(current, frozenset()):
            if nxt not in seen:
                seen.add(nxt)
                work.append(nxt)
    return target in seen
