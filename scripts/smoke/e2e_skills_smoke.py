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
    pytest_exit_code: int = -1
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
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return "unknown"
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
        try:
            resolved = Path(candidate).resolve()
            if resolved.exists():
                return str(resolved)
        except OSError:
            continue
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
    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
    except OSError:
        # Interpreter missing or not executable: count it as a failure, never a pass.
        return 0, 1, 0, -1
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
    try:
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
    except OSError as exc:
        return False, [
            {"name": "repo_truth_check.py", "status": "FAIL", "detail": type(exc).__name__}
        ]
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


def _overall(pytest_code: int, pytest_failed: int, repo_truth_passed: bool) -> str:
    """PASS only if pytest exited 0, no failures were parsed, and repo truth passed.

    The exit code is required because collection errors and similar problems can
    exit nonzero while the parsed output still shows passed tests and no failures.
    """
    if pytest_code == 0 and pytest_failed == 0 and repo_truth_passed:
        return "PASS"
    return "FAIL"


def _remove_artifacts() -> list[str]:
    """Delete the receipt, summary and timestamp; return those that could not be removed.

    The receipt goes first so a half-finished cleanup never leaves a pointer
    to evidence that no longer matches.
    """
    failed: list[str] = []
    for path in (RECEIPT_PATH, SUMMARY_PATH, TIMESTAMP_PATH):
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            failed.append(f"{path.name} ({type(exc).__name__})")
    return failed


def main() -> int:
    # Invalidate prior evidence before any check runs, so a failed or aborted
    # run can never leave an earlier PASS standing as this run's result.
    stale = _remove_artifacts()
    if stale:
        print(
            "Smoke lane: could not clear previous artifacts: " + ", ".join(stale),
            file=sys.stderr,
        )
        return 1

    started = _now()
    receipt_id = f"smoke_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{_short_ref()}"

    pytest_passed, pytest_failed, pytest_skipped, pytest_code = _run_pytest_smoke()
    repo_truth_passed, repo_truth_details = _run_repo_truth()

    finished = _now()
    started_dt = datetime.fromisoformat(started)
    finished_dt = datetime.fromisoformat(finished)
    duration = (finished_dt - started_dt).total_seconds()

    overall = _overall(pytest_code, pytest_failed, repo_truth_passed)

    summary = SmokeResult(
        overall=overall,
        pytest_passed=pytest_passed,
        pytest_failed=pytest_failed,
        pytest_skipped=pytest_skipped,
        pytest_exit_code=pytest_code,
        repo_truth_passed=repo_truth_passed,
        repo_truth_details=repo_truth_details,
        started_at=started,
        finished_at=finished,
        duration_seconds=duration,
        receipt_id=receipt_id,
        python_executable=sys.executable,
    )

    try:
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        SUMMARY_PATH.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")
        TIMESTAMP_PATH.write_text(finished, encoding="utf-8")
        # The receipt is the proof of a run, so it is published last.
        RECEIPT_PATH.write_text(receipt_id, encoding="utf-8")
    except OSError as exc:
        # Never leave partial output looking like evidence for this run.
        print(f"Smoke lane: could not write artifacts ({type(exc).__name__})", file=sys.stderr)
        leftovers = _remove_artifacts()
        if leftovers:
            print(
                "Smoke lane: could not clean up partial artifacts: " + ", ".join(leftovers),
                file=sys.stderr,
            )
        return 1

    print(f"\nSmoke lane: {overall}")
    print(
        f"  pytest: {pytest_passed} passed, {pytest_failed} failed, "
        f"{pytest_skipped} skipped (exit code {pytest_code})"
    )
    print(f"  repo_truth: {'PASS' if repo_truth_passed else 'FAIL'}")
    print(f"  receipt: {receipt_id}")
    print(f"  artifacts:")
    print(f"    {SUMMARY_PATH}")
    print(f"    {RECEIPT_PATH}")
    print(f"    {TIMESTAMP_PATH}")

    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
