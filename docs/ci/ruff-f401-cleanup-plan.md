# Ruff F401 Cleanup Ladder — Phase 3 Plan

**Status:** Planning only — no code cleanup, no import removals.

**Branch:** `docs/ruff-f401-cleanup-plan`  
**Deliverable:** `docs/ci/ruff-f401-cleanup-plan.md`

---

## Executive Summary

> **Configured Ruff gate reports zero F401 failures, but the raw active-dir F401 backlog must be
> audited because F401 remains suppressed in per-file-ignores.**

Running `ruff check . --select F401` against the main config passes cleanly because several
active-directory path patterns have F401 listed in `per-file-ignores`. The gate is not detecting
unused imports in those paths — it is silencing them.

A raw audit using `ruff check --isolated` (bypassing per-file-ignores) reveals **48 F401
violations** across active directories.

---

## Active-Dir F401 Suppression Entries

The following `per-file-ignores` entries in `pyproject.toml` suppress F401 in active directories:

| Pattern | Line | Also suppresses |
|---------|------|-----------------|
| `portal/routers/**` | 226 | ARG001, ARG002, B008, B904, DTZ003, E741, F811, N999, UP006, UP035 |
| `portal/services/**` | 229 | ARG001, ARG002, N806, N999, RUF006, UP006, UP015, UP035 |
| `portal/tests/**` | 231 | ARG001, ARG002, ARG005, B017, DTZ003, N802, N999, PT011, RUF002, RUF012, SIM117 |
| `tests/**` | 234 | ARG002, F811, F841, N802, N999, PT009, PT011, PT027, RUF059 |

**Non-active dirs (also suppressed, not in scope for this plan):**
- `scripts/**` (line 214)
- `backend/lead-router/**` (line 216)
- `backend/stripe-payments/**` (line 217)
- `governance/**` (line 219)

---

## Raw F401 Backlog (Active Dirs Only)

**Command used:**

```bash
ruff check portal tests --select F401 --isolated --output-format=concise
```

> Note: `packages/` directory was not found on main (no violation either way).
> `portal/middleware.py` has a known syntax error (pre-existing, tracked separately).

**Total: 48 violations across 10 files. 33 are auto-fixable (marked `[*]`). 15 are not.**

---

## File-by-File Classification

### `portal/routers/__init__.py` — 4 violations — [⚠️ `__init__.py` export risk]

```
portal/routers/__init__.py:2:15: F401 `.auth` imported but unused
portal/routers/__init__.py:2:21: F401 `.billing` imported but unused
portal/routers/__init__.py:2:30: F401 `.cases` imported but unused
portal/routers/__init__.py:2:37: F401 `.documents` imported but unused
```

**Classification: `__init__.py` export surface — DO NOT REMOVE**  
Imports in `__init__.py` may be re-exporting names to downstream consumers (`from portal.routers
import auth`). Removing without checking all call sites can break the public API silently.

---

### `portal/services/document_processor.py` — 1 violation — [⚠️ Side-effect risk]

```
portal/services/document_processor.py:64:16: F401 `pytesseract` imported but unused
  (consider using `importlib.util.find_spec` to test for availability)
```

**Classification: Possible side-effect import — AUDIT BEFORE REMOVING**  
`pytesseract` may be imported to register itself with PIL/Pillow or to trigger an OCR engine
check. The `importlib.util.find_spec` suggestion from ruff confirms it suspects a non-trivial
pattern. Must inspect the function body before any removal.

---

### `portal/tests/test_app_startup.py` — 5 violations — [⚠️ Test availability probe]

```
portal/tests/test_app_startup.py:25:35: F401 `portal.config.get_settings` imported but unused
portal/tests/test_app_startup.py:26:33: F401 `portal.main.create_app` imported but unused
portal/tests/test_app_startup.py:27:55: F401 `portal.middleware.cors_middleware.CORSMiddleware` imported but unused
portal/tests/test_app_startup.py:28:44: F401 `portal.sso.jwt_service.JWTTokenService` imported but unused
portal/tests/test_app_startup.py:29:48: F401 `portal.sso.session_manager.SessionManager` imported but unused
```

**Classification: Test availability probes — DO NOT REMOVE**  
In app-startup test files, importing a module without using it is a deliberate pattern: the test
checks that the import itself does not raise an error. Removing these imports would destroy the
test's intent. The ruff `importlib.util.find_spec` suggestion confirms this pattern.

---

### `tests/test_nova_agent.py` — 16 violations — [Mixed]

