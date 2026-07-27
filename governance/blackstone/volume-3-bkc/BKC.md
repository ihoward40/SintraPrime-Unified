---
version: 1.0.0
effective_date: 2026-07-27
status: draft
supersedes: []
derived_from: [BGS v1.0.0, BKGC v2.0]
---

# Blackstone Knowledge Core (BKC)

## Purpose (Informative)

The Blackstone Knowledge Core defines the shared semantic model for the Blackstone ecosystem. It governs **meaning**: the definitions, relationships, ontologies, and lifecycle states that every agent uses when handling claims, evidence, authorities, and decisions.

By standardizing these concepts, BKC prevents one agent from using "verified" differently than another. It is the semantic operating system every agent shares.

## Dependency (Normative)

**BKC-C-001 Semantic Authority.** BKC is the canonical semantic authority for all governance implementations. Every schema, ontology, registry, API, and engine in the ecosystem MUST derive its vocabulary from BKC.

BKC derives from `volume-2-bgs/BGS.md` and `volume-1-bkgc/BKGC.md`. It MUST NOT contradict either. BRA, BCCM, BKR, and BGC derive from BKC.

## 1. Core Ontology

### 1.1 Knowledge Object

A Knowledge Object is any entity in the ecosystem that carries meaning and can be governed. Examples include claims, evidence, authorities, sources, and decisions.

### 1.2 Core Concepts

| Concept | Definition | Derived From |
|---------|------------|--------------|
| **BKC-C-002** Claim | An assertion that can be supported, challenged, revised, or superseded by evidence. | BKGC § 1.2 |
| **BKC-C-003** Evidence | Material that supports or challenges a claim, with identifiable provenance. | BKGC § 1.3 |
| **BKC-C-004** Authority | Source recognized as controlling, persuasive, historical, scholarly, or educational. | BKGC § 1.4 |
| **BKC-C-005** Source | Origin of evidence. | BKGC § 5.1 |
| **BKC-C-006** Provenance | Documented origin, custody, and history of evidence. | BKGC § 1.5 |
| **BKC-C-007** Interpretation | Reasoned explanation of what evidence means for a claim. | BKGC § 29.1 |
| **BKC-C-008** Assumption | A premise accepted without direct evidence, explicitly declared. | BKGC § 18.1 |
| **BKC-C-009** Risk | Possibility that a conclusion is wrong or that evidence is flawed. | BGS 7 |
| **BKC-C-010** Jurisdiction | Legally or institutionally relevant scope. | BKGC § 1.6 |
| **BKC-C-011** Confidence | Evidence-derived measure of strength, not intuition. | BGS 3 |
| **BKC-C-012** Decision | Commitment to a conclusion or recommendation. | BKGC § 18.1 |
| **BKC-C-013** Review | Examination of a knowledge object for conformance. | BGS 6 |
| **BKC-C-014** Objection | Challenge to a claim, decision, or interpretation. | BKGC § 7.3 |
| **BKC-C-015** Counter-Evidence | Evidence that challenges a claim. | BKGC § 7.3 |
| **BKC-C-016** Revision | Updated version of a knowledge object. | BKGC § 25.3 |
| **BKC-C-017** Supersession | Replacement of a knowledge object by a newer one. | BGS 8.2 |

## 2. Knowledge Maturity Model

### 2.1 Lifecycle Stages

Every Knowledge Object progresses through defined stages:

```text
IDEA
    ↓
HYPOTHESIS
    ↓
RESEARCH
    ↓
CORROBORATED
    ↓
VERIFIED
    ↓
OPERATIONAL
    ↓
LITIGATION READY
    ↓
HISTORICAL ARCHIVE
```

### 2.2 Stage Definitions

| Stage | Definition | Exit Criteria |
|-------|------------|---------------|
| Idea | Initial thought or observation | Formulated as a question or hypothesis |
| Hypothesis | Testable proposition | Evidence collection plan defined |
| Research | Evidence collection in progress | At least one evidence item registered |
| Corroborated | Multiple sources align | Corroboration review passed |
| Verified | Independent verification completed | Verification record produced |
| Operational | Approved for operational use | R2 review passed |
| Litigation Ready | Audit trail and custody complete | Litigation readiness check passed |
| Historical Archive | Preserved for reference | No longer operational; archived |

