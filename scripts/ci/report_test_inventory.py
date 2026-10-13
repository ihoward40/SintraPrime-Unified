#!/usr/bin/env python3
"""Report actual pytest collection and execution outcomes for CI truth.

Collection and execution are distinct measurements. The collection-only pass
records the number of selected items before execution; an optional execution
pass records passed, failed, skipped, xfailed, xpassed, and deselected items.
Both are bound to the same supplied/resolved commit and tree.

When ``--execute`` is used, this tool writes the receipt even when pytest
reports test failures so the separate policy consumer can provide the
fail-closed verdict and the workflow can upload the evidence. The workflow
must run assert_test_floor.py after this tool.

Usage:
    python scripts/ci/report_test_inventory.py --pytest-args <suite> --out FILE
        [--commit X] [--tree Y] [--execute]
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

_PER_FILE_RE = re.compile(r"^(?:\.+[\\/])?[\w.\-/\\]+\.py:\s*(\d+)\s*$")
_SUMMARY_RE = re.compile(r"collected\s+(\d+)\s+items", re.IGNORECASE)
_ERROR_RE = re.compile(r"ERROR|error collecting|collection error", re.IGNORECASE)


class OutcomeRecorder:
    """Pytest plugin that records one final category per collected nodeid."""

    def __init__(self):
        self.outcomes: dict[str, str] = {}
        self.deselected = 0

    def pytest_deselected(self, items):
        self.deselected += len(items)

    def pytest_runtest_logreport(self, report):
        was_xfail = getattr(report, "wasxfail", None) is not None
        if was_xfail and (report.passed or report.failed):
            category = "xpassed"
        elif was_xfail and report.skipped:
            category = "xfailed"
        elif report.failed:
            category = "failed"
        elif report.skipped:
            category = "skipped"
        elif report.when == "call" and report.passed:
            category = "passed"
        else:
            # Setup/teardown passes do not represent a completed test outcome.
            return

        previous = self.outcomes.get(report.nodeid)
        # A later teardown failure must override a passing call. Preserve an
        # already-recorded terminal failure/xfail/skip against later pass hooks.
        if previous in {"failed", "xpassed", "xfailed", "skipped"} and category == "passed":
            return
        if previous == "failed" and category != "failed":
            return
        self.outcomes[report.nodeid] = category

    def counts(self) -> dict[str, int]:
        return {
            "passed": sum(value == "passed" for value in self.outcomes.values()),
            "failed": sum(value == "failed" for value in self.outcomes.values()),
            "skipped": sum(value == "skipped" for value in self.outcomes.values()),
            "xfailed": sum(value == "xfailed" for value in self.outcomes.values()),
            "xpassed": sum(value == "xpassed" for value in self.outcomes.values()),
            "deselected": self.deselected,
        }


def parse_collect_output(text: str) -> dict:
    """Parse collection totals and detected collection errors from pytest output."""
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
        match = _SUMMARY_RE.search(stripped)
        if match:
            summary = int(match.group(1))
            has_summary = True
        file_match = _PER_FILE_RE.match(stripped)
        if file_match:
            per_file += int(file_match.group(1))
    collected = summary if summary is not None else per_file
    return {
        "collected": collected,
        "summary_collected": summary,
        "per_file_collected": per_file,
        "errors": errors,
        "has_summary": has_summary,
    }


def run_collect(pytest_args: list[str] | None = None) -> dict:
    """Run pytest in collection-only mode and return a structured result."""
    command = [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"]
    if pytest_args:
        command += list(pytest_args)
    try:
        proc = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True)
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "collection_status": "error",
            "collection_command": " ".join(command),
            "collection_return_code": -1,
            "collected_count": 0,
            "parse_method": "none",
            "collection_errors": [f"subprocess failed: {exc}"],
            "incomplete": True,
            "raw_tail": "",
        }
    output = proc.stdout + proc.stderr
    parsed = parse_collect_output(output)
    incomplete = (proc.returncode != 0) or bool(parsed["errors"])
    if parsed["has_summary"]:
        parse_method = "summary-line"
    elif parsed["per_file_collected"] > 0:
        parse_method = "per-file-sum"
    else:
        parse_method = "none"
    return {
        "collection_status": "ok" if not incomplete else "error",
        "collection_command": " ".join(command),
        "collection_return_code": proc.returncode,
        "collected_count": parsed["collected"],
        "parse_method": parse_method,
        "collection_errors": parsed["errors"],
        "incomplete": incomplete or parse_method == "none",
        "authoritative": (not incomplete) and parse_method != "none",
        "raw_tail": output[-800:],
    }


def run_execution(pytest_args: list[str] | None = None) -> dict:
    """Execute the selected suite once and record final per-test outcomes."""
    recorder = OutcomeRecorder()
    args = ["-p", "no:cacheprovider", "-v", "--tb=short"]
    if pytest_args:
        args += list(pytest_args)
    try:
        import pytest

        exit_code = int(pytest.main(args, plugins=[recorder]))
        complete = exit_code in (0, 1)  # 1 is the ordinary completed-tests-failed status.
        errors: list[str] = []
    except Exception as exc:  # pragma: no cover - defensive
        exit_code = -1
        complete = False
        errors = [f"pytest execution could not complete: {type(exc).__name__}: {exc}"]
    return {
        "execution_status": "ok" if complete else "error",
        "execution_return_code": exit_code,
        "execution_complete": complete,
        "execution_errors": errors,
        **recorder.counts(),
    }


def _git(*parts: str) -> str:
    try:
        return subprocess.run(["git", *parts], cwd=REPO_ROOT, capture_output=True, text=True).stdout.strip()
    except Exception:
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pytest-args", default=None, help="Extra args passed to pytest collection/execution (comma-separated)")
    parser.add_argument("--out", default=os.path.join(REPO_ROOT, "artifacts", "ci", "test-inventory.json"))
    parser.add_argument("--commit", default=None)
    parser.add_argument("--tree", default=None)
    parser.add_argument("--execute", action="store_true", help="Also execute the selected suite and record outcomes")
    args = parser.parse_args(argv)

    extra_args = args.pytest_args.split(",") if args.pytest_args else None
    collection = run_collect(extra_args)
    result = {
        "generated_at": datetime.now(UTC).isoformat(),
        "commit": args.commit or _git("rev-parse", "HEAD"),
        "tree": args.tree or _git("rev-parse", "HEAD^{tree}"),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "collected": collection["collected_count"],
        "collection_status": collection["collection_status"],
        "collection_command": collection["collection_command"],
        "collection_return_code": collection["collection_return_code"],
        "parse_method": collection["parse_method"],
        "collection_errors": collection["collection_errors"],
        "incomplete": collection["incomplete"],
        "authoritative": collection["authoritative"],
        "passed": None,
        "failed": None,
        "skipped": None,
        "xfailed": None,
        "xpassed": None,
        "deselected": None,
        "execution_status": "not_run",
        "execution_return_code": None,
        "execution_complete": False,
        "execution_errors": [],
    }
    if args.execute:
        result.update(run_execution(extra_args))

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))

    # When execution mode is active, the policy consumer is authoritative; keep
    # the step green after recording even failed/incomplete evidence so the next
    # fail-closed assertion and always-upload step can run. Legacy collection-
    # only callers retain the original nonzero-on-incomplete behavior.
    if args.execute:
        return 0
    return 1 if collection["incomplete"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
