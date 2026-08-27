"""
Mission Control Projection for Bridge-mediated missions.

This module provides a READ-ONLY projection of L2 mission state for
the mission control bridge. The L2 store is the ONLY state machine;
the projection merely reflects it truthfully.

Design rules:
  - Projection is READ-ONLY — never mutates L2 state.
  - Projection MUST match L2 store.
  - BRIDGE_TRANSPORT_SUCCESS != MISSION_SUCCESS
  - MISSION_SUCCESS_WITHOUT_REQUIRED_EVIDENCE = UNVERIFIED
  - UNVERIFIED != COMPLETE
"""

from __future__ import annotations

import hmac
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class BridgeMissionStatus(str, Enum):
    """Canonical status for a bridge-mediated mission."""
    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    VERIFIED_COMPLETE = "VERIFIED_COMPLETE"
    UNVERIFIED = "UNVERIFIED"
    FAILED = "FAILED"
    DENIED = "DENIED"


@dataclass(frozen=True)
class BridgeMissionProjection:
    """
    Read-only projection of a mission's state as seen by mission control.

    Attributes:
        mission_id:         The canonical mission identity string.
        execution_id:       Unique execution / envelope identifier.
        status:             Current BridgeMissionStatus.
        aggregate_version:  Version of the aggregate (L2 state) this projection reflects.
        aggregate_sha256:   SHA-256 of the canonical aggregate bytes at projection time.
        evidence_sha256:    SHA-256 of the evidence hash chain (envelope + result evidence).
        authority_decision: The authority decision applied (e.g. "APPROVED", "DENIED", None).
        projected_at:       Unix timestamp (float) when the projection was created.
    """
    mission_id: str
    execution_id: str
    status: BridgeMissionStatus
    aggregate_version: int
    aggregate_sha256: str
    evidence_sha256: Optional[str]
    authority_decision: Optional[str]
    projected_at: float = field(default_factory=time.time)


def project_mission_for_bridge(
    mission_id: str,
    execution_id: str,
    aggregate_version: int,
    aggregate_sha256: str,
    authority_decision: Optional[str] = None,
    evidence_sha256: Optional[str] = None,
    status: BridgeMissionStatus = BridgeMissionStatus.PENDING,
) -> BridgeMissionProjection:
    """
    Create a read-only BridgeMissionProjection from the current L2 state.

    The caller is responsible for reading the L2 store and passing the
    *current* aggregate version, aggregate hash, and evidence hash.
    This function does NOT touch the store — it only packages the values.

    Returns:
        BridgeMissionProjection with the supplied values and a fresh timestamp.
    """
    return BridgeMissionProjection(
        mission_id=mission_id,
        execution_id=execution_id,
        status=status,
        aggregate_version=aggregate_version,
        aggregate_sha256=aggregate_sha256,
        evidence_sha256=evidence_sha256,
        authority_decision=authority_decision,
        projected_at=time.time(),
    )


def verify_evidence_chain(
    envelope_evidence_sha256: Optional[str],
    result_evidence_sha256: Optional[str],
) -> bool:
    """
    Verify that the evidence hash chain is intact.

    Both the envelope's evidence hash and the result's evidence hash
    must be present and must match. If either is missing or they differ,
    the evidence chain is broken.

    Returns:
        True if both hashes are present and equal, False otherwise.
    """
    if envelope_evidence_sha256 is None or result_evidence_sha256 is None:
        return False
    if envelope_evidence_sha256 == "" or result_evidence_sha256 == "":
        return False
    # Constant-time comparison to avoid timing attacks on hash equality.
    return hmac.compare_digest(envelope_evidence_sha256, result_evidence_sha256)


def reconcile_bridge_result(
    result: Any,
    projection: BridgeMissionProjection,
) -> BridgeMissionStatus:
    """
    Reconcile a BridgeResultV1 against the current projection to determine
    the canonical mission status.

    Reconciliation checks (all must pass for VERIFIED_COMPLETE):
      1. Evidence hash chain is intact (envelope evidence == result evidence).
      2. Authority delta is zero (authority was not escalated or degraded).
      3. No unexpected side effects (side_effect_count == 0).
      4. The transport/execution outcome was successful.

    If transport succeeded but evidence is missing/mismatched → UNVERIFIED.
    If authority denied the mission → DENIED.
    If any other failure → FAILED.

    Args:
        result:     A BridgeResultV1 (or compatible object) with attributes:
                    evidence_sha256, authority_delta, side_effect_count,
                    and a transport status / success indicator.
        projection: The current BridgeMissionProjection.

    Returns:
        The reconciled BridgeMissionStatus.
    """
    # If the projection already says DENIED, honour that.
    if projection.status == BridgeMissionStatus.DENIED:
        return BridgeMissionStatus.DENIED

    # Extract fields from the result object defensively.
    result_evidence_sha256 = getattr(result, "evidence_sha256", None)
    authority_delta = getattr(result, "authority_delta", None)
    side_effect_count = getattr(result, "side_effect_count", None)

    # Determine transport/execution success.
    # BridgeResultV1 may carry a 'transport_status' or 'success' attribute.
    transport_status = getattr(result, "transport_status", None)
    success_flag = getattr(result, "success", None)

    transport_success = False
    if transport_status is not None:
        # BridgeTransportStatus.SUCCESS or string "SUCCESS"
        ts_val = getattr(transport_status, "value", transport_status)
        transport_success = (ts_val == "SUCCESS")
    elif success_flag is not None:
        transport_success = bool(success_flag)
    else:
        # If we cannot determine transport status, check an 'outcome' field.
        outcome = getattr(result, "outcome", None)
        if outcome is not None:
            oc_val = getattr(outcome, "value", outcome)
            transport_success = (oc_val == "SUCCESS")

    # --- Denial check ---
    if projection.authority_decision is not None:
        decision_val = projection.authority_decision
        if hasattr(decision_val, "value"):
            decision_val = decision_val.value
        decision_upper = str(decision_val).upper()
        if decision_upper in ("DENIED", "DENY", "REJECTED"):
            return BridgeMissionStatus.DENIED

    # --- Transport failure → FAILED ---
    if not transport_success:
        return BridgeMissionStatus.FAILED

    # --- Evidence chain verification ---
    # The projection's evidence_sha256 is the envelope-side evidence hash.
    chain_ok = verify_evidence_chain(
        projection.evidence_sha256,
        result_evidence_sha256,
    )
    if not chain_ok:
        # Transport succeeded but evidence is missing or mismatched.
        return BridgeMissionStatus.UNVERIFIED

    # --- Authority delta must be zero ---
    if authority_delta is not None and authority_delta != 0:
        return BridgeMissionStatus.UNVERIFIED

    # --- No unexpected side effects ---
    if side_effect_count is not None and side_effect_count != 0:
        return BridgeMissionStatus.UNVERIFIED

    # --- All checks passed ---
    return BridgeMissionStatus.VERIFIED_COMPLETE