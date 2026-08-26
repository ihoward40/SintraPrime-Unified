"""
Tests for bridge_mission_projection.py — Mission Control projection layer.

Verifies:
  - Projection matches L2 state
  - Mismatched aggregate hash is rejected
  - Bridge result reconciliation pass/fail
  - Evidence chain verification
  - UNVERIFIED != COMPLETE
  - DENIED status
  - Projection does not mutate state
"""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass
from typing import Any, Optional

import pytest

from sintra_live.l2.bridge_mission_projection import (
    BridgeMissionProjection,
    BridgeMissionStatus,
    project_mission_for_bridge,
    reconcile_bridge_result,
    verify_evidence_chain,
)


# ---------------------------------------------------------------------------
# Helper fakes
# ---------------------------------------------------------------------------

@dataclass
class FakeBridgeResult:
    """Minimal stand-in for BridgeResultV1."""
    evidence_sha256: Optional[str]
    authority_delta: int = 0
    side_effect_count: int = 0
    transport_status: str = "SUCCESS"
    success: bool = True


AGG_HASH_A = "a" * 64
AGG_HASH_B = "b" * 64
EVID_HASH_OK = "e" * 64


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestProjectionMatchesL2State:
    def test_projection_matches_l2_state(self):
        """Projection fields must match the L2 state values supplied."""
        proj = project_mission_for_bridge(
            mission_id="m-001",
            execution_id="exec-001",
            aggregate_version=3,
            aggregate_sha256=AGG_HASH_A,
            authority_decision="APPROVED",
            evidence_sha256=EVID_HASH_OK,
            status=BridgeMissionStatus.EXECUTING,
        )
        assert proj.mission_id == "m-001"
        assert proj.execution_id == "exec-001"
        assert proj.aggregate_version == 3
        assert proj.aggregate_sha256 == AGG_HASH_A
        assert proj.evidence_sha256 == EVID_HASH_OK
        assert proj.authority_decision == "APPROVED"
        assert proj.status == BridgeMissionStatus.EXECUTING


class TestProjectionRejectsMismatchedAggregateHash:
    def test_projection_rejects_mismatched_aggregate_hash(self):
        """If the aggregate hash differs, the projection must not claim to
        represent the same L2 state."""
        proj_a = project_mission_for_bridge(
            mission_id="m-002",
            execution_id="exec-002",
            aggregate_version=1,
            aggregate_sha256=AGG_HASH_A,
        )
        proj_b = project_mission_for_bridge(
            mission_id="m-002",
            execution_id="exec-002",
            aggregate_version=1,
            aggregate_sha256=AGG_HASH_B,
        )
        assert proj_a.aggregate_sha256 != proj_b.aggregate_sha256
        # A projection with the wrong hash must not equal the correct one.
        assert proj_a != proj_b


class TestBridgeResultReconciliation:
    def test_bridge_result_reconciliation_pass(self):
        """When evidence, authority delta, and side effects all check out,
        reconciliation returns VERIFIED_COMPLETE."""
        proj = project_mission_for_bridge(
            mission_id="m-003",
            execution_id="exec-003",
            aggregate_version=2,
            aggregate_sha256=AGG_HASH_A,
            authority_decision="APPROVED",
            evidence_sha256=EVID_HASH_OK,
            status=BridgeMissionStatus.EXECUTING,
        )
        result = FakeBridgeResult(
            evidence_sha256=EVID_HASH_OK,
            authority_delta=0,
            side_effect_count=0,
            transport_status="SUCCESS",
        )
        status = reconcile_bridge_result(result, proj)
        assert status == BridgeMissionStatus.VERIFIED_COMPLETE

    def test_bridge_result_reconciliation_fail(self):
        """Transport failure → FAILED."""
        proj = project_mission_for_bridge(
            mission_id="m-004",
            execution_id="exec-004",
            aggregate_version=2,
            aggregate_sha256=AGG_HASH_A,
            authority_decision="APPROVED",
            evidence_sha256=EVID_HASH_OK,
            status=BridgeMissionStatus.EXECUTING,
        )
        result = FakeBridgeResult(
            evidence_sha256=EVID_HASH_OK,
            authority_delta=0,
            side_effect_count=0,
            transport_status="FAILED",
            success=False,
        )
        status = reconcile_bridge_result(result, proj)
        assert status == BridgeMissionStatus.FAILED


