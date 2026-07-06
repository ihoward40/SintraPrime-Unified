# Blackstone Governance Standards (BGS)

## Volume II — Operational Standards

### Version 2.0

---

## Preamble

This volume operationalizes the Blackstone Knowledge Governance Constitution (BKGC) through concrete standards, schemas, protocols, and procedures. It governs the day-to-day evaluation, classification, review, and preservation of knowledge objects within the Blackstone Ecosystem.

Where the Constitution establishes principles, this volume establishes the rules by which those principles are applied.

---

## 1. Scope and Relationship to the Constitution

1.1. BGS is subordinate to BKGC. Any BGS provision that conflicts with BKGC is invalid and must be amended.

1.2. BGS applies to all agents, systems, and human reviewers that produce, modify, evaluate, or rely upon knowledge objects.

1.3. BGS may be amended through the CDR process defined in BKGC Article XXV and Section 15 of this volume.

---

## 2. Governance Roles

### 2.1. Governance Board

- Ratifies amendments to BGS.
- Reviews material constitutional violations.
- Authorizes exceptions to standards where justified by a CDR.

### 2.2. Human Reviewer

- Approves, rejects, or overrides knowledge objects and recommendations.
- Documents reasoning for overrides.
- Bears responsibility for high-stakes or legally consequential decisions.

### 2.3. Agent Operator

- Executes tasks under constitutional and standard-compliant configuration.
- Logs evidence, reasoning, and uncertainty.
- Escalates boundary conditions to human reviewers.

### 2.4. Evidence Curator

- Maintains source taxonomy, claim taxonomy, and jurisdiction registry.
- Reviews and updates metadata standards.
- Ensures the Blackstone Knowledge Registry remains accurate.

---

## 3. Constitutional Decision Record (CDR) Standard

### 3.1. CDR Identifier Format

`CDR-{YYYY}-{NNNN}` where:
- `{YYYY}` is the ratification year.
- `{NNNN}` is a zero-padded sequential number.

### 3.2. Required CDR Fields

| Field | Description |
|-------|-------------|
| CDR ID | Unique identifier. |
| Question | The governance or architectural question asked. |
| Decision | The decision made. |
| Reasoning | The reasoning supporting the decision. |
| Evidence | Relevant evidence items, BKGC articles, prior CDRs. |
| Alternatives Considered | Other options evaluated and why they were not selected. |
| Risks | Identified risks and mitigations. |
| Approved By | Governance board or authorized reviewer. |
| Effective Date | Date the decision takes effect. |
| Supersedes | Prior CDRs replaced by this decision, if any. |
| Status | `DRAFT`, `RATIFIED`, `SUPERSEDED`, or `WITHDRAWN`. |

### 3.3. CDR Lifecycle

- **DRAFT:** Under preparation and review.
- **RATIFIED:** Approved and effective.
- **SUPERSEDED:** Replaced by a later CDR.
- **WITHDRAWN:** Withdrawn without replacement; reason recorded.

### 3.4. CDR Storage

CDRs are stored in the Blackstone Knowledge Registry under `registry/cdr/`.

---

## 4. Knowledge Object Lifecycle Standard

### 4.1. Required Metadata

Every knowledge object shall include the metadata fields required by BKGC Article XXXV.

| Field | Format | Required |
|-------|--------|----------|
| `bko_id` | `BKO-{domain}-{NNNNNN}` | Yes |
| `version` | Semantic version (`MAJOR.MINOR.PATCH`) | Yes |
| `created_at` | ISO 8601 UTC timestamp | Yes |
| `last_reviewed_at` | ISO 8601 UTC timestamp | No |
| `reviewer` | Identifier of last human reviewer | No |
| `jurisdiction` | Jurisdiction code from registry | Yes, when applicable |
| `subject_area` | Controlled vocabulary term | Yes |
| `source_classification` | From Source Taxonomy | Yes |
| `claim_classification` | From Claim Taxonomy | Yes |
| `confidence` | `HIGH`, `MODERATE`, `LIMITED`, `PRELIMINARY`, `INSUFFICIENT` | Yes |
| `related_claims` | List of `bko_id` references | No |
| `supersedes` | Prior `bko_id` and version | No |

### 4.2. Maturity Stage Transitions

| From | To | Required Evidence | Approver |
|------|----|-------------------|----------|
| IDEA | HYPOTHESIS | Identified evidence pathway | Agent Operator |
| HYPOTHESIS | RESEARCH | Evidence collection plan | Agent Operator |
| RESEARCH | CORROBORATED | At least one corroborating source | Evidence Curator or Agent Operator |
| CORROBORATED | VERIFIED | Verification protocol completed | Evidence Curator |
| VERIFIED | OPERATIONAL | Operational risk review passed | Human Reviewer |
| OPERATIONAL | LITIGATION-READY | Chain of custody and audit trail verified | Human Reviewer |
| Any | HISTORICAL ARCHIVE | Object superseded or no longer operational | Evidence Curator |

