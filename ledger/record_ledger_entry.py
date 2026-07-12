import argparse
import hashlib
import json
import os
import shutil
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION = "ledger-entry.v1"
RECEIPT_SCHEMA_VERSION = "ledger-receipt.v1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json_atomic(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


class FileLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.fd = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(self.fd, str(os.getpid()).encode("ascii"))
        except FileExistsError as exc:
            raise SystemExit(f"ledger is locked: {self.path}") from exc
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.fd is not None:
            os.close(self.fd)
        with suppress(FileNotFoundError):
            self.path.unlink()


def infer_case_id(target_rel: Path) -> str | None:
    parts = target_rel.as_posix().split("/")
    if len(parts) >= 2 and parts[0] == "clients":
        return parts[1]
    if len(parts) >= 3 and parts[0] == "artifacts" and parts[1] == "court":
        return parts[2]
    return None


def normalize_repo_relative(target_rel: Path | str) -> str:
    return Path(target_rel).as_posix().lstrip("./")


def compute_receipt_key(*, case_id: str | None, target: str, artifact_sha256: str, operation: str) -> str:
    payload = "\n".join(
        [
            RECEIPT_SCHEMA_VERSION,
            case_id or "",
            normalize_repo_relative(target),
            artifact_sha256,
            operation,
        ]
    ).encode("utf-8")
    return sha256_bytes(payload)


