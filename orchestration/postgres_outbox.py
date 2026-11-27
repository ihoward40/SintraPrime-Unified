"""Async PostgreSQL outbox adapter with exclusive lease claims."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text


class PostgresOutboxStore:
    def __init__(self, session: Any):
        self.session = session

    async def enqueue(self, *, receipt_id: str, sender_agent_id: str, tenant_id: str, recipient: str, payload_hash: str, idempotency_key: str) -> str:
        outbox_id = uuid.uuid4()
        await self.session.execute(text("""
            INSERT INTO a2a_outbox_current_state
              (tenant_id, outbox_id, idempotency_key, status, receipt_id,
               sender_agent_id, recipient, payload_hash)
            VALUES (:tenant_id, :outbox_id, :idempotency_key, 'pending', :receipt_id,
                    :sender_agent_id, :recipient, :payload_hash)
        """), {"tenant_id": tenant_id, "outbox_id": outbox_id, "idempotency_key": idempotency_key, "receipt_id": receipt_id, "sender_agent_id": sender_agent_id, "recipient": recipient, "payload_hash": payload_hash})
        return str(outbox_id)

    async def claim(self, *, tenant_id: str, worker_id: str, limit: int = 1, lease_seconds: int = 60) -> list[dict[str, Any]]:
        result = await self.session.execute(text("""
            SELECT * FROM a2a_outbox_current_state
            WHERE tenant_id=:tenant_id AND status IN ('pending','validated')
              AND (lease_until IS NULL OR lease_until < now())
            ORDER BY created_at
            FOR UPDATE SKIP LOCKED LIMIT :limit
        """), {"tenant_id": tenant_id, "limit": limit})
        rows = [dict(row) for row in result.mappings().all()]
        for row in rows:
            await self.session.execute(text("""
                UPDATE a2a_outbox_current_state
                SET status='claimed', lease_owner=:worker_id, lease_until=now() + (:lease_seconds * interval '1 second'), claim_version=claim_version+1, version=version+1, updated_at=now()
                WHERE tenant_id=:tenant_id AND outbox_id=:outbox_id AND status IN ('pending','validated')
            """), {"tenant_id": tenant_id, "outbox_id": row["outbox_id"], "worker_id": worker_id, "lease_seconds": lease_seconds})
        return rows

    async def transition(self, *, tenant_id: str, outbox_id: str, worker_id: str, claim_version: int, status: str, reason: str | None = None) -> None:
        if status not in {"dispatched", "failed", "blocked", "expired", "dlq"}:
            raise ValueError("invalid terminal outbox status")
        result = await self.session.execute(text("""
            UPDATE a2a_outbox_current_state
            SET status=:status, reason=:reason, version=version+1, updated_at=now()
            WHERE tenant_id=:tenant_id AND outbox_id=:outbox_id
              AND status='claimed' AND lease_owner=:worker_id AND claim_version=:claim_version
        """), {"tenant_id": tenant_id, "outbox_id": outbox_id, "worker_id": worker_id, "claim_version": claim_version, "status": status, "reason": reason})
        if getattr(result, "rowcount", 1) == 0:
            raise PermissionError("stale or non-owner outbox transition")

    async def get(self, outbox_id: str, *, tenant_id: str) -> dict[str, Any] | None:
        result = await self.session.execute(text("""
            SELECT * FROM a2a_outbox_current_state WHERE tenant_id=:tenant_id AND outbox_id=:outbox_id
        """), {"tenant_id": tenant_id, "outbox_id": outbox_id})
        row = result.mappings().first()
        return dict(row) if row else None
