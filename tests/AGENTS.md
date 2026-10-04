# tests — Root-Level Test Suite

## Purpose

Owns the root-level pytest suite for core infrastructure and domain packages that do not have a closer test boundary. Does *not* own portal tests (those live in `portal/tests/` and are governed by `portal/AGENTS.md`).

## Ownership

- Root-level scheduler tests (`test_scheduler_core.py`, `test_scheduler_dispatcher.py`, `test_scheduler_executor.py`, `test_scheduler_queue.py`, `test_scheduler_recurring.py`, `test_scheduler_task_types.py`).
- Root-level agent tests (`test_nova_agent.py`, `test_sigma_agent.py`, `test_zero_agent.py`).
- Root-level legal-authority and other domain-package tests when the owning package does not contain its own test subtree.
- `tests/security/` subdirectory.
- Does *not* own `portal/tests/`, `portal/sso/tests/`, or `portal/routers/tests/`.

## Local Contracts

- Pytest-based (configured in `pytest.ini` and `pyproject.toml`).
- Each agent test file must test that agent's public API without calling real external services.
- Scheduler tests must use in-memory or test-only backends (no production DB).
- Security tests must validate that no dangerous runtime exec patterns exist.
- Legal-authority benchmark tests must be deterministic, offline, fail-closed, and must not treat benchmark assertions as verified law.

## Work Guidance

- Prefer focused tests that assert public contracts and failure behavior.
- High-risk legal-action cases must assert containment or human-review routing, not operational execution.

## Verification

- Run the focused test file first, then the existing legal-authority suite when legal-authority contracts change.

## Child DOX Index

*(None — all test files are leaf modules.)*
