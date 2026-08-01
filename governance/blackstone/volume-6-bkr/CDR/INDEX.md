# Constitutional Decision Record — Index

## Authority

This index catalogs every Constitutional Decision Record (CDR) in
`volume-6-bkr/CDR/` so that status, scope, and inter-CDR dependencies are
discoverable without opening each file. It is a derived index only; the
authoritative content of each decision is the CDR file itself.

## Derived From

`BKR.md` § 1.2, § 1.3 ("BKR SHOULD maintain an index mapping each
identifier to the document and section where it is defined or used");
CDR-0008.

## Index

| CDR | Title | Status | Amendment Class | Affected Volumes | Superseded By | Depends On |
|---|---|---|---|---|---|---|
| CDR-0001 | Adopt Blackstone Governance Library | Ratified | Constitutional | BKGC, BGS, BKC, BRA, BCCM, BKR, BGC | — | — |
| CDR-0002 | Separate Constitution from Standards and Implementation | Ratified | Major | BKGC, BGS, BKC, BRA, BCCM, BKR, BGC | — | CDR-0001 |
| CDR-0003 | Adopt Governed Knowledge Doctrine | Ratified | Major | BKGC, BKC | — | CDR-0001 |
| CDR-0004 | Designate Knowledge Core as Canonical Semantic Authority | Ratified | Major | BKGC, BKC, BKR | — | CDR-0001, CDR-0003 |
| CDR-0005 | Adopt Requirement Traceability System | Ratified | Major | BKGC, BGS, BKC, BRA, BCCM, BKR, BGC | — | CDR-0001, CDR-0002 |
| CDR-0006 | Govern Advisory Service as a Non-Execution Capability | Ratified | Major | BKGC (v2.0), BKR | — | CDR-0001 |
| CDR-0007 | Extend BKR Instead of Creating a Parallel Registry | Ratified | Editorial | BKGC (v1.0 archive), BKR | — | CDR-0001, CDR-0002, CDR-0005 |
| CDR-0008 | Add Lightweight Registry Tooling Under BKR | Ratified | Editorial | BKR | — | CDR-0005, CDR-0007 |

## Rules

1. Every CDR MUST appear in this index at creation time; adding a CDR file
   without an index row is incomplete.
2. `Superseded By` is populated only when a later CDR explicitly supersedes
   an earlier one (correction, not extension); CDRs are otherwise immutable
   per CDR-0006's governing principle "CDRs are immutable; corrections
   require a new CDR."
3. `Depends On` lists CDRs whose decisions this CDR presumes, extends, or
   was constrained by — it is informative (for navigation), not a formal
   dependency-graph authority; see
   `REGISTRIES/governance_dependency_graph.md` for the normative volume
   hierarchy.
4. This index does not alter the status or authority of any CDR; in case of
   any discrepancy, the individual CDR file governs.

## Change Control

Editorial: adding a row for a newly created CDR may be done by the
maintainer alongside creating that CDR. Any change to a CDR's `Status` or
`Superseded By` value requires the referenced CDR itself to be updated
first (a new CDR recording the correction), then this index synchronized.
