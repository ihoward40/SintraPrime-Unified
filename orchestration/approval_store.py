"""Durable approval lifecycle storage for governed A2A dispatch."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from threading import Lock
from typing import Any

from .a2a_governance import ApprovalReceipt, DispatchAudit, audit_dict


class ApprovalStore:
    """Append-only JSONL approval event log reconstructed on every read."""

    def __init__(self, path: str | None = None, audit_store: Any | None = None):
        self.path = Path(path or os.getenv("A2A_APPROVAL_STORE", "var/a2a_approvals.jsonl"))
        self.audit_store = audit_store
        self._lock = Lock()

    @staticmethod
    def _receipt_dict(receipt: ApprovalReceipt) -> dict[str, Any]:
        data = dict(receipt.__dict__)
        data["attachment_hashes"] = list(receipt.attachment_hashes)
        return data

    def _append(self, event: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def _record_lifecycle(self, receipt: ApprovalReceipt, status: str, reason: str | None = None) -> None:
        if self.audit_store is None:
            return
        self.audit_store.append(DispatchAudit(
            mission_id=receipt.receipt_id,
            objective="APPROVAL",
            agents_used=(receipt.sender_agent_id,),
            sources_used=(),
            claims_verified=(),
            risks_flagged=(),
            user_approval=receipt.approved_by,
            external_action_taken=False,
            final_output_hash=receipt.final_content_hash,
            payload_hash=receipt.final_content_hash,
            status=status,
            reason_code="approval_lifecycle",
            reason_detail=reason,
        ))

    def issue(self, receipt: ApprovalReceipt) -> ApprovalReceipt:
        self._append({"event": "issued", "receipt": self._receipt_dict(receipt), "timestamp": time.time()})
        self._record_lifecycle(receipt, "issued")
        return receipt

    def _states(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        states: dict[str, dict[str, Any]] = {}
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            receipt = event["receipt"]
            states[receipt["receipt_id"]] = event
        return states

    def get(self, receipt_id: str) -> dict[str, Any] | None:
        return self._states().get(receipt_id)

    def verify_and_consume(self, receipt: ApprovalReceipt) -> None:
        event = self.get(receipt.receipt_id)
        if event is None:
            raise PermissionError("Dispatch blocked: approval receipt is not in durable store")
        stored = event["receipt"]
        if stored != self._receipt_dict(receipt):
            raise PermissionError("Dispatch blocked: approval receipt does not match durable record")
        status = event["event"]
        if status == "revoked":
            raise PermissionError("Dispatch blocked: approval receipt is revoked")
        if status == "used":
            raise PermissionError("Dispatch blocked: approval receipt has already been used")
        if status == "expired" or receipt.expires_at <= time.time():
            if status != "expired":
                self._append({"event": "expired", "receipt": stored, "timestamp": time.time()})
                self._record_lifecycle(receipt, "expired")
            raise PermissionError("Dispatch blocked: approval receipt is expired")
        self._append({"event": "used", "receipt": stored, "timestamp": time.time()})
        self._record_lifecycle(receipt, "used")

    def revoke(self, receipt_id: str, reason: str = "revoked") -> None:
        event = self.get(receipt_id)
        if event is None:
            raise KeyError(receipt_id)
        receipt = ApprovalReceipt(**event["receipt"])
        self._append({"event": "revoked", "receipt": self._receipt_dict(receipt), "reason": reason, "timestamp": time.time()})
        self._record_lifecycle(receipt, "revoked", reason)

    def expire(self) -> int:
        count = 0
        for event in list(self._states().values()):
            receipt = ApprovalReceipt(**event["receipt"])
            if event["event"] == "issued" and receipt.expires_at <= time.time():
                self._append({"event": "expired", "receipt": self._receipt_dict(receipt), "timestamp": time.time()})
                self._record_lifecycle(receipt, "expired")
                count += 1
        return count
