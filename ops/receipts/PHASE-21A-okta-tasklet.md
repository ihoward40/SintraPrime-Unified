# Phase 21A: Okta OAuth 2.0 Provider — Tasklet Build Receipt

**Status:** ✅ COMPLETE — All review items addressed and merged to `main`

---

## Merge History

| PR | Commit | Description |
|---|---|---|
| #36 | `72582a6` | Initial real httpx.AsyncClient implementation (squash-merged) |
| #41 | `0bcca33` | Post-review fixes: timeout, ValueError, revocation, tests, .env.example |

**Final `main` HEAD:** `0bcca33`

---

## Summary

Okta OAuth 2.0 OIDC provider with a real HTTPS boundary via injectable `httpx.AsyncClient`.
All stubs replaced with production code. Tests use dependency injection — no real network calls.

---

## Implementation Details

### Architecture: Dependency Injection Pattern

```python
# Tests: inject a mocked client
provider = OktaProvider(config, client=AsyncMock(spec=httpx.AsyncClient))

# Production: default client uses config.timeout_seconds
provider = OktaProvider(config)
```

**Real HTTPS Endpoints:**

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `{okta_domain}/oauth2/v1/token` | Authorization code → token exchange |
| `GET` | `{okta_domain}/oauth2/v1/userinfo` | Fetch user profile |
| `POST` | `{okta_domain}/oauth2/v1/revoke` | Revoke old refresh token before refresh |

**Failure Handling:**

- `HTTPStatusError` caught and re-raised as `ValueError` (callers never see raw httpx internals)
- Network errors wrapped in `ValueError` with context
- Timeout sourced from `OktaConfig.timeout_seconds` via `httpx.Timeout(float(config.timeout_seconds))`
- Async context manager cleanup: `async with OktaProvider(...) as provider:`

**Refresh Token Revocation:**

`refresh_access_token()` calls `_revoke_token()` at `/oauth2/v1/revoke` before issuing a new token,
mirroring the Sessions layer's revocation behaviour. Revocation failure is fail-open (logged, non-fatal).

---

## Review Items Addressed (PR #41)

| # | Item | Resolution |
|---|---|---|
| 1 | Sync PR body / receipt with reality | Receipt updated with correct SHAs and test counts |
| 2 | `OktaConfig.from_env()` parameter names | Already correct; `test_from_env_success` + `test_from_env_missing_var` added to prove it |
| 3 | Use configured timeout | `httpx.Timeout(float(config.timeout_seconds))` — no hardcoded values |
| 4 | Handle HTTP errors explicitly | `HTTPStatusError` → `ValueError` in both `exchange_code_for_token` and `get_user_info` |
| 5 | Revoke old refresh tokens | `refresh_access_token()` calls `/revoke` before `/token`; test asserts call order |
| 6 | Expand `.env.example` placeholders | All `OKTA_*` vars with REQUIRED/OPTIONAL labels and stricter security warnings |

---

## Test Evidence

```
21 passed in 0.85s
```

```
Run metrics:
  Total issues (by severity):
    Low: 0  Medium: 0  High: 0
```

**Test breakdown (21 total):**

| Class | Tests |
|---|---|
| `TestOktaConfig` | `test_init_valid`, `test_missing_domain`, `test_invalid_protocol`, `test_missing_client_id`, `test_missing_redirect_uri`, `test_from_env_success`, `test_from_env_missing_var` |
| `TestOktaProvider` | `test_get_authorization_url_with_state`, `test_get_authorization_url_auto_state`, `test_timeout_applied_from_config`, `test_exchange_code_for_token`, `test_exchange_code_empty_code`, `test_exchange_code_http_error_raises_value_error`, `test_get_user_info`, `test_get_user_info_empty_token`, `test_get_user_info_http_error_raises_value_error`, `test_refresh_access_token_revokes_old_token`, `test_refresh_access_token_empty_raises`, `test_validate_state_valid`, `test_validate_state_invalid`, `test_response_models_new_fields` |

---

## Files Changed

| File | Purpose |
|---|---|
| `portal/sso/okta_provider.py` | OAuth 2.0 flow — timeout from config, ValueError wrapping, `refresh_access_token` + `_revoke_token` |
| `portal/sso/okta_config.py` | Config validation, `from_env()` classmethod |
| `portal/sso/okta_models.py` | Response models — added `refresh_token`, `preferred_username`, `groups` |
| `portal/sso/tests/test_okta.py` | 21 tests (was 10) |
| `.env.example` | Expanded Okta section with REQUIRED/OPTIONAL labels |

---

## CI Status (PR #41 head `d2b7963`)

| Workflow | Result | Notes |
|---|---|---|
| SintraPrime CI — 797 Tests | failure | Pre-existing on `main` (numpy/collection errors unrelated to Okta) |
| Sigma Gate | failure | Pre-existing coverage threshold failure on `main` |
| IssueVerifier CI | **success** | ✅ |
| security (bandit) | **success** | ✅ 0 issues |

The test and Sigma Gate failures are pre-existing on `main` at `72582a6` and are not introduced by this PR.

---

## Integration Path (Phase 21B)

**Next:** Route registration in portal FastAPI app

```python
@router.post("/auth/okta/callback")
async def okta_callback(code: str, state: str):
    provider = OktaProvider(OktaConfig.from_env())
    # Validate state (sync, constant-time)
    # Exchange code for token (async)
    # Fetch user info (async)
    # Create session via SessionManager and return redirect
```

---

**Built by:** Tasklet AI + Manus review fixes
**Date:** 2026-05-01
**Verified:** ✅ Real HTTP boundary, 21/21 tests, 0 bandit issues
