# SP-MC3D-001 — Full 3D World Architecture

**State:** IMPLEMENTATION IN PROGRESS  
**Parent:** SP-MC3D-001 Command Town  
**Closed boundaries:** CR-2P, CR-3, deployment, merge, PostgreSQL, new agent authority.

## Objective

Evolve Command Town from its 2.5D fallback into a persistent, navigable 3D
operator projection with PBR-ready districts, streets, agent presence,
day/night environment, volumetric-ready atmosphere, animated governed data
flows, Town Hall sessions, walk-up inspection, spatial activity, and scalable
graphics presets.

## Non-negotiable authority rule

The 3D client is a **projection and interaction shell**, not an executor.

Walk-up interaction can inspect an agent or district, request a brief, open
evidence, or propose a Town Hall topic. It cannot execute a task, approve a
proposal, grant a connector, grant authority, hire/spawn an agent, merge code,
deploy software, or mutate PostgreSQL.

Town Hall attendance is not authority. A statement is not an approval. A
proposal is not an approval. A visual animation is not evidence of execution.

## Rendering tiers

| Tier | Target | Expensive shadows | Volumetrics | Reflections | Avatar cap |
|---|---|---:|---:|---:|---:|
| Lite | GT 1030 / legacy GPU | off | off | off | 16 |
| Balanced | modern midrange | on | off | off | 48 |
| Cinematic | RTX-class | on | on | on | 128 |

The existing CSS/React Command Town remains the fail-safe fallback.

## World model

Renderer-neutral contracts live under
`web/src/pages/mission-control/three/` so governed state is not coupled to
a graphics engine. The renderer consumes that model.

The model includes:
- districts and world-space transforms;
- agent presence and state;
- Town Hall sessions;
- spatial mission/evidence/proposal/approval/receipt/incident flows;
- time-of-day and environment state;
- quality preset limits.

## Renderer admission gate

A WebGL/PBR implementation may be admitted only with a synchronized dependency
and lockfile change plus successful type-check, production build, and browser
smoke evidence. Until that gate executes, the renderer-neutral world contract
is implemented while the 2.5D town remains the operational visualization.

## Doctrine

**Observability should increase faster than authority.**

**Agents may become more capable without becoming more authoritative.**
