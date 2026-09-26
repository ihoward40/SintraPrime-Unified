# Prior Lane Supersession Record

SP-SYSTEM-ONE-DECISION-FABRIC-001 — R1-RECOVERY

## What the prior lane claimed

A lane identifying as `HERMES@admin` reported a completed R1 implementation:

- worktree `C:\Users\admin\SintraPrime-Unified-decision-fabric-r1-r2`
- branch `feat/sp-system-one-decision-fabric-001-r1-r2`
- baseline `be6f07cf`
- Artifact 0 with SHA-256 `61fc40b5255a83f5dcfc6ba3dab078252a973f2c5eb33330f729efce0e513855`
- implementation under `decision/`
- evidence under `artifacts/SP-SYSTEM-ONE-DECISION-FABRIC-001/R1/`
- test result `29/29 × 3`

These claims arrived as **pasted chat text**, never as tool outputs, files, or
verifiable artifacts in any environment accessible to the record lane.

## What the audit established

A read-only provenance reconciliation (2026-09-26, receipt
`agent-resolution-r1-provenance-reconciliation-implementat-f8fd` in the howar
fabric) measured the only accessible host (`IKESOLUTIONS\howar`):

- `C:\Users\admin` does not exist; the machine has a single user profile
- no decision-fabric worktree, branch, or worktree metadata exists
- no Artifact 0 file, no `r1-file-sha256.txt`, no R1 evidence directory exists
- the claimed Artifact 0 hash is not a git object and appears in no file,
  database, log, or session record on the host
- the Hermes session database contains no admin-lane session and no tool call
  that ever created the claimed artifacts

Verdict: `IMPLEMENTATION_EXISTENCE = NOT_PROVEN`; all five prior claims
`NOT_PROVEN`; `RECOVERY_REQUIRED = TRUE`.

## Rulings that follow

1. The prior lane is **SUPERSEDED / NOT_PROVEN**. It is not "a failed
   implementation" — there is no evidence an implementation ever existed.
2. The claimed Artifact 0 hash is a **historical reference to an unproven
   claim**. It is never used as a live provenance anchor. The recovery
   Artifact 0 (`artifact-0-provenance-freeze.md`, hash
   `9ad49f915cf5c6e3bb3a05a8b8abecbbb8833f0e4c4377d94e7c932c650685d4`) is the
   only live anchor for this lane.
3. The claimed `29/29 × 3` results are **not inherited**. The recovery lane's
   test count (49/49 conformance tests, run 4× deterministically) was produced
   on this host, reproducible by any verifier with the recorded command.
4. **No prior source code was reconstructed from chat.** Every file in this
   recovery worktree was written fresh in this session against the frozen
   directive, from baseline `be6f07cf`, with the full write history in this
   session's tool record.

## Purpose of this record

Future reviewers must not confuse the phantom lane with the recovery lane.
Citations of R1 progress before 2026-09-26 that reference `C:\Users\admin\...`
or the `61fc40b5…` hash reference an unproven claim, not an implementation.
