"""One-way Obsidian-compatible Markdown projection for approved OmniBrain context."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable, List

from .context_packages import ContextPackage


_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|client[_-]?secret|refresh[_-]?token|access[_-]?token|password)\s*[:=]\s*\S+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    return cleaned[:100] or "item"


def _redact(text: str) -> str:
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


class ObsidianProjector:
    """Writes read-only projection files; never ingests them back into memory."""

    def __init__(self, vault_root: str):
        self.vault_root = Path(vault_root)

    def project_package(self, package: ContextPackage) -> List[Path]:
        written: List[Path] = []
        agent_dir = self.vault_root / "Agents" / _safe_name(package.scope.agent_id)
        memory_dir = self.vault_root / "Memory"
        agent_dir.mkdir(parents=True, exist_ok=True)
        memory_dir.mkdir(parents=True, exist_ok=True)

        links: List[str] = []
        for item in package.items:
            filename = f"{_safe_name(item.memory_id)}.md"
            path = memory_dir / filename
            body = _redact(item.content)
            source = item.provenance.get("source") or "unknown"
            source_id = item.provenance.get("source_id") or ""
            scope = item.scope
            content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
            frontmatter = [
                "---",
                f"id: {item.memory_id}",
                "type: memory",
                f"source: {source}",
                f"source_id: {source_id}",
                f"project_id: {scope.get('project_id') or ''}",
                f"matter_id: {scope.get('matter_id') or ''}",
                f"tenant_id: {scope.get('tenant_id') or ''}",
                f"content_sha256: {content_hash}",
                "projection: one-way",
                "---",
                "",
            ]
            path.write_text("\n".join(frontmatter) + body + "\n", encoding="utf-8")
            written.append(path)
            links.append(f"[[Memory/{filename[:-3]}]]")

        package_name = _safe_name(package.created_at.replace(":", "-"))
        index_path = agent_dir / f"context-{package_name}.md"
        index_lines = [
            "---",
            f"agent_id: {package.scope.agent_id}",
            f"user_id: {package.scope.user_id or ''}",
            f"project_id: {package.scope.project_id or ''}",
            f"matter_id: {package.scope.matter_id or ''}",
            "projection: one-way",
            "---",
            "",
            f"# Context package — {package.scope.agent_id}",
            "",
            f"Query: {_redact(package.query)}",
            "",
            *[f"- {link}" for link in links],
            "",
        ]
        index_path.write_text("\n".join(index_lines), encoding="utf-8")
        written.append(index_path)
        return written
