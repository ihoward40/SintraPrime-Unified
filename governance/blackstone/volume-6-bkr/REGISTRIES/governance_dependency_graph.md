# Registry — Governance Dependency Graph

## Authority

This registry represents, as structured data, the dependency relationships
that are already normative prose in `ARCHITECTURAL_FREEZE_NOTICE.md` § 2
(the frozen seven-volume hierarchy) and `constitution_registry.md` (CDR-0007,
constitutional lineage). It adds no new relationships and overrides neither
document; it is a queryable view of relationships that already govern.

## Derived From

`ARCHITECTURAL_FREEZE_NOTICE.md` § 2; `constitution_registry.md`; CDR-0001;
CDR-0007; CDR-0008.

## Scope

Two kinds of edges are represented:

- **Hierarchy edges** — the frozen, strict downward dependency chain among
  the seven Blackstone Governance Library volumes. These are normative and
  may not be reordered, inverted, or peer-connected without an architecture
  revision (`ARCHITECTURAL_FREEZE_NOTICE.md` § 5).
- **Doctrine edges** — the relationship between BKGC and any ecosystem
  constitution (existing or `Planned`). Every constitution in the ecosystem,
  by definition, derives its governing doctrine from BKGC, but a doctrine
  edge is **not** a hierarchy edge: it does not add the ecosystem
  constitution to the seven-volume library, and it does not imply the
  document exists yet.

## Library Hierarchy (Normative — frozen)

```text
BKGC (Constitutional Charter)
  └─ BGS (Operational Standards)
       └─ BKC (Knowledge Core — semantic authority)
            └─ BRA (Reference Architecture)
                 └─ BCCM (Certification & Compliance)
                      └─ BKR (Knowledge Registry)
                           └─ BGC (Governance Casebook)
```

| From | To | Relationship | Source |
|---|---|---|---|
| BKGC | BGS | constrains | `ARCHITECTURAL_FREEZE_NOTICE.md` § 2 |
| BGS | BKC | constrains | `ARCHITECTURAL_FREEZE_NOTICE.md` § 2 |
| BKC | BRA | constrains | `ARCHITECTURAL_FREEZE_NOTICE.md` § 2 |
| BRA | BCCM | constrains | `ARCHITECTURAL_FREEZE_NOTICE.md` § 2 |
| BCCM | BKR | constrains | `ARCHITECTURAL_FREEZE_NOTICE.md` § 2 |
| BKR | BGC | constrains | `ARCHITECTURAL_FREEZE_NOTICE.md` § 2 |

## Doctrine Edges (Informative — ecosystem constitutions)

| Constitution ID | Status | Relationship to BKGC | Notes |
|---|---|---|---|
| BKGC-V1 | Archived | — (is BKGC) | Superseded by BKGC-V2. |
| BKGC-V2 | Draft (unratified) | — (is BKGC) | Current constitutional charter. |
| SEOS | Planned | derives doctrine from | Not yet drafted; placeholder only. |
| ENGINEERING | Planned | derives doctrine from | Not yet drafted; placeholder only. |
| MISSION_CONTROL | Planned | derives doctrine from | Not yet drafted; placeholder only. |
| TRUST | Planned | derives doctrine from | Not yet drafted; placeholder only. |
| AUTOMATION | Planned | derives doctrine from | Not yet drafted; placeholder only. |

A `Planned` doctrine edge asserts only that *if* the document is eventually
drafted, it would derive its governing doctrine from BKGC — it does not
place the document in the seven-volume hierarchy and does not authorize its
creation. See `constitution_registry.md` Rule 2.

## Rules

1. Hierarchy edges are normative and MUST match
   `ARCHITECTURAL_FREEZE_NOTICE.md` § 2 exactly. Any discrepancy is an error
   in this file, not in the notice.
2. Doctrine edges MUST NOT be promoted to hierarchy edges — adding an
   ecosystem constitution as an eighth volume, or as a peer of an existing
   volume, requires the architecture revision process in
   `ARCHITECTURAL_FREEZE_NOTICE.md` § 5.
3. Adding a doctrine edge row for a new `Planned` constitution ID requires
   the corresponding row to already exist in `constitution_registry.md`.
4. This file is descriptive tooling under
   `ARCHITECTURAL_FREEZE_NOTICE.md` § 3–4; it carries no independent
   authority beyond the documents it derives from.

## Initial State

Seeded 2026-08-01 per CDR-0008, alongside the CDR index and machine-readable
registry mirror.
