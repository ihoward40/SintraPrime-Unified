# SintraPrime — Evidence Lifecycle (ELC) v1.0.0
## FROZEN SPECIFICATION

**Status:** Frozen  
**Effective Version:** v1.0.0  
**Freeze Date:** 2025-12-24  
**Scope:** Evidence lifecycle, verification, and court-facing artifacts

---

## Purpose

ELC v1.0.0 defines the immutable evidence lifecycle used by SintraPrime to
intake, normalize, cryptographically anchor, verify, and present evidence
for courts, regulators, and auditors.

This specification is frozen to ensure that artifacts generated under v1.0.0
remain valid, reproducible, and defensible over time.

---

## Scope (What ELC v1.0.0 Covers)

ELC v1.0.0 governs:

- Evidence intake, normalization, hashing, and manifesting
- Merkle tree construction and proof generation
- Ledger event recording
- Time anchoring (TSA) and notary anchoring
- Dual-anchor verification reports
- Public, offline verification
- Court-facing outputs (bench copy, CM/ECF ZIP, hearing artifacts)
- Hearing lifecycle artifacts (transcript markers, admitted exhibits, snapshots)

All artifacts are schema-validated and deterministic.

---

## Invariants (What Must Never Change)

The following invariants are absolute:

1. **Immutability**  
   Evidence and derived cryptographic artifacts are never modified after freeze.

2. **No Post-Hoc Recalculation**  
   Post-hearing or court artifacts may reference existing hashes only.
   Re-hashing or recomputation is forbidden.

3. **Deterministic Outputs**  
   Given the same inputs, outputs must be byte-for-byte reproducible.

4. **Offline Verifiability**  
   Verification must not require network access, servers, or trust in operators.

5. **Schema Enforcement**  
   All artifacts must conform to published JSON schemas.
   Invalid artifacts fail validation and CI.

6. **Fail-Closed Operation**  
   Missing lifecycle steps, anchors, or required artifacts cause hard failure.

---

## Explicit Non-Goals (What ELC v1.0.0 Does NOT Do)

ELC v1.0.0 intentionally does NOT:

- Upload filings to courts or regulators
- Email clerks, judges, or third parties
- Modify evidence after freeze
- Perform server-side verification
- Provide legal advice or advocacy
- Automate discretionary court interactions

These are policy decisions, not technical omissions.

---

## Versioning Policy

- **v1.x**  
  Additive features only. No changes to ELC invariants.
  v1 artifacts remain valid indefinitely.

- **v2.0**  
  Created only if ELC rules or invariants change.
  Requires a new freeze document and migration strategy.

---

## Authority

This document defines the authoritative scope and constraints of
SintraPrime ELC v1.0.0.

Any deviation constitutes a new lifecycle version.
