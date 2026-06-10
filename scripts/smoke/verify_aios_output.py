#!/usr/bin/env python3
"""
AIOS Output Verification — SintraPrime-Unified
=============================================
Validates that all expected AIOS documentation and configuration files exist
and are valid.  Exit code 0 = all checks pass.  Exit code 1 = any failure.

Run:  python scripts/smoke/verify_aios_output.py
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

results: list[dict] = []


def check(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    icon = PASS if passed else FAIL
    results.append({"name": name, "status": status, "detail": detail})
    print(f"  [{icon}] {name}" + (f" — {detail}" if detail else ""))
    return passed

def check_json_valid(path: Path) -> bool:
    """Try to parse a JSON file.  Return True if valid."""
    if not path.exists():
        return check(f"{path.name} exists", False, "file not found")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return check(f"{path.name} is valid JSON", True)
    except json.JSONDecodeError as e:
        return check(f"{path.name} is valid JSON", False, str(e))

# ── Expected AIOS docs ──────────────────────────────────────────────────────
def check_aios_docs():
    print("\n📋 AIOS Documentation")
    expected_docs = [
        "docs/policies/PERMISSION_LAYER.md",
        "docs/workflows/SELF_VERIFICATION.md",
        "docs/cadence/CADENCE_MAP.md",
    ]
    all_found = True
    for rel_path in expected_docs:
        full = ROOT / rel_path
        exists = full.exists()
        if not exists:
            all_found = False
        check(f"{rel_path} exists", exists)
    return all_found

# ── Skills registry ────────────────────────────────────────────────────────
def check_skills_registry():
    print("\n📋 Skills Registry")
    paths_to_try = [
        ROOT / "skills" / "registry.json",
        ROOT / "skills_registry.json",
        ROOT / "agents" / "skills_registry.json",
    ]
    for p in paths_to_try:
        if p.exists():
            return check_json_valid(p)
    # If none exist, that's a failure
    return check("skills registry found", False,
                  "no skills registry at skills/registry.json, skills_registry.json, or agents/skills_registry.json")

# ── Agent registry ──────────────────────────────────────────────────────────
def check_agent_registry():
    print("\n🤖 Agent Registry")
    paths_to_try = [
        ROOT / "agents" / "registry.json",
        ROOT / "agent_registry.json",
        ROOT / "agents" / "agent_registry.json",
    ]
    for p in paths_to_try:
        if p.exists():
            return check_json_valid(p)
    return check("agent registry found", False,
                  "no agent registry at agents/registry.json, agent_registry.json, or agents/agent_registry.json")

# ── Permissions file ────────────────────────────────────────────────────────
def check_permissions():
    print("\n🔐 Permissions File")
    perms_path = ROOT / "policies" / "permissions.json"
    if not perms_path.exists():
        return check("policies/permissions.json exists", False)
    if not check_json_valid(perms_path):
        return False
    # Validate structure
    try:
        data = json.loads(perms_path.read_text(encoding="utf-8"))
        perms = data.get("permissions", [])
        if not isinstance(perms, list) or len(perms) == 0:
            return check("permissions list non-empty", False,
                          "missing or empty 'permissions' array")
        required = {"read_only", "draft_only", "write_local_only",
                     "external_send_requires_confirmation",
                     "destructive_action_blocked",
                     "legal_output_requires_review",
                     "financial_output_requires_review",
                     "identity_data_requires_redaction"}
        found = {p.get("name") for p in perms}
        missing = required - found
        if missing:
            return check("all required permissions present", False,
                          f"missing: {', '.join(sorted(missing))}")
        # Check each has required fields
        for p in perms:
            name = p.get("name", "?")
            if "description" not in p:
                return check(f"permission '{name}' has description", False)
            if "default" not in p:
                return check(f"permission '{name}' has default", False)
            if "override_conditions" not in p:
                return check(f"permission '{name}' has override_conditions", False)
        return check("all required permissions present", True)
    except Exception as e:
        return check("permissions structure valid", False, str(e))

# ── Cadence registry ────────────────────────────────────────────────────────
def check_cadence_registry():
    print("\n📅 Cadence Registry")
    cad_path = ROOT / "automations" / "cadence_registry.json"
    if not cad_path.exists():
        return check("automations/cadence_registry.json exists", False)
    if not check_json_valid(cad_path):
        return False
    try:
        data = json.loads(cad_path.read_text(encoding="utf-8"))
        cadences = data.get("cadences", [])
        if not isinstance(cadences, list) or len(cadences) == 0:
            return check("cadences list non-empty", False,
                          "missing or empty 'cadences' array")
        required_fields = {"name", "schedule", "actions", "owner", "verification"}
        for c in cadences:
            name = c.get("name", "?")
            missing = required_fields - set(c.keys())
            if missing:
                return check(f"cadence '{name}' has all required fields", False,
                              f"missing: {', '.join(sorted(missing))}")
        return check("cadence registry structure valid", True)
    except Exception as e:
        return check("cadence registry structure valid", False, str(e))

# ── Main ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  AIOS Output Verification")
    print("=" * 60)

    check_aios_docs()
    check_skills_registry()
    check_agent_registry()
    check_permissions()
    check_cadence_registry()

    # Summary
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")

    print("\n" + "=" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        print(f"\n❌ {failed} check(s) FAILED — AIOS output not verified.")
        sys.exit(1)
    else:
        print(f"\n✅ All {passed} checks passed — AIOS output verified.")
        sys.exit(0)

if __name__ == "__main__":
    main()