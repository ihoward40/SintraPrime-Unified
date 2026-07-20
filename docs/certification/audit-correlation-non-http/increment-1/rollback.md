# Rollback Plan

If this certification increment must be reverted:

1. Remove the evidence commit:
   - `git revert <evidence-commit>`

2. Remove the implementation commit:
   - `git revert <implementation-commit>`

3. If the branch must be restored to the remote frozen state, push the reverted branch with `--force-with-lease` only after the revert commits are validated.

Preserve the evidence artifacts when possible; they document the exact tested state that was rejected.

## What is reverted
- portal/auth/correlation.py (new file)
- portal/auth/audit_envelope.py (new file)
- portal/auth/websocket_auth.py (new file)
- portal/admin/dashboard.py (modified: auth/audit controls)
- portal/main.py (modified: dashboard router mount)
- portal/tests/test_audit_correlation_non_http_certification.py (new file)
- .github/workflows/ci.yml (modified: new CI job)
- pyproject.toml (modified: B008 ignore for portal/admin)
- docs/certification/audit-correlation-non-http/increment-1/ (new evidence)
