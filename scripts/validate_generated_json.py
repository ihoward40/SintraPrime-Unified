"""Validate generated artifact JSON with strict local validators."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


def load_artifact_schemas():
    path = Path(__file__).resolve().parents[1] / "backend" / "stripe_payments" / "services" / "artifact_schemas.py"
    spec = importlib.util.spec_from_file_location("artifact_schemas", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load artifact_schemas.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_legacy_manifest() -> dict[str, dict]:
    manifest_path = Path("schemas/artifacts/legacy_artifacts_manifest.json")
    if not manifest_path.exists():
        return {}
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != "legacy_artifacts_manifest.v1":
        raise RuntimeError("legacy_artifacts_manifest.json has unsupported schema")
    allowed_keys = {"schema_version", "generated_at", "policy", "grandfathered_files"}
    extra = set(data) - allowed_keys
    if extra:
        raise RuntimeError(f"legacy_artifacts_manifest.json has unknown fields: {', '.join(sorted(extra))}")
    records = data.get("grandfathered_files", [])
    if not isinstance(records, list):
        raise RuntimeError("legacy_artifacts_manifest.json grandfathered_files must be a list")
    manifest: dict[str, dict] = {}
    for record in records:
        if not isinstance(record, dict):
            raise RuntimeError("legacy_artifacts_manifest.json grandfathered_files entries must be objects")
        required = {"path", "sha256", "grandfathered_at", "reason"}
        missing = required - set(record)
        extra_record = set(record) - required
        if missing:
            raise RuntimeError(f"legacy_artifacts_manifest.json missing grandfathered file fields: {', '.join(sorted(missing))}")
        if extra_record:
            raise RuntimeError(f"legacy_artifacts_manifest.json has unknown grandfathered file fields: {', '.join(sorted(extra_record))}")
        manifest[str(record["path"]).replace("\\", "/")] = record
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", default=["clients", "artifacts/court", "artifacts/notion"])
    args = parser.parse_args()
    schemas = load_artifact_schemas()
    legacy_manifest = load_legacy_manifest()
    errors = []
    legacy_skipped = 0
    repo_root = Path.cwd().resolve()
    for raw in args.paths:
        path = Path(raw)
        if not path.exists():
            continue
        json_files = [path] if path.is_file() and path.suffix == ".json" else sorted(path.rglob("*.json"))
        for json_path in json_files:
            try:
                data = schemas._load(json_path)
                rel = json_path.resolve().relative_to(repo_root).as_posix()
                if "schema_version" not in data:
                    record = legacy_manifest.get(rel)
                    if record is None:
                        errors.append(f"{json_path}: missing schema_version and not present in legacy_artifacts_manifest.json")
                        continue
                    digest = hashlib.sha256(json_path.read_bytes()).hexdigest()
                    if digest != record["sha256"]:
                        errors.append(f"{json_path}: grandfathered file digest mismatch")
                        continue
                    legacy_skipped += 1
                    continue
                schemas.validate_artifact(json_path)
            except schemas.SchemaValidationError as exc:
                errors.append(f"{json_path}: {exc}")
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"generated JSON schemas: ok; grandfathered legacy unversioned skipped={legacy_skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