### 4.3. Demotion Rules

A knowledge object may be demoted when:
- New evidence undermines prior verification.
- A controlling authority changes or is repealed.
- Counter-evidence previously omitted is discovered.
- The object has not been reviewed within its required review window.

---

## 5. Source Taxonomy

### 5.1. Source Classifications

| Classification | Definition |
|----------------|------------|
| `GOVERNMENT_PRIMARY` | Official government records, statutes, regulations, court filings. |
| `JUDICIAL` | Court opinions, orders, and rulings. |
| `LEGISLATIVE` | Statutes, bills, legislative history. |
| `ACADEMIC` | Peer-reviewed scholarship, law reviews, university publications. |
| `COMMERCIAL` | Commercially published treatises, guides, and databases. |
| `PRIVATE_PUBLICATION` | Privately published treatises, manuals, and research. |
| `HISTORICAL_ARCHIVE` | Archival materials, historical records, out-of-print sources. |
| `INSTITUTIONAL_MANUAL` | Procedures, guidelines, and manuals from private institutions. |
| `AI_GENERATED` | Outputs generated by artificial intelligence systems. |
| `UNSOURCED` | Source cannot be identified or authenticated. |

### 5.2. Source Reliability Assessment

Reliability is evaluated across four dimensions:

| Dimension | Question |
|-----------|----------|
| Authenticity | Is the source what it claims to be? |
| Provenance | Can its origin and custody be documented? |
| Corroboration | Is it supported by independent sources? |
| Internal Consistency | Is it internally coherent and free of contradictions? |

Each dimension is scored `STRONG`, `ADEQUATE`, `WEAK`, or `UNKNOWN`.

### 5.3. Origin Neutrality Rule

No source classification is assigned a default reliability score. A `GOVERNMENT_PRIMARY` source may score `WEAK` if its provenance is unknown, and a `PRIVATE_PUBLICATION` source may score `STRONG` if it is authentic, corroborated, and internally consistent.

---

## 6. Claim Taxonomy

### 6.1. Claim Classifications

| Classification | Definition |
|----------------|------------|
| `CONTROLLING` | Supported by governing legal authority within the relevant jurisdiction. |
| `PERSUASIVE` | Supported by respected but non-controlling authority. |
| `HISTORICALLY_DOCUMENTED` | Supported by historical evidence but not necessarily current law. |
| `SCHOLARLY` | Derived primarily from academic analysis. |
| `EDUCATIONAL` | Intended for learning and explanation. |
| `EMERGING` | Supported by limited evidence requiring further validation. |
| `DISPUTED` | Credible authorities materially disagree. |
| `UNVERIFIED` | Insufficient evidence currently available. |

### 6.2. Multi-Status Claims

A single claim may carry multiple classifications when its legal status varies by jurisdiction or context. All applicable classifications shall be recorded.

### 6.3. Claim Status Display

When presenting a claim to a user, the system shall display:
- The claim classification.
- The jurisdiction to which it applies.
- The confidence level.
- A concise explanation of the evidence basis.

---

## 7. Evidence Evaluation Protocol

### 7.1. Required Questions

For every significant claim, the system shall record answers to:

1. What evidence supports the claim?
2. What evidence challenges the claim?
3. What evidence is still missing?
4. What additional evidence would materially change the conclusion?

### 7.2. Evidence Sufficiency Thresholds

| Threshold | Standard |
|-----------|----------|
| **Citation** | A specific, verifiable source exists. |
| **Corroboration** | At least one independent source supports the claim. |
| **Controlling Authority** | A binding authority in the relevant jurisdiction supports the claim. |
| **Chain of Custody** | The evidence item's provenance is documented. |
| **Temporal Relevance** | The authority or evidence is currently effective or its historical status is explicit. |

### 7.3. Counter-Evidence Handling

- Material counter-evidence shall be preserved.
- The reasoning record shall explain how counter-evidence was weighed.
- A claim that omits material counter-evidence receives a lower Compliance Score.

---

## 8. Provenance and Chain of Custody Standard

### 8.1. Provenance Metadata

| Field | Description |
|-------|-------------|
| `source_id` | Identifier of the originating source. |
| `collection_date` | When the evidence was collected. |
| `collection_method` | How the evidence was obtained. |
| `collector` | Agent or human who collected the evidence. |
| `transformations` | List of modifications, normalizations, or derivations. |
| `review_history` | List of reviews, reviewers, dates, and outcomes. |

### 8.2. Chain of Custody Requirements

