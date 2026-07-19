# Repository Convergence Increment One — Evidence

**Baseline commit:** 10cad07f046b5675ed10a1fba1aa4a955636f739
**Baseline tree:** 66f59a5bf832e9f3ce3c484c64891fd543359abf
**Subject-code commit:** e1e94581e1d0840e1ad6d4c9ddb775bcf2a34db1
**Subject-code tree:** 9448a71b30a7b4900b1ce79667143a57921b6f15
**Integration branch:** docs/repository-convergence-increment-1
**Evidence-container commit:** recorded in final PR metadata after evidence amendment
**Generated:** 2026-07-19T18:35:55Z

## Scope
Documentation, CI-truth, and governance convergence ONLY. No runtime, model,
migration, route, or frontend behavior changes.

## Verification results
| Check | Result |
|-------|--------|
| Documentation/claim validator | PASS |
| report_test_inventory unit tests | 10 passed |
| validate_repository_claims unit tests | 8 passed |
| Runtime diff vs baseline (portal/web/src/migrations) | EMPTY (no changes) |
| Frontend lint/type-check/build | PASS (pre-edit run; no web files changed) |
| PostgreSQL race lane | SUCCESS (preserved job green) |
| Exact-head SintraPrime CI | SUCCESS (all required jobs green) |
| Test inventory from exact head | collected=432, rc=0, authoritative=true, incomplete=false (artifact-confirmed) |
| git diff --check | CR-at-EOL warnings only (CRLF repo convention); no CI gate enforces it |

## Swarm execution note (honest)
The governed parallel specialist dispatch (RC-A..G) was interrupted by the
tool-limit path: no genuine specialist receipts were produced. The Integration
Agent therefore completed the work serially from the preserved consolidated
candidate and performed the RC-H-equivalent verification itself. The correct
classification is:

SWARM PARTIAL — specialist dispatch unsuccessful; integration completed
serially with honest disclosure.

## Stash comparison
The named `rc-increment-1-prior-turn-backup` stash is not visible in this
workspace's current `refs/stash`; the visible stash entries are unrelated and
were left untouched. No destructive stash operation was performed.

| file | specialist source | stash source | selected source | reason |
|---|---|---|---|---|
| docs/repository-convergence/* | unavailable (no genuine specialist receipts) | unavailable in current refs/stash | integrated branch evidence files | preserve the stronger validated anchors, exact-head CI facts, and honest partial-swarm disclosure |
| scripts/ci/report_test_inventory.py | integration-agent hardening | prior consolidated work candidate | integrated branch version | return-code-aware parsing, error capture, incomplete flag, tests |
| scripts/ci/validate_repository_claims.py | integration-agent verification path | prior consolidated work candidate | integrated branch version | deterministic claim validation and machine-readable output |

## Runtime behavior unchanged — explicit statement
No production Python files, routes, schemas, or frontend source files were
modified. The only code changes are two CI scripts (test inventory + claim
validator) and their tests, plus CI workflow edits that preserve all security
and concurrency gates.
