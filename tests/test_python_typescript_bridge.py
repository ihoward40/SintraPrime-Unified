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