- Every transformation of an evidence item shall be documented.
- Any break in custody shall be flagged and explained.
- Integrity checks (hash, checksum, signature) shall be preserved where applicable.

### 8.3. Unknown Provenance

Unknown provenance shall be recorded as `UNKNOWN` and shall reduce the source reliability score accordingly. Fabricated or inferred provenance is prohibited.

---

## 9. Jurisdiction and Temporal Standard

### 9.1. Jurisdiction Metadata

| Field | Description |
|-------|-------------|
| `jurisdiction_code` | Standard code from the jurisdiction registry. |
| `authority_name` | Name of the controlling or persuasive authority. |
| `authority_level` | `FEDERAL`, `STATE`, `LOCAL`, `TRIBAL`, `INTERNATIONAL`, `ADMINISTRATIVE`, `PRIVATE`. |
| `effective_date` | Date the authority took effect. |

### 9.2. Temporal Metadata

| Field | Description |
|-------|-------------|
| `effective_date` | When the authority or evidence became effective. |
| `review_date` | When it was last reviewed. |
| `amendment_history` | List of amendments, repeals, or updates. |
| `expiration_date` | When it expires, if applicable. |
| `historical_status` | `CURRENT`, `AMENDED`, `REPEALED`, `SUPERSEDED`, `HISTORICAL`. |

### 9.3. Cross-Jurisdictional Conflicts

When authorities from multiple jurisdictions conflict:
- Each authority is recorded with its jurisdiction.
- The system shall identify the conflict.
- The system shall not resolve the conflict by inference unless a recognized choice-of-law principle is documented.

---

## 10. Review Protocols

### 10.1. Review Levels

| Level | Trigger | Reviewer |
|-------|---------|----------|
| **Automated** | Low-risk, routine knowledge objects | Agent Operator |
| **Curatorial** | New sources, classifications, or taxonomy entries | Evidence Curator |
| **Human** | High-stakes, legally consequential, or disputed claims | Human Reviewer |
| **Governance Board** | Constitutional amendments, exceptions, or escalations | Governance Board |

### 10.2. Human Review Requirements

Human review is required before:
- Promoting a knowledge object to `OPERATIONAL` or `LITIGATION-READY`.
- Recommending a legally consequential action.
- Overriding a verified conclusion.
- Using a `DISPUTED` or `UNVERIFIED` claim in an operational recommendation.

### 10.3. Override Documentation

When a human reviewer overrides a system conclusion, the following shall be recorded:
- The reviewer's identity.
- The original system conclusion.
- The override conclusion.
- The reasoning.
- The date and time.

---

## 11. Multi-Agent Review Protocol

### 11.1. Preserved Outputs

When multiple agents participate in an analysis, the system shall preserve:
- Each agent's reasoning.
- Areas of agreement.
- Areas of disagreement.
- The evidence each agent relied upon.

### 11.2. No Forced Consensus

The system shall not force consensus where evidence remains divided. Disagreement shall be recorded and presented to the user.

### 11.3. Attribution

Final conclusions shall identify the contributing agents or reviewers.

---

## 12. Constitutional Compliance Score Standard

### 12.1. Scoring Dimensions

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Citation Integrity | 15% | Claims are traceable to specific sources. |
| Provenance Completeness | 15% | Origin, custody, and transformations are documented. |
| Jurisdiction Accuracy | 10% | Controlling and persuasive authorities are correctly assigned to jurisdictions. |
| Temporal Accuracy | 10% | Effective dates, amendments, and historical status are documented. |
| Counter-Evidence Review | 15% | Material contrary evidence is preserved and weighed. |
| Confidence Calibration | 10% | Confidence reflects evidence strength. |
| Transparency | 10% | Reasoning, assumptions, and alternatives are documented. |
| Auditability | 10% | All significant actions are logged. |
| Reproducibility | 5% | The evaluation can be reproduced from recorded evidence. |

### 12.2. Score Interpretation

| Score Range | Meaning |
|-------------|---------|
| 90–100 | Strong constitutional compliance. |
| 75–89 | Adequate compliance with minor gaps. |
| 60–74 | Conditional compliance; human review recommended. |
| Below 60 | Non-compliant; not suitable for operational use without remediation. |

### 12.3. Score Is Process-Based

The Compliance Score measures adherence to governance process, not whether the conclusion aligns with any particular viewpoint.

---

## 13. Constitutional Evidence Ledger Standard

### 13.1. Ledger Entry Format

