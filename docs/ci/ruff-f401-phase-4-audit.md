# Ruff F401 Phase 4 Audit — Fixture and Framework Imports

**Status:** Audit only — no import removals, no pyproject.toml changes, no workflow changes.

**Branch:** `docs/ruff-f401-phase-4-audit`
**Deliverable:** `docs/ci/ruff-f401-phase-4-audit.md`
**Audit command:** `ruff check portal tests --select F401 --isolated --output-format=concise`
**Base:** PR #112 merge commit (`7fc4841`)

---

## Executive Summary

Running the isolated F401 audit against `portal/` and `tests/` reveals **36 violations across
11 files**. Violations split cleanly into four categories with very different risk profiles.
The only safe auto-fixable subset for PR #111 execution is the **test fixture / mock import
category** — 26 violations in 8 test files where ruff can auto-remove confirmed-unused imports
with zero side-effect risk.

The remaining 10 violations require manual review or deliberate `# noqa` suppression and are
**not in scope for PR #111**.

---

## Audit Command

```bash
ruff check portal tests --select F401 --isolated --output-format=concise
```

`--isolated` bypasses `pyproject.toml` per-file-ignores so that actively-suppressed violations
are visible. This is a read-only diagnostic — it does not modify any file.

---

## Full Violation List (36 total)

### Group A — Auto-fixable test fixture/mock imports [26 violations, 8 files]

> `[*]` marker = ruff confirms auto-fixable. All are in `tests/` (not `portal/`).
> All are genuine unused imports — confirmed by cross-referencing usage in each file.
> No side-effect risk: none are `__init__` re-exports, framework hooks, or conditional imports.

| File | Line | Import | Risk |
|------|------|--------|------|
| `tests/test_nova_agent.py` | 5 | `unittest.mock.patch` | ✅ Unused mock, safe |
| `tests/test_nova_agent.py` | 13 | `agents.nova.action_registry.ActionCategory` | ✅ Unused fixture, safe |
| `tests/test_nova_agent.py` | 16 | `agents.nova.action_registry.ActionValidationError` | ✅ Unused fixture, safe |
| `tests/test_nova_agent.py` | 22 | `agents.nova.action_registry.ApprovalLevel` | ✅ Unused fixture, safe |
| `tests/test_nova_agent.py` | 25 | `agents.nova.approval_gateway.AUTO_APPROVE_ACTIONS` | ✅ Unused fixture, safe |
| `tests/test_nova_agent.py` | 26 | `agents.nova.approval_gateway.LEGAL_REVIEW_ACTIONS` | ✅ Unused fixture, safe |
| `tests/test_nova_agent.py` | 28 | `agents.nova.approval_gateway.ApprovalRequest` | ✅ Unused fixture, safe |
| `tests/test_nova_agent.py` | 37 | `agents.nova.execution_ledger.LedgerIntegrityError` | ✅ Unused fixture, safe |
| `tests/test_nova_agent.py` | 40 | `agents.nova.nova_agent.ActionSpec` | ✅ Unused fixture, safe |
| `tests/test_nova_agent.py` | 42 | `agents.nova.nova_agent.ApprovalLevel` | ✅ Unused fixture, safe |
| `tests/test_nova_agent.py` | 43 | `agents.nova.nova_agent.ExecutionRecord` | ✅ Unused fixture, safe |
| `tests/test_sigma_agent.py` | 6 | `unittest.mock.MagicMock` | ✅ Unused mock, safe |
| `tests/test_sigma_agent.py` | 6 | `unittest.mock.PropertyMock` | ✅ Unused mock, safe |
| `tests/test_sigma_agent.py` | 6 | `unittest.mock.patch` | ✅ Unused mock, safe |
| `tests/test_sigma_agent.py` | 19 | `agents.sigma.sigma_agent.GateReport` | ✅ Unused fixture, safe |
| `tests/test_zero_agent.py` | 9 | `unittest.mock.patch` | ✅ Unused mock, safe |
| `tests/test_zero_agent.py` | 16 | `agents.zero.health_monitor.Alert` | ✅ Unused fixture, safe |
| `tests/test_zero_agent.py` | 21 | `agents.zero.zero_agent.COMMON_IMPORT_FIXES` | ✅ Unused fixture, safe |
| `tests/test_zero_agent.py` | 22 | `agents.zero.zero_agent.HealthReport` | ✅ Unused fixture, safe |
| `tests/test_zero_agent.py` | 23 | `agents.zero.zero_agent.ImportError_` | ✅ Unused fixture, safe |
| `tests/test_scheduler_core.py` | 18 | `scheduler.task_types.TaskResult` | ✅ Unused fixture, safe |
| `tests/test_scheduler_dispatcher.py` | 13 | `scheduler.task_types.Schedule` | ✅ Unused fixture, safe |
| `tests/test_scheduler_executor.py` | 15 | `scheduler.task_types.TaskResult` | ✅ Unused fixture, safe |
| `tests/test_scheduler_recurring.py` | 20 | `scheduler.task_types.TaskStatus` | ✅ Unused fixture, safe |
| `tests/test_scheduler_recurring.py` | 144 | `scheduler.task_scheduler.TaskScheduler` | ✅ Unused fixture, safe |
| `tests/test_scheduler_task_types.py` | 11 | `pytest` | ✅ Unused pytest import, safe |

