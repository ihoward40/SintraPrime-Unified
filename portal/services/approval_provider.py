"""
Approval Provider Abstraction (G4.6 Stabilization).

Defines the protocol for approval resolution in the execution guard.
Production uses PersistedApprovalProvider (queries the Approval table).
Tests inject TestApprovalProvider (explicit allowlist, deny-by-default).

This module exists because non-mission-scoped actions (kill_switch.clear,
identity.action) cannot obtain persisted approval — the Approval model
requires a non-nullable mission_id FK. Until G4.8 implements system-scoped
approvals, the provider interface allows tests to proceed without embedding
bypass logic in the production guard.

Design constraints:
  - ExecutionGuard contains NO environment-variable checks for approval bypass.
  - TestApprovalProvider is NEVER imported by production composition.
  - Production always uses PersistedApprovalProvider.
  - ApprovalResolution is immutable (frozen dataclass).
  - The provider receives full context (action, mission_id, gate, principal)
    and returns a structured decision — it does NOT mutate state.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Approval Resolution
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ApprovalResolution:
    """Immutable result of an approval resolution query.

    Attributes:
        approved: Whether the action is approved.
        approval_id: ID of the approval record, if one was found.
        scope: The approval scope (e.g. 'mission', 'system', 'identity').
            None means scope was not applicable or not determined.
        reason: Human-readable reason for the decision.
    """
    approved: bool
    approval_id: Optional[str] = None
    scope: Optional[str] = None
    reason: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# Approval Provider Protocol
# ═══════════════════════════════════════════════════════════════════════════════

@runtime_checkable
class ApprovalProvider(Protocol):
    """Protocol for approval resolution.

    Implementations receive full action context and return an
    ApprovalResolution. The guard uses this result to decide whether
    the action may proceed.

    Production composition: PersistedApprovalProvider
    Test composition: TestApprovalProvider (never imported by production)
    """

    async def resolve(
        self,
        *,
        session: AsyncSession,
        action: str,
        mission_id: Optional[str],
        governance_gate: Optional[str],
        principal_context: object,  # PrincipalContext — avoids circular import
    ) -> ApprovalResolution:
        ...


# ═══════════════════════════════════════════════════════════════════════════════
# Production Provider — PersistedApprovalProvider
# ═══════════════════════════════════════════════════════════════════════════════

class PersistedApprovalProvider:
    """Production approval provider.

    Queries the persisted Approval table in the database.

    Mission-scoped actions:
      - Looks up Approval records matching mission_id and governance_gate.
      - Returns approved=True only if a valid APPROVED-status record exists.
      - Fails closed on query errors.

    Non-mission-scoped actions (mission_id is None):
      - Returns not approved with reason 'non_mission_approval_not_implemented'.
      - This is a known gap documented in NON_MISSION_APPROVAL_GAP.md.
      - G4.8 will implement system-scoped approvals.
      - Never synthesizes approval.
    """

    async def resolve(
        self,
        *,
        session: AsyncSession,
        action: str,
        mission_id: Optional[str],
        governance_gate: Optional[str],
        principal_context: object,
    ) -> ApprovalResolution:
        from portal.models.observatory import Approval

        # ── Non-mission-scoped action: no mechanism to approve ──
        if not mission_id:
            return ApprovalResolution(
                approved=False,
                scope=None,
                reason=(
                    f"Non-mission action '{action}' cannot be approved: "
                    "no system-scoped approval mechanism exists "
                    "(see NON_MISSION_APPROVAL_GAP.md)"
                ),
            )

        # ── Mission-scoped action: query persisted approvals ──
        try:
            mid = uuid.UUID(mission_id) if isinstance(mission_id, str) else mission_id
        except (ValueError, AttributeError):
            return ApprovalResolution(
                approved=False,
                scope="mission",
                reason=f"Invalid mission_id format: {mission_id}",
            )

        try:
            result = await session.execute(
                select(Approval).where(
                    Approval.mission_id == mid,
                    Approval.status == "APPROVED",
                )
            )
            approvals = result.scalars().all()
        except Exception as e:
            logger.error(
                "PersistedApprovalProvider.query_failed action=%s mission=%s error=%s",
                action, mission_id, e,
            )
            # Fail closed on query errors
            return ApprovalResolution(
                approved=False,
                scope="mission",
                reason=f"Unable to query approval state; failing closed: {e}",
            )

        for a in approvals:
            if governance_gate and a.gate and a.gate != governance_gate:
                continue
            if a.status == "APPROVED":
                return ApprovalResolution(
                    approved=True,
                    approval_id=str(a.id),
                    scope="mission",
                    reason=f"Approved by approval {a.id}",
                )

        return ApprovalResolution(
            approved=False,
            scope="mission",
            reason=(
                f"No approved {governance_gate or ''} approval found "
                f"for mission {mission_id}"
            ),
        )