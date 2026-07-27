# Case — Provenance Failure

## Case ID

BGC-CASE-006

## Title

Provenance Failure

## Scenario

A key document in an evidence package has an incomplete provenance record. The current holder cannot explain how it was obtained or whether it was altered.

## Inputs

- Document of uncertain origin.
- Partial custody log with missing transfer records.
- Statements from two custodians with conflicting accounts.

## Governing Principles and Articles

- BKGC-R-007 Provenance Preservation
- BKGC-R-008 Chain of Custody
- BKC-C-006 Provenance
- BGS-S-003 Provenance Record

## Evidence Evaluation

| Evidence | Source Category | Weight | Notes |
|----------|-----------------|--------|-------|
| Document of uncertain origin | Unknown | Unverified | Provenance gap |
| Partial custody log | Internal Record | Informative | Incomplete |
| Custodian statements | Testimonial / Internal | Conflicting | Cannot resolve origin |

## Reasoning

1. A provenance break means the document's integrity cannot be verified.
2. The document cannot be treated as operational knowledge until provenance is restored.
3. The conflicting custodian statements are themselves evidence that must be preserved.
4. Remediation requires either reconstructing the chain of custody or obtaining a certified copy.

## Outcome

- Downgrade the document to unverified status.
- Preserve the document and the conflicting statements.
- Initiate a remediation workflow to recover provenance.
- Do not use the document as supporting evidence for a consequential conclusion.

## Audit Trail

- Evidence IDs: EID-CASE006-001, EID-CASE006-002, EID-CASE006-003
- Reasoning chain ID: RC-CASE006
- Reviewer: Governance Casebook v1.0.0
- Outcome status: PROVENANCE BREAK — PENDING REMEDIATION

## Lessons Learned

- Provenance gaps are not minor metadata issues; they affect whether evidence can be used.
- Conflicting custody accounts must be preserved, not ignored.
