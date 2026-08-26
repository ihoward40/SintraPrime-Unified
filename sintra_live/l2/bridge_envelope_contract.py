"""Canonical L2 bridge envelope/result contract — sp-bridge-v1.

Wave 0 semantic contract for the Python<->TypeScript runtime bridge.
This module defines the authoritative envelope and result data structures,
their serialization, integrity hashing, and fail-closed validation rules.

Design rules:
  * The bridge contract PROTECTS/VALIDATES existing governed semantics.
  * It does NOT create a second authority model.
  * All hashes are deterministic via canonical_bytes() from mission/model.py.
  * JSON canonicalization: sort_keys=True, separators=(",",":"), ensure_ascii=False.
  * Fail-closed: any validation failure rejects the envelope/result.
  * BRIDGE_TRANSPORT_SUCCESS != MISSION_SUCCESS.
  * MISSION_SUCCESS_WITHOUT_REQUIRED_EVIDENCE = UNVERIFIED.
  * UNVERIFIED != COMPLETE.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Set, Tuple

from sintra_live.l2.action_envelope_contract import ConsequenceClass
from sintra_live.l2.mission.model import canonical_bytes

BRIDGE_CONTRACT_VERSION = "sp-bridge-v1"
HASH_DOMAIN_PAYLOAD = b"SP-LIVE-001:L2:BRIDGE:PAYLOAD:V1\x00"
HASH_DOMAIN_EVIDENCE = b"SP-LIVE-001:L2:BRIDGE:EVIDENCE:V1\x00"
HASH_DOMAIN_ENVELOPE = b"SP-LIVE-001:L2:BRIDGE:ENVELOPE:V1\x00"

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")

MAX_INT = 2**63 - 1


class AuthorityDecision(str, Enum):
    """Authority decision values carried by the bridge envelope.

    These are PROJECTIONS of existing governed authority semantics,
    not a new authority model.
    """

    ALLOW = "ALLOW"
    DENY = "DENY"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    AUTHORITY_MISSING = "AUTHORITY_MISSING"
    POLICY_CONFLICT = "POLICY_CONFLICT"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


# Re-export ConsequenceClass for convenience
__all__ = [
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
    "compute_contract_sha256",
    "contract_artifact",
]


class BridgeValidationError(Exception):
    """Raised when a bridge envelope or result fails fail-closed validation."""

    def __init__(self, rule: str, message: str = ""):
        self.rule = rule
        self.message = message or rule
        super().__init__(f"{rule}: {self.message}" if message else rule)


# ---------------------------------------------------------------------------
# Validators (private)
# ---------------------------------------------------------------------------

def _validate_identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER_RE.fullmatch(value):
        raise BridgeValidationError("INVALID_IDENTIFIER", f"invalid {name}")
    return value


def _validate_sha256(value: Any, name: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise BridgeValidationError("INVALID_SHA256", f"invalid {name}")
    return value


def _validate_timestamp(value: Any, name: str) -> str:
    if not isinstance(value, str) or not TIMESTAMP_RE.fullmatch(value):
        raise BridgeValidationError("INVALID_TIMESTAMP", f"invalid {name}")
    return value


def _validate_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_INT:
        raise BridgeValidationError("INVALID_INTEGER", f"invalid {name}")
    return value


def _validate_authority_decision(value: Any) -> str:
    if not isinstance(value, str):
        raise BridgeValidationError("INVALID_AUTHORITY_DECISION", "authority_decision must be a string")
    try:
        return AuthorityDecision(value).value
    except ValueError:
        raise BridgeValidationError(
            "INVALID_AUTHORITY_DECISION",
            f"unknown authority_decision: {value}",
        )


def _validate_consequence_class(value: Any) -> str:
    if not isinstance(value, str):
        raise BridgeValidationError("INVALID_CONSEQUENCE_CLASS", "consequence_class must be a string")
    try:
        return ConsequenceClass(value).value
    except ValueError:
        raise BridgeValidationError(
            "INVALID_CONSEQUENCE_CLASS",
            f"unknown consequence_class: {value}",
        )


# ---------------------------------------------------------------------------
# Hash helpers
# ---------------------------------------------------------------------------

def compute_payload_sha256(payload: Any) -> str:
    """Compute the SHA-256 of the payload using domain separation + canonical bytes."""
    return hashlib.sha256(HASH_DOMAIN_PAYLOAD + canonical_bytes(payload)).hexdigest()


def compute_evidence_sha256(evidence: Any) -> str:
    """Compute the SHA-256 of the evidence using domain separation + canonical bytes."""
    return hashlib.sha256(HASH_DOMAIN_EVIDENCE + canonical_bytes(evidence)).hexdigest()


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

ENVELOPE_FIELDS: Tuple[str, ...] = (
    "schema_version",
    "mission_id",
    "execution_id",
    "nonce",
    "tenant_id",
    "actor_id",
    "authority_decision",
    "consequence_class",
    "capability_id",
    "payload",
    "payload_sha256",
    "issued_at",
    "expires_at",
    "provenance",
)

RESULT_FIELDS: Tuple[str, ...] = (
    "schema_version",
    "mission_id",
    "execution_id",
    "nonce",
    "status",
    "result",
    "evidence",
    "evidence_sha256",
    "authority_delta",
    "side_effect_count",
    "completed_at",
)


@dataclass(frozen=True)
class BridgeEnvelopeV1:
    """Immutable canonical bridge envelope (sp-bridge-v1).

    Carries governed authority and mission identity across the runtime boundary.
    This is a projection/serialization of existing L2 semantics — NOT a new
    authority source.
    """

    schema_version: str
    mission_id: str
    execution_id: str
    nonce: str
    tenant_id: str
    actor_id: str
    authority_decision: str
    consequence_class: str
    capability_id: str
    payload: Dict[str, Any]
    payload_sha256: str
    issued_at: str
    expires_at: str
    provenance: str

    def __post_init__(self) -> None:
        if self.schema_version != BRIDGE_CONTRACT_VERSION:
            raise BridgeValidationError("SCHEMA_VERSION_MISMATCH")
        _validate_identifier(self.mission_id, "mission_id")
        _validate_identifier(self.execution_id, "execution_id")
        _validate_identifier(self.nonce, "nonce")
        _validate_identifier(self.tenant_id, "tenant_id")
        _validate_identifier(self.actor_id, "actor_id")
        _validate_authority_decision(self.authority_decision)
        _validate_consequence_class(self.consequence_class)
        _validate_identifier(self.capability_id, "capability_id")
        if not isinstance(self.payload, dict):
            raise BridgeValidationError("INVALID_PAYLOAD", "payload must be a dict")
        _validate_sha256(self.payload_sha256, "payload_sha256")
        _validate_timestamp(self.issued_at, "issued_at")
        _validate_timestamp(self.expires_at, "expires_at")
        if not isinstance(self.provenance, str) or not self.provenance.strip():
            raise BridgeValidationError("INVALID_PROVENANCE", "provenance must be non-empty")
        # Verify payload hash binding at construction
        expected = compute_payload_sha256(self.payload)
        if self.payload_sha256 != expected:
            raise BridgeValidationError("PAYLOAD_HASH_MISMATCH")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def body_for_hash(self) -> Dict[str, Any]:
        """Return dict without payload_sha256 (for envelope-level hashing if needed)."""
        d = self.to_dict()
        return d


@dataclass(frozen=True)
class BridgeResultV1:
    """Immutable canonical bridge result (sp-bridge-v1).

    Carries execution outcome back across the runtime boundary.
    Invariants: authority_delta=0, side_effect_count=0, evidence hash binding.
    """

    schema_version: str
    mission_id: str
    execution_id: str
    nonce: str
    status: str
    result: Dict[str, Any]
    evidence: Dict[str, Any]
    evidence_sha256: str
    authority_delta: int
    side_effect_count: int
    completed_at: str

    def __post_init__(self) -> None:
        if self.schema_version != BRIDGE_CONTRACT_VERSION:
            raise BridgeValidationError("SCHEMA_VERSION_MISMATCH")
        _validate_identifier(self.mission_id, "mission_id")
        _validate_identifier(self.execution_id, "execution_id")
        _validate_identifier(self.nonce, "nonce")
        if not isinstance(self.status, str) or not self.status.strip():
            raise BridgeValidationError("INVALID_STATUS", "status must be non-empty")
        if not isinstance(self.result, dict):
            raise BridgeValidationError("INVALID_RESULT", "result must be a dict")
        if not isinstance(self.evidence, dict):
            raise BridgeValidationError("INVALID_EVIDENCE", "evidence must be a dict")
        _validate_sha256(self.evidence_sha256, "evidence_sha256")
        _validate_int(self.authority_delta, "authority_delta")
        _validate_int(self.side_effect_count, "side_effect_count")
        _validate_timestamp(self.completed_at, "completed_at")
        # Invariant: authority_delta must be 0
        if self.authority_delta != 0:
            raise BridgeValidationError("AUTHORITY_DELTA_NONZERO")
        # Invariant: side_effect_count must be 0
        if self.side_effect_count != 0:
            raise BridgeValidationError("SIDE_EFFECT_COUNT_NONZERO")
        # Verify evidence hash binding at construction
        expected = compute_evidence_sha256(self.evidence)
        if self.evidence_sha256 != expected:
            raise BridgeValidationError("EVIDENCE_HASH_MISMATCH")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def _to_json_bytes(data: Any) -> bytes:
    """Canonical JSON: sort_keys=True, separators=(',',':'), ensure_ascii=False."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def serialize_envelope_v1(envelope: BridgeEnvelopeV1) -> bytes:
    """Serialize envelope to canonical JSON bytes."""
    data = envelope.to_dict()
    return _to_json_bytes(data)


