# registry — Registries and Release-Surface Manifest

## Purpose

Holds machine-readable and human-readable registries: agent registry entries (`agents/`), the capability registry (`capabilities/`), CDR records (`cdr/`), and the single release-surface manifest `release_surface_manifest.json` (SP-RELEASE-SURFACE-MANIFEST-001).

## Ownership

- Owns `registry/**` content and `release_surface_manifest.json`.
- Owns the manifest validator `scripts/ci/validate_release_surface_manifest.py` and its tests `scripts/ci/tests/test_validate_release_surface_manifest.py` (`scripts/ci/` has no AGENTS.md of its own).
- Does not own agent runtime authority (`agent_runtime/`), Agent Commons, or any module the manifest describes.

## Local Contracts

- `release_surface_manifest.json` is the one release-surface inventory. Do not add a parallel module inventory or agent registry; generate any other view from it.
- Coverage is `PARTIAL`: mission-control, agents, hermes, ike-bot, agent-commons only. The validator rejects any other coverage status; do not claim full WS-00 coverage until that is ratified.
- Keep source presence, canonical status and runtime evidence separate fields. `canonical_status` records the ownership decision, never implies it; competing implementations stay `unresolved` (Agent Commons PR #244 and #346).
- `on-main` entries: every path, entrypoint, test, owner and ci_lane file must exist with exact case in both the `baseline_ref` git tree and the checkout, and `verified_ref` must equal `baseline_ref`. Do not weaken exact-case checks (git tracks both `apps/SintraPrime` and `apps/sintraprime`).
- `branch-only` entries record every candidate's PR, branch and full head SHA; `external-not-inspected` entries have `source_presence: unknown`.
- Unevidenced WS-00 metadata is written `UNKNOWN`, never guessed.
- When the baseline advances, change `baseline_ref`/`verified_ref` and re-verify paths in one commit.

## Work Guidance

- Validator is standard-library Python plus `git`; no network access and no fallback to HEAD when the baseline commit is missing.
- CI job `claims-validation` checks out full history (`fetch-depth: 0`) so the baseline commit is available.

## Verification

- `python scripts/ci/validate_release_surface_manifest.py`
- `python -m pytest scripts/ci/tests/test_validate_release_surface_manifest.py -q`
- `python scripts/ci/validate_repository_claims.py`

## Child DOX Index

*(None.)*
