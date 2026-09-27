# BOE-001 Master Implementation Specification

## Status

`DRAFT — IMPLEMENTATION READY FOR SPRINT 1 EXECUTION`

## Program Scope

BOE-001 establishes the Executive Foundation required to run repeatable, evidence-based institutional decision cycles for the Howard Life Institution.

### In Scope (Sprint 1)

1. Decision enablement and capture (Decision Register standard, schema, and first record).
2. Agent operating accountability (Agent Passport standard and first five completed passports).
3. Portfolio-level execution visibility (Portfolio Registry).
4. Weekly governance cadence (Weekly Life Board packet and first board run).
5. M1 acceptance review and activation gate.

### Out of Scope (until Sprint 1 completion)

- Executive Dashboard
- Confidence Ledger
- Operational History
- Board Intelligence

### Standing Engineering Rule

Every BOE artifact must either enable a decision, support a decision, execute a decision, or preserve a decision. If it does none of those, it does not belong in BOE.

## Module Map

| Order | Module | Artifact(s) | Purpose | Primary Output |
|---|---|---|---|---|
| 1 | Program Foundation | `BOE/00-Program/BOE-001_Master_Implementation_Spec.md` | Defines BOE operating contract and delivery order | Authoritative BOE implementation plan |
| 2 | Decision Register | `BOE/01-Decision-Register/DRS-001.md`, Decision Register schema, `DR-0001` | Make decisions durable, traceable, and replayable | Operational register + first institutional decision |
| 3 | Agent Passports | `BOE/02-Agent-Passports/AOP-001.md`, Agent Passport template, five passports | Define and evidence agent authority, responsibility, and operating constraints | Five completed role-bound passports |
| 4 | Portfolio Registry | Portfolio Registry artifact | Track institutional assets, ownership, and operating state | Established portfolio baseline |
| 5 | Weekly Life Board | Weekly Life Board packet and first board session record | Run recurring executive governance loop | First board packet + held board |
| 6 | Milestone Gate | M1 acceptance review record | Verify BOE minimum foundation is operational before Active state | M1 pass/fail decision with evidence |

## Dependency Graph

1. Program Foundation has no upstream BOE dependency and must be authored first.
2. Decision Register standard (`DRS-001`) must exist before register schema finalization and `DR-0001` entry.
3. Agent Passport template depends on `AOP-001`; completed passports depend on both.
4. Portfolio Registry and Weekly Life Board require Decision Register and Agent Passports as governance inputs.
5. M1 acceptance review depends on all Sprint 1 outputs being operational and evidenced.

```text
BOE-001 Master Spec
  ├── DRS-001 ──> Decision Register Schema ──> DR-0001
  ├── AOP-001 ──> Agent Passport Template ──> 5 Agent Passports
  ├── Portfolio Registry
  └── Weekly Life Board Packet

M1 Acceptance Review depends on all branches above.
```

## Sprint 1 Milestones

### M0 — Foundation Initialized

- BOE-001 Master Implementation Spec is approved and published.
- Sprint order, dependencies, and acceptance rules are fixed.

### M1 — Executive Foundation Operational

- Decision Register operational.
- Five Agent Passports completed.
- Portfolio Registry established.
- First Weekly Life Board held.
- `DR-0001` recorded.
- First institutional asset created.

## Acceptance Criteria

A BOE module may not advance to **Active** until all of the following are true:

1. Required artifacts for the module are authored and versioned.
2. Required operational event(s) for the module have occurred.
3. Evidence is attached to the event(s) and artifact state.
4. Dependencies listed in this specification are satisfied.
5. Review authority records an explicit pass decision.

### M1 Gate (Program-Level)

M1 is accepted only when every required checkpoint in the M1 milestone is satisfied and evidenced.

## Lifecycle Guidance

Each BOE module follows the lifecycle below:

1. **Draft** — Problem definition and contract language are authored.
2. **Specified** — Scope, dependencies, and acceptance criteria are complete.
3. **Operational** — Module artifacts exist and are in active use.
4. **Verified** — Evidence confirms module outputs and dependency compliance.
5. **Active** — Module is approved for routine institutional use.
6. **Revised** — Any material change re-enters Draft/Specified and is re-verified before returning to Active.

## Governance and Change Control

- This document is the root implementation contract for BOE Sprint 1.
- Any change to module order, dependencies, or M1 acceptance criteria requires a revision entry in this file and downstream artifact alignment.
- Downstream BOE artifacts must reference this specification as program authority.

## Execution Checklist

- [ ] Publish `DRS-001`.
- [ ] Implement Decision Register schema.
- [ ] Record `DR-0001`.
- [ ] Publish `AOP-001`.
- [ ] Publish Agent Passport template.
- [ ] Complete five Agent Passports.
- [ ] Establish Portfolio Registry.
- [ ] Produce Weekly Life Board packet.
- [ ] Hold first Weekly Life Board.
- [ ] Record first institutional asset.
- [ ] Run and record M1 acceptance review.