def find_existing_receipt(
    *,
    ledger_root: Path,
    receipt_key: str,
    target: str,
    artifact_sha256: str,
    operation: str,
) -> tuple[str, Path] | None:
    logs_dir = ledger_root / "logs"
    matches: list[tuple[str, Path]] = []
    for log_path in sorted(logs_dir.glob("*.json")):
        try:
            entry = load_json(log_path, {})
        except Exception:
            continue
        if entry.get("receipt_key") != receipt_key:
            continue
        if normalize_repo_relative(entry.get("target", "")) != normalize_repo_relative(target):
            continue
        if entry.get("after_hash") != artifact_sha256:
            continue
        if entry.get("operation") != operation:
            continue
        if entry.get("status") not in {"PASS", "INFO"}:
            continue
        matches.append((str(entry.get("entry_id") or entry.get("id") or ""), log_path))

    if len(matches) > 1:
        raise SystemExit(f"conflicting ledger receipts share receipt_key={receipt_key}")
    return matches[0] if matches else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--agent", default="hermes")
    p.add_argument("--operation", required=True, help="write_file|edit_file|delete_file|config_change|agent_memory_update|registry_update")
    p.add_argument("--target", required=True, help="Repo-relative path, e.g. config/academy_registry.json")
    p.add_argument("--expected_outcome", default=None)
    p.add_argument("--actual_outcome", default=None)
    p.add_argument("--status", default="PASS", help="PASS|FAIL|INFO")
    p.add_argument("--failure_mode", default=None)
    p.add_argument("--verification", default=None, help="JSON string for verification object")
    p.add_argument("--before_hash", default=None)
    p.add_argument("--after_hash", default=None)
    p.add_argument("--snapshot", action="store_true", help="If target exists, snapshot it into ledger/snapshots")
    p.add_argument("--snapshot_name", default=None, help="Override snapshot filename (optional)")
    args = p.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    ledger_root = repo_root / "ledger"
    logs_dir = ledger_root / "logs"
    snaps_dir = ledger_root / "snapshots"
    hashes_dir = ledger_root / "hashes"
    index_path = ledger_root / "ledger_index.json"

    target_rel = Path(args.target)
    if target_rel.is_absolute():
        target_rel = target_rel.resolve()
        try:
            target_rel = target_rel.relative_to(repo_root)
        except ValueError as exc:
            raise SystemExit(f"--target must be repo-relative (got absolute outside repo): {args.target}") from exc

    target_path = (repo_root / target_rel).resolve()
    try:
        target_rel = target_path.relative_to(repo_root)
    except ValueError as exc:
        raise SystemExit(f"--target escaped repo root: {args.target}") from exc

    lock_path = ledger_root / ".ledger.lock"
    with FileLock(lock_path):
        index = load_json(index_path, {
            "schema_version": "ledger-index.v1",
            "total_entries": 0,
            "last_entry": None,
            "last_entry_sha256": None,
            "operations": {},
        })
        previous_entry_sha256 = index.get("last_entry_sha256")
        if previous_entry_sha256 is None and index.get("last_entry"):
            previous_entry_sha256 = f"legacy:{index['last_entry']}"
        now = datetime.now(UTC)
        ledger_id = f"LEDGER-{now.strftime('%Y-%m-%d')}-{now.strftime('%H%M%S%f')}-{uuid.uuid4().hex[:8].upper()}"

        verification_obj = json.loads(args.verification) if args.verification else None
        target_exists = target_path.exists()
        snapshot_path = None
        snapshot_sha256 = None
        actual_hash = args.after_hash
        if actual_hash is None and target_exists:
            actual_hash = sha256_file(target_path)

        receipt_key = None
        receipt_status = None
        if isinstance(verification_obj, dict):
            receipt_key = verification_obj.get("receipt_key")
            receipt_status = verification_obj.get("receipt_status")
        if receipt_key and actual_hash:
            existing = find_existing_receipt(
                ledger_root=ledger_root,
                receipt_key=str(receipt_key),
                target="/" + target_rel.as_posix(),
                artifact_sha256=str(actual_hash),
                operation=args.operation,
            )
            if existing is not None:
                ledger_id, existing_log_path = existing
                print(json.dumps({"ok": True, "ledger_id": ledger_id, "log_path": str(existing_log_path), "reused": True}, ensure_ascii=False))
                return

        if args.snapshot and target_exists:
            snap_name = args.snapshot_name or f"{now.strftime('%Y-%m-%dT%H%M%S%f')}_{target_rel.name}"
            snapshot_path = snaps_dir / snap_name
            snaps_dir.mkdir(parents=True, exist_ok=True)
            if snapshot_path.exists():
                raise SystemExit(f"snapshot already exists: {snapshot_path}")
            shutil.copy2(target_path, snapshot_path)
            snapshot_sha256 = sha256_file(snapshot_path)
            if actual_hash and snapshot_sha256 != actual_hash:
                raise SystemExit("snapshot hash does not match target hash at write time")

        entry = {
            "entry_id": ledger_id,
            "id": ledger_id,
            "schema_version": SCHEMA_VERSION,
            "created_at": utc_now_iso(),
            "timestamp": utc_now_iso(),
            "agent": args.agent,
            "operation": args.operation,
            "case_id": infer_case_id(target_rel),
            "target": "/" + target_rel.as_posix(),
            "input_hash": args.before_hash,
            "after_hash": actual_hash,
            "snapshot_path": str(snapshot_path.relative_to(repo_root)).replace("\\", "/") if snapshot_path else None,
            "snapshot_sha256": snapshot_sha256,
            "previous_entry_sha256": previous_entry_sha256,
            "generator_version": os.getenv("SINTRAPRIME_GENERATOR_VERSION", "unversioned-local"),
            "expected_outcome": args.expected_outcome,
            "actual_outcome": args.actual_outcome,
            "verification": verification_obj,
            "status": args.status,
            "failure_mode": args.failure_mode,
            "receipt_key": receipt_key,
            "receipt_status": receipt_status or "VERIFIED",
        }
        if snapshot_path:
            entry["snapshot"] = {
                "path": entry["snapshot_path"],
                "filename": snapshot_path.name,
            }

        log_path = logs_dir / f"{ledger_id}.json"
        if log_path.exists():
            raise SystemExit(f"ledger entry already exists: {log_path}")
        save_json_atomic(log_path, entry)
        entry_sha256 = sha256_file(log_path)

        if actual_hash:
            save_json_atomic(hashes_dir / f"{ledger_id}.sha256", {
                "schema_version": "ledger-hash.v1",
                "entry_id": ledger_id,
                "sha256": actual_hash,
                "snapshot_path": entry["snapshot_path"],
                "snapshot_sha256": snapshot_sha256,
                "target": "/" + target_rel.as_posix(),
                "receipt_key": receipt_key,
            })

        index["schema_version"] = "ledger-index.v1"
        index["total_entries"] = int(index.get("total_entries", 0)) + 1
        index["last_entry"] = ledger_id
        index["last_entry_sha256"] = entry_sha256
        ops = index.setdefault("operations", {})
        ops[args.operation] = int(ops.get(args.operation, 0)) + 1
        save_json_atomic(index_path, index)

    print(json.dumps({"ok": True, "ledger_id": ledger_id, "log_path": str(log_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
