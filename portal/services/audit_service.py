"""
Immutable, hash-chained audit log service.
Every action is recorded with: who, what, when, IP, device.
SHA-256 chain links entries for tamper detection.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.audit import AuditLog

log = structlog.get_logger()


async def audit(
    db: AsyncSession,
    action: str,
    user_id: str | None = None,
    tenant_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    resource_name: str | None = None,
    status: str = "success",
    details: dict[str, Any] | None = None,
    actor_email: str | None = None,
    actor_role: str | None = None,
    actor_ip: str | None = None,
    actor_user_agent: str | None = None,
    http_method: str | None = None,
    http_path: str | None = None,
    http_status_code: int | None = None,
    error_message: str | None = None,
) -> AuditLog:
    """Append an immutable audit entry with SHA-256 chaining.

    ``created_at`` is assigned in application code rather than relying only on the
    database server default. SQLite's ``CURRENT_TIMESTAMP`` is commonly only
    second-resolution, which allowed multiple sequential writes to share the same
    timestamp and made ``ORDER BY created_at`` unable to identify the real chain
    head deterministically. Using the same high-resolution UTC timestamp for both
    the persisted row and the hash payload keeps chain order reproducible across
    supported databases.
    """
    prev_hash = await _get_last_hash(db, tenant_id)
    event_time = datetime.now(UTC)

    entry_data = {
        "action": action,
        "user_id": str(user_id) if user_id else None,
        "tenant_id": str(tenant_id) if tenant_id else None,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "resource_name": resource_name,
        "status": status,
        "details": details,
        "timestamp": event_time.isoformat(),
        "prev_hash": prev_hash,
    }
    entry_hash = _compute_hash(entry_data)

    entry = AuditLog(
        tenant_id=str(tenant_id) if tenant_id else None,
        user_id=str(user_id) if user_id else None,
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
        created_at=event_time,
    )
    add_result = db.add(entry)
    if inspect.isawaitable(add_result):
        await add_result

    try:
        await db.flush()
    except Exception as exc:
        log.error("audit.write_failed", action=action, error=str(exc))
        raise

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
    tenant_id: str | None,
) -> str | None:
    """Get the entry_hash of the most recent audit log entry for this tenant."""
    stmt = (
        select(AuditLog.entry_hash)
        .where(AuditLog.tenant_id == str(tenant_id) if tenant_id else True)
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _compute_hash(data: dict) -> str:
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


async def verify_audit_chain(
    db: AsyncSession,
    tenant_id: str | None = None,
    limit: int = 1000,
) -> dict:
    """
    Verify the integrity of the audit chain.
    Returns dict with verification result and any broken links.
    """
    stmt = (
        select(AuditLog)
        .where(AuditLog.tenant_id == str(tenant_id) if tenant_id else True)
        .order_by(AuditLog.created_at.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    entries = result.scalars().all()

    broken_links = []
    prev_hash = None

    for entry in entries:
        if entry.previous_hash != prev_hash:
            broken_links.append(
                {
                    "id": str(entry.id),
                    "action": entry.action,
                    "expected_prev": prev_hash,
                    "actual_prev": entry.previous_hash,
                }
            )
        prev_hash = entry.entry_hash

    return {
        "verified": len(broken_links) == 0,
        "entries_checked": len(entries),
        "broken_links": broken_links,
    }
