# Phase One Certification Report

| Field | Value |
|-------|-------|
| Commit SHA | `d3f851e521221ed3fff8e0a12fc77685b2217237` |
| Short SHA | `d3f851e5` |
| Branch | `main` |
| Timestamp | `2026-07-27T03:00:50.723979+00:00` |
| Python version | `Python 3.11.9` |
| Ruff status | **PASS** |
| Pytest totals | `393 passed, 2 warnings in 119.16s (0:01:59)` |
| Smoke pytest totals | **3 passed, 0 failed, 0 skipped** |
| Repository Truth Check totals | **31 passed, 0 failed, 0 warnings** |
| Smoke lane overall | **PASS** |
| Receipt ID | `smoke_20260727030050_d3f851e5` |
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

| Artifact | Path | SHA-256 |
|----------|------|---------|
| `last_smoke_receipt_ref.txt` | `artifacts/last_smoke_receipt_ref.txt` | `78bca5d81ac684d608ca20bdf4c55cfa93eefa50b90132c3fcdb3edb4e6286d7` |
| `last_smoke_summary.json` | `artifacts/last_smoke_summary.json` | `fb751558d23002340dc53dd3c3ffcebbf49dd4ba33b6bbe800fd8579c4c733ef` |
| `last_smoke_timestamp.txt` | `artifacts/last_smoke_timestamp.txt` | `2ea2abb7fc366559b5fbb75005efe6eab22d0dbb07f1db5661b7d62228fd51ee` |

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
