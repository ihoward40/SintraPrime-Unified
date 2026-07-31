# Blackstone Governance Library — Architectural Freeze Notice

**Status:** Standing Notice (post-ratification)
**Date:** 2026-07-31
**Applies to:** Governance Baseline 1 (GB-1)
**Classification:** Meta-governance (not part of the frozen GB-1 baseline content)

## 1. Notice

> The seven-volume Blackstone Governance Library architecture is established as the reference governance architecture for GB-1.
>
> Future work SHALL presume this architecture unless operational evidence demonstrates that the architecture itself — not merely its implementation — requires revision.
>
> Future improvements should preferentially occur within existing architectural boundaries before proposing new layers or restructuring the library.

## 2. Frozen Architecture

The reference governance architecture for GB-1 is the seven-volume, strictly hierarchical library defined in `README.md` and `GOVERNANCE_MANIFEST.md`:

```text
BKGC (Constitutional Charter)
  └─ BGS (Operational Standards)
       └─ BKC (Knowledge Core — semantic authority)
            └─ BRA (Reference Architecture)
                 └─ BCCM (Certification & Compliance)
                      └─ BKR (Knowledge Registry)
                           └─ BGC (Governance Casebook)
```

| Volume | Abbrev | Role | Directory |
|--------|--------|------|-----------|
| I | BKGC | Constitutional Charter | `volume-1-bkgc/` |
| II | BGS | Operational Standards | `volume-2-bgs/` |
| III | BKC | Knowledge Core (semantic authority) | `volume-3-bkc/` |
| IV | BRA | Reference Architecture | `volume-4-bra/` |
| V | BCCM | Certification & Compliance | `volume-5-bccm/` |
| VI | BKR | Knowledge Registry | `volume-6-bkr/` |
| VII | BGC | Governance Casebook | `volume-7-bgc/` |

The following are frozen as architecture:

- The **volume count (seven)** and the **one-to-one mapping** of each volume to its role above.
- The **strict downward dependency hierarchy** (each volume derives from and is constrained by the volumes above it; a downstream volume MUST NOT contradict an upstream volume).
- The **top-level concept set** — Constitution, Standards, Knowledge Core, Reference Architecture, Certification, Registry, Casebook — as the only first-class architectural layers.
- The **canonical semantic authority** of BKC over all schemas, APIs, registries, and engines.

## 3. Scope of the Freeze

This notice prevents **architecture drift**: the gradual accretion of new top-level layers or parallel structures because they seem useful in the moment (an eighth volume, a second parallel registry, a new top-level concept, or a peer-to-peer volume relationship that bypasses the hierarchy).

It does **not** freeze:

- The *content* of any volume (already governed by the GB-1 constitutional freeze and the per-volume change procedures).
- The addition of new documents, cases, terms, tests, or registries *within* an existing volume.
- Governance tooling (linter, traceability graph, dashboard, automated compliance tests) as scoped in `GBC-2-PLAN.md` — these are implementation aids, not architecture layers.

## 4. Permitted Without Architecture Revision

The following do **not** require architecture revision and are governed by existing per-volume procedures (standards revisions, governed updates, or CDRs as applicable):

- Adding or revising documents, standards, concepts, engines, tests, terms, or cases **within** an existing volume.
- Adding new registries **under** BKR (e.g., Jurisdiction Registry, Source Taxonomy Registry) — BKR is the canonical registry volume; new registries extend it rather than parallel it.
- Adding new casebook entries under BGC drawn from real development.
- Governance tooling that operates on the existing architecture without introducing new layers.

## 5. Requires Architecture Revision

The following are **prohibited without explicit architecture revision**, which may occur only through the GB-1 review trigger or the formal BKGC amendment process:

- Introducing an **eighth (or further) volume** as a new first-class architectural layer.
- Creating a **parallel top-level registry** or parallel governance structure outside BKR.
- Introducing a **new top-level concept** that is not one of the seven roles above.
- **Reordering, inverting, or peer-connecting** the dependency hierarchy.
- **Splitting or merging** an existing volume in a way that changes the volume count or role mapping.

Architecture revision requires: (a) the GB-1 review trigger (90-day retrospective or RS-1 elevation per `GOVERNANCE_LIFECYCLE.md`), or (b) a Constitutional Decision Record (`CDR-xxxx`) in `volume-6-bkr/CDR/` followed by the BKGC amendment procedure in `volume-1-bkgc/RATIFICATION.md`.

## 6. Relationship to Existing Freezes

This notice is distinct from, and complements, the existing freezes:

- **GB-1 constitutional freeze** (`RELEASES/GB-1.md` § Freeze): freezes the *content* of the Constitution and downstream volumes against change without the amendment procedure. This notice freezes the *shape* of the library itself.
- The two freezes are orthogonal: a change can respect the content freeze yet violate the architecture freeze (e.g., adding an eighth volume with perfectly valid content), and vice versa.

## 7. Primary Success Indicator

The architecture freeze is validated operationally, not documentarily. The primary indicator is **Decision Rework Rate** — the frequency with which a decision is revisited because important evidence was missing at the time it was made. A successful GB-1 should show, over the retrospective window, fewer premature decisions, fewer contradictory positions, fewer missing-evidence requests, and less rework from avoidable uncertainty. See `GB-1-CLOSURE.md` and the `RETROSPECTIVES/` process.

## 8. Status

Standing notice. Effective 2026-07-31. Recorded post-ratification; does not alter GB-1 baseline content.

**End of Architectural Freeze Notice.**