**Execution command for PR #111:**
```bash
ruff check tests --select F401 --isolated --fix
```

---

### Group B — `portal/routers/__init__.py` re-exports [4 violations, 1 file]

> Not auto-fixable. Not in scope for PR #111.

| File | Line | Import | Risk |
|------|------|--------|------|
| `portal/routers/__init__.py` | 2 | `.auth` | ⚠️ Package re-export — may be used by FastAPI router registration |
| `portal/routers/__init__.py` | 2 | `.billing` | ⚠️ Package re-export — may be used by FastAPI router registration |
| `portal/routers/__init__.py` | 2 | `.cases` | ⚠️ Package re-export — may be used by FastAPI router registration |
| `portal/routers/__init__.py` | 2 | `.documents` | ⚠️ Package re-export — may be used by FastAPI router registration |

**Explanation:** `from . import auth, billing, cases, documents` in `__init__.py` is a common
FastAPI pattern for side-effect registration — importing the submodule causes the router objects
inside it to be constructed and registered. Ruff flags it as unused because none of `auth`,
`billing`, `cases`, or `documents` are explicitly referenced by name after the import. However,
removing them could silently drop route registration.

**Required before fixing:** Trace where `portal.routers` is imported in `portal/main.py` or the
app factory and verify whether the submodule import is relied upon for registration side-effects
or whether routes are explicitly `include_router`-ed elsewhere.

**Resolution path:** Add to `__all__` or add `# noqa: F401  # re-export for FastAPI registration`
comment. Either approach is manual — not auto-fixable.

---

### Group C — `portal/services/document_processor.py` inline import [1 violation, 1 file]

> Not auto-fixable. Not in scope for PR #111.

| File | Line | Import | Risk |
|------|------|--------|------|
| `portal/services/document_processor.py` | 64 | `pytesseract` | ⚠️ Intentional lazy/optional import |

**Explanation:** The import is inside a `try/except ImportError` block:
```python
async def _run_ocr(...):
    try:
        import pytesseract  # type: ignore
        # ... OCR logic ...
    except ImportError:
        log.warning("ocr.unavailable", ...)
```
This is a deliberate optional-dependency pattern — the import is not unused, it is the
availability probe. Ruff cannot detect the side-effect intent and flags it as unused because
`pytesseract` is not referenced after the import statement.

**Resolution path:** Add `# noqa: F401  # optional OCR dependency — availability probe` comment.
One-line manual fix, appropriate for a future cleanup PR or inline at review time.

---

### Group D — `portal/tests/test_app_startup.py` smoke-test imports [5 violations, 1 file]

> Not auto-fixable. Not in scope for PR #111.

| File | Lines | Imports | Risk |
|------|-------|---------|------|
| `portal/tests/test_app_startup.py` | 25–29 | `get_settings`, `create_app`, `CORSMiddleware`, `JWTTokenService`, `SessionManager` | ⚠️ Intentional import-presence test |

**Explanation:** The top-level imports in this file (`lines 25–29`) are used by `test_settings_loads()`
and `test_app_creation()` — but the same names are *re-imported* inside `test_no_import_errors()`
(lines 22–29). The top-level imports appear unused because the test body uses the inner-scope
re-imports. However, removing the top-level imports would change the file's behavior — any import
error in those modules would be raised at collection time rather than caught by the `try/except`
inside `test_no_import_errors()`, changing the test semantics.

**Ruff's suggestion** (`importlib.util.find_spec`) is technically correct but requires rewriting
the smoke test. This is design-level work, not a linting fix.

