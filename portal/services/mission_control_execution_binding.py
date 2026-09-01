"""Server-owned Mission execution capability binding.

This module is the governed allow-list/policy layer between an authoritative
Mission and the DurableWorkflowEngine runtime registry. It does not register
arbitrary client workflows, become a scheduler, or grant agent authority.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.mission_control_execution import Mission


class ExecutionBindingError(ValueError):
    """Mission cannot be bound to an execution capability."""


async def resolve_mission_capability(
    db: AsyncSession,
    *,
    mission_id: str,
    tenant_id: str,
) -> str:
    """Return the server-owned execution capability bound to a Mission.

    Raises:
        ExecutionBindingError: when the Mission is missing, cross-tenant, or
            has no server-assigned capability.
    """
    mission = await db.scalar(
        select(Mission).where(
            Mission.mission_id == mission_id,
            Mission.tenant_id == tenant_id,
        )
    )
    if mission is None:
        raise ExecutionBindingError("MISSION_NOT_FOUND")
    if not mission.workflow_type:
        raise ExecutionBindingError("MISSION_CAPABILITY_UNBOUND")
    return mission.workflow_type
