# Repository Convergence Increment Two — Rollback Instructions

This document provides actionable instructions for reverting all changes made in
Repository Convergence Increment Two. The increment modifies exactly 14 files:
9 existing tracked files (updates) and 5 newly created files (creates).

No runtime, CI, migration, model, test, or frontend files were changed. Reverting
is safe and has no runtime impact.

---

## File inventory

### Updated files (9) — revert to previous version

| # | Path | Action | Revert method |
|---|------|--------|---------------|
| 1 | `docs/ARCHITECTURE.md` | UPDATE | `git checkout HEAD -- docs/ARCHITECTURE.md` (before commit) or `git checkout <pre-increment-commit> -- docs/ARCHITECTURE.md` (after commit) |
| 2 | `docs/CAPABILITY_INDEX.md` | UPDATE | `git checkout HEAD -- docs/CAPABILITY_INDEX.md` or `git checkout <pre-increment-commit> -- docs/CAPABILITY_INDEX.md` |
| 3 | `docs/CLAIMS.md` | UPDATE | `git checkout HEAD -- docs/CLAIMS.md` or `git checkout <pre-increment-commit> -- docs/CLAIMS.md` |
| 4 | `docs/DATABASE_AUTHORITY.md` | UPDATE | `git checkout HEAD -- docs/DATABASE_AUTHORITY.md` or `git checkout <pre-increment-commit> -- docs/DATABASE_AUTHORITY.md` |
| 5 | `docs/SECURITY.md` | UPDATE | `git checkout HEAD -- docs/SECURITY.md` or `git checkout <pre-increment-commit> -- docs/SECURITY.md` |
| 6 | `docs/QUICK_START.md` | UPDATE | `git checkout HEAD -- docs/QUICK_START.md` or `git checkout <pre-increment-commit> -- docs/QUICK_START.md` |
| 7 | `docs/REPOSITORY_STATUS.md` | UPDATE | `git checkout HEAD -- docs/REPOSITORY_STATUS.md` or `git checkout <pre-increment-commit> -- docs/REPOSITORY_STATUS.md` |
| 8 | `docs/governance/OPEN_PR_DISPOSITION.md` | UPDATE | `git checkout HEAD -- docs/governance/OPEN_PR_DISPOSITION.md` or `git checkout <pre-increment-commit> -- docs/governance/OPEN_PR_DISPOSITION.md` |
| 9 | `docs/governance/MISSION_CONTROL_OBSERVATORY_AUTHORITY.md` | UPDATE | `git checkout HEAD -- docs/governance/MISSION_CONTROL_OBSERVATORY_AUTHORITY.md` or `git checkout <pre-increment-commit> -- docs/governance/MISSION_CONTROL_OBSERVATORY_AUTHORITY.md` |

### Newly created files (5) — delete

| # | Path | Action | Revert method |
|---|------|--------|---------------|
| 10 | `docs/repository-convergence/increment-2-scope-and-discrepancy-matrix.md` | CREATE | `rm docs/repository-convergence/increment-2-scope-and-discrepancy-matrix.md` (before commit) or `git rm docs/repository-convergence/increment-2-scope-and-discrepancy-matrix.md` (after commit) |
| 11 | `docs/repository-convergence/increment-2-discrepancy-matrix.json` | CREATE | `rm docs/repository-convergence/increment-2-discrepancy-matrix.json` or `git rm docs/repository-convergence/increment-2-discrepancy-matrix.json` |
| 12 | `docs/repository-convergence/increment-2-decision-log.json` | CREATE | `rm docs/repository-convergence/increment-2-decision-log.json` or `git rm docs/repository-convergence/increment-2-decision-log.json` |
| 13 | `docs/repository-convergence/increment-2-architectural-map.md` | CREATE | `rm docs/repository-convergence/increment-2-architectural-map.md` or `git rm docs/repository-convergence/increment-2-architectural-map.md` |
| 14 | `docs/repository-convergence/increment-2-rollback.md` | CREATE | `rm docs/repository-convergence/increment-2-rollback.md` or `git rm docs/repository-convergence/increment-2-rollback.md` |

---

## Scenario 1: Revert before commit (uncommitted changes)

If the increment has NOT been committed yet, all changes are in the working tree
and/or staging area. To revert:

