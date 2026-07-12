from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import uuid
from pathlib import Path

import pytest


def load_verify():
    spec = importlib.util.spec_from_file_location("verify_ledger", Path("ledger/verify_ledger.py"))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, obj: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, sort_keys=True, indent=2).encode()
    path.write_bytes(text)
    return sha_bytes(text)


def scratch_repo() -> Path:
    root = Path.cwd() / ".case_runs" / "ledger-tests" / uuid.uuid4().hex
    (root / "ledger" / "logs").mkdir(parents=True)
    (root / "ledger" / "hashes").mkdir(parents=True)
    (root / "ledger" / "snapshots").mkdir(parents=True)
    return root


def build_chain(root: Path) -> dict[str, Path]:
    snap1 = root / "ledger" / "snapshots" / "one.json"
    snap2 = root / "ledger" / "snapshots" / "two.json"
    snap1_digest = write_json(snap1, {"case_id": "CASE-LEDGER-1"})
    snap2_digest = write_json(snap2, {"case_id": "CASE-LEDGER-2"})
    legacy = {"id": "LEDGER-LEGACY", "snapshot": {"path": "ledger/snapshots/one.json"}}
    write_json(root / "ledger" / "logs" / "000-legacy.json", legacy)
    write_json(root / "ledger" / "hashes" / "LEDGER-LEGACY.sha256", {"sha256": snap1_digest, "snapshot_path": "ledger/snapshots/one.json"})
    entry1 = {
        "schema_version": "ledger-entry.v1",
        "entry_id": "LEDGER-CHAIN-1",
        "snapshot_path": "ledger/snapshots/two.json",
        "snapshot_sha256": snap2_digest,
        "previous_entry_sha256": "legacy:LEDGER-LEGACY",
    }
    entry1_hash = write_json(root / "ledger" / "logs" / "001-chain.json", entry1)
    write_json(root / "ledger" / "hashes" / "LEDGER-CHAIN-1.sha256", {"snapshot_sha256": snap2_digest, "snapshot_path": "ledger/snapshots/two.json"})
    snap3 = root / "ledger" / "snapshots" / "three.json"
    snap3_digest = write_json(snap3, {"case_id": "CASE-LEDGER-3"})
    entry2 = {
        "schema_version": "ledger-entry.v1",
        "entry_id": "LEDGER-CHAIN-2",
        "snapshot_path": "ledger/snapshots/three.json",
        "snapshot_sha256": snap3_digest,
        "previous_entry_sha256": entry1_hash,
    }
    write_json(root / "ledger" / "logs" / "002-chain.json", entry2)
    write_json(root / "ledger" / "hashes" / "LEDGER-CHAIN-2.sha256", {"snapshot_sha256": snap3_digest, "snapshot_path": "ledger/snapshots/three.json"})
    index = {
        "schema_version": "ledger-index.v1",
        "total_entries": 3,
        "last_entry": "LEDGER-CHAIN-2",
        "last_entry_sha256": sha_bytes((root / "ledger" / "logs" / "002-chain.json").read_bytes()),
        "operations": {},
    }
    write_json(root / "ledger" / "ledger_index.json", index)
    return {"entry1": root / "ledger" / "logs" / "001-chain.json", "snap2": snap2, "hash1": root / "ledger" / "hashes" / "LEDGER-CHAIN-1.sha256"}


def test_two_new_chained_entries_verify_end_to_end():
    root = scratch_repo()
    try:
        build_chain(root)
        result = load_verify().verify(root)
        assert result["ok"] is True
        assert result["legacy_unchained_entries"] == 1
        assert result["chained_entries"] == 2
        assert result["chain_status"] == "chained verified"
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.parametrize(("tamper", "expected"), [
    ("delete_middle", "broken chain"),
    ("modify_snapshot", "snapshot hash mismatch"),
    ("swapped_hash", "swapped snapshot mapping"),
    ("duplicate_id", "duplicate entry ids"),
    ("orphan_snapshot", "orphan snapshot"),
])
def test_ledger_tamper_detection(tamper: str, expected: str):
    root = scratch_repo()
    try:
        paths = build_chain(root)
        if tamper == "delete_middle":
            paths["entry1"].unlink()
        elif tamper == "modify_snapshot":
            paths["snap2"].write_text('{"case_id":"TAMPERED"}', encoding="utf-8")
        elif tamper == "swapped_hash":
            data = json.loads(paths["hash1"].read_text(encoding="utf-8"))
            data["snapshot_path"] = "ledger/snapshots/three.json"
            write_json(paths["hash1"], data)
        elif tamper == "duplicate_id":
            dup = root / "ledger" / "logs" / "003-dup.json"
            write_json(dup, {"schema_version": "ledger-entry.v1", "entry_id": "LEDGER-CHAIN-2", "previous_entry_sha256": "bad"})
            write_json(root / "ledger" / "hashes" / "LEDGER-CHAIN-2.sha256", {"snapshot_sha256": "bad"})
        elif tamper == "orphan_snapshot":
            (root / "ledger" / "snapshots" / "orphan.json").write_text("{}", encoding="utf-8")
        result = load_verify().verify(root)
        assert result["ok"] is False
        assert any(expected in error for error in result["errors"])
    finally:
        shutil.rmtree(root, ignore_errors=True)
