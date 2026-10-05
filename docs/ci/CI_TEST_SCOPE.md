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
- **Scheduler APScheduler trigger adapter repair** — Issue #164. Fixed: `scheduler/task_scheduler.py` now uses `DateTrigger(run_date=...)` for one-time datetime tasks instead of passing a raw `datetime` to APScheduler. The scheduler arming tests (`tests/test_scheduler_core.py -k arm`) pass when run directly. A bare `python -m pytest --tb=short -q` currently cannot be used as evidence they pass, because collection of the default lane is interrupted by unrelated pre-existing errors in other `tests/` files before any test executes; this is a pre-existing collection defect in the default lane, not a regression from this fix, and is out of scope for this document.

## Explicit test-file CI targets outside the default lane

Some test files are intentionally excluded from `testpaths` (in both `pytest.ini` and `pyproject.toml`) and are instead run by naming the file explicitly in a CI job step (`python -m pytest path/to/test_file.py ...`), bypassing directory-level discovery entirely. A bare `python -m pytest` run does not collect these files, so a passing default-lane run is not evidence that they pass or even exist. Current examples:

- `governance/tests/test_gov001a_fail_closed.py` — `gov-001a-regression` job
- `governance/tests/test_governance.py` (named assertions) — `gov-001a-regression` job
- `governance/tests/test_governance.py` (whole file), `security/tests/test_security.py`, `agent_protocol/tests/test_agent_protocol.py`, `trust_law/tests/test_trust_law.py` — `governance-security-regression` and `security-critical-regression` jobs

Each of these jobs measures its target's collection count with `scripts/ci/report_test_inventory.py` and asserts a minimum floor with `scripts/ci/assert_test_floor.py` before executing the suite, so an incomplete or collapsed collection fails the job even if pytest itself would otherwise exit 0 on zero collected tests.

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

Both files currently exist and currently diverge (for example, `pytest.ini`'s `testpaths` includes `decision/tests` and markers `postgresql`/`smoke` that `pyproject.toml` does not). Pytest uses only one ini-style config file, chosen by a fixed priority order, and does not merge them. Because `pytest.ini` is present, it is the file actually in effect; `pyproject.toml`'s `[tool.pytest.ini_options]` section is currently ignored. Confirmed empirically: `decision/tests` is collected by a bare `python -m pytest --collect-only`, which is only possible if `pytest.ini`'s `testpaths` is the one being read.