### 2.3 Stage Transitions

A transition from one stage to the next MUST be recorded with:

- Transition timestamp
- Trigger
- Reviewer or agent identity
- Evidence or reason

## 3. Claim Ontology

### 3.1 Claim Structure

A Claim object has:

- Identifier (CID)
- Textual statement
- Status (from claim status taxonomy)
- Confidence score
- Supporting evidence set
- Counter-evidence set
- Reasoning chain reference
- Review history
- Version chain

### 3.2 Claim Relationships

| Relationship | Meaning |
|--------------|---------|
| supports | Evidence supports claim |
| challenges | Evidence challenges claim |
| supersedes | New claim replaces old claim |
| related | Claims share subject matter |
| depends_on | Claim relies on another claim |

## 4. Evidence Ontology

### 4.1 Evidence Structure

An Evidence object has:

- Identifier (EID)
- Source reference
- Content or content reference
- Provenance record
- Integrity hash
- Confidence score
- Jurisdiction
- Classification

### 4.2 Evidence Relationships

| Relationship | Meaning |
|--------------|---------|
| sourced_from | Evidence comes from a source |
| corroborates | Evidence supports another evidence item |
| contradicts | Evidence conflicts with another evidence item |
| derived_from | Evidence is a derivative of another evidence item |

## 5. Authority Ontology

### 5.1 Authority Structure

An Authority object has:

- Identifier (AID)
- Name or citation
- Authority type
- Jurisdiction
- Effective date
- Repeal or expiration date
- Source category
- Weight

### 5.2 Authority Types

| Type | Definition |
|------|------------|
| Controlling | Governs the question within its jurisdiction |
| Persuasive | Respected but non-controlling |
| Scholarly | Academic or analytical |
| Historical | Reflects past authority |
| Educational | Intended for explanation |

## 6. Decision Ontology

### 6.1 Decision Structure

A Decision object has:

- Identifier (DID)
- Question
- Selected alternative
- Alternatives considered
- Evidence used
- Rejected evidence and reasons
- Governing authority
- Reasoning chain
- Confidence
- Reviewer
- Timestamp
- Supersession link

### 6.2 Decision Lifecycle

```text
Proposed → Under Review → Approved → Operational → Superseded → Archived
```

## 7. Objection and Counter-Evidence Ontology

### 7.1 Objection Structure

An Objection object has:

- Identifier (OID)
- Target claim or decision
- Objection text
- Supporting evidence
- Severity
- Status
- Resolution

### 7.2 Counter-Evidence Structure

A Counter-Evidence object is an Evidence object explicitly linked as challenging a claim. It carries the same metadata as Evidence plus a challenge rationale.

## 8. Taxonomy Alignment

BKC does not replace BKR taxonomies. It provides the ontology within which BKR taxonomies are applied. BKR `REGISTRIES/` contains the authoritative enumerations; BKC defines the semantic structure.

## 9. API Implications

BRA MUST implement interfaces that enforce BKC object shapes. APIs receiving or returning governed knowledge SHOULD validate conformance to BKC schemas.

## 8. Governance Maturity Levels (Normative)

### 8.1 Levels

| Level | Name | Meaning |
|-------|------|---------|
| G0 | Concept | Idea identified, no formal definition |
| G1 | Draft | Initial definition or implementation drafted |
| G2 | Reviewed | Reviewed against upstream volumes |
| G3 | Ratified | Approved as baseline or standard |
| G4 | Implemented | Implemented in a conforming system |
| G5 | Certified | Passed BCCM certification |
| G6 | Operational | Used in production governance |
| G7 | Reference Standard | Recognized as ecosystem reference |

### 8.2 Usage

Every governance artifact SHOULD declare its maturity level. A level MAY advance only after the prior level's exit criteria are met and recorded.

