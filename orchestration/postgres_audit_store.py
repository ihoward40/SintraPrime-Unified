"""Async PostgreSQL audit adapter; transaction ownership belongs to the caller."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from .a2a_governance import DispatchAudit, audit_dict


class PostgresAuditStore:
    def __init__(self, session: Any):
        self.session = session

    async def append(self, record: DispatchAudit, *, tenant_id: str) -> None:
        if not tenant_id:
            raise ValueError("tenant_id is required")
        data = audit_dict(record)
        await self.session.execute(text("""
            INSERT INTO a2a_audit_events
              (tenant_id, event_type, mission_id, actor_agent_id, objective,
               status, reason_code, reason_detail, user_approval,
               external_action_taken, payload_hash, attachment_hashes,
               final_output_hash, evidence, idempotency_key)
            VALUES
              (:tenant_id, :event_type, :mission_id, :actor_agent_id, :objective,
               :status, :reason_code, :reason_detail, :user_approval,
               FALSE, :payload_hash, CAST(:attachment_hashes AS jsonb),
               :final_output_hash, CAST(:evidence AS jsonb), :idempotency_key)
            ON CONFLICT (tenant_id, idempotency_key) DO NOTHING
        """), {
            "tenant_id": tenant_id, "event_type": "dispatch_audit",
            "mission_id": data["mission_id"], "actor_agent_id": data["agents_used"][0] if data["agents_used"] else None,
            "objective": data["objective"], "status": data["status"],
            "reason_code": data.get("reason_code"), "reason_detail": data.get("reason_detail"),
            "user_approval": data["user_approval"], "payload_hash": data.get("payload_hash", ""),
            "attachment_hashes": json.dumps([]), "final_output_hash": data["final_output_hash"],
            "evidence": json.dumps({"agents_used": data["agents_used"], "sources_used": data["sources_used"], "claims_verified": data["claims_verified"], "risks_flagged": data["risks_flagged"]}),
            "idempotency_key": data["audit_id"],
        })

    async def read(self, *, tenant_id: str, mission_id: str | None = None) -> list[dict[str, Any]]:
        if not tenant_id:
            raise ValueError("tenant_id is required")
        result = await self.session.execute(text("""
            SELECT * FROM a2a_audit_events
            WHERE tenant_id = :tenant_id AND (:mission_id IS NULL OR mission_id = :mission_id)
            ORDER BY sequence
        """), {"tenant_id": tenant_id, "mission_id": mission_id})
        return [dict(row) for row in result.mappings().all()]

    async def integrity_check(self, *, tenant_id: str) -> dict[str, Any]:
        rows = await self.read(tenant_id=tenant_id)
        sequences = [int(row["sequence"]) for row in rows]
        return {"records": len(rows), "last_sequence": sequences[-1] if sequences else 0, "sequential": sequences == sorted(sequences)}
