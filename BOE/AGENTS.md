# BOE — DOX Contract

## Purpose

This subtree contains the Howard Life Institution BOE program artifacts that define, sequence, and preserve the institution's operational decision framework.

## Ownership

- Isiah Howard is the ratifying authority for BOE program decisions.
- Implementation agents may draft and update BOE artifacts within the approved program scope.
- The root `AGENTS.md` owns repository-wide workflow rules.

## Local Contracts

- Every BOE artifact MUST either enable a decision, support a decision, execute a decision, or preserve a decision.
- `00-Program/` contains master implementation program specifications.
- `01-Decision-Register/` contains recorded decision records (`DR-####`) governing BOE execution.
- BOE records MUST use stable identifiers and cite the concrete file paths they govern.

## Work Guidance

- Keep BOE documents operational, concise, and directly actionable for the Howard Life Institution.
- When a decision approves or changes BOE execution scope, update the governing `DR-####` record and the affected program artifact together.
- Use canonical identifiers in the forms `BOE-###` and `DR-####`.

## Verification

- Confirm every referenced authoritative BOE file path exists; planned future deliverables must be clearly labeled as planned.
- Review `git status --porcelain=v1` before completion to ensure only intended BOE and DOX files changed.

## Child DOX Index

| Path | Scope | Controls |
|---|---|---|
| `00-Program/` | BOE program specifications | Master implementation plans and execution scope |
| `01-Decision-Register/` | BOE decision records | Recorded approvals, supersession, and institutional decision history |
