"""Lightweight fail-closed secret-pattern scan for tracked files."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    re.compile(r"sk_live_[A-Za-z0-9_]{16,}"),
    re.compile(r"whsec_[A-Za-z0-9_]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]
ALLOWLIST = {
    ".bandit-baseline.json",
    "backend/stripe_payments/.env.example",
    "backend/stripe_payments/README.md",
    "backend/stripe_payments/STRIPE_SETUP.md",
    "backend/stripe_payments/config.py",
    "esignature/tests/test_esignature.py",
    "phase18/stripe_webhooks/tests/test_webhook_handler.py",
    "phase19/revenue_smoke_test/test_config.py",
}


def main() -> int:
    git = shutil.which("git")
    if not git:
        print("git executable not found")
        return 1
    proc = subprocess.run([git, "-c", "safe.directory=C:/SintraPrime-Unified", "ls-files"], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        print(proc.stderr)
        return proc.returncode
    findings = []
    for raw in proc.stdout.splitlines():
        if raw in ALLOWLIST:
            continue
        path = Path(raw)
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in PATTERNS:
            if pattern.search(text):
                findings.append(raw)
                break
    if findings:
        print("potential secrets found in tracked files:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("secret scan: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
