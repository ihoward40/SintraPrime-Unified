# Dependency Matrix

This document reconciles the declared dependencies in SintraPrime-Unified.

## Source of truth status

- **`pyproject.toml` is the intended package metadata source** for the project.
- **`requirements.txt` is the current operational install source** for verified local commands, CI workflows, and Docker builds.
- The two files are now synchronized: `requirements.txt` contains the flattened runtime + test dependencies matching `pyproject.toml` core + `dev`/`test` optional extras.
- To regenerate from `pyproject.toml` in the future:
  ```bash
  pip install pip-tools
  pip-compile pyproject.toml -o requirements.txt
  ```
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
|| Logging/metrics | python-json-logger, prometheus-client, structlog |
|| Scheduler | apscheduler |
|| Test/quality (installed from requirements.txt) | pytest, pytest-asyncio, pytest-cov, black, ruff, mypy, bandit, safety |

## CI lint and security pins

The required `ruff` version for the default lint gate is:

- **ruff==0.15.20**

CI (`ci.yml` and `sigma-gate.yml`) installs `ruff==0.15.20` explicitly. `requirements-py313-windows.txt` matches this pin. `pyproject.toml` `[project.optional-dependencies] dev` also declares `ruff>=0.15.20`.

Security scanning uses `safety` and `bandit`, installed separately in the security CI job.

## Optional integration groups

These groups are documented but **not installed or tested in the default supported CI lane** unless explicitly installed and tested:

| Group | File | Packages | Status |
|---|---|---|---|
| portal | `pyproject.toml` `[project.optional-dependencies] portal` | PyJWT, requests, email-validator | Present in core `requirements.txt` and `pyproject.toml`; not a separate install target today. |
| predictive | `pyproject.toml` | pandas, scikit-learn | Not installed by default. |
|| integrations | `pyproject.toml` | plaid-python | `aiohttp` has been promoted to the core supported lane; `plaid-python` is not wired or tested in the default lane. |
|| all | `pyproject.toml` | Union of the above | Not used by CI. |

## Deferred work

- **Dependency reconciliation between `pyproject.toml` and `requirements.txt`** — completed. Both files now reflect the same core runtime and test dependencies.
- **Optional integration activation** — each integration needs its own verified issue, env vars, and tests before it can be promoted to the supported lane.
- **Scheduler APScheduler trigger adapter repair** — Issue #164. Fixed: `scheduler/task_scheduler.py` now uses `DateTrigger(run_date=...)` for one-time datetime tasks instead of passing a raw `datetime` to APScheduler. The scheduler arming tests are verified in the default lane.

## Verified commands

```bash
# Python supported test lane (operational install source)
pip install -r requirements.txt
python -m pytest --tb=short -q

# Alternative package install (metadata source)
pip install -e ".[dev,test]"
python -m pytest --tb=short -q

# Web verification
cd web && npm install
cd web && npm run lint
cd web && npm run type-check
cd web && npm run build
```
