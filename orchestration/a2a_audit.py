"""Small durable audit store for A2A dispatch records."""
from __future__ import annotations

import os
from pathlib import Path

from .a2a_governance import DispatchAudit, audit_dict
from .jsonl_store import append_jsonl, integrity_check, read_jsonl


class A2AAuditStore:
    def __init__(self, path: str | None = None):
        self.path = Path(path or os.getenv("A2A_AUDIT_LOG", "var/a2a_audit.jsonl"))

    def append(self, record: DispatchAudit) -> None:
        append_jsonl(self.path, audit_dict(record))

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        return read_jsonl(self.path)

    def integrity_check(self) -> dict:
        return integrity_check(self.path)
