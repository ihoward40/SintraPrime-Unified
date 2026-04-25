"""
Immutable, hash-chained audit log service.
Every action is recorded with: who, what, when, IP, device.
SHA-256 chain links entries for tamper detection.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.audit import AuditLog

log = structlog.get_logger()


async def audit(
    db: AsyncSession,
    action: str,
    user_id: Optional[str | uuid.UUID] = None,
    tenant_id: Optional[str | uuid.UUID] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    resource_name: Optional[str] = None,
    status: str = "success",
    details: Optional[Dict[str, Any]] = None,
    actor_email: Optional[str] = None,
    actor_role: Optional[str] = None,
    actor_ip: Optional[str] = None,
    actor_user_agent: Optional[str] = None,
    http_method: Optional[str] = None,
    http_path: Optional[str] = None,
    http_status_code: Optional[int] = None,
    error_message: Optional[str] = None,
) -> AuditLog:
    """
    Append an immutable audit entry with SHA-256 chaining.
    """
    # Get the hash of the previous entry for chain integrity
    prev_hash = await _get_last_hash(db, tenant_id)

    entry_data = {
        "action": action,
        "user_id": str(user_id) if user_id else None,
        "tenant_id": str(tenant_id) if tenant_id else None,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "resource_name": resource_name,
        "status": status,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prev_hash": prev_hash,
    }
    entry_hash = _compute_hash(entry_data)

    entry = AuditLog(
        tenant_id=uuid.UUID(str(tenant_id)) if tenant_id else None,
        user_id=uuid.UUID(str(user_id)) if user_id else None,
        actor_email=actor_email,
        actor_role=actor_role,
        actor_ip=actor_ip,
        actor_user_agent=actor_user_agent,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        status=status,
        details=details,
        http_method=http_method,
        http_path=http_path,
        http_status_code=http_status_code,
        error_message=error_message,
        previous_hash=prev_hash,
        entry_hash=entry_hash,
    )
    db.add(entry)

    try:
        await db.flush()
    except Exception as exc:
        log.error("audit.write_failed", action=action, error=str(exc))
        # Audit failure should not break the main flow
        await db.rollback()

    log.info(
        "audit",
        action=action,
        user_id=str(user_id) if user_id else None,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
    )
    return entry


async def _get_last_hash(
    db: AsyncSession,
    tenant_id: Optional[str | uuid.UUID],
) -> Optional[str]:
    """Get the entry_hash of the most recent audit log entry for this tenant."""
    stmt = (
        select(AuditLog.entry_hash)
        .where(AuditLog.tenant_id == uuid.UUID(str(tenant_id)) if tenant_id else True)
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    return row


def _compute_hash(data: dict) -> str:
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


async def verify_audit_chain(
    db: AsyncSession,
    tenant_id: Optional[str | uuid.UUID] = None,
    limit: int = 1000,
) -> dict:
    """
    Verify the integrity of the audit chain.
    Returns dict with verification result and any broken links.
    """
    stmt = (
        select(AuditLog)
        .where(AuditLog.tenant_id == uuid.UUID(str(tenant_id)) if tenant_id else True)
        .order_by(AuditLog.created_at.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    entries = result.scalars().all()

    broken_links = []
    prev_hash = None

    for entry in entries:
        if entry.previous_hash != prev_hash:
            broken_links.append({
                "id": str(entry.id),
                "action": entry.action,
                "expected_prev": prev_hash,
                "actual_prev": entry.previous_hash,
            })
        prev_hash = entry.entry_hash

    return {
        "verified": len(broken_links) == 0,
        "entries_checked": len(entries),
        "broken_links": broken_links,
    }
