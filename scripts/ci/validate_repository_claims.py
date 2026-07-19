#!/usr/bin/env python3
"""Validate repository documentation/claims integrity.

Fails (exit 1) when:
- README links point to missing local files
- documented source paths do not exist (retired src/... paths)
- forbidden hardcoded test-total patterns appear in authoritative docs
- known retired src/... paths appear
- public operational payment identifiers appear
- compliance claims use prohibited unqualified language
- architecture authority document is missing
- Mission Control/Observatory authority document is missing

Deterministic and documented. Safe to run in CI.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Local files referenced by README/docs that MUST exist.
REQUIRED_DOCS = [
    "docs/ARCHITECTURE.md",
    "docs/QUICK_START.md",
    "docs/CAPABILITY_INDEX.md",
    "docs/SECURITY.md",
    "docs/CLAIMS.md",
    "docs/REPOSITORY_STATUS.md",
    "docs/governance/MISSION_CONTROL_OBSERVATORY_AUTHORITY.md",
    "docs/governance/OPEN_PR_DISPOSITION.md",
    "docs/DATABASE_AUTHORITY.md",
]

# Retired/forbidden source paths (the old src/ layout no longer exists).
FORBIDDEN_PATH_PATTERNS = [
    r"src/trust_law/",
    r"src/document_gen/",
    r"src/financial_mastery/",
    r"src/payment/",
    r"src/portal/",
    r"src/audit/",
    r"src/agents/",
    r"tests/trust_law/",
    r"tests/financial_mastery/",
    r"tests/payment/",
    r"tests/audit/",
    r"tests/document_gen/",
    r"tests/legal_docs/",
    r"tests/portal/",
]

# Forbidden hardcoded test totals in authoritative docs (case-insensitive).
FORBIDDEN_TEST_TOTAL = re.compile(
    r"\b(\d{2,4}\+?\s*tests?|4,?\d{3}\+?\s*(documented\s*)?tests?|~?333\+?\s*tests?)\b",
    re.IGNORECASE,
)

# Public Stripe payment-intent identifiers (pi_...).
FORBIDDEN_PAYMENT_ID = re.compile(r"pi_[0-9A-Za-z]{10,}")

# Unqualified compliance claims.
FORBIDDEN_COMPLIANCE = re.compile(
    r"(HIPAA|SOC\s*2|PCI[- ]?DSS)[^.\n]*\b(compliant|certified)\b", re.IGNORECASE
)

# Docs scanned for forbidden patterns (not the validator's own dir).
SCANNED_DOCS = [
    "README.md",
    "docs/CLAIMS.md",
    "docs/CAPABILITY_INDEX.md",
    "docs/REPOSITORY_STATUS.md",
]


def errors(root: str | None = None) -> list[str]:
    repo = root or REPO_ROOT
    errs: list[str] = []

    # 1. Required docs exist.
    for rel in REQUIRED_DOCS:
        if not os.path.exists(os.path.join(repo, rel)):
            errs.append(f"MISSING REQUIRED DOC: {rel}")

    # 2. README local links resolve.
    readme = os.path.join(repo, "README.md")
    if os.path.exists(readme):
        with open(readme, encoding="utf-8") as fh:
            text = fh.read()
        for m in re.finditer(r"\]\(([^)]+)\)", text):
            target = m.group(1).split("#")[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            cand = os.path.join(repo, target)
            if not (os.path.exists(cand) or os.path.isdir(cand)):
                errs.append(f"README BROKEN LINK: {target}")
        # Forbidden patterns in README.
        _scan_text("README.md", text, errs)

    # 3. Scan other docs.
    for rel in SCANNED_DOCS:
        if rel == "README.md":
            continue
        p = os.path.join(repo, rel)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                _scan_text(rel, fh.read(), errs)

    return errs


def _scan_text(rel: str, text: str, errs: list[str]) -> None:
    for pat in FORBIDDEN_PATH_PATTERNS:
        if re.search(pat, text):
            errs.append(f"{rel}: retired path pattern '{pat}'")
    if FORBIDDEN_TEST_TOTAL.search(text):
        errs.append(f"{rel}: forbidden hardcoded test total")
    if FORBIDDEN_PAYMENT_ID.search(text):
        errs.append(f"{rel}: public payment-intent identifier present")
    if FORBIDDEN_COMPLIANCE.search(text):
        errs.append(f"{rel}: unqualified compliance claim (HIPAA/SOC2/PCI 'compliant/certified')")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=REPO_ROOT)
    args = ap.parse_args()

    errs = errors(args.root)
    if errs:
        print("VALIDATION FAILED:")
        for e in errs:
            print(f"  - {e}")
        return 1
    print("VALIDATION PASSED: no documentation/claim drift detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

