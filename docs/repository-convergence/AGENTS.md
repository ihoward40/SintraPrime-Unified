# Repository Convergence DOX

## Purpose

Planning and evidence documents for the repository convergence program: per-increment snapshots of what exists on `main`, what exists only on open PR branches, and what remains unverified, so work advances one unified SintraPrime product. This folder holds documentation and planning artifacts only; it grants no runtime, merge, deployment, or production authority.

## Ownership

- The root `AGENTS.md` owns repository-wide workflow rules.
- Isiah Howard holds approval authority for any action beyond documentation.

## Local Contracts

- Documents are numbered increments (`increment-N-*.md`); each increment records its baseline commit SHA, generation date, scope, and verification results.
- Every material claim must carry evidence: file paths, commit SHAs, and issue/PR links.
- Status must distinguish: implemented on main; open PR branch only (head SHA recorded); referenced but not verified; not inspected.
- Inspection defaults to this repository only; external repositories are marked NOT INSPECTED unless explicitly examined.
- Increments are additive snapshots. Do not rewrite earlier increments to describe a newer baseline; extend with a new increment or correct in place with the correction noted.

## Work Guidance

- Prefer extending this increment series over creating parallel convergence plans elsewhere.
- Keep documents concise and operational; remove stale claims rather than layering history.

## Verification

- `python scripts/ci/validate_repository_claims.py` (CI lane `claims-validation`) must pass.

## Child DOX Index

None.
