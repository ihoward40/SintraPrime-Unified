# BOE — Board of Executive Operations DOX Contract

## Purpose

This subtree defines the minimum operational foundation for repeatable, evidence-based decision cycles in Howard Life Institution.

## Ownership

- Executive operations owner: Isiah Howard
- Implementation owner: repository contributors delivering BOE artifacts
- Root `AGENTS.md` controls repository-wide rules

## Local Contracts

- Every BOE artifact MUST directly enable, support, execute, or preserve a decision.
- Sprint 1 build order MUST be honored for BOE baseline delivery.
- Decision records in `01-Decision-Register/Decision_Register.jsonl` are append-only.
- Agent Passports MUST use the template defined by `AOP-001.md`.
- M1 acceptance requires all BOE-001 criteria to be explicitly evidenced.

## Work Guidance

- Keep BOE artifacts concise, operational, and evidence-linked.
- Prefer structured fields (tables/JSON) where repeatability is required.
- Do not store secrets or personal sensitive data in BOE artifacts.

## Verification

- Validate JSON artifacts parse correctly before completion.
- Re-check Sprint 1 checklist and M1 acceptance checklist before completion.

## Child DOX Index

| Path | Scope | Controls |
|---|---|---|
| `00-Program/` | Program-level BOE specs | Build order, standing engineering rule, Sprint/M1 tracking |
| `01-Decision-Register/` | Decision governance and records | DRS-001, schema, append-only decision log |
| `02-Agent-Passports/` | Agent operating identities | AOP-001, template, completed passports |
| `03-Portfolio-Registry/` | Institutional assets and portfolio state | Registry entries and decision linkage |
| `04-Weekly-Life-Board/` | Weekly board operating packet | Agenda, evidence inputs, decision outputs |
| `05-Acceptance/` | Milestone acceptance evidence | M1 gate verification and sign-off |
