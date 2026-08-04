# Mission Control Phase Two Increment One — Corrected Certification Evidence

## Certification state

- Original PR: #210 (merged; certification suspended)
- Superseded implementation: `795bdaf2f8da94b7bb4706874be688c477c7f9ba`
- Superseded tree: `320084225fa78244e4373272c5e9a82b7651c240`
- Correction base: `daa65ca4aeba3157677d55d7124a634ec276d658`
- Correction base tree: `8235d88108f05a04e043c88c80bb8048c52bb749`
- Correction branch: `fix/pr210-certification-reproducibility`
- Corrective implementation commit: `450ca21393edc9c05f0fcadada1f6b292708a9fc`
- Corrective implementation tree: `99b5dbb7cc15fd23acdbf0a6bdb5f930bd31e8fa`
- Verification timestamp: `2026-07-31T21:34:18Z`
- Final evidence commit/tree and exact-head CI run IDs: recorded in the draft PR body because a commit cannot contain its own identity or CI runs triggered after it is pushed.

The PR #210 version of this document remains preserved in Git history at the superseded implementation commit. Its stale `20`/`125` test counts and `git diff --check` claim are superseded by the reproducible results below.

## Authorized correction scope

Only certification reproducibility was changed:

1. declared the missing async SQLite test dependency and synchronized managed dependency exports;
2. replaced fragile route-path inspection with a shared recursive inventory helper;
3. normalized the three isolated trailing CR line endings and regenerated this evidence.

No supported command, refusal behavior, authorization rule, idempotency behavior, collision recovery, hash linkage, audit transaction, persistence behavior, database schema semantics, frontend, Operations Floor, Phase One artifact, scheduler, runner, task, mission, agent, assignment, or Increment Two behavior changed.

## Changed files

Implementation commit:

- `pyproject.toml`
- `requirements.txt`
- `requirements-py313-windows.txt`
- `portal/tests/helpers/__init__.py`
- `portal/tests/helpers/route_inventory.py`
- `portal/tests/test_route_inventory.py`
- `portal/tests/test_mission_control_commands.py`
- `portal/tests/test_http_correlation_ws_hardening_certification.py`
- `portal/migrations/add_mission_control_command_ledger.sql`
- `portal/models/mission_control_command.py`
- `portal/services/mission_control_command_guard.py`

Evidence-only commit adds this document update.

## Dependency provenance

Source-of-truth correction:

- `aiosqlite>=0.20.0` added to `dev`, `test`, and `all` optional dependency groups in `pyproject.toml`.

Repository-managed exports synchronized:

- `requirements.txt`: `aiosqlite>=0.20.0`
- `requirements-py313-windows.txt`: `aiosqlite==0.22.1`

The repository had no committed `uv.lock` at the correction base, so no new lock file was introduced.

Artifact SHA-256 values:

| Artifact | SHA-256 |
|---|---|
| `pyproject.toml` | `8ce5b9644c2f31abe377487ce265b126922e40dab15b114aae95656564737f66` |
| `requirements.txt` | `960a79ba7519f40cb14adea1e55b800ef622551a592f40b5d8c6a70ec3089bf8` |
| `requirements-py313-windows.txt` | `3036739beeec18019f3c6939dfd79e0f2111cd994c9e0dcffae22b1d48b7453e` |

## Clean-environment installation

Command, run from the repository root with no pre-existing `.venv-cert` and no intervening manual installation:

```bash
UV_PROJECT_ENVIRONMENT=.venv-cert uv sync --extra dev --extra portal
```

Result: **PASS**, exit code `0`. The isolated environment installed `aiosqlite==0.22.1` directly from committed dependency metadata.

Resolved verification versions:

| Component | Version |
|---|---:|
| Python | `3.13.14` |
| FastAPI | `0.141.1` |
| SQLAlchemy | `2.0.51` |
| aiosqlite | `0.22.1` |
| pytest | `9.1.1` |

## Route inventory design

`portal/tests/helpers/route_inventory.py` recursively resolves terminal routes across:

- FastAPI `APIRoute` leaves;
- Starlette `Mount` containers;
- nested `.routes` collections;
- FastAPI `_IncludedRouter` wrappers via `.original_router.routes`;
- `.include_context.prefix`;
- duplicate/trailing slash normalization;
- cyclic graphs through ancestry-based cycle prevention.

