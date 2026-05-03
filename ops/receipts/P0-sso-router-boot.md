# P0 SSO Router Boot Repair Receipt

## Branch

`fix/p0-sso-router-boot`

## Problem

Current `main` was boot-blocked by invalid SSO router syntax and import/runtime mismatches in `portal/main.py`.

Observed blockers:

- `portal/routers/sso.py` contained invalid Python: `@Hfrom_fastapi.default_corass`.
- `portal/main.py` imported local middleware/security/router modules that are not present in the repository:
  - `portal.middleware.session_middleware`
  - `portal.middleware.timestamp_middleware`
  - `portal.security.security_layer`
  - `portal.routers.webhooks`
- `portal/main.py` defined `lifespan()` but did not pass it to `FastAPI(...)`.
- `JWTTokenService` was initialized with a raw string even though it expects `SessionConfig`.
- `SessionConfig` was constructed with `session_timeout_seconds`, which does not exist.

## Changes Applied

- Rewrote `portal/main.py` to use only present boot-safe imports.
- Switched SSO session middleware to Starlette's `SessionMiddleware`.
- Added `lifespan=lifespan` to the FastAPI constructor.
- Added `build_session_config()` to construct `SessionConfig` with the correct fields.
- Initialized `JWTTokenService` with `SessionConfig`.
- Removed missing `webhooks`, `TimestampMiddleware`, and `SecurityLayer` imports from app startup wiring.
- Rewrote `portal/routers/sso.py` as an import-safe placeholder router with Okta/Azure/Google authorize routes plus health endpoint.

## Required Verification

Run locally or in CI:

```bash
python -m compileall portal
python -c "from portal.main import create_app; app = create_app(); print(app.title)"
pytest portal/tests/test_app_startup.py -q
pytest portal/sso portal/middleware -q
```

## Notes

This repair is intentionally surgical. It does not address the later Trust Compliance placeholder-policy regression or `/tmp/sp_task` path issue.
Those should be handled in a separate P1 PR.
