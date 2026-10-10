# R1-RECOVERY Evidence Inventory — SP-SYSTEM-ONE-DECISION-FABRIC-001

- Inventory id: SP-R1-EVIDENCE-CONSOLIDATION-006
- Created: 2026-10-10
- Purpose: consolidated inventory of the recovery-lane evidence preserved alongside
  the authoritative mainline R1. Companion to `r1-supersession-notice-…`.
- authority_delta: 0

## Preserved documents (byte-for-byte, SHA-256 verified)

| Document | SHA-256 | Class | Role |
|---|---|---|---|
| R1-DIRECTIVE-FROZEN.md | 12de45a93e0e9efe9fd65e584a8ada07947b6ca790394879a59e0d17e4b5e6bc | Spec (authoritative) | Frozen R1 directive source |
| R1-CONTROL-STATE-ADDENDUM-FROZEN.md | 5bac511f0d208536a35e53b01439a1105797df85253ac188c744dabdee46081f | Spec (authoritative) | Control-state addendum |
| cleanup-receipt-2026-10-09.md | 4abaa06bf604c0fd616d47c6968f54f3818012d3e7e6f486234d674d00ee138a | Receipt (superseded lane) | Worktree prune record |
| r1-rebuild-receipt-2026-10-09.md | a32a725d70160fcc8cfb953371c030abad7cdbeba0804e899357cc958c5b40f1 | Receipt (superseded lane) | From-spec rebuild record |
| r1-verification-receipt-SP-R1-INDEPENDENT-VERIFICATION-001.md | 8729ed21051a72519e93f3080b85fae780394b207dec11f1d4f6199aee18cebd | Receipt (superseded lane) | Independent verification |
| r1-supersession-notice-SP-R1-EVIDENCE-CONSOLIDATION-006.md | (see companion; new doc) | Notice (new) | Governance supersession record |

## Provenance anchors

- Recovery commit (PR #368): `fd0bf23bea517c8cd6043abb3ba3922775103b6c`.
- Authoritative mainline R1: `051e2594c67a805ceacc66ea2a6fc6db9c0bc793`
  (PR #312 `05e6182b`; 57/57 conformance + R2 shadow calibration).
- Recovery branch artifact-0 (this lane's file): `85e69126630df5cd1e00811ccb31b11e48182b1923c3a760d331adea3a457534`.
- Mainline artifact-0 anchor (referenced by the rebuild receipt, matches main's
  manifest): `9ad49f915cf5c6e3bb3a05a8b8abecbbb8833f0e4c4377d94e7c932c650685d4`.

## Disposition summary

- Spec documents (directive, addendum): **PRESERVE** (authoritative spec source).
- Receipts (cleanup, rebuild, verification): **PRESERVE** (historical, superseded lane).
- Recovery code (`decision/`, 23 files): **SUPERSEDED** (not integrated).
- YAML contract parsing: **DEFERRED** (no established operational need).
- Mainline JCS repair: **NOT WARRANTED** (mainline is RFC 8785-conformant; the
  defect is recovery-only).

## Boundary

Preparation only. No commit, push, PR creation, or PR #368 closure. `AUTHORITY_DELTA = 0`.
