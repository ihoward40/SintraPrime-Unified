# Dependency Matrix

This document reconciles the declared dependencies in SintraPrime-Unified.

## Source of truth status

- **`requirements.txt` is the current operational install source** for verified local commands and CI workflows.
- **`pyproject.toml` remains the intended package metadata source** for a future clean packaging install (`pip install -e .[...]`). It should be reconciled with `requirements.txt` in a later packaging cleanup issue, not in the default supported CI lane.
- **`requirements-py313-windows.txt`** is a pinned Windows-specific export. It has been updated to pin `ruff==0.15.20` to match the CI lint gate.

## Core / default supported lane

These dependencies are installed by `pip install -r requirements.txt` and exercised by `python -m pytest --tb=short -q`:

| Category | Key packages |
|---|---|
| Web framework | fastapi, uvicorn[standard], gunicorn, starlette |
| Data validation | pydantic, pydantic-settings |
| Database | sqlalchemy, psycopg2-binary, asyncpg, alembic |
| Auth/security | python-jose[cryptography], passlib[bcrypt], bcrypt, PyJWT, pyotp, qrcode |
| HTTP clients | httpx, requests, aiohttp |
| Async/cache/jobs | aioredis, celery, redis |
| Payments | stripe |
| LLM APIs | openai, anthropic |
| Config/utilities | python-dotenv, pyyaml, click, typer, rich, python-dateutil, pytz, tzlocal |
| Logging/metrics | python-json-logger, prometheus-client, structlog |
| Test/quality (installed from requirements.txt) | pytest, pytest-asyncio, pytest-cov, black, ruff, mypy |

## CI lint pin

The required `ruff` version for the default lint gate is:

- **ruff==0.15.20**

CI (`ci.yml` and `sigma-gate.yml`) installs `ruff==0.15.20` explicitly. `requirements-py313-windows.txt` now matches this pin. `requirements.txt` does not pin `ruff` because it is installed separately by CI; future reconciliation may add the pin.

## Optional integration groups

These groups are documented but **not installed or tested in the default supported CI lane** unless explicitly installed and tested:

| Group | File | Packages | Status |
|---|---|---|---|
| portal | `pyproject.toml` `[project.optional-dependencies] portal` | PyJWT, requests, email-validator | Partially present in `requirements.txt`; not a separate install target today. |
| predictive | `pyproject.toml` | pandas, scikit-learn | Not installed by default. |
| integrations | `pyproject.toml` | aiohttp, plaid-python | `aiohttp` is present in `requirements.txt`; Plaid integration is not wired or tested in the default lane. |
| all | `pyproject.toml` | Union of the above | Not used by CI. |

## Deferred work

- **Dependency reconciliation between `pyproject.toml` and `requirements.txt`** — future packaging cleanup; not in scope for the default CI lane.
- **Optional integration activation** — each integration needs its own verified issue, env vars, and tests before it can be promoted to the supported lane.
- **Scheduler APScheduler trigger adapter repair** — Issue #164. Fixed: `scheduler/task_scheduler.py` now uses `DateTrigger(run_date=...)` for one-time datetime tasks instead of passing a raw `datetime` to APScheduler. The scheduler arming tests are verified in the default lane.

## Verified commands

```bash
pip install -r requirements.txt
python -m pytest --tb=short -q
cd web && npm install
cd web && npm run lint
cd web && npm run type-check
cd web && npm run build
```
