# SSO Test Dependency Classification

Mission ID: SP-TKM-001
Report Date: 2026-07-27
Prepared by: Hermes

## Affected Test

```text
portal/routers/tests/test_sso_routes.py
```

## Status

**NOT EXECUTED**

## Reason

```text
ModuleNotFoundError: No module named 'itsdangerous'
```

The test file imports `starlette.middleware.sessions.SessionMiddleware`, which depends on `itsdangerous`. The dependency is not present in the current environment, so pytest cannot collect the module.

## Mission Attribution

```text
NO EVIDENCE THAT THE FAILURE WAS INTRODUCED BY SP-TKM-001
```

The SP-TKM-001 changes are confined to:

- `portal/config.py` — added `SP_TKM_001_PREVIEW_ENABLED` setting.
- `portal/main.py` — added conditional router registration.
- `portal/routers/sp_tkm_001.py` — new preview router.
- `portal/routers/tests/test_sp_tkm_001.py` — new tests for the preview router.

None of these files interact with `itsdangerous`, Starlette sessions, or SSO routes. The import failure predates SP-TKM-001 work.

## Allowed Outcomes

| Outcome | Status |
|---|---|
| DEPENDENCY INSTALLED AND TEST PASSED | Not yet done |
| DEPENDENCY ALREADY DECLARED BUT ENVIRONMENT INCOMPLETE | Under review |
| FORMALLY WAIVED AS OUT OF SCOPE | Possible |
| FAILURE ATTRIBUTED TO MISSION CHANGE | Not supported by evidence |

## Current Classification

```text
portal/routers/tests/test_sso_routes.py:
status: NOT EXECUTED
reason: missing itsdangerous dependency
mission attribution: no evidence that the failure was introduced by SP-TKM-001
```

## Follow-Up Task

TASK-027 — Resolve or formally waive unrelated SSO test dependency.

Allowed outcomes:

```text
DEPENDENCY INSTALLED AND TEST PASSED
DEPENDENCY ALREADY DECLARED BUT ENVIRONMENT INCOMPLETE
FORMALLY WAIVED AS OUT OF SCOPE
FAILURE ATTRIBUTED TO MISSION CHANGE
```

Do not install or alter dependencies unless permitted by repository governance.
