---
id: SP-R1-INDEPENDENT-VERIFICATION-001-RECEIPT
parent_task: SP-SYSTEM-ONE-DECISION-FABRIC-001-R1-RECOVERY-GOVERNED
verification_objective: "Independently verify the rebuilt R1 Decision Fabric (READ-ONLY)"
verifier: "HERMES@admin (acting as independent verifier per recovery-review handoff; no source/test changes made)"
target_worktree: "C:\\Users\\howar\\SintraPrime-Unified-r1-recovery-clean"
baseline_commit: "be6f07cf6c6ed0f9e0596aac548d7d1e7f74ca3b"
branch: "feat/sp-system-one-decision-fabric-001-r1-recovery-governed"
mode: READ-ONLY (no source/test edits, no commit/push/merge, no branch-protection change)
authority_delta: 0
disposition: VERIFIED (recovery candidate — from-spec rebuild; merge/deploy NOT authorized)
issued_utc: "2026-10-09T13:30:00Z"
---

# R1 Independent Verification Receipt — SP-R1-INDEPENDENT-VERIFICATION-001

## 1. Git baseline, worktree identity, dirty/untracked state
- `git rev-parse HEAD` → **be6f07cf6c6ed0f9e0596aac548d7d1e7f74ca3b** (matches frozen baseline).
- Branch → `feat/sp-system-one-decision-fabric-001-r1-recovery-governed`.
- `git status --porcelain` (filtered for tracked changes) → **no tracked-file modifications**; `decision/` and `artifacts/` are **untracked additions** only.
- `git worktree list | grep r1-recovery` → **exactly one** recovery worktree (the clean one); the 9 earlier sprawl worktrees are gone.
- **Conclusion:** baseline and identity VERIFIED; governed worktree is clean and isolated.

## 2. Independent file inventory + SHA-256 (23 reconstructed source files)
Enumerated with stdlib `hashlib` over `decision/` (excluding `__pycache__`). Count = **23**, matching the
architecture-note declared layout (11 implementation modules + `tests/test_r1_conformance.py` + `AGENTS.md` +
10 package `__init__.py`). No unexpected additions, no missing declared files. No secrets; no ambient network
(`httpx` confined to the injectable live transport in `providers/jev/provider.py`, guarded by a `RuntimeError`
when absent; `JEV_API_KEY` read from env only, never serialized into state/receipts).

```
ae405178d9ed0d9136c1b843b0614fc82492b8efd0a351c68a86f59160607819   2080  decision\AGENTS.md
400437d4e80d82a3f75f8b284889b2061fb979aab6044fd59772bf5b082e045a    237  decision\__init__.py
f2707dbac1da4b3385e27de0ed432296619ac9975899fc0530535435d7270c2f    135  decision\canonical\__init__.py
fb8c438668e0b1ee815f8a0652e031c78d64c92df5003b6aabe70c42075f645d   3727  decision\canonical\jcs.py
af67b395a46166ee0322a37f126a66800f362c9d680517b575bec66ea1c4e0ad    177  decision\contracts\__init__.py
0a2124f8c7c0146b3e999035dbb16752233958c724b7afedd1dc39ef5595fbd4   3665  decision\contracts\contracts.py
339be718a26a82a910d7c3e8fa6f3d63fbdfb4f49c7304011d6c3e1bd6404df4    178  decision\engine\__init__.py
21e32d7c110d2094550f202a76d5e2606f13a2fd7d15488de822c6ae3637a1da   1928  decision\engine\engine.py
d921393476b63b89d40cecdc20e972c534fabe82932e1b742e16d07ec1ba71df   2084  decision\engine\types.py
1f19ca765f38d040c9e1b5f6bbb69633a193be74b7e1f2cb117aa81de0f02078     70  decision\ledger\__init__.py
42d7e1fc303e10f0a41d4a05577187889e0a1a43ae46daeeadc13c95649f2019   2222  decision\ledger\ledger.py
f7a38797a09f2286aefe71541028f72830dbb23cfe70e0e232cd8a0eda835979    113  decision\policy\__init__.py
2aebfc5d4a191332252c7c8feaace41ebee93c6bc1329c56abfcd8a8c5caa55d   2034  decision\policy\policy.py
6d8f396aa37785bb450f17f3da9cddb9258ea608aca7dac4a2190cef9cb10979     67  decision\providers\__init__.py
f35448f2e66888c1ebd4f31eb551213ff1f52336b2d57067ea13d4ab93e6af7e    407  decision\providers\base.py
cf3cc27c4244fde8e6c5d0816193215a3e1d890fb4b6a2f34546a4674f178362   2616  decision\providers\config.py
ad6180fa492d73c577e265da043c28e7f620090f9c463d63d564092e741edeae   3223  decision\providers\mock.py
49949f64b0e33e6ea804124f712a668f47e831f92a8786a7b8796dd2bfd954f5    110  decision\providers\jev\__init__.py
538d46d2abeb04a91e0a63ff621d8fd3cd041a3898e219eb338f278af6b9b5a0   6700  decision\providers\jev\provider.py
67436ed4976e47bd010e6042dce9c7c5d6cb78f82125f5f4ed7d2bc38cbb49ac    135  decision\security\__init__.py
ece3380a53a99aabdc8b289b276bacc6bc7b58d5426e45e7e7554ad068275fde   2255  decision\security\untrusted.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855      0  decision\tests\__init__.py
92cb399138667708aecf53fb082a1906cdc2dfc4da343a433ba8f66562c36141  15572  decision\tests\test_r1_conformance.py
```

