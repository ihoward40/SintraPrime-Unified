#!/usr/bin/env python3
"""
E2E Skills Smoke Runner — SintraPrime-Unified
===============================================

Runs the smoke test lane:
  1. Pytest tests marked with `@pytest.mark.smoke`
  2. scripts/smoke/repo_truth_check.py

Writes deterministic artifacts:
  - artifacts/last_smoke_summary.json
  - artifacts/last_smoke_receipt_ref.txt
  - artifacts/last_smoke_timestamp.txt

Exit code 0 = smoke lane passed. Non-zero = at least one failure.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACTS = ROOT / "artifacts"
SUMMARY_PATH = ARTIFACTS / "last_smoke_summary.json"
RECEIPT_PATH = ARTIFACTS / "last_smoke_receipt_ref.txt"
TIMESTAMP_PATH = ARTIFACTS / "last_smoke_timestamp.txt"


@dataclass
class SmokeResult:
    overall: str = "pending"
    pytest_passed: int = 0
    pytest_failed: int = 0
    pytest_skipped: int = 0
    repo_truth_passed: bool = False
    repo_truth_details: list[dict] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""
    duration_seconds: float = 0.0
    receipt_id: str = ""
    python_executable: str = ""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _short_ref() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _python_executable() -> str:
    # Prefer the project virtual environment interpreter; fall back to the
    # interpreter running this script so paths remain deterministic in CI.
    candidates = [
        ROOT / ".venv" / "Scripts" / "python.exe",
        ROOT / ".venv" / "bin" / "python",
        Path(sys.executable),
    ]
    for candidate in candidates:
        resolved = Path(candidate).resolve()
        if resolved.exists():
            return str(resolved)
    return sys.executable


def _run_pytest_smoke() -> tuple[int, int, int, int]:
    cmd = [
        _python_executable(),
        "-m",
        "pytest",
        "-o",
        "addopts=",
        "-m",
        "smoke",
        "-q",
        "--tb=short",
        "--import-mode=importlib",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    # Parse summary line like "3 passed, 390 deselected, 2 warnings in 1.33s"
    passed = failed = skipped = 0
    for line in result.stdout.splitlines():
        if re.search(r"\b\d+\s+passed\b", line):
            match = re.search(r"(\d+)\s+passed", line)
            if match:
                passed = int(match.group(1))
        if re.search(r"\b\d+\s+failed\b", line):
            match = re.search(r"(\d+)\s+failed", line)
            if match:
                failed = int(match.group(1))
        if re.search(r"\b\d+\s+skipped\b", line):
            match = re.search(r"(\d+)\s+skipped", line)
            if match:
                skipped = int(match.group(1))
    # If pytest found no smoke tests, treat as failure unless explicitly allowed.
    if result.returncode != 0 and passed == 0 and failed == 0:
        failed = 1
    return passed, failed, skipped, result.returncode


def _run_repo_truth() -> tuple[bool, list[dict]]:
    script = ROOT / "scripts" / "smoke" / "repo_truth_check.py"
    if not script.exists():
        return False, [
            {"name": "repo_truth_check.py", "status": "FAIL", "detail": "script missing"}
        ]

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    # repo_truth_check prints summary but does not emit JSON; infer from exit code.
    passed = result.returncode == 0
    details = [
        {
            "name": "repo_truth_check.py",
            "status": "PASS" if passed else "FAIL",
            "detail": result.stdout[-500:],
        }
    ]
    return passed, details


def main() -> int:
    started = _now()
    receipt_id = f"smoke_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{_short_ref()}"

    ARTIFACTS.mkdir(parents=True, exist_ok=True)

    pytest_passed, pytest_failed, pytest_skipped, _pytest_code = _run_pytest_smoke()
    repo_truth_passed, repo_truth_details = _run_repo_truth()

    finished = _now()
    started_dt = datetime.fromisoformat(started)
    finished_dt = datetime.fromisoformat(finished)
    duration = (finished_dt - started_dt).total_seconds()

    overall = "PASS" if pytest_failed == 0 and repo_truth_passed else "FAIL"

    summary = SmokeResult(
        overall=overall,
        pytest_passed=pytest_passed,
        pytest_failed=pytest_failed,
        pytest_skipped=pytest_skipped,
        repo_truth_passed=repo_truth_passed,
        repo_truth_details=repo_truth_details,
        started_at=started,
        finished_at=finished,
        duration_seconds=duration,
        receipt_id=receipt_id,
        python_executable=sys.executable,
    )

    SUMMARY_PATH.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")
    RECEIPT_PATH.write_text(receipt_id, encoding="utf-8")
    TIMESTAMP_PATH.write_text(finished, encoding="utf-8")

    print(f"\nSmoke lane: {overall}")
    print(f"  pytest: {pytest_passed} passed, {pytest_failed} failed, {pytest_skipped} skipped")
    print(f"  repo_truth: {'PASS' if repo_truth_passed else 'FAIL'}")
    print(f"  receipt: {receipt_id}")
    print(f"  artifacts:")
    print(f"    {SUMMARY_PATH}")
    print(f"    {RECEIPT_PATH}")
    print(f"    {TIMESTAMP_PATH}")

    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
