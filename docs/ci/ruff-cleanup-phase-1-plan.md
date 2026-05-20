# Ruff Cleanup Ladder — Phase 1 Plan

## Selected Rule: I001 (Import Sorting)

**Category:** `isort` — import block formatting and ordering
**Total violations:** 51 across 46 files
**Auto-fixable:** 51/51 (100%)
**Behavior-changing:** No — import order is low semantic risk; CI/test verification guards against circular-import or side-effect surprises

## Why I001 First

| Criterion | Assessment |
|-----------|------------|
| Mechanical? | ✅ Yes — ruff auto-fix handles 100% |
| Behavior-changing? | ❌ No — import order is cosmetic |
| Risk of breakage? | Near zero — import order is low semantic risk; checked for circular imports (none found), CI/test verification guards against surprises |
| Touches excluded dirs? | ❌ No — only active (non-excluded) directories |
| Per-file-ignore cleanup? | ✅ I001 can be removed from 11 per-file-ignore entries |
| CI enforced after? | ✅ New unsorted imports will fail CI immediately |

### Why Not Whitespace (W293)?
W293 (284 violations) is also mechanical and auto-fixable, but 280 of 286 whitespace violations live in `backend/` and 88 require `--unsafe-fixes`. I001 is cleaner — 100% safe-fixable, spread across all active directories, and has a clear per-file-ignore cleanup story.

### Why Not F401 (Unused Imports)?
F401 (91 violations) is partially auto-fixable (80/91), but 11 require manual review (possible side-effect imports). Not mechanical enough for Phase 1.

## Current Baseline

| Metric | Value |
|--------|-------|
| Total ruff violations (all dirs) | 24,378 |
| Violations in active dirs | ~430 (after per-file-ignores) |
| I001 violations | 51 |
| I001 files affected | 46 |
| Per-file-ignore entries with I001 | 11 |

## Affected Files (46)

### `tests/` — 9 files
```
tests/test_nova_agent.py           (2 violations)
tests/test_scheduler_core.py       (1)
tests/test_scheduler_dispatcher.py (1)
tests/test_scheduler_executor.py   (1)
tests/test_scheduler_queue.py      (1)
tests/test_scheduler_recurring.py  (1)
tests/test_scheduler_task_types.py (1)
tests/test_sigma_agent.py          (2)
tests/test_zero_agent.py           (2)
```

### `backend/lead-router/` — 13 files
```
api/__init__.py, api/routes.py, main.py,
models/__init__.py, models/lead.py, router.py,
services/__init__.py, services/agent_service.py,
services/airtable_service.py, services/email_service.py,
tests/test_router.py,
utils/__init__.py, utils/matching.py
```

### `backend/stripe-payments/` — 12 files
```
api/routes.py, main.py,
models/__init__.py, models/subscription.py,
services/__init__.py, services/airtable_sync.py (×2),
services/subscription_service.py, stripe_client.py,
tests/test_stripe.py (×2),
utils/pricing.py,
webhooks/__init__.py, webhooks/webhook_handler.py
```

### `portal/` — 5 files
```
middleware/session_middleware.py
middleware/timestamp_middleware.py
routers/trust_compliance.py
services/trust_compliance_service.py
tests/test_trust_compliance.py
```

### `governance/` — 4 files
```
__init__.py, risk_assessor.py, risk_types.py,
tests/test_governance.py
```

### Root / scripts — 3 files
```
conftest.py
load_test_runner.py
scripts/smoke/repo_truth_check.py
```

## What the Fix Looks Like

All changes are import reordering — alphabetical sorting within groups, blank line separation between stdlib/third-party/first-party. Example:

```python
# BEFORE
import sys
import os
import sysconfig
import types
import contextlib
import glob

# AFTER
import contextlib
import glob
import os
import sys
import sysconfig
import types
```

No lines added or removed (except blank-line separators between import groups). No new imports. No removed imports.

## Per-File-Ignore Cleanup

After fixing all I001 violations, `I001` can be removed from these 11 entries in `pyproject.toml`:

