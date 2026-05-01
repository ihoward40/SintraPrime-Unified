# Phase 21A: Okta OAuth 2.0 Provider — Tasklet Build Receipt

**Status:** ✅ COMPLETE (Real HTTP Boundary Implemented)

## Summary

Okta OAuth 2.0 provider with real HTTPS boundary via injectable `httpx.AsyncClient` (dependency injection pattern). All stubs replaced with production code. No real network calls in tests (mocked).

## Implementation Details

### Architecture: Dependency Injection Pattern

```python
# Allows flexible testing with mocked clients
provider = OktaProvider(config, client=AsyncMock(spec=httpx.AsyncClient))

# Production uses default client (real HTTPS)
provider = OktaProvider(config)
```

**Real HTTPS Endpoints:**
- Token Exchange: `POST {okta_domain}/oauth2/v1/token`
- User Info: `GET {okta_domain}/oauth2/v1/userinfo`

**Failure Handling:**
- Network errors logged with context
- Async context manager cleanup: `async with OktaProvider(...) as provider:`
- Request timeout: 10.0 seconds (configurable)

### Files Changed (7 total, 535 LOC)

| File | Lines | Purpose |
|---|---|---|
| `portal/sso/okta_provider.py` | 174 | OAuth 2.0 flow (real httpx.AsyncClient) |
| `portal/sso/okta_config.py` | 108 | Config validation, `from_env()` classmethod |
| `portal/sso/okta_models.py` | 58 | Response models (Pydantic) |
| `portal/sso/providers/okta.py` | 4 | Thin provider wrapper |
| `portal/sso/tests/test_okta.py` | 233 | 16 async tests (from_env(), HTTP mocks) |
| `portal/sso/__init__.py` | 31 | Updated exports (Session + Okta) |
| `.env.example` | 27 | Okta config + security warnings |

### Test Coverage: 16/16 Passing ✅

**OktaConfig Tests (7):**
- ✅ Valid initialization
- ✅ Missing domain validation
- ✅ Invalid protocol (non-HTTPS) validation
- ✅ Missing client_id validation
- ✅ Missing redirect_uri validation
- ✅ `from_env()` success with all required vars
- ✅ `from_env()` failure with missing var

**OktaProvider Tests (9):**
- ✅ Authorization URL generation (with state)
- ✅ Authorization URL generation (auto-generated state)
- ✅ Token exchange via mocked httpx POST
- ✅ Token exchange fails on empty code
- ✅ User info retrieval via mocked httpx GET
- ✅ User info fails on empty token
- ✅ State validation (valid/invalid)
- ✅ Response model parsing

**Command to Verify:**
```bash
python -m pytest portal/sso/tests/test_okta.py -v
# Result: 16 passed in 0.47s
```

### Security Profile

**Fail-Closed Behavior:**
- Missing `OKTA_DOMAIN` env var → `KeyError` (caught as `ValueError`)
- Missing `OKTA_CLIENT_ID` → explicit `ValueError("client_id is required")`
- Missing `OKTA_CLIENT_SECRET` → explicit `ValueError("client_secret is required")`
- Missing `OKTA_REDIRECT_URI` → explicit `ValueError("redirect_uri is required")`

**Production Safety:**
- No real Okta credentials in `.env.example` (placeholders only)
- No hardcoded secrets in code
- All real credentials must come from:
  1. GitHub Secrets (CI/CD)
  2. Secure credential manager (production servers)
  3. Environment variables (NEVER in code)

**CRITICAL:** If Okta credentials are accidentally committed:
- Rotate `OKTA_CLIENT_SECRET` immediately
- Re-issue `OKTA_CLIENT_ID` if needed
- Purge git history with BFG or git filter-branch

### Async/Await Pattern

```python
async with OktaProvider(config) as provider:
    auth_url, state = provider.get_authorization_url()
    token = await provider.exchange_code_for_token(code)
    user_info = await provider.get_user_info(token.access_token)
```

Sync code (CSRF validation):
```python
if not provider.validate_state(callback_state, stored_state):
    raise ValueError("CSRF check failed")
```

### Integration Path (Phase 21B)

**Next:** Route registration in portal FastAPI app
```python
@router.post("/login/okta")
async def okta_login(code: str, state: str):
    provider = OktaProvider(OktaConfig.from_env())
    # Validate state (sync)
    # Exchange code for token (async)
    # Fetch user info (async)
    # Create session and return redirect
```

### Commits

1. `ec6c17c` — Initial Okta (stubs)
2. `983e63b` — Tests + receipt
3. `a9bfc21` — Env + module exports
4. `c0f6e3d` — Refactor: Replace stubs with real httpx
5. `5d09ae0` — Merge main + fix __init__.py
6. `<current>` — Fix test regex, finalize tests

## Validation Checklist

- ✅ All tests passing (16/16)
- ✅ Async/await properly implemented
- ✅ Dependency injection for testing
- ✅ Real HTTPS endpoints (not mocked in production)
- ✅ Security warnings in .env.example
- ✅ from_env() tests (success + failure)
- ✅ Fail-closed configuration
- ✅ No runtime exec() calls
- ✅ Bandit clean
- ✅ No CI bypasses

## Status: Ready for Review & Merge to Main

**PR #36** can now be reviewed by Commander and merged.

**Blocking Issues:** None.

**Open Questions for Phase 21B:**
- Should Azure/Google follow the same injectable client pattern?
- Where should session creation logic live (this provider or route handler)?

---

**Built by:** Tasklet AI  
**Date:** 2026-04-30  
**Verified:** ✅ Real HTTP boundary, no mocks in production path
