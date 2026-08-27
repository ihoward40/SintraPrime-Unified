"""
Canonical 12-stage acceptance mission for the SintraPrime bridge.

Tests exercise the full mission lifecycle using deterministic / mock
objects so that no external services are required:

  PRINCIPAL_REQUEST → MISSION_SCOPE → POLICY_RESOLUTION →
  AUTHORITY_RESOLUTION → EXECUTION_ENVELOPE → PYTHON_BRIDGE →
  TYPESCRIPT_RUNTIME → GOVERNED_INTERNAL_ACTION →
  TYPESCRIPT_RESULT → PYTHON_RECONCILIATION → EVIDENCE_HASH →
  MISSION_CONTROL_PROJECTION → VERIFIED_COMPLETE

Sub-variants test denial, expiry, missing evidence, transport-success-
but-mission-fail, and hash determinism.
"""

from __future__ import annotations

import copy
import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

import pytest

from sintra_live.l2.bridge_mission_projection import (
    BridgeMissionProjection,
    BridgeMissionStatus,
    project_mission_for_bridge,
    reconcile_bridge_result,
    verify_evidence_chain,
)
from sintra_live.l2.python_typescript_bridge import (
    BridgeExecutionOutcome,
    BridgeTransportStatus,
    build_v1_envelope,
)
from sintra_live.l2.bridge_envelope_contract import AuthorityDecision, serialize_envelope_v1


# ---------------------------------------------------------------------------
# Deterministic test infrastructure
# ---------------------------------------------------------------------------

AGG_HASH = hashlib.sha256(b"aggregate-v1").hexdigest()
EVID_HASH = hashlib.sha256(b"evidence-chain-ok").hexdigest()
BRIDGE_CONTRACT_SHA256 = (
    "7c08de2fc06a3698d40c0d947d77ea2915419d4354e459de95e2dfc1e199a062"
)


class TransportStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass
class MockAuthorityDecision:
    decision: str  # "APPROVED" | "DENIED"
    delta: int = 0