**Resolution path:** Rewrite `test_no_import_errors()` to use `importlib.util.find_spec`, or
remove the duplicate top-level imports and accept earlier-failure behavior. Either is manual and
requires intentional design decision.

---

## Violation Summary

| Group | Files | Count | Auto-fixable | Scope |
|-------|-------|-------|-------------|-------|
| A — Test fixture/mock imports | 8 | 26 | ✅ Yes (`[*]`) | ✅ PR #111 |
| B — Router `__init__` re-exports | 1 | 4 | ❌ No | ❌ Out of scope |
| C — Lazy optional import | 1 | 1 | ❌ No | ❌ Out of scope |
| D — Smoke-test duplicate imports | 1 | 5 | ❌ No | ❌ Out of scope |
| **Total** | **11** | **36** | **26** | **26** |

---

## PR #111 Execution Scope

### What

Remove 26 confirmed-unused test fixture and mock imports from `tests/` using ruff auto-fix.

### What NOT included

- Group B (`portal/routers/__init__.py`) — needs manual re-export decision
- Group C (`portal/services/document_processor.py`) — needs `# noqa` comment, not removal
- Group D (`portal/tests/test_app_startup.py`) — needs design decision on smoke-test structure
- No `pyproject.toml` changes
- No per-file-ignore removal (F401 still suppressed in per-file-ignores; removal is a separate PR)
- No excluded directories
- No CI/workflow changes
- No Bandit changes
- No Sigma threshold changes

### Exact command

```bash
ruff check tests --select F401 --isolated --fix
```

Scoped to `tests/` only. Does not touch `portal/`. `--isolated` bypasses per-file-ignores so
the fix is applied even though F401 is suppressed in `tests/**`.

### Expected outcome

- 26 violations removed from 8 test files
- `ruff check tests --select F401 --isolated` → 0 violations in `tests/`
- `ruff check portal --select F401 --isolated` → 10 violations remain (Groups B, C, D — unchanged)
- `ruff check . --output-format=concise` (normal config) → 0 violations (baseline unchanged)
- `pytest tests/` → all tests pass (removals are confirmed-unused, no behavior change)

### Files changed (expected)

| File | Violations removed |
|------|--------------------|
| `tests/test_nova_agent.py` | 11 |
| `tests/test_zero_agent.py` | 5 |
| `tests/test_sigma_agent.py` | 4 |
| `tests/test_scheduler_recurring.py` | 2 |
| `tests/test_scheduler_core.py` | 1 |
| `tests/test_scheduler_dispatcher.py` | 1 |
| `tests/test_scheduler_executor.py` | 1 |
| `tests/test_scheduler_task_types.py` | 1 |
| **Total** | **26** |

### Verification plan

1. `ruff check tests --select F401 --isolated` → 0 violations in `tests/`
2. `ruff check portal --select F401 --isolated` → 10 violations remain (no regressions)
3. `ruff check . --output-format=concise` → 0 violations (normal config baseline clean)
4. `pytest tests/ -q` → all tests pass, exit 0
5. `git diff --stat` → exactly 8 files changed in `tests/`, no other files

### Rollback plan

1. Revert the commit for PR #111
2. `ruff check . --output-format=concise` re-verified → 0 (per-file-ignores still suppress F401)
3. No CI impact — F401 was already suppressed in `tests/**` per-file-ignores; rollback is clean

---

## What Stays Suppressed After PR #111

After PR #111, `tests/**` still has F401 in per-file-ignores. The 10 remaining `portal/`
violations (Groups B, C, D) are also still suppressed by `portal/routers/**`,
`portal/services/**`, and `portal/tests/**` entries. Removing those suppressions is a future PR
once the manual resolutions above are applied.

---

## Deferred Work (Not PR #111)

| Item | File | Resolution |
|------|------|-----------|
| Router re-export clarification | `portal/routers/__init__.py` | Add `__all__` or `# noqa` comment after tracing app factory |
| OCR optional import | `portal/services/document_processor.py` | Add `# noqa: F401` comment |
| Smoke-test design | `portal/tests/test_app_startup.py` | Rewrite with `importlib.util.find_spec` or remove duplicate imports |
| Remove `tests/**` F401 suppression | `pyproject.toml` | After Group A fixes land — separate PR |
| Remove `portal/**` F401 suppressions | `pyproject.toml` | After Groups B/C/D resolved — separate PR |
