# Mission Control Phase Two Increment Two A Rollback Notes

Rollback is additive-schema safe and must preserve audit history.

Preserve:

- all command-event history;
- all run-control transition history;
- all durable workflow rows;
- all custom role grants that are not part of canonical system-role reconciliation;
- all evidence artifacts already published.

Do not roll back by deleting history or mutating durable workflow records.

Preferred rollback order:

1. Disable any explicit reconcile invocation path.
2. Leave verification and diagnostics in place.
3. Revert the additive migration only if schema reversal is required and the database is still disposable.
4. Restore the previous code commit with a normal git revert or by re-pointing the branch, preserving audit evidence.
5. Re-run the targeted regression suite after rollback.

If the deployment must be reverted in production, prefer a forward-fix unless the database is known to be disposable and the schema was never used for live transitions.