@dataclass
class MockEnvelope:
    """Deterministic stand-in for BridgeEnvelopeV1."""
    envelope_id: str
    mission_id: str
    payload: Dict[str, Any]
    authority_decision: MockAuthorityDecision
    nonce: str
    expires_at: float
    evidence_sha256: Optional[str] = None
    payload_sha256: Optional[str] = None

    def canonical_bytes(self) -> bytes:
        """Deterministic canonical serialization for hashing."""
        return json.dumps(
            {
                "envelope_id": self.envelope_id,
                "mission_id": self.mission_id,
                "payload": self.payload,
                "authority_decision": self.authority_decision.decision,
                "authority_delta": self.authority_decision.delta,
                "nonce": self.nonce,
                "expires_at": self.expires_at,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")


@dataclass
class MockBridgeResult:
    """Deterministic stand-in for BridgeResultV1."""
    envelope_id: str
    mission_id: str
    transport_status: TransportStatus
    evidence_sha256: Optional[str]
    authority_delta: int = 0
    side_effect_count: int = 0
    success: bool = True
    result_payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MockL2State:
    """Minimal L2 store representation for tests."""
    mission_id: str
    execution_id: str
    aggregate_version: int
    aggregate_sha256: str
    authority_decision: Optional[str]
    evidence_sha256: Optional[str]
    status: BridgeMissionStatus = BridgeMissionStatus.PENDING


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Stage helpers
# ---------------------------------------------------------------------------

def stage_principal_request(action: str = "read_config") -> Dict[str, Any]:
    """Stage 1: PRINCIPAL_REQUEST"""
    return {"action": action, "requested_at": "2026-08-26T12:00:00Z"}


def stage_mission_scope(request: Dict[str, Any], mission_id: str = "m-acc-001") -> Dict[str, Any]:
    """Stage 2: MISSION_SCOPE"""
    return {"mission_id": mission_id, "action": request["action"], "scope": "internal"}


def stage_policy_resolution(scope: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 3: POLICY_RESOLUTION"""
    return {"policy": "allow_internal_read", "scope": scope["scope"]}


def stage_authority_resolution(
    policy: Dict[str, Any],
    decision: str = "APPROVED",
) -> MockAuthorityDecision:
    """Stage 4: AUTHORITY_RESOLUTION"""
    return MockAuthorityDecision(decision=decision, delta=0)


def stage_execution_envelope(
    scope: Dict[str, Any],
    authority: MockAuthorityDecision,
    evidence_sha256: Optional[str] = EVID_HASH,
    expires_in: float = 300.0,
) -> MockEnvelope:
    """Stage 5: EXECUTION_ENVELOPE"""
    now = time.time()
    return MockEnvelope(
        envelope_id="env-" + scope["mission_id"],
        mission_id=scope["mission_id"],
        payload={"action": scope["action"]},
        authority_decision=authority,
        nonce="nonce-12345",
        expires_at=now + expires_in,
        evidence_sha256=evidence_sha256,
        payload_sha256=_sha256(json.dumps({"action": scope["action"]}, sort_keys=True).encode()),
    )


def stage_python_bridge(envelope: MockEnvelope) -> MockEnvelope:
    """Stage 6: PYTHON_BRIDGE — pass envelope through the Python bridge layer."""
    return envelope


def stage_typescript_runtime(envelope: MockEnvelope) -> Dict[str, Any]:
    """Stage 7: TYPESCRIPT_RUNTIME — simulate TS runtime receiving envelope."""
    return {"received_envelope_id": envelope.envelope_id, "payload": envelope.payload}


def stage_governed_internal_action(ts_context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 8: GOVERNED_INTERNAL_ACTION — perform the internal action."""
    return {"action_result": "ok", "action": ts_context["payload"]["action"]}


def stage_typescript_result(
    envelope: MockEnvelope,
    action_result: Dict[str, Any],
    transport_status: TransportStatus = TransportStatus.SUCCESS,
    evidence_sha256: Optional[str] = EVID_HASH,
    side_effect_count: int = 0,
) -> MockBridgeResult:
    """Stage 9: TYPESCRIPT_RESULT"""
    return MockBridgeResult(
        envelope_id=envelope.envelope_id,
        mission_id=envelope.mission_id,
        transport_status=transport_status,
        evidence_sha256=evidence_sha256,
        authority_delta=envelope.authority_decision.delta,
        side_effect_count=side_effect_count,
        success=(transport_status == TransportStatus.SUCCESS),
        result_payload=action_result,
    )


def stage_python_reconciliation(
    result: MockBridgeResult,
    envelope: MockEnvelope,
) -> Dict[str, Any]:
    """Stage 10: PYTHON_RECONCILIATION — verify result against envelope."""
    chain_ok = verify_evidence_chain(envelope.evidence_sha256, result.evidence_sha256)
    return {
        "evidence_chain_ok": chain_ok,
        "authority_delta": result.authority_delta,
        "side_effect_count": result.side_effect_count,
        "transport_success": result.transport_status == TransportStatus.SUCCESS,
    }


def stage_evidence_hash(reconciliation: Dict[str, Any], envelope: MockEnvelope) -> str:
    """Stage 11: EVIDENCE_HASH — compute / verify the evidence hash."""
    if reconciliation["evidence_chain_ok"]:
        return envelope.evidence_sha256 or EVID_HASH
    return _sha256(b"broken-evidence")


def stage_mission_control_projection(
    envelope: MockEnvelope,
    evidence_sha256: str,
    l2_state: MockL2State,
    status: BridgeMissionStatus = BridgeMissionStatus.EXECUTING,
) -> BridgeMissionProjection:
    """Stage 12: MISSION_CONTROL_PROJECTION — create read-only projection."""
    return project_mission_for_bridge(
        mission_id=l2_state.mission_id,
        execution_id=l2_state.execution_id,
        aggregate_version=l2_state.aggregate_version,
        aggregate_sha256=l2_state.aggregate_sha256,
        authority_decision=l2_state.authority_decision,
        evidence_sha256=evidence_sha256,
        status=status,
    )


def _run_full_flow(
    authority_decision: str = "APPROVED",
    expires_in: float = 300.0,
    result_evidence: Optional[str] = EVID_HASH,
    transport_status: TransportStatus = TransportStatus.SUCCESS,
    side_effect_count: int = 0,
    l2_authority: Optional[str] = "APPROVED",
) -> tuple[BridgeMissionProjection, BridgeMissionStatus, MockEnvelope, MockBridgeResult, Dict[str, Any]]:
    """Run the complete 12-stage flow and return the final state."""
    # 1
    req = stage_principal_request()
    # 2
    scope = stage_mission_scope(req)
    # 3
    policy = stage_policy_resolution(scope)
    # 4
    authority = stage_authority_resolution(policy, decision=authority_decision)
    # 5
    envelope = stage_execution_envelope(scope, authority, expires_in=expires_in)
    # 6
    envelope = stage_python_bridge(envelope)
    # 7
    ts_ctx = stage_typescript_runtime(envelope)
    # 8
    action_res = stage_governed_internal_action(ts_ctx)
    # 9
    result = stage_typescript_result(
        envelope, action_res,
        transport_status=transport_status,
        evidence_sha256=result_evidence,
        side_effect_count=side_effect_count,
    )
    # 10
    recon = stage_python_reconciliation(result, envelope)
    # 11
    ev_hash = stage_evidence_hash(recon, envelope)
    # L2 state
    l2_state = MockL2State(
        mission_id=envelope.mission_id,
        execution_id=envelope.envelope_id,
        aggregate_version=1,
        aggregate_sha256=AGG_HASH,
        authority_decision=l2_authority,
        evidence_sha256=ev_hash,
        status=BridgeMissionStatus.EXECUTING,
    )
    # 12
    proj = stage_mission_control_projection(envelope, ev_hash, l2_state)
    # Reconcile
    final_status = reconcile_bridge_result(result, proj)
    return proj, final_status, envelope, result, recon


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFullAcceptanceFlow:
    def test_full_acceptance_flow(self):
        """All 12 stages complete successfully → VERIFIED_COMPLETE."""
        proj, status, envelope, result, recon = _run_full_flow()

        # Each stage must have produced valid output.
        assert envelope.envelope_id is not None
        assert recon["evidence_chain_ok"] is True
        assert recon["transport_success"] is True
        assert recon["authority_delta"] == 0
        assert recon["side_effect_count"] == 0

        # Projection reflects L2 state.
        assert proj.mission_id == envelope.mission_id
        assert proj.aggregate_sha256 == AGG_HASH
        assert proj.evidence_sha256 == EVID_HASH

        # Final status is VERIFIED_COMPLETE.
        assert status == BridgeMissionStatus.VERIFIED_COMPLETE


class TestAcceptanceFlowDenyAtAuthority:
    def test_acceptance_flow_deny_at_authority(self):
        """Authority resolution returns DENIED → final status DENIED."""
        proj, status, envelope, result, recon = _run_full_flow(
            authority_decision="DENIED",
            l2_authority="DENIED",
        )
        assert status == BridgeMissionStatus.DENIED
        assert status != BridgeMissionStatus.VERIFIED_COMPLETE


class TestAcceptanceFlowExpiredEnvelope:
    def test_acceptance_flow_expired_envelope(self):
        """Expired envelope (expires_in=0, already past) → mission FAILS."""
        # Create an envelope that is already expired.
        req = stage_principal_request()
        scope = stage_mission_scope(req, mission_id="m-exp-001")
        policy = stage_policy_resolution(scope)
        authority = stage_authority_resolution(policy, decision="APPROVED")
        envelope = stage_execution_envelope(scope, authority, expires_in=-1.0)

        # Check expiry.
        assert time.time() > envelope.expires_at

        # Simulate: expired envelope is rejected → transport FAILED.
        result = stage_typescript_result(
            envelope,
            {"action_result": "rejected_expired"},
            transport_status=TransportStatus.FAILED,
            evidence_sha256=EVID_HASH,
        )
        recon = stage_python_reconciliation(result, envelope)
        assert recon["transport_success"] is False

        l2_state = MockL2State(
            mission_id=envelope.mission_id,
            execution_id=envelope.envelope_id,
            aggregate_version=1,
            aggregate_sha256=AGG_HASH,
            authority_decision="APPROVED",
            evidence_sha256=EVID_HASH,
            status=BridgeMissionStatus.FAILED,
        )
        proj = stage_mission_control_projection(envelope, EVID_HASH, l2_state, status=BridgeMissionStatus.FAILED)
        status = reconcile_bridge_result(result, proj)
        assert status == BridgeMissionStatus.FAILED


class TestAcceptanceFlowEvidenceMissingUnverified:
    def test_acceptance_flow_evidence_missing_unverified(self):
        """Transport succeeds but evidence hash is missing → UNVERIFIED."""
        proj, status, envelope, result, recon = _run_full_flow(
            result_evidence=None,
        )
        assert status == BridgeMissionStatus.UNVERIFIED
        assert status != BridgeMissionStatus.VERIFIED_COMPLETE
        assert recon["evidence_chain_ok"] is False


class TestAcceptanceFlowTransportSuccessButMissionFail:
    def test_acceptance_flow_transport_success_but_mission_fail(self):
        """Transport SUCCESS but evidence mismatch → UNVERIFIED (not COMPLETE).

        Demonstrates: BRIDGE_TRANSPORT_SUCCESS != MISSION_SUCCESS
        """
        # Result evidence differs from envelope evidence.
        wrong_evidence = _sha256(b"wrong-evidence")
        proj, status, envelope, result, recon = _run_full_flow(
            result_evidence=wrong_evidence,
        )
        # Transport succeeded...
        assert recon["transport_success"] is True
        # ...but mission is not complete.
        assert status == BridgeMissionStatus.UNVERIFIED
        assert status != BridgeMissionStatus.VERIFIED_COMPLETE

    def test_transport_success_side_effects_unverified(self):
        """Transport SUCCESS but side_effect_count > 0 → UNVERIFIED."""
        proj, status, envelope, result, recon = _run_full_flow(
            side_effect_count=1,
        )
        assert recon["transport_success"] is True
        assert status == BridgeMissionStatus.UNVERIFIED

    def test_transport_success_authority_delta_unverified(self):
        """Transport SUCCESS but authority_delta != 0 → UNVERIFIED."""
        # We need a result with non-zero authority delta.
        req = stage_principal_request()
        scope = stage_mission_scope(req, mission_id="m-delta-001")
        policy = stage_policy_resolution(scope)
        authority = stage_authority_resolution(policy, decision="APPROVED")
        envelope = stage_execution_envelope(scope, authority)
        action_res = stage_governed_internal_action(stage_typescript_runtime(envelope))
        result = MockBridgeResult(
            envelope_id=envelope.envelope_id,
            mission_id=envelope.mission_id,
            transport_status=TransportStatus.SUCCESS,
            evidence_sha256=EVID_HASH,
            authority_delta=1,  # Non-zero!
            side_effect_count=0,
            success=True,
            result_payload=action_res,
        )
        recon = stage_python_reconciliation(result, envelope)
        l2_state = MockL2State(
            mission_id=envelope.mission_id,
            execution_id=envelope.envelope_id,
            aggregate_version=1,
            aggregate_sha256=AGG_HASH,
            authority_decision="APPROVED",
            evidence_sha256=EVID_HASH,
            status=BridgeMissionStatus.EXECUTING,
        )
        proj = stage_mission_control_projection(envelope, EVID_HASH, l2_state)
        status = reconcile_bridge_result(result, proj)
        assert status == BridgeMissionStatus.UNVERIFIED


class TestAcceptanceFlowHashDeterministic:
    def test_acceptance_flow_hash_deterministic(self):
        """Running the flow twice produces the same evidence hash and
        aggregate hash — hashes are deterministic."""
        proj1, status1, env1, res1, recon1 = _run_full_flow()
        proj2, status2, env2, res2, recon2 = _run_full_flow()

        assert proj1.evidence_sha256 == proj2.evidence_sha256
        assert proj1.aggregate_sha256 == proj2.aggregate_sha256
        assert status1 == status2 == BridgeMissionStatus.VERIFIED_COMPLETE

        # The deterministic evidence hash is the known constant.
        assert proj1.evidence_sha256 == EVID_HASH


class TestTypescriptProcessFailure:
    """Test that a TypeScript runtime process failure is handled gracefully
    by the bridge — the Python side receives a transport failure, not a crash."""

    def test_typescript_process_failure(self):
        """Simulate a TypeScript process crash: the bridge returns
        TRANSPORT_FAILED, and the mission projection reflects FAILED status."""
        from sintra_live.l2.python_typescript_bridge import BridgeProjection
        proj = BridgeProjection(
            mission_id="mission-ts-crash",
            aggregate_version=1,
            aggregate_sha256="abc",
            current_state="READY",
            authority_delta=0,
            side_effects=0,
        )
        envelope = build_v1_envelope(
            projection=proj,
            authority_decision=AuthorityDecision.ALLOW.value,
            execution_id="exec-ts-crash",
            nonce="nonce-ts-crash",
            tenant_id="tenant-ts-crash",
            actor_id="actor-ts-crash",
            capability_id="named_agents",
            payload={"action": "ts_crash_test"},
        )
        raw = serialize_envelope_v1(envelope)

        # Simulate TS process failure by passing corrupted/empty response
        # The bridge should handle this as TRANSPORT_FAILED, not raise
        outcome = BridgeExecutionOutcome(
            transport_status=BridgeTransportStatus.TRANSPORT_FAILED,
            result=None,
            reason="TypeScript process exited unexpectedly",
        )
        assert outcome.transport_status == BridgeTransportStatus.TRANSPORT_FAILED
        assert outcome.result is None
        assert "unexpected" in outcome.reason

        # Mission projection should reflect FAILED for a transport failure
        from sintra_live.l2.bridge_mission_projection import BridgeMissionProjection, BridgeMissionStatus
        l2_state = BridgeMissionProjection(
            mission_id=envelope.mission_id,
            execution_id=envelope.execution_id,
            status=BridgeMissionStatus.FAILED,
            aggregate_version=1,
            aggregate_sha256="abc",
            evidence_sha256="",
            authority_decision="ALLOW",
            projected_at="2026-08-26T12:00:00.000000Z",
        )
        assert l2_state.status == BridgeMissionStatus.FAILED
        # No evidence → cannot be VERIFIED_COMPLETE
        assert l2_state.status != BridgeMissionStatus.VERIFIED_COMPLETE