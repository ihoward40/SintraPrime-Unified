"""Check bandit results for new HIGH findings using semantic comparison.

Bandit's --baseline flag matches by (filename, test_id, line_number, severity).
When line numbers shift due to formatting changes (e.g., Ruff remediation),
baseline matching fails and previously-accepted findings appear as "new".

This script performs semantic comparison: findings are matched by
(test_id, normalized_filename) regardless of line number. Only truly new
findings — those not in the baseline at ANY line number for the same
test_id in the same file — are reported.

Usage in CI:
  bandit -r . -x tests/,portal/tests/ -ll -f json -o /tmp/bandit.json
  python scripts/check_bandit.py

The baseline file (.bandit-baseline.json) is read directly by this script,
NOT passed to Bandit via --baseline.
"""

import json
import sys
from pathlib import Path


def normalize_filename(fn: str) -> str:
    """Normalize path separators for cross-platform comparison.

    .\\agents\\nova\\nova_agent.py  ->  agents/nova/nova_agent.py
    ./agents/nova/nova_agent.py     ->  agents/nova/nova_agent.py
    """
    return fn.replace("\\", "/").lstrip("./")


def main() -> int:
    # Load current scan results (run WITHOUT --baseline)
    bandit_path = Path("/tmp/bandit.json")
    if not bandit_path.exists():
        print("FAIL: /tmp/bandit.json not found — run bandit first")
        return 2

    with open(bandit_path) as f:
        current_data = json.load(f)

    # Load historical baseline
    baseline_path = Path(".bandit-baseline.json")
    if not baseline_path.exists():
        print("FAIL: .bandit-baseline.json not found")
        return 2

    with open(baseline_path) as f:
        baseline_data = json.load(f)

    # Build baseline index: (test_id, normalized_filename) -> True
    baseline_index: set[tuple[str, str]] = set()
    for r in baseline_data.get("results", []):
        key = (r.get("test_id", ""), normalize_filename(r.get("filename", "")))
        baseline_index.add(key)

    # Compare current findings against baseline semantically
    current_results = current_data.get("results", [])
    truly_new: list[dict] = []
    semantic_match = 0

    for r in current_results:
        key = (r.get("test_id", ""), normalize_filename(r.get("filename", "")))
        if key in baseline_index:
            semantic_match += 1
        else:
            truly_new.append(r)

    new_high = [r for r in truly_new if r.get("issue_severity") == "HIGH"]
    new_medium = [r for r in truly_new if r.get("issue_severity") == "MEDIUM"]

    print(f"Bandit semantic comparison:")
    print(f"  Total current findings: {len(current_results)}")
    print(f"  Semantic matches in baseline: {semantic_match}")
    print(f"  Truly new findings: {len(truly_new)}")
    print(f"  New HIGH: {len(new_high)}")
    print(f"  New MEDIUM: {len(new_medium)}")

    if truly_new:
        print("\nNew findings (not in baseline by test_id + file):")
        for r in truly_new:
            print(
                f"  {r['issue_severity']:6s} {r['test_id']} "
                f"at {r['filename']}:{r['line_number']}"
            )
            print(f"    {r.get('issue_text', '')[:120]}")

    if new_high:
        print("\nFAIL: New HIGH severity findings detected — not in baseline")
        return 1

    print("PASS: No new HIGH severity findings (semantic baseline comparison)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
