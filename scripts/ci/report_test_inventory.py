#!/usr/bin/env python3
"""Report actual pytest inventory for CI truth.

This tool replaces hardcoded test totals in documentation. It runs pytest in
collection-only mode, captures the real collected count, and records
environment metadata plus the collection command's return code and any errors.

Design guarantees (per convergence requirements):
- The collection command's return code is always captured.
- If collection fails (non-zero return code) or emits errors, the result is
  marked `incomplete` and the count is NOT reported as authoritative.
- A parse failure never silently reports 0; the status reflects the failure.
- Both the per-file summary (`tests/test_x.py: 42`) and the summary line
  (`collected N items`) are parsed, on Windows and Linux path formats.
- No test behavior is changed; this is documentation/CI truth only.

Usage:
    python scripts/ci/report_test_inventory.py [--pytest-args ...] [--out FILE]
                                                [--commit X] [--tree Y]
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
from datetime import UTC, datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Per-file collect line, e.g. "tests/test_x.py: 42" or Windows "tests\\test_x.py: 42"
_PER_FILE_RE = re.compile(r"^(?:\.+[\\/])?[\w.\-/\\]+\.py:\s*(\d+)\s*$")
# Summary line, e.g. "collected 147 items" or "collected 147 items / 3 errors"
_SUMMARY_RE = re.compile(r"collected\s+(\d+)\s+items", re.IGNORECASE)
_ERROR_RE = re.compile(r"ERROR|error collecting|collection error", re.IGNORECASE)


def parse_collect_output(text: str) -> dict:
    """Pure parser for pytest --collect-only output.

    Returns a dict with:
        collected (int): best-effort collected count (may be 0 if undetectable)
        summary_collected (int|None): count from 'collected N items' line
        per_file_collected (int): sum of per-file ': N' lines
        errors (list[str]): error/warning lines detected
        has_summary (bool): a 'collected N items' line was present
    """
    lines = text.splitlines()
    errors: list[str] = []
    per_file = 0
    summary = None
    has_summary = False
    for line in lines:
        stripped = line.strip()
        if _ERROR_RE.search(stripped) and (
            "error" in stripped.lower()
            and ("collect" in stripped.lower() or "import" in stripped.lower() or "ERROR" in stripped)
        ):
            errors.append(stripped)
        m = _SUMMARY_RE.search(stripped)
        if m:
            summary = int(m.group(1))
            has_summary = True
        fm = _PER_FILE_RE.match(stripped)
        if fm:
            per_file += int(fm.group(1))
    # Prefer the explicit summary line when present; fall back to per-file sum.
    collected = summary if summary is not None else per_file
    return {
        "collected": collected,
        "summary_collected": summary,
        "per_file_collected": per_file,
        "errors": errors,
        "has_summary": has_summary,
    }


def run_collect(pytest_args: list[str] | None = None) -> dict:
    """Run pytest --collect-only and return structured collection result."""
    cmd = [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"]
    if pytest_args:
        cmd += list(pytest_args)
    try:
        proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "collection_status": "error",
            "collection_command": " ".join(cmd),
            "collection_return_code": -1,
            "collected_count": 0,
            "parse_method": "none",
            "collection_errors": [f"subprocess failed: {exc}"],
            "incomplete": True,
            "raw_tail": "",
        }
    out = proc.stdout + proc.stderr
    parsed = parse_collect_output(out)
    rc = proc.returncode
    # A non-zero return code, or any detected collection error, means the
    # inventory is incomplete and must not be reported as authoritative.
    incomplete = (rc != 0) or bool(parsed["errors"])
    if parsed["has_summary"]:
        parse_method = "summary-line"
    elif parsed["per_file_collected"] > 0:
        parse_method = "per-file-sum"
    else:
        parse_method = "none"
    return {
        "collection_status": "ok" if not incomplete else "error",
        "collection_command": " ".join(cmd),
        "collection_return_code": rc,
        "collected_count": parsed["collected"],
        "parse_method": parse_method,
        "collection_errors": parsed["errors"],
        "incomplete": incomplete,
        "authoritative": (not incomplete) and parse_method != "none",
        "raw_tail": out[-800:],
    }


def _git(*parts: str) -> str:
    try:
        return subprocess.run(
            ["git", *parts], cwd=REPO_ROOT, capture_output=True, text=True
        ).stdout.strip()
    except Exception:
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pytest-args", default=None,
                    help="Extra args passed to pytest collect (comma-separated)")
    ap.add_argument("--out",
                    default=os.path.join(REPO_ROOT, "artifacts", "ci", "test-inventory.json"))
    ap.add_argument("--commit", default=None)
    ap.add_argument("--tree", default=None)
    args = ap.parse_args()

    extra = args.pytest_args.split(",") if args.pytest_args else None
    collect = run_collect(extra)

    result = {
        "generated_at": datetime.now(UTC).isoformat(),
        "commit": args.commit or _git("rev-parse", "HEAD"),
        "tree": args.tree or _git("rev-parse", "HEAD^{tree}"),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "collected": collect["collected_count"],
        "collection_status": collect["collection_status"],
        "collection_command": collect["collection_command"],
        "collection_return_code": collect["collection_return_code"],
        "parse_method": collect["parse_method"],
        "collection_errors": collect["collection_errors"],
        "incomplete": collect["incomplete"],
        "authoritative": (not collect["incomplete"]) and collect["parse_method"] != "none",
        "passed": None,
        "failed": None,
        "skipped": None,
        "xfailed": None,
        "xpassed": None,
        "warnings": None,
        "duration": None,
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))
    # Exit non-zero if collection was incomplete so CI does not publish a false total.
    return 1 if collect["incomplete"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
