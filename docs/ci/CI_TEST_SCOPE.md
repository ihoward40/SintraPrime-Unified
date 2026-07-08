# CI Test Scope

This document defines the supported default CI test lane and the categories of tests that are intentionally excluded from it.

## Supported default lane

The default CI lane runs:

```bash
python -m pytest --tb=short -q
```

It includes tests from these directories:

- `tests/` — core scheduler and agent unit tests
- `portal/tests/` — portal backend tests

The default lane skips any test marked with `@pytest.mark.experimental`.

## Marker registry

| Marker | Meaning |
|--------|---------|
| `experimental` | Tests that exercise unfinished or unstable integrations. Not part of the default CI lane. |
| `integration` | Tests that require external services or infrastructure. Run explicitly with `-m integration`. |
| `slow` | Tests that take significantly longer than normal unit tests. |

## Currently re-scoped experimental tests

(None — the previously re-scoped scheduler arming tests were fixed and re-enabled by PR #164.)

## Deferred work

- **Dependency reconciliation between `pyproject.toml` and `requirements.txt`** — future packaging cleanup; not in scope for the default CI lane.
- **Optional integration activation** — each integration needs its own verified issue, env vars, and tests before it can be promoted to the supported lane.
- **Scheduler APScheduler trigger adapter repair** — Issue #164. Fixed: `scheduler/task_scheduler.py` now uses `DateTrigger(run_date=...)` for one-time datetime tasks instead of passing a raw `datetime` to APScheduler. The scheduler arming tests are verified in the default lane.

## Running the full suite

To run experimental tests explicitly:

```bash
python -m pytest --tb=short -q -m experimental
```

To run all tests including experimental:

```bash
python -m pytest --tb=short -q -m ""
```

## Source of configuration

- `pytest.ini`
- `pyproject.toml` (`[tool.pytest.ini_options]`)

Both files are kept in sync. If they diverge, the `pyproject.toml` section takes precedence.
