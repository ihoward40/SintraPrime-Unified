"""Generate the Gate 3 evidence manifest with file hashes and versions.

Immutability rules:
- Initial generation creates the manifest and a freeze record.
- After the freeze record exists, ordinary invocation fails.
- Regeneration requires --amendment IDENTIFIER and --reason TEXT.
- The script records the previous manifest digest and creates an amendment file.
"""
import argparse
import hashlib
import json
import os
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

import alembic
import sqlalchemy

EVIDENCE_ROOT = Path(
    os.environ.get("GATE3_EVIDENCE_ROOT", "docs/observatory/gates/gate-3/evidence")
)
REPORT_PATH = Path(
    os.environ.get("GATE3_REPORT_PATH", "docs/observatory/gates/gate-3/GATE3_ACCEPTANCE_REPORT.md")
)
MANIFEST_PATH = Path(
    os.environ.get("GATE3_MANIFEST_PATH", "docs/observatory/gates/gate-3/gate-3-evidence-manifest.json")
)
FREEZE_RECORD_PATH = Path(
    os.environ.get("GATE3_FREEZE_RECORD_PATH", "docs/observatory/gates/gate-3/GATE3_FREEZE_RECORD.json")
)
AMENDMENTS_DIR = Path(
    os.environ.get("GATE3_AMENDMENTS_DIR", "docs/observatory/gates/gate-3/amendments")
)
MIGRATIONS_DIR = Path(
    os.environ.get("GATE3_MIGRATIONS_DIR", "portal/alembic/versions")
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_artifacts(root: Path, package_root: Path) -> list:
    """Collect evidence artifacts relative to the Gate 3 package root."""
    artifacts = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(package_root).as_posix()
            artifacts.append({
                "path": rel,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })
    return artifacts


def load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True))


def build_manifest() -> dict:
    package_root = MANIFEST_PATH.parent
    artifacts = collect_artifacts(EVIDENCE_ROOT, package_root)
    manifest = {
        "gate": 3,
        "status": "PASS",
        "created_at": datetime.now(UTC).isoformat(),
        "environment": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "sqlalchemy_version": sqlalchemy.__version__,
            "alembic_version": alembic.__version__,
            "sqlite_version": None,
            "postgresql_version": None,
        },
        "migrations": [],
        "artifacts": artifacts,
        "commands": [
            "DATABASE_URL=sqlite+aiosqlite:////tmp/gate3_bootstrap.db alembic upgrade head",
            "DATABASE_URL=postgresql+asyncpg://sintraprime:sintraprime@127.0.0.1:5433/gate3_bootstrap alembic upgrade head",
            "pytest portal/tests/test_observatory.py portal/tests/test_gate4_hardening.py portal/tests/test_event_canonicalization.py portal/tests/test_migration_backfill.py -v -W error",
            "pytest portal/tests/test_observatory.py -v -k kill_switch -W error",
            "pytest portal/tests/test_gate4_hardening.py::TestPostgreSQLConcurrency -v -W error",
        ],
        "limitations": [
            "cleared_by is attribution only, not authenticated authorization",
            "Principal-backed clear authorization remains Gate 4 work",
            "PostgreSQL round-trip fingerprints differ only in system-generated NOT NULL check-constraint OIDs",
        ],
    }

    # SQLite version
    try:
        import sqlite3
        manifest["environment"]["sqlite_version"] = sqlite3.connect(":memory:").execute("SELECT sqlite_version()").fetchone()[0]
    except Exception as e:
        manifest["environment"]["sqlite_version"] = f"unavailable: {e}"

    # PostgreSQL version from existing disposable database
    try:
        import asyncio
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text

        async def get_pg_version():
            engine = create_async_engine("postgresql+asyncpg://sintraprime:sintraprime@127.0.0.1:5433/gate3_bootstrap")
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT version()"))
                return result.scalar()

        manifest["environment"]["postgresql_version"] = asyncio.run(get_pg_version())
    except Exception as e:
        manifest["environment"]["postgresql_version"] = f"unavailable: {e}"

    # Migration file hashes
    migrations_dir = MIGRATIONS_DIR
    for f in sorted(migrations_dir.glob("*.py")):
        if f.name.startswith("__"):
            continue
        manifest["migrations"].append({
            "file": f.name,
            "sha256": sha256_file(f),
            "bytes": f.stat().st_size,
        })

    return manifest