Ancestry-based prevention allows the same router to remain visible when legitimately mounted under distinct prefixes. The Mission Control prohibited-route assertion and the existing WebSocket route-count certification both use the shared helper.

Route-inventory and WebSocket certification commands:

```bash
.venv-cert/bin/python -m pytest   portal/tests/test_route_inventory.py   portal/tests/test_http_correlation_ws_hardening_certification.py   --collect-only -q

.venv-cert/bin/python -m pytest   portal/tests/test_route_inventory.py   portal/tests/test_http_correlation_ws_hardening_certification.py   -q
```

Collection: `5 + 122 = 127`. Result: **127 passed**, exit code `0`. No route-object `AttributeError` occurred.

## Exact test results

### Mission Control command suite

```bash
.venv-cert/bin/python -m pytest portal/tests/test_mission_control_commands.py --collect-only -q
.venv-cert/bin/python -m pytest portal/tests/test_mission_control_commands.py -q
```

- Collected: `45`
- Result: **45 passed**
- Exit code: `0`

This suite includes the recursive no-operational-mutation-route assertion.

### Combined focused suite

```bash
.venv-cert/bin/python -m pytest   portal/tests/test_mission_control_commands.py   portal/tests/test_mission_control.py   portal/tests/test_rbac.py   portal/tests/test_service_units.py   --collect-only -q

.venv-cert/bin/python -m pytest   portal/tests/test_mission_control_commands.py   portal/tests/test_mission_control.py   portal/tests/test_rbac.py   portal/tests/test_service_units.py   -q
```

Collection:

- `test_mission_control_commands.py`: `45`
- `test_mission_control.py`: `1`
- `test_rbac.py`: `34`
- `test_service_units.py`: `70`
- Total: `150`

Result: **150 passed**, exit code `0`.

### Service-unit suite

```bash
.venv-cert/bin/python -m pytest portal/tests/test_service_units.py --collect-only -q
.venv-cert/bin/python -m pytest portal/tests/test_service_units.py -q
```

- Collected: `70`
- Result: **70 passed**
- Exit code: `0`

## Static and metadata validation

### Ruff

```bash
.venv-cert/bin/ruff check   portal/tests/helpers/route_inventory.py   portal/tests/test_route_inventory.py   portal/tests/test_mission_control_commands.py   portal/tests/test_http_correlation_ws_hardening_certification.py   portal/models/mission_control_command.py   portal/services/mission_control_command_guard.py
```

Result: **PASS**, exit code `0`.

### Python compilation

```bash
.venv-cert/bin/python -m py_compile   portal/tests/helpers/route_inventory.py   portal/tests/test_route_inventory.py   portal/tests/test_mission_control_commands.py   portal/tests/test_http_correlation_ws_hardening_certification.py   portal/models/mission_control_command.py   portal/services/mission_control_command_guard.py
```

Result: **PASS**, exit code `0`.

### SQLAlchemy metadata registration

The metadata smoke check imported `portal.models` and verified exact registration of:

- `mission_control_commands`
- `mission_control_command_events`
- `mission_control_command_receipts`

Result: **PASS**, exit code `0`.

### Diff integrity and line endings

```bash
git diff --check daa65ca4aeba3157677d55d7124a634ec276d658..450ca21393edc9c05f0fcadada1f6b292708a9fc
```

Result: **PASS**, exit code `0`.

The isolated trailing CR was removed from each authorized file. Corrected SHA-256 values:

| File | SHA-256 |
|---|---|
| `portal/migrations/add_mission_control_command_ledger.sql` | `20e0e8b532e6233df7cb72048c016855fb0fe7d4b2e255eb3acb9ea1a0713356` |
| `portal/models/mission_control_command.py` | `e3c7286b64b703c5a3ce4438e629cb57a21929c1d6bfc520441e726c5546588f` |
| `portal/services/mission_control_command_guard.py` | `707f2526b51b2ba3d5d04c992229adb1b5ab84ab6207d4df6e0b988011f9bcd8` |

## Exact-head CI and review closure

Final pushed-head workflow run IDs, job conclusions, live unresolved-review count, review quiet-period result, and the final certification recommendation are recorded in the draft PR body after GitHub completes checks against the evidence commit. This committed report does not fabricate future run identifiers.

## Current recommendation

**REVIEW INCOMPLETE** until the final evidence commit is pushed, exact-head CI is green, review threads are refreshed, and the required quiet period closes. Command execution and Increment Two remain prohibited.
