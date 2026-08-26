"""Tests for authority propagation and replay protection.

Tests:
  - Authority decision binding (ALLOW / DENY)
  - authority_delta == 0 invariant
  - Nonce replay detection (duplicate, cross-mission, cross-tenant)
  - Envelope expiry rejection
  - Revoked authority rejection
  - Nonce tracker isolation across tenants and missions
  - All 8 AuthorityDecision values propagated

BRIDGE_CONTRACT_SHA256 = 7c08de2fc06a3698d40c0d947d77ea2915419d4354e459de95e2dfc1e199a062
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from sintra_live.l2.bridge_envelope_contract import (
    BRIDGE_CONTRACT_VERSION,
    AuthorityDecision,
    BridgeValidationError,
    compute_payload_sha256,
)
from sintra_live.l2.action_envelope_contract import ConsequenceClass
from sintra_live.l2.bridge_authority_propagation import (
    AuthorityPropagator,
    propagate_authority,
    check_authority_delta,
)
from sintra_live.l2.bridge_replay_protection import (
    NonceTracker,
    check_expiry,
    check_revoked,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _future(seconds: int = 3600) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )


def _past(seconds: int = 3600) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )


def _envelope_fields(**overrides):
    """Return a dict of valid envelope fields suitable for propagate_authority."""
    payload = {"action": "test_action", "data": {"key": "value"}}
    fields = dict(
        schema_version=BRIDGE_CONTRACT_VERSION,
        mission_id="mission-001",
        execution_id="exec-001",
        nonce="nonce-001",
        tenant_id="tenant-001",
        actor_id="actor-001",
        consequence_class=ConsequenceClass.READ_ONLY.value,
        capability_id="named_agents",
        payload=payload,
        issued_at=_now(),
        expires_at=_future(3600),
        provenance="sintra_live/l2/bridge_authority_propagation",
    )
    fields.update(overrides)
    return fields


# ---------------------------------------------------------------------------
# Authority propagation
# ---------------------------------------------------------------------------

class TestAuthorityPropagation:
    def test_authority_propagation_allow(self):
        """propagate_authority with ALLOW binds ALLOW to the envelope."""
        env = propagate_authority(
            AuthorityDecision.ALLOW.value,
            **_envelope_fields(),
        )
        assert env.authority_decision == AuthorityDecision.ALLOW.value
        assert env.mission_id == "mission-001"
        assert env.schema_version == BRIDGE_CONTRACT_VERSION

    def test_authority_propagation_deny(self):
        """propagate_authority with DENY binds DENY to the envelope."""
        env = propagate_authority(
            AuthorityDecision.DENY.value,
            **_envelope_fields(nonce="nonce-deny-001"),
        )
        assert env.authority_decision == AuthorityDecision.DENY.value

    def test_authority_decision_all_values_propagated(self):
        """All 8 AuthorityDecision values are propagated correctly."""
        all_decisions = [
            AuthorityDecision.ALLOW,
            AuthorityDecision.DENY,
            AuthorityDecision.APPROVAL_REQUIRED,
            AuthorityDecision.CAPABILITY_UNAVAILABLE,
            AuthorityDecision.AUTHORITY_MISSING,
            AuthorityDecision.POLICY_CONFLICT,
            AuthorityDecision.EXPIRED,
            AuthorityDecision.REVOKED,
        ]
        assert len(all_decisions) == 8

        for i, decision in enumerate(all_decisions):
            env = propagate_authority(
                decision.value,
                **_envelope_fields(nonce=f"nonce-all-{i:02d}"),
            )
            assert env.authority_decision == decision.value, (
                f"authority_decision mismatch for {decision.value}"
            )

    def test_propagator_mismatch_rejected(self):
        """AuthorityPropagator rejects envelope with mismatched decision."""
        propagator = AuthorityPropagator(AuthorityDecision.ALLOW.value)
        with pytest.raises(BridgeValidationError, match="AUTHORITY_DECISION_MISMATCH"):
            propagator.bind_to_envelope(
                **_envelope_fields(authority_decision=AuthorityDecision.DENY.value)
            )

    def test_propagator_unknown_decision_rejected(self):
        """AuthorityPropagator rejects unknown authority decision."""
        with pytest.raises(BridgeValidationError, match="INVALID_AUTHORITY_DECISION"):
            AuthorityPropagator("BOGUS_DECISION")

    def test_propagate_authority_auto_payload_hash(self):
        """propagate_authority computes payload_sha256 when not provided."""
        env = propagate_authority(
            AuthorityDecision.ALLOW.value,
            **_envelope_fields(nonce="nonce-hash-001"),
        )
        assert env.payload_sha256 == compute_payload_sha256(env.payload)


# ---------------------------------------------------------------------------
# authority_delta invariant
# ---------------------------------------------------------------------------

class TestAuthorityDelta:
    def test_authority_delta_zero_passes(self):
        """check_authority_delta(0) returns (True, ...)."""
        allowed, reason = check_authority_delta(0)
        assert allowed is True
        assert reason == "OK"

    def test_authority_delta_nonzero_rejected(self):
        """check_authority_delta(nonzero) returns (False, ...)."""
        for delta in (1, -1, 42, 100):
            allowed, reason = check_authority_delta(delta)
            assert allowed is False, f"delta={delta} should be rejected"
            assert reason == "AUTHORITY_DELTA_NONZERO"

    def test_authority_delta_bool_rejected(self):
        """check_authority_delta rejects bool (even True which == 1)."""
        allowed, reason = check_authority_delta(True)  # noqa: FBT003
        assert allowed is False
        assert reason == "AUTHORITY_DELTA_NONZERO"


# ---------------------------------------------------------------------------
# Nonce tracker
# ---------------------------------------------------------------------------

class TestNonceTracker:
    def test_valid_nonce_accepted(self):
        """A fresh nonce is accepted."""
        tracker = NonceTracker()
        allowed, reason = tracker.check_nonce("mission-001", "tenant-001", "nonce-A")
        assert allowed is True
        assert reason == "OK"

    def test_duplicate_nonce_rejected(self):
        """Duplicate nonce on same mission+tenant is rejected."""
        tracker = NonceTracker()
        tracker.check_nonce("mission-001", "tenant-001", "nonce-DUP")
        allowed, reason = tracker.check_nonce(
            "mission-001", "tenant-001", "nonce-DUP"
        )
        assert allowed is False
        assert reason == "DUPLICATE_NONCE"

    def test_cross_mission_replay_rejected(self):
        """Same nonce on different mission_id is rejected."""
        tracker = NonceTracker()
        tracker.check_nonce("mission-A", "tenant-001", "nonce-XM")
        allowed, reason = tracker.check_nonce(
            "mission-B", "tenant-001", "nonce-XM"
        )
        assert allowed is False
        assert reason == "CROSS_MISSION_REPLAY"

    def test_cross_tenant_replay_rejected(self):
        """Same nonce on different tenant_id is rejected."""
        tracker = NonceTracker()
        tracker.check_nonce("mission-001", "tenant-A", "nonce-XT")
        allowed, reason = tracker.check_nonce(
            "mission-001", "tenant-B", "nonce-XT"
        )
        assert allowed is False
        assert reason == "CROSS_TENANT_REPLAY"

    def test_nonce_tracker_isolation(self):
        """Different tenants and missions with same nonce don't interfere.

        Wait -- per the design rules, same nonce on different mission or
        tenant IS a replay. So isolation means: different nonces on different
        (mission, tenant) pairs are all accepted independently.
        """
        tracker = NonceTracker()
        # Different nonces on different (mission, tenant) pairs -- all accepted
        for i in range(5):
            allowed, reason = tracker.check_nonce(
                f"mission-{i}", f"tenant-{i}", f"nonce-iso-{i}"
            )
            assert allowed is True, f"nonce-iso-{i} should be accepted"
            assert reason == "OK"

    def test_nonce_tracker_clear(self):
        """clear() resets the tracker so nonces can be reused."""
        tracker = NonceTracker()
        tracker.check_nonce("mission-001", "tenant-001", "nonce-CLR")
        tracker.clear()
        allowed, reason = tracker.check_nonce(
            "mission-001", "tenant-001", "nonce-CLR"
        )
        assert allowed is True
        assert reason == "OK"


# ---------------------------------------------------------------------------
# Expiry check
# ---------------------------------------------------------------------------

class TestExpiry:
    def test_expired_envelope_rejected(self):
        """check_expiry rejects a past timestamp."""
        allowed, reason = check_expiry(_past(3600))
        assert allowed is False
        assert reason == "EXPIRED_ENVELOPE"

    def test_future_envelope_accepted(self):
        """check_expiry accepts a future timestamp."""
        allowed, reason = check_expiry(_future(3600))
        assert allowed is True
        assert reason == "OK"

    def test_invalid_timestamp_rejected(self):
        """check_expiry rejects an unparseable timestamp (fail-closed)."""
        allowed, reason = check_expiry("not-a-timestamp")
        assert allowed is False
        assert reason == "EXPIRED_ENVELOPE"


# ---------------------------------------------------------------------------
# Revoked authority check
# ---------------------------------------------------------------------------

class TestRevokedAuthority:
    def test_revoked_authority_rejected(self):
        """check_revoked rejects REVOKED authority_decision."""
        allowed, reason = check_revoked(AuthorityDecision.REVOKED.value)
        assert allowed is False
        assert reason == "REVOKED_AUTHORITY"

    def test_non_revoked_authority_accepted(self):
        """check_revoked accepts non-REVOKED authority_decision values."""
        for decision in [
            AuthorityDecision.ALLOW,
            AuthorityDecision.DENY,
            AuthorityDecision.APPROVAL_REQUIRED,
            AuthorityDecision.CAPABILITY_UNAVAILABLE,
            AuthorityDecision.AUTHORITY_MISSING,
            AuthorityDecision.POLICY_CONFLICT,
            AuthorityDecision.EXPIRED,
        ]:
            allowed, reason = check_revoked(decision.value)
            assert allowed is True, f"{decision.value} should be accepted"
            assert reason == "OK"