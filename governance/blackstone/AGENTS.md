# Blackstone Governance Library — DOX Contract

## Purpose

This subtree contains the Blackstone Governance Library, a seven-volume constitutional knowledge-governance framework for SintraPrime-Unified and any conforming implementation.

## Ownership

- Hermes Agent is the authoring steward for structural and editorial changes.
- Isiah Howard holds ratification authority.
- The root `AGENTS.md` owns repository-wide workflow rules.

## Local Contracts

- All changes MUST follow the normative dependency graph: BKGC → BGS → BKC → BRA → BCCM → BKR → BGC.
- BKGC changes are constitutional amendments and require explicit ratification.
- Every downstream document MUST cite its upstream basis using RFC-style references.
- No code, product feature, or operational schema may be placed in this subtree.
- CDRs live under `volume-6-bkr/CDR/`.
- Baselines are ratified through the GBC-N sequence, not merged mid-sequence.

## Work Guidance

- Before expanding any volume, read the upstream volumes first.
- Add identifiers in the canonical forms: `BKGC-R-xxx`, `BGS-S-xxx`, `BKC-C-xxx`, `BRA-E-xxx`, `BCCM-T-xxx`, `BKR-TERM-xxx`, `BGC-CASE-xxx`, `CDR-xxxx`.
- Mark sections as `(Normative)` or `(Informative)`.
- Keep the Constitution implementation-neutral.
- Use RFC 2119 keywords (`MUST`, `SHOULD`, `MAY`) for normative provisions.

## Verification

- Run a governance consistency audit before each freeze:
  - duplicate definitions
  - undefined terms
  - circular references
  - orphaned articles
  - inconsistent numbering
  - terminology drift
  - broken cross-references
- `git status --porcelain=v1` MUST show only intended governance files before any PR.

## Child DOX Index

| Path | Scope | Controls |
|---|---|---|
| `volume-1-bkgc/` | Constitutional Charter | Enduring principles, articles, amendment procedure |
| `volume-2-bgs/` | Operational Standards | Evidence intake, review protocols, metadata schemas |
| `volume-3-bkc/` | Knowledge Core | Ontology, taxonomies, knowledge models |
| `volume-4-bra/` | Reference Architecture | Engines, interfaces, APIs, diagrams |
| `volume-5-bccm/` | Certification & Compliance | Tests, certification, audits, scorecards |
| `volume-6-bkr/` | Knowledge Registry | Registries, CDRs, glossaries, identifiers |
| `volume-7-bgc/` | Governance Casebook | Worked cases demonstrating application |
