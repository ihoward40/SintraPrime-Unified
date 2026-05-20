# Ruff Cleanup Ladder Phase 2 Plan

**Date:** 2026-05-20  
**Context:** Phase 1 (I001 import sorting) completed in PR #109. Active directories now have I001 enforcement. Phase 2 prepares the next safe cleanup target.

---

## Current Repository State

| Metric | Value |
|--------|-------|
| Phase 1 Status | ✅ Complete (I001 in 46 files, 51 → 0 violations) |
| Active dirs (portal/, tests/, etc.) | 100% clean for W293 + F401 |
| Excluded dirs (legacy/phase dirs) | Baseline violations: 24,378 (from main 2026-05-20) |
| Sigma Gate threshold | 75% (held) |
| CI ruff command | `ruff check . --output-format=github` (unchanged) |

---

## Phase 2 Candidate Analysis

### Candidate A: W293 (Trailing Whitespace)

**Definition:** Lines with trailing whitespace (invisible, usually from editor misconfiguration).

**Violation Count (active dirs):** 0  
**Violation Count (excluded dirs):** Part of 6,566 whitespace violations (W291/W292/W293)  
**Auto-fixable:** ✅ Yes (no semantic impact)  
**Risk:** ⭐ **LOWEST** — whitespace only, purely cosmetic  
**Verification:** `ruff check . --select W293 (zero output after fix)`

**Fix Command (excluded dirs):**
```bash
ruff check <excluded_dir> --select W293 --fix
```

**Example Files (from baseline report):**
- `core/` (6,701 total violations, subset are W293)
- `integrations/` (1,721 total violations)
- `phase19/` (530 total violations)

---

### Candidate B: F401 (Unused Imports)

**Definition:** Import statement that is never used in the module. Some imports have side effects (e.g., plugin registration, monkeypatching) and should not be removed.

**Violation Count (active dirs):** 0  
**Violation Count (excluded dirs):** 1,187 (per baseline report)  
**Auto-fixable:** ⚠️ Partial (ruff can identify, but ~15-20% require manual review for side effects)  
**Risk:** ⭐⭐ **MEDIUM** — requires code review per file, side-effect risk  
**Verification:** Manual review + `pytest` to catch side-effect breakage

**Review Process:**
1. `ruff check . --select F401 --output-format=json` → export list
2. Group by directory
3. For each file: inspect imports for side effects (decorators, plugin registration, etc.)
4. Mark safe removals vs. keep-as-is
5. Apply removals selectively
6. Run full test suite

**Example Files (high F401 count in excluded dirs):**
- `core/` (subset of 6,701 violations)
- `backend/` (572 violations)

---

## Recommendation: **Phase 2 = W293 Cleanup (Active Dirs → Excluded Dirs Subset)**

### Rationale

1. **Lowest risk:** Whitespace-only fixes, zero semantic impact
2. **Fully auto-fixable:** Single `ruff --fix` command, no manual review needed
3. **Natural progression:** Phase 1 → Phase 1b (whitespace) → Phase 2 (F401)
4. **Verification is trivial:** Rerun ruff, confirm zero output
5. **No test risk:** Whitespace changes cannot break functionality
6. **Prerequisite for Phase 3:** Cleaner codebase before F401 manual reviews

### Rejected Alternative: F401 (Unused Imports)

**Why not Phase 2?**
- ⚠️ Requires manual side-effect review per file (1,187 violations)
- ⚠️ Risk of silent breakage if side-effect imports are removed
- ⚠️ Needs full test suite run after each batch of deletions
- ⚠️ Higher cognitive load: "Is this import doing something I don't see?"

**When to target F401?**
- After Phase 2 completes and codebase confidence is high
- With dedicated code review cycle (not a single PR)
- Possibly in Phase 3 with explicit side-effect audit first

---

## Phase 2 Execution Plan

### Scope

**Target:** All excluded directories with W293 violations (subset of 6,566 whitespace total)

**Directories to clean (order TBD in PR #111 execution):**
- `core/`
- `integrations/`
- `docket/`
- `predictive/`
- And 40+ others (per exclude list in pyproject.toml)

### Execution Command (PR #111)

```bash
# Run against each excluded directory in sequence
ruff check core/ --select W293,W291,W292 --fix
ruff check integrations/ --select W293,W291,W292 --fix
# ... etc. for all excluded dirs

# Verify: zero violations remain
ruff check . --select W293,W291,W292 --output-format=github
# Expected output: (empty)
```

### Verification Plan

1. **Pre-fix:** Run baseline to document current state
   ```bash
   ruff check . --select W293,W291,W292 --output-format=json > pre-fix.json
   jq 'length' pre-fix.json  # Document violation count
   ```

2. **Post-fix:** Confirm zero violations
   ```bash
   ruff check . --select W293,W291,W292 --output-format=json
   # Expected: [] (empty array)
   ```

3. **CI Pass:** Green checkmark on GitHub Actions lint job
   - No new violations introduced
   - All test suites pass (should be instant — no logic changes)

4. **Sigma Gate:** Remain at 75% threshold (coverage unaffected)

### Rollback Plan

If any test suite unexpectedly fails (unlikely, since whitespace is inert):

```bash
# Full rollback via git
git revert <commit-sha>

# Alternative: selective rollback per file
git checkout HEAD -- <whitespace-fixed-file>
```

**Risk:** < 0.1% (whitespace is guaranteed inert)

---

## After Phase 2 Completes (Phase 3 Preparation)

Once PR #111 merges with W293 cleanup:

1. **Update baseline report** to show W293 = 0
2. **Remove W293 from per-file-ignores** (if present in any entry)
3. **Plan Phase 3:** F401 with dedicated side-effect audit
4. **Consider:** W291/W292 cleanup alongside W293 (same PR is safe)

---

## Ruff Gate Status (After Phase 2)

| Rule | Phase | Status | CI Enforcement |
|------|-------|--------|---|
| I001 | 1 | ✅ Done | ✅ New violations fail CI |
| W293 | 2 |�📋 Planned | ⏳ To be enforced after cleanup |
| F401 | 3 | 📋 Queued | ⏳ Manual review, then enforce |
| Others | TBD | ⏳ Excluded | ⏳ Baseline holds them |

---

## Summary

- **Selected target:** W293 (Trailing Whitespace)
- **Risk level:** ⭐ Lowest
- **Rejected alternative:** F401 (requires side-effect review, move to Phase 3)
- **Affected files:** Subset of excluded dirs (to be enumerated in PR #111)
- **Execution command:** `ruff check . --select W293 --fix` (per directory)
- **Verification:** Rerun ruff, expect zero output
- **Rollback:** Single `git revert` if needed (extremely unlikely)
- **Sigma 75% threshold:** Remains held (whitespace fixes don't affect coverage)

---

**Next step:** PR #111 will execute Phase 2 with the exact file list and cumulative violation counts.
