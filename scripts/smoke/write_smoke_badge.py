#!/usr/bin/env python3
"""
Smoke Badge Writer — SintraPrime-Unified
========================================

Reads `artifacts/last_smoke_summary.json` and refreshes the smoke status
badge in README.md.

Usage:
    python scripts/smoke/write_smoke_badge.py
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
README = ROOT / "README.md"
SUMMARY = ROOT / "artifacts" / "last_smoke_summary.json"

BADGE_RE = re.compile(
    r"\[!\[Smoke: [^\]]*\]\([^\)]*\)\]\([^\)]*\)"
)


def _insert_after_first_badge_block(lines: list[str], badge_line: str) -> list[str]:
    """Insert after the first contiguous block of header badges (before first blank line)."""
    last_badge = -1
    for idx, line in enumerate(lines):
        if line.strip() == "":
            if last_badge != -1:
                lines.insert(last_badge + 1, badge_line + "\n")
                return lines
        elif line.startswith("[!["):
            last_badge = idx
    # Fallback: prepend if no block found
    lines.insert(0, badge_line + "\n")
    return lines


@dataclass(frozen=True)
class Badge:
    label: str
    message: str
    color: str

    def markdown(self, link: str = "https://github.com/ihoward40/SintraPrime-Unified/actions/workflows/smoke.yml") -> str:
        shield = f"https://img.shields.io/badge/{self.label}-{self.message}-{self.color}?style=for-the-badge"
        return f"[![Smoke: {self.message}]({shield})]({link})"


def _choose_badge(summary: dict) -> Badge:
    overall = summary.get("overall", "FAIL")
    if overall == "PASS":
        return Badge("smoke", "passing", "brightgreen")
    return Badge("smoke", "failing", "red")


def main() -> int:
    if not SUMMARY.exists():
        print(f"ERROR: {SUMMARY} not found — run scripts/smoke/e2e_skills_smoke.py first", file=sys.stderr)
        return 1

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    badge = _choose_badge(summary)

    if not README.exists():
        print(f"ERROR: {README} not found", file=sys.stderr)
        return 1

    original = README.read_text(encoding="utf-8")
    new_badge = badge.markdown()

    if BADGE_RE.search(original):
        updated = BADGE_RE.sub(new_badge, original, count=1)
    else:
        # Insert inside the first contiguous block of header badges.
        lines = original.splitlines(keepends=True)
        updated = "".join(_insert_after_first_badge_block(lines, new_badge))

    README.write_text(updated, encoding="utf-8")
    print(f"Updated README smoke badge: {badge.message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
