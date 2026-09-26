"""One-way Obsidian projection (SP-OMNIBRAIN-RUNTIME-001 Phase 11).

Projection ONLY: SintraPrime -> Obsidian markdown files. The vault is never
a source of truth for the runtime; nothing reads the vault back into
governed state (no reverse parser is provided, by design).

Layout (directive Phase 11):
    /Missions /Agents /Memory /Evidence /Decisions /Receipts /Entities /Relationships

Stable IDs are embedded as front-matter keys so cross-links survive
re-projection. Projections are idempotent: re-projecting the same facts
produces the same bytes.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

SECTION_DIRS = ("Missions", "Agents", "Memory", "Evidence",
                "Decisions", "Receipts", "Entities", "Relationships")


@dataclass(frozen=True)
class ProjectedNote:
    relative_path: str
    content: str


def _front_matter(note_type: str, note_id: str, links: Mapping[str, str]) -> str:
    lines = ["---", f"type: {note_type}", f"id: {note_id}"]
    for key, target in links.items():
        lines.append(f"{key}: \"[[{target}]]\"")
    lines.append("---")
    return "\n".join(lines)


def project_note(*, section: str, note_id: str, title: str, body: str,
                 note_type: str = "note", links: Mapping[str, str] | None = None) -> ProjectedNote:
    """Build one markdown note with stable-ID front matter and wikilinks."""
    if section not in SECTION_DIRS:
        raise ValueError(f"unknown projection section: {section!r}")
    fm = _front_matter(note_type, note_id, links or {})
    content = f"{fm}\n\n# {title}\n\n{body.rstrip()}\n"
    return ProjectedNote(relative_path=f"{section}/{note_id}.md", content=content)


def project_relationship_note(edge_dicts: Iterable[Mapping[str, object]]) -> ProjectedNote:
    """One Relationships note enumerating provenance edges as a stable table."""
    rows = ["| relation | source | target |", "|---|---|---|"]
    for e in edge_dicts:
        rows.append(
            f"| {e.get('relation')} | {e.get('source_type')}:{e.get('source_id')} "
            f"| {e.get('target_type')}:{e.get('target_id')} |"
        )
    body = "Provenance edges (read-only projection).\n\n" + "\n".join(rows) + "\n"
    return ProjectedNote(relative_path="Relationships/provenance-edges.md", content=body)


def write_vault(root: Path, notes: Iterable[ProjectedNote]) -> list[str]:
    """Idempotently write notes under root. Returns written relative paths."""
    root = Path(root)
    written: list[str] = []
    for note in notes:
        target = root / note.relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        existing = target.read_text(encoding="utf-8") if target.exists() else None
        if existing != note.content:
            target.write_text(note.content, encoding="utf-8", newline="\n")
        written.append(note.relative_path)
    return sorted(written)
