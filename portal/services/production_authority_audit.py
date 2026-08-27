"""Hash-chained audit writer for the raw-schema production authority registry."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.production_authority import ProductionAuditLog


def _compute_hash(data: dict[str, Any]) -> str:
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


async def append_production_authority_audit(
    db: AsyncSession,
    *,
    action: str,
    user_id: str | None,
    tenant_id: str | None,
    resource_type: str | None,
    resource_id: str | None,
    resource_name: str | None,
    status: str,
    details: dict[str, Any] | None,
) -> ProductionAuditLog:
    """Append one immutable audit entry matching ``portal_schema.sql`` exactly."""
    stmt = select(ProductionAuditLog.entry_hash).order_by(ProductionAuditLog.created_at.desc()).limit(1)
    if tenant_id is not None:
        stmt = stmt.where(ProductionAuditLog.tenant_id == tenant_id)
    previous_hash = (await db.execute(stmt)).scalar_one_or_none()
    event_time = datetime.now(UTC)
    entry_data = {
        "action": action,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "resource_name": resource_name,
        "status": status,
        "details": details,
        "timestamp": event_time.isoformat(),
        "prev_hash": previous_hash,
    }
    entry = ProductionAuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        status=status,
        details=details,
        previous_hash=previous_hash,
        entry_hash=_compute_hash(entry_data),
        created_at=event_time,
    )
    db.add(entry)
    await db.flush()
    return entry
