# W4-5 CERTIFICATION — SP-W4-5-EXECUTOR-BINDING-001

**Base:** `f0d5a24eb5513f9c261e7b5256604d3b2990d4aa` (SP-MW-RECONCILE-001 seal)
**Commit:** `a589e60c8b61fe4f62f408e1e64be0a8ec4962b5` (5 files, +519/−29)
**Outcome: PASS / SEALED**

## Objective delivered

`W4-5 = bind browser executor through governed capability registry` — the
registry-to-browser-executor binding now exists as an enforced gate, not
declared data. Every governed browser action validates that its canonical
capability is bound to `GovernedBrowserExecutor` at the same registry
generation resolution used, BEFORE delegation/approval/mechanism contact.

## Three-way separation (implemented)

```text
CAPABILITY REGISTRY (W4-1/W4-2)  = WHAT a capability means
EXECUTOR BINDING  (W4-5, NEW)    = HOW it may be performed
AUTHORITY (delegation/approval)  = WHETHER a mission may do it
```

## Refusal matrix (all verified PASS)

```text
CAPABILITY_WITH_NO_EXECUTOR_BINDING  = REFUSE
WRONG_EXECUTOR_BINDING               = REFUSE
REGISTRY_GENERATION_MISMATCH         = REFUSE (resolution gen != binding-snapshot gen)
UNKNOWN_CAPABILITY / AMBIGUOUS_ALIAS / INVALID_FORMAT / DISABLED / DORMANT /
REGISTRY_NOT_TRUSTED                 = REFUSE (W4-2/W4-3 gates, unchanged)
CAPABILITY_NOT_DELEGATED             = REFUSE (pre-contact, exploding-factory proven)
PRE_GOVERNANCE_EXTERNAL_CONTACT      = FALSE (mechanism factory never called on refusal)
UNBOUND_BROWSER_CAPABILITIES         = 0 (all ACTIVE computer.browser.* bound to THIS executor)
ALIAS_FALLBACK                       = 0 (binding layer sees canonical ids only)
```

## Positive matrix (PASS)

```text
CANONICAL_CAPABILITY_BOUND_TO_BROWSER_EXECUTOR = PASS
VALID_GOVERNED_BROWSER_ACTION_EXECUTES         = PASS
ALIAS_AND_CANONICAL_SAME_EXECUTOR_BINDING      = PASS
EXECUTOR_BINDING_GENERATION_STABLE             = PASS
EXECUTOR_BINDING_GENERATION_DERIVED_FROM_SET   = PASS (changes iff bindings change)
```

## Architecture changes

1. `agent_runtime/executor_binding.py` (NEW, 161 lines) — HOW layer,
   executor-agnostic; future MCP/provider executors bind through the same API.
   `executor_binding_generation` = deterministic hash of the binding set +
   registry generation (W4-6 dependency, alongside manifest/capability/authority
   generations).
2. `GovernedBrowserExecutor._gate` — binding validation inserted between
   resolution and delegation: `REGISTERED != BINDABLE`. Executor also exposes
   `executor_binding_generation`.
3. `MissionRunner` routing — now BINDING-DRIVEN: the raw
   `computer.browser.*` string-prefix trust (last private vocabulary) is
   eliminated; capabilities bound to other/no executors refuse
   `EXECUTOR_NOT_WIRED` at routing time.
4. Static boundary guard updated to the W4-5 surface (portal, swarm_runtime,
   certify.py, .github, deployment remain banned).
5. Dead duplicated `CAPABILITY_NOT_DELEGATED` block in `_gate` removed.

## Certification matrix (all JUnit-counted, serial runs)

```text
W4-5 FOCUSED        = 11/11 (11/0/0/0)
W4-4 FOCUSED        = 15/15 (dependency gate: 26/0/0/0 combined with W4-5)
MISSION_WIRING + AGENT_RUNTIME = 317/317 (317/0/0/0)
SWARM CANONICAL     = 177/177 (177/0/0/0)
PORTAL              = 88 passed / 0 failed / 0 errors / 2 skipped (90/0/0/2, exit 0)
DEFAULT             = 563/563 (563/0/0/0)
RUFF                = PASS (agent_runtime + mission_wiring)
```

## Test-infra findings (environment class, not product defects)

TEST-INFRA-WORKTREE-COLLISION-001: `swarm_runtime/tests/test_acceptance_004_real.py`
spawns real AI-subprocess workers in real git worktrees. Two failure modes
observed, both environmental:
(a) teardown `git worktree remove` timing out under concurrent load (60s limit);
(b) worker B3 inheriting the worktree's detached-HEAD lineage instead of
producing its fixture commit (behavior-nondeterministic subprocess worker).
Product code unaffected — full serial rerun 177/177. Residue cleaned
(worktrees pruned, fixture branches deleted).

## Provenance

```text
W4_5_COMMIT_SHA = a589e60c8b61fe4f62f408e1e64be0a8ec4962b5
PARENT          = f0d5a24eb5513f9c261e7b5256604d3b2990d4aa
FILES_CHANGED   = 5
EVIDENCE LOCK   = artifacts/convergence/wave4/w4_5_evidence_lock.json
                  (per-file SHA-256 + JUnit receipt hashes)
POST_SEAL_CHECK = exit 0 (mission_wiring + W4-4 + W4-3 focused on sealed tree)
```

## Controlling state after W4-5

```text
W4-1 = 51974cca · W4-2 = 98bc9b70 · W4-3 = 6d5214f2
W4-4 = f9c7faae (supersedes 05885aa2)
SP-MW-RECONCILE-001 = f0d5a24e
W4-5 = a589e60c  ← current Wave-4 head

W4-6..W4-9 = NOT AUTHORIZED
PUSH / PR / MERGE / DEPLOYMENT = NOT AUTHORIZED
SP-DEPLOY-TARGET-001 / ZD-005 = NOT OPENED
```

STOP — sealed for Principal review. No push/PR/merge/deploy performed.