| Field | Description |
|-------|-------------|
| `evidence_id` | Unique identifier (`EV-{NNNNNN}`). |
| `source_id` | Reference to the source registry entry. |
| `collection_date` | ISO 8601 UTC timestamp. |
| `collection_method` | Controlled vocabulary. |
| `hash` | Cryptographic hash when applicable. |
| `version` | Version of the evidence item. |
| `chain_of_custody` | Ordered list of custody events. |
| `validation_history` | Reviews, checks, and outcomes. |
| `related_claims` | List of `bko_id` references. |
| `jurisdiction` | Jurisdiction code. |
| `classification` | Source classification. |
| `integrity_status` | `INTACT`, `ALTERED`, `UNKNOWN`, `DEGRADED`. |
| `archive_status` | `ACTIVE`, `PRESERVED`, `SCHEDULED_FOR_DELETION`, `DELETED`. |

### 13.2. Integrity Status Rules

- `INTACT`: Hash or custody checks pass.
- `ALTERED`: A change was detected in the evidence item.
- `UNKNOWN`: No integrity check is available.
- `DEGRADED`: Partial custody or metadata loss occurred.

### 13.3. Deletion Policy

Deletion is permitted only when:
- Legally appropriate.
- Not subject to a preservation obligation.
- Authorized by a CDR.
- Logged in the audit trail.

---

## 14. Uncertainty and Confidence Standard

### 14.1. Confidence Levels

| Level | Criteria |
|-------|----------|
| `HIGH` | Strong, corroborated evidence and controlling or persuasive authority. |
| `MODERATE` | Substantial evidence, but with gaps or non-controlling authority. |
| `LIMITED` | Some supporting evidence, but significant uncertainty or limited corroboration. |
| `PRELIMINARY` | Early-stage evaluation; further evidence is expected to change the conclusion. |
| `INSUFFICIENT` | Not enough evidence to support a meaningful conclusion. |

### 14.2. Confidence Explanation

Every confidence assignment shall include a brief explanation of the evidence basis.

### 14.3. Confidence Updates

Confidence levels shall be updated as new evidence becomes available or as existing evidence is undermined.

---

## 15. Amendment and Exception Process

### 15.1. Proposing Amendments

Amendments to BGS may be proposed by:
- A Human Reviewer.
- The Governance Board.
- A CDR that identifies an inconsistency between BGS and BKGC.

### 15.2. Exception Requests

Temporary exceptions to BGS may be authorized by the Governance Board through a CDR that documents:
- The exception.
- The reason.
- The risk.
- The duration or conditions for expiration.

### 15.3. Ratification

BGS amendments are ratified by a majority vote of the Governance Board or by the authorized decision authority in the CDR.

---

## 16. Security and Privacy Standards

### 16.1. Least Privilege

Access to knowledge objects shall be granted at the minimum level necessary for the actor's role.

### 16.2. Data Classification

Knowledge objects shall be classified by sensitivity:

| Classification | Handling |
|----------------|----------|
| `PUBLIC` | May be shared freely. |
| `INTERNAL` | Limited to ecosystem participants. |
| `CONFIDENTIAL` | Restricted to authorized reviewers. |
| `PRIVILEGED` | Protected by legal privilege; access strictly controlled. |

### 16.3. Audit Logging

All significant actions shall be logged in a tamper-evident manner, including:
- Creation, modification, and deletion of knowledge objects.
- Promotion and demotion of maturity stages.
- Human overrides.
- Exception approvals.

### 16.4. Evidence Preservation

Evidence subject to legal or constitutional preservation obligations shall not be deleted, altered, or hidden.

---

## 17. Integration with SintraPrime-Unified

### 17.1. Evidence Pipeline Mapping

| BKGC/BGS Concept | SintraPrime-Unified Mapping |
|------------------|-----------------------------|
| Knowledge Object | EvidenceSnapshot, AuditRecord, rendered packets |
| Evidence Item | EvidenceSnapshot source material |
| Provenance Chain | Snapshot → Packet → AuditRecord linkage |
| Chain of Custody | Hash boundary and provenance replay tests |
| Constitutional Evidence Ledger | AuditService and evidence registry |
| Maturity Stage | Workflow status and review gates |

### 17.2. Existing Governance Records

The following existing records remain in force for their specific operational and decision authority purposes:

- `governance/GOVERNANCE.md`
- `docs/governance/VR-001-S5-GOVERNANCE-DECISION.md`
- `docs/governance/GI-B-2026-001-CLOSURE.md`
- `VR-001_STEP4_GOVERNANCE_DECISION.md`

Where any existing record conflicts with BKGC or BGS, the conflict shall be resolved under BKGC Article XIX and the existing record shall be updated or annotated.

---

## 18. Implementation Notes

18.1. This volume is standards-level. Technical implementation details belong in Volume III (Blackstone Reference Architecture).

18.2. Compliance testing criteria belong in Volume IV (Blackstone Certification & Compliance Manual).

18.3. Canonical definitions, taxonomy entries, and CDRs belong in Volume V (Blackstone Knowledge Registry).

---

*Blackstone Governance Standards, Volume II — Operational Standards, Version 2.0*
