"""System administration router — firm statistics, health, API keys, branding."""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select

from ..auth.rbac import CurrentUser, Permission, Role, require_permissions, require_role
from ..database import check_db_connection, get_db
from ..models.audit import AuditLog
from ..models.billing import Invoice
from ..models.case import Case
from ..models.client import Client
from ..models.document import Document
from ..models.user import Tenant, User
from ..services.audit_service import audit

if TYPE_CHECKING:
    import uuid
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


# ── Dashboard stats ───────────────────────────────────────────────────────────

class FirmStats(BaseModel):
    total_users: int
    active_users: int
    total_clients: int
    active_clients: int
    total_cases: int
    open_cases: int
    total_documents: int
    storage_used_gb: float
    outstanding_invoices: float
    recent_activity_count: int


@router.get("/stats", response_model=FirmStats)
async def get_firm_stats(
    current_user: CurrentUser = Depends(require_permissions(Permission.ADMIN_DASHBOARD)),
    db: AsyncSession = Depends(get_db),
):
    tid = current_user.tenant_id

    users_q = await db.execute(select(func.count(User.id)).where(User.tenant_id == tid, User.deleted_at.is_(None)))
    active_users_q = await db.execute(select(func.count(User.id)).where(User.tenant_id == tid, User.is_active, User.deleted_at.is_(None)))
    clients_q = await db.execute(select(func.count(Client.id)).where(Client.tenant_id == tid, Client.deleted_at.is_(None)))
    active_clients_q = await db.execute(select(func.count(Client.id)).where(Client.tenant_id == tid, Client.status == "active", Client.deleted_at.is_(None)))
    cases_q = await db.execute(select(func.count(Case.id)).where(Case.tenant_id == tid, Case.deleted_at.is_(None)))
    open_cases_q = await db.execute(select(func.count(Case.id)).where(Case.tenant_id == tid, Case.stage.not_in(["closed", "archived"]), Case.deleted_at.is_(None)))
    docs_q = await db.execute(select(func.count(Document.id)).where(Document.tenant_id == tid, Document.deleted_at.is_(None)))
    storage_q = await db.execute(select(func.sum(Document.size_bytes)).where(Document.tenant_id == tid, Document.deleted_at.is_(None)))
    outstanding_q = await db.execute(select(func.sum(Invoice.amount_due)).where(Invoice.tenant_id == tid, Invoice.status.in_(["sent", "partial", "overdue"])))
    activity_q = await db.execute(select(func.count(AuditLog.id)).where(AuditLog.tenant_id == tid))

    storage_bytes = storage_q.scalar() or 0
    storage_gb = round(storage_bytes / (1024 ** 3), 3)

    return FirmStats(
        total_users=users_q.scalar() or 0,
        active_users=active_users_q.scalar() or 0,
        total_clients=clients_q.scalar() or 0,
        active_clients=active_clients_q.scalar() or 0,
        total_cases=cases_q.scalar() or 0,
        open_cases=open_cases_q.scalar() or 0,
        total_documents=docs_q.scalar() or 0,
        storage_used_gb=storage_gb,
        outstanding_invoices=float(outstanding_q.scalar() or 0),
        recent_activity_count=activity_q.scalar() or 0,
    )


# ── Audit log ─────────────────────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    actor_email: str | None = None
    actor_role: str | None = None
    actor_ip: str | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    status: str
    details: dict | None = None
    http_method: str | None = None
    http_path: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/audit-log")
async def get_audit_log(
    action: str | None = None,
    user_id: uuid.UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 50,
    current_user: CurrentUser = Depends(require_permissions(Permission.ADMIN_AUDIT_LOG)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AuditLog).where(AuditLog.tenant_id == current_user.tenant_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if date_from:
        stmt = stmt.where(AuditLog.created_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditLog.created_at <= date_to)

    total_q = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_q.scalar() or 0

    stmt = stmt.offset((page-1)*page_size).limit(page_size).order_by(AuditLog.created_at.desc())
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return {
        "items": [AuditLogResponse.model_validate(log) for log in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ── API keys ──────────────────────────────────────────────────────────────────

class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    created_at: str
    last_used_at: str | None = None
    is_active: bool


@router.post("/api-keys")
async def create_api_key(
    name: str,
    current_user: CurrentUser = Depends(require_permissions(Permission.ADMIN_API_KEYS)),
    db: AsyncSession = Depends(get_db),
):
    """Generate an API key for server-to-server integration."""
    raw_key = f"sp_{secrets.token_urlsafe(40)}"
    key_prefix = raw_key[:12]
    hash_password_for_key(raw_key)

    await audit(db, action="api_key_create", user_id=current_user.user_id,
                tenant_id=current_user.tenant_id,
                details={"name": name, "prefix": key_prefix})

    return {
        "key": raw_key,  # Only shown once!
        "prefix": key_prefix,
        "name": name,
        "warning": "Save this key — it will not be shown again.",
    }


def hash_password_for_key(key: str) -> str:
    from ..auth.password_handler import hash_password
    return hash_password(key)


# ── Branding ──────────────────────────────────────────────────────────────────

class BrandingUpdate(BaseModel):
    logo_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    firm_name: str | None = None


@router.put("/branding")
async def update_branding(
    body: BrandingUpdate,
    current_user: CurrentUser = Depends(require_permissions(Permission.ADMIN_BRANDING)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404)

    if body.logo_url is not None:
        tenant.logo_url = body.logo_url
    if body.primary_color is not None:
        tenant.primary_color = body.primary_color
    if body.secondary_color is not None:
        tenant.secondary_color = body.secondary_color
    if body.firm_name is not None:
        tenant.name = body.firm_name

    await db.commit()
    await audit(db, action="branding_update", user_id=current_user.user_id,
                tenant_id=current_user.tenant_id)
    return {"message": "Branding updated successfully"}


# ── System health (SUPER_ADMIN only) ─────────────────────────────────────────

@router.get("/system-health")
async def system_health(
    current_user: CurrentUser = Depends(require_role(Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    db_ok = await check_db_connection()
    return {
        "database": "healthy" if db_ok else "unhealthy",
        "environment": "production",
        "version": "1.0.0",
    }


# ── Storage quota ─────────────────────────────────────────────────────────────

@router.get("/storage-usage")
async def storage_usage(
    current_user: CurrentUser = Depends(require_permissions(Permission.ADMIN_QUOTA)),
    db: AsyncSession = Depends(get_db),
):

    # Per-client storage usage
    result = await db.execute(
        select(
            Document.client_id,
            func.count(Document.id).label("doc_count"),
            func.sum(Document.size_bytes).label("total_bytes"),
        )
        .where(Document.tenant_id == current_user.tenant_id, Document.deleted_at.is_(None))
        .group_by(Document.client_id)
        .order_by(func.sum(Document.size_bytes).desc())
        .limit(50)
    )
    rows = result.all()

    usage_list = []
    for row in rows:
        usage_list.append({
            "client_id": str(row.client_id) if row.client_id else None,
            "document_count": row.doc_count,
            "storage_bytes": row.total_bytes or 0,
            "storage_gb": round((row.total_bytes or 0) / (1024 ** 3), 4),
        })

    return {"by_client": usage_list}
