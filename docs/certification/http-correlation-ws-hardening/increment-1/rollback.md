# Rollback Plan

If this certification increment must be reverted:

## Authoritative rollback method (post-merge)

After merge, revert the merge commit with -m 1:

```
git revert -m 1 <merge-commit-sha>
```

## Component-commit alternative

Revert the evidence commit, then the implementation commit, in reverse order:

```
git revert <evidence-commit-sha>
git revert <implementation-commit-sha>
```

## What is reverted

See the exact changed-file list in the PR body and the git diff output.
The implementation commit changes:
- .github/workflows/ci.yml (modified)
- portal/admin/dashboard.py (modified)
- portal/auth/correlation.py (modified)
- portal/auth/rbac.py (modified)
- portal/auth/websocket_auth.py (modified)
- portal/auth/ws_hardening.py (new)
- portal/main.py (modified)
- portal/middleware/correlation_middleware.py (new)
- portal/tests/test_http_correlation_ws_hardening_certification.py (new)

The evidence commit changes:
- docs/certification/http-correlation-ws-hardening/increment-1/ (new evidence directory)

## Warnings against partial rollback

Do not partially revert. A partial rollback could leave:
- CorrelationMiddleware registered in main.py without the middleware module
- WebSocket hardening imports in dashboard.py without the ws_hardening module
- CI referencing a missing certification test
- Evidence files describing controls no longer present
- correlation.py public context API used by middleware without the module
- rbac.py Request-injected get_current_user used by routes without the dependency