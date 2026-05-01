# Phase 21D: App Wiring & Integration Tests

**Status:** Complete
**PR:** #47
**Branch:** `manus/PHASE-21D-app-wiring`
**Head Commit:** `020c33c`

## Summary
Phase 21D successfully wires the Phase 21C SSO middleware components into the FastAPI portal application and fixes three bugs discovered during the wiring audit.

## Deliverables

### 1. `portal/main.py` Wiring
- Registered `_LazySSOSessionMiddleware` in the middleware stack. It reads `app.state.sso_session_manager` lazily at the first request to avoid startup ordering issues with Starlette's middleware registration.
- Initialised `SessionMiddlewareManager` and `TokenRefreshManager` in the lifespan context manager and attached both to `app.state`.
- Conditionally initialised `OktaProvider`, `AzureADProvider`, and `GoogleWorkspaceProvider` from config. Skips with `logger.info` when required env vars are absent.
- Gracefully stops all active `TokenRefreshManager` loops on shutdown.
- Fixed `RateLimiterMiddleware` import name (was incorrectly `RateLimitMiddleware`).
- Removed unused `ws_manager.startup/shutdown` calls (`ConnectionManager` has no such methods).

### 2. `portal/sso/session_store.py` Bug Fix
- `RedisSessionStore.__init__` now accepts `redis_url: str` and creates the `redis.Redis` client internally via `Redis.from_url()`.
- Raises `ValueError` when called with neither `redis_client` nor `redis_url`.
- `redis_client` takes precedence when both are provided.

### 3. `portal/sso/middleware.py` Bug Fix
- `stop_refresh_loop` now explicitly pops `session_id` from `active_tasks` in a `finally` block. Previously, the cancelled task remained in the dict.

### 4. `portal/sso/__init__.py` Exports
- Exported all Phase 21C middleware classes: `SessionMiddlewareManager`, `TokenRefreshManager`, `IdPErrorHandler`, `IdPError`, `SessionMiddleware`, `SessionToken`.
- Exported Phase 21A provider classes: `AzureADProvider`, `AzureConfig`, `GoogleWorkspaceProvider`, `GoogleConfig`, `OktaProvider`, `OktaConfig`.

### 5. `portal/sso/tests/test_integration.py`
Added 22 integration tests covering:
- Module export completeness
- `RedisSessionStore` constructor (4 cases: no args, `redis_client`, `redis_url`, both)
- `SessionMiddlewareManager` CRUD (create, validate, invalidate, expiry, determinism)
- `TokenRefreshManager` circuit breaker and loop lifecycle
- `SessionMiddleware` fail-closed behaviour (protected route → 401, public route → 200)
- `portal/main.py` wiring smoke tests

## Test Results
- **154/154 tests passing** (all SSO tests; `test_sso.py` excluded due to a pre-existing syntax error unrelated to this PR).
- **0 bandit issues** on production files.

## Known Pre-existing Issue (Not in Scope)
`portal/models/case.py` has a SQLAlchemy `metadata` field name collision with the Declarative API. This causes `portal.main` to fail on import in test environments that load the full model chain. This is tracked separately for Phase 22 cleanup.
