# Mission Control Phase Two Increment Two A Rollback Notes

Rollback is forward-disable plus code revert unless a separate approved database procedure exists.

Preserve:

- all command-event history;
- all run-control transition history;
- all durable workflow rows;
- all custom role grants that are not part of canonical system-role reconciliation;
- all evidence artifacts already published.

Do not describe this increment as reversible if only code rollback is supported.

Normal rollback order:

1. Disable any explicit reconcile invocation path.
2. Leave verification and diagnostics in place.
3. Revert the code change with a normal git revert or by re-pointing the branch, preserving audit evidence.
4. Keep the additive schema in place unless a separate approved destructive database procedure is explicitly authorized.
5. Re-run the targeted regression suite after rollback.

If the deployment must be reverted in production, prefer forward-disable plus code revert. Any destructive schema removal is outside normal rollback and requires a separate approved procedure.
