# Registry — Constitution Registry

## Authority

This registry records constitutional documents across the Blackstone ecosystem:
identifier, version, status, effective date, supersession lineage, integrity
hash, governing Constitutional Decision Record (CDR), evidence reference, and
verification status. It extends the Blackstone Knowledge Registry (BKR) under
`ARCHITECTURAL_FREEZE_NOTICE.md` §4 ("Adding new registries under BKR ...
BKR is the canonical registry volume; new registries extend it rather than
parallel it") and does not create a parallel top-level registry.

## Derived From

BKGC Article VII (Knowledge Provenance), Article X (Evidence Integrity
Engine), Article XIX (Authority Lifecycle Management); BKR § 1.1;
`ARCHITECTURAL_FREEZE_NOTICE.md` §4; CDR-0007.

## Scope

Two categories of rows:

- **Library volumes** — the seven volumes of the Blackstone Governance
  Library (BKGC, BGS, BKC, BRA, BCCM, BKR, BGC). Each volume's own
  `CHANGELOG.md` remains the authoritative version history; rows here are a
  cross-reference index only and do not duplicate or override it.
- **Ecosystem constitutions** — constitutional documents outside the
  seven-volume library. Rows for documents that do not yet exist in this
  repository (e.g., SEOS, an Engineering Constitution) are recorded with
  `status: Planned` and no version, effective date, or hash. **A `Planned`
  row is an identifier reservation only — it MUST NOT be read as asserting
  that the document exists, has been drafted, or has been ratified.**

## Entries — Library Volumes

| Constitution ID | Title | Version (see CHANGELOG) | Status | Supersedes | Superseded By | SHA-256 | CDR | Repository Path |
|---|---|---|---|---|---|---|---|---|
| BKGC-V1 | Blackstone Knowledge Governance Constitution — Enterprise Knowledge Governance Framework | 1.0.0 | Archived | — | BKGC-V2 | `3ab6dde80faa52eb62afac3fa956accddbc745cda2796b1b7d0f66bab2314bcf` | CDR-0007 | `volume-1-bkgc/archive/BKGC_v1.0.md` |
| BKGC-V2 | Blackstone Knowledge Governance Constitution | 2.0.0 | Draft (unratified) | BKGC-V1 | — | not computed — hash to be added at ratification, per Rule 4 | CDR-0001 | `volume-1-bkgc/BKGC.md` |
| BGS | Blackstone Governance Standards | see CHANGELOG | Draft | — | — | not computed | CDR-0002 | `volume-2-bgs/BGS.md` |
| BKC | Blackstone Knowledge Core | see CHANGELOG | Draft | — | — | not computed | CDR-0003, CDR-0004 | `volume-3-bkc/BKC.md` |
| BRA | Blackstone Reference Architecture | see CHANGELOG | Draft | — | — | not computed | — | `volume-4-bra/BRA.md` |
| BCCM | Blackstone Certification & Compliance Manual | see CHANGELOG | Draft | — | — | not computed | — | `volume-5-bccm/BCCM.md` |
| BKR | Blackstone Knowledge Registry | see CHANGELOG | Draft | — | — | not computed | CDR-0005 | `volume-6-bkr/BKR.md` |
| BGC | Blackstone Governance Casebook | see CHANGELOG | Draft | — | — | not computed | — | `volume-7-bgc/BGC.md` |

## Entries — Ecosystem Constitutions (Planned)

| Constitution ID | Title | Version | Status | Repository Path |
|---|---|---|---|---|
| SEOS | SintraPrime Executive Operating System Constitution | — | Planned | not yet created |
| ENGINEERING | Engineering Constitution | — | Planned | not yet created |
| MISSION_CONTROL | Mission Control Constitution | — | Planned | not yet created |
| TRUST | Trust Constitution | — | Planned | not yet created |
| AUTOMATION | Automation Constitution | — | Planned | not yet created |

## Rules

1. Only the governance steward may add, promote, or revoke entries.
2. Adding or editing a `Planned` row never creates, drafts, or ratifies
   content; it only reserves a Constitution ID for future tracking.
3. Promoting a row from `Planned` to `Draft` REQUIRES that the corresponding
   document already exist at the stated repository path. Promoting from
   `Draft` to `Active`/ratified REQUIRES a ratification record (as in
   `volume-1-bkgc/RATIFICATION.md`). Both promotions MUST be recorded as a
   CDR in `volume-6-bkr/CDR/`.
4. SHA-256 values, when present, are computed over the canonical
   constitutional text only (from its title heading through its closing
   Ratification/closing section), excluding front matter and any editorial
   or archival notices; line endings are normalized to LF before hashing.
   A hash MUST be recomputed and updated whenever that text changes.
5. Status values: `Planned`, `Draft`, `Active`, `Archived`, `Superseded`.
6. This registry is an index. It does not supersede or duplicate the
   authority of `GOVERNANCE_MANIFEST.md`, any volume's own `CHANGELOG.md`,
   or `volume-1-bkgc/RATIFICATION.md`.

## Related Tooling

- `constitution_registry.json` — machine-readable mirror of this file
  (derived, non-authoritative). Regenerate whenever the tables above change.
- `governance_dependency_graph.md` — structured view of the frozen volume
  hierarchy and ecosystem-constitution doctrine edges.
- `CDR/INDEX.md` — master index of all CDRs, including CDR-0007 and
  CDR-0008 governing this registry and its tooling.
- `validate_registry.py` has been relocated: see `scripts/governance/validate_constitution_registry.py`
  at the repository root (outside `governance/`), per CDR-0009. It is a
  standalone script checking internal consistency of this registry and its
  JSON mirror (unique IDs, resolvable/reciprocal supersession in both
  directions, resolvable CDR references, on-disk repository paths, and
  Markdown/JSON drift). Not wired into CI; see CDR-0008.

## Initial State

Seeded 2026-08-01 per CDR-0007, alongside the BKGC v1.0 archival. Ecosystem
constitution rows are placeholders pending future drafting and ratification.
Registry tooling (index, dependency graph, JSON mirror, validator) added
2026-08-01 per CDR-0008.
