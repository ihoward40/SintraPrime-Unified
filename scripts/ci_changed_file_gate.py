"""Changed-file CI gate for remediation work.

Runs blocking checks only against changed files where possible, while invoking
repository-specific validators that are safe and scoped.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess  # nosec B404
import sys
from pathlib import Path

SENSITIVE_PATTERNS = ("backend/stripe_payments", "ledger", "scripts", "orchestration/enforcement")
BASELINE_PATH = Path("docs/ci/changed-file-baseline.json")


def run(cmd: list[str]) -> dict:
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env, encoding="utf-8", errors="replace")
    return {"cmd": cmd, "exit_code": proc.returncode, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:]}


def parse_ruff_count(output: str) -> int:
    for line in output.splitlines()[::-1]:
        lowered = line.lower().strip()
        if lowered.startswith("found ") and "error" in lowered:
            try:
                return int(lowered.split()[1])
            except (IndexError, ValueError):
                return 1
    return 0


def parse_bandit_count(output: str) -> int:
    return output.lower().count(">> issue:")


def load_baseline() -> dict:
    if not BASELINE_PATH.exists():
        return {"ruff": {}, "bandit": {}}
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8")).get("counts", {"ruff": {}, "bandit": {}})


def per_file_gate(tool: str, files: list[str], baseline: dict) -> list[dict]:
    results: list[dict] = []
    for file in files:
        if tool == "ruff":
            result = run([sys.executable, "-m", "ruff", "check", file])
            count = parse_ruff_count(result["stdout"] + result["stderr"])
        else:
            result = run([sys.executable, "-m", "bandit", "-q", file])
            count = parse_bandit_count(result["stdout"] + result["stderr"])
        allowed = int(baseline.get(tool, {}).get(file, 0))
        result.update({"tool": tool, "file": file, "count": count, "allowed": allowed, "gate_ok": count <= allowed})
        results.append(result)
    return results


def changed_files(base: str) -> list[str]:
    proc = subprocess.run(["git", "-c", "safe.directory=C:/SintraPrime-Unified", "diff", "--name-only", f"{base}...HEAD"], capture_output=True, text=True, check=False)  # nosec B603,B607
    tracked = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    untracked_proc = subprocess.run(["git", "-c", "safe.directory=C:/SintraPrime-Unified", "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True, check=False)  # nosec B603,B607
    untracked = [line.strip() for line in untracked_proc.stdout.splitlines() if line.strip()] if untracked_proc.returncode == 0 else []
    return sorted(set(tracked + untracked))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    files = changed_files(args.base)
    py_files = [f for f in files if f.endswith(".py") and Path(f).exists()]
    sensitive = [f for f in py_files if any(f.startswith(prefix) for prefix in SENSITIVE_PATTERNS) and "/tests/" not in f.replace("\\", "/")]
    baseline = load_baseline()
    results = []
    results.extend(per_file_gate("ruff", py_files, baseline))
    results.extend(per_file_gate("bandit", sensitive, baseline))
    results.append(run([sys.executable, "scripts/validate_generated_json.py", "clients", "artifacts/court", "artifacts/notion"]))
    results.append(run([sys.executable, "ledger/verify_ledger.py"]))
    results.append(run([sys.executable, "scripts/scan_secrets.py"]))
    results.append(run([sys.executable, "scripts/check_confidential_artifacts.py", "--base", args.base]))
    failed = [r for r in results if ("gate_ok" in r and not r["gate_ok"]) or ("gate_ok" not in r and r["exit_code"] != 0)]
    report = {"changed_files": files, "python_files": py_files, "results": results, "ok": not failed}
    if args.as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for result in results:
            print(f"{' '.join(result['cmd'])}: exit {result['exit_code']}")
            if result["stdout"]:
                print(result["stdout"])
            if result["stderr"]:
                print(result["stderr"])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
