# Rollback Plan

If the certification must be reverted, undo the last two commits in reverse order:

1. Remove the evidence commit:
   - `git revert <evidence-commit>`
2. Remove the security subject commit:
   - `git revert <security-commit>`

If the branch must be restored to the remote frozen state, push the reverted branch with `--force-with-lease` only after the revert commits are validated.

Preserve the evidence artifacts when possible; they document the exact tested state that was rejected.
