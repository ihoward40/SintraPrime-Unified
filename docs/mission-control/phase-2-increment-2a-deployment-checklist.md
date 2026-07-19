# Mission Control Phase Two Increment Two A Deployment Checklist

1. Verify baseline tag and implementation commit.
2. Confirm the worktree is clean except for the intended closure commit.
3. Run the permission verification mode in an isolated evidence subprocess.
4. Run the permission dry-run mode and confirm it performs no writes.
5. Run explicit reconcile only when authorized and auditable.
6. Confirm refreshed JWT access tokens reflect synchronized permissions.
7. Confirm existing access tokens remain unchanged until refresh or reauthentication.
8. Verify the run-control projection tables exist and are additive only.
9. Verify transition history is append-only and the stale-version path emits no duplicate event.
10. Re-run the targeted and regression test matrix.
11. Recompute the migration checksum.
12. Verify `git diff --check` and Ruff on touched Python files.
13. Update the evidence package with the final commit, tree, parent, and branch.
14. Push the branch and keep the PR draft only.
