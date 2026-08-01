#!/usr/bin/env python3
"""Governance registry validator (BKR tooling, per CDR-0008).

Standalone, manually-run consistency checker for the constitution registry.
NOT wired into CI — see CDR-0008 "Revisit Conditions" for when that should
be proposed. Run from anywhere:

    python governance/blackstone/volume-6-bkr/REGISTRIES/validate_registry.py

Checks performed:
  1. Every constitution_id in the JSON registry is unique.
  2. Every `supersedes` / `superseded_by` reference resolves to a known ID.
  3. Supersession pairs are reciprocal (A.superseded_by == B  <=>  B.supersedes == A).
  4. Every CDR referenced by a registry entry exists as a file under CDR/.
  5. Every library volume's repository_path exists on disk.
  6. Planned ecosystem constitutions have no repository_path, version, or sha256
     (a Planned row must not assert the document exists).

Exit code 0 = all checks passed. Exit code 1 = one or more checks failed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BKR_DIR = Path(__file__).resolve().parent.parent
REGISTRY_JSON = BKR_DIR / "REGISTRIES" / "constitution_registry.json"
CDR_DIR = BKR_DIR / "CDR"
BLACKSTONE_ROOT = BKR_DIR.parent


def load_registry() -> dict:
    with REGISTRY_JSON.open("r", encoding="utf-8") as f:
        return json.load(f)


def flatten_cdr_refs(entry: dict) -> list[str]:
    cdr = entry.get("cdr")
    if cdr is None:
        return []
    if isinstance(cdr, list):
        return cdr
    return [cdr]


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    registry = load_registry()
    volumes = registry.get("library_volumes", [])
    ecosystem = registry.get("ecosystem_constitutions", [])
    all_entries = volumes + ecosystem

    # 1. Unique IDs
    ids = [e["constitution_id"] for e in all_entries]
    seen = set()
    for cid in ids:
        if cid in seen:
            errors.append(f"Duplicate constitution_id: {cid}")
        seen.add(cid)

    known_ids = set(ids)

    # 2. Resolvable supersession references (library volumes only; ecosystem
    #    entries currently carry no supersession fields).
    for e in volumes:
        for field in ("supersedes", "superseded_by"):
            ref = e.get(field)
            if ref is not None and ref not in known_ids:
                errors.append(
                    f"{e['constitution_id']}.{field} references unknown ID '{ref}'"
                )

    # 3. Reciprocal supersession
    by_id = {e["constitution_id"]: e for e in volumes}
    for e in volumes:
        cid = e["constitution_id"]
        sb = e.get("superseded_by")
        if sb and sb in by_id:
            other = by_id[sb]
            if other.get("supersedes") != cid:
                errors.append(
                    f"Non-reciprocal supersession: {cid}.superseded_by={sb} "
                    f"but {sb}.supersedes={other.get('supersedes')!r}"
                )

    # 4. CDR references resolve to files
    for e in all_entries:
        for cdr_id in flatten_cdr_refs(e):
            cdr_file = CDR_DIR / f"{cdr_id}.md"
            if not cdr_file.exists():
                errors.append(
                    f"{e['constitution_id']} references {cdr_id}, "
                    f"but {cdr_file} does not exist"
                )

    # 5. Library volume repository paths exist
    for e in volumes:
        path = e.get("repository_path")
        if path:
            full_path = BLACKSTONE_ROOT / path
            if not full_path.exists():
                errors.append(
                    f"{e['constitution_id']}.repository_path does not exist: {path}"
                )

    # 6. Planned rows assert nothing about existence
    for e in ecosystem:
        if e.get("status") == "Planned":
            if e.get("repository_path") not in (None, "not yet created"):
                errors.append(
                    f"Planned entry {e['constitution_id']} has a non-null "
                    f"repository_path: {e.get('repository_path')!r}"
                )
            if e.get("version") is not None:
                errors.append(
                    f"Planned entry {e['constitution_id']} has a non-null version"
                )
        else:
            warnings.append(
                f"Ecosystem entry {e['constitution_id']} has status "
                f"'{e.get('status')}' (expected 'Planned' until drafted)"
            )

    # 7. CDR index cross-check: every CDR file has a row in INDEX.md
    index_path = CDR_DIR / "INDEX.md"
    if index_path.exists():
        index_text = index_path.read_text(encoding="utf-8")
        for cdr_file in sorted(CDR_DIR.glob("CDR-*.md")):
            cdr_id = cdr_file.stem
            if cdr_id not in index_text:
                errors.append(f"{cdr_id}.md has no row in CDR/INDEX.md")
    else:
        warnings.append("CDR/INDEX.md not found; skipped CDR index cross-check")

    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print("Errors:")
        for e in errors:
            print(f"  - {e}")
        print(f"\nFAILED: {len(errors)} error(s), {len(warnings)} warning(s).")
        return 1

    print(f"OK: all checks passed ({len(warnings)} warning(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
