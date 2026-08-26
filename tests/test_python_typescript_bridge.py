"""Focused tests for the governed Python↔TypeScript bridge adapter.

These tests verify:
  - envelope round-trip (serialize → deserialize)
  - schema version mismatch denial
  - authority_delta != 0 denial
  - side_effects != 0 denial
  - wrong canonical source denial
  - tampered payload / integrity hash mismatch denial
  - missing required field denial
  - projection from a mock L2 aggregate
  - Python↔TypeScript wire compatibility (hash determinism)
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from sintra_live.l2.python_typescript_bridge import (
    BRIDGE_SCHEMA_VERSION,
    BridgeEnvelope,
    BridgeEnvelopeError,
    BridgeProjection,
    deserialize_envelope,
    project_mission_state,
    serialize_envelope,
)


# ── Test helpers ──────────────────────────────────────────────────────────────

def _mock_aggregate(
    mission_id: str = "test-mission-001",
    version: int = 3,
    aggregate_sha256: str = "a" * 64,
    state_value: str = "MISSION_SCOPED",
) -> Any:
    """Build a mock L2 aggregate with the attributes the bridge reads."""
    identity = MagicMock()
    identity.mission_id = mission_id
    aggregate = MagicMock()
    aggregate.identity = identity
    aggregate.version = version
    aggregate.aggregate_sha256 = aggregate_sha256
    state = MagicMock()
    state.value = state_value
    aggregate.current_state = state
    return aggregate


def _valid_projection(**overrides: Any) -> BridgeProjection:
    defaults = dict(
        mission_id="test-mission-001",
        aggregate_version=3,
        aggregate_sha256="a" * 64,
        current_state="MISSION_SCOPED",
        authority_delta=0,
        side_effects=0,
        canonical_state_source="sintra_live/l2",
    )
    defaults.update(overrides)
    return BridgeProjection(**defaults)


# ── Round-trip tests ──────────────────────────────────────────────────────────

def test_envelope_round_trip():
    """serialize → deserialize produces identical envelope."""
    proj = _valid_projection()
    envelope = serialize_envelope(proj, payload={"summary": "test"})
    raw = envelope.to_json()
    restored = deserialize_envelope(raw)
    assert restored.mission_id == proj.mission_id
    assert restored.aggregate_version == proj.aggregate_version
    assert restored.aggregate_sha256 == proj.aggregate_sha256
    assert restored.current_state == proj.current_state
    assert restored.authority_delta == 0
    assert restored.side_effects == 0
    assert restored.envelope_sha256 == envelope.envelope_sha256
    assert restored.payload == {"summary": "test"}


def test_envelope_hash_is_deterministic():
    """Same projection + payload always produces the same hash."""
    proj = _valid_projection()
    e1 = serialize_envelope(proj, payload={"x": 1})
    e2 = serialize_envelope(proj, payload={"x": 1})
    assert e1.envelope_sha256 == e2.envelope_sha256


# ── Fail-closed tests ─────────────────────────────────────────────────────────

def test_schema_version_mismatch_denied():
    """Envelopes with wrong schema_version are rejected."""
    proj = _valid_projection()
    envelope = serialize_envelope(proj)
    raw = json.loads(envelope.to_json())
    raw["schema_version"] = 999
    with pytest.raises(BridgeEnvelopeError, match="schema_version mismatch"):
        deserialize_envelope(json.dumps(raw, sort_keys=True).encode())


def test_authority_delta_nonzero_denied():
    """Envelopes with nonzero authority_delta are rejected."""
    proj = _valid_projection()
    envelope = serialize_envelope(proj)
    raw = json.loads(envelope.to_json())
    raw["authority_delta"] = 1
    # Recompute hash to prove the value itself is rejected, not just hash
    body_for_hash = {k: v for k, v in raw.items() if k != "envelope_sha256"}
    raw["envelope_sha256"] = hashlib.sha256(
        json.dumps(body_for_hash, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    with pytest.raises(BridgeEnvelopeError, match="authority_delta must be zero"):
        deserialize_envelope(json.dumps(raw, sort_keys=True).encode())


def test_side_effects_nonzero_denied():
    """Envelopes with nonzero side_effects are rejected."""
    proj = _valid_projection()
    envelope = serialize_envelope(proj)
    raw = json.loads(envelope.to_json())
    raw["side_effects"] = 1
    body_for_hash = {k: v for k, v in raw.items() if k != "envelope_sha256"}
    raw["envelope_sha256"] = hashlib.sha256(
        json.dumps(body_for_hash, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    with pytest.raises(BridgeEnvelopeError, match="side_effects must be zero"):
        deserialize_envelope(json.dumps(raw, sort_keys=True).encode())


def test_wrong_canonical_source_denied():
    """Envelopes not from sintra_live/l2 are rejected."""
    proj = _valid_projection(canonical_state_source="wrong/source")
    # serialize_envelope doesn't validate — it just packages
    # deserialize_envelope must reject
    envelope = serialize_envelope(proj)
    raw = envelope.to_json()
    with pytest.raises(BridgeEnvelopeError, match="canonical_state_source"):
        deserialize_envelope(raw)


def test_tampered_payload_denied():
    """Tampering with the payload after sealing is detected by hash mismatch."""
    proj = _valid_projection()
    envelope = serialize_envelope(proj, payload={"safe": True})
    raw = json.loads(envelope.to_json())
    raw["payload"]["safe"] = False  # tamper
    with pytest.raises(BridgeEnvelopeError, match="integrity hash mismatch"):
        deserialize_envelope(json.dumps(raw, sort_keys=True).encode())


def test_missing_required_field_denied():
    """Missing mission_id is rejected."""
    proj = _valid_projection()
    envelope = serialize_envelope(proj)
    raw = json.loads(envelope.to_json())
    del raw["mission_id"]
    with pytest.raises(BridgeEnvelopeError, match="missing required field: mission_id"):
        deserialize_envelope(json.dumps(raw, sort_keys=True).encode())


def test_invalid_json_denied():
    """Malformed JSON is rejected cleanly."""
    with pytest.raises(BridgeEnvelopeError, match="not valid JSON"):
        deserialize_envelope(b"{not json")


def test_nonzero_authority_in_projection_does_not_leak():
    """A projection with authority_delta != 0 still serializes with 0
    because serialize_envelope hard-codes from the projection, but the
    envelope itself carries the projection's value.  The deserializer
    must reject it."""
    proj = _valid_projection(authority_delta=1)
    envelope = serialize_envelope(proj)
    # The envelope carries authority_delta=1
    assert envelope.authority_delta == 1
    # Deserialization must reject
    with pytest.raises(BridgeEnvelopeError, match="authority_delta must be zero"):
        deserialize_envelope(envelope.to_json())


# ── Projection tests ──────────────────────────────────────────────────────────

def test_project_mission_state_from_mock_aggregate():
    """project_mission_state extracts correct fields from an L2 aggregate."""
    aggregate = _mock_aggregate()
    proj = project_mission_state(aggregate)
    assert proj.mission_id == "test-mission-001"
    assert proj.aggregate_version == 3
    assert proj.aggregate_sha256 == "a" * 64
    assert proj.current_state == "MISSION_SCOPED"
    assert proj.authority_delta == 0
    assert proj.side_effects == 0
    assert proj.canonical_state_source == "sintra_live/l2"


def test_project_mission_state_incomplete_aggregate_denied():
    """Missing mission_id or version raises BridgeEnvelopeError."""
    aggregate = MagicMock()
    aggregate.identity = MagicMock()
    aggregate.identity.mission_id = ""
    aggregate.version = 1
    aggregate.aggregate_sha256 = "abc"
    with pytest.raises(BridgeEnvelopeError, match="incomplete"):
        project_mission_state(aggregate)


# ── Python↔TypeScript wire compatibility ────────────────────────────────────────

def test_wire_format_matches_typescript_expectations():
    """The Python JSON output has the exact field names and order the
    TypeScript deserializeEnvelope function expects."""
    proj = _valid_projection()
    envelope = serialize_envelope(proj, payload={"key": "value"})
    raw = json.loads(envelope.to_json())
    # TypeScript expects these exact fields
    expected_fields = {
        "schema_version", "mission_id", "aggregate_version",
        "aggregate_sha256", "current_state", "authority_delta",
        "side_effects", "canonical_state_source", "payload",
        "envelope_sha256",
    }
    assert set(raw.keys()) == expected_fields
    assert raw["schema_version"] == BRIDGE_SCHEMA_VERSION
    assert raw["canonical_state_source"] == "sintra_live/l2"


# ---------------------------------------------------------------------------
# V1 canonical bridge runtime adapter tests
# ---------------------------------------------------------------------------

from sintra_live.l2.python_typescript_bridge import (
    BridgeExecutionOutcome,
    BridgeTransportStatus,
    build_v1_envelope,
    build_v1_result,
    execute_via_bridge,
    receive_v1_envelope,
    receive_v1_result,
)
from sintra_live.l2.bridge_envelope_contract import (
    BRIDGE_CONTRACT_VERSION,
    AuthorityDecision,
    BridgeEnvelopeV1,
    BridgeResultV1,
    BridgeValidationError,
    InMemoryNonceTracker,
    compute_evidence_sha256,
    compute_payload_sha256,
    deserialize_envelope_v1,
    deserialize_result_v1,
    serialize_envelope_v1,
    serialize_result_v1,
)
from sintra_live.l2.action_envelope_contract import ConsequenceClass


def _v1_projection(**overrides: Any) -> BridgeProjection:
    defaults = dict(
        mission_id="v1-mission-001",
        aggregate_version=5,
        aggregate_sha256="b" * 64,
        current_state="MISSION_SCOPED",
        authority_delta=0,
        side_effects=0,
        canonical_state_source="sintra_live/l2",
    )
    defaults.update(overrides)
    return BridgeProjection(**defaults)


def _v1_payload() -> Dict[str, Any]:
    return {"action": "dogfood.execute", "data": {"key": "v1-value"}}


def test_v1_envelope_build_and_receive():
    """build_v1_envelope → serialize → receive_v1_envelope round-trips."""
    proj = _v1_projection()
    payload = _v1_payload()
    envelope = build_v1_envelope(
        projection=proj,
        authority_decision=AuthorityDecision.ALLOW.value,
        execution_id="v1-exec-001",
        nonce="v1-nonce-001",
        tenant_id="v1-tenant-001",
        actor_id="v1-actor-001",
        capability_id="named_agents",
        payload=payload,
    )
    # Envelope is a canonical V1
    assert isinstance(envelope, BridgeEnvelopeV1)
    assert envelope.schema_version == BRIDGE_CONTRACT_VERSION
    assert envelope.mission_id == proj.mission_id
    assert envelope.payload_sha256 == compute_payload_sha256(payload)

    # Serialize → receive round-trip
    raw = serialize_envelope_v1(envelope)
    tracker = InMemoryNonceTracker()
    restored = receive_v1_envelope(
        raw,
        nonce_tracker=tracker,
        expected_mission_id=proj.mission_id,
        expected_tenant_id="v1-tenant-001",
    )
    assert restored == envelope

    # Tampered bytes are rejected (fail-closed)
    tampered = bytearray(raw)
    tampered[0] = tampered[0] ^ 0x01  # flip a bit
    with pytest.raises(BridgeValidationError):
        receive_v1_envelope(bytes(tampered))


def test_v1_result_build_and_receive():
    """build_v1_result → serialize → receive_v1_result round-trips."""
    proj = _v1_projection()
    envelope = build_v1_envelope(
        projection=proj,
        authority_decision=AuthorityDecision.ALLOW.value,
        execution_id="v1-exec-002",
        nonce="v1-nonce-002",
        tenant_id="v1-tenant-001",
        actor_id="v1-actor-001",
        capability_id="named_agents",
        payload=_v1_payload(),
    )
    result_data = {"status": "COMPLETE", "output": "ok"}
    evidence = {"receipt": "ev-002", "proof": "abc123"}
    result = build_v1_result(envelope, "COMPLETE", result_data, evidence)

    assert isinstance(result, BridgeResultV1)
    assert result.schema_version == BRIDGE_CONTRACT_VERSION
    assert result.mission_id == envelope.mission_id
    assert result.execution_id == envelope.execution_id
    assert result.nonce == envelope.nonce
    assert result.authority_delta == 0
    assert result.side_effect_count == 0
    assert result.evidence_sha256 == compute_evidence_sha256(evidence)

    # Serialize → receive round-trip
    raw = serialize_result_v1(result)
    restored = receive_v1_result(raw, expected_envelope=envelope)
    assert restored == result

    # Tampered result is rejected
    tampered = bytearray(raw)
    tampered[-1] = tampered[-1] ^ 0x01
    with pytest.raises(BridgeValidationError):
        receive_v1_result(bytes(tampered))


def test_v1_bridge_execute_allow():
    """execute_via_bridge with ALLOW produces TRANSPORT_OK + COMPLETE result."""
    proj = _v1_projection()
    payload = _v1_payload()
    envelope = build_v1_envelope(
        projection=proj,
        authority_decision=AuthorityDecision.ALLOW.value,
        execution_id="v1-exec-003",
        nonce="v1-nonce-003",
        tenant_id="v1-tenant-001",
        actor_id="v1-actor-001",
        capability_id="named_agents",
        payload=payload,
    )
    raw = serialize_envelope_v1(envelope)
    tracker = InMemoryNonceTracker()
    outcome = execute_via_bridge(raw, nonce_tracker=tracker)

    assert outcome.transport_status == BridgeTransportStatus.TRANSPORT_OK
    assert outcome.result is not None
    assert outcome.result.status == "COMPLETE"
    assert outcome.result.authority_delta == 0
    assert outcome.result.side_effect_count == 0
    # Evidence hash binding
    assert outcome.result.evidence_sha256 == compute_evidence_sha256(
        outcome.result.evidence
    )
    # Identity binding to envelope
    assert outcome.result.mission_id == envelope.mission_id
    assert outcome.result.execution_id == envelope.execution_id
    assert outcome.result.nonce == envelope.nonce


def test_v1_bridge_execute_denied():
    """execute_via_bridge with DENY returns TRANSPORT_DENIED, no result."""
    proj = _v1_projection()
    envelope = build_v1_envelope(
        projection=proj,
        authority_decision=AuthorityDecision.DENY.value,
        execution_id="v1-exec-004",
        nonce="v1-nonce-004",
        tenant_id="v1-tenant-001",
        actor_id="v1-actor-001",
        capability_id="named_agents",
        payload=_v1_payload(),
    )
    raw = serialize_envelope_v1(envelope)
    tracker = InMemoryNonceTracker()
    outcome = execute_via_bridge(raw, nonce_tracker=tracker)

    assert outcome.transport_status == BridgeTransportStatus.TRANSPORT_DENIED
    assert outcome.result is None
    assert "DENY" in outcome.reason


def test_v1_bridge_transport_vs_mission_success():
    """BRIDGE_TRANSPORT_SUCCESS != MISSION_SUCCESS.

    Transport can succeed (TRANSPORT_OK) while the mission result reports
    a non-COMPLETE status.  We demonstrate this by building a result with
    status='FAILED' through build_v1_result and verifying the outcome
    object can carry a non-COMPLETE mission status under TRANSPORT_OK.
    """
    proj = _v1_projection()
    envelope = build_v1_envelope(
        projection=proj,
        authority_decision=AuthorityDecision.ALLOW.value,
        execution_id="v1-exec-005",
        nonce="v1-nonce-005",
        tenant_id="v1-tenant-001",
        actor_id="v1-actor-001",
        capability_id="named_agents",
        payload=_v1_payload(),
    )
    # Build a result with a FAILED mission status (transport OK, mission failed)
    failed_result = build_v1_result(
        envelope,
        status="FAILED",
        result={"error": "mission failed"},
        evidence={"failure_proof": "0xdeadbeef"},
    )
    outcome = BridgeExecutionOutcome(
        transport_status=BridgeTransportStatus.TRANSPORT_OK,
        result=failed_result,
        reason="transport ok but mission failed",
    )
    assert outcome.transport_status == BridgeTransportStatus.TRANSPORT_OK
    assert outcome.result is not None
    assert outcome.result.status == "FAILED"
    # The key assertion: transport OK ≠ mission COMPLETE
    assert outcome.transport_status == BridgeTransportStatus.TRANSPORT_OK
    assert outcome.result.status != "COMPLETE"


def test_v1_unverified_not_complete():
    """MISSION_SUCCESS_WITHOUT_REQUIRED_EVIDENCE = UNVERIFIED; UNVERIFIED != COMPLETE.

    A result with status='UNVERIFIED' is a valid V1 result but must not be
    confused with COMPLETE.  This demonstrates the design rule that missing
    required evidence yields UNVERIFIED, which is distinct from COMPLETE.
    """
    proj = _v1_projection()
    envelope = build_v1_envelope(
        projection=proj,
        authority_decision=AuthorityDecision.ALLOW.value,
        execution_id="v1-exec-006",
        nonce="v1-nonce-006",
        tenant_id="v1-tenant-001",
        actor_id="v1-actor-001",
        capability_id="named_agents",
        payload=_v1_payload(),
    )
    # UNVERIFIED result — evidence present but status explicitly UNVERIFIED
    unverified_result = build_v1_result(
        envelope,
        status="UNVERIFIED",
        result={"reason": "required evidence not provided"},
        evidence={"available": False, "required": "external_attestation"},
    )
    assert unverified_result.status == "UNVERIFIED"
    assert unverified_result.status != "COMPLETE"
    # Round-trip preserves UNVERIFIED
    raw = serialize_result_v1(unverified_result)
    restored = receive_v1_result(raw, expected_envelope=envelope)
    assert restored.status == "UNVERIFIED"
    assert restored.status != "COMPLETE"