---
version: 1.0.0
effective_date: 2026-07-27
status: draft
supersedes: []
derived_from: [BCCM v1.0.0, BRA v1.0.0, BKC v1.0.0, BGS v1.0.0, BKGC v2.0]
---

# Blackstone Knowledge Registry (BKR)

## Purpose (Informative)

The Blackstone Knowledge Registry is the authoritative repository of canonical definitions, identifiers, taxonomies, classifications, jurisdiction metadata, Constitutional Decision Records (CDRs), and the master glossary. Every implementation and agent MUST reference the registry to ensure consistent meaning.

## Dependency (Normative)

BKR derives from all upstream volumes. It does not create new substantive governance rules; it records, organizes, and indexes the rules and definitions established upstream. Changes to BKR definitions that alter meaning require a CDR and may require upstream amendment.

## 1. Registry Contents

### 1.1 Registries

- `REGISTRIES/source_taxonomy.md` — Authoritative source categories and default weights.
- `REGISTRIES/claim_status_taxonomy.md` — Claim status codes and definitions.
- `REGISTRIES/lifecycle_stages.md` — Knowledge object lifecycle stages.
- `REGISTRIES/jurisdiction_metadata.md` — Jurisdiction identifiers and governing authorities.
- `REGISTRIES/agent_certification.md` — Certified agents and implementations.
- `REGISTRIES/constitution_registry.md` — Constitutional document lineage: version, status, supersession, integrity hash, governing CDR (see CDR-0007).
- `REGISTRIES/constitution_registry.json` — Machine-readable mirror of the above (derived, non-authoritative; see CDR-0008).
- `REGISTRIES/governance_dependency_graph.md` — Structured view of the frozen volume hierarchy and ecosystem-constitution doctrine edges (see CDR-0008).
- `scripts/governance/validate_constitution_registry.py` (repository root, outside `governance/`) — Standalone (non-CI) consistency validator for the registries above; relocated out of this subtree per CDR-0009 to comply with this volume's own AGENTS.md ("no code in this subtree"). See CDR-0008 for the tooling decision and CDR-0009 for the relocation.

### 1.2 Constitutional Decision Records

- `CDR/` — One file per CDR.
- `CDR/INDEX.md` — Master index of all CDRs, their status, and inter-CDR dependencies (see CDR-0008).

### 1.3 Glossary

- `GLOSSARY/core_terms.md` — Master glossary of constitutional and operational terms.
- `GLOSSARY/abbreviations.md` — Abbreviations used across the library.

## 2. Governance of the Registry

### 2.1 Authority

BKR is authoritative only to the extent that its contents accurately reflect upstream volumes. If a registry entry conflicts with BKGC, BGS, BKC, BRA, or BCCM, the upstream volume governs.

### 2.2 Change Control

- Editorial corrections may be made by the maintainer.
- Taxonomy additions require a CDR.
- Definition changes that alter meaning require upstream amendment.

## 3. Identifier Conventions

| Prefix | Object |
|--------|--------|
| CDR- | Constitutional Decision Record |
| CID- | Claim |
| EID- | Evidence |
| SID- | Source |
| AID- | Authority |
| DID- | Decision |
| RID- | Review |
| OID- | Objection |
| CERT- | Certification record |

## 4. Cross-Reference Index

BKR SHOULD maintain an index mapping each identifier to the document and section where it is defined or used.
