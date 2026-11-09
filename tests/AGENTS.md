# tests — Root-Level Test Suite

## Purpose

Owns the root-level test suite: scheduler tests, agent unit tests, and certification runner receipt tests that validate core infrastructure behavior. Does *not* own portal tests (those live in `portal/tests/` and are governed by `portal/AGENTS.md`).

## Ownership

- Root-level test files: scheduler tests (`test_scheduler_core.py`, `test_scheduler_dispatcher.py`, `test_scheduler_executor.py`, `test_scheduler_queue.py`, `test_scheduler_recurring.py`, `test_scheduler_task_types.py`) and agent tests (`test_nova_agent.py`, `test_sigma_agent.py`, `test_zero_agent.py`)
- `test_certify_runner.py`: receipt contract of `scripts/certify.py` (and its private helper `scripts/_certify_collect_plugin.py`)
- `tests/security/` subdirectory
- Does *not* own `portal/tests/`, `portal/sso/tests/`, or `portal/routers/tests/`

## Local Contracts

- Pytest-based (configured in `pytest.ini` and `pyproject.toml`)
- Each agent test file must test that agent's public API without calling real external services
- Scheduler tests must use in-memory or test-only backends (no production DB)
- Security tests must validate that no dangerous runtime exec patterns exist
- `test_certify_runner.py` points certify at a throwaway repo root under `tmp_path`: tiny real pytest collections and controlled subprocess faults only; never a real lane, service or DB, and nothing written in the repo. It pins: `COLLECTION PASS` means `executed_count` 0 and is never runtime certification; unknown evidence is `null`, not 0 or PASS; zero tests, a missing/empty configured path or an incomplete collection fail the gate; raw pytest return code is preserved (certify's own codes: 3 timeout, 6 evidence gate, 7 launch error); failure temp evidence is preserved; `TARGETS`/`LANE_ENV` fingerprints, 120s per-test and 1800s wall-clock caps and the network guard are unchanged

## Work Guidance

- Cover both quiet output and timed pytest summaries. Module-level skips, and skips/expected failures before or inside a body, must not create false zero counts or unsupported execution claims.

## Verification

- Runner and existing claims/inventory regressions: `python -m pytest tests/test_certify_runner.py scripts/ci/tests -q -p no:cacheprovider` (CI installs `pytest-timeout`; the runner fixtures stub `--timeout` flags only if the plugin is absent).
- Changed Python files: `python -m ruff check scripts/certify.py scripts/_certify_collect_plugin.py tests/test_certify_runner.py`.

## Child DOX Index

*(None — all test files are leaf modules.)*
