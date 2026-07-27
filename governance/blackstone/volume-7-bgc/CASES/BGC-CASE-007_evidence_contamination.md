# Case — Evidence Contamination

## Case ID

BGC-CASE-007

## Title

Evidence Contamination

## Scenario

A digital evidence file is found to have been modified after collection. The modification is small but materially affects the conclusion drawn from the file.

## Inputs

- Original collected file hash.
- Current file hash.
- Hash mismatch indicating post-collection modification.
- Logs showing an editor opened the file after intake.

## Governing Principles and Articles

- BKGC-R-007 Provenance Preservation
- BKGC § XXI — Failure Mode Governance
- BGS-S-004 Chain of Custody
- BRA-E-004 Provenance Engine

## Evidence Evaluation

| Evidence | Source Category | Weight | Notes |
|----------|-----------------|--------|-------|
| Original hash | Forensic Metadata | Controlling | Baseline integrity |
| Current hash | Forensic Metadata | Disqualifying | Mismatch with original |
| Editor logs | System Record | Controlling | Shows post-collection access |

## Reasoning

1. The hash mismatch proves the file was altered after collection.
2. Post-collection modification constitutes evidence contamination.
3. The current file cannot be relied upon for a governed conclusion.
4. The original may be recoverable from immutable backup or content-addressed storage.

## Outcome

- Quarantine the contaminated file.
- Treat it as critical failure mode.
- Attempt recovery from immutable evidence store.
- If recovery fails, declare the evidence unavailable.

## Audit Trail

- Evidence IDs: EID-CASE007-001, EID-CASE007-002, EID-CASE007-003
- Reasoning chain ID: RC-CASE007
- Reviewer: Governance Casebook v1.0.0
- Outcome status: CRITICAL FAILURE — CONTAMINATION

## Lessons Learned

- Immutable storage and integrity hashes are not optional for legally sensitive evidence.
- Any post-collection modification must be documented as contamination or explicitly ratified through a controlled workflow.
