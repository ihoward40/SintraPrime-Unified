# Phase 21E Receipt — Baseline Cleanup & Security Remediation

**Date:** 2026-05-01
**Author:** Manus
**PR:** [#49](https://github.com/ihoward40/SintraPrime-Unified/pull/49)
**Branch:** `manus/PHASE-21E-baseline-cleanup`
**Commit:** `d4ed9ca`
**Issue:** [#48](https://github.com/ihoward40/SintraPrime-Unified/issues/48)

---

## Summary

Phase 21E addressed four categories of pre-existing technical debt that were
blocking global `pytest` collection and leaving known CVEs unpatched across
the repository.

---

## Deliverables

### 1. Fatal Syntax Errors Fixed

| File | Root Cause | Resolution |
|---|---|---|
| `portal/sso/tests/test_sso.py` | Tasklet heredoc serialisation produced escaped triple-quote `SyntaxError` | Replaced with valid index comment pointing to real test files |
| `portal/sso/dependencies.py` | Same escaped-quote serialisation bug | Replaced with clean FastAPI dependency implementation |
| `portal/sso/schemas.py` | Same escaped-quote serialisation bug | Replaced with clean Pydantic schema definitions |
| `portal/sso/sso.py` | Corrupted single-line JSON-escaped file, never imported | Deleted; real Phase 21B router is at `portal/routers/sso.py` |

**Impact:** Global `pytest` collection was completely blocked (1 error, 0 tests
collected). After fix: **316 tests collected, 0 collection errors**.

### 2. SQLAlchemy Declarative API Collision Fixed

- **File:** `portal/models/case.py`
- **Problem:** `CaseEvent.metadata` collided with SQLAlchemy's internal
  `__metadata__` attribute, causing `portal.main` to fail on import in test
  environments.
- **Fix:** Renamed Python attribute to `event_metadata`; DB column name
  preserved via `mapped_column("metadata", ...)` — no Alembic migration needed.

### 3. Dependabot CVEs Patched

| Package | Previous | Patched | Severity | Files |
|---|---|---|---|---|
| `python-multipart` | `==0.0.6` | `>=0.0.26` | High (×3) | lead-router, stripe-payments |
| `requests` | `>=2.31.0` / `==2.31.0` | `>=2.33.0` | High | core, lead-router |
| `pytest` | `>=7.4.0` / `==7.4.3` | `>=9.0.3` | Medium | core, lead-router, stripe-payments |
| `python-dotenv` | `>=1.0.0` / `==1.0.0` | `>=1.2.2` | Medium | core, lead-router, stripe-payments |
| `vite` | `^5.3.1` | `>=6.4.2` | Medium | web/package.json |

Note: `requirements.txt` (root) and root `package.json` were already at
patched versions from prior P0-004 remediation.

---

## Test Results

| Metric | Before Phase 21E | After Phase 21E |
|---|---|---|
| pytest collection | 1 fatal error, 0 tests | 316 tests, 0 errors |
| Tests passing | N/A (blocked) | 247/316 |
| Pre-existing failures | N/A | 69 (test_auth/cases/documents/billing) |
| Bandit issues (production) | — | 0 |

The 69 pre-existing failures in `portal/tests/` are unrelated to Phase 21E
scope and are tracked separately for Phase 22.

---

## Deferred to Phase 22

- Fix 69 pre-existing test failures in `portal/tests/test_auth.py`,
  `test_cases.py`, `test_documents.py`, and `test_billing.py`.
- Ruff lint debt: ~440 remaining `E501`/`W293`/`F401` errors.