## 3. Comparison to frozen directive / addendum / surviving evidence
- The rebuild implements the directive's declared **7 invariants** and the **17-row failure matrix** as discrete,
  individually-named tests (see §5).
- **Documented difference:** the original section-20 manifest enumerated a **32-file** transfer set; that set
  included 9 **evidence/R1-RECOVERY docs** (architecture, canonicalization, provider-contract, failure-matrix,
  security-boundary, manifest, test-results, addendum, directive). Those are **preserved separately** in
  `…/R1-RECOVERY/` and are NOT implementation files. The implementation itself is **23 files** — this is correct,
  not a shortfall. The original *implementation* frozen bytes were unrecoverable on-host (all 20 R1-RECOVERY dirs
  failed their own 32/32 manifest), so a from-spec rebuild was the only provenance-correct path.
- No interface/signature contradicted the directive; vendor-neutral `DecisionProvider` Protocol is the sole
  extension point; Jev is an adapter only.

## 4. Independent execution of the 49-test suite
- Command (fresh `uv` ephemeral env, root conftest disabled so pre-existing repo errors are excluded):
  `uv run --no-project --with pytest --with pyyaml pytest --noconftest -o addopts="" -q decision/tests/test_r1_conformance.py`
- Environment: **python 3.14.7**, **pytest 8.x**, **pyyaml 6.0.3** (uv ephemeral; no project venv).
- Result: **49 passed, 0 failed in 0.26s** (deterministic; re-run reproduced identically).
- 2 pytest warnings (`Unknown config option: asyncio_mode`) originate from the **repo-root** pytest config and
  are pre-existing baseline noise, not introduced by R1.

## 5. Invariant / failure-matrix coverage (assertions inspected, not just names)
- I7 safe defaults+provenance: `TestConfigurationDefaults` (5). | I6 untrusted boundary: `TestUntrustedInputBoundary` (3).
- I5 abstain + fail-closed: `TestAbstention` (1) + `TestFailClosed` (12 mock faults → 6 UNAVAILABLE / 6 ERROR,
  all → `FALLBACK_HERMES`; + Jev transport-raise → UNAVAILABLE; + 5 malformed-Jev responses → ERROR).
- I4 full distribution+margin: `TestDistributionMechanics.test_margin_computation` (3).
- I3 contract hash: `TestContractHashing` (3). | I2 state_sha256: `TestCanonicalization` (6).
- I1 vocabulary/Noul boundary: `TestPrimitiveNormalization.test_noul_contained_in_adapter` (1).
- 17-row matrix: 12 rows covered directly by mock-fault tests; the Jev-adapter fault classes (transport
  timeout/connection/dns, 429/5xx, malformed JSON, unknown primitive, off-contract choice, schema mismatch) are
  additionally exercised by the independent probes in §6.
