"""Block staged or changed confidential/generated artifacts by policy."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess  # nosec B404
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_MANIFEST = REPO_ROOT / "schemas" / "artifacts" / "legacy_artifacts_manifest.json"


def git_paths(base: str | None) -> list[str]:
    if base:
        cmd = ["git", "-c", "safe.directory=C:/SintraPrime-Unified", "diff", "--name-only", f"{base}...HEAD"]
    else:
        cmd = ["git", "-c", "safe.directory=C:/SintraPrime-Unified", "diff", "--cached", "--name-only"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)  # nosec B603
    if proc.returncode != 0:
        raise SystemExit(proc.stderr or proc.stdout or "git diff failed")
    return [line.strip().replace("\\", "/") for line in proc.stdout.splitlines() if line.strip()]


def load_legacy_allowlist() -> dict[str, dict]:
    if not LEGACY_MANIFEST.exists():
        return {}
    data = json.loads(LEGACY_MANIFEST.read_text(encoding="utf-8"))
    records = data.get("grandfathered_files", []) if isinstance(data, dict) else []
    allowlist: dict[str, dict] = {}
    for record in records:
        if isinstance(record, dict) and record.get("path") and record.get("sha256"):
            allowlist[str(record["path"]).replace("\\", "/")] = record
    return allowlist


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blocked_reason(rel_path: str) -> str | None:
    normalized = rel_path.replace("\\", "/")
    if normalized.startswith(".case_runs/"):
        return "runtime state must not be staged"
    if normalized.startswith("artifacts/notion/runs/"):
        return "run-scoped dashboard snapshots must not be staged"
    if normalized.startswith("clients/CASE-"):
        return "generated client case artifacts are confidential by default"
    if normalized.startswith("artifacts/court/CASE-"):
        return "generated court artifacts are confidential by default"
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=None, help="Optional diff base for CI-style checks")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    paths = git_paths(args.base)
    allowlist = load_legacy_allowlist()
    findings: list[tuple[str, str]] = []
    for rel in paths:
        reason = blocked_reason(rel)
        allow = allowlist.get(rel)
        if allow and Path(rel).exists() and file_digest(REPO_ROOT / rel) == allow["sha256"]:
            continue
        if reason:
            findings.append((rel, reason))
    report = {"ok": not findings, "blocked_count": len(findings), "blocked_paths": [{"path": rel, "reason": reason} for rel, reason in findings]}
    if args.as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        if findings:
            for rel, reason in findings:
                print(f"BLOCKED {rel}: {reason}")
        else:
            print("confidential artifact staging guard: ok")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
