"""Canonical governed Python↔TypeScript runtime bridge adapter.

This module provides the Python side of a deterministic, versioned JSON
envelope that carries governed mission-control state across the runtime
boundary between the Python L2 backend and the TypeScript web frontend.

Design rules (P6 bridge):
  * The L2 store is the **only** state machine.
  * This adapter owns no transition logic — it projects read-only state.
  * Every envelope carries an integrity hash and authority_delta = 0.
  * Provider invocation, live external calls, and secrets are prohibited.
  * Replay/stale/tamper detection is fail-closed.
  * The wire schema is versioned; mismatches are denied.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

__all__ = [
    "BridgeEnvelope",
    "BridgeEnvelopeError",
    "BridgeProjection",
    "BRIDGE_SCHEMA_VERSION",
    "serialize_envelope",
    "deserialize_envelope",
    "project_mission_state",
]

BRIDGE_SCHEMA_VERSION = 1


class BridgeEnvelopeError(RuntimeError):
    """Raised when a bridge envelope fails validation."""


@dataclass(frozen=True)
class BridgeProjection:
    """Read-only projection of L2 mission state for the TypeScript side."""

    mission_id: str
    aggregate_version: int
    aggregate_sha256: str
    current_state: str
    authority_delta: int
    side_effects: int
    canonical_state_source: str = "sintra_live/l2"


@dataclass(frozen=True)
class BridgeEnvelope:
    """Versioned JSON envelope crossing the Python↔TypeScript boundary."""

    schema_version: int
    mission_id: str
    aggregate_version: int
    aggregate_sha256: str
    current_state: str
    authority_delta: int
    side_effects: int
    canonical_state_source: str
    envelope_sha256: str
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> bytes:
        body = {
            "schema_version": self.schema_version,
            "mission_id": self.mission_id,
            "aggregate_version": self.aggregate_version,
            "aggregate_sha256": self.aggregate_sha256,
            "current_state": self.current_state,
            "authority_delta": self.authority_delta,
            "side_effects": self.side_effects,
            "canonical_state_source": self.canonical_state_source,
            "envelope_sha256": self.envelope_sha256,
            "payload": self.payload,
        }
        return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()

    @staticmethod
    def compute_hash(body_without_hash: Dict[str, Any]) -> str:
        raw = json.dumps(body_without_hash, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()


def serialize_envelope(projection: BridgeProjection, payload: Optional[Dict[str, Any]] = None) -> BridgeEnvelope:
    """Build a sealed envelope from a projection and optional payload."""
    body = {
        "schema_version": BRIDGE_SCHEMA_VERSION,
        "mission_id": projection.mission_id,
        "aggregate_version": projection.aggregate_version,
        "aggregate_sha256": projection.aggregate_sha256,
        "current_state": projection.current_state,
        "authority_delta": projection.authority_delta,
        "side_effects": projection.side_effects,
        "canonical_state_source": projection.canonical_state_source,
        "payload": payload or {},
    }
    envelope_sha256 = BridgeEnvelope.compute_hash(body)
    return BridgeEnvelope(
        schema_version=BRIDGE_SCHEMA_VERSION,
        mission_id=projection.mission_id,
        aggregate_version=projection.aggregate_version,
        aggregate_sha256=projection.aggregate_sha256,
        current_state=projection.current_state,
        authority_delta=projection.authority_delta,
        side_effects=projection.side_effects,
        canonical_state_source=projection.canonical_state_source,
        envelope_sha256=envelope_sha256,
        payload=payload or {},
    )


def deserialize_envelope(raw: bytes) -> BridgeEnvelope:
    """Parse and validate a raw JSON envelope.  Fail-closed on all violations."""
    try:
        body = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BridgeEnvelopeError(f"envelope is not valid JSON: {exc}") from exc

    if not isinstance(body, dict):
        raise BridgeEnvelopeError("envelope body must be a JSON object")

    # Schema version check
    sv = body.get("schema_version")
    if sv != BRIDGE_SCHEMA_VERSION:
        raise BridgeEnvelopeError(
            f"schema_version mismatch: expected {BRIDGE_SCHEMA_VERSION}, got {sv}"
        )

    # Required fields
    required: Tuple[str, ...] = (
        "mission_id", "aggregate_version", "aggregate_sha256",
        "current_state", "authority_delta", "side_effects",
        "canonical_state_source", "envelope_sha256",
    )
    for key in required:
        if key not in body:
            raise BridgeEnvelopeError(f"missing required field: {key}")

    # Authority delta must be zero
    if body["authority_delta"] != 0:
        raise BridgeEnvelopeError(
            f"authority_delta must be zero, got {body['authority_delta']}"
        )

    # Side effects must be zero
    if body["side_effects"] != 0:
        raise BridgeEnvelopeError(
            f"side_effects must be zero, got {body['side_effects']}"
        )

    # Canonical source must be L2
    if body["canonical_state_source"] != "sintra_live/l2":
        raise BridgeEnvelopeError(
            f"canonical_state_source must be sintra_live/l2, got {body['canonical_state_source']}"
        )

    # Integrity hash verification
    envelope_sha = body["envelope_sha256"]
    body_for_hash = {k: v for k, v in body.items() if k != "envelope_sha256"}
    computed = BridgeEnvelope.compute_hash(body_for_hash)
    if computed != envelope_sha:
        raise BridgeEnvelopeError(
            f"integrity hash mismatch: expected {envelope_sha}, computed {computed}"
        )

    return BridgeEnvelope(
        schema_version=body["schema_version"],
        mission_id=body["mission_id"],
        aggregate_version=body["aggregate_version"],
        aggregate_sha256=body["aggregate_sha256"],
        current_state=body["current_state"],
        authority_delta=body["authority_delta"],
        side_effects=body["side_effects"],
        canonical_state_source=body["canonical_state_source"],
        envelope_sha256=envelope_sha,
        payload=body.get("payload", {}),
    )


def project_mission_state(aggregate: Any) -> BridgeProjection:
    """Project read-only L2 mission aggregate state for the bridge."""
    identity = getattr(aggregate, "identity", None)
    mission_id = getattr(identity, "mission_id", "")
    version = getattr(aggregate, "version", None)
    aggregate_sha256 = getattr(aggregate, "aggregate_sha256", "")
    current_state = getattr(aggregate, "current_state", None)
    current_state_value = getattr(current_state, "value", str(current_state))

    if not mission_id or not isinstance(version, int) or not aggregate_sha256:
        raise BridgeEnvelopeError("canonical aggregate identity is incomplete")

    return BridgeProjection(
        mission_id=mission_id,
        aggregate_version=version,
        aggregate_sha256=aggregate_sha256,
        current_state=current_state_value,
        authority_delta=0,
        side_effects=0,
    )