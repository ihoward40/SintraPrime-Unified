"""Deterministic certification runner for SintraPrime-Unified.

SP-CONVERGE-001 / 2A-0 — repository-owned temp policy.

Guarantees deterministic temporary storage for certification pytest runs so
host-level temp ACL problems (WinError 5 on the default pytest temp base)
can never poison a certification run. Every run gets a unique repo-local
temp root; pytest cache provider is disabled; a receipt is always written.

Usage:
  python scripts/certify.py --target default
  python scripts/certify.py --target portal --name portal-after-fix
  python scripts/certify.py --target swarm -k artifact_store

Targets:
  default  tests/ + voice_concierge/governed/tests/   (Tier 1, 651 tests)
  portal   portal/tests/                              (Tier 2)
  swarm    swarm_runtime/tests/                       (Tier 3)

Temp policy:
  artifacts/test-temp/<run_id>/       pytest --basetemp + child-process TMP
  - unique per run (never shared across concurrent runs)
  - removed on PASS, preserved on FAIL (evidence)
  - recorded in the receipt
  - pytest cache writes disabled (deterministic; no host .pytest_cache)

Receipts: artifacts/cert-receipts/<run_id>.json  (always written, PASS or FAIL)
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"

TARGETS: dict[str, list[str]] = {
    "default": ["tests/", "voice_concierge/governed/tests/"],
    "portal": ["portal/tests/"],
    "swarm": ["swarm_runtime/tests/"],
}

# Visible-lane mapping (Wave 2B): the root conftest only un-ignores a Tier-2/3
# directory when its lane name is listed in SINTRAPRIME_TEST_LANES.
LANE_ENV: dict[str, str] = {
    "default": "default",
    "portal": "default,portal",
    "swarm": "default,swarm",
}


def _git(args: list[str]) -> str:
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else "unknown"


def _python_exe() -> str:
    win = ROOT / ".venv" / "Scripts" / "python.exe"
    posix = ROOT / ".venv" / "bin" / "python"
    if win.exists():
        return str(win)
    if posix.exists():
        return str(posix)
    return sys.executable


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", choices=sorted(TARGETS), default="default")
    ap.add_argument("--name", default=None, help="optional human run name for the receipt")
    ap.add_argument("pytest_args", nargs="*", help="extra pytest args appended verbatim")
    args = ap.parse_args()

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"cert_{stamp}_{uuid.uuid4().hex[:8]}"
    label = args.name or run_id
    temp_dir = ARTIFACTS / "test-temp" / run_id
    tmp_for_children = temp_dir / "child-tmp"
    basetemp = temp_dir / "basetemp"
    basetemp.mkdir(parents=True, exist_ok=True)
    tmp_for_children.mkdir(parents=True, exist_ok=True)

    receipt_dir = ARTIFACTS / "cert-receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / f"{run_id}.json"

    python_exe = _python_exe()
    cmd = [
        python_exe,
        "-m",
        "pytest",
        *TARGETS[args.target],
        "-m",
        "not experimental",
        "--tb=short",
        "-q",
        f"--basetemp={basetemp}",
        "-p",
        "no:cacheprovider",
        *args.pytest_args,
    ]

    env = os.environ.copy()
    env["TMPDIR"] = env["TEMP"] = env["TMP"] = str(tmp_for_children)
    env["PYTHONPATH"] = str(ROOT)
    env["SINTRAPRIME_TEST_LANES"] = LANE_ENV[args.target]

    started = datetime.now(UTC).isoformat()
    t0 = time.monotonic()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    duration = time.monotonic() - t0
    finished = datetime.now(UTC).isoformat()

    stdout = proc.stdout or ""
    log_path = receipt_path.with_suffix(".stdout.txt")
    log_path.write_text(stdout, encoding="utf-8")

    # Robust summary extraction: prefer a "N passed" summary line; fall back to
    # counting progress-dot characters for quiet runs that print no summary.
    summary_match = None
    for line in stdout.splitlines():
        if re.search(r"\d+ (passed|failed|error)", line):
            summary_match = line.strip()
            break

    def grab(pattern: str) -> int:
        if not summary_match:
            return 0
        m = re.search(pattern, summary_match)
        return int(m.group(1)) if m else 0

    passed, failed, skipped = grab(r"(\d+) passed"), grab(r"(\d+) failed"), grab(r"(\d+) skipped")
    if summary_match is None:
        dots = 0
        s_count = 0
        for line in stdout.splitlines():
            stripped = line.strip()
            if re.fullmatch(r"[.sFXxXE]+(\s+\[\s*\d+%\])?", stripped):
                marks = stripped.split("[")[0].strip()
                dots += marks.count(".")
                s_count += marks.count("s")
        if dots:
            passed, skipped = dots, s_count
            summary_match = f"{passed} passed (counted from progress dots)" + (
                f", {skipped} skipped" if skipped else ""
            )

    receipt = {
        "run_id": run_id,
        "name": label,
        "target": args.target,
        "command": cmd,
        "git_sha": _git(["rev-parse", "HEAD"]),
        "branch": _git(["branch", "--show-current"]),
        "python": python_exe,
        "host": platform.platform(),
        "basetemp": str(basetemp),
        "tmp_policy": "repo-owned, per-run unique, cache provider disabled",
        "started_at": started,
        "finished_at": finished,
        "duration_seconds": round(duration, 2),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "exit_code": proc.returncode,
        "summary_line": summary_match,
        "stdout_log": str(log_path),
    }
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    cleaned = False
    if proc.returncode == 0:
        shutil.rmtree(temp_dir, ignore_errors=True)
        cleaned = True

    print(f"[certify] target={args.target} run={run_id} name={label}")
    print(f"[certify] {'PASS' if proc.returncode == 0 else 'FAIL'}: {summary_match or 'no summary parsed'}")
    print(f"[certify] temp={'cleaned' if cleaned else 'PRESERVED (failure evidence)'}: {temp_dir}")
    print(f"[certify] receipt: {receipt_path}")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
