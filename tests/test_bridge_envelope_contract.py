"""Contract tests for the canonical bridge envelope/result contract (sp-bridge-v1).

Wave 0 tests verifying:
  - Round-trip serialization (envelope + result)
  - Hash determinism
  - Payload hash binding
  - Evidence hash binding
  - AuthorityDecision enum validation (all 8 values)
  - All 14 fail-closed reject rules
  - Cross-mission / cross-tenant replay denial
  - Duplicate nonce denial
  - Malformed result evidence denial
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import pytest

from sintra_live.l2.bridge_envelope_contract import (
    BRIDGE_CONTRACT_VERSION,
    AuthorityDecision,
    BridgeEnvelopeV1,
    BridgeResultV1,
    BridgeValidationError,
    InMemoryNonceTracker,
    compute_contract_sha256,
    compute_evidence_sha256,
    compute_payload_sha256,
    contract_artifact,
    deserialize_envelope_v1,
    deserialize_result_v1,
    serialize_envelope_v1,
    serialize_result_v1,
    validate_envelope,
    validate_result,
)
from sintra_live.l2.action_envelope_contract import ConsequenceClass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _future(seconds: int = 3600) -> str:
    from datetime import timedelta
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )


def _past(seconds: int = 3600) -> str:
    from datetime import timedelta
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )


def _make_envelope(**overrides) -> BridgeEnvelopeV1:
    """Build a valid envelope with sensible defaults; override any field."""
    payload = {"action": "test_action", "data": {"key": "value"}}
    defaults = dict(
        schema_version=BRIDGE_CONTRACT_VERSION,
        mission_id="mission-001",
        execution_id="exec-001",
        nonce="nonce-001",
        tenant_id="tenant-001",
        actor_id="actor-001",
        authority_decision=AuthorityDecision.ALLOW.value,
        consequence_class=ConsequenceClass.READ_ONLY.value,
        capability_id="named_agents",
        payload=payload,
        payload_sha256=compute_payload_sha256(payload),
        issued_at=_now(),
        expires_at=_future(3600),
        provenance="sintra_live/l2/bridge_envelope_contract",
    )
    defaults.update(overrides)
    return BridgeEnvelopeV1(**defaults)


def _make_result(**overrides) -> BridgeResultV1:
    """Build a valid result with sensible defaults; override any field."""
    evidence = {"receipt": "ev-001", "hash": "abc123"}
    result_data = {"status": "COMPLETE", "output": "success"}
    defaults = dict(
        schema_version=BRIDGE_CONTRACT_VERSION,
        mission_id="mission-001",
        execution_id="exec-001",
        nonce="nonce-001",
        status="COMPLETE",
        result=result_data,
        evidence=evidence,
        evidence_sha256=compute_evidence_sha256(evidence),
        authority_delta=0,
        side_effect_count=0,
        completed_at=_now(),
    )
    defaults.update(overrides)
    return BridgeResultV1(**defaults)


# ---------------------------------------------------------------------------
# Round-trip tests
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_envelope_round_trip(self):
        """Envelope survives serialize -> deserialize without loss."""
        env = _make_envelope()
        raw = serialize_envelope_v1(env)
        restored = deserialize_envelope_v1(raw)
        assert restored == env, "round-trip should produce identical envelope"

    def test_result_round_trip(self):
        """Result survives serialize -> deserialize without loss."""
        res = _make_result()
        raw = serialize_result_v1(res)
        restored = deserialize_result_v1(raw)
        assert restored == res, "round-trip should produce identical result"


# ---------------------------------------------------------------------------
# Hash determinism and binding
# ---------------------------------------------------------------------------

class TestHashing:
    def test_envelope_hash_deterministic(self):
        """Same logical payload produces same hash every time."""
        payload = {"b": 2, "a": 1, "nested": {"z": True, "y": "str"}}
        h1 = compute_payload_sha256(payload)
        h2 = compute_payload_sha256(payload)
        assert h1 == h2, "hash should be deterministic"
        # Reordered dict should produce same hash (sort_keys=True)
        payload_reordered = {"a": 1, "b": 2, "nested": {"y": "str", "z": True}}
        h3 = compute_payload_sha256(payload_reordered)
        assert h1 == h3, "hash should be order-independent"

    def test_payload_hash_binding(self):
        """Envelope payload_sha256 must match computed hash of payload."""
        payload = {"action": "execute", "params": {"x": 42}}
        env = _make_envelope(
            payload=payload,
            payload_sha256=compute_payload_sha256(payload),
        )
        assert env.payload_sha256 == compute_payload_sha256(payload)
        # Mismatch should be rejected at construction
        with pytest.raises(BridgeValidationError, match="PAYLOAD_HASH_MISMATCH"):
            BridgeEnvelopeV1(
                **{**_make_envelope().to_dict(),
                   "payload_sha256": "0" * 64}
            )

    def test_evidence_hash_binding(self):
        """Result evidence_sha256 must match computed hash of evidence."""
        evidence = {"proof": "hash-proof", "chain": ["a", "b"]}
        res = _make_result(
            evidence=evidence,
            evidence_sha256=compute_evidence_sha256(evidence),
        )
        assert res.evidence_sha256 == compute_evidence_sha256(evidence)
        # Mismatch should be rejected at construction
        with pytest.raises(BridgeValidationError, match="EVIDENCE_HASH_MISMATCH"):
            BridgeResultV1(
                **{**_make_result().to_dict(),
                   "evidence_sha256": "0" * 64}
            )


# ---------------------------------------------------------------------------
# AuthorityDecision enum validation
# ---------------------------------------------------------------------------

class TestAuthorityDecision:
    def test_authority_decision_enum_validation(self):
        """All 8 AuthorityDecision values are valid; unknown values rejected."""
        valid_values = [
            AuthorityDecision.ALLOW,
            AuthorityDecision.DENY,
            AuthorityDecision.APPROVAL_REQUIRED,
            AuthorityDecision.CAPABILITY_UNAVAILABLE,
            AuthorityDecision.AUTHORITY_MISSING,
            AuthorityDecision.POLICY_CONFLICT,
            AuthorityDecision.EXPIRED,
            AuthorityDecision.REVOKED,
        ]
        assert len(valid_values) == 8, "must have exactly 8 values"

        # Each valid value should construct successfully
        for decision in valid_values:
            env = _make_envelope(authority_decision=decision.value)
            assert env.authority_decision == decision.value

        # Unknown value should be rejected
        with pytest.raises(BridgeValidationError, match="INVALID_AUTHORITY_DECISION"):
            _make_envelope(authority_decision="UNKNOWN_DECISION")


# ---------------------------------------------------------------------------
# 14 fail-closed reject rules
# ---------------------------------------------------------------------------

class TestRejectRules:
    def test_schema_version_mismatch_denied(self):
        """Unknown schema version is rejected."""
        with pytest.raises(BridgeValidationError, match="SCHEMA_VERSION_MISMATCH"):
            _make_envelope(schema_version="wrong-version")

    def test_missing_mission_id_denied(self):
        """Missing mission_id is rejected."""
        with pytest.raises(BridgeValidationError, match="INVALID_IDENTIFIER"):
            _make_envelope(mission_id="")

    def test_missing_execution_id_denied(self):
        """Missing execution_id is rejected."""
        with pytest.raises(BridgeValidationError, match="INVALID_IDENTIFIER"):
            _make_envelope(execution_id="")

    def test_missing_nonce_denied(self):
        """Missing nonce is rejected."""
        with pytest.raises(BridgeValidationError, match="INVALID_IDENTIFIER"):
            _make_envelope(nonce="")

    def test_missing_tenant_id_denied(self):
        """Missing tenant_id is rejected."""
        with pytest.raises(BridgeValidationError, match="INVALID_IDENTIFIER"):
            _make_envelope(tenant_id="")

    def test_missing_authority_decision_denied(self):
        """Missing authority_decision is rejected."""
        with pytest.raises(BridgeValidationError, match="INVALID_AUTHORITY_DECISION"):
            _make_envelope(authority_decision="")

    def test_missing_capability_id_denied(self):
        """Missing capability_id is rejected."""
        with pytest.raises(BridgeValidationError, match="INVALID_IDENTIFIER"):
            _make_envelope(capability_id="")

    def test_payload_hash_mismatch_denied(self):
        """Payload hash mismatch is rejected at construction."""
        with pytest.raises(BridgeValidationError, match="PAYLOAD_HASH_MISMATCH"):
            BridgeEnvelopeV1(
                **{**_make_envelope().to_dict(),
                   "payload_sha256": "0" * 64}
            )

    def test_expired_envelope_denied(self):
        """Expired envelope is rejected by validate_envelope."""
        env = _make_envelope(
            issued_at=_past(7200),
            expires_at=_past(3600),
        )
        with pytest.raises(BridgeValidationError, match="EXPIRED_ENVELOPE"):
            validate_envelope(env)

    def test_authority_delta_nonzero_denied(self):
        """Result with authority_delta != 0 is rejected."""
        with pytest.raises(BridgeValidationError, match="AUTHORITY_DELTA_NONZERO"):
            BridgeResultV1(
                **{**_make_result().to_dict(),
                   "authority_delta": 1}
            )

    def test_duplicate_nonce_denied(self):
        """Duplicate nonce is rejected by validate_envelope with nonce tracker."""
        tracker = InMemoryNonceTracker()
        env = _make_envelope(nonce="unique-nonce-001")
        # First validation should pass
        validate_envelope(env, nonce_tracker=tracker)

        # Second validation with same nonce should fail
        with pytest.raises(BridgeValidationError, match="DUPLICATE_NONCE"):
            validate_envelope(env, nonce_tracker=tracker)

    def test_malformed_result_evidence_denied(self):
        """Malformed result evidence is rejected by validate_result."""
        # Empty evidence dict
        res = _make_result(evidence={}, evidence_sha256=compute_evidence_sha256({}))
        with pytest.raises(BridgeValidationError, match="MALFORMED_RESULT_EVIDENCE"):
            validate_result(res)

    def test_cross_mission_replay_denied(self):
        """Cross-mission replay (mismatched mission_id) is rejected."""
        env = _make_envelope(mission_id="mission-A")
        with pytest.raises(BridgeValidationError, match="CROSS_MISSION_REPLAY"):
            validate_envelope(env, expected_mission_id="mission-B")

    def test_cross_tenant_replay_denied(self):
        """Cross-tenant replay (mismatched tenant_id) is rejected."""
        env = _make_envelope(tenant_id="tenant-A")
        with pytest.raises(BridgeValidationError, match="CROSS_TENANT_REPLAY"):
            validate_envelope(env, expected_tenant_id="tenant-B")


# ---------------------------------------------------------------------------
# Additional validation tests
# ---------------------------------------------------------------------------

class TestAdditionalValidation:
    def test_revoked_authority_denied(self):
        """REVOKED authority_decision is rejected by validate_envelope."""
        env = _make_envelope(authority_decision=AuthorityDecision.REVOKED.value)
        with pytest.raises(BridgeValidationError, match="REVOKED_AUTHORITY"):
            validate_envelope(env)

    def test_expired_authority_decision_denied(self):
        """EXPIRED authority_decision is rejected by validate_envelope."""
        env = _make_envelope(authority_decision=AuthorityDecision.EXPIRED.value)
        with pytest.raises(BridgeValidationError, match="EXPIRED_AUTHORITY"):
            validate_envelope(env)

    def test_side_effect_count_nonzero_denied(self):
        """Result with side_effect_count != 0 is rejected."""
        with pytest.raises(BridgeValidationError, match="SIDE_EFFECT_COUNT_NONZERO"):
            BridgeResultV1(
                **{**_make_result().to_dict(),
                   "side_effect_count": 1}
            )

    def test_valid_envelope_passes_validation(self):
        """A valid envelope passes all validation rules."""
        tracker = InMemoryNonceTracker()
        env = _make_envelope(nonce="valid-nonce-001")
        validate_envelope(env, nonce_tracker=tracker)

    def test_valid_result_passes_validation(self):
        """A valid result passes all validation rules."""
        res = _make_result()
        validate_result(res)

    def test_result_envelope_binding(self):
        """Result must match envelope identity fields when provided."""
        env = _make_envelope(
            mission_id="mission-bound",
            execution_id="exec-bound",
            nonce="nonce-bound",
        )
        # Matching result passes
        res = _make_result(
            mission_id="mission-bound",
            execution_id="exec-bound",
            nonce="nonce-bound",
        )
        validate_result(res, expected_envelope=env)

        # Mismatched mission_id fails
        res_mismatch = _make_result(mission_id="mission-wrong")
        with pytest.raises(BridgeValidationError, match="CROSS_MISSION_REPLAY"):
            validate_result(res_mismatch, expected_envelope=env)

    def test_canonical_json_format(self):
        """Serialized output uses sort_keys=True, separators=(',',':')."""
        env = _make_envelope()
        raw = serialize_envelope_v1(env)
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        # No spaces after colons or commas
        assert ": " not in text, "should not have spaces after colons"
        assert ", " not in text, "should not have spaces after commas"
        # Keys should be sorted
        data = json.loads(text)
        keys = list(data.keys())
        assert keys == sorted(keys), "keys should be sorted"

    def test_contract_artifact_and_sha256(self):
        """Contract artifact is emitted and has a deterministic SHA-256."""
        artifact = contract_artifact()
        assert "BRIDGE_CONTRACT_VERSION = sp-bridge-v1" in artifact
        assert "IDENTITY_BINDINGS" in artifact
        assert "AUTHORITY_BINDINGS" in artifact
        assert "INTEGRITY_BINDINGS" in artifact
        assert "TEMPORAL_BINDINGS" in artifact
        assert "RESULT_INVARIANTS" in artifact

        sha = compute_contract_sha256()
        assert len(sha) == 64, "SHA-256 should be 64 hex chars"
        # Deterministic
        sha2 = compute_contract_sha256()
        assert sha == sha2, "contract SHA-256 should be deterministic"