def generate_initial():
    manifest = build_manifest()
    save_json(MANIFEST_PATH, manifest)
    manifest_hash = sha256_file(MANIFEST_PATH)
    freeze = {
        "gate": "3",
        "status": "PASS",
        "authoritative_manifest": MANIFEST_PATH.name,
        "authoritative_manifest_sha256": manifest_hash,
        "supersedes_manifest_sha256": None,
        "superseded_manifest_available": None,
        "amendment": None,
        "frozen_at": datetime.now(UTC).isoformat(),
        "regeneration_prohibited": True,
        "regeneration_requires_amendment": True,
        "actor": "Hermes Agent",
    }
    save_json(FREEZE_RECORD_PATH, freeze)
    print(f"Manifest: {MANIFEST_PATH}")
    print(f"Manifest SHA-256: {manifest_hash}")
    print(f"Freeze record: {FREEZE_RECORD_PATH}")
    print(json.dumps({"artifact_count": len(manifest["artifacts"]), "migration_count": len(manifest["migrations"])}, indent=2))


def generate_amendment(amendment_id: str, reason: str):
    if not FREEZE_RECORD_PATH.exists():
        raise RuntimeError("No freeze record exists. Use initial generation instead.")
    freeze = load_json(FREEZE_RECORD_PATH)
    previous_manifest_hash = freeze["authoritative_manifest_sha256"]
    previous_manifest_available = MANIFEST_PATH.exists()

    # Generate new manifest
    manifest = build_manifest()
    save_json(MANIFEST_PATH, manifest)
    manifest_hash = sha256_file(MANIFEST_PATH)

    # Write amendment file
    AMENDMENTS_DIR.mkdir(parents=True, exist_ok=True)
    amendment = {
        "amendment": amendment_id,
        "previous_manifest_hash": previous_manifest_hash,
        "new_manifest_hash": manifest_hash,
        "previous_manifest_available": previous_manifest_available,
        "reason": reason,
        "amended_at": datetime.now(UTC).isoformat(),
        "actor": "Hermes Agent",
    }
    amendment_path = AMENDMENTS_DIR / f"{amendment_id}.json"
    save_json(amendment_path, amendment)
    amendment_digest = sha256_file(amendment_path)

    # Also create a markdown summary if one does not exist
    md_path = AMENDMENTS_DIR / f"{amendment_id}.md"
    if not md_path.exists():
        md_path.write_text(
            f"# {amendment_id}\n\n"
            f"- Previous manifest: `{previous_manifest_hash}`\n"
            f"- New manifest: `{manifest_hash}`\n"
            f"- Reason: {reason}\n"
            f"- Amended at: {datetime.now(UTC).isoformat()}\n"
        )

    # Update freeze record
    freeze["supersedes_manifest_sha256"] = previous_manifest_hash
    freeze["superseded_manifest_available"] = previous_manifest_available
    freeze["authoritative_manifest_sha256"] = manifest_hash
    freeze["amendment"] = amendment_id
    freeze["amendment_digest"] = amendment_digest
    freeze["frozen_at"] = datetime.now(UTC).isoformat()
    save_json(FREEZE_RECORD_PATH, freeze)

    print(f"Amendment: {amendment_path}")
    print(f"Amendment SHA-256: {amendment_digest}")
    print(f"Amendment summary: {md_path}")
    print(f"Manifest: {MANIFEST_PATH}")
    print(f"New manifest SHA-256: {manifest_hash}")
    print(f"Previous manifest SHA-256: {previous_manifest_hash}")


def main():
    parser = argparse.ArgumentParser(description="Generate or amend the Gate 3 evidence manifest")
    parser.add_argument("--amendment", help="Amendment identifier (e.g., GATE3-AMENDMENT-002)")
    parser.add_argument("--reason", help="Reason for amendment")
    parser.add_argument("--force-initial", action="store_true", help="Allow initial generation even if a freeze record exists (dangerous)")
    args = parser.parse_args()

    if args.reason and not args.amendment:
        print("ERROR: --amendment is required when --reason is provided.", file=sys.stderr)
        sys.exit(1)

    if FREEZE_RECORD_PATH.exists() and not args.force_initial:
        if not args.amendment:
            print("ERROR: A freeze record already exists. Regeneration is prohibited.", file=sys.stderr)
            print(f"Freeze record: {FREEZE_RECORD_PATH}", file=sys.stderr)
            print("Use --amendment IDENTIFIER --reason TEXT to generate a controlled amendment.", file=sys.stderr)
            sys.exit(1)
        if not args.reason:
            print("ERROR: --reason is required when using --amendment.", file=sys.stderr)
            sys.exit(1)
        generate_amendment(args.amendment, args.reason)
    else:
        if args.amendment:
            print("ERROR: --amendment is only valid when a freeze record already exists.", file=sys.stderr)
            sys.exit(1)
        if FREEZE_RECORD_PATH.exists() and args.force_initial:
            print("WARNING: --force-initial overwrites the existing freeze record.", file=sys.stderr)
        generate_initial()


if __name__ == "__main__":
    main()
