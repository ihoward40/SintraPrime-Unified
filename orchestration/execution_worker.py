"""Dry-run governed outbox worker; external side effects are disabled by default."""
from __future__ import annotations

import hashlib
import os
from typing import Any, Callable

from .outbox import DurableOutbox


class ExecutionWorker:
    def __init__(
        self,
        *,
        outbox: DurableOutbox,
        approval_store: Any,
        agent_policy: Any,
        max_retries: int = 3,
        dry_run: bool = True,
        executor: Callable[[dict[str, Any]], Any] | None = None,
    ):
        self.outbox = outbox
        self.approval_store = approval_store
        self.agent_policy = agent_policy
        self.max_retries = max_retries
        self.dry_run = dry_run
        self.executor = executor

    @staticmethod
    def idempotency_key(record: dict[str, Any]) -> str:
        material = f"{record['outbox_id']}:{record['receipt_id']}:{record['payload_hash']}"
        return hashlib.sha256(material.encode()).hexdigest()

    def run_once(self, outbox_id: str, *, payload_hash: str, tenant_id: str) -> dict[str, Any]:
        record = self.outbox.get(outbox_id)
        if record is None:
            raise KeyError(outbox_id)
        if record.get("status") in {"blocked", "failed", "dispatched", "expired", "dlq"}:
            raise PermissionError(f"Worker blocked: terminal outbox status {record['status']}")
        try:
            validated = self.outbox.revalidate(
                outbox_id,
                approval_store=self.approval_store,
                agent_policy=self.agent_policy,
                payload_hash=payload_hash,
                tenant_id=tenant_id,
            )
        except PermissionError:
            raise

        current = self.outbox.get(outbox_id) or validated
        key = self.idempotency_key(current)
        current["idempotency_key"] = key
        if self.dry_run or os.getenv("A2A_EXTERNAL_ACTIONS_ENABLED", "false").lower() != "true":
            self.outbox.mark_blocked(outbox_id, "external execution disabled; dry-run only")
            return {"outbox_id": outbox_id, "status": "blocked", "idempotency_key": key, "dry_run": True}
        if not self.executor:
            self.outbox.mark_blocked(outbox_id, "no execution adapter configured")
            return {"outbox_id": outbox_id, "status": "blocked", "idempotency_key": key}
        try:
            self.executor(current)
        except Exception as exc:
            retries = int(current.get("retry_count", 0)) + 1
            if retries >= self.max_retries:
                self.outbox.mark_dlq(outbox_id, f"retry limit reached: {exc}")
                return {"outbox_id": outbox_id, "status": "dlq", "retry_count": retries, "idempotency_key": key}
            self.outbox.mark_retry_pending(outbox_id, retries)
            return {"outbox_id": outbox_id, "status": "pending", "retry_count": retries, "idempotency_key": key}
        self.outbox.mark_dispatched(outbox_id)
        return {"outbox_id": outbox_id, "status": "dispatched", "idempotency_key": key}
