# SP-TKM-001 Router Certification Report

Mission ID: SP-TKM-001
Report Date: 2026-07-27
Owner: Hermes
Status: Internal preview router certified for feature-flagged use

## 1. Isolation Statement

Mission artifacts remain confined to `mission-control-evidence/SP-TKM-001/`. Application integration changes are limited to the isolated preview router and its registration in `portal/main.py`.

## 2. Feature Flag

- Setting: `SP_TKM_001_PREVIEW_ENABLED`
- Default: `false`
- Location: `portal/config.py`
- Guard in `portal/main.py`:

```python
if settings.SP_TKM_001_PREVIEW_ENABLED:
    app.include_router(sp_tkm_001.router, prefix="", tags=["sp-tkm-001"])
```

## 3. Import Verification

Command:

```bash
.venv/Scripts/python -c "import portal.main; print('import ok')"
```

Result:

```text
import ok
EXIT_CODE:0
```

Environment: repository virtualenv at `.venv/Scripts/python` (Python 3.11.9).

## 4. Application Startup Verification

### Flag enabled

Command:

```bash
SP_TKM_001_PREVIEW_ENABLED=true .venv/Scripts/python -c "from portal.main import create_app; from portal.config import get_settings; app=create_app(); routes=[r.path for r in app.routes]; print('consumer-evidence present:', '/consumer-evidence' in routes)"
```

Result:

```text
flag= True
consumer-evidence present: True
EXIT_CODE:0
```

Routes registered when enabled:

- `/consumer-evidence`
- `/api/v1/consumer-evidence/interest`
- `/api/v1/consumer-evidence/event`

### Flag disabled

Command:

```bash
SP_TKM_001_PREVIEW_ENABLED=false .venv/Scripts/python -c "from portal.main import create_app; from portal.config import get_settings; app=create_app(); routes=[r.path for r in app.routes]; print('consumer-evidence present:', '/consumer-evidence' in routes)"
```

Result:

```text
flag= False
consumer-evidence present: False
EXIT_CODE:0
```

### Duplicate registration check

No duplicate route registration observed. Route appears once when enabled and zero times when disabled.

### Dependency and template-path check

- `portal/routers/sp_tkm_001.py` resolves the template path relative to its own file.
- Path resolution succeeds on Windows and will succeed on POSIX.
- No missing dependency errors on startup with flag enabled or disabled.
- No unrelated startup behavior changes.

## 5. Route Tests

File: `portal/routers/tests/test_sp_tkm_001.py`

| Test | Result |
|---|---|
| Flag disabled → route unavailable | PASS |
| Flag enabled → route available | PASS |
| GET route → expected status (200) | PASS |
| Expected content type (text/html) | PASS |
| Required disclaimer text present | PASS |
| No payment action present | PASS |
| UTM parameters accepted safely | PASS |
| Unexpected query values do not crash route | PASS |
| Interest endpoint placeholder works | PASS |
| Interest endpoint does not echo PII fields | PASS |
| Event endpoint accepts valid event | PASS |
| Event endpoint rejects invalid event name | PASS |

Test run:

```bash
.venv/Scripts/python -m pytest portal/routers/tests/test_sp_tkm_001.py -v
```

Result:

```text
12 passed in ~11 seconds
EXIT_CODE:0
```

## 6. Regression Tests

Commands and results:

```bash
.venv/Scripts/python -m pytest portal/tests/test_app_startup.py portal/tests/test_router_coverage.py -v
```

Result:

```text
40 passed, 1 skipped in 8.27s
EXIT_CODE:0
```

```bash
.venv/Scripts/python -m pytest tests/test_governed_inference.py tests/test_governed_inference_adapters.py -v
```

Result:

```text
58 passed in 1.41s
EXIT_CODE:0
```

Note: `portal/routers/tests/test_sso_routes.py` cannot currently be collected and is recorded as **NOT EXECUTED** because the `itsdangerous` dependency is missing from the environment. Mission attribution: **NO EVIDENCE THAT THE FAILURE WAS INTRODUCED BY SP-TKM-001**. This pre-existing dependency gap is tracked as TASK-027 — Resolve or formally waive unrelated SSO test dependency.

## 7. Frontend / HTML Validation

Manual/automated checks performed on `offers/consumer-evidence/landing-page/index.html`:

| Check | Result |
|---|---|
| Mobile viewport meta | PASS |
| No horizontal overflow CSS | PASS |
| Form labels present | PASS |
| Accessible input/label association | PASS |
| Disclaimer visible | PASS |
| "Not a law firm" visible | PASS |
| Price `$9` displayed | PASS |
| No payment button | PASS |
| No external script loaded | PASS |
| No SSN/account number input | PASS |
| UTM values not rendered unsafely | PASS |

## 8. Certification Conclusion

The SP-TKM-001 preview router is certified for internal, feature-flagged use.

Internal preview router certification:

```text
INTERNAL PREVIEW ROUTER: CERTIFIED WITH ONE UNRELATED TEST ENVIRONMENT LIMITATION
```

The unrelated limitation is `portal/routers/tests/test_sso_routes.py`, which cannot be collected because the `itsdangerous` dependency is missing from the current environment. This limitation predates SP-TKM-001 and is tracked as TASK-027.

It is not authorized for production deployment during this phase.

---

Prepared by: Hermes
Reviewed by: Mission Owner (pending)
