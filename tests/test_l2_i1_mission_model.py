import dataclasses
import json
from datetime import datetime, timedelta, timezone

import pytest

from sintra_live.l2.mission import (
    GENESIS_PREVIOUS_EVENT_SHA256,
    MissionAggregate,
    MissionIdentity,
    MissionScope,
    MissionState,
    TransitionRequest,
    canonical_bytes,
    reachable_in_i1,
)
from sintra_live.l2.mission.errors import SchemaError

H = "a" * 64


def identity(mission_id="mission-001"):
    return MissionIdentity("SP-LIVE-001", "L2-I1", mission_id, "request-001", H, "principal-ref", H, "authority-ref")


def scope(**changes):
    values = dict(
        purpose="Durable mission control",
        allowed_operations=("mission.read", "mission.transition"),
        prohibited_operations=("external.write", "provider.call"),
        consequence_ceiling="E0",
        budget_ceilings=(("tokens", 100), ("wall_seconds", 30)),
        side_effect_budget=0,
        required_evidence_types=("mission_transition",),
        expiry="2030-01-01T00:00:00.000000Z",
        cancellation_authority="principal-ref",
    )
    values.update(changes)
    return MissionScope(**values)


def test_genesis_is_immutable_canonical_and_zero_write():
    aggregate = MissionAggregate.genesis(identity(), scope(), "2026-08-24T13:00:00.000000Z")
    assert aggregate.version == 0
    assert aggregate.current_state is MissionState.RECEIVED
    assert aggregate.previous_event_sha256 == GENESIS_PREVIOUS_EVENT_SHA256
    assert aggregate.scope.side_effect_budget == 0
    assert canonical_bytes(aggregate.to_dict()) == aggregate.canonical_bytes()
    assert aggregate.canonical_bytes() == aggregate.canonical_bytes()
    assert len(aggregate.aggregate_sha256) == 64
    with pytest.raises(dataclasses.FrozenInstanceError):
        aggregate.version = 1


def test_canonical_json_byte_contract():
    raw = canonical_bytes({"é": [1, "x"], "a": True})
    assert raw == '{"a":true,"é":[1,"x"]}'.encode()
    assert not raw.endswith(b"\n")
    with pytest.raises(SchemaError):
        canonical_bytes({"value": 1.5})
    with pytest.raises(SchemaError):
        canonical_bytes({"value": {"unordered"}})


@pytest.mark.parametrize("bad", [1, -1, True])
def test_side_effect_budget_must_be_zero(bad):
    with pytest.raises(SchemaError):
        scope(side_effect_budget=bad)


def test_semantic_sets_must_be_sorted_and_unique():
    with pytest.raises(SchemaError):
        scope(allowed_operations=("z", "a"))
    with pytest.raises(SchemaError):
        scope(allowed_operations=("a", "a"))


def test_mission_identifier_rejects_path_traversal():
    with pytest.raises(SchemaError):
        identity("../escape")


def test_transition_request_hash_is_deterministic_and_bound():
    kwargs = dict(
        mission_id="mission-001",
        idempotency_key="transition-001",
        expected_version=0,
        expected_state=MissionState.RECEIVED,
        expected_previous_event_sha256=GENESIS_PREVIOUS_EVENT_SHA256,
        to_state=MissionState.PRINCIPAL_IDENTIFIED,
        reason="identity verified",
        evidence_sha256=H,
        actor_reference="principal-ref",
    )
    assert TransitionRequest(**kwargs).transition_request_sha256 == TransitionRequest(**kwargs).transition_request_sha256


def test_strict_deserialization_denies_unknown_field():
    aggregate = MissionAggregate.genesis(identity(), scope(), "2026-08-24T13:00:00.000000Z")
    data = aggregate.to_dict()
    data["unknown"] = "denied"
    with pytest.raises(SchemaError):
        MissionAggregate.from_dict(data)


def test_later_operational_states_are_unreachable():
    assert not reachable_in_i1(MissionState.READY)
    assert not reachable_in_i1(MissionState.EXECUTING)
    assert not reachable_in_i1(MissionState.COMPLETE)
    assert reachable_in_i1(MissionState.CANCELLED)


def test_timestamp_requires_canonical_utc_microseconds():
    with pytest.raises(SchemaError):
        MissionAggregate.genesis(identity(), scope(), "2026-08-24T13:00:00+00:00")


def test_missing_expected_version_is_not_constructible():
    with pytest.raises(TypeError):
        TransitionRequest(
            mission_id="mission-001", idempotency_key="x", expected_state=MissionState.RECEIVED,
            expected_previous_event_sha256=GENESIS_PREVIOUS_EVENT_SHA256, to_state=MissionState.CANCELLED,
            reason="x", evidence_sha256=H, actor_reference="principal-ref"
        )
