"""CollaborationStore — disk-persisted state for CF-1.

JSON persistence per entity, mirroring the workflow_runtime checkpoint
pattern. PostgreSQL migrations are Phase CF-2 (directive defers DB).
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")


def _dump(obj):
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, (list, tuple)):
        return [_dump(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _dump(v) for k, v in obj.items()}
    return str(obj)


class CollaborationStore:
    """Keyed JSON persistence with atomic writes."""

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, kind: str, key: str) -> Path:
        return self.base_dir / kind / f"{key}.json"

    def save(self, kind: str, key: str, obj) -> None:
        path = self._path(kind, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(_dump(obj), sort_keys=True, indent=2), encoding="utf-8")
        tmp.replace(path)

    def load(self, kind: str, key: str, cls: type[T]) -> T | None:
        path = self._path(kind, key)
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(**raw)

    def load_many(self, kind: str, cls: type[T]) -> list[T]:
        kind_dir = self.base_dir / kind
        if not kind_dir.exists():
            return []
        results = []
        for path in sorted(kind_dir.glob("*.json")):
            raw = json.loads(path.read_text(encoding="utf-8"))
            results.append(cls(**raw))
        return results

    def delete(self, kind: str, key: str) -> None:
        path = self._path(kind, key)
        if path.exists():
            path.unlink()
