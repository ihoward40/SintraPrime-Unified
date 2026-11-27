# Supersession Notice — SP-SYSTEM-ONE-DECISION-FABRIC-001 R1-RECOVERY (PR #368)

- Notice id: SP-R1-EVIDENCE-CONSOLIDATION-006
- Created: 2026-10-10
- Type: governance notice (new document; historical receipts are NOT modified)
- authority_delta: 0

## Disposition

**SUPERSEDED — evidence retained; recovery code not integrated.**

- PR #368 (branch `feat/sp-system-one-decision-fabric-001-r1-recovery-governed`,
  commit `fd0bf23bea517c8cd6043abb3ba3922775103b6c`) proposed a from-spec rebuild of
  the R1 Decision Fabric. After independent compatibility analysis
  (SP-R1-MAINLINE-RECOVERY-COMPATIBILITY-003) and canonicalization revalidation
  (SP-R1-CANONICALIZATION-REVALIDATION-004), the recovery code is **NOT recommended
  for integration**.
- The **authoritative** R1 implementation is the **mainline** at frozen SHA
  `051e2594c67a805ceacc66ea2a6fc6db9c0bc793` (Agent-0 CI baseline, PR #312
  `05e6182b`; 57/57 conformance semantics + R2 shadow calibration).
- This notice records the governance disposition. It does **not** modify any
  historical receipt; the original documents are preserved byte-for-byte.

## Why superseded (evidence-backed)

- Mainline already implements a more complete R1: full evidence-bearing ledger
  receipt, 4-level `Risk`, richer provider validation, untrusted trust-segmentation
  model, `coerce.py`, and R2 shadow-calibration scaffolding — all CI-green.
- The recovery rebuild is a smaller, parallel implementation with an independently
  confirmed defect (JCS number formatting: 2 ECMAScript mismatches — `0.000001234`
  and `0.30000000000000004`) and an incompatible import layout (absolute
  `from decision.…` vs mainline's relative `from ..canonical…`).
- No material code value present in the recovery is missing from mainline.
  (YAML contract parsing was considered and DEFERRED — no established operational
  need for the added dependency.)

## Evidence preserved (byte-for-byte, unmodified)

The five recovery-only documents are preserved as historical evidence of this
recovery lane. They are **not** authoritative for the live R1 implementation
(except the two frozen spec documents, which are authoritative as the spec source):

| Document | SHA-256 | Class |
|---|---|---|
| R1-DIRECTIVE-FROZEN.md | 12de45a93e0e9efe9fd65e584a8ada07947b6ca790394879a59e0d17e4b5e6bc | Spec (authoritative) |
| R1-CONTROL-STATE-ADDENDUM-FROZEN.md | 5bac511f0d208536a35e53b01439a1105797df85253ac188c744dabdee46081f | Spec (authoritative) |
| cleanup-receipt-2026-10-09.md | 4abaa06bf604c0fd616d47c6968f54f3818012d3e7e6f486234d674d00ee138a | Receipt (superseded lane) |
| r1-rebuild-receipt-2026-10-09.md | a32a725d70160fcc8cfb953371c030abad7cdbeba0804e899357cc958c5b40f1 | Receipt (superseded lane) |
| r1-verification-receipt-SP-R1-INDEPENDENT-VERIFICATION-001.md | 8729ed21051a72519e93f3080b85fae780394b207dec11f1d4f6199aee18cebd | Receipt (superseded lane) |

## Artifact-0 hash discrepancy (documented, NOT rewritten)

- The historical `r1-rebuild-receipt-2026-10-09.md` references artifact-0 hash
  `9ad49f915cf5c6e3bb3a05a8b8abecbbb8833f0e4c4377d94e7c932c650685d4`. This is the
  **mainline / pruned-lane anchor**: the actual mainline artifact-0 file at frozen
  SHA `051e2594` hashes to `9ad49f91…` (4590 B), matching main's manifest.
- The recovery branch's own `artifact-0-provenance-freeze.md` hashes to
  `85e69126630df5cd1e00811ccb31b11e48182b1923c3a760d331adea3a457534` — a different,
  byte-distinct artifact written in this lane.
- This discrepancy is recorded here for transparency. The historical receipts are
  left unmodified: altering them would change their SHA-256 and break byte-for-byte
  preservation.

## Line-ending provenance — frozen directives (Option A)

The two frozen directives are preserved as their original CRLF bytes. Git's
`core.autocrlf=true` normalized them to LF when committed in the recovery branch
(`fd0bf23`). Three distinct facts must not be conflated:

1. **Original evidence bytes (authoritative):** CRLF, matching the frozen SHA-256
   records — `R1-DIRECTIVE-FROZEN.md` `12de45a9…e6bc`,
   `R1-CONTROL-STATE-ADDENDUM-FROZEN.md` `5bac511f…081f`. These are the bytes
   preserved in this evidence package (Option A).
2. **Committed representations (`fd0bf23`):** LF, produced by Git normalization —
   `353bae18…c8a2` and `b3bfd4da…ed9a`. The recovery commit does **not** contain
   byte-identical frozen artifacts; it contains line-ending-normalized copies.
3. **Semantic equivalence:** the CRLF and LF forms are textually equivalent after
   line-ending normalization (both LF-normalize to `353bae18…`/`b3bfd4da…`), but
   semantic equivalence is **not** a substitute for byte-level provenance.

The recovery commit is therefore not characterized as corrupted — its content is
correct — but it is not byte-identical to the frozen sources for these two files.
This evidence package preserves the original CRLF bytes.

## Authority boundary

`AUTHORITY_DELTA = 0`. No merge, deployment, or runtime activation. PR #368 remains
**OPEN / DRAFT** pending the Principal's separate closure authorization. This notice
is preparation only; it has not been committed, pushed, or published.
