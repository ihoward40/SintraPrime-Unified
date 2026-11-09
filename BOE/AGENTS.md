# BOE Domain Contract

## Purpose

- Define contracts for BOE executive-foundation program artifacts.
- Keep BOE modules aligned to decision enable/support/execute/preserve outcomes.

## Ownership

- BOE program owners and assigned implementation agents for BOE issues.

## Local Contracts

- `BOE/00-Program/BOE-001_Master_Implementation_Spec.md` is the root BOE Sprint 1 implementation authority.
- BOE module artifacts must preserve declared module order, dependency rules, and M1 acceptance gates from the master specification.
- BOE artifacts in this subtree must satisfy the standing engineering rule from issue #193.

## Work Guidance

- For BOE module additions, explicitly state scope, dependencies, acceptance criteria, and lifecycle state.
- Keep artifact naming aligned with the BOE build order (`00-Program`, `01-Decision-Register`, `02-Agent-Passports`, etc.).

## Verification

- Documentation-only updates in this subtree require a manual contract-consistency review against BOE-001 and issue #193 acceptance requirements.

## Child DOX Index

| Path | Scope | Controls |
|---|---|---|
| `BOE/00-Program/` | BOE program-level implementation contracts | BOE master specification and program lifecycle guidance |
