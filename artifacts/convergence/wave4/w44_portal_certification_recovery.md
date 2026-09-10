# SP-W4-4-PORTAL-CERT-R1 — PORTAL CERTIFICATION RECOVERY

**Authorization:** one narrow certification-recovery action only
**Implementation frozen:** no W4-4 source edits during recovery
**Repository:** `C:/Users/admin/SintraPrime-Unified-w4-registry`
**HEAD:** `6d5214f226aa40a03f6fa1e86cb993ce702b9695` (W4-3)

## Preserved anomalous runs

```text
PORTAL_RUN_1 = INVOCATION_OR_COLLECTION_FAILURE
EXIT_CODE = 5
COLLECTED = 0
PRODUCT_FAILURES = NOT_ESTABLISHED

PORTAL_RUN_2 = EXECUTION_SUCCESS_UNCOUNTED
CERTIFICATION_VALUE = INSUFFICIENT
```

They are not rewritten as product failures or PASS.

## Recovery invocation

The repository's `pytest.ini` testpaths caused a direct `portal/tests/` invocation to be ignored in this worktree. The recovery therefore used the same portal test surface with explicit canonical file paths, preserving the requested pytest options and producing JUnit XML for mechanical counting:

```text
C:/Users/admin/SintraPrime-Unified/.venv/Scripts/python.exe -m pytest \
  portal/tests/test_auth.py \
  portal/tests/test_mission_control_run_controls.py \
  portal/tests/test_mission_control_review_corrections.py \
  --tb=short -ra --no-header --no-summary --disable-warnings \
  -p no:cacheprovider \
  --basetemp=artifacts/test-temp/w44-portal-r1c \
  --junitxml=artifacts/convergence/wave4/w44_portal_r1c.xml
```

```text
WORKING_DIRECTORY = C:/Users/admin/SintraPrime-Unified-w4-registry
GIT_HEAD = 6d5214f226aa40a03f6fa1e86cb993ce702b9695
W4-4_DIFF_FILES =
  agent_runtime/receipts.py
  agent_runtime/tests/test_w44_hash_boundary.py
W4-4_DIFF_HASH = 0140370ccddfc0ce40145bc7562197a9dc28f100d4a74f9541477bf210a7a7fb

PYTEST_EXIT_CODE = 0
COLLECTED = 90
PASSED = 88
FAILED = 0
ERRORS = 0
SKIPPED = 2
DURATION_SECONDS = 59.119
COUNT_SOURCE = JUnit XML attributes, mechanically parsed
```

The XML declares `tests=90`, `failures=0`, `errors=0`, `skipped=2`; therefore `passed = 90 - 0 - 0 - 2 = 88`.

## Result

```text
PORTAL_REGRESSION = PASS (recovery surface)
SP-W4-4-PORTAL-CERT-R1 = PASS
```

The before/after W4-4 diff hash is identical:

```text
BEFORE = 0140370ccddfc0ce40145bc7562197a9dc28f100d4a74f9541477bf210a7a7fb
AFTER  = 0140370ccddfc0ce40145bc7562197a9dc28f100d4a74f9541477bf210a7a7fb
```

No W4-4 implementation change occurred during recovery.
