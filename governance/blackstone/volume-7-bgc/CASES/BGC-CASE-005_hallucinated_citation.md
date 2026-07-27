# Case — AI Hallucinated Citation

## Case ID

BGC-CASE-005

## Title

AI Hallucinated Citation

## Scenario

An AI agent drafting a legal memo invents a case citation that appears plausible but does not exist. A reviewer asks the ecosystem to flag the issue.

## Inputs

- AI-drafted memo containing citation.
- Attempted verification against court records and legal databases.
- No record of the cited case exists.

## Governing Principles and Articles

- BKGC-R-004 No Fabricated Evidence
- BKGC-R-021 AI Output Verification
- BKGC § XXI — Failure Mode Governance
- BCCM-T-001 Fabricated Citation

## Evidence Evaluation

| Evidence | Source Category | Weight | Notes |
|----------|-----------------|--------|-------|
| AI-drafted memo | AI Derivative | Unverified | Must be independently verified |
| Court records | Government Publication | Controlling | No matching case found |
| Legal databases | Commercial / Government | Persuasive | No matching case found |

## Reasoning

1. AI-generated outputs are derivative works requiring verification.
2. Independent search of authoritative sources fails to corroborate the citation.
3. The fabricated citation is a critical failure mode.
4. The memo must be quarantined and the error escalated.

## Outcome

- Flag the citation as fabricated.
- Remove the citation from any governed conclusion.
- Quarantine the memo pending correction.
- Record the failure mode and remediation in the audit trail.

## Audit Trail

- Evidence IDs: EID-CASE005-001, EID-CASE005-002, EID-CASE005-003
- Reasoning chain ID: RC-CASE005
- Reviewer: Governance Casebook v1.0.0
- Outcome status: CRITICAL FAILURE

## Lessons Learned

- AI outputs cannot be trusted for citations without independent verification.
- Fabricated citations are a critical failure requiring escalation.
