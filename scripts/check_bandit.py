"""Check bandit results for new HIGH findings."""
import json
import sys

with open("/tmp/bandit.json") as f:
    data = json.load(f)

results = data.get("results", [])
high = [r for r in results if r.get("issue_severity") == "HIGH"]

print(f"Bandit (new findings only): {len(results)} findings, {len(high)} HIGH")
if high:
    for r in high:
        print(f"  HIGH: {r['test_id']} at {r['filename']}:{r['line_number']}")
        print(f"    {r['issue_text'][:120]}")
    print("FAIL: New HIGH severity findings detected — not in baseline")
    sys.exit(1)
print("PASS: No new critical security findings")
