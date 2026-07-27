# Case — Conflicting Appellate Decisions

## Case ID

CASE-001

## Title

Conflicting Appellate Decisions

## Scenario

Two intermediate appellate courts in the same state have reached opposite conclusions on the same statutory interpretation question. A user asks which position governs.

## Inputs

- Court A opinion: holds the statute requires X.
- Court B opinion: holds the statute requires not-X.
- No higher court has resolved the conflict.
- User jurisdiction is within the geographic scope of both courts.

## Governing Principles and Articles

- BKGC Article VIII — Authority Governance
- BKGC Article XII — Conflict Resolution
- BKGC Article XV — Claim Classification
- BGS 5 — Claim Status Assignment
- BKC § 5.2 — Authority Types

## Evidence Evaluation

| Evidence | Source Category | Weight | Notes |
|----------|-----------------|--------|-------|
| Court A opinion | Judicial Decision | Persuasive within its district | Non-controlling outside its district |
| Court B opinion | Judicial Decision | Persuasive within its district | Conflicts with Court A |
| Statute text | Government Publication | Controlling | Both courts interpret the same text |

## Reasoning

1. Both courts are intermediate appellate courts; neither is controlling over the other's district.
2. The statute text is controlling but ambiguous.
3. The correct answer depends on which district's precedent applies to the user's specific matter.
4. The claim status for "the statute requires X" in the abstract is therefore `DISPUTED`.

## Outcome

- Present both positions.
- Identify the jurisdictional split.
- Recommend consultation with controlling authority for the user's specific district or seeking higher court resolution.
- Do not present one position as settled law across the entire state.

## Audit Trail

- Evidence IDs: EID-CASE001-001, EID-CASE001-002, EID-CASE001-003
- Reasoning chain ID: RC-CASE001
- Reviewer: Governance Casebook v1.0.0
- Outcome status: DISPUTED

## Lessons Learned

- Intermediate appellate conflicts are common and must be preserved, not resolved by selecting the preferred opinion.
- The user must be told what additional fact (jurisdiction/district) determines the controlling answer.
