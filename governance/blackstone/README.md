# Blackstone Governance Library

## Status

Active constitutional repository for the Blackstone ecosystem.

## Purpose

This directory contains the normative governance documents for the Blackstone Knowledge Governance ecosystem. The library is structured as a layered standards system, not a single document. Each downstream volume derives from and is constrained by the volumes above it.

## Dependency Graph

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

## Foundational Documents

- `GOVERNANCE_MANIFEST.md` — Dependency graph and normative authority rules
- `GOVERNANCE_ROADMAP.md` — Planned amendments, standards, engines, registries
- `GOVERNANCE_PRINCIPLES.md` — Bill of Rights for governance
- `GOVERNANCE_STYLE_GUIDE.md` — Drafting conventions for all volumes

## Volumes

| Volume | Directory | Purpose |
|--------|-----------|---------|
| I | `volume-1-bkgc/` | Constitutional charter |
| II | `volume-2-bgs/` | Operational standards |
| III | `volume-3-bkc/` | Shared semantic model |
| IV | `volume-4-bra/` | Software reference architecture |
| V | `volume-5-bccm/` | Certification and compliance |
| VI | `volume-6-bkr/` | Canonical registry |
| VII | `volume-7-bgc/` | Worked casebook |

## Core Doctrine

> Knowledge is governed by process rather than popularity.

This is the central epistemological commitment of the library. A claim does not become trustworthy because it is widely believed; it becomes governed when it has been produced, evaluated, preserved, and reviewed according to the constitutional process.

## Conformance Rule

A downstream document MUST NOT contradict an upstream document. If a conflict is discovered, the upstream document governs until the conflict is resolved by a constitutional amendment recorded as a Constitutional Decision Record (CDR).

## Reference Implementation

SintraPrime-Unified is designated as the reference implementation of the Blackstone Governance Library. The implementation is bound by the Architecture, which is bound by the Standards, which are bound by the Constitution.
