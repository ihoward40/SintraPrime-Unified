"""Verify SintraPrime ledger hashes, snapshots, and append-only chain."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

LEGACY_INDEX_SCHEMA = None
CURRENT_INDEX_SCHEMA = "ledger-index.v1"
CURRENT_ENTRY_SCHEMA = "ledger-entry.v1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return data


def entry_id(entry: dict[str, Any]) -> str | None:
    value = entry.get("entry_id") or entry.get("id")
    return str(value) if value else None


def classify_index(index: dict[str, Any], *, index_path: Path, has_current_entries: bool) -> tuple[str, list[str]]:
    errors: list[str] = []
    schema_version = index.get("schema_version")
    if schema_version is None:
        if any(key not in {"total_entries", "last_entry", "operations", "last_entry_sha256"} for key in index):
            errors.append(f"{index_path} has unknown legacy fields")
            return "invalid index", errors
        return "legacy index", errors
    if schema_version != CURRENT_INDEX_SCHEMA:
        errors.append(f"{index_path} has unsupported schema_version: {schema_version!r}")
        return "invalid index", errors
    if not has_current_entries:
        # The repository may still carry a current-shaped index while historical logs remain legacy-only.
        # The caller still needs the same shape checks below.
        pass
    return "current verified index", errors


def verify(repo_root: Path) -> dict[str, Any]:
    ledger_root = repo_root / "ledger"
    index_path = ledger_root / "ledger_index.json"
    logs = sorted((ledger_root / "logs").glob("*.json"))
    hashes = sorted((ledger_root / "hashes").glob("*.sha256"))
    snapshots = sorted(p for p in (ledger_root / "snapshots").glob("*") if p.is_file())
    seen_hashes: set[Path] = set()
    seen_snapshots: set[Path] = set()
    entry_ids: list[str] = []
    errors: list[str] = []
    previous_current_sha: str | None = None
    last_legacy_entry_id: str | None = None
    current_chain_started = False
    current_entries_present = False
    legacy_entries_count = 0
    current_entries_count = 0

    if not index_path.exists():
        return {
            "ok": False,
            "index_status": "invalid index",
            "ledger_entries": len(logs),
            "hash_files": len(hashes),
            "snapshots": len(snapshots),
            "orphan_hashes": len(hashes),
            "orphan_snapshots": len(snapshots),
            "legacy_unchained_entries": len(logs),
            "chained_entries": 0,
            "chain_status": "broken chain",
            "errors": [f"missing ledger index: {index_path.relative_to(repo_root)}"],
        }

    try:
        index = load_json(index_path)
    except Exception as exc:
        return {
            "ok": False,
            "index_status": "invalid index",
            "ledger_entries": len(logs),
            "hash_files": len(hashes),
            "snapshots": len(snapshots),
            "orphan_hashes": len(hashes),
            "orphan_snapshots": len(snapshots),
            "legacy_unchained_entries": len(logs),
            "chained_entries": 0,
            "chain_status": "broken chain",
            "errors": [f"malformed ledger index: {exc}"],
        }

    for log_path in logs:
        try:
            entry = load_json(log_path)
        except Exception as exc:
            errors.append(f"unreadable ledger log {log_path}: {exc}")
            continue

        e_id = entry_id(entry)
        if not e_id:
            errors.append(f"{log_path} missing entry_id")
            continue
        entry_ids.append(e_id)

        is_current = entry.get("schema_version") == CURRENT_ENTRY_SCHEMA or "previous_entry_sha256" in entry or "receipt_key" in entry
        if is_current:
            current_entries_present = True
            current_entries_count += 1
            if not current_chain_started:
                expected_previous = f"legacy:{last_legacy_entry_id}" if last_legacy_entry_id else None
                current_chain_started = True
            else:
                expected_previous = previous_current_sha
            if entry.get("previous_entry_sha256") != expected_previous:
                errors.append(f"broken chain at {e_id}")
            previous_current_sha = sha256_file(log_path)
        else:
            if current_chain_started:
                errors.append(f"legacy entry appears after current chain starts: {e_id}")
            last_legacy_entry_id = e_id
            legacy_entries_count += 1

        snapshot_path_raw = entry.get("snapshot_path") or (entry.get("snapshot") or {}).get("path")
        hash_path = ledger_root / "hashes" / f"{e_id}.sha256"
        if not hash_path.exists():
            errors.append(f"missing hash record for {e_id}")
            continue
        seen_hashes.add(hash_path.resolve())
        hash_record = load_json(hash_path)

        if snapshot_path_raw:
            snapshot_path = repo_root / str(snapshot_path_raw).lstrip("/\\")
            if not snapshot_path.exists():
                errors.append(f"missing snapshot for {e_id}: {snapshot_path_raw}")
                continue
            seen_snapshots.add(snapshot_path.resolve())
            snapshot_digest = sha256_file(snapshot_path)
            expected_digest = hash_record.get("snapshot_sha256") or hash_record.get("sha256")
            if snapshot_digest != expected_digest:
                errors.append(f"snapshot hash mismatch for {e_id}")
            if hash_record.get("snapshot_path") and hash_record.get("snapshot_path") != str(snapshot_path_raw):
                errors.append(f"swapped snapshot mapping for {e_id}")

        target = str(hash_record.get("target", "")).lstrip("/\\")
        if target and not (repo_root / target).exists():
            errors.append(f"hash target missing for {e_id}: {target}")

    duplicate_ids = [e_id for e_id, count in Counter(entry_ids).items() if count > 1]
    if duplicate_ids:
        errors.append(f"duplicate entry ids: {', '.join(duplicate_ids)}")

    orphan_hashes = [p for p in hashes if p.resolve() not in seen_hashes]
    orphan_snapshots = [p for p in snapshots if p.resolve() not in seen_snapshots]
    for p in orphan_hashes:
        errors.append(f"orphan hash: {p.relative_to(repo_root)}")
    for p in orphan_snapshots:
        errors.append(f"orphan snapshot: {p.relative_to(repo_root)}")

    index_status, index_errors = classify_index(index, index_path=index_path, has_current_entries=current_entries_present)
    errors.extend(index_errors)

    index_schema = index.get("schema_version")
    if index_schema == CURRENT_INDEX_SCHEMA:
        required = {"schema_version", "total_entries", "last_entry", "last_entry_sha256", "operations"}
        missing = sorted(required - set(index))
        if missing:
            errors.append(f"{index_path} missing required fields: {', '.join(missing)}")
        if index.get("last_entry") and index.get("last_entry") not in entry_ids:
            errors.append(f"index last_entry missing from ledger logs: {index.get('last_entry')}")
        if index.get("last_entry"):
            last_log = logs[-1] if logs else None
            if last_log is not None:
                last_log_entry = load_json(last_log)
                last_log_id = entry_id(last_log_entry)
                if last_log_id != index.get("last_entry"):
                    errors.append(f"index last_entry does not point to tail record: {index.get('last_entry')}")
                else:
                    recomputed_tail_hash = sha256_file(last_log)
                    if index.get("last_entry_sha256") != recomputed_tail_hash:
                        errors.append(f"index last_entry_sha256 mismatch: {index.get('last_entry')}")
        expected_total = len(logs)
        if int(index.get("total_entries", -1)) != expected_total:
            errors.append(f"index total_entries mismatch: expected {expected_total}, got {index.get('total_entries')}")
        expected_ops = Counter(entry.get("operation") for entry in (load_json(p) for p in logs) if entry.get("operation"))
        if {k: int(v) for k, v in expected_ops.items()} != {k: int(v) for k, v in (index.get("operations") or {}).items()}:
            errors.append("index operation counters mismatch")
    elif index_schema is None:
        required = {"total_entries", "last_entry", "operations"}
        missing = sorted(required - set(index))
        if missing:
            errors.append(f"{index_path} missing required legacy fields: {', '.join(missing)}")
        expected_total = len(logs)
        if int(index.get("total_entries", -1)) != expected_total:
            errors.append(f"index total_entries mismatch: expected {expected_total}, got {index.get('total_entries')}")
        if logs and index.get("last_entry") != entry_ids[-1]:
            errors.append(f"index last_entry does not point to tail record: {index.get('last_entry')}")
        expected_ops = Counter(entry.get("operation") for entry in (load_json(p) for p in logs) if entry.get("operation"))
        if {k: int(v) for k, v in expected_ops.items()} != {k: int(v) for k, v in (index.get("operations") or {}).items()}:
            errors.append("index operation counters mismatch")
    else:
        errors.append(f"{index_path} has unsupported schema_version: {index_schema!r}")
        index_status = "invalid index"

    return {
        "ok": not errors,
        "index_status": index_status,
        "ledger_entries": len(logs),
        "hash_files": len(hashes),
        "snapshots": len(snapshots),
        "orphan_hashes": len(orphan_hashes),
        "orphan_snapshots": len(orphan_snapshots),
        "legacy_unchained_entries": legacy_entries_count,
        "chained_entries": current_entries_count,
        "chain_status": "broken chain" if any("broken chain" in e for e in errors) else ("chained verified" if current_entries_count else "legacy verified"),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    result = verify(Path(args.repo_root).resolve())
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