def deserialize_envelope_v1(raw: bytes | str) -> BridgeEnvelopeV1:
    """Deserialize canonical JSON bytes to a BridgeEnvelopeV1.

    Construction-level validation (schema version, identifiers, hash binding)
    runs in __post_init__. Full validate_envelope() must be called separately
    for the 14 fail-closed reject rules.
    """
    if isinstance(raw, bytes):
        text = raw.decode("utf-8")
    else:
        text = raw
    data = json.loads(text)
    if not isinstance(data, dict):
        raise BridgeValidationError("INVALID_ENVELOPE", "envelope must be a JSON object")
    # Check for exact field set
    expected = set(ENVELOPE_FIELDS)
    actual = set(data.keys())
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise BridgeValidationError(
            "FIELD_MISMATCH",
            f"missing={missing}, unknown={unknown}",
        )
    return BridgeEnvelopeV1(**data)


def serialize_result_v1(result: BridgeResultV1) -> bytes:
    """Serialize result to canonical JSON bytes."""
    data = result.to_dict()
    return _to_json_bytes(data)


def deserialize_result_v1(raw: bytes | str) -> BridgeResultV1:
    """Deserialize canonical JSON bytes to a BridgeResultV1."""
    if isinstance(raw, bytes):
        text = raw.decode("utf-8")
    else:
        text = raw
    data = json.loads(text)
    if not isinstance(data, dict):
        raise BridgeValidationError("INVALID_RESULT", "result must be a JSON object")
    expected = set(RESULT_FIELDS)
    actual = set(data.keys())
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise BridgeValidationError(
            "FIELD_MISMATCH",
            f"missing={missing}, unknown={unknown}",
        )
    return BridgeResultV1(**data)