class TestEvidenceChainVerification:
    def test_evidence_chain_verification(self):
        """Evidence chain is valid when both hashes are present and equal."""
        assert verify_evidence_chain(EVID_HASH_OK, EVID_HASH_OK) is True
        assert verify_evidence_chain(EVID_HASH_OK, "f" * 64) is False
        assert verify_evidence_chain(None, EVID_HASH_OK) is False
        assert verify_evidence_chain(EVID_HASH_OK, None) is False
        assert verify_evidence_chain("", "") is False


class TestUnverifiedNotComplete:
    def test_unverified_not_complete(self):
        """Transport success but mismatched evidence → UNVERIFIED, not COMPLETE."""
        proj = project_mission_for_bridge(
            mission_id="m-005",
            execution_id="exec-005",
            aggregate_version=1,
            aggregate_sha256=AGG_HASH_A,
            authority_decision="APPROVED",
            evidence_sha256=EVID_HASH_OK,
            status=BridgeMissionStatus.EXECUTING,
        )
        # Result has a different evidence hash.
        result = FakeBridgeResult(
            evidence_sha256="x" * 64,
            authority_delta=0,
            side_effect_count=0,
            transport_status="SUCCESS",
        )
        status = reconcile_bridge_result(result, proj)
        assert status == BridgeMissionStatus.UNVERIFIED
        assert status != BridgeMissionStatus.VERIFIED_COMPLETE

    def test_unverified_when_evidence_missing(self):
        """Transport success but no evidence hash on result → UNVERIFIED."""
        proj = project_mission_for_bridge(
            mission_id="m-005b",
            execution_id="exec-005b",
            aggregate_version=1,
            aggregate_sha256=AGG_HASH_A,
            authority_decision="APPROVED",
            evidence_sha256=EVID_HASH_OK,
            status=BridgeMissionStatus.EXECUTING,
        )
        result = FakeBridgeResult(
            evidence_sha256=None,
            authority_delta=0,
            side_effect_count=0,
            transport_status="SUCCESS",
        )
        status = reconcile_bridge_result(result, proj)
        assert status == BridgeMissionStatus.UNVERIFIED


class TestDeniedMissionStatus:
    def test_denied_mission_status(self):
        """Authority DENIED → projection status DENIED and reconciliation
        preserves it."""
        proj = project_mission_for_bridge(
            mission_id="m-006",
            execution_id="exec-006",
            aggregate_version=1,
            aggregate_sha256=AGG_HASH_A,
            authority_decision="DENIED",
            evidence_sha256=EVID_HASH_OK,
            status=BridgeMissionStatus.DENIED,
        )
        result = FakeBridgeResult(
            evidence_sha256=EVID_HASH_OK,
            authority_delta=0,
            side_effect_count=0,
            transport_status="SUCCESS",
        )
        status = reconcile_bridge_result(result, proj)
        assert status == BridgeMissionStatus.DENIED


class TestProjectionNoStateMutation:
    def test_projection_no_state_mutation(self):
        """project_mission_for_bridge must not mutate any external state —
        it is a pure function that only packages values."""
        # Use a simple dict to represent "L2 state".
        l2_state = {
            "mission_id": "m-007",
            "execution_id": "exec-007",
            "aggregate_version": 5,
            "aggregate_sha256": AGG_HASH_A,
            "authority_decision": "APPROVED",
            "evidence_sha256": EVID_HASH_OK,
        }
        original = copy.deepcopy(l2_state)

        proj = project_mission_for_bridge(
            mission_id=l2_state["mission_id"],
            execution_id=l2_state["execution_id"],
            aggregate_version=l2_state["aggregate_version"],
            aggregate_sha256=l2_state["aggregate_sha256"],
            authority_decision=l2_state["authority_decision"],
            evidence_sha256=l2_state["evidence_sha256"],
        )

        # L2 state must be unchanged.
        assert l2_state == original
        # Projection is frozen (immutable).
        with pytest.raises((AttributeError, Exception)):
            proj.status = BridgeMissionStatus.FAILED  # type: ignore[misc]