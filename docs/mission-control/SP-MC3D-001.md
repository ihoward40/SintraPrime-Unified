# SP-MC3D-001 — SintraPrime Command Town

**Status:** IMPLEMENTATION OPEN — VISUALIZATION SLICE 1  
**Authority:** Principal-authorized visualization work only.  
**Explicitly excluded:** CR-2P, CR-3, deployment, merge, production authority expansion.

## Doctrine

> Observability should increase faster than authority.

> Agents may become more capable without becoming more authoritative.

## Slice 1

The first vertical slice adds a cinematic Command Town to the existing Mission Control frontend. It is a consumer of existing read-only Mission Control projections and does not introduce an execution API, approval bypass, agent-spawn authority, connector grant, persistence migration, or deployment surface.

The town preserves the requested social/spatial concept while placing the Command Citadel and Constitutional Chamber inside it. Town Hall is a first-class district for Principal-led council sessions.

### Districts

- Command Citadel — Principal command deck
- Town Hall — council and agent assembly
- Constitutional Chamber — authority and restraint
- Agent Quarter — workers and directors
- Evidence Vault — receipts and provenance
- Build Lab — engineering
- Financial District — cost/treasury observatory
- Creative Studio — media/design

## Data boundary

Slice 1 consumes:
- Mission Control summary
- Principal Brief
- Sigma/cancellation gate status

Unavailable data renders as unknown/unavailable. The visualization must not invent operational state.

## Graphics strategy

Slice 1 uses the existing React, Framer Motion, and CSS stack to avoid an unverified dependency/lockfile mutation. A future separately certified graphics gate may add WebGL/Three.js/React Three Fiber, PBR assets, spatial audio, avatar rigs, weather, day/night lighting, and scalable quality presets.

The 2D Mission Control remains a supported fallback and the 3D client remains non-authoritative.