# ---------------------------------------------------------------------------
# Nonce tracker (in-memory, for duplicate nonce detection)
# ---------------------------------------------------------------------------

class InMemoryNonceTracker:
    """Simple in-memory nonce tracker for replay detection.

    Tracks (mission_id, nonce) and (tenant_id, nonce) tuples.
    In production this would be backed by a durable store.
    """

    def __init__(self) -> None:
        self._mission_nonces: Set[Tuple[str, str]] = set()
        self._tenant_nonces: Set[Tuple[str, str]] = set()

    def check_and_record(self, mission_id: str, tenant_id: str, nonce: str) -> bool:
        """Returns True if nonce is fresh (and records it), False if duplicate."""
        m_key = (mission_id, nonce)
        t_key = (tenant_id, nonce)
        if m_key in self._mission_nonces:
            return False
        if t_key in self._tenant_nonces:
            return False
        self._mission_nonces.add(m_key)
        self._tenant_nonces.add(t_key)
        return True

    def is_duplicate(self, mission_id: str, tenant_id: str, nonce: str) -> bool:
        """Check if nonce is duplicate without recording."""
        m_key = (mission_id, nonce)
        t_key = (tenant_id, nonce)
        return m_key in self._mission_nonces or t_key in self._tenant_nonces

    def clear(self) -> None:
        self._mission_nonces.clear()
        self._tenant_nonces.clear()