- **Honest limitation (matches review caveat #1):** the rebuilt tests *exercise* the behaviors via real assertions
  (I inspected them), but byte/assertion equivalence to the **lost original verifier's** tests cannot be proven
  because those original tests are gone. This is a residual risk, not a defect in the rebuild.

## 6. Independent adversarial probes (beyond the mirrored suite)
A throwaway script (not committed) imported `decision` fresh and confirmed:
- Canonicalization edges: `1→"1"`, `-0→"0"`, `0.1`, `1e+21`, `1e-7`, `0.000001`; UTF-16 ordering U+1D400 before
  U+FFFD; `1 == 1.0` hash equality. **OK.**
- Jev fail-closed (hand-built transports): DNS transport-raise → `UNAVAILABLE`; malformed JSON → `ERROR`; unknown
  primitive `oracle` → `ERROR`; off-contract choice `banking` → `ERROR`; policy maps every non-DECISION to
  `FALLBACK_HERMES`. **OK.**
- Ledger tamper: append then mutate a field → `verify()` flips `True→False`. **OK.**
- Engine e2e (shadow): `DECISION` result, disposition `FALLBACK_HERMES` (shadow default — no execution). **OK.**
- Noul confinement: `noul`/`Noul` present only in `providers/jev/provider.py` + the confinement tests; **zero**
  occurrences in the 10 core modules. **OK.**

## 7. Repaired-defect regression checks (review caveat: circular import + ledger DI)
- Circular import: `engine/__init__.py` no longer re-exports `engine.engine`; `import decision` and all submodules
  import cleanly (verified by probe + suite). **Fixed/regression-clean.**
- Ledger dependency-injection defect: engine uses `ledger if ledger is not None else Ledger()` — an empty `Ledger`
  is falsy via `__len__`, so the prior `ledger or Ledger()` silently replaced an injected ledger. Probe passes an
  injected ledger and confirms the entry lands in **that** object. **Fixed/regression-clean.**

## 8. Integration compatibility vs repository expectations
- `import decision` and all submodules resolve with only stdlib + optional `pyyaml` + guarded `httpx`; no
  dependency on the repo's missing `pydantic` (the source of the pre-existing baseline test-collection errors).
- R1 introduces **no new** import/collection failures at the repository level. Pre-existing baseline defects are
  out of R1 scope and were excluded via `--noconftest`/`-o addopts=""`, exactly as the suite is intended to run.
- Recommended (not blocking): the Principal should separately run the broader repo suite to confirm R1 does not
  regress pre-existing behavior outside its own package.

## 9. Discrepancy / unresolved item
- A fabric record `[2026-09-26T18:00] agent: R1 IV = PASS: 49/49x3 deterministic, 32/32 manifest, … 3 advisory
  findings` claims a **prior** independent verification with a **32/32 manifest**. That claim is **not
  reconcilable** with the present state: the present artifacts are a 23-file from-spec rebuild (the original
  frozen implementation bytes were confirmed lost), and no 32/32 manifest exists here. The claim is therefore
  recorded as **unverifiable / possibly-stale** and is explicitly NOT relied upon for this disposition.

## 10. Prohibited actions — compliance
None taken. No source/test edits, no commits, pushes, merges, deployments, or branch-protection changes. Only
inspection, hashing, isolated test execution, and this receipt were produced.

## 11. Disposition
**VERIFIED (recovery candidate).** The R1 Decision Fabric is independently reproducible (49/49 re-run),
self-consistent, and conforms to the directive's 7 invariants and 17-row failure matrix under independent
adversarial probing; the baseline is clean and the terminology/secret/network boundaries hold.

**Advisory findings (non-blocking, recorded for Principal):**
1. Reconstructed-test assertion equivalence to the lost original verifier's tests is unprovable (inherent).
2. Original frozen implementation bytes remain unrecoverable; this is a from-spec rebuild, not a byte restoration.
3. Pending fabric record claims a prior 32/32 PASS but is unreconcilable with current artifacts (unverifiable).
4. Broader-repo regression (outside `decision/`) not separately assessed.

**Authority boundary:** `AUTHORITY_DELTA = 0`. This verification does **NOT** authorize merge, deployment, or any
production action. Return to Principal for final authorization before any further step.
