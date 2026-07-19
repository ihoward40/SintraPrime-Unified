# Mission Control Phase Two Increment Two A Deployment Checklist

1. Verify the baseline tag, reviewed head, and subject code head.
2. Confirm the run-control transition boundary requires tenant scope.
3. Confirm mission_control_run_control_events.principal_id aligns with users.id.
4. Run permission verification, dry-run, and explicit reconcile only through trusted admin paths.
5. Confirm verify and dry-run do not commit.
6. Confirm refreshed JWT access tokens reflect synchronized permissions.
7. Confirm existing access tokens remain unchanged until refresh or reauthentication.
8. Verify the run-control projection tables exist and remain additive only.
9. Verify transition history is append-only and stale-version races append no duplicate event.
10. Run the targeted regression suite, RBAC, auth/JWT, service-unit, and orchestration tests.
11. Run the PostgreSQL concurrency test when a PostgreSQL test database is configured; otherwise record the skip.
12. Run Ruff and `git diff --check` on touched Python files.
13. Regenerate the evidence package from the verified subject code head.
14. Push the branch and keep the PR draft only.