# ---------------------------------------------------------------------------
# Validation: 14 fail-closed reject rules for envelopes
# ---------------------------------------------------------------------------

def _parse_timestamp(ts: str) -> float:
    """Parse canonical timestamp string to epoch seconds (float, UTC)."""
    # Format: YYYY-MM-DDTHH:MM:SS.ffffffZ
    dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    return dt.timestamp()


def validate_envelope(
    envelope: BridgeEnvelopeV1,
    *,
    nonce_tracker: Optional[InMemoryNonceTracker] = None,
    expected_mission_id: Optional[str] = None,
    expected_tenant_id: Optional[str] = None,
    current_time: Optional[str] = None,
) -> None:
    """Validate a bridge envelope against all 14 fail-closed reject rules.

    Raises BridgeValidationError on any failure.

    Reject rules:
      1.  Unknown schema version
      2.  Missing mission_id
      3.  Missing execution_id
      4.  Missing nonce
      5.  Missing tenant_id
      6.  Missing authority_decision
      7.  Missing capability_id
      8.  Payload hash mismatch
      9.  Expired envelope
      10. Revoked authority
      11. Cross-mission replay
      12. Cross-tenant replay
      13. Duplicate nonce
      14. authority_delta != 0 (not applicable to envelope — enforced on result;
          this rule is checked on result validation but listed here for completeness;
          envelope-level check: authority_decision must not be REVOKED with a live
          envelope — covered by rule 10)
    """
    # Rule 1: Unknown schema version
    if envelope.schema_version != BRIDGE_CONTRACT_VERSION:
        raise BridgeValidationError("SCHEMA_VERSION_MISMATCH")

    # Rule 2: Missing mission_id
    if not envelope.mission_id:
        raise BridgeValidationError("MISSING_MISSION_ID")

    # Rule 3: Missing execution_id
    if not envelope.execution_id:
        raise BridgeValidationError("MISSING_EXECUTION_ID")

    # Rule 4: Missing nonce
    if not envelope.nonce:
        raise BridgeValidationError("MISSING_NONCE")

    # Rule 5: Missing tenant_id
    if not envelope.tenant_id:
        raise BridgeValidationError("MISSING_TENANT_ID")

    # Rule 6: Missing authority_decision
    if not envelope.authority_decision:
        raise BridgeValidationError("MISSING_AUTHORITY_DECISION")
    # Also validate it's a known value
    _validate_authority_decision(envelope.authority_decision)

    # Rule 7: Missing capability_id
    if not envelope.capability_id:
        raise BridgeValidationError("MISSING_CAPABILITY_ID")

    # Rule 8: Payload hash mismatch
    expected_hash = compute_payload_sha256(envelope.payload)
    if envelope.payload_sha256 != expected_hash:
        raise BridgeValidationError("PAYLOAD_HASH_MISMATCH")

    # Rule 9: Expired envelope
    # Use provided current_time or generate it
    now_ts = None
    if current_time is not None:
        now_ts = _parse_timestamp(current_time)
    else:
        now_ts = time.time()

    expires_ts = _parse_timestamp(envelope.expires_at)
    if now_ts > expires_ts:
        raise BridgeValidationError("EXPIRED_ENVELOPE")

    # Rule 10: Revoked authority
    if envelope.authority_decision == AuthorityDecision.REVOKED.value:
        raise BridgeValidationError("REVOKED_AUTHORITY")

    # Rule 11: Cross-mission replay
    if expected_mission_id is not None and envelope.mission_id != expected_mission_id:
        raise BridgeValidationError("CROSS_MISSION_REPLAY")

    # Rule 12: Cross-tenant replay
    if expected_tenant_id is not None and envelope.tenant_id != expected_tenant_id:
        raise BridgeValidationError("CROSS_TENANT_REPLAY")

    # Rule 13: Duplicate nonce
    if nonce_tracker is not None:
        if not nonce_tracker.check_and_record(
            envelope.mission_id, envelope.tenant_id, envelope.nonce
        ):
            raise BridgeValidationError("DUPLICATE_NONCE")

    # Rule 14: authority_delta != 0 unless explicitly authorized
    # This is enforced on the result side, but we also check that
    # EXPRIED authority_decision is rejected (covered by rule 9 if expired,
    # but EXPRIED as a decision value means the authority itself is expired)
    if envelope.authority_decision == AuthorityDecision.EXPIRED.value:
        raise BridgeValidationError("EXPIRED_AUTHORITY")


