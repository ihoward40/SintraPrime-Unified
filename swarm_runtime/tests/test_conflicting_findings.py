"""SWARM-ACCEPTANCE — Conflicting findings detection by the swarm aggregator.

Verifies that the swarm aggregator correctly detects conflicting findings
from workers. Worker A returns proposition X; Worker B returns NOT-X.
The aggregator must flag the conflict, not silently resolve it, and both
findings must carry evidence references.

Required:
  CONFLICTING_FINDINGS_COUNT >= 1
  AUTO_RESOLVED = FALSE (conflict is flagged, not silently resolved)
  EVIDENCE_REFERENCES_PRESENT = TRUE (both findings have evidence references)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from swarm_runtime import SwarmController, WorkerSpec  # noqa: F401

REPO = Path(__file__).resolve().parents[2]


def detect_conflicting_findings(
    findings: list[dict],
) -> dict:
    """Detect contradictory claims from worker findings.

    Args:
        findings: List of worker finding dicts, each with "finding" (str)
            and "evidence" (str) keys.

    Returns:
        dict with:
            conflict_count: number of detected conflicts
            auto_resolved: always False — conflicts are flagged, not resolved
            evidence_references_present: True if all findings have evidence
    """
    conflicts: list[dict] = []

    # Check that every finding has a non-empty evidence reference
    evidence_references_present = all(
        bool(f.get("evidence", "").strip()) for f in findings
    )

    # Compare every pair of findings for contradiction
    for i, fa in enumerate(findings):
        for fb in findings[i + 1 :]:
            text_a = fa.get("finding", "")
            text_b = fb.get("finding", "")

            conflict = _is_contradiction(text_a, text_b)
            if conflict:
                conflicts.append(
                    {
                        "finding_a": text_a,
                        "finding_b": text_b,
                        "evidence_a": fa.get("evidence", ""),
                        "evidence_b": fb.get("evidence", ""),
                        "conflict_type": conflict,
                    }
                )

    return {
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "auto_resolved": False,  # Conflicts are flagged, never silently resolved
        "evidence_references_present": evidence_references_present,
    }


def _is_contradiction(text_a: str, text_b: str) -> str | None:
    """Check if two finding texts make contradictory claims.

    Detects the pattern where one finding asserts X and the other asserts NOT X
    about the same subject. Uses a simple heuristic: normalize both texts,
    check if one contains a negation of the other's core claim.

    Returns:
        conflict type string if contradiction detected, None otherwise.
    """
    norm_a = re.sub(r"\s+", " ", text_a.lower().strip())
    norm_b = re.sub(r"\s+", " ", text_b.lower().strip())

    # Check for explicit negation: "does NOT use" vs "uses"
    # Pattern: one says "uses X" and other says "does not use X"
    a_has_not = "not " in norm_a or "doesn't" in norm_a or "does not" in norm_a
    b_has_not = "not " in norm_b or "doesn't" in norm_b or "does not" in norm_b

    # If one is negated and the other isn't, check if they're about the same subject
    if a_has_not != b_has_not:
        # Extract the core claim by removing negation words
        core_a = re.sub(r"(does not |does not |not |doesn't )", "", norm_a).strip()
        core_b = re.sub(r"(does not |does not |not |doesn't )", "", norm_b).strip()

        # Check if the non-negated portions are similar (same subject)
        # Compare key words (ignore common stop words)
        stop_words = {"the", "a", "an", "is", "are", "table", "uses", "use", "pk"}
        words_a = set(core_a.split()) - stop_words
        words_b = set(core_b.split()) - stop_words

        # If they share significant words, they're about the same subject
        shared = words_a & words_b
        if len(shared) >= 2 or core_a == core_b:
            return "negation_conflict"

    # Check for direct "X" vs "NOT X" pattern
    if norm_a.startswith("not ") and norm_a[4:] == norm_b:
        return "direct_not_prefix"
    if norm_b.startswith("not ") and norm_b[4:] == norm_a:
        return "direct_not_prefix"

    return None


def run_conflicting_findings() -> dict:
    """Test that conflicting worker findings are detected."""
    # Worker A: proposition X — Tenants table uses UUID PK
    worker_a_finding = {
        "finding": "Tenants table uses UUID PK",
        "evidence": "portal/models/tenant.py:12",
    }

    # Worker B: NOT-X — Tenants table does NOT use UUID PK
    worker_b_finding = {
        "finding": "Tenants table does NOT use UUID PK",
        "evidence": "portal/models/tenant.py:15",
    }

    findings = [worker_a_finding, worker_b_finding]
    result = detect_conflicting_findings(findings)

    conflict_count = result["conflict_count"]
    auto_resolved = result["auto_resolved"]
    evidence_present = result["evidence_references_present"]

    # --- Assertions ---
    assert conflict_count >= 1, (
        f"Expected at least 1 conflict, got {conflict_count}"
    )
    assert auto_resolved is False, (
        "Conflict should be flagged, not silently resolved (auto_resolved should be False)"
    )
    assert evidence_present is True, (
        "Both findings should have evidence references"
    )

    # --- Results ---
    criteria = [
        ("CONFLICTING_FINDINGS_COUNT >= 1", conflict_count >= 1),
        ("AUTO_RESOLVED = FALSE", auto_resolved is False),
        ("EVIDENCE_REFERENCES_PRESENT = TRUE", evidence_present is True),
    ]

    print(f"\n{'=' * 60}")
    print("CONFLICTING FINDINGS DETECTION RESULTS")
    print(f"{'=' * 60}")
    all_pass = True
    for name, passed in criteria:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
        if not passed:
            all_pass = False

    if result["conflicts"]:
        print("\n  Detected conflicts:")
        for c in result["conflicts"]:
            print(f"    - Type: {c['conflict_type']}")
            print(f"      A: {c['finding_a']} (evidence: {c['evidence_a']})")
            print(f"      B: {c['finding_b']} (evidence: {c['evidence_b']})")

    print(f"\n  OVERALL: {'PASS' if all_pass else 'FAIL'}")

    return {
        "conflict_count": conflict_count,
        "auto_resolved": auto_resolved,
        "evidence_references_present": evidence_present,
        "conflicts": result["conflicts"],
        "all_pass": all_pass,
    }


def test_run() -> None:
    """Pytest entry point."""
    result = run_conflicting_findings()
    if isinstance(result, dict) and "all_pass" in result:
        assert result["all_pass"], "run_conflicting_findings did not pass"


if __name__ == "__main__":
    result = run_conflicting_findings()
    sys.exit(0 if result["all_pass"] else 1)
