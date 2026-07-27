# Blackstone Governance Library — Manifest

## Normative Dependency Graph

```text
                Constitution
                     │
                     ▼
  Blackstone Knowledge Governance Constitution (BKGC)
                     │
                     ▼
        Blackstone Governance Standards (BGS)
                     │
                     ▼
         Blackstone Knowledge Core (BKC)
                     │
                     ▼
      Blackstone Reference Architecture (BRA)
                     │
                     ▼
  Blackstone Certification & Compliance Manual (BCCM)
                     │
                     ▼
        Blackstone Knowledge Registry (BKR)
                     │
                     ▼
        Blackstone Governance Casebook (BGC)
```

## Authority Rule

A downstream volume MUST NOT contradict an upstream volume.

- `volume-1-bkgc/BKGC.md` is the supreme normative authority.
- `volume-2-bgs/BGS.md` derives from BKGC.
- `volume-3-bkc/BKC.md` derives from BGS.
- `volume-4-bra/BRA.md` derives from BKC and BGS.
- `volume-5-bccm/BCCM.md` certifies conformance to BKGC, BGS, BKC, and BRA.
- `volume-6-bkr/BKR.md` provides canonical definitions and records.
- `volume-7-bgc/BGC.md` demonstrates application of all upstream volumes.

## Conformance Resolution

When a conflict is discovered:

1. The upstream volume governs until the conflict is resolved.
2. A Constitutional Decision Record (CDR) MUST be created in `volume-6-bkr/CDR/`.
3. The CDR MUST identify the conflicting provisions, the resolution, and the rationale.
4. If the resolution changes a constitutional provision, the change MUST follow the amendment procedure in `volume-1-bkgc/RATIFICATION.md`.

## Amendment Doctrine

- Changes to BKGC are constitutional amendments.
- Changes to BGS are standards revisions.
- Changes to BKC, BRA, BCCM, BKR, and BGC are governed updates.

Each level of change has its own approval threshold, defined in the relevant volume.

## Traceability Requirement (Normative)

**BKR-TERM-013 Traceability.** Every downstream documentr Policy (Normative)

Every mandatory requirement, standard, concept, engine, test, term, and case MUST carry a permanent identifier in one of these canonical forms:

| Prefix | Scope | Example |
|--------|-------|---------|
| `BKGC-R-xxx` | Constitutional requirement | `BKGC-R-001` |
| `BGS-S-xxx` | Governance standard | `BGS-S-004` |
| `BKC-C-xxx` | Knowledge Core concept | `BKC-C-012` |
| `BRA-E-xxx` | Reference architecture engine or API requirement | `BRA-E-008` |
| `BCCM-T-xxx` | Certification test | `BCCM-T-041` |
| `BKR-TERM-xxx` | Registry term | `BKR-TERM-029` |
| `BGC-CASE-xxx` | Casebook worked example | `BGC-CASE-041` |
| `CDR-xxxx` | Constitutional Decision Record | `CDR-0001` |

Every downstream identifier MUST trace back to at least one upstream requirement identifier. BKGC-R identifiers derive from the Constitution itself and require no upstream trace.

 MUST cite its upstream basis using RFC-style section references, for example:

- `Derived from: BKGC Article III § 3.2`
- `Governed by: BGS 4.1`
- `Implements: BKC Knowledge Object 2.1`

## Identifier Policy (Normative)

Every mandatory requirement, standard, concept, engine, test, term, and case MUST carry a permanent identifier in one of these canonical forms:

| Prefix | Scope | Example |
|--------|-------|---------|
| `BKGC-R-xxx` | Constitutional requirement | `BKGC-R-001` |
| `BGS-S-xxx` | Governance standard | `BGS-S-004` |
| `BKC-C-xxx` | Knowledge Core concept | `BKC-C-012` |
| `BRA-E-xxx` | Reference architecture engine or API requirement | `BRA-E-008` |
| `BCCM-T-xxx` | Certification test | `BCCM-T-041` |
| `BKR-TERM-xxx` | Registry term | `BKR-TERM-029` |
| `BGC-CASE-xxx` | Casebook worked example | `BGC-CASE-041` |
| `CDR-xxxx` | Constitutional Decision Record | `CDR-0001` |

Every downstream identifier MUST trace back to at least one upstream requirement identifier. BKGC-R identifiers derive from the Constitution itself and require no upstream trace.

## Reference Implementation

SintraPrime-Unified is the reference implementation of this library. It is bound by `volume-4-bra/BRA.md` and certified by `volume-5-bccm/BCCM.md`.

## Governance of the Library Itself

Changes to this manifest are governed by the same dependency rule: this manifest may not contradict `README.md` or any upstream volume. Amendments to the manifest itself require a CDR.
