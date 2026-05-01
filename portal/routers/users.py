"""User management router (admin)."""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from ..auth.password_handler import generate_secure_password, hash_password
from ..auth.rbac import CurrentUser, Permission, require_permissions
from ..auth.session_manager import revoke_all_user_sessions
from ..config import get_settings
from ..database import get_db
from ..models.user import User
from ..schemas.user import (
    SessionResponse,
    UserInvite,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from ..services.audit_service import audit
from ..services.notification_service import send_email

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
settings = get_settings()


@router.get("", response_model=UserListResponse)
async def list_users(
    search: str | None = Query(None),
    role: str | None = Query(None),
    is_active: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_permissions(Permission.USER_READ)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(
        User.tenant_id == current_user.tenant_id,
        User.deleted_at.is_(None),
    )
    if search:
        from sqlalchemy import or_
        stmt = stmt.where(or_(
            User.email.ilike(f"%{search}%"),
            User.first_name.ilike(f"%{search}%"),
            User.last_name.ilike(f"%{search}%"),
        ))
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)

    total_q = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_q.scalar() or 0
    pages = (total + page_size - 1) // page_size

    stmt = stmt.offset((page-1)*page_size).limit(page_size).order_by(User.created_at.desc())
    result = await db.execute(stmt)
    users = result.scalars().all()

    return UserListResponse(
        items=[UserResponse.from_orm_with_role(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("/invite", response_model=UserResponse, status_code=201)
async def invite_user(
    body: UserInvite,
    current_user: CurrentUser = Depends(require_permissions(Permission.USER_INVITE)),
    db: AsyncSession = Depends(get_db),
):
    # Check duplicate
    existing = await db.execute(
        select(User).where(
            User.email == body.email.lower(),
            User.tenant_id == current_user.tenant_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User already exists")

    # Find role
    from ..models.user import Role as RoleModel
    role_result = await db.execute(select(RoleModel).where(RoleModel.name == body.role))
    role_obj = role_result.scalar_one_or_none()
    if not role_obj:
        raise HTTPException(status_code=400, detail=f"Invalid role: {body.role}")

    invite_token = secrets.token_urlsafe(32)
    temp_password = generate_secure_password(20)

    user = User(
        tenant_id=current_user.tenant_id,
        role_id=role_obj.id,
        email=body.email.lower(),
        first_name=body.first_name,
        last_name=body.last_name,
        hashed_password=hash_password(temp_password),
        invite_token=invite_token,
        is_active=True,
        email_verified=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    if body.send_welcome_email:
        invite_url = f"{settings.BASE_URL}/auth/accept-invite?token={invite_token}"
        await send_email(
            to=user.email,
            subject="You've been invited to SintraPrime Portal",
            body=f"Hello {user.full_name},\n\nYou've been invited to join the portal.\n\nClick here to set your password: {invite_url}\n\nLink expires in 7 days.",
        )

    await audit(db, action="user_invite", user_id=current_user.user_id,
                tenant_id=current_user.tenant_id,
                resource_type="user", resource_id=str(user.id), resource_name=user.email)
    return UserResponse.from_orm_with_role(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permissions(Permission.USER_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404)
    return UserResponse.from_orm_with_role(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    current_user: CurrentUser = Depends(require_permissions(Permission.USER_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == current_user.tenant_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    await audit(db, action="user_update", user_id=current_user.user_id,
                tenant_id=current_user.tenant_id, resource_type="user", resource_id=str(user_id))
    return UserResponse.from_orm_with_role(user)


@router.post("/{user_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permissions(Permission.USER_DELETE)),
    db: AsyncSession = Depends(get_db),
):
    if str(user_id) == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == current_user.tenant_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404)

    user.is_active = False
    await db.commit()
    await revoke_all_user_sessions(str(user_id))
    await audit(db, action="user_deactivate", user_id=current_user.user_id,
                tenant_id=current_user.tenant_id, resource_type="user", resource_id=str(user_id))


@router.post("/{user_id}/change-role", response_model=UserResponse)
async def change_user_role(
    user_id: uuid.UUID,
    role: str,
    current_user: CurrentUser = Depends(require_permissions(Permission.USER_MANAGE_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == current_user.tenant_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404)

    from ..models.user import Role as RoleModel
    role_result = await db.execute(select(RoleModel).where(RoleModel.name == role))
    role_obj = role_result.scalar_one_or_none()
    if not role_obj:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")

    user.role_id = role_obj.id
    await db.commit()

    # Revoke sessions to force re-login with new role
    await revoke_all_user_sessions(str(user_id))
    await audit(db, action="role_change", user_id=current_user.user_id,
                tenant_id=current_user.tenant_id,
                resource_type="user", resource_id=str(user_id),
                details={"new_role": role})
    await db.refresh(user)
    return UserResponse.from_orm_with_role(user)


@router.get("/{user_id}/sessions", response_model=list[SessionResponse])
async def get_user_sessions(
    user_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permissions(Permission.USER_READ)),
    db: AsyncSession = Depends(get_db),
):
    from ..auth.session_manager import get_user_sessions
    sessions = await get_user_sessions(str(user_id))
    return [SessionResponse(**s) for s in sessions]
