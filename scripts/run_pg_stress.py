#!/usr/bin/env python
"""Run 10 consecutive PostgreSQL stress iterations with a fresh DB rebuild first."""
import json
import os
import subprocess
import sys
import time

os.environ.setdefault(
    "GATE4_TEST_DATABASE_URL",
    ""  # Must be set by the caller; no embedded credentials.
)

python = os.path.join(os.path.dirname(__file__), "..", ".venv", "Scripts", "python.exe")
python = os.path.normpath(python)

# Step 1: Rebuild the disposable PostgreSQL database from scratch
print("=" * 60)
print("  REBUILDING DISPOSABLE POSTGRESQL DATABASE")
print("=" * 60, flush=True)

rebuild = subprocess.run(
    [python, "scripts/rebuild_gate4_test.py"],
    capture_output=True, text=True, timeout=120
)
print(rebuild.stdout.strip(), flush=True)
if rebuild.returncode != 0:
    print(f"  REBUILD FAILED (exit {rebuild.returncode})", flush=True)
    print(rebuild.stderr.strip())
    sys.exit(1)

# Step 2: Run 10 consecutive stress iterations
results = []
for i in range(1, 11):
    print(f"\n{'=' * 60}")
    print(f"  STRESS ITERATION {i}/10")
    print(f"{'=' * 60}", flush=True)

    start = time.time()
    proc = subprocess.run(
        [python, "-m", "pytest", "portal/tests/test_gate4_pg_concurrency.py",
         "--tb=short", "-W", "error", "-q", "--timeout=120"],
        capture_output=True, text=True, timeout=300,
    )
    elapsed = time.time() - start

    lines = proc.stdout.strip().splitlines()
    summary_line = ""
    test_count = ""
    for line in reversed(lines):
        if "passed" in line or "failed" in line or "error" in line:
            summary_line = line.strip()
            # Extract test count
            import re
            m = re.search(r'(\d+) passed', line)
            if m:
                test_count = m.group(1)
            break

    status = "PASS" if proc.returncode == 0 else "FAIL"
    results.append({
        "iteration": i,
        "status": status,
        "time_s": round(elapsed, 1),
        "exit_code": proc.returncode,
        "summary": summary_line,
        "test_count": test_count,
        "database": "gate4_test",
        "alembic_revision": "905b70986558",
    })
    print(f"  Result: {status} | Time: {elapsed:.1f}s | Exit: {proc.returncode} | {summary_line}", flush=True)

    if proc.returncode != 0:
        print(f"  STDOUT (last 20 lines):")
        for line in lines[-20:]:
            print(f"    {line}")
        break

# Write results
out_path = os.path.join(os.path.dirname(__file__), "..", "gate4_pg_stress_results.json")
out_path = os.path.normpath(out_path)
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)

passes = sum(1 for r in results if r["status"] == "PASS")
fails = sum(1 for r in results if r["status"] == "FAIL")
print(f"\n  STRESS SUMMARY: {passes} PASS / {fails} FAIL out of {len(results)}", flush=True)
