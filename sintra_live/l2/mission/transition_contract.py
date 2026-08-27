"""Immutable canonical contracts for the L2-I2 transition policy."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, fields, replace
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Mapping, Tuple

from sintra_live.l2.mission import MissionAggregate, MissionState, canonical_bytes

from .transition_errors import PolicyOutcome, PolicyReason

POLICY_SCHEMA_VERSION = "sp-live-001-l2-i2-transition-policy-contract-v1"
PREDICATE_SCHEMA_VERSION = "sp-live-001-l2-i2-predicate-set-v1"
DECISION_SCHEMA_VERSION = "sp-live-001-l2-i2-transition-decision-v1"
POLICY_VERSION = "sp-live-001-l2-transition-policy-v1"
PREDICATE_HASH_DOMAIN = b"SP-LIVE-001:L2:I2:PREDICATE-SET:v1\0"
DECISION_HASH_DOMAIN = b"SP-LIVE-001:L2:I2:TRANSITION-DECISION:v1\0"


class PredicateValue(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


POSITIVE_PREDICATES = (
    "principal_identity_current", "principal_identity_unambiguous", "mission_scope_valid",
    "memory_record_complete", "workforce_selection_complete", "specialists_dispatch_complete",
    "specialist_outputs_reconciled", "model_decision_complete", "policy_decision_complete",
    "policy_decision_permits", "authority_snapshot_valid", "action_proposal_complete",
    "approval_required", "approval_valid", "approval_unexpired", "approval_unused",
    "capability_resolution_exact", "execution_identity_bound", "preflight_complete",
    "provider_attempt_recorded", "provider_outcome_known", "independent_readback_complete",
    "evidence_complete", "evidence_sealed", "principal_brief_complete",
)
CONTROL_PREDICATES = ("cancellation_requested", "kill_switch_active")
FAILURE_INDICATORS = (
    "identity_ambiguous", "mission_scope_invalid", "memory_policy_violation",
    "specialist_scope_violation", "model_policy_violation", "policy_denied",
    "authority_missing", "approval_invalid", "approval_expired", "capability_unavailable",
    "execution_ambiguous", "execution_failed", "verification_failed", "evidence_incomplete",
)
ALL_PREDICATES = POSITIVE_PREDICATES + CONTROL_PREDICATES + FAILURE_INDICATORS


def _strict_keys(data: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(data) != expected:
        raise ValueError(f"{label} fields must exactly match schema")


def _parse_time(value: str) -> datetime:
    if not isinstance(value, str) or len(value) != 27 or not value.endswith("Z"):
        raise ValueError("timestamp must be YYYY-MM-DDTHH:MM:SS.ffffffZ")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")


@dataclass(frozen=True)
class TransitionPredicateRecord:
    schema_version: str
    policy_version: str
    mission_id: str
    aggregate_version: int
    aggregate_sha256: str
    request_sha256: str
    mission_scope_sha256: str
    authority_snapshot_reference: str
    created_at: str
    expires_at: str
    predicates: Tuple[Tuple[str, PredicateValue], ...]
    predicate_set_sha256: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != PREDICATE_SCHEMA_VERSION or self.policy_version != POLICY_VERSION:
            raise ValueError("unknown predicate schema or policy version")
        if isinstance(self.aggregate_version, bool) or not isinstance(self.aggregate_version, int) or self.aggregate_version < 0:
            raise ValueError("invalid aggregate version")
        _parse_time(self.created_at); _parse_time(self.expires_at)
        names = tuple(name for name, _ in self.predicates)
        if names != tuple(sorted(ALL_PREDICATES)) or len(names) != len(set(names)):
            raise ValueError("predicate fields must be complete, sorted, and unique")
        if any(not isinstance(value, PredicateValue) for _, value in self.predicates):
            raise ValueError("invalid predicate value")
        expected = self.compute_sha256()
        if self.predicate_set_sha256 and self.predicate_set_sha256 != expected:
            raise ValueError("predicate set hash mismatch")
        object.__setattr__(self, "predicate_set_sha256", expected)

    @classmethod
    def create(cls, aggregate: MissionAggregate, *, created_at: str, expires_at: str, values: Mapping[str, PredicateValue]) -> "TransitionPredicateRecord":
        _strict_keys(values, set(ALL_PREDICATES), "predicate")
        return cls(
            schema_version=PREDICATE_SCHEMA_VERSION, policy_version=POLICY_VERSION,
            mission_id=aggregate.identity.mission_id, aggregate_version=aggregate.version,
            aggregate_sha256=aggregate.aggregate_sha256, request_sha256=aggregate.identity.request_sha256,
            mission_scope_sha256=aggregate.identity.mission_scope_sha256,
            authority_snapshot_reference=aggregate.identity.authority_snapshot_reference,
            created_at=created_at, expires_at=expires_at,
            predicates=tuple(sorted((name, PredicateValue(value)) for name, value in values.items())),
        )

    def value(self, name: str) -> PredicateValue:
        return dict(self.predicates)[name]

    def body(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version, "policy_version": self.policy_version,
            "mission_id": self.mission_id, "aggregate_version": self.aggregate_version,
            "aggregate_sha256": self.aggregate_sha256, "request_sha256": self.request_sha256,
            "mission_scope_sha256": self.mission_scope_sha256,
            "authority_snapshot_reference": self.authority_snapshot_reference,
            "created_at": self.created_at, "expires_at": self.expires_at,
            **{name: value.value for name, value in self.predicates},
        }

    def compute_sha256(self) -> str:
        return hashlib.sha256(PREDICATE_HASH_DOMAIN + canonical_bytes(self.body())).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {**self.body(), "predicate_set_sha256": self.predicate_set_sha256}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TransitionPredicateRecord":
        expected = {"schema_version", "policy_version", "mission_id", "aggregate_version", "aggregate_sha256", "request_sha256", "mission_scope_sha256", "authority_snapshot_reference", "created_at", "expires_at", "predicate_set_sha256", *ALL_PREDICATES}
        _strict_keys(data, expected, "predicate record")
        return cls(
            schema_version=data["schema_version"], policy_version=data["policy_version"], mission_id=data["mission_id"],
            aggregate_version=data["aggregate_version"], aggregate_sha256=data["aggregate_sha256"],
            request_sha256=data["request_sha256"], mission_scope_sha256=data["mission_scope_sha256"],
            authority_snapshot_reference=data["authority_snapshot_reference"], created_at=data["created_at"],
            expires_at=data["expires_at"], predicates=tuple(sorted((name, PredicateValue(data[name])) for name in ALL_PREDICATES)),
            predicate_set_sha256=data["predicate_set_sha256"],
        )


@dataclass(frozen=True)
class TransitionPolicyRequest:
    policy_version: str
    proposed_from_state: MissionState
    proposed_to_state: MissionState
    expected_aggregate_version: int
    expected_aggregate_sha256: str
    expected_previous_event_sha256: str
    evaluation_time: str
    predicates: TransitionPredicateRecord


@dataclass(frozen=True)
class TransitionPolicyDecision:
    schema_version: str
    policy_version: str
    mission_id: str
    aggregate_version: int
    aggregate_sha256: str
    request_sha256: str
    mission_scope_sha256: str
    authority_snapshot_reference: str
    previous_event_sha256: str
    from_state: MissionState
    to_state: MissionState
    predicate_set_sha256: str
    evaluation_time: str
    outcome: PolicyOutcome
    reason_code: PolicyReason
    required_predicates: Tuple[str, ...]
    satisfied_predicates: Tuple[str, ...]
    missing_predicates: Tuple[str, ...]
    false_predicates: Tuple[str, ...]
    active_failure_indicators: Tuple[str, ...]
    authority_delta: int = 0
    decision_sha256: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != DECISION_SCHEMA_VERSION or self.policy_version != POLICY_VERSION:
            raise ValueError("unknown decision schema or policy version")
        _parse_time(self.evaluation_time)
        for name in ("required_predicates", "satisfied_predicates", "missing_predicates", "false_predicates", "active_failure_indicators"):
            values = getattr(self, name)
            if values != tuple(sorted(set(values))):
                raise ValueError(f"{name} must be sorted and duplicate-free")
        if self.authority_delta != 0:
            raise ValueError("I2 authority delta must remain zero")
        expected = self.compute_sha256()
        if self.decision_sha256 and self.decision_sha256 != expected:
            raise ValueError("decision hash mismatch")
        object.__setattr__(self, "decision_sha256", expected)

    def body(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        for item in fields(self):
            if item.name == "decision_sha256":
                continue
            value = getattr(self, item.name)
            if isinstance(value, Enum): value = value.value
            elif isinstance(value, tuple): value = list(value)
            data[item.name] = value
        return data

    def compute_sha256(self) -> str:
        return hashlib.sha256(DECISION_HASH_DOMAIN + canonical_bytes(self.body())).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {**self.body(), "decision_sha256": self.decision_sha256}


__all__ = [
    "ALL_PREDICATES", "CONTROL_PREDICATES", "DECISION_HASH_DOMAIN", "DECISION_SCHEMA_VERSION",
    "FAILURE_INDICATORS", "POLICY_SCHEMA_VERSION", "POLICY_VERSION", "POSITIVE_PREDICATES",
    "PREDICATE_HASH_DOMAIN", "PREDICATE_SCHEMA_VERSION", "PredicateValue",
    "TransitionPolicyDecision", "TransitionPolicyRequest", "TransitionPredicateRecord", "_parse_time",
]
