"""Small durable audit store for A2A dispatch records."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .a2a_governance import DispatchAudit, audit_dict
from .jsonl_store import append_jsonl, integrity_check, read_jsonl


class A2AAuditStore:
    def __init__(self, path: str | None = None, shadow_recorder: Any | None = None):
        self.path = Path(path or os.getenv("A2A_AUDIT_LOG", "var/a2a_audit.jsonl"))
        self.shadow_recorder = shadow_recorder

    def append(self, record: DispatchAudit) -> None:
        payload = audit_dict(record)
        append_jsonl(self.path, payload)
        if self.shadow_recorder is not None:
            self.shadow_recorder.record(tenant_id=str(payload.get("tenant_id", "default")), lifecycle_area="audit_event", state=payload)

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        return read_jsonl(self.path)

    def integrity_check(self) -> dict:
        return integrity_check(self.path)
