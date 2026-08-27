"""Canonical internal mission path integration: P2 + P3 + P4.

Tests the first complete canonical internal mission path:
  production request → production_gateway → L2 MissionAggregate →
  real specialist dispatch → specialist result → evidence →
  mission_control_bridge → Mission Control projection.

Zero external side effects. Zero authority bypasses.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from sintra_live.l2.mission.model import (
    MissionAggregate,
    MissionIdentity,
    MissionScope,
    MissionState,
    TransitionRequest,
)
from sintra_live.l2.mission.store import MissionStore
from sintra_live.l2.mission_control_bridge import (
    BridgeStartRequest,
    BridgeTransitionResult,
    MissionControlBridge,
)
from sintra_live.l2.production_gateway import (
    extract_principal,
    resolve_authority,
)
from sintra_live.swarm.swarm import (
    BoundedResult,
    SpecialistDispatcher,
    SpecialistRole,
)


# ─── helpers ───

class _FakeUser:
    user_id = "principal-001"
    email = "p@example.com"
    role = "admin"
    tenant_id = "tenant-001"
    session_id = "session-001"

class _FakeState:
    current_user = _FakeUser()
    user_id = "principal-001"
    tenant_id = "tenant-001"
    role = "admin"

class _FakeRequest:
    state = _FakeState()
    headers = {"Authorization": "Bearer test-token"}
    method = "POST"
    url = type("URL", (), {"path": "/api/v1/orchestration/execute"})()


def _make_identity(mission_id: str = "canonical-internal-001") -> MissionIdentity:
    return MissionIdentity(
        program_id="SP-LIVE-001",
        gate_id="L2-I7B",
        mission_id=mission_id,
        request_id="req-canonical-001",
        request_sha256=hashlib.sha256(b"canonical-request").hexdigest(),
        principal_identity_reference="principal-001",
        mission_scope_sha256=hashlib.sha256(b"canonical-scope").hexdigest(),
        authority_snapshot_reference="sp-live-001-genesis-root",
    )


def _make_scope() -> MissionScope:
    return MissionScope(
        purpose="First canonical internal mission path test",
        allowed_operations=("dispatch_specialist",),
        prohibited_operations=("external_write",),
        consequence_ceiling="INTERNAL_ONLY",
        budget_ceilings=(("cost", 100), ("tokens", 1000)),
        side_effect_budget=0,
        required_evidence_types=("dispatch_receipt",),
        expiry="2026-08-25T16:00:00.000000Z",
        cancellation_authority="principal-001",
    )


def _make_bridge_start_request(mission_id: str = "canonical-internal-001") -> BridgeStartRequest:
    return BridgeStartRequest(
        purpose="First canonical internal mission path test",
        principal_reference="principal-001",
        mission_id=mission_id,
        program_id="SP-LIVE-001",
        gate_id="L2-I7B",
        request_id="req-canonical-001",
        request_sha256=hashlib.sha256(b"canonical-internal-001").hexdigest(),
        mission_scope_sha256=hashlib.sha256(b"scope-canonical-001").hexdigest(),
        authority_snapshot_reference="sp-live-001-genesis-root",
        allowed_operations=("dispatch_specialist",),
        prohibited_operations=("external_write",),
        consequence_ceiling="INTERNAL_ONLY",
        budget_ceilings=(("cost", 100), ("tokens", 1000)),
        required_evidence_types=("dispatch_receipt",),
        expiry="2026-08-25T16:00:00.000000Z",
        cancellation_authority="principal-001",
        actor_reference="principal-001",
        metadata={},
    )


# ─── P1: Production gateway ───

class TestProductionGatewayWiring:
    """P1: Production gateway extracts principal and bridges to L2."""

    def test_extract_principal(self):
        principal = extract_principal(_FakeRequest())
        assert principal["principal_id"] == "principal-001"

    def test_resolve_authority_delegates_to_l2(self):
        """Gateway forwards payload to L2 resolver and returns result unchanged."""
        from sintra_live.l2.principal_gateway_contract import (
            AuthorityResolution,
            AuthResult,
            Resolution,
        )
        sentinel = Resolution(
            result=AuthResult.ALLOW,
            record=object.__new__(AuthorityResolution),
        )
        with patch("sintra_live.l2.production_gateway._l2_resolve", return_value=sentinel) as mock:
            result = resolve_authority(_FakeRequest(), {"mission_id": "m1"})
            assert result is sentinel
            mock.assert_called_once()

    def test_resolve_authority_rejects_principal_mismatch(self):
        from sintra_live.l2.production_gateway import PortalAuthorityError
        class _FakeSession:
            principal_identity_reference = "someone-else"
        payload = {"session_attestation": _FakeSession()}
        with pytest.raises(PortalAuthorityError):
            resolve_authority(_FakeRequest(), payload)


# ─── P2: Real specialist dispatch ───

class TestSpecialistDispatch:
    """P2: Real governed specialist dispatch — not hardcoded."""

    def test_dispatch_returns_bounded_result(self):
        dispatcher = SpecialistDispatcher(mission_id="test-mission-001")
        result = dispatcher.dispatch(
            role=SpecialistRole.AUTHORITY_REVIEWER,
            memory_items=[],
            mission_scope={},
        )
        assert result.mission_id == "test-mission-001"
        assert result.authority_delta == 0
        assert result.output_hash

    def test_dispatch_is_not_hardcoded_string(self):
        dispatcher = SpecialistDispatcher(mission_id="test-mission-002")
        result = dispatcher.dispatch(
            role=SpecialistRole.AUTHORITY_REVIEWER,
            memory_items=[],
            mission_scope={},
        )
        assert not isinstance(result, str)
        assert hasattr(result, "claims")
        assert hasattr(result, "evidence_refs")

    def test_authority_delta_enforced_zero(self):
        with pytest.raises(ValueError, match="authority_delta"):
            BoundedResult(
                mission_id="test",
                role=SpecialistRole.AUTHORITY_REVIEWER,
                claims=[],
                evidence_refs=[],
                authority_delta=1,
            )

    def test_dispatch_deterministic_hash(self):
        d1 = SpecialistDispatcher(mission_id="test-det-001")
        d2 = SpecialistDispatcher(mission_id="test-det-001")
        r1 = d1.dispatch(
            role=SpecialistRole.AUTHORITY_REVIEWER,
            memory_items=[{"k": "v"}],
            mission_scope={"s": "d"},
        )
        r2 = d2.dispatch(
            role=SpecialistRole.AUTHORITY_REVIEWER,
            memory_items=[{"k": "v"}],
            mission_scope={"s": "d"},
        )
        assert r1.output_hash == r2.output_hash


# ─── P3+P4: Mission Control bridge ───

class TestMissionControlBridge:
    """P3+P4: Mission Control bridge projects canonical L2 state."""

    def test_bridge_start_and_load(self, tmp_path):
        bridge = MissionControlBridge(tmp_path / "store")
        request = _make_bridge_start_request("bridge-test-001")
        result = bridge.start(request)
        assert isinstance(result, BridgeTransitionResult)
        assert result.mission_id == "bridge-test-001"
        assert result.applied

        loaded = bridge.load("bridge-test-001")
        assert loaded is not None
        assert isinstance(loaded, MissionAggregate)
        assert loaded.current_state == MissionState.RECEIVED
        assert loaded.version == 0
        assert loaded.aggregate_sha256

    def test_bridge_projections_match_l2_store(self, tmp_path):
        """P4: Bridge projection matches exact L2 store state."""
        store_root = tmp_path / "store"
        bridge = MissionControlBridge(store_root)
        request = _make_bridge_start_request("projection-test-001")
        bridge.start(request)

        bridge_projection = bridge.load("projection-test-001")
        store = MissionStore(store_root)
        direct = store.load("projection-test-001")

        assert bridge_projection.identity.mission_id == direct.identity.mission_id
        assert bridge_projection.current_state == direct.current_state
        assert bridge_projection.version == direct.version
        assert bridge_projection.aggregate_sha256 == direct.aggregate_sha256


# ─── End-to-end canonical internal mission path ───

class TestCanonicalInternalMissionPath:
    """End-to-end: production request → L2 → dispatch → evidence → projection."""

    def test_full_canonical_internal_mission_path(self, tmp_path):
        """P2 + P3 + P4: the complete canonical internal mission path."""
        store_root = tmp_path / "mission_store"
        store = MissionStore(store_root)

        # Step 1: Production request enters L2
        principal = extract_principal(_FakeRequest())
        assert principal["principal_id"] == "principal-001"

        # Step 2: Authority resolution (mocked — full crypto attestation
        # is tested in the L2 I7 suite; here we verify the gateway bridge)
        from sintra_live.l2.principal_gateway_contract import (
            AuthorityResolution,
            AuthResult,
            Resolution,
        )
        sentinel = Resolution(
            result=AuthResult.ALLOW,
            record=object.__new__(AuthorityResolution),
        )
        with patch("sintra_live.l2.production_gateway._l2_resolve", return_value=sentinel):
            auth_result = resolve_authority(_FakeRequest(), {"mission_id": "canonical-internal-001"})
        assert auth_result.result == "ALLOW"

        # Step 3: L2 MissionAggregate created
        identity = _make_identity()
        scope = _make_scope()
        created_at = "2026-08-25T15:00:00.000000Z"
        aggregate = store.create(identity, scope, created_at=created_at)
        assert aggregate.current_state == MissionState.RECEIVED
        assert aggregate.identity.mission_id == "canonical-internal-001"
        assert aggregate.version == 0
        assert aggregate.aggregate_sha256

        # Step 4: Mission transitions through canonical I1 states
        # I1 edges: RECEIVED→PRINCIPAL_IDENTIFIED→MISSION_SCOPED
        transitions = [
            (MissionState.PRINCIPAL_IDENTIFIED, "Principal identified via production gateway"),
            (MissionState.MISSION_SCOPED, "Mission scope validated"),
        ]
        for i, (to_state, reason) in enumerate(transitions):
            loaded = store.load("canonical-internal-001")
            tr = TransitionRequest(
                mission_id="canonical-internal-001",
                idempotency_key=f"transition-{i}",
                expected_version=loaded.version,
                expected_state=loaded.current_state,
                expected_previous_event_sha256=loaded.previous_event_sha256,
                to_state=to_state,
                reason=reason,
                evidence_sha256=hashlib.sha256(reason.encode()).hexdigest(),
                actor_reference="principal-001",
                cancellation_authority_reference=None,
            )
            result = store.transition(tr)
            assert result.outcome.value in ("TRANSITIONED", "APPLIED")

        loaded = store.load("canonical-internal-001")
        assert loaded.current_state == MissionState.MISSION_SCOPED

        # Step 5: P2 — Real specialist dispatch
        dispatcher = SpecialistDispatcher(mission_id="canonical-internal-001")
        dispatch_result = dispatcher.dispatch(
            role=SpecialistRole.AUTHORITY_REVIEWER,
            memory_items=[{"key": "test", "value": "data"}],
            mission_scope={"description": "canonical internal mission"},
        )
        assert dispatch_result is not None
        assert dispatch_result.mission_id == "canonical-internal-001"
        assert dispatch_result.role == SpecialistRole.AUTHORITY_REVIEWER
        assert dispatch_result.authority_delta == 0
        assert dispatch_result.output_hash
        assert len(dispatch_result.claims) > 0
        assert len(dispatch_result.evidence_refs) > 0
        assert not isinstance(dispatch_result, str)

        # Step 6: P3 — Collaboration context bound to L2 mission
        assert dispatch_result.mission_id == loaded.identity.mission_id
        assert loaded.aggregate_sha256

        # Step 7: Evidence generated
        evidence = {
            "mission_id": "canonical-internal-001",
            "aggregate_sha256": loaded.aggregate_sha256,
            "specialist_role": dispatch_result.role.value,
            "specialist_output_hash": dispatch_result.output_hash,
            "authority_delta": dispatch_result.authority_delta,
            "evidence_type": "dispatch_receipt",
        }
        evidence_hash = hashlib.sha256(
            json.dumps(evidence, sort_keys=True).encode()
        ).hexdigest()
        assert evidence_hash

        # Step 8: P4 — Mission Control projects L2 state
        bridge = MissionControlBridge(store_root)
        projection = bridge.load("canonical-internal-001")
        assert projection is not None
        assert projection.identity.mission_id == "canonical-internal-001"
        assert projection.current_state == MissionState.MISSION_SCOPED
        assert projection.version >= 1
        assert projection.aggregate_sha256 == loaded.aggregate_sha256

        # Step 9: Verify zero authority bypasses
        assert dispatch_result.authority_delta == 0
        assert auth_result.result == "ALLOW"
        assert loaded.current_state == MissionState.MISSION_SCOPED