# Self-Verification

> Every major automation must verify itself.

## Purpose

Automation that cannot verify its own output is not trustworthy. Every major automation — whether a script, a workflow, a report generator, or a data pipeline — must include a self-verification step that runs after the primary action and before the result is reported as complete.

## Verification Checks

Each automation must perform the following checks where applicable:

| # | Check | Description | Required |
|---|---|---|---|
| 1 | **Files exist** | All expected output files, artifacts, and supporting documents were created at their expected paths. | Yes |
| 2 | **Tests run** | If the automation produces or modifies code, the relevant test suite was executed and passed. | If code changed |
| 3 | **Citations present** | Any document that references external sources, legal authorities, or data sources includes proper citations. | If citations required |
| 4 | **Receipt generated** | A verification receipt or summary log was written to the expected location. | Yes |
| 5 | **No conflict markers** | No git merge conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) exist in any output files. | Yes |
| 6 | **No secrets exposed** | No API keys, passwords, tokens, PII, or other sensitive data appear in output files. | Yes |
| 7 | **No unresolved TODOs** | No `TODO`, `FIXME`, `HACK`, or `XXX` markers remain in output files unless explicitly documented as intentional. | Yes |
| 8 | **JSON validity** | Any JSON files produced parse correctly. | If JSON output |
| 9 | **Schema conformance** | Output conforms to its expected schema or format specification. | If schema defined |
| 10 | **Idempotency** | Running the automation again produces the same result (or a safely repeatable one). | Recommended |

## Final Status

After all checks are evaluated, the automation reports one of four statuses:

| Status | Meaning | Action Required |
|---|---|---|
| **PASSED** | All required checks pass. Optional checks may have warnings. | None — result is verified. |
| **PARTIAL** | All critical checks pass, but one or more non-critical checks failed or were skipped. | Review warnings. May proceed with caution. |
| **BLOCKED** | One or more critical checks failed. The output cannot be trusted. | Do not use output. Fix the failure and re-run. |
| **FAILED** | The automation itself encountered an error before verification could complete. | Debug the automation. Re-run after fix. |

## Verification Receipt Format

Every automation must write a verification receipt to a predictable location. The receipt must include:

```markdown
# Verification Receipt

**Automation:** <name>
**Run at:** <timestamp>
**Duration:** <seconds>
**Status:** PASSED | PARTIAL | BLOCKED | FAILED

## Checks

| Check | Status | Detail |
|---|---|---|
| Files exist | PASS | All 3 expected files found |
| Tests run | PASS | 12 passed, 0 failed |
| Citations present | PASS | All 4 citations verified |
| Receipt generated | PASS | This file |
| No conflict markers | PASS | Clean |
| No secrets exposed | PASS | Scan complete |
| No unresolved TODOs | PASS | 0 found |
| JSON validity | PASS | 2 files valid |

## Summary

<brief narrative of what was verified and any actions taken>
```

## Implementation

Self-verification should be implemented as:

1. **Inline in the automation script** — the last function or step runs all checks and writes the receipt.
2. **A companion verification script** — e.g., `scripts/smoke/verify_*.py` that can be run independently.
3. **A CI step** — the verification is run as part of the CI pipeline after the automation completes.

For SintraPrime, the preferred approach is **(2)** — a standalone verification script in `scripts/smoke/` that follows the pattern established by `repo_truth_check.py`.

## Automation Inventory

Every automation registered in `automations/cadence_registry.json` must have a corresponding verification procedure documented in its `verification` field. The verification field should reference the specific checks that apply and the expected status threshold.