# tests — Root-Level Test Suite

## Purpose

Owns the root-level test suite: scheduler tests and agent unit tests that validate core infrastructure behavior. Does *not* own portal tests (those live in `portal/tests/` and are governed by `portal/AGENTS.md`).

## Ownership

- Root-level test files: scheduler tests (`test_scheduler_core.py`, `test_scheduler_dispatcher.py`, `test_scheduler_executor.py`, `test_scheduler_queue.py`, `test_scheduler_recurring.py`, `test_scheduler_task_types.py`) and agent tests (`test_nova_agent.py`, `test_sigma_agent.py`, `test_zero_agent.py`)
- `tests/security/` subdirectory
- Does *not* own `portal/tests/`, `portal/sso/tests/`, or `portal/routers/tests/`

## Local Contracts

- Pytest-based (configured in `pytest.ini` and `pyproject.toml`)
- Each agent test file must test that agent's public API without calling real external services
- Scheduler tests must use in-memory or test-only backends (no production DB)
- Security tests must validate that no dangerous runtime exec patterns exist

## Work Guidance

*(No project-specific standards yet — fill when engineering conventions emerge.)*

## Verification

*(No verification framework documented yet — fill when test/coverage thresholds exist.)*

## Child DOX Index

*(None — all test files are leaf modules.)*
