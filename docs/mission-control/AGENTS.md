# SP-MC3D-001 Mission Control DOX

## Purpose

Own the SintraPrime Cinematic Mission Control visualization track and its renderer-certification records.

## Ownership

- `SP-MC3D-001*` documents define Command Town architecture, graphics admission, and evidence state.
- Visualization is a consumer of governed state; it is never an authority source or agent runtime.

## Local Contracts

- **Observability should increase faster than authority.**
- 2D and 3D clients must remain downstream of the governed event/read-model boundary.
- Visualization must not execute commands, approve actions, grant authority, spawn agents, mutate PostgreSQL, or expand connector/financial/external-action permissions.
- Town Hall attendance and statements are observations; they are not approvals.
- Replay visualization must preserve `Replay ≠ Reality`.
- CR-2P, CR-3, deployment, and merge require separate authorization.

## Work Guidance

- Keep a 2D fallback and GPU-scalable quality tiers.
- Prefer procedural or provenance-cleared assets; do not add unlicensed third-party models or textures.
- Label projected/degraded/unknown data honestly; never fabricate live metrics.
- Keep interaction envelopes projection-only unless a separately governed command boundary is explicitly authorized.

## Verification

- `cd web && npm ci`
- `cd web && npm run lint`
- `cd web && npm run build`
- `cd web && npx playwright test tests/e2e/mission-control-town-3d.spec.ts --project=chromium`
- Browser admission must show a WebGL canvas and `NO EXECUTION AUTHORITY`, and must emit no POST/PUT/PATCH/DELETE request while loading or entering 3D.
- Target-host performance claims require measurements on that host; renderer existence is not performance certification.

## Child DOX Index

