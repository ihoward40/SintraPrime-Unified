#!/usr/bin/env python3
"""Governance constitution registry validator (per CDR-0008 / CDR-0009).

Standalone, manually-run consistency checker for the Blackstone constitution
registry. Lives under `scripts/` (NOT under `governance/blackstone/`) because
`governance/blackstone/AGENTS.md` Local Contracts explicitly prohibit placing
code in that subtree ("No code, product feature, or operational schema may
be placed in this subtree.").

NOT wired into CI (deliberately: see CDR-0008 Revisit Conditions —
`GBC-2-PLAN.md` entry criteria are not yet met). Run manually:

    python scripts/governance/validate_constitution_registry.py

Checks performed:
  1. Every constitution_id in the JSON registry is unique.
  2. Every `supersedes` / `superseded_by` reference resolves to a known ID.
  3. Supersession pairs are reciprocal in BOTH directions:
       A.superseded_by == B  <=>  B.supersedes == A
       A.supersedes == B     <=>  B.superseded_by == A
  4. Every CDR referenced by a registry entry exists as a file under CDR/.
  5. Every library volume's repository_path exists on disk.
  6. Planned ecosystem constitutions have no repository_path, version, or
     sha256 (a Planned row must not assert the document exists).
  7. The Markdown registry (`constitution_registry.md`) and its JSON mirror
     (`constitution_registry.json`) describe the same set of entries with
     the same field values, so JSON/Markdown drift (CDR-0008) is detected
     rather than silently ignored.
  8. Every CDR file has a corresponding row in `CDR/INDEX.md`.

Exit code 0 = all checks passed. Exit code 1 = one or more checks failed.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BKR_DIR = REPO_ROOT / "governance" / "blackstone" / "volume-6-bkr"
REGISTRY_JSON = BKR_DIR / "REGISTRIES" / "constitution_registry.json"
REGISTRY_MD = BKR_DIR / "REGISTRIES" / "constitution_registry.md"
CDR_DIR = BKR_DIR / "CDR"
BLACKSTONE_ROOT = BKR_DIR.parent

EM_DASH_FIELDS = {"—", "-", ""}


def load_registry_json() -> dict:
    with REGISTRY_JSON.open("r", encoding="utf-8") as f:
        return json.load(f)


def _normalize(value):
    if value is None:
        return None
    value = value.strip().strip("`")
    if value in EM_DASH_FIELDS:
        return None
    return value


def _normalize_sha256(value):
    """Treat the registry's "not computed[...]" placeholder prose as null,
    matching the JSON mirror's `sha256: null` for unratified/undrafted
    volumes (see constitution_registry.md Rule 4)."""
    value = _normalize(value)
    if value is not None and value.lower().startswith("not computed"):
        return None
    return value


def _parse_md_table(markdown: str, header_marker: str) -> list:
    """Parse a pipe-delimited Markdown table following `header_marker`."""
    lines = markdown.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == header_marker)
    except StopIteration:
        return []

    table_lines = []
    for line in lines[start + 1:]:
        stripped = line.strip()
        if stripped.startswith("|"):
            table_lines.append(stripped)
        elif table_lines:
            break

    if len(table_lines) < 2:
        return []

    header_cells = [c.strip() for c in table_lines[0].strip("|").split("|")]
    rows = []
    for row_line in table_lines[2:]:  # skip header + separator row
        cells = [c.strip() for c in row_line.strip("|").split("|")]
        if len(cells) != len(header_cells):
            continue
        rows.append(dict(zip(header_cells, cells)))
    return rows


def parse_md_registry():
    markdown = REGISTRY_MD.read_text(encoding="utf-8")

    library_rows = _parse_md_table(markdown, "## Entries — Library Volumes")
    volumes = []
    for row in library_rows:
        volumes.append(
            {
                "constitution_id": _normalize(row.get("Constitution ID")),
                "version": _normalize(row.get("Version (see CHANGELOG)")),
                "status": _normalize(row.get("Status")),
                "supersedes": _normalize(row.get("Supersedes")),
                "superseded_by": _normalize(row.get("Superseded By")),
                "sha256": _normalize_sha256(row.get("SHA-256")),
                "cdr": _normalize(row.get("CDR")),
                "repository_path": _normalize(row.get("Repository Path")),
            }
        )

    ecosystem_rows = _parse_md_table(
        markdown, "## Entries — Ecosystem Constitutions (Planned)"
    )
    ecosystem = []
    for row in ecosystem_rows:
        ecosystem.append(
            {
                "constitution_id": _normalize(row.get("Constitution ID")),
                "version": _normalize(row.get("Version")),
                "status": _normalize(row.get("Status")),
                "repository_path": _normalize(row.get("Repository Path")),
            }
        )
    return volumes, ecosystem


def flatten_cdr_refs(entry: dict) -> list:
    cdr = entry.get("cdr")
    if cdr is None:
        return []
    if isinstance(cdr, list):
        return cdr
    if isinstance(cdr, str):
        # MD cells may hold multiple CDR IDs separated by commas.
        return [c.strip() for c in re.split(r"[,\s]+", cdr) if c.strip()]
    return []


def _sha_matches(json_val, md_val) -> bool:
    """Compare SHA-256 fields (both already normalized to None or a hash)."""
    return json_val == md_val


def main() -> int:
    errors = []
    warnings = []

    registry = load_registry_json()
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

    # 2. Resolvable supersession references (library volumes only).
    for e in volumes:
        for field in ("supersedes", "superseded_by"):
            ref = e.get(field)
            if ref is not None and ref not in known_ids:
                errors.append(
                    f"{e['constitution_id']}.{field} references unknown ID '{ref}'"
                )

    # 3. Reciprocal supersession, checked in BOTH directions.
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
        sup = e.get("supersedes")
        if sup and sup in by_id:
            other = by_id[sup]
            if other.get("superseded_by") != cid:
                errors.append(
                    f"Non-reciprocal supersession: {cid}.supersedes={sup} "
                    f"but {sup}.superseded_by={other.get('superseded_by')!r}"
                )

    # 4. CDR references resolve to files.
    for e in all_entries:
        for cdr_id in flatten_cdr_refs(e):
            cdr_file = CDR_DIR / f"{cdr_id}.md"
            if not cdr_file.exists():
                errors.append(
                    f"{e['constitution_id']} references {cdr_id}, "
                    f"but {cdr_file} does not exist"
                )

    # 5. Library volume repository paths exist.
    for e in volumes:
        path = e.get("repository_path")
        if path:
            full_path = BLACKSTONE_ROOT / path
            if not full_path.exists():
                errors.append(
                    f"{e['constitution_id']}.repository_path does not exist: {path}"
                )

    # 6. Planned rows assert nothing about existence.
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

    # 7. Markdown/JSON mirror consistency.
    md_volumes, md_ecosystem = parse_md_registry()
    md_by_id = {r["constitution_id"]: r for r in md_volumes if r.get("constitution_id")}
    json_by_id = {e["constitution_id"]: e for e in volumes}

    if set(md_by_id) != set(json_by_id):
        only_md = set(md_by_id) - set(json_by_id)
        only_json = set(json_by_id) - set(md_by_id)
        if only_md:
            errors.append(f"Markdown has library-volume IDs missing from JSON: {sorted(only_md)}")
        if only_json:
            errors.append(f"JSON has library-volume IDs missing from Markdown: {sorted(only_json)}")

    for cid in sorted(set(md_by_id) & set(json_by_id)):
        md_row = md_by_id[cid]
        json_row = json_by_id[cid]
        for field in ("status", "supersedes", "superseded_by", "repository_path"):
            md_val = md_row.get(field)
            json_val = json_row.get(field)
            if md_val != json_val:
                errors.append(
                    f"{cid}.{field} differs between Markdown ({md_val!r}) "
                    f"and JSON ({json_val!r})"
                )
        if not _sha_matches(json_row.get("sha256"), md_row.get("sha256")):
            errors.append(
                f"{cid}.sha256 differs between Markdown ({md_row.get('sha256')!r}) "
                f"and JSON ({json_row.get('sha256')!r})"
            )

    md_eco_by_id = {r["constitution_id"]: r for r in md_ecosystem if r.get("constitution_id")}
    json_eco_by_id = {e["constitution_id"]: e for e in ecosystem}
    if set(md_eco_by_id) != set(json_eco_by_id):
        errors.append(
            "Ecosystem constitution IDs differ between Markdown "
            f"({sorted(md_eco_by_id)}) and JSON ({sorted(json_eco_by_id)})"
        )

    # 8. CDR index cross-check: every CDR file has a row in INDEX.md.
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
