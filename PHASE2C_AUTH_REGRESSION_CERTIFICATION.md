# Phase 2C — Category B Auth Regression Certification

**Date:** 2026-08-10  
**Branch:** `feat/phase-3c-command-authority`  
**Head commit:** `4eff47f9ea3284fcbd7f20fdfe9d843e3bcc3c01`  
**Certifying agent:** Copilot Task Agent (CI-BASELINE-RECOVERY Phase 2C)

---

## Completion Gate

| Gate | Status |
|---|---|
| CATEGORY A | ✅ PASS |
| CATEGORY B | ✅ PASS |
| CATEGORY C | ✅ PASS |
| SHARED SUITE | ✅ PASS |
| AUTHORIZATION BOUNDARY | ✅ PRESERVED |
| CATEGORY D | ✅ UNTOUCHED |
| R3 | ✅ UNTOUCHED |

---

## 1. Failing Tests (Reproduced)

The following two Category B tests failed in CI run `31340152941` on branch
`feat/sp-voice-002-federated-speech-runtime` at commit `2f9f26b4`:

```
FAILED tests/test_legal_authority_phase_two_b.py::test_phase_2b_api_new_states_comparison_and_ucc_endpoints
       assert 401 == 200  (GET /jurisdictions/{code})

FAILED tests/test_legal_authority_phase_two_c_one.py::test_federal_read_only_api_endpoints
       assert 401 == 200  (GET /federal/domains, /federal/rules, etc.)
```

---

## 2. Route Dependency Chain

**Endpoints under test (read-only):**
- `GET /federal/domains`
- `GET /federal/rules`
- `GET /federal/rules/{rule_id}`
- `GET /federal/authorities`
- `GET /federal/conflicts`
- `GET /jurisdictions/{code}`
- `GET /jurisdictions/{code}/rules`
- `GET /legal-rules/compare`

**Router:** `portal/routers/jurisdictions.py` — registered in `portal/main.py` via
`app.include_router(jurisdictions.router)` with no prefix and no auth dependency.

**Auth on read endpoints:** None. The router uses `_authorized_actor()` only on
write/mutating operations (`POST /ucc-filings/evaluate`, `POST /legal-rules/{id}/reviews`,
`POST /legal-rules/{id}/challenges`, `POST /legal-rules/{id}/submit-review`,
`POST /legal-authorities/{id}/refresh-metadata`, `GET /jurisdictions/{code}/review-queue`).

---

## 3. Root Cause — CODE_DEFECT

**Classification: CODE_DEFECT** (not a stale test)

At commit `2f9f26b4` on branch `feat/sp-voice-002-federated-speech-runtime`,
`portal/main.py` contained:

```python
from portal.middleware.auth_middleware import AuthMiddleware
...
app.add_middleware(AuthMiddleware)
```

`portal/middleware/auth_middleware.py` at that commit defined `PUBLIC_EXACT_PATHS`
covering only auth/SSO/health paths (`/api/v1/auth/*`, `/api/v1/sso/*`, `/health`,
`/docs`, `/openapi.json`). The read-only legal authority routes (`/federal/*`,
`/jurisdictions/*`) were **not** included in the public path allowlist.

As a result, every unauthenticated request to those endpoints was rejected with
`401 Unauthorized` by the middleware before reaching the route handler.

The tests were correct: read-only legal authority endpoints are a public reference
data contract — they have never required a session token.

---

## 4. Resolution

On the current branch (`4eff47f9`), `AuthMiddleware` is **not registered** in
`create_app()`. The `portal/main.py` middleware stack contains only:

- `CORSMiddleware`
- `SessionMiddleware`
- `RateLimiterMiddleware`
- `TimestampMiddleware`
- `CorrelationMiddleware`

No global JWT enforcement middleware is present. Write endpoints in the
jurisdictions router are protected by application-level `_authorized_actor()`
checks that require `X-Reviewer-Role` and `X-Reviewer-Identity` request headers.

No code change was required on the current branch — the regression does not exist here.

---

## 5. Authorization Boundary Verification

Verified by direct test client probe at head commit `4eff47f9`:

| Endpoint | Method | Auth required | Observed |
|---|---|---|---|
| `/federal/domains` | GET | No | 200 ✅ |
| `/jurisdictions/NY` | GET | No | 200 ✅ |
| `/ucc-filings/evaluate` | POST | Yes (reviewer headers) | 403 without headers ✅ |
| `/legal-rules/{id}/submit-review` | POST | Yes (reviewer headers) | 403 without headers ✅ |
| `/legal-rules/{id}/reviews` | POST | Yes (reviewer headers) | 403 without headers ✅ |

No write endpoint was weakened. No new public endpoint was created. Auth contract
is identical to the pre-regression baseline.

---

## 6. Test Results

### Category B (the two failing tests)
```
tests/test_legal_authority_phase_two_b.py::test_phase_2b_api_new_states_comparison_and_ucc_endpoints  PASSED
tests/test_legal_authority_phase_two_c_one.py::test_federal_read_only_api_endpoints                   PASSED
```
2 passed, 0 failed.

### Category A (legal authority suite)
```
tests/test_legal_authority_phase_one.py        ✅ PASS
tests/test_legal_authority_phase_two_a.py      ✅ PASS
tests/test_legal_authority_phase_two_b.py      ✅ PASS
tests/test_legal_authority_phase_two_c_one.py  ✅ PASS
```
44 passed, 0 failed.

### Category C (certification gates)
```
portal/tests/test_auth_tenant_rbac_certification.py              ✅ PASS
portal/tests/test_audit_correlation_non_http_certification.py    ✅ PASS
portal/tests/test_http_correlation_ws_hardening_certification.py ✅ PASS
```
189 passed, 0 failed.

### Shared Suite (full pytest run)
All tests collected under `pytest.ini` testpaths (`tests/`, `portal/tests/`,
`voice_concierge/governed/tests/`): **all passed, 0 failed**.

---

## 7. Category D / R3 Confirmation

- `portal/tests/test_postgresql_bootstrap_schema_authority.py` — **not touched**
- Alembic migration files — **not touched**
- `portal/alembic/` — **not touched**
- R3 schema migration gate — **not touched**

---

## 8. Evidence References

| Item | Value |
|---|---|
| Failing CI run | `31340152941` |
| Failing branch | `feat/sp-voice-002-federated-speech-runtime` |
| Failing commit | `2f9f26b4` |
| Offending change | `app.add_middleware(AuthMiddleware)` in `portal/main.py` |
| Missing path coverage | `/federal/*`, `/jurisdictions/*` not in `PUBLIC_EXACT_PATHS` |
| Current head | `4eff47f9` — `AuthMiddleware` not registered |
| Auth boundary probe | write=403, read=200 ✅ |
