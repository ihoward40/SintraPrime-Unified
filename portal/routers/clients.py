"""Client management router."""

from __future__ import annotations

import uuid
from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.rbac import CurrentUser, Permission, require_permissions
from ..database import get_db
from ..models.client import Client, Matter
from ..schemas.client import (
    ClientCreate,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
    MatterCreate,
    MatterResponse,
)
from ..services.audit_service import audit

router = APIRouter()


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    body: ClientCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.CLIENT_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    client = Client(
        tenant_id=current_user.tenant_id,
        **body.model_dump(),
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    await audit(db, action="client_create", user_id=current_user.user_id,
                tenant_id=current_user.tenant_id,
                resource_type="client", resource_id=str(client.id),
                resource_name=client.display_name)
    return ClientResponse.model_validate(client)


@router.get("", response_model=ClientListResponse)
async def list_clients(
    search: str | None = Query(None),
    status: str | None = Query(None),
    attorney_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_permissions(Permission.CLIENT_READ)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Client).where(
        Client.tenant_id == current_user.tenant_id,
        Client.deleted_at.is_(None),
    )
    if search:
        stmt = stmt.where(or_(
            Client.first_name.ilike(f"%{search}%"),
            Client.last_name.ilike(f"%{search}%"),
            Client.company_name.ilike(f"%{search}%"),
            Client.email.ilike(f"%{search}%"),
        ))
    if status:
        stmt = stmt.where(Client.status == status)
    if attorney_id:
        stmt = stmt.where(Client.primary_attorney_id == attorney_id)

    # CLIENT role can only see their own record
    if current_user.is_client():
        # Assuming the user's client record is linked via portal_user_id
        stmt = stmt.where(Client.portal_user_id == current_user.user_id)

    total_q = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_q.scalar() or 0

    stmt = stmt.offset((page - 1) * page_size).limit(page_size).order_by(Client.created_at.desc())
    result = await db.execute(stmt)
    clients = result.scalars().all()

    return ClientListResponse(
        items=[ClientResponse.model_validate(c) for c in clients],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permissions(Permission.CLIENT_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.tenant_id == current_user.tenant_id,
            Client.deleted_at.is_(None),
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # CLIENT role: can only see their own record
    if current_user.is_client() and str(client.portal_user_id) != current_user.user_id:
        raise HTTPException(status_code=403)

    return ClientResponse.model_validate(client)


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: uuid.UUID,
    body: ClientUpdate,
    current_user: CurrentUser = Depends(require_permissions(Permission.CLIENT_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.tenant_id == current_user.tenant_id,
            Client.deleted_at.is_(None),
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(client, field, value)
    await db.commit()
    await db.refresh(client)
    await audit(db, action="client_update", user_id=current_user.user_id,
                tenant_id=current_user.tenant_id, resource_type="client", resource_id=str(client.id))
    return ClientResponse.model_validate(client)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permissions(Permission.CLIENT_DELETE)),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.tenant_id == current_user.tenant_id,
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404)
    client.deleted_at = datetime.now(UTC)
    await db.commit()
    await audit(db, action="client_delete", user_id=current_user.user_id,
                tenant_id=current_user.tenant_id, resource_type="client", resource_id=str(client_id))


# ── Matters ───────────────────────────────────────────────────────────────────

@router.post("/{client_id}/matters", response_model=MatterResponse, status_code=201)
async def create_matter(
    client_id: uuid.UUID,
    body: MatterCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.CASE_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    body_dict = body.model_dump()
    body_dict.pop("client_id", None)

    # Auto-generate matter number
    if not body_dict.get("matter_number"):
        from datetime import datetime
        year = datetime.utcnow().year
        count_q = await db.execute(
            select(func.count(Matter.id)).where(
                Matter.tenant_id == current_user.tenant_id
            )
        )
        count = (count_q.scalar() or 0) + 1
        body_dict["matter_number"] = f"{year}-{count:04d}"

    matter = Matter(
        tenant_id=current_user.tenant_id,
        client_id=client_id,
        **body_dict,
    )
    db.add(matter)
    await db.commit()
    await db.refresh(matter)
    return MatterResponse.model_validate(matter)


@router.get("/{client_id}/matters")
async def list_matters(
    client_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permissions(Permission.CASE_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Matter).where(
            Matter.client_id == client_id,
            Matter.tenant_id == current_user.tenant_id,
            Matter.deleted_at.is_(None),
        )
    )
    return [MatterResponse.model_validate(m) for m in result.scalars().all()]
