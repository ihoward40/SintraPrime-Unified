---
version: 1.0.0
effective_date: 2026-07-27
status: draft
---

# Blackstone Knowledge Registry — Changelog

## Unreleased — 2026-08-01

### Added

- `REGISTRIES/constitution_registry.md` — constitutional document lineage
  registry (version, status, supersession, SHA-256, governing CDR), added
  under BKR per `ARCHITECTURAL_FREEZE_NOTICE.md` §4 rather than as a
  parallel top-level registry. See CDR-0007.
- `CDR/CDR-0007.md` — records the decision to extend BKR instead of creating
  a separate ecosystem-wide Governance Registry.

### Added (registry tooling)

- `CDR/INDEX.md` — master index of all CDRs (status, amendment class,
  affected volumes, inter-CDR dependencies). See CDR-0008.
- `REGISTRIES/governance_dependency_graph.md` — structured (table-form)
  view of the frozen seven-volume hierarchy plus doctrine edges for
  ecosystem constitutions, derived from `ARCHITECTURAL_FREEZE_NOTICE.md` §2
  and `constitution_registry.md`. See CDR-0008.
- `REGISTRIES/constitution_registry.json` — machine-readable mirror of
  `constitution_registry.md`; derived and non-authoritative. See CDR-0008.
- `REGISTRIES/validate_registry.py` — standalone script validating unique
  IDs, resolvable/reciprocal supersession references, resolvable CDR
  references, on-disk repository paths, and Planned-row invariants. Not
  wired into CI; see CDR-0008 Revisit Conditions.
- `CDR/CDR-0008.md` — records the decision to add this tooling under BKR
  without prematurely wiring it into CI ahead of `GBC-2-PLAN.md` entry
  criteria.

## 1.0.0 — 2026-07-27

### Added

- Registry framework and governance rules.
- Initial registries: source taxonomy, claim status, lifecycle stages, jurisdiction metadata, agent certification.
- CDR directory structure.
- Master glossary and abbreviations.
- Identifier conventions.

### Derived From

- BKGC v2.0
- BGS v1.0.0
- BKC v1.0.0
- BRA v1.0.0
- BCCM v1.0.0
