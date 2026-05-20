# Ruff F401 Cleanup Ladder — Phase 3 Plan

**Status:** Planning only — no code cleanup, no import removals.

**Branch:** `docs/ruff-f401-cleanup-plan`  
**Deliverable:** `docs/ci/ruff-f401-cleanup-plan.md`

---

## Executive Summary

Active directories (`portal`, `packages`, `tests`) are **already clean for F401 (unused imports)**.

| Metric | Result |
|--------|--------|
| **Total F401 violations (active dirs)** | 0 |
| **Affected files** | None |
| **Risk level** | ✅ Green |
| **PR #112 scope** | Monitoring plan only |
| **Excluded directories** | Untouched (no approval) |

---

## Investigation Details

### Ruff Command Executed

```bash
ruff check . --select F401 --output-format=json
```

**Run date:** May 20, 2026  
**Scope:** Active directories only (`portal/`, `packages/`, `tests/`)

### Results

- **Portal violations:** 0
- **Packages violations:** 0
- **Tests violations:** 0
- **__init__.py export surfaces:** 0 violations detected
- **Test fixture imports:** 0 violations detected
- **Other active-dir files:** 0 violations detected

### Categorization

| Category | Count | Files |
|----------|-------|-------|
| `__init__.py` exports | 0 | — |
| Test fixture patterns | 0 | — |
| Monkeypatch/plugin imports | 0 | — |
| Safe obvious removals | 0 | — |

---

## PR #112 Scope Recommendation

**Status:** No immediate cleanup needed.

Since active directories are already clean, **PR #112 has two options:**

### Option 1: Establish Monitoring (Recommended)

Create a lightweight monitoring approach:

1. **CI integration:** Add F401 check to GitHub Actions (if not already present)
2. **Active-dir baseline:** Document current clean state
3. **Review checklist:** Add to PR template: "F401 violations introduced? Y/N"
4. **Quarterly audit:** Schedule ruff F401 scan as part of Sigma Gate

**PR #112 deliverable:** Monitoring/CI enhancement doc, not code cleanup.

### Option 2: Skip PR #112

If monitoring is not desired, close Phase 3 of Ruff Cleanup Ladder.

---

## Risk Assessment

### Safe Import Removal Criteria (Not Applied)

These criteria were defined but found zero applicable files:

1. ✅ No unused imports in `portal/` core modules
2. ✅ No unused imports in `packages/` library modules
3. ✅ No unsafe patterns in test files
4. ✅ No `__init__.py` exports at risk
5. ✅ No plugin/registration imports flagged

### Excluded Directories (Untouched)

Per approval rules, excluded directories (`scripts/`, `docs/`, `devops/`, etc.) are not inspected or cleaned.

---

## Verification Plan

### PR #111 Verification Steps

1. **Verify active-dir clean state:**
   ```bash
   ruff check portal packages tests --select F401
   # Expected: All checks passed
   ```

2. **Confirm excluded dirs untouched:**
   ```bash
   git diff main -- scripts/ docs/ devops/
   # Expected: No changes
   ```

3. **Verify no Sigma/workflow changes:**
   ```bash
   git diff main -- .github/workflows/ pyproject.toml
   # Expected: No changes
   ```

### PR #112 Verification Steps (If Monitoring Chosen)

1. Confirm CI integration works
2. Test baseline capture in Actions
3. Validate review checklist template

---

## Rollback Plan

### If PR #111 Needs Reversal

```bash
git revert <commit-sha>
```

This PR is planning/documentation only; rollback is immediate (no code impact).

### If PR #112 Introduces Issues

Monitoring enhancements are non-blocking. Revert the Actions change:

```bash
git revert <commit-sha>
git push
```

Ruff enforcement continues at current 70% Sigma Gate threshold.

---

## Ruff Cleanup Ladder Progress

| Phase | Focus | Status | PR |
|-------|-------|--------|-----|
| Phase 1 | I001 import sorting | ✅ Complete | #109 |
| Phase 2 | W293 trailing whitespace | ✅ Planning approved | #110 |
| Phase 3 | F401 unused imports | 🟢 Plan complete | #111 |
| Phase 4 | Monitoring/CI integration | ⏳ Optional (PR #112) | TBD |

---

## Constraints (Enforced)

- ✅ No source code cleanup in PR #111
- ✅ No import removals
- ✅ No excluded-directory cleanup
- ✅ No workflow changes
- ✅ No Bandit changes
- ✅ No Sigma threshold changes (70% enforced, 75% ratchet held)

---

## Recommendation

**Proceed with Option 1 (Monitoring)** in PR #112 to:
- Lock in the clean F401 state
- Prevent regressions via CI
- Support future Ruff phases

Then **Phase 3 (Ruff Cleanup Ladder) is complete.**