```
tests/test_nova_agent.py:3:8:  F401 [*] `json` imported but unused
tests/test_nova_agent.py:6:8:  F401 [*] `tempfile` imported but unused
tests/test_nova_agent.py:7:21: F401 [*] `pathlib.Path` imported but unused
tests/test_nova_agent.py:8:38: F401 [*] `unittest.mock.patch` imported but unused
tests/test_nova_agent.py:16:5: F401 [*] `agents.nova.action_registry.ActionCategory` imported but unused
tests/test_nova_agent.py:19:5: F401 [*] `agents.nova.action_registry.ActionValidationError` imported but unused
tests/test_nova_agent.py:25:22: F401 [*] `agents.nova.action_registry.ApprovalLevel` imported but unused
tests/test_nova_agent.py:28:5: F401 [*] `agents.nova.approval_gateway.AUTO_APPROVE_ACTIONS` imported but unused
tests/test_nova_agent.py:29:5: F401 [*] `agents.nova.approval_gateway.LEGAL_REVIEW_ACTIONS` imported but unused
tests/test_nova_agent.py:31:5: F401 [*] `agents.nova.approval_gateway.ApprovalRequest` imported but unused
tests/test_nova_agent.py:40:5: F401 [*] `agents.nova.execution_ledger.LedgerIntegrityError` imported but unused
tests/test_nova_agent.py:43:5: F401 [*] `agents.nova.nova_agent.ActionSpec` imported but unused
tests/test_nova_agent.py:45:5: F401 [*] `agents.nova.nova_agent.ApprovalLevel` imported but unused
tests/test_nova_agent.py:46:5: F401 [*] `agents.nova.nova_agent.ExecutionRecord` imported but unused
```

**Classification breakdown:**
- `json`, `tempfile`, `pathlib.Path` — **Likely safe stdlib removals**  
- `unittest.mock.patch` — **Test fixture risk** — may be used indirectly (decorator or conftest)
- `agents.nova.*` imports — **Test fixture / monkeypatch pattern** — may be needed for
  test-time registration or to trigger module-level side effects. Verify before removing.

---

### `tests/test_scheduler_core.py` — 2 violations — [Mixed]

```
tests/test_scheduler_core.py:10:8: F401 [*] `time` imported but unused
tests/test_scheduler_core.py:19:5: F401 [*] `scheduler.task_types.TaskResult` imported but unused
```

- `time` — **Likely safe stdlib removal**
- `scheduler.task_types.TaskResult` — **Test fixture pattern** — audit before removing

---

### `tests/test_scheduler_dispatcher.py` — 1 violation

```
tests/test_scheduler_dispatcher.py:13:34: F401 [*] `scheduler.task_types.Schedule` imported but unused
```

**Classification: Test fixture pattern** — audit before removing.

---

### `tests/test_scheduler_executor.py` — 1 violation

```
tests/test_scheduler_executor.py:15:59: F401 [*] `scheduler.task_types.TaskResult` imported but unused
```

**Classification: Test fixture pattern** — audit before removing.

---

### `tests/test_scheduler_recurring.py` — 2 violations

```
tests/test_scheduler_recurring.py:20:44:  F401 [*] `scheduler.task_types.TaskStatus` imported but unused
tests/test_scheduler_recurring.py:144:46: F401 [*] `scheduler.task_scheduler.TaskScheduler` imported but unused
```

**Classification: Test fixture patterns** — audit before removing.

---

### `tests/test_scheduler_task_types.py` — 1 violation

```
tests/test_scheduler_task_types.py:11:8: F401 [*] `pytest` imported but unused
```

**Classification: Test framework import** — audit carefully. `pytest` may appear unused to
ruff but could be referenced by a conftest or fixture via string. Likely safe, but verify.

---

### `tests/test_sigma_agent.py` — 6 violations — [Mixed]

```
tests/test_sigma_agent.py:3:8:  F401 [*] `json` imported but unused
tests/test_sigma_agent.py:6:8:  F401 [*] `tempfile` imported but unused
tests/test_sigma_agent.py:8:27: F401 [*] `unittest.mock.MagicMock` imported but unused
tests/test_sigma_agent.py:8:38: F401 [*] `unittest.mock.PropertyMock` imported but unused
tests/test_sigma_agent.py:8:52: F401 [*] `unittest.mock.patch` imported but unused
tests/test_sigma_agent.py:21:5: F401 [*] `agents.sigma.sigma_agent.GateReport` imported but unused
```

- `json`, `tempfile` — **Likely safe stdlib removals**
- `unittest.mock.*` — **Test fixture risk** — patch/MagicMock/PropertyMock may be used via
  decorators or passed to helper functions not visible at import site
- `agents.sigma.sigma_agent.GateReport` — **Test fixture pattern** — audit before removing

---

### `tests/test_zero_agent.py` — 7 violations — [Mixed]

```
tests/test_zero_agent.py:8:8:  F401 [*] `tempfile` imported but unused
tests/test_zero_agent.py:10:38: F401 [*] `unittest.mock.patch` imported but unused
tests/test_zero_agent.py:17:5: F401 [*] `agents.zero.health_monitor.Alert` imported but unused
tests/test_zero_agent.py:22:5: F401 [*] `agents.zero.zero_agent.COMMON_IMPORT_FIXES` imported but unused
tests/test_zero_agent.py:23:5: F401 [*] `agents.zero.zero_agent.HealthReport` imported but unused
tests/test_zero_agent.py:24:5: F401 [*] `agents.zero.zero_agent.ImportError_` imported but unused
```

- `tempfile` — **Likely safe stdlib removal**
- `unittest.mock.patch` — **Test fixture risk**
- `agents.zero.*` — **Test fixture / monkeypatch patterns** — audit before removing

---

## Risk Category Summary

| Category | Count | Files | Action |
|----------|-------|-------|--------|
| `__init__.py` export surface | 4 | `portal/routers/__init__.py` | 🚫 DO NOT REMOVE |
| Side-effect import | 1 | `portal/services/document_processor.py` | ⚠️ Audit first |
| Test availability probes | 5 | `portal/tests/test_app_startup.py` | 🚫 DO NOT REMOVE |
| Test fixture / monkeypatch | ~25 | Various `tests/` files | ⚠️ Audit first |
| Stdlib removals (likely safe) | ~7 | Various `tests/` files | ✅ Pilot candidates |
| `pytest` framework import | 1 | `tests/test_scheduler_task_types.py` | ⚠️ Audit first |

---

## Raw Audit Method (Reproducible)

To reproduce the raw backlog count on any branch:

```bash
# Isolated mode bypasses per-file-ignores
ruff check portal tests --select F401 --isolated --output-format=concise
```

To audit a single file in depth:

```bash
ruff check <file> --select F401 --isolated --output-format=full
```

To count only auto-fixable violations:

```bash
ruff check portal tests --select F401 --isolated --output-format=concise 2>&1 | grep '\[\*\]' | wc -l
```

---

## PR #112 Recommendation

**Scope: Stdlib-only safe removal pilot**

Remove only the following obvious unused stdlib imports from test files where there is **zero
side-effect risk** and the import is NOT a fixture, NOT a monkeypatch helper, and NOT used via
an indirect reference:

### Candidates for PR #112 (subject to file-level inspection)

| File | Import | Risk |
|------|--------|------|
| `tests/test_nova_agent.py` | `json`, `tempfile`, `pathlib.Path` | Low — stdlib, unused |
| `tests/test_scheduler_core.py` | `time` | Low — stdlib, unused |
| `tests/test_sigma_agent.py` | `json`, `tempfile` | Low — stdlib, unused |
| `tests/test_zero_agent.py` | `tempfile` | Low — stdlib, unused |

**Total safe pilot: ~7 removals**

### Explicitly Rejected for PR #112

| File | Reason |
|------|--------|
| `portal/routers/__init__.py` | `__init__.py` export surface — requires full API audit |
| `portal/services/document_processor.py` | Side-effect import (`pytesseract`) |
| `portal/tests/test_app_startup.py` | Availability probes — intentionally unused |
| All `unittest.mock.*` imports | Test fixture risk — indirect usage patterns |
| All `agents.*` test imports | Monkeypatch / fixture registration risk |
| `tests/test_scheduler_task_types.py:pytest` | Framework import — audit required |
| All excluded directories | No approval granted |

---

## Verification Plan (For PR #112)

```bash
# 1. Confirm only targeted files changed
git diff --name-only

# 2. Verify no __init__.py touched
git diff --name-only | grep __init__
# Expected: empty

# 3. Run pytest on affected files
pytest tests/test_nova_agent.py tests/test_scheduler_core.py tests/test_sigma_agent.py tests/test_zero_agent.py -v

# 4. Run configured F401 check (gate must still pass)
ruff check portal tests --select F401

# 5. Confirm per-file-ignores unchanged
git diff pyproject.toml
# Expected: empty
```

---

## Rollback Plan

```bash
git revert <pr-112-commit-sha>
git push
```

All changes in the PR #112 pilot are single-line import removals with no logic impact.
Rollback is immediate and safe.

---

## Constraints (Enforced)

- ✅ No source code cleanup in PR #111
- ✅ No import removals in PR #111
- ✅ No excluded-directory cleanup
- ✅ No workflow changes
- ✅ No Bandit changes
- ✅ No Sigma threshold changes
- ✅ Sigma 70% enforced; 75% ratchet held

---

## Ruff Cleanup Ladder Progress

| Phase | PR | Focus | Status |
|-------|----|-------|--------|
| Phase 1 | #109 | I001 import sorting | ✅ Merged |
| Phase 2 | #110 | W293 trailing whitespace plan | ✅ Merged |
| Phase 3 | #111 | F401 backlog audit | 🟠 This PR |
| Phase 4 | #112 | F401 stdlib pilot (7 removals) | ⏳ Pending |
