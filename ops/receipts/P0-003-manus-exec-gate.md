# P0-003 Receipt — Exec Gate Implementation

**Task:** P0-003: Disable unsafe `exec()` paths in Nova agent and scheduler  
**Agent:** Manus  
**Branch:** `agent/manus/P0-003-disable-exec`  
**Date:** 2026-04-30  
**Status:** COMPLETE ✅

---

## Summary

All `exec()` call sites in `agents/nova/nova_agent.py` and `scheduler/task_executor.py` are now gated behind the `NOVA_ALLOW_DYNAMIC_EXEC` environment variable, which defaults to `false` (deny). The gate is case-insensitive and re-evaluated on every call. `PermissionError` propagates cleanly — it is no longer swallowed by the broad `except Exception` block.

---

## Files Changed

| File | Change |
|---|---|
| `agents/nova/nova_agent.py` | Added `NOVA_ALLOW_DYNAMIC_EXEC` gate before `exec()` at line 319; added `PermissionError` re-raise at line 340 to prevent gate bypass via broad except |
| `scheduler/task_executor.py` | Added `import os`; added `NOVA_ALLOW_DYNAMIC_EXEC` gate before `exec()` in `execute_python()`; added `shell=False` confirmation log in `execute_shell()` |
| `tests/security/test_no_runtime_exec.py` | **New file** — 28 tests across 3 test classes |

---

## Before/After

```bash
# BEFORE — exec() reachable with no env var set
grep -n "exec(" agents/nova/nova_agent.py scheduler/task_executor.py
agents/nova/nova_agent.py:320:                    exec(code.strip(), globals(), local_env)
scheduler/task_executor.py:188:                exec(textwrap.dedent(code), safe_globals)  # noqa: S102

# AFTER — both lines are gated
grep -n "NOVA_ALLOW_DYNAMIC_EXEC" agents/nova/nova_agent.py scheduler/task_executor.py
agents/nova/nova_agent.py:320:                    if os.environ.get("NOVA_ALLOW_DYNAMIC_EXEC", "false").lower() != "true":
scheduler/task_executor.py:187:        if os.environ.get("NOVA_ALLOW_DYNAMIC_EXEC", "false").lower() != "true":
```

---

## Gate Behaviour

| `NOVA_ALLOW_DYNAMIC_EXEC` value | Result |
|---|---|
| Not set (default) | `PermissionError` — blocked |
| `false`, `0`, `""`, any non-`true` | `PermissionError` — blocked |
| `true`, `TRUE`, `True` | Permitted — exec() runs |

---

## Test Results

```
28 passed in 0.12s
```

**Test classes:**

- `TestNovaExecGate` (9 tests) — gate blocked/permitted/case-insensitive/known-actions/re-evaluated
- `TestTaskExecutorExecGate` (11 tests) — gate blocked/permitted/case-insensitive/safe-builtins/output-capture/error-message
- `TestTaskExecutorShellSafety` (8 tests) — shell=False enforcement, dangerous pattern blocking, timeout

---

## Bandit Verification

```bash
bandit -r agents/nova/nova_agent.py scheduler/task_executor.py --baseline .bandit-baseline.json
# Result: No new issues introduced
```

The two `exec()` calls remain in the bandit baseline (pre-existing), but are now unreachable without explicit opt-in.

---

## Security Impact

| Risk | Before | After |
|---|---|---|
| Arbitrary code execution via Nova dynamic handler | **HIGH** — reachable by any caller | **MITIGATED** — requires `NOVA_ALLOW_DYNAMIC_EXEC=true` |
| Arbitrary Python execution via TaskExecutor | **HIGH** — reachable by any caller | **MITIGATED** — requires `NOVA_ALLOW_DYNAMIC_EXEC=true` |
| Shell injection via execute_shell() | **LOW** — already used list args | **CONFIRMED** — `shell=False` documented and tested |
| Gate bypass via exception swallowing | **HIGH** — `PermissionError` was caught by broad `except Exception` | **FIXED** — `PermissionError` now re-raised before the broad handler |

---

## .env.example Update Required

Add to `.env.example` (already present from P0-001):
```
NOVA_ALLOW_DYNAMIC_EXEC=false   # Set to true ONLY in trusted dev environments
```

---

## Next Task

**P0-004:** Fix 19 Dependabot CVEs (6 high, 13 moderate) in `requirements.txt`.
