# Scheduler Test Failure

**Status:** Known Issue  
**Created:** 2026-06-14  
**Priority:** Low (does not block ECC MVP)  
**Follow-up:** PR-0008

---

## Failing Test

`tests/test_scheduler_core.py::TestArming::test_arm_threading_run_at`

**Error:** APScheduler trigger type mismatch - expected trigger instance/string, got datetime

**Result:** 116 passed, 1 failed, 3 warnings (99.1% pass rate)

**Smoke Receipt:** `artifacts/last_smoke_receipt_ref.txt`

---

## Assessment

- **Impact:** Low (scheduler not in production)
- **ECC Blocking:** No (independent subsystem)
- **Fix:** Change `trigger=datetime_obj` to `trigger='date', run_date=datetime_obj`

---

## Follow-up

**PR-0008:** Scheduler smoke cleanup

1. Fix APScheduler trigger in `scheduler/task_scheduler.py:225`
2. Add `__test__ = False` to dataclasses (pytest warnings)
3. Expected: 117/117 tests passing

**Timeline:** After ECC MVP complete