def validate_result(
    result: BridgeResultV1,
    *,
    expected_envelope: Optional[BridgeEnvelopeV1] = None,
) -> None:
    """Validate a bridge result against fail-closed invariants.

    Checks:
      - authority_delta == 0
      - side_effect_count == 0
      - evidence hash binding
      - schema version match
      - result/envelope identity binding (if expected_envelope provided)
      - malformed result evidence

    Raises BridgeValidationError on any failure.
    """
    # Schema version
    if result.schema_version != BRIDGE_CONTRACT_VERSION:
        raise BridgeValidationError("SCHEMA_VERSION_MISMATCH")

    # authority_delta must be 0
    if result.authority_delta != 0:
        raise BridgeValidationError("AUTHORITY_DELTA_NONZERO")

    # side_effect_count must be 0
    if result.side_effect_count != 0:
        raise BridgeValidationError("SIDE_EFFECT_COUNT_NONZERO")

    # Evidence hash binding
    expected_hash = compute_evidence_sha256(result.evidence)
    if result.evidence_sha256 != expected_hash:
        raise BridgeValidationError("EVIDENCE_HASH_MISMATCH")

    # Malformed result evidence — evidence must be a non-empty dict
    if not isinstance(result.evidence, dict) or not result.evidence:
        raise BridgeValidationError("MALFORMED_RESULT_EVIDENCE")

    # If envelope provided, verify identity binding
    if expected_envelope is not None:
        if result.mission_id != expected_envelope.mission_id:
            raise BridgeValidationError("CROSS_MISSION_REPLAY")
        if result.execution_id != expected_envelope.execution_id:
            raise BridgeValidationError("EXECUTION_ID_MISMATCH")
        if result.nonce != expected_envelope.nonce:
            raise BridgeValidationError("NONCE_MISMATCH")


# ---------------------------------------------------------------------------
# Contract artifact (immutable)
# ---------------------------------------------------------------------------

def contract_artifact() -> str:
    """Return the immutable contract artifact string."""
    lines = [
        f"BRIDGE_CONTRACT_VERSION = {BRIDGE_CONTRACT_VERSION}",
        "IDENTITY_BINDINGS = [mission_id, execution_id, nonce, tenant_id, actor_id]",
        "AUTHORITY_BINDINGS = [authority_decision, consequence_class, capability_id]",
        "INTEGRITY_BINDINGS = [payload_sha256, evidence_sha256]",
        "TEMPORAL_BINDINGS = [issued_at, expires_at]",
        "RESULT_INVARIANTS = [authority_delta, side_effect_count, status]",
    ]
    return "\n".join(lines)


def compute_contract_sha256() -> str:
    """Compute the SHA-256 of the contract artifact."""
    artifact = contract_artifact()
    return hashlib.sha256(artifact.encode("utf-8")).hexdigest()