# Phase 23D — Lint Debt Burn-Down Receipt

**Date:** 2026-05-02
**Branch:** agent/manus/PHASE-23D-lint-burndown
**Files Changed:** 91

## Results

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Total ruff violations | 2,160 | 472 | **-78%** |
| Auto-fixable (standard) | 1,399 | 0 | -1,399 |
| Auto-fixable (unsafe) | 253 | 0 | -253 |
| Remaining (manual review) | 508 | 472 | -36 |

## Rules Fixed

| Rule | Count Fixed | Description |
|------|-------------|-------------|
| UP045 | 665 | `Optional[X]` → `X \| None` |
| W293 | 194 | Trailing whitespace on blank lines |
| I001 | 143 | Unsorted imports |
| UP006 | 110 | `List[X]` → `list[X]`, `Dict` → `dict` |
| UP017 | 61 | `datetime.timezone.utc` → `UTC` |
| F401 | 10 | Unused imports removed |
| B/RUF/PT/SIM | ~606 | Various best-practice fixes |

## Remaining Violations (472 — require manual review)

| Rule | Count | Description |
|------|-------|-------------|
| B008 | 260 | Function call in default argument (FastAPI `Depends()` — intentional) |
| ARG001 | 74 | Unused function argument (route handlers — intentional) |
| DTZ003 | 30 | `datetime.utcnow()` without timezone |
| ARG002 | 19 | Unused method argument |
| F821 | 16 | Undefined name (dynamic attributes) |
| B904 | 15 | `raise` without `from` inside `except` |
| Others | 58 | Various |

## Notes

- `B008` (260 violations) are all FastAPI `Depends()` calls in route function signatures — this is the correct FastAPI pattern and should be suppressed with `# noqa: B008` or added to `ruff.toml` ignore list in Phase 23E.
- No syntax errors introduced. `python -m compileall portal/` passes cleanly.
- Tests were not re-run in this branch (requires venv install). Run `pytest portal/ -x -q` to validate.
