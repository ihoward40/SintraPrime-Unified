# R1-RECOVERY — Failure Matrix

Every row is exercised by `decision/tests/test_r1_conformance.py`
(TestFailClosed, TestAbstention). Expected result for ALL rows:
`no deterministic execution → FALLBACK_HERMES` (the pre-existing governed
path). Fail-open on any row = R1 failure.

## Transport-class failures (Jev adapter; mock fault injection + real mapping)

| # | Fault | Provider result | Policy result | Test |
|---|---|---|---|---|
| 1 | timeout | UNAVAILABLE | FALLBACK_HERMES | TestFailClosed::test_all_faults_fail_closed[timeout] |
| 2 | connection failure | UNAVAILABLE | FALLBACK_HERMES | [connection] |
| 3 | DNS failure | UNAVAILABLE | FALLBACK_HERMES | [dns] + live mapping test |
| 4 | HTTP 429 | UNAVAILABLE | FALLBACK_HERMES | [http_429] |
| 5 | HTTP 5xx | UNAVAILABLE | FALLBACK_HERMES | [http_500] |
| 6 | connection error (live transport seam) | UNAVAILABLE | FALLBACK_HERMES | test_jev_transport_failures_map_unavailable |

## Response-class failures

| # | Fault | Provider result | Policy result | Test |
|---|---|---|---|---|
| 7 | malformed response (non-mapping) | ERROR | FALLBACK_HERMES | TestFailClosed::test_all_faults_fail_closed[malformed] |
| 8 | invalid JSON body | ERROR | FALLBACK_HERMES | [invalid_json] |
| 9 | unknown provider primitive (`oracle`) | ERROR | FALLBACK_HERMES | [unknown_primitive] + jev malformed[resp1] |
| 10 | missing confidence | ERROR | FALLBACK_HERMES | [missing_confidence] |
| 11 | missing distribution | ERROR | FALLBACK_HERMES | [missing_distribution] + jev malformed[resp2] |
| 12 | schema mismatch (missing answers) | ERROR | FALLBACK_HERMES | [schema_mismatch] + jev malformed[resp3,4] |
| 13 | contract mismatch (unknown question / off-contract choice) | ERROR | FALLBACK_HERMES | [contract_mismatch] + jev malformed[resp2] |

## Semantic failure classes

| # | Fault | Behavior | Test |
|---|---|---|---|
| 14 | provider ABSTAIN | first-class result; FALLBACK_HERMES; never success/low-risk/route | TestAbstention |
| 15 | ambiguous distribution 0.41/0.40/0.19 (argmax exists, margin 0.01) | HERMES_REVIEW even with shadow off | TestDistributionMechanics::test_argmax_alone_cannot_authorize |
| 16 | partial answers from provider | ERROR (missing answers) | TestFailClosed (jev malformed[resp3/4]) |
| 17 | off-contract selection (e.g. `banking` not in choices) | ERROR | TestFailClosed (jev malformed[resp2]) |

## Notes for the verifier

- The mock provider's fault channel (`_mock_fault`) is deliberately the SAME
  semantic fault list as the frozen directive §13 — the matrix above is
  testable without network.
- The Jev adapter's transport seam is injectable; tests 7–13 and 16–17 drive
  the real adapter code path with scripted transport responses.
- "Fail-open" would be: any row resolving to AUTO_ROUTE_CANDIDATE,
  SHADOW_ONLY-with-decision, or any execution-adjacent disposition. None
  exists in the policy code path for non-DECISION results (structural
  guard: `kind is not DECISION` short-circuits before thresholds).
