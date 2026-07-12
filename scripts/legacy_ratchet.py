"""Compare legacy quality debt against a committed baseline."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

BASELINE = Path("docs/ci/legacy-ratchet-baseline.json")


def run_count(cmd: list[str]) -> tuple[int, int, str]:
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env, encoding="utf-8", errors="replace")
    output = proc.stdout + proc.stderr
    count = 0
    if "ruff" in cmd:
        for line in output.splitlines()[::-1]:
            lowered = line.lower().strip()
            if lowered.startswith("found ") and "error" in lowered:
                try:
                    count = int(lowered.split()[1])
                    break
                except Exception:
                    pass
    elif "bandit" in cmd:
        count = output.lower().count(">> issue:")
    elif "pytest" in cmd:
        count = output.count(" FAILED") + output.count(" ERROR ")
    return proc.returncode, count, output[-4000:]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    checks = {
        "ruff": [sys.executable, "-m", "ruff", "check", "."],
        "bandit": [sys.executable, "-m", "bandit", "-q", "-r", "backend", "ledger", "scripts", "-x", "backend/stripe_payments/tests"],
    }
    current = {}
    details = {}
    for name, cmd in checks.items():
        exit_code, count, output = run_count(cmd)
        current[name] = count
        details[name] = {"exit_code": exit_code, "count": count, "output_tail": output}
    if args.update_baseline or not BASELINE.exists():
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps({"schema_version": "legacy-ratchet-baseline.v1", "counts": current}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))["counts"]
    deltas = {name: current[name] - int(baseline.get(name, 0)) for name in current}
    ok = all(delta <= 0 for delta in deltas.values())
    report = {"baseline": baseline, "current": current, "delta": deltas, "details": details, "ok": ok}
    print(json.dumps(report, indent=2, sort_keys=True) if args.as_json else report)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