| Entry | Current rules | After I001 removal |
|-------|--------------|-------------------|
| `load_test_runner.py` | I001, W292, W293 | W292, W293 |
| `conftest.py` | ARG001, I001, SIM108 | ARG001, SIM108 |
| `scripts/**` | F401, F541, I001 | F401, F541 |
| `backend/lead-router/**` | (15 rules incl I001) | (14 rules) |
| `backend/stripe-payments/**` | (17 rules incl I001) | (16 rules) |
| `governance/**` | (18 rules incl I001) | (17 rules) |
| `portal/middleware/**` | I001, N999, RET504, UP017, UP035 | N999, RET504, UP017, UP035 |
| `portal/routers/**` | (12 rules incl I001) | (11 rules) |
| `portal/services/**` | (10 rules incl I001) | (9 rules) |
| `portal/tests/**` | (13 rules incl I001) | (12 rules) |
| `tests/**` | (11 rules incl I001) | (10 rules) |

**Net effect:** I001 is no longer suppressed anywhere → new unsorted imports fail CI immediately.

## Proposed PR #109 Scope

### Step 1: Auto-fix
```bash
ruff check . --select I001 --fix
```

### Step 2: Remove I001 from per-file-ignores
Edit `pyproject.toml` — remove `"I001"` from all 11 per-file-ignore entries.

### Step 3: Verify
```bash
# Confirm zero I001 violations
ruff check . --select I001
# → All checks passed!

# Confirm no OTHER new violations surfaced
ruff check .
# → All checks passed!

# Run test suite
pytest tests/ --tb=short
# → All tests pass (import order is low semantic risk; CI/test verification confirms no surprises)
```

### Step 4: Update baseline docs
Update `docs/ci/ruff-baseline.md`:
- Reduce active-dir I001 count from 51 → 0. The historical all-directory import-sorting backlog remains tracked separately because excluded directories are not re-included in this phase.
- Update per-file-ignores entry count

## What This Does NOT Do

- ❌ Does not touch excluded directories (48 dirs still excluded)
- ❌ Does not fix whitespace (W291/W292/W293) — Phase 2 candidate
- ❌ Does not fix unused imports (F401) — Phase 2 candidate
- ❌ Does not change behavior of any code
- ❌ Does not modify Sigma Gate threshold or Bandit baseline
- ❌ Does not re-include any excluded directory

## Verification Plan

| Check | Expected |
|-------|----------|
| `ruff check .` | All checks passed (0 violations) |
| `ruff check . --select I001` | All checks passed (0 I001 violations) |
| `pytest tests/ --tb=short` | All 330 tests pass |
| CI lint | ✅ green |
| CI test | ✅ green |
| CI security | ✅ green |
| Sigma Gate | ✅ green at 70% |
| No new per-file-ignores | Confirmed — only removals |

## Rollback Plan

1. Revert `pyproject.toml` per-file-ignores (re-add I001 to all 11 entries)
2. `git revert` the auto-fix commit
3. CI returns to current state — I001 suppressed everywhere

Rollback is trivial because the fix is a single `ruff check --fix` command.

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Circular import exposed by reorder | Very low | Python resolves imports by module, not by line position within an import block. Ruff's isort only reorders within blocks, not across them. |
| Test breakage | Near zero | Import order is low semantic risk; CI/test verification guards against circular-import or side-effect surprises. |
| New violations surface | None | Only I001 is being fixed; per-file-ignores for other rules remain. |
| Excluded dirs affected | None | Excluded dirs are not linted at all. |

## Phase 2+ Preview (Not in Scope)

After I001 is clean:

| Phase | Rule | Count | Type |
|-------|------|-------|------|
| Phase 2 | W293 (whitespace) | 284 | Auto-fixable (198 safe + 88 unsafe) |
| Phase 3 | F401 (unused imports) | 91 | Partially auto-fixable (80/91) |
| Phase 4 | UP006/UP035 (type modernization) | TBD | Auto-fixable, scoped to active dirs |
| Phase 5+ | Directory re-inclusion | TBD | Per-directory, violation-by-violation |

## Summary

- **Target:** I001 (import sorting) — 51 violations, 46 files
- **Method:** `ruff check . --select I001 --fix` + per-file-ignore cleanup
- **Risk:** Near zero — mechanical, auto-fixable, low semantic risk with CI/test verification
- **Outcome:** Import sorting enforced across all active directories going forward
