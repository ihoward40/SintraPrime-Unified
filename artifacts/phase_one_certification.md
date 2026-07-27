# Phase One Certification Report

| Field | Value |
|-------|-------|
| Commit SHA | `7bdddfd5ae8a4e46eb7e8e486675fadb3107f4f6` |
| Short SHA | `7bdddfd5` |
| Branch | `main` |
| Timestamp | `2026-07-27T03:00:50.723979+00:00` |
| Python version | `Python 3.11.9` |
| Ruff status | **PASS** |
| Pytest totals | `393 passed, 2 warnings in 119.16s (0:01:59)` |
| Smoke pytest totals | **3 passed, 0 failed, 0 skipped** |
| Repository Truth Check totals | **31 passed, 0 failed, 0 warnings** |
| Smoke lane overall | **PASS** |
| Receipt ID | `smoke_20260727025733_7bdddfd5` |
| Badge status | `[![Smoke: passing](https://img.shields.io/badge/smoke-passing-brightgreen?style=for-the-badge)](https://github.com/ihoward40/SintraPrime-Unified/actions/workflows/smoke.yml)` |

## CI Workflow Names

- `badge-update.yml`
- `ci.yml`
- `deploy-production.yml`
- `deploy-staging.yml`
- `docker-build.yml`
- `issue-verifier-ci.yml`
- `load-test.yml`
- `sigma-gate.yml`
- `smoke.yml`

## Smoke Artifact Locations

| Artifact | Path |
|----------|------|
| `last_smoke_receipt_ref.txt` | `artifacts/last_smoke_receipt_ref.txt` |
| `last_smoke_summary.json` | `artifacts/last_smoke_summary.json` |
| `last_smoke_timestamp.txt` | `artifacts/last_smoke_timestamp.txt` |

Artifact hashes are recorded in `artifacts/phase_one_baseline_snapshot.md` at the time of the baseline snapshot.

## Verification Commands Executed

```text
ruff check .
.venv/Scripts/python -m pytest --tb=short
.venv/Scripts/python scripts/smoke/e2e_skills_smoke.py
.venv/Scripts/python scripts/smoke/write_smoke_badge.py
.venv/Scripts/python scripts/smoke/repo_truth_check.py
git status --porcelain=v1
git diff --stat
```

## Gate Result

**Phase One: PASS**

All verification commands completed successfully with no unexpected file modifications and a clean working tree after commit.