```bash
# Revert all 9 updated files to their pre-edit state (HEAD = 48e2caa7)
git checkout HEAD -- docs/ARCHITECTURE.md \
  docs/CAPABILITY_INDEX.md \
  docs/CLAIMS.md \
  docs/DATABASE_AUTHORITY.md \
  docs/SECURITY.md \
  docs/QUICK_START.md \
  docs/REPOSITORY_STATUS.md \
  docs/governance/OPEN_PR_DISPOSITION.md \
  docs/governance/MISSION_CONTROL_OBSERVATORY_AUTHORITY.md

# Delete all 5 newly created files
rm docs/repository-convergence/increment-2-scope-and-discrepancy-matrix.md
rm docs/repository-convergence/increment-2-discrepancy-matrix.json
rm docs/repository-convergence/increment-2-decision-log.json
rm docs/repository-convergence/increment-2-architectural-map.md
rm docs/repository-convergence/increment-2-rollback.md

# Verify clean state
git status --porcelain=v1
# Expected: empty output
```

If some files were staged with `git add`, also run:
```bash
git reset HEAD docs/repository-convergence/increment-2-*
```

---

## Scenario 2: Revert after a normal (non-merge) commit

If the increment was committed as a single normal commit (not a merge commit),
use `git revert` to create an inverse commit:

```bash
# Identify the increment commit SHA (replace <commit-sha> with the actual SHA)
# This is the SHA of the commit that contains all 14 file changes.

# Create an inverse commit
git revert <commit-sha> --no-edit

# This creates a new commit that undoes all 14 file changes.
# The original increment commit remains in history.
```

Alternatively, to reset the branch to the pre-increment state (destructive — rewrites
history):
```bash
# Reset to the commit before the increment
git reset --hard <pre-increment-commit-sha>
# The pre-increment commit is 48e2caa7 (the branch HEAD before this increment)
```

---

## Scenario 3: Revert after a merge commit

If the increment was merged via a merge commit (e.g., a GitHub PR merge), use
`git revert -m 1` to revert the merge:

```bash
# Identify the merge commit SHA (replace <merge-sha> with the actual SHA)

# Revert the merge, keeping the first parent (mainline)
git revert -m 1 <merge-sha> --no-edit

# This creates a new commit that undoes all changes introduced by the merge.
```

To re-apply the increment after reverting a merge:
```bash
# Revert the revert commit
git revert <revert-commit-sha> --no-edit
```

---

## Pre-increment baseline

The pre-increment baseline is:
```
Commit: 48e2caa759661cc75617cc752bcc26eaad666647
Tree:   9ee6d193dd7f607cd59487df9ef26d46b9593803
Branch: docs/repository-convergence-increment-2
```

This is the state of `origin/main` at the time the increment was authored. All 9
updated files should be reverted to this commit. The 5 created files did not exist
at this commit and should be deleted.

---

## Verification after rollback

```bash
# Confirm no changes remain
git status --porcelain=v1
# Expected: empty output

# Confirm no increment-2 files exist
ls docs/repository-convergence/increment-2-* 2>/dev/null
# Expected: no such file or directory

# Confirm authority docs are at pre-increment baseline
grep -l "10cad07f" docs/ARCHITECTURE.md docs/CAPABILITY_INDEX.md docs/CLAIMS.md \
  docs/DATABASE_AUTHORITY.md docs/SECURITY.md docs/QUICK_START.md \
  docs/REPOSITORY_STATUS.md docs/governance/OPEN_PR_DISPOSITION.md \
  docs/governance/MISSION_CONTROL_OBSERVATORY_AUTHORITY.md
# Expected: all 9 files listed (stale anchors restored)

# Confirm no 48e2caa7 anchor in authority docs
grep -r "48e2caa7" docs/ARCHITECTURE.md docs/CAPABILITY_INDEX.md docs/SECURITY.md
# Expected: no matches
```

---

## Important notes

- This rollback only affects documentation files. No runtime, CI, migration, model,
  test, or frontend files were changed by this increment.
- The future commit SHA of this increment is not known until the increment is
  committed. Replace `<commit-sha>` and `<merge-sha>` placeholders with actual SHAs
  at revert time.
- The pre-increment commit SHA is `48e2caa7` and is known now.
- If the increment has been pushed to a remote and merged, coordinate the revert
  with the team to avoid conflicting with downstream work.
- Rolling back this increment restores the stale authority anchors (10cad07f). This
  is intentional — the rollback returns the repository to its exact pre-increment
  state, including stale anchors.