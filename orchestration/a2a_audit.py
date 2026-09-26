"""Small durable audit store for A2A dispatch records."""
from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock

from .a2a_governance import DispatchAudit, audit_dict


class A2AAuditStore:
    def __init__(self, path: str | None = None):
        self.path = Path(path or os.getenv("A2A_AUDIT_LOG", "var/a2a_audit.jsonl"))
        self._lock = Lock()

    def append(self, record: DispatchAudit) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(audit_dict(record), sort_keys=True)
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        records: list[dict] = []
        for index, line in enumerate(lines):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                if index == len(lines) - 1:
                    # A final partial write can be safely ignored; prior
                    # corruption must remain visible instead of disappearing.
                    continue
                raise
        return records
