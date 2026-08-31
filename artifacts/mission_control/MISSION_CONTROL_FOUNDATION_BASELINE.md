# Mission Control Foundation — Baseline Record

**Record type:** Baseline
**Date:** 2026-08-04
**Branch:** feat/mission-control-foundation

## 1. Git SHAs

| Item | SHA |
|------|-----|
| Base (main) | 22b384a707f87ab7dcc3051f483eba000ab8e71f |
| Starting HEAD | 759c4e3944a8d564e7f1945e7c3e7be4ef64dbce |
| Starting tree SHA | 6e151330f0dfa3678e4138abb9a30408b3de5a23 |

## 2. Files Created

### 2.1 New Backend Files (4)

1. `backend/app/routers/mission_control.py` — Mission Control read-only router (6 new GET endpoints).
2. `backend/app/schemas/mission_control.py` — Pydantic schemas for intent, run-control, causation-chain, sigma-gate, summary.
3. `backend/app/services/mission_control_service.py` — Read-only projection service (intents, run-controls, causation chain, sigma gate).
4. `backend/tests/mission_control/test_mission_control.py` — Backend test suite for Mission Control (tenant isolation, read-only enforcement, sigma gate, auth).

### 2.2 New Frontend / Spec Files (1)

5. `e2e/mission-control.spec.ts` — Playwright spec covering the Mission Control shell (13 tests).

## 3. Files Modified

1. `backend/app/main.py` — Registration of the Mission Control router.
2. `backend/app/core/permissions.py` — Addition of `MISSION_COMMAND_READ` permission.
3. `backend/app/core/sigma_gate.py` — Sigma gate implementation (`is_cancellation_blocked()` returns True; BLOCKED state).
4. `frontend/src/pages/mission-control/` — Mission Control shell (Layout, Home, Surface, data adapters).

## 4. ADR-002 Conformance Checklist

| Requirement | Conforms | Notes |
|-------------|----------|-------|
| Brain owns intent/dispatch/cancellation state | YES | No mutation authority transferred to Mission Control. |
| Mission Control is read-only projection | YES | 6 new GET endpoints; no new mutation routes. |
| No new mutation routes introduced | YES | Only GET endpoints added. |
| Pre-existing POST /commands unchanged | YES | Refusal-only, returns COMMAND_EXECUTION_NOT_ENABLED. |
| No cancellation/approval/retry/replay/lease/dispatch mutation | YES | None added. |
| No persistence migrations added | YES | None added. |
| SIGMA_LEASE_EXPIRY_CONTINUATION_GATE BLOCKED | YES | Gate remains blocking. |
| Cancellation controls DISABLED | YES | is_cancellation_blocked() returns True. |
| Transport neutrality preserved | YES | No transport technology selected. |
| Tenant isolation enforced | YES | All queries filter on current_user.tenant_id; cross-tenant returns 404. |
| Auth required (MISSION_COMMAND_READ) | YES | All new endpoints require permission. |

## 5. Notes

- The baseline was captured before any local commits on the feature branch beyond the starting HEAD.
- All SHAs are exact and reproducible from the repository.
- This baseline record supports the certification and status artifacts.