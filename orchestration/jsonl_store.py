"""Cross-process-safe JSONL append and integrity helpers."""
from __future__ import annotations

import fcntl
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


@contextmanager
def file_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def append_jsonl(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(path):
        sequence = 1
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    sequence = max(sequence, int(json.loads(line)["sequence"]) + 1)
        record = {"sequence": sequence, **payload}
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
            stream.flush()
            import os
            os.fsync(stream.fileno())
        return record


def read_jsonl(path: Path, *, allow_final_partial: bool = True) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    records: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            if allow_final_partial and index == len(lines) - 1:
                continue
            raise
    return records


def integrity_check(path: Path) -> dict[str, Any]:
    records = read_jsonl(path, allow_final_partial=False)
    sequences = [int(record["sequence"]) for record in records]
    if sequences != list(range(1, len(sequences) + 1)):
        raise ValueError("JSONL sequence integrity check failed")
    return {"records": len(records), "last_sequence": sequences[-1] if sequences else 0}
