# Ruff F401 Cleanup Ladder — Phase 4 Audit (Post-PR #112)

**Status:** Planning/audit only — no import removals in this PR.

**Baseline plan:** `docs/ci/ruff-f401-cleanup-plan.md`  
**Audit command:**

```bash
ruff check portal tests --select F401 --isolated --output-format=concise
```

## 1) Current remaining F401 count after PR #112

- Command output reports `Found 41 errors`, which includes **5 pre-existing `invalid-syntax` parser diagnostics** in `portal/middleware.py`.
- **Current remaining F401 count (active dirs audited): 36**

## 2) File-by-file remaining violations

| File | Remaining F401 |
|---|---:|
| `portal/routers/__init__.py` | 4 |
| `portal/services/document_processor.py` | 1 |
| `portal/tests/test_app_startup.py` | 5 |
| `tests/test_nova_agent.py` | 11 |
| `tests/test_scheduler_core.py` | 1 |
| `tests/test_scheduler_dispatcher.py` | 1 |
| `tests/test_scheduler_executor.py` | 1 |
| `tests/test_scheduler_recurring.py` | 2 |
| `tests/test_scheduler_task_types.py` | 1 |
| `tests/test_sigma_agent.py` | 4 |
| `tests/test_zero_agent.py` | 5 |
| **Total** | **36** |

## 3) Classification of each remaining import

| File:Line | Import | Classification |
|---|---|---|
| `portal/routers/__init__.py:2` | `.auth` | keep/export surface |
| `portal/routers/__init__.py:2` | `.billing` | keep/export surface |
| `portal/routers/__init__.py:2` | `.cases` | keep/export surface |
| `portal/routers/__init__.py:2` | `.documents` | keep/export surface |
| `portal/services/document_processor.py:64` | `pytesseract` | keep/availability probe |
| `portal/tests/test_app_startup.py:25` | `portal.config.get_settings` | keep/availability probe |
| `portal/tests/test_app_startup.py:26` | `portal.main.create_app` | keep/availability probe |
| `portal/tests/test_app_startup.py:27` | `portal.middleware.cors_middleware.CORSMiddleware` | keep/availability probe |
| `portal/tests/test_app_startup.py:28` | `portal.sso.jwt_service.JWTTokenService` | keep/availability probe |
| `portal/tests/test_app_startup.py:29` | `portal.sso.session_manager.SessionManager` | keep/availability probe |
| `tests/test_nova_agent.py:5` | `unittest.mock.patch` | audit framework import |
| `tests/test_nova_agent.py:13` | `agents.nova.action_registry.ActionCategory` | audit fixture import |
| `tests/test_nova_agent.py:16` | `agents.nova.action_registry.ActionValidationError` | audit fixture import |
| `tests/test_nova_agent.py:22` | `agents.nova.action_registry.ApprovalLevel` | audit fixture import |
| `tests/test_nova_agent.py:25` | `agents.nova.approval_gateway.AUTO_APPROVE_ACTIONS` | audit fixture import |
| `tests/test_nova_agent.py:26` | `agents.nova.approval_gateway.LEGAL_REVIEW_ACTIONS` | audit fixture import |
| `tests/test_nova_agent.py:28` | `agents.nova.approval_gateway.ApprovalRequest` | audit fixture import |
| `tests/test_nova_agent.py:37` | `agents.nova.execution_ledger.LedgerIntegrityError` | audit fixture import |
| `tests/test_nova_agent.py:40` | `agents.nova.nova_agent.ActionSpec` | audit fixture import |
| `tests/test_nova_agent.py:42` | `agents.nova.nova_agent.ApprovalLevel` | audit fixture import |
| `tests/test_nova_agent.py:43` | `agents.nova.nova_agent.ExecutionRecord` | audit fixture import |
| `tests/test_scheduler_core.py:18` | `scheduler.task_types.TaskResult` | audit fixture import |
| `tests/test_scheduler_dispatcher.py:13` | `scheduler.task_types.Schedule` | audit fixture import |
| `tests/test_scheduler_executor.py:15` | `scheduler.task_types.TaskResult` | audit fixture import |
| `tests/test_scheduler_recurring.py:20` | `scheduler.task_types.TaskStatus` | audit fixture import |
| `tests/test_scheduler_recurring.py:144` | `scheduler.task_scheduler.TaskScheduler` | audit fixture import |
| `tests/test_scheduler_task_types.py:11` | `pytest` | safe cleanup candidate |
| `tests/test_sigma_agent.py:6` | `unittest.mock.MagicMock` | audit framework import |
| `tests/test_sigma_agent.py:6` | `unittest.mock.PropertyMock` | audit framework import |
| `tests/test_sigma_agent.py:6` | `unittest.mock.patch` | audit framework import |
| `tests/test_sigma_agent.py:19` | `agents.sigma.sigma_agent.GateReport` | audit fixture import |
| `tests/test_zero_agent.py:9` | `unittest.mock.patch` | audit framework import |
| `tests/test_zero_agent.py:16` | `agents.zero.health_monitor.Alert` | audit fixture import |
| `tests/test_zero_agent.py:21` | `agents.zero.zero_agent.COMMON_IMPORT_FIXES` | audit fixture import |
| `tests/test_zero_agent.py:22` | `agents.zero.zero_agent.HealthReport` | audit fixture import |
| `tests/test_zero_agent.py:23` | `agents.zero.zero_agent.ImportError_` | audit fixture import |

## 4) Recommended narrow PR #114 cleanup target (single target only)

**Target file:** `tests/test_scheduler_task_types.py`  
**Target import:** `import pytest` (line 11)

Why this is the preferred narrow candidate:
- Single-file, single-line change.
- File uses only plain `assert` statements and contains no `pytest` symbol references, decorators, fixtures, or `pytest.raises`.
- Isolated scheduler test scope keeps blast radius small.

## 5) Explicit confirmations

- ✅ Sigma remains 70%
- ✅ 75% ratchet held
- ✅ no code imports removed in this PR
- ✅ no `pyproject.toml` changes
- ✅ no workflow changes
- ✅ no excluded directory cleanup
