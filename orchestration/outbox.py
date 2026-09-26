"""Durable governed dispatch outbox with restart-time revalidation."""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from threading import Lock
from typing import Any

from .a2a_governance import DispatchAudit


class DurableOutbox:
    STATUSES = {"pending", "validated", "blocked", "dispatched", "failed", "expired"}

    def __init__(self, path: str | None = None, audit_store: Any | None = None):
        self.path = Path(path or os.getenv("A2A_OUTBOX_STORE", "var/a2a_outbox.jsonl"))
        self.audit_store = audit_store
        self._lock = Lock()

    def _append(self, event: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def _records(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        records: dict[str, dict[str, Any]] = {}
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                event = json.loads(line)
                records[event["outbox_id"]] = event
        return records

    def _audit(self, record: dict[str, Any], status: str, reason: str | None = None) -> None:
        if self.audit_store is None:
            return
        self.audit_store.append(DispatchAudit(
            mission_id=record["outbox_id"],
            objective="OUTBOX",
            agents_used=(record["sender_agent_id"], record["recipient"]),
            sources_used=(),
            claims_verified=(),
            risks_flagged=(),
            user_approval="yes",
            external_action_taken=False,
            final_output_hash=record["payload_hash"],
            payload_hash=record["payload_hash"],
            status=status,
            reason_code="outbox_revalidation" if status == "blocked" else None,
            reason_detail=reason,
        ))

    def enqueue(
        self,
        *,
        receipt_id: str,
        sender_agent_id: str,
        tenant_id: str,
        recipient: str,
        payload_hash: str,
        attachment_hashes: tuple[str, ...] = (),
    ) -> str:
        outbox_id = uuid.uuid4().hex
        record = {
            "outbox_id": outbox_id,
            "receipt_id": receipt_id,
            "sender_agent_id": sender_agent_id,
            "tenant_id": tenant_id,
            "recipient": recipient,
            "payload_hash": payload_hash,
            "attachment_hashes": list(attachment_hashes),
            "status": "pending",
            "created_at": time.time(),
        }
        self._append(record)
        return outbox_id

    def get(self, outbox_id: str) -> dict[str, Any] | None:
        return self._records().get(outbox_id)

    def _transition(self, record: dict[str, Any], status: str, reason: str | None = None) -> None:
        updated = dict(record)
        updated["status"] = status
        updated["updated_at"] = time.time()
        if reason:
            updated["reason"] = reason
        self._append(updated)
        if status in {"blocked", "failed", "expired"}:
            self._audit(updated, status, reason)

    def revalidate(
        self,
        outbox_id: str,
        *,
        approval_store: Any,
        agent_policy: Any,
        payload_hash: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        record = self.get(outbox_id)
        if record is None:
            raise KeyError(outbox_id)
        if record["status"] in {"blocked", "failed", "dispatched", "expired"}:
            raise PermissionError(f"Outbox item is already terminal: {record['status']}")
        if record["payload_hash"] != payload_hash:
            self._transition(record, "blocked", "payload hash changed")
            raise PermissionError("Outbox blocked: payload hash changed")
        if record["tenant_id"] != tenant_id:
            self._transition(record, "blocked", "tenant scope changed")
            raise PermissionError("Outbox blocked: tenant scope changed")
        profile = agent_policy.profile(record["sender_agent_id"])
        if not profile or profile.get("status") != "active" or profile.get("can_send_external"):
            self._transition(record, "blocked", "sender registry profile is not eligible")
            raise PermissionError("Outbox blocked: sender registry profile is not eligible")
        approval = approval_store.get(record["receipt_id"])
        if approval is None:
            self._transition(record, "blocked", "approval missing from durable store")
            raise PermissionError("Outbox blocked: approval missing from durable store")
        if approval["event"] == "revoked":
            self._transition(record, "blocked", "approval revoked")
            raise PermissionError("Outbox blocked: approval revoked")
        receipt = approval["receipt"]
        if approval["event"] == "used":
            self._transition(record, "blocked", "approval already used")
            raise PermissionError("Outbox blocked: approval already used")
        if float(receipt["expires_at"]) <= time.time():
            self._transition(record, "expired", "approval expired")
            raise PermissionError("Outbox blocked: approval expired")
        if receipt["sender_agent_id"] != record["sender_agent_id"] or receipt["tenant_id"] != tenant_id:
            self._transition(record, "blocked", "approval identity scope changed")
            raise PermissionError("Outbox blocked: approval identity scope changed")
        if receipt["recipient"] != record["recipient"] or receipt["final_content_hash"] != payload_hash:
            self._transition(record, "blocked", "approval binding changed")
            raise PermissionError("Outbox blocked: approval binding changed")
        self._transition(record, "validated")
        return self.get(outbox_id) or record

    def mark_failed(self, outbox_id: str, reason: str) -> None:
        record = self.get(outbox_id)
        if record is None:
            raise KeyError(outbox_id)
        self._transition(record, "failed", reason)

    def mark_dispatched(self, outbox_id: str) -> None:
        record = self.get(outbox_id)
        if record is None:
            raise KeyError(outbox_id)
        self._transition(record, "dispatched")
