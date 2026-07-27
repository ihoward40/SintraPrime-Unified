# Case — Jurisdiction Conflict

## Case ID

BGC-CASE-009

## Title

Jurisdiction Conflict

## Scenario

Two state supreme courts have issued directly conflicting interpretations of identical statutory language. A user asks which interpretation applies to a multi-state transaction.

## Inputs

- State A supreme court opinion.
- State B supreme court opinion.
- Statutory text adopted by both states.
- Transaction documents showing contacts with both states.

## Governing Principles and Articles

- BKGC-R-009 Multi-Jurisdiction Conflict Preservation
- BKGC § X — Jurisdiction Governance
- BKC-C-010 Jurisdiction
- BGS-S-009 Status Determination

## Evidence Evaluation

| Evidence | Source Category | Weight | Notes |
|----------|-----------------|--------|-------|
| State A opinion | Judicial Decision | Controlling within State A | Binding precedent |
| State B opinion | Judicial Decision | Controlling within State B | Conflicts with State A |
| Identical statutory text | Government Publication | Controlling in each state | Same words, different interpretation |

## Reasoning

1. Each state supreme court is the controlling authority within its own jurisdiction.
2. Neither opinion governs the other state.
3. The conflict must be preserved; one state cannot be silently preferred.
4. The governing jurisdiction for the transaction must be determined by traditional choice-of-law analysis, not by the ecosystem.

## Outcome

- Present both controlling authorities.
- Explain that the applicable law depends on which state governs the transaction.
- Recommend choice-of-law analysis by qualified counsel.
- Do not resolve the conflict as if one state necessarily wins.

## Audit Trail

- Evidence IDs: EID-CASE009-001, EID-CASE009-002, EID-CASE009-003
- Reasoning chain ID: RC-CASE009
- Reviewer: Governance Casebook v1.0.0
- Outcome status: DISPUTED ACROSS JURISDICTIONS

## Lessons Learned

- Conflicts between controlling authorities of equal rank must be preserved.
- The ecosystem's role is to document the conflict and identify the governing jurisdiction, not to make a binding choice-of-law determination.
