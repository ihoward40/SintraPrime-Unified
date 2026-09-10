# SP-MW-PUBLISH-READINESS-001 — Mission-Wiring Publication Readiness

**Outcome: B — MISSION_WIRING_REQUIRES_CORRECTIVE_RECONCILIATION_BEFORE_PUBLICATION**
**Publication recommendation: CORRECTION_REQUIRED** · **W4-5: BLOCKED_BY_RECONCILIATION**

Read-only lane. No production code modified. No push/PR/merge/deploy. Machine-readable twin: `SP-MW-PUBLISH-READINESS-001.json`.

## A. Lineage (Git-proven, not memory)

```text
origin/main            = 79deec881544a80105e0b45663740ad0f0fccf17
W4 head                = 05885aa2ae4791e1a5fabca9aa4d4941fcf4050d  (branch feat/wave4-w1-registry-install)
merge-base(HEAD, main) = 79deec88          remote commits not local = 0
local not on main      = 51974cca -> 98bc9b70 -> 6d5214f2 -> 05885aa2   (exact expected chain)
mission_wiring/ on main = ABSENT (git ls-tree)   on W4 head = ABSENT
ZD-001 source           = SintraPrime-Unified-sp-zero-dollar-wiring @ cc23293e; mission_wiring/ is UNTRACKED there (never committed anywhere)
```

## B–C. Inventory and minimal subset

19 files inventoried with SHA-256 (`zd001_mission_wiring_inventory.json`). Minimal production subset = **6 files**:

| File | Role | Class | Publish |
|---|---|---|---|
| `envelope.py` | MissionEnvelope carrier; refuses self-declared approval on consequential types | REQUIRED_SECURITY | YES (after C2) |
| `browser_executor.py` | GovernedBrowserExecutor — the governed boundary | REQUIRED_RUNTIME | YES (after C1, C4, C5) |
| `receipt.py` | MissionReceipt + event taxonomy | REQUIRED_EVIDENCE | YES (after C2) |
| `mission_runner.py` | coordinator over canonical `agent_runtime.DelegationAuthority` | REQUIRED_RUNTIME | MAYBE (raw prefix checks -> resolver) |
| `approval_service.py` | approval binding issue/validate/consume | REQUIRED_SECURITY | MAYBE (must be WIRED, not parallel) |
| `__init__.py` | package | — | YES |

Excluded: `origin_adapters.py` (not needed for browser boundary), `tests/negative_outcome.py` (already promoted to `agent_runtime/tests` in W4-2), `test_zd3_harness_integrity.py`, `test_zd3_registry_approval_attacks.py` (ZD evidence-lock tests bound to cc23293e).

Replaced by Wave 4: private `BROWSER_CAPABILITIES` map → registry + resolver; raw membership checks → `resolve_capability`; raw-capability hashing → W4-4 `canonicalize_capability_for_hash`.

## D. Dependency graph

All `agent_runtime` dependencies (`canonical`, `manifest`, `delegation`, `registry`) are present on the W4 lineage. `operator.BrowserController` is injected, not imported. No dependency on portal, ZD artifacts, or `mission_wiring.origin_adapters` from the browser path.

## E. Authority overlap — `SECOND_AUTHORITY_KERNEL_RISK = LOW`

`mission_runner` is an **adapter** over canonical `DelegationAuthority` (grants nothing; calls `issue(require_approval=True)`). No competing kernel.

**Finding (carrier-trust gap):** `browser_executor._gate` trusts `envelope.approval_state ∈ {GRANTED, CONSUMED}` — a carrier field — and `mission_runner` passes `approval_reference=envelope.delegation_id` (caller-supplied). `AuthorityApprovalService` (full mission/actor/tenant/capability/resource binding, expiry, exactly-once) exists but is **unwired** (tests only). Wave-3 `DelegationAuthority.consume_approval` gives exactly-once but not binding validation. Publishing `approval_service.py` unwired would create a dormant parallel component; the correction is to wire **one** validator into the pre-execution gate.

## F. Capability compatibility — `NEEDS_RECONCILIATION` (mechanical)

```text
registry covers 10/10 browser ids; side-effect classes 10/10 identical; ALIAS_CONFLICTS = 0; REGISTRY_CONFLICTS = 0
MISSION_WIRING_RAW_CAPABILITY_CHECKS       = 4   (browser_executor._gate x2, mission_runner startswith x2)
MISSION_WIRING_PRIVATE_CAPABILITY_REGISTRIES = 1 (BROWSER_CAPABILITIES)
MISSION_WIRING_ALIAS_BLIND_CHECKS          = 4
MISSION_WIRING_CAPABILITY_HASHING_SITES    = 2   (envelope.hash_payload, receipt.hash_payload — RAW strings)
```

