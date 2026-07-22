# Correlation Context Exception Cleanup Evidence

## Scope

PR-A only: correlation middleware exception cleanup.

Changed runtime file:

- `portal/middleware/correlation_middleware.py`

Changed regression test:

- `portal/tests/test_correlation_middleware_exception_regression.py`

Out of scope:

- PR-B database/bootstrap work
- PR-C workshop work
- PR #219
- workshop runtime files
- shared migration files
- frontend files
- payment files
- deployment or activation

## Base anchor

- Base branch: `origin/main`
- Base commit: `cb343b92ef776e2a827ee459d9512179bc9aad6a`
- Base tree: `740a752b200672a5840bf9c1647b628eed6d403c`

## Defect reproduction on untouched base

Command context:

- Temporary detached worktree from `origin/main`
- FastAPI app with `CorrelationMiddleware`
- POST route raises `RuntimeError("boom")`
- Client uses `httpx.ASGITransport`

Observed on untouched `origin/main`:

- Exception type: `RuntimeError`
- Exception text: `<Token used var=<ContextVar name='_correlation_context' ...> has already been used once`

Conclusion:

- The original downstream `RuntimeError("boom")` was masked by duplicate ContextVar token reset cleanup.
- Current `origin/main` did not already contain an equivalent correction.

## Root cause

`CorrelationMiddleware.dispatch()` reset the middleware-owned context token in both the `except Exception` block and the `finally` block. When a downstream exception occurred, the token was used once in `except` and then used again in `finally`. The second reset raised a `RuntimeError`, masking the original downstream exception.

## Correction

The middleware now performs cleanup once in `finally`:

- reset authentication-enrichment request tokens through `_reset_auth_tokens(request)`
- reset the middleware-owned bind token once through `reset_current_context(bind_token)`

The explicit `except Exception` cleanup block was removed. Downstream exceptions propagate with their original type and message.

## Required runtime behavior

- Correlation token resets exactly once: verified by code inspection and exception regression.
- Original downstream exception is not masked: verified by `test_post_exception_preserves_original_runtime_error`.
- Successful requests still clean up context and return `X-Request-ID`: verified by `test_post_success_still_returns_request_id_header` and existing middleware tests.
- Exception requests still clean up context: verified by certification suite and single-reset cleanup path.
- No correlation context leaks between requests: covered by existing audit/correlation and HTTP/WebSocket certification suites.
- Request-ID behavior remains consistent with certified boundaries: existing certification suites passed.

## Verification

Focused regression:

- Command: `python -m pytest portal/tests/test_correlation_middleware_exception_regression.py --tb=short -rw`
- Result: 2 passed, 0 failed, 0 skipped

Certification suites:

- Command: `python -m pytest portal/tests/test_audit_correlation_non_http_certification.py portal/tests/test_http_correlation_ws_hardening_certification.py portal/tests/test_auth_tenant_rbac_certification.py --tb=short -rw`
- Result: 189 passed, 0 failed, 0 skipped, 88 warnings

Relevant middleware tests:

- Command: `python -m pytest portal/tests/test_middleware_units.py --tb=short -rw`
- Result: 33 passed, 0 failed, 0 skipped, 1 warning

Consolidated selected matrix:

- Command: `python -m pytest portal/tests/test_correlation_middleware_exception_regression.py portal/tests/test_audit_correlation_non_http_certification.py portal/tests/test_http_correlation_ws_hardening_certification.py portal/tests/test_auth_tenant_rbac_certification.py portal/tests/test_middleware_units.py --tb=short -rw`
- Result: 224 passed, 0 failed, 0 skipped, 89 warnings

Static and repository checks:

- `python -m ruff check portal/middleware/correlation_middleware.py portal/tests/test_correlation_middleware_exception_regression.py`: PASS
- `python scripts/ci/validate_repository_claims.py`: PASS
- `git diff --check`: PASS
- changed-file sensitive-value scan: PASS

## Warnings

Unresolved warnings are PyJWT `InsecureKeyLengthWarning` warnings from existing certification/middleware tests using short test HMAC keys. They are not introduced by the correlation middleware cleanup.

## Risk and rollback

Risk:

- Low to moderate. The change is narrow but affects shared HTTP middleware cleanup behavior.

Rollback:

- Revert the PR-A commit that changes `portal/middleware/correlation_middleware.py` and `portal/tests/test_correlation_middleware_exception_regression.py`.

## Nonclaims

This evidence does not claim:

- PR-B database/bootstrap publication
- PR-C workshop publication
- modification of PR #219
- workshop runtime activation
- migration repair
- frontend repair
- payment repair
- deployment readiness
- auto-merge or merge approval
