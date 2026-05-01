# Receipt: PHASE-21A Azure + Google SSO Providers

**Agent:** Manus AI
**Branch:** `manus/PHASE-21A-azure-google`
**Base:** `agent/tasklet/PHASE-21A-okta` (PR #36 head — `a9bfc21`)
**Date:** 2026-04-30
**Status:** Ready for review (PR #40)

---

## Context

PR #39 (`manus/PHASE-21A-providers`) was closed per Commander Option A resolution — it contained a duplicate Okta implementation that conflicted with Tasklet's PR #36. This PR extracts only the Azure and Google providers from that work, rebased cleanly on top of Tasklet's Okta foundation.

---

## Files Added

| File | Lines | Purpose |
|---|---|---|
| `portal/sso/providers/azure.py` | 191 | Azure AD OIDC provider (PKCE, JWKS validation) |
| `portal/sso/providers/google.py` | 107 | Google Workspace OIDC provider (hosted domain enforcement) |
| `portal/sso/tests/test_azure.py` | 393 | 27 unit tests for Azure provider |
| `portal/sso/tests/test_google.py` | 378 | 35 unit tests for Google provider |

**Total: 62 tests, 1,069 lines added. No Okta files touched.**

---

## Verification Results

| Check | Result | Evidence |
|---|---|---|
| Azure tests | 27/27 ✅ | `pytest portal/sso/tests/test_azure.py` |
| Google tests | 35/35 ✅ | `pytest portal/sso/tests/test_google.py` |
| Bandit (azure.py) | 0 issues ✅ | `bandit portal/sso/providers/azure.py -ll` |
| Bandit (google.py) | 0 issues ✅ | `bandit portal/sso/providers/google.py -ll` (B105 false-positive suppressed with `# nosec` — public OAuth2 endpoint URL, not a password) |

---

## Security Notes

**Azure provider:** PKCE enforced on all authorization requests; JWKS-based token validation using `PyJWKClient`; `timeout=10` on all HTTP calls (bandit B113 clean); tenant ID validated at config init.

**Google provider:** Hosted domain enforcement via `hd` claim validation; JWKS-based token validation; `timeout=10` on all HTTP calls; `# nosec B105` on `self.token_url` — bandit incorrectly flags the string `"https://oauth2.googleapis.com/token"` as a hardcoded password because the variable is named `token_url`. This is a well-known false positive for OAuth2 endpoint constants.

---

## Collision Avoidance

This PR deliberately excludes:
- `portal/sso/providers/okta.py` — owned by Tasklet (PR #36)
- `portal/sso/__init__.py` — owned by Tasklet (PR #36)
- `.env.example` — owned by Tasklet (PR #36)
- `portal/sso/tests/test_okta.py` — owned by Tasklet (PR #36)

---

## Merge Sequence

```
PR #36 (Tasklet — Okta)  →  merge first
  ↓
PR #40 (Manus — Azure + Google)  →  merge after #36
```
