# Ruff Cleanup Ladder Phase 2 Plan

**Date:** 2026-05-20  
**Context:** Phase 1 (I001 import sorting) completed in PR #109. Active directories now have I001 enforcement. Phase 2 prepares the next safe cleanup target.

---

## Current Repository State

| Metric | Value |
|--------|-------|
| Phase 1 Status | ✅ Complete (I001 in 46 files, 51 → 0 violations) |
| Active dirs (portal/, tests/, etc.) | W293/F401 status must be verified before execution |
| Excluded dirs (legacy/phase dirs) | Baseline violations: 24,378 (from main 2026-05-20) |
| Sigma Gate threshold | 70%; 75% ratchet is held |
| CI ruff command | `ruff check . --output-format=github` (unchanged) |

---

## Phase 2 Candidate Analysis

### Candidate A: W293 (Trailing Whitespace)

**Definition:** Lines with trailing whitespace (invisible, usually from editor misconfiguration).

**Violation Count (active dirs):** TBD — must verify via `ruff check . --select W293`  
**Violation Count (excluded dirs):** Part of 6,566 whitespace violations (W291/W292/W293)  
**Auto-fixable:** ✅ Yes (no semantic impact)  
**Risk:** ⭐ **LOWEST** — whitespace only, purely cosmetic  
**Verification:** `ruff check . --select W293 (zero output after fix)`

**Fix Command (active dirs subset, if violations exist):**
```bash
ruff check . --select W293 --fix
```

---

### Candidate B: F401 (Unused Imports)

**Definition:** Import statement that is never used in the module. Some imports have side effects (e.g., plugin registration, monkeypatching) and should not be removed.

**Violation Count (active dirs):** TBD — must verify via `ruff check . --select F401`  
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

---

## Recommendation: **Phase 2 = W293 Cleanup (Active Dirs Only, Safe Subset)**

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

### Scope (PR #111)

**Option A (Recommended if active dirs have W293 violations):**  
Clean W293 violations from active directories only (portal/, tests/, packages/) using safe auto-fix.

```bash
# Verify active dirs first
ruff check . --select W293 --output-format=json > /tmp/w293-check.json

# If violations exist in active dirs, fix them
ruff check . --select W293 --fix

# Verify zero violations
ruff check . --select W293 --output-format=github
# Expected output: (empty)
```

**Option B (if active dirs are already clean):**  
Skip to Phase 3 planning (F401 dedicated audit with side-effect review).

**Option C (if pilot excluded-dir test desired):**  
Requires explicit user approval. Will clean ONE excluded directory as controlled test, then measure stability before broader excluded-dir campaign.

### Verification Plan

1. **Pre-execution:** Document current state
   ```bash
   ruff check . --select W293 --output-format=json > pre-fix.json
   ```

2. **Post-execution:** Confirm zero violations in active dirs
   ```bash
   ruff check . --select W293 --output-format=json
   # Expected: [] (empty array)
   ```

3. **CI Pass:** Green checkmark on GitHub Actions lint job
   - No new violations introduced
   - All test suites pass

4. **Sigma Gate:** Remain at 70% (Sigma Gate); 75% ratchet held (coverage unaffected)

### Rollback Plan

If any test suite unexpectedly fails (extremely unlikely, since whitespace is inert):

```bash
# Full rollback via git
git revert <commit-sha>
```

**Risk:** < 0.1% (whitespace is guaranteed inert)

---

## Scope Boundaries (Phase 2 Enforced)

✅ **Allowed:**
- W293 cleanup in active directories only
- Auto-fix only (no manual edits)
- Verification via ruff re-run

❌ **Not Allowed:**
- Excluded directories (no broad cleanup without separate approval)
- Workflow changes
- Bandit baseline changes
- Sigma Gate threshold changes
- Ratchet release (75% ratchet remains held)

---

## Ruff Gate Status (After Phase 2)

| Rule | Phase | Status | CI Enforcement |
|------|-------|--------|---|
| I001 | 1 | ✅ Done | ✅ New violations fail CI |
| W293 | 2 | 📋 Planned | ⏳ To be enforced after cleanup |
| F401 | 3 | 📋 Queued | ⏳ Manual review, then enforce |
| Others | TBD | ⏳ Excluded | ⏳ Baseline holds them |

---

## Summary

- **Selected target:** W293 (Trailing Whitespace)
- **Risk level:** ⭐ Lowest
- **Scope:** Active directories only (safe auto-fix subset)
- **Rejected alternative:** F401 (requires side-effect review, defer to Phase 3)
- **Affected files:** TBD in PR #111 (depends on verification result)
- **Execution command:** `ruff check . --select W293 --fix` (active dirs)
- **Verification:** Rerun ruff, expect zero output
- **Rollback:** Single `git revert` if needed (extremely unlikely)
- **Boundaries:** No excluded-dir cleanup, no workflow changes, no Sigma changes
- **Sigma Gate threshold:** 70%; 75% ratchet held
- **PR #111 locked to:** Option A (active-dir W293 auto-fix) OR Option B (skip to Phase 3 planning) OR Option C (single approved pilot excluded-dir only)

---

**Next step:** PR #111 will execute Phase 2 per chosen option (A, B, or C) with exact scope verification.
