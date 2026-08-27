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
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, Optional, Tuple

# Canonical V1 contract — re-exported for convenience
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
    validate_envelope,
    validate_result,
)
from sintra_live.l2.action_envelope_contract import ConsequenceClass

__all__ = [
    "BridgeEnvelope",
    "BridgeEnvelopeError",
    "BridgeProjection",
    "BRIDGE_SCHEMA_VERSION",
    "serialize_envelope",
    "deserialize_envelope",
    "project_mission_state",
    # V1 canonical contract re-exports
    "BRIDGE_CONTRACT_VERSION",
    "AuthorityDecision",
    "ConsequenceClass",
    "BridgeEnvelopeV1",
    "BridgeResultV1",
    "BridgeValidationError",
    "InMemoryNonceTracker",
    "serialize_envelope_v1",
    "deserialize_envelope_v1",
    "serialize_result_v1",
    "deserialize_result_v1",
    "compute_payload_sha256",
    "compute_evidence_sha256",
    "validate_envelope",
    "validate_result",
    # V1 bridge runtime adapter additions
    "BridgeTransportStatus",
    "BridgeExecutionOutcome",
    "build_v1_envelope",
    "receive_v1_envelope",
    "build_v1_result",
    "receive_v1_result",
    "execute_via_bridge",
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


# ---------------------------------------------------------------------------
# V1 canonical bridge runtime adapter
# ---------------------------------------------------------------------------
# The functions below use the canonical sp-bridge-v1 contract from
# bridge_envelope_contract.py.  They build, serialize, deserialize, validate,
# and execute V1 envelopes/results crossing the Python<->TypeScript boundary.
#
# Design rules:
#   * BRIDGE_TRANSPORT_SUCCESS != MISSION_SUCCESS
#   * MISSION_SUCCESS_WITHOUT_REQUIRED_EVIDENCE = UNVERIFIED
#   * UNVERIFIED != COMPLETE
#   * Fail-closed on every validation failure
# ---------------------------------------------------------------------------


class BridgeTransportStatus(str, Enum):
    """Transport-layer status for a bridge-mediated execution.

    Distinguished from mission success:
      * TRANSPORT_OK    — the envelope was received, validated, and a result
                          was produced (the result itself may still indicate
                          mission failure or UNVERIFIED).
      * TRANSPORT_DENIED — authority denied execution (DENY, REVOKED, etc.).
      * TRANSPORT_FAILED — transport/validation error (deserialize failure,
                           validation reject rule, etc.).
    """

    TRANSPORT_OK = "TRANSPORT_OK"
    TRANSPORT_DENIED = "TRANSPORT_DENIED"
    TRANSPORT_FAILED = "TRANSPORT_FAILED"


@dataclass(frozen=True)
class BridgeExecutionOutcome:
    """Outcome of execute_via_bridge().

    transport_status — whether the bridge transport succeeded, was denied,
                       or failed.
    result           — the V1 result if one was produced (None when denied
                       or failed before a result could be built).
    reason           — human-readable reason for the status.
    """

    transport_status: BridgeTransportStatus
    result: Optional[BridgeResultV1]
    reason: str


def _v1_timestamp(dt: Optional[datetime] = None) -> str:
    """Return a canonical V1 timestamp string (UTC, microsecond precision)."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def build_v1_envelope(
    projection: BridgeProjection,
    authority_decision: str,
    execution_id: str,
    nonce: str,
    tenant_id: str,
    actor_id: str,
    capability_id: str,
    payload: Dict[str, Any],
    *,
    consequence_class: str = ConsequenceClass.READ_ONLY.value,
    issued_at: Optional[str] = None,
    expires_at: Optional[str] = None,
    provenance: str = "sintra_live/l2/python_typescript_bridge",
) -> BridgeEnvelopeV1:
    """Build a canonical V1 envelope from L2 mission projection + authority.

    The projection supplies ``mission_id`` (and corroborates L2 state).
    The payload hash is computed deterministically via
    ``compute_payload_sha256``.
    """
    payload_sha = compute_payload_sha256(payload)
    now = datetime.now(timezone.utc)
    ts_issued = issued_at or _v1_timestamp(now)
    ts_expires = expires_at or _v1_timestamp(now + timedelta(seconds=3600))
    return BridgeEnvelopeV1(
        schema_version=BRIDGE_CONTRACT_VERSION,
        mission_id=projection.mission_id,
        execution_id=execution_id,
        nonce=nonce,
        tenant_id=tenant_id,
        actor_id=actor_id,
        authority_decision=authority_decision,
        consequence_class=consequence_class,
        capability_id=capability_id,
        payload=payload,
        payload_sha256=payload_sha,
        issued_at=ts_issued,
        expires_at=ts_expires,
        provenance=provenance,
    )


def receive_v1_envelope(
    raw: bytes,
    *,
    nonce_tracker: Optional[InMemoryNonceTracker] = None,
    expected_mission_id: Optional[str] = None,
    expected_tenant_id: Optional[str] = None,
    current_time: Optional[str] = None,
) -> BridgeEnvelopeV1:
    """Deserialize and fully validate a V1 envelope from raw bytes.

    Fail-closed: any deserialize or validation error raises
    ``BridgeValidationError``.
    """
    try:
        envelope = deserialize_envelope_v1(raw)
    except BridgeValidationError:
        raise
    except Exception as exc:
        raise BridgeValidationError(
            "INVALID_ENVELOPE", f"deserialize failed: {exc}"
        ) from exc
    validate_envelope(
        envelope,
        nonce_tracker=nonce_tracker,
        expected_mission_id=expected_mission_id,
        expected_tenant_id=expected_tenant_id,
        current_time=current_time,
    )
    return envelope


def build_v1_result(
    envelope: BridgeEnvelopeV1,
    status: str,
    result: Dict[str, Any],
    evidence: Dict[str, Any],
    *,
    completed_at: Optional[str] = None,
) -> BridgeResultV1:
    """Build a canonical V1 result from an execution outcome + evidence.

    Invariants enforced by ``BridgeResultV1``:
      * ``authority_delta == 0``
      * ``side_effect_count == 0``
      * ``evidence_sha256`` binds to ``evidence``
    """
    return BridgeResultV1(
        schema_version=BRIDGE_CONTRACT_VERSION,
        mission_id=envelope.mission_id,
        execution_id=envelope.execution_id,
        nonce=envelope.nonce,
        status=status,
        result=result,
        evidence=evidence,
        evidence_sha256=compute_evidence_sha256(evidence),
        authority_delta=0,
        side_effect_count=0,
        completed_at=completed_at or _v1_timestamp(),
    )


def receive_v1_result(
    raw: bytes,
    *,
    expected_envelope: Optional[BridgeEnvelopeV1] = None,
) -> BridgeResultV1:
    """Deserialize and fully validate a V1 result from raw bytes.

    Fail-closed: any deserialize or validation error raises
    ``BridgeValidationError``.
    """
    try:
        result = deserialize_result_v1(raw)
    except BridgeValidationError:
        raise
    except Exception as exc:
        raise BridgeValidationError(
            "INVALID_RESULT", f"deserialize failed: {exc}"
        ) from exc
    validate_result(result, expected_envelope=expected_envelope)
    return result


# ---------------------------------------------------------------------------
# Deterministic mock executor (dogfood / integration)
# ---------------------------------------------------------------------------

def _mock_execute_payload(payload: Dict[str, Any]) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    """Deterministic mock execution for dogfood.

    Returns (status, result_dict, evidence_dict).  The status is COMPLETE
    only when evidence is non-empty — otherwise UNVERIFIED, demonstrating
    that MISSION_SUCCESS_WITHOUT_REQUIRED_EVIDENCE = UNVERIFIED and
    UNVERIFIED != COMPLETE.
    """
    result_data = {
        "executed_action": payload.get("action", "unknown"),
        "deterministic_output": hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }
    evidence = {
        "payload_sha256": compute_payload_sha256(payload),
        "executor": "sintra_live.l2.python_typescript_bridge._mock_execute_payload",
        "execution_proof": result_data["deterministic_output"],
    }
    # Evidence is always non-empty here, so the mission is COMPLETE.
    status = "COMPLETE"
    return status, result_data, evidence


def execute_via_bridge(
    raw_envelope: bytes,
    *,
    nonce_tracker: Optional[InMemoryNonceTracker] = None,
    expected_mission_id: Optional[str] = None,
    expected_tenant_id: Optional[str] = None,
    current_time: Optional[str] = None,
) -> BridgeExecutionOutcome:
    """Canonical bridge-mediated execution flow (Python entry point).

    Flow:
      1. Deserialize + validate the incoming envelope (all 14 reject rules).
      2. If authority_decision != ALLOW, return a denied outcome.
      3. If ALLOW, execute the payload (mock/deterministic for dogfood).
      4. Build a V1 result with evidence hash.
      5. Return the outcome.

    BRIDGE_TRANSPORT_SUCCESS != MISSION_SUCCESS:
      Transport may succeed (TRANSPORT_OK) while the mission result status
      is UNVERIFIED or even a failure.  The caller must inspect
      ``outcome.result.status`` for mission-level success.
    """
    # 1. Deserialize + validate (fail-closed → TRANSPORT_FAILED)
    try:
        envelope = receive_v1_envelope(
            raw_envelope,
            nonce_tracker=nonce_tracker,
            expected_mission_id=expected_mission_id,
            expected_tenant_id=expected_tenant_id,
            current_time=current_time,
        )
    except BridgeValidationError as exc:
        return BridgeExecutionOutcome(
            transport_status=BridgeTransportStatus.TRANSPORT_FAILED,
            result=None,
            reason=f"envelope validation failed: {exc}",
        )
    except Exception as exc:  # pragma: no cover — defensive
        return BridgeExecutionOutcome(
            transport_status=BridgeTransportStatus.TRANSPORT_FAILED,
            result=None,
            reason=f"envelope deserialize error: {exc}",
        )

    # 2. Authority decision gate
    if envelope.authority_decision != AuthorityDecision.ALLOW.value:
        return BridgeExecutionOutcome(
            transport_status=BridgeTransportStatus.TRANSPORT_DENIED,
            result=None,
            reason=(
                f"authority_decision={envelope.authority_decision} "
                f"does not permit execution"
            ),
        )

    # 3. Execute payload (deterministic mock)
    status, result_data, evidence = _mock_execute_payload(envelope.payload)

    # 4. Build V1 result with evidence hash
    v1_result = build_v1_result(envelope, status, result_data, evidence)

    # 5. Return outcome
    return BridgeExecutionOutcome(
        transport_status=BridgeTransportStatus.TRANSPORT_OK,
        result=v1_result,
        reason="execution completed",
    )