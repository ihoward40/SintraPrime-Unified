---
version: 1.0.0
effective_date: 2026-07-27
status: draft
supersedes: []
derived_from: [BKGC v2.0]
---

# Blackstone Governance Standards (BGS)

## Purpose (Informative)

This volume translates the Blackstone Knowledge Governance Constitution into operational rules. It defines how evidence is handled, how provenance is recorded, how confidence is scored, and how review workflows operate.

## Dependency (Normative)

BGS derives from `volume-1-bkgc/BKGC.md`. It MUST NOT contradict BKGC. BKC, BRA, BCCM, BKR, and BGC derive from BGS.

## 1. Evidence Handling Standard

### 1.1 Evidence Registration (Normative)

**BGS-S-001** Every evidence item used in a governed conclusion MUST be registered with:

- Unique Evidence ID (EID)
- Source ID (SID)
- Collection timestamp
- Collector identity
- Evidence type
- Integrity hash when applicable
- Jurisdiction

### 1.2 Evidence Lifecycle (Informative)

```text
Intake → Validation → Classification → Storage → Review → Archive
```

### 1.3 Evidence Acceptance Criteria (Normative)

**BGS-S-002** Evidence MUST have:

- Identifiable source
- Verifiable provenance
- Relevance to at least one claim
- Metadata completeness score ≥ BGS threshold

## 2. Provenance Standard

### 2.1 Provenance Record (Normative)

**BGS-S-003** A provenance record MUST contain:

- Evidence ID
- Source origin
- Custody transfers
- Transformation history
- Review history
- Integrity status

### 2.2 Chain of Custody (Normative)

**BGS-S-004** For legally sensitive evidence, every custody transfer MUST record:

- Transfer timestamp
- Transferor
- Transferee
- Purpose
- Integrity verification result

## 3. Evidence Confidence Scoring

### 3.1 Operational Scoring Model (Informative)

Derived from `volume-1-bkgc/APPENDICES/A_evidence_confidence_model.md`.

| Score | Minimum Requirement |
|-------|---------------------|
| A | Two or more independent primary sources corroborating the same material fact |
| B | One primary source plus persuasive or scholarly support |
| C | Persuasive authority only |
| D | Reliable educational or explanatory source |
| E | Scholarly discussion, community commentary, or emerging evidence |
| F | Unverified or insufficient evidence |

### 3.2 Score Assignment (Normative)

**BGS-S-005** A confidence score MUST be assigned by a qualified reviewer or a certified automated process. The assignment MUST be documented and auditable.

### 3.3 Score Disagreement (Normative)

**BGS-S-006** When reviewers disagree on a confidence score, the lower score governs until the disagreement is resolved by a CDR.

## 4. Source Classification Standard

### 4.1 Taxonomy (Normative)

**BGS-S-007** Sources MUST be classified using the BKR `REGISTRIES/source_taxonomy.md`. `volume-1-bkgc/APPENDICES/B_universal_source_taxonomy.md`.

Sources MUST be classified using the BKR `REGISTRIES/source_taxonomy.md`.

### 4.2 Source Weight Override (Normative)

**BGS-S-008** A source's default weight MAY be overridden based on provenance strength, corroboration, and jurisdictional relevance. Overrides MUST be documented.

## 5. Claim Status Assignment

### 5.1 Status Determination (Normative)

**BGS-S-009** A claim status MUST be determined by: BKGC Article XV § 15.1.

A claim status MUST be determined by:

- Highest authority level supporting the claim
- Jurisdictional match
- Evidence confidence score
- Presence of counter-evidence
- Recency and temporal validity

### 5.2 Status Downgrade (Normative)

**BGS-S-010** A claim status MUST be downgraded when:

- A higher authority contradicts it.
- New counter-evidence is material.
- The authority is found stale.
- The jurisdiction is mismatched.

## 6. Review Workflow Standard

### 6.1 Review Levels

| Level | Actor | Scope |
|-------|-------|-------|
| R0 | Automated | Metadata completeness, schema conformance |
| R1 | Agent | Evidence sufficiency, reasoning chain |
| R2 | Human | Consequential, novel, or high-risk conclusions |
| R3 | Panel | Constitutional or major governance questions |

### 6.2 Review Record (Normative)

**BGS-S-012** Every review MUST produce:

- Review ID
- Reviewer identity
- Date
- Scope
- Findings
- Required actions
- Outcome

## 7. Failure Mode Handling

### 7.1 Failure Taxonomy (Informative)

Derived from BKGC Article XXI § 21.1.

### 7.2 Severity Levels

| Severity | Definition | Response |
|----------|------------|----------|
| Informational | Minor issue, no material impact | Log only |
| Warning | Potential issue, requires monitoring | Notify reviewer |
| Major | Material impact on a claim or decision | Suspend claim pending review |
| Critical | Integrity of evidence or reasoning compromised | Quarantine and escalate |

### 7.3 Failure Remediation (Normative)

**BGS-S-014** Every failure mode in the catalog MUST have a documented remediation path. Remediation outcomes MUST be logged.

## 8. Decision Ledger Standard

### 8.1 Decision Record (Normative)

**BGS-S-015** Every significant decision MUST be recorded with:

- Decision ID
- Question
- Alternatives considered
- Evidence used
- Rejected evidence and reason
- Governing authority
- Reasoning chain
- Confidence
- Reviewer
- Timestamp

### 8.2 Supersession (Normative)

**BGS-S-016** When a decision is superseded, the original record MUST be preserved and linked to the superseding decision.

## 9. Constitutional Compliance Scoring

### 9.1 Scoring Dimensions (Normative)

**BGS-S-017** A compliance score SHOULD evaluate:

- Citation integrity
- Provenance completeness
- Jurisdiction accuracy
- Temporal accuracy
- Counter-evidence review
- Confidence calibration
- Transparency
- Auditability
- Reproducibility
- Evidence preservation

### 9.2 Pass Threshold

A conclusion MUST achieve a passing score in all required dimensions before it is treated as operational knowledge.

## 10. Amendment Compatibility

### 10.1 Downstream Impact Assessment

When BGS is amended, the amendment MUST include an impact assessment for BKC, BRA, BCCM, BKR, and BGC.

### 10.2 Transition Period

Major BGS amendments MAY include a transition period. During the transition, both old and new standards MAY be applied, provided the difference is documented.
