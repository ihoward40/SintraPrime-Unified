#!/usr/bin/env python3
"""
Repo Truth Smoke Check — SintraPrime-Unified
=============================================
Validates that documentation, configuration, and source code tell the truth.
Exit code 0 = all checks pass.  Non-zero = at least one failure.

Run:  python scripts/smoke/repo_truth_check.py
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"

results: list[dict] = []


def check(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    icon = PASS if passed else FAIL
    results.append({"name": name, "status": status, "detail": detail})
    print(f"  [{icon}] {name}" + (f" — {detail}" if detail else ""))
    return passed


def warn(name: str, detail: str = ""):
    results.append({"name": name, "status": "WARN", "detail": detail})
    print(f"  [{WARN}] {name}" + (f" — {detail}" if detail else ""))


# ── docker-compose.yml ──────────────────────────────────────────────────────
def check_docker_compose():
    print("\n📦 Docker Compose")
    dc_path = ROOT / "docker-compose.yml"
    check("docker-compose.yml exists", dc_path.exists())
    if not dc_path.exists():
        return

    dc = dc_path.read_text()

    # Required services
    required_services = ["postgres", "redis", "api", "airlock-server", "nginx"]
    for svc in required_services:
        # Look for service definition (indented under services:)
        pattern = rf"^  {re.escape(svc)}:"
        found = bool(re.search(pattern, dc, re.MULTILINE))
        check(f"service '{svc}' defined", found)

    # No hardcoded production secrets
    bad_defaults = [
        ("sintraprime123", "POSTGRES_PASSWORD default"),
        ("change_me_32_char_secret_key_here", "SECRET_KEY default"),
        ("change_me_jwt_secret_here", "JWT_SECRET default"),
        ("change-me-in-production", "TWIN_AUTH_TOKEN default"),
    ]
    for pattern, label in bad_defaults:
        # Check if it appears as a fallback default (:-pattern)
        has_bad = f":-{pattern}" in dc
        check(f"no hardcoded {label}", not has_bad,
              f"found ':-{pattern}'" if has_bad else "")


# ── Nginx health route ──────────────────────────────────────────────────────
def check_nginx():
    print("\n🔀 Nginx Configuration")
    nginx_path = ROOT / "shared" / "config" / "nginx.conf"
    check("nginx.conf exists", nginx_path.exists())
    if not nginx_path.exists():
        return

    ng = nginx_path.read_text()
    check("/health route configured", "/health" in ng)
    check("upstream api_backend defined", "api_backend" in ng)


# ── README truth ────────────────────────────────────────────────────────────
def check_readme():
    print("\n📖 README Truth")
    readme_path = ROOT / "README.md"
    check("README.md exists", readme_path.exists())
    if not readme_path.exists():
        return

    readme = readme_path.read_text()

    # Should NOT reference localhost:8000 (that port doesn't exist)
    has_8000 = "localhost:8000" in readme
    check("no stale localhost:8000 reference", not has_8000,
          "README still references :8000 which is not in docker-compose" if has_8000 else "")

    # Python version should say 3.11+
    has_310_only = "3.10+" in readme and "3.11" not in readme
    check("Python version matches pyproject (3.11+)",
          not has_310_only,
          "README says 3.10+ but pyproject requires >=3.11" if has_310_only else "")


# ── Python version alignment ───────────────────────────────────────────────
def check_python_version():
    print("\n🐍 Python Version Alignment")
    pyproject = ROOT / "pyproject.toml"
    check("pyproject.toml exists", pyproject.exists())
    if not pyproject.exists():
        return

    pp = pyproject.read_text()
    m = re.search(r'requires-python\s*=\s*["\'](.*?)["\']', pp)
    if m:
        req = m.group(1)
        check(f"requires-python = {req}", "3.11" in req or "3.12" in req,
              f"found: {req}")
    else:
        warn("requires-python not found in pyproject.toml")


# ── Dependency source of truth ──────────────────────────────────────────────
def check_dependencies():
    print("\n📦 Dependency Source of Truth")
    pyproject = ROOT / "pyproject.toml"
    requirements = ROOT / "requirements.txt"
    check("pyproject.toml exists", pyproject.exists())
    check("requirements.txt exists", requirements.exists())

    if requirements.exists():
        req = requirements.read_text()
        is_derived = "DERIVED" in req or "source of truth" in req.lower() or "pyproject.toml" in req
        check("requirements.txt marked as derived", is_derived,
              "Should reference pyproject.toml as source" if not is_derived else "")


# ── Pytest discovery ────────────────────────────────────────────────────────
def check_pytest():
    print("\n🧪 Pytest Discovery")
    pytest_ini = ROOT / "pytest.ini"
    check("pytest.ini exists", pytest_ini.exists())
    if not pytest_ini.exists():
        return

    pi = pytest_ini.read_text()
    has_dot = re.search(r"^testpaths\s*=\s*\.\s*$", pi, re.MULTILINE)
    check("pytest.ini does NOT use testpaths = .", not has_dot,
          "testpaths = . causes ~131 collection errors" if has_dot else "")


# ── Private data in public source ───────────────────────────────────────────
def check_private_data():
    print("\n🔐 Private Data in Public Source")
    index_ts = ROOT / "apps" / "sintraprime" / "src" / "index.ts"
    if not index_ts.exists():
        warn("apps/sintraprime/src/index.ts not found — skipping")
        return

    ts = index_ts.read_text()
    pii_patterns = [
        (r"92-6080121", "Howard Trust EIN"),
        (r"87-1798434", "IKE Solutions EIN"),
        (r"lwinbush34@gmail\.com", "beneficiary email"),
        (r"991 Frelinghuysen", "mailing address"),
        (r"Latanya Winbush", "beneficiary name"),
        (r"ISIAH TARIK HOWARD TRUST", "trust name (hardcoded)"),
    ]
    for pattern, label in pii_patterns:
        found = bool(re.search(pattern, ts))
        check(f"no hardcoded {label}", not found,
              f"found in index.ts" if found else "")


# ── CI workflow ─────────────────────────────────────────────────────────────
def check_ci():
    print("\n⚙️  CI Workflow")
    ci_path = ROOT / ".github" / "workflows" / "ci.yml"
    check("ci.yml exists", ci_path.exists())
    if not ci_path.exists():
        return

    ci = ci_path.read_text()
    has_smoke = "repo_truth_check" in ci
    check("CI includes repo truth smoke step", has_smoke,
          "Add: python scripts/smoke/repo_truth_check.py" if not has_smoke else "")


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  SintraPrime Repo Truth Smoke Check")
    print("=" * 60)

    check_docker_compose()
    check_nginx()
    check_readme()
    check_python_version()
    check_dependencies()
    check_pytest()
    check_private_data()
    check_ci()

    # Summary
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    warned = sum(1 for r in results if r["status"] == "WARN")

    print("\n" + "=" * 60)
    print(f"  Results: {passed} passed, {failed} failed, {warned} warnings")
    print("=" * 60)

    if failed > 0:
        print(f"\n❌ {failed} check(s) FAILED — repo truth not verified.")
        sys.exit(1)
    elif warned > 0:
        print(f"\n⚠️  All checks passed with {warned} warning(s).")
        sys.exit(0)
    else:
        print(f"\n✅ All {passed} checks passed — repo truth verified.")
        sys.exit(0)


if __name__ == "__main__":
    main()
