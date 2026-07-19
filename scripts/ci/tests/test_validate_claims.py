"""Tests for the repository claims validator and test-inventory reporter.

These tests create temporary repository-like trees and assert the validator's
deterministic rules. They do not touch the real repo.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import report_test_inventory as ri
import validate_repository_claims as vc


def _make_tree(files: dict) -> str:
    root = tempfile.mkdtemp()
    for rel, content in files.items():
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
    return root


GOOD_README = """# Test
- [ARCHITECTURE](docs/ARCHITECTURE.md)
- [Claims](docs/CLAIMS.md)
"""

BAD_README_LINK = """# Test
- [Missing](docs/DOES_NOT_EXIST.md)
"""

BAD_README_PATH = """# Test
See [trust](src/trust_law/) for details.
"""

BAD_README_TOTAL = """# Test
We have 333 tests passing.
"""

BAD_README_PAYMENT = """# Test
Payment Intent: pi_3TRW78CT25knq5v20vTV8j03 succeeded.
"""

BAD_README_COMPLIANCE = """# Test
We are HIPAA compliant and SOC 2 certified.
"""


def test_validator_passes_good_tree():
    root = _make_tree({
        "docs/ARCHITECTURE.md": "# A",
        "docs/QUICK_START.md": "# Q",
        "docs/CAPABILITY_INDEX.md": "# C",
        "docs/SECURITY.md": "# S",
        "docs/CLAIMS.md": "# Claims",
        "docs/REPOSITORY_STATUS.md": "# R",
        "docs/governance/MISSION_CONTROL_OBSERVATORY_AUTHORITY.md": "# M",
        "docs/governance/OPEN_PR_DISPOSITION.md": "# O",
        "docs/DATABASE_AUTHORITY.md": "# D",
        "README.md": GOOD_README,
    })
    vc.REPO_ROOT = root
    assert vc.errors() == []


def test_validator_fails_missing_required_doc():
    root = _make_tree({"README.md": GOOD_README})
    vc.REPO_ROOT = root
    errs = vc.errors()
    assert any("MISSING REQUIRED DOC" in e for e in errs)


def test_validator_fails_broken_readme_link():
    root = _make_tree({
        "docs/ARCHITECTURE.md": "# A",
        "docs/QUICK_START.md": "# Q",
        "docs/CAPABILITY_INDEX.md": "# C",
        "docs/SECURITY.md": "# S",
        "docs/CLAIMS.md": "# Claims",
        "docs/REPOSITORY_STATUS.md": "# R",
        "docs/governance/MISSION_CONTROL_OBSERVATORY_AUTHORITY.md": "# M",
        "docs/governance/OPEN_PR_DISPOSITION.md": "# O",
        "docs/DATABASE_AUTHORITY.md": "# D",
        "README.md": BAD_README_LINK,
    })
    vc.REPO_ROOT = root
    assert any("README BROKEN LINK" in e for e in vc.errors())


def test_validator_fails_retired_path():
    root = _make_tree({
        "docs/ARCHITECTURE.md": "# A",
        "docs/QUICK_START.md": "# Q",
        "docs/CAPABILITY_INDEX.md": "# C",
        "docs/SECURITY.md": "# S",
        "docs/CLAIMS.md": "# Claims",
        "docs/REPOSITORY_STATUS.md": "# R",
        "docs/governance/MISSION_CONTROL_OBSERVATORY_AUTHORITY.md": "# M",
        "docs/governance/OPEN_PR_DISPOSITION.md": "# O",
        "docs/DATABASE_AUTHORITY.md": "# D",
        "README.md": BAD_README_PATH,
    })
    vc.REPO_ROOT = root
    assert any("retired path pattern" in e for e in vc.errors())


def test_validator_fails_test_total():
    root = _make_tree({
        "docs/ARCHITECTURE.md": "# A",
        "docs/QUICK_START.md": "# Q",
        "docs/CAPABILITY_INDEX.md": "# C",
        "docs/SECURITY.md": "# S",
        "docs/CLAIMS.md": "# Claims",
        "docs/REPOSITORY_STATUS.md": "# R",
        "docs/governance/MISSION_CONTROL_OBSERVATORY_AUTHORITY.md": "# M",
        "docs/governance/OPEN_PR_DISPOSITION.md": "# O",
        "docs/DATABASE_AUTHORITY.md": "# D",
        "README.md": BAD_README_TOTAL,
    })
    vc.REPO_ROOT = root
    assert any("forbidden hardcoded test total" in e for e in vc.errors())


def test_validator_fails_payment_id():
    root = _make_tree({
        "docs/ARCHITECTURE.md": "# A",
        "docs/QUICK_START.md": "# Q",
        "docs/CAPABILITY_INDEX.md": "# C",
        "docs/SECURITY.md": "# S",
        "docs/CLAIMS.md": "# Claims",
        "docs/REPOSITORY_STATUS.md": "# R",
        "docs/governance/MISSION_CONTROL_OBSERVATORY_AUTHORITY.md": "# M",
        "docs/governance/OPEN_PR_DISPOSITION.md": "# O",
        "docs/DATABASE_AUTHORITY.md": "# D",
        "README.md": BAD_README_PAYMENT,
    })
    vc.REPO_ROOT = root
    assert any("public payment-intent identifier" in e for e in vc.errors())


def test_validator_fails_compliance_claim():
    root = _make_tree({
        "docs/ARCHITECTURE.md": "# A",
        "docs/QUICK_START.md": "# Q",
        "docs/CAPABILITY_INDEX.md": "# C",
        "docs/SECURITY.md": "# S",
        "docs/CLAIMS.md": "# Claims",
        "docs/REPOSITORY_STATUS.md": "# R",
        "docs/governance/MISSION_CONTROL_OBSERVATORY_AUTHORITY.md": "# M",
        "docs/governance/OPEN_PR_DISPOSITION.md": "# O",
        "docs/DATABASE_AUTHORITY.md": "# D",
        "README.md": BAD_README_COMPLIANCE,
    })
    vc.REPO_ROOT = root
    assert any("unqualified compliance claim" in e for e in vc.errors())


def test_import_report_module_ok():
    # The inventory reporter must import cleanly (it no longer exposes parse_junit;
    # executed-count parsing is out of scope for collection-only truth).
    assert hasattr(ri, "parse_collect_output")
    assert hasattr(ri, "run_collect")

