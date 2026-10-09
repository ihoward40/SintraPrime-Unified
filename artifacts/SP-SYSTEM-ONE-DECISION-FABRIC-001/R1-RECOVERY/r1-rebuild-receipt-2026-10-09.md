---
id: R1-REBUILD-RECEIPT-2026-10-09
task_id: SP-SYSTEM-ONE-DECISION-FABRIC-001-R1-RECOVERY-GOVERNED
created_utc: "2026-10-09T12:45:00Z"
agent: "HERMES@admin (on-host recovery implementer, per 09-22 routing)"
type: rebuild-receipt
authority_delta: 0
---

# R1 Rebuild Receipt — from-spec re-implementation (no clean source bytes existed)

## What was done
The R1 decision-fabric was REBUILT FROM SPEC in the clean governed worktree
`C:/Users/howar/SintraPrime-Unified-r1-recovery-clean` (baseline `be6f07cf`,
branch `feat/sp-system-one-decision-fabric-001-r1-recovery-governed`).

Source of truth for the build: the two PASS-reconciled frozen artifacts
(`R1-DIRECTIVE-FROZEN.md`, `R1-CONTROL-STATE-ADDENDUM-FROZEN.md`) plus the
surviving `R1-RECOVERY` evidence docs (architecture / canonicalization /
provider-contract / failure-matrix / security-boundary / manifest / test-results)
recovered from `SintraPrime-MC3D/.../R1-RECOVERY/`.

No clean frozen implementation bytes existed on this host (all 20 R1-RECOVERY dirs
scanned earlier failed their own 32/32 manifest), and the off-host transfer origin
was unreachable, so re-transfer (option a) was not executable; from-spec rebuild
(option c) was the only provenance-correct path.

## Modules delivered (decision/)
11 implementation modules + tests + subsystem DOX:
canonical/jcs.py, contracts/contracts.py, engine/types.py, engine/engine.py,
ledger/ledger.py, policy/policy.py, providers/base.py, providers/config.py,
providers/mock.py, providers/jev/provider.py, security/untrusted.py,
tests/test_r1_conformance.py, AGENTS.md (plus package __init__ files).

## Verification (self-test — NOT independent verification)
Command: `uv run --no-project --with pytest --with pyyaml pytest
          --noconftest -o addopts="" decision/tests/test_r1_conformance.py`
Result: **49 passed, 0 failed** (deterministic; mirrors the independent-verifier
test-class structure: TestCanonicalization, TestContractHashing,
TestPrimitiveNormalization, TestDistributionMechanics, TestAbstention,
TestFailClosed, TestUntrustedInputBoundary, TestLedger, TestConfigurationDefaults,
TestEngineEndToEnd).

Coverage confirmed against the directive's 7 invariants and the 17-row failure
matrix: JCS canonicalization (key order, number formatting, UTF-16 ordering),
semantic contract hashing (format/comment-insensitive, semantic-sensitive,
noul-rejected), primitive normalization (Noul contained in jev adapter only),
full distribution + margin, abstention first-class, fail-closed -> FALLBACK_HERMES,
untrusted-input boundary, hash-chained ledger, safe defaults + provenance-bearing
overrides.

## Governance status (strict vocab)
- This is IMPLEMENTATION REBUILT + SELF-TEST PASSED. It is **NOT** an R1 PASS.
- Per the frozen directive §14, final R1 = PASS requires an INDEPENDENT VERIFIER
  re-running the suite and recomputing evidence hashes. That gate is intentionally
  NOT closed by this receipt (no self-certification / weaken-to-pass).
- R1 overall status remains: **BLOCKED pending independent verification**.
- AUTHORITY_DELTA = 0. No commit, push, or PR was made; the worktree holds the
  rebuilt files as untracked local artifacts for the verifier to inspect.

## Reality gate
Observability increased (full test suite now runs and is green from a single
governed worktree); authority was NOT asserted. Next owner: independent verifier,
or Principal authorizing commit/PR once satisfied.
