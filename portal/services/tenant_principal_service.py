"""Tenant Principal verification service.

Read-only check: does the authenticated user hold the constitutional Principal
binding for the given tenant? Uses the durable TenantPrincipal record only;
never role inference, never Hermes OwnerProfile.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def is_tenant_principal(
    db: AsyncSession,
    *,
    authenticated_user_id: str,
    tenant_id: str,
) -> bool:
    """Fail-closed check for constitutional tenant Principal identity."""
    from portal.models.tenant_principal import TenantPrincipal

    result = await db.execute(
        select(TenantPrincipal)
        .where(TenantPrincipal.tenant_id == tenant_id)
        .where(TenantPrincipal.principal_user_id == authenticated_user_id)
    )
    principal = result.scalar_one_or_none()
    return principal is not None
