"""Async PostgreSQL approval lifecycle adapter."""
from __future__ import annotations

import json
import time
from typing import Any

from sqlalchemy import text

from .a2a_governance import ApprovalReceipt


class PostgresApprovalStore:
    def __init__(self, session: Any):
        self.session = session

    @staticmethod
    def _params(receipt: ApprovalReceipt, tenant_id: str) -> dict[str, Any]:
        return {"tenant_id": tenant_id, "receipt_id": receipt.receipt_id, "approved_by": receipt.approved_by, "sender_agent_id": receipt.sender_agent_id, "recipient": receipt.recipient, "approved_output_id": receipt.approved_output_id, "final_content_hash": receipt.final_content_hash, "attachment_hashes": json.dumps(list(receipt.attachment_hashes)), "signature": receipt.signature, "expires_at": receipt.expires_at}

    async def issue(self, receipt: ApprovalReceipt, *, tenant_id: str) -> ApprovalReceipt:
        if tenant_id != receipt.tenant_id:
            raise PermissionError("approval tenant scope does not match")
        params = self._params(receipt, tenant_id)
        await self.session.execute(text("""
            INSERT INTO a2a_approval_events
              (tenant_id, receipt_id, event_type, approved_by, sender_agent_id,
               recipient, approved_output_id, final_content_hash, attachment_hashes,
               signature, expires_at)
            VALUES (:tenant_id, :receipt_id, 'issued', :approved_by, :sender_agent_id,
                    :recipient, :approved_output_id, :final_content_hash,
                    CAST(:attachment_hashes AS jsonb), :signature,
                    to_timestamp(:expires_at))
        """), params)
        await self.session.execute(text("""
            INSERT INTO a2a_approval_current_state
              (tenant_id, receipt_id, status, approved_by, sender_agent_id,
               recipient, approved_output_id, final_content_hash, attachment_hashes,
               signature, expires_at)
            VALUES (:tenant_id, :receipt_id, 'issued', :approved_by, :sender_agent_id,
                    :recipient, :approved_output_id, :final_content_hash,
                    CAST(:attachment_hashes AS jsonb), :signature,
                    to_timestamp(:expires_at))
        """), params)
        return receipt

    async def verify_and_consume(self, receipt: ApprovalReceipt, *, tenant_id: str, consumer_id: str) -> None:
        if tenant_id != receipt.tenant_id:
            raise PermissionError("approval tenant scope does not match")
        result = await self.session.execute(text("""
            SELECT * FROM a2a_approval_current_state
            WHERE tenant_id = :tenant_id AND receipt_id = :receipt_id
            FOR UPDATE
        """), {"tenant_id": tenant_id, "receipt_id": receipt.receipt_id})
        row = result.mappings().first()
        if row is None:
            raise PermissionError("approval receipt is not in durable store")
        if row["status"] != "issued":
            raise PermissionError(f"approval receipt is {row['status']}")
        if row["expires_at"].timestamp() <= time.time():
            raise PermissionError("approval receipt is expired")
        if row["sender_agent_id"] != receipt.sender_agent_id or row["recipient"] != receipt.recipient or row["final_content_hash"] != receipt.final_content_hash:
            raise PermissionError("approval receipt binding does not match")
        await self.session.execute(text("""
            UPDATE a2a_approval_current_state
            SET status = 'used', consumed_by = :consumer_id, consumed_at = now(), version = version + 1, updated_at = now()
            WHERE tenant_id = :tenant_id AND receipt_id = :receipt_id AND status = 'issued'
        """), {"tenant_id": tenant_id, "receipt_id": receipt.receipt_id, "consumer_id": consumer_id})
        await self.session.execute(text("""
            INSERT INTO a2a_approval_events
              (tenant_id, receipt_id, event_type, approved_by, sender_agent_id,
               recipient, approved_output_id, final_content_hash, attachment_hashes,
               signature, expires_at)
            SELECT tenant_id, receipt_id, 'used', approved_by, sender_agent_id,
                   recipient, approved_output_id, final_content_hash, attachment_hashes,
                   signature, expires_at
            FROM a2a_approval_current_state
            WHERE tenant_id = :tenant_id AND receipt_id = :receipt_id
        """), {"tenant_id": tenant_id, "receipt_id": receipt.receipt_id})

    async def revoke(self, receipt_id: str, *, tenant_id: str, reason: str = "revoked") -> None:
        result = await self.session.execute(text("""
            SELECT * FROM a2a_approval_current_state
            WHERE tenant_id = :tenant_id AND receipt_id = :receipt_id FOR UPDATE
        """), {"tenant_id": tenant_id, "receipt_id": receipt_id})
        if result.mappings().first() is None:
            raise KeyError(receipt_id)
        await self.session.execute(text("""
            UPDATE a2a_approval_current_state SET status='revoked', version=version+1, updated_at=now()
            WHERE tenant_id=:tenant_id AND receipt_id=:receipt_id AND status='issued'
        """), {"tenant_id": tenant_id, "receipt_id": receipt_id})

    async def get(self, receipt_id: str, *, tenant_id: str) -> dict[str, Any] | None:
        result = await self.session.execute(text("""
            SELECT * FROM a2a_approval_current_state WHERE tenant_id=:tenant_id AND receipt_id=:receipt_id
        """), {"tenant_id": tenant_id, "receipt_id": receipt_id})
        row = result.mappings().first()
        return dict(row) if row else None