## G. Browser governance boundary — `NEEDS_RECONCILIATION`

```text
PRE_GOVERNANCE_EXTERNAL_CONTACT = FALSE inside GovernedBrowserExecutor (AST: _gate precedes every mechanism call; __init__ launches nothing)
CAVEAT (MEDIUM): operator.BrowserController.__init__ launches Playwright/requests at construction. If constructed eagerly, a browser PROCESS exists pre-governance (no navigation). Fix: lazy/factory injection.
GATE ORDER = UNKNOWN_CAPABILITY -> CAPABILITY_NOT_DELEGATED -> APPROVAL_REQUIRED -> SIDE_EFFECT_CLASS_EXCEEDS_MISSION -> BUDGET_EXHAUSTED -> URL_OUT_OF_SCOPE -> execute   (matches directive)
APPROVAL_BINDING = WEAK (see E)      SIDE_EFFECT_BINDING = PRESENT      URL_SCOPE_BINDING = PRESENT (empty allowlist = deny-all)
BUDGET_BINDING = PRESENT but NEVER DECREMENTED (max_actions checked > 0, not consumed) — FINDING
RECONCILIATION_SUPPORT = ABSENT as runtime state (test doctrine only)
Executor methods implemented: navigate, extract_text, screenshot, fill_form, submit_form. Missing: read, interact, upload, download, financial_submit.
GAP: credential entry / 2FA / captcha not modeled — would fall under form_fill (LOCAL_REVERSIBLE), under-classifying secret handling. Needs its own class + credential broker.
```

## H. Receipt convergence — `MISSION_RECEIPT_CONVERGENCE_REQUIRED = TRUE`

Same hash primitive (`canonical_hash`) — no algorithm duplication. Two models at different scopes (`AgentRuntimeReceipt` agent-level vs `MissionReceipt` mission-level) is legitimate layering **if** MissionReceipt references agent receipt hashes and routes capability identity through the W4-4 boundary instead of hashing raw strings.

## J. Exactly-once — `PARTIAL`

Present: single attempt, no retry loop, bounded FAILED receipt on crash, in-process exactly-once approval consumption. Absent: durable `UNKNOWN_EXTERNAL_STATE`, ReconciliationQueue, cross-process approval persistence (known Wave-5 deferral — left deferred).

## K. Test evidence (DERIVATIVE — not production certification)

| Run | Result |
|---|---|
| ZD-001 worktree, full suite @ cc23293e | 117/117 PASS |
| **Byte-exact overlay onto W4 head 05885aa2** (isolated worktree `SintraPrime-Unified-mw-overlay-analysis`) | 107/117; 6 FAIL + 4 ERROR |
| Failure classification | all 10 = `STALE_EXPECTATION` in the two ZD evidence-lock test files (assert cc23293e head, PR#302 frozen, 23-alias vocabulary, zd002 artifact paths) |
| **Production-module tests on W4 lineage** | **87/87 PASS — 0 product-module failures** |

The certified ZD-001 modules import cleanly and pass against the Wave-4 `agent_runtime` without modification. Compatibility is not the blocker; the corrections below are.

## L. Corrections required before publication

```text
C1  browser_executor: replace private BROWSER_CAPABILITIES map with capability_resolver lookup (vocabulary already identical)
C2  envelope + receipt: route capability identity through W4-4 canonicalize_capability_for_hash (no raw strings in security hashes)
C3  wire ONE approval validator into the executor pre-gate; stop trusting envelope.approval_state as proof
C4  lazy/factory BrowserController injection — no browser process before first gated call
C5  enforce/decrement max_actions per gated action
C6  drop ZD evidence-lock tests; use agent_runtime/tests/negative_outcome.py
DEFER  credential/2FA/captcha capability class; durable UNKNOWN_EXTERNAL_STATE + ReconciliationQueue; origin_adapters
```

None of these alter Wave-3 architecture, the registry, or canonical hashing; all are mechanical alignments to W4-1..W4-4. Recommended next lane: `SP-MW-RECONCILE-001` (implement C1–C6 in an isolated worktree on 05885aa2, certify, then Principal publication decision) — **not authorized by this report**.
