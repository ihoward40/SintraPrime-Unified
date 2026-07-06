# Blackstone Reference Architecture (BRA)

## Volume III — Technical Implementation Guidance

### Version 2.0

---

## Preamble

This volume translates the Blackstone Knowledge Governance Constitution (BKGC) and Blackstone Governance Standards (BGS) into technical implementation guidance. It describes engines, interfaces, data structures, workflows, and integration patterns that realize constitutional and standard-level requirements.

BRA is implementation-neutral in principle, but it is also practical: it maps concepts to concrete patterns that can be adopted by Hermes, Blackstone, SintraPrime-Unified, Mission Control, and future agents.

---

## 1. Architectural Principles

1.1. **Constitutional Compliance by Design.** Every engine and interface shall have a clearly identifiable path to one or more BKGC articles or BGS sections.

1.2. **Separation of Concerns.** Knowledge governance, decision governance, evidence management, reasoning, provenance, and audit shall be separable components.

1.3. **Tamper-Evident Logging.** All significant actions shall be recorded in an append-only, integrity-protected audit trail.

1.4. **Human-in-the-Loop.** High-stakes decisions require explicit human authorization.

1.5. **Reproducibility.** Every evaluation shall be reconstructible from stored evidence, metadata, and reasoning records.

1.6. **Extensibility.** New sources, agents, jurisdictions, and claim types shall be addable without rewriting the architecture.

---

## 2. Ecosystem Reference Model

```
BKGC (Volume I)
    │
    ▼
BGS (Volume II)
    │
    ▼
BRA (Volume III)
    │
    ├── Knowledge Kernel
    │       ├── Evidence Engine
    │       ├── Authority Engine
    │       ├── Reasoning Engine
    │       ├── Provenance Engine
    │       └── Risk Engine
    │
    ├── Decision Layer
    │       ├── Human Review Gateway
    │       ├── Approval Engine
    │       └── Intervention Controller
    │
    ├── Registry Layer
    │       ├── Source Registry
    │       ├── Claim Registry
    │       ├── Jurisdiction Registry
    │       └── CDR Registry
    │
    └── Audit Layer
            ├── Evidence Ledger
            ├── Constitutional Compliance Score Engine
            └── Audit Trail


            ▼

Hermes, Blackstone, SintraPrime-Unified, Mission Control, Future Agents
```

---

## 3. Component Definitions

### 3.1. Knowledge Kernel

The Knowledge Kernel is the central runtime for evaluating, classifying, and versioning knowledge objects. It coordinates the Evidence, Authority, Reasoning, Provenance, and Risk Engines.

### 3.2. Evidence Engine

- Ingests evidence items from sources.
- Computes integrity hashes.
- Records provenance and chain of custody.
- Stores entries in the Constitutional Evidence Ledger.

### 3.3. Authority Engine

- Identifies whether a source is controlling, persuasive, historical, scholarly, or otherwise authoritative within a jurisdiction.
- Applies the Source Taxonomy and Claim Taxonomy from BGS.
- Records jurisdiction-specific authority status.

### 3.4. Reasoning Engine

- Evaluates claims according to evidence.
- Produces reasoning records.
- Assigns confidence levels and maturity stages.
- Preserves counter-evidence and competing interpretations.

### 3.5. Provenance Engine

- Tracks origin, custody, transformations, and review history.
- Interfaces with SintraPrime-Unified's evidence pipeline (snapshot → packet → audit).
- Flags breaks in custody or unknown provenance.

### 3.6. Risk Engine

- Assesses operational, legal, financial, and reputational risk.
- Triggers human review when thresholds are exceeded.
- Records risk assessments in the audit trail.

### 3.7. Decision Layer

- Converts governed knowledge into recommendations.
- Requires human approval for high-risk or legally consequential actions.
- Keeps decision governance separate from knowledge governance.

### 3.8. Audit Layer

- Maintains the Constitutional Evidence Ledger.
- Computes Constitutional Compliance Scores.
- Provides tamper-evident audit trails.

---

## 4. Data Model Reference

### 4.1. Knowledge Object (`BKO`)

```json
{
  "bko_id": "BKO-LEGAL-000001",
  "version": "1.0.0",
  "created_at": "2026-07-06T12:00:00Z",
  "last_reviewed_at": "2026-07-06T14:00:00Z",
  "reviewer": "reviewer@ikesolutions.org",
  "jurisdiction": "US-FEDERAL",
  "subject_area": "TAX-PROCEDURE",
  "source_classification": ["GOVERNMENT_PRIMARY", "JUDICIAL"],
  "claim_classification": ["CONTROLLING"],
  "confidence": "HIGH",
  "maturity_stage": "OPERATIONAL",
  "claim": "A taxpayer may request currently not collectible status based on economic hardship.",
  "supporting_evidence": ["EV-000001", "EV-000002"],
  "counter_evidence": ["EV-000003"],
  "related_claims": ["BKO-LEGAL-000010"],
  "supersedes": null,
  "reasoning_record_id": "RR-000001",
  "compliance_score": 94
}
```

### 4.2. Evidence Item (`EV`)

```json
{
  "evidence_id": "EV-000001",
  "source_id": "SRC-IRC-0001",
  "collection_date": "2026-07-06T12:00:00Z",
  "collection_method": "OFFICIAL_DOWNLOAD",
  "hash": "sha256:abc123...",
  "version": "1.0.0",
  "chain_of_custody": [
    {"event": "DOWNLOAD", "actor": "hermes", "timestamp": "2026-07-06T12:00:00Z"},
    {"event": "VERIFY", "actor": "blackstone", "timestamp": "2026-07-06T12:05:00Z"}
  ],
  "validation_history": [
    {"check": "HASH_MATCH", "result": "PASS", "timestamp": "2026-07-06T12:05:00Z"}
  ],
  "related_claims": ["BKO-LEGAL-000001"],
  "jurisdiction": "US-FEDERAL",
  "classification": "GOVERNMENT_PRIMARY",
  "integrity_status": "INTACT",
  "archive_status": "ACTIVE"
}
```

### 4.3. Reasoning Record (`RR`)

```json
{
  "reasoning_record_id": "RR-000001",
  "bko_id": "BKO-LEGAL-000001",
  "question_asked": "What hardship protections exist for an individual taxpayer unable to pay assessed tax?",
  "evidence_considered": ["EV-000001", "EV-000002", "EV-000003"],
  "authorities_consulted": ["IRS Form 656", "IRC 6159", "IRM 5.16.1"],
  "assumptions": ["Taxpayer is an individual, not a business entity."],
  "alternatives_considered": ["Offer in Compromise", "Installment Agreement"],
  "selected_conclusion": "CNC status is available if hardship criteria are met.",
  "why_selected": "Directly supported by controlling IRS authority and the taxpayer's documented hardship.",
  "could_change_if": ["Hardship documentation is found incomplete.", "IRS policy changes."]
}
```

### 4.4. Constitutional Decision Record (`CDR`)

See BGS Section 3 for CDR schema. In BRA, CDRs are stored as versioned JSON or Markdown documents in `registry/cdr/`.

---

## 5. Engine Interfaces

### 5.1. Evidence Engine Interface

```python
def ingest(source_ref: SourceRef, collector: ActorRef) -> EvidenceItem:
    """Ingest evidence, compute hash, record provenance."""

def verify(evidence_id: str) -> VerificationResult:
    """Verify integrity and custody of an evidence item."""

def get_custody_chain(evidence_id: str) -> list[CustodyEvent]:
    """Return the documented chain of custody."""
```

### 5.2. Authority Engine Interface

```python
def classify_source(source: SourceRef, jurisdiction: str) -> SourceClassification:
    """Classify a source within a jurisdiction."""

def classify_claim(claim: Claim, jurisdiction: str) -> list[ClaimClassification]:
    """Classify a claim's legal status within a jurisdiction."""

def is_controlling(claim: Claim, jurisdiction: str) -> bool:
    """Return whether a claim is supported by controlling authority."""
```

### 5.3. Reasoning Engine Interface

```python
def evaluate(claim: Claim, evidence: list[EvidenceItem]) -> ReasoningRecord:
    """Evaluate a claim against evidence and produce a reasoning record."""

def assign_confidence(reasoning: ReasoningRecord) -> ConfidenceLevel:
    """Assign a confidence level based on evidence strength."""

def promote(bko_id: str, target_stage: MaturityStage, reviewer: ActorRef) -> BKO:
    """Promote a knowledge object to a new maturity stage."""
```

### 5.4. Provenance Engine Interface

```python
def record_origin(evidence_id: str, origin: OriginRecord) -> None:
    """Record the origin of an evidence item."""

def record_transformation(evidence_id: str, transformation: TransformationRecord) -> None:
    """Record any transformation applied to an evidence item."""

def flag_break(evidence_id: str, reason: str) -> ProvenanceAlert:
    """Flag a break in provenance or custody."""
```

### 5.5. Risk Engine Interface

```python
def assess_action(action: Action, context: Context) -> RiskAssessment:
    """Assess the risk of a proposed action."""

def requires_human_review(assessment: RiskAssessment) -> bool:
    """Return whether the action requires human review."""
```

### 5.6. Compliance Score Engine Interface

```python
def score(bko: BKO) -> ComplianceScore:
    """Compute a Constitutional Compliance Score for a knowledge object."""

def report(bko_id: str) -> ComplianceReport:
    """Return a detailed compliance report."""
```

---

## 6. Workflows

### 6.1. Knowledge Object Creation Workflow

1. Agent or human submits a claim.
2. Evidence Engine ingests supporting evidence.
3. Provenance Engine records origin and custody.
4. Authority Engine classifies sources and claims.
5. Reasoning Engine evaluates the claim and assigns confidence.
6. Compliance Score Engine computes a score.
7. Knowledge Object is stored at `IDEA` or `HYPOTHESIS` stage.
8. Curator or reviewer advances the object through maturity stages.

### 6.2. Human Review Workflow

1. Risk Engine assesses recommendation.
2. If threshold is exceeded, a Human Review Request is created.
3. Reviewer is presented with evidence, confidence, counter-evidence, and reasoning.
4. Reviewer approves, rejects, or requests changes.
5. Override, if any, is logged in the audit trail.
6. Decision Layer proceeds or aborts.

### 6.3. Multi-Agent Review Workflow

1. Multiple agents evaluate the same question.
2. Each agent produces an independent reasoning record.
3. System records areas of agreement and disagreement.
4. If consensus is not possible, the output is marked `DISPUTED`.
5. Contributing agents are attributed.

### 6.4. Amendment and Supersession Workflow

1. New evidence or reasoning undermines an existing `BKO`.
2. A new version of the `BKO` is created.
3. The new version supersedes the old version.
4. The old version is moved to `HISTORICAL ARCHIVE`.
5. Related claims and CDRs are updated.

---

## 7. Integration Patterns

### 7.1. SintraPrime-Unified Evidence Pipeline

| BKGC/BGS Concept | SintraPrime-Unified Component |
|------------------|-------------------------------|
| Evidence Item | Raw evidence source material |
| Knowledge Object | `EvidenceSnapshot` |
| Rendered Presentation | `PacketRenderer` output |
| Audit Trail | `AuditRecord` via `AuditService` |
| Chain of Custody | Provenance replay acceptance tests (AT-5) |
| Integrity Check | Snapshot hash, packet hash |

### 7.2. Hermes Orchestration

Hermes acts as the orchestration agent:
- Dispatches tasks to Blackstone engines.
- Requests human review when required.
- Logs all significant actions.
- Refuses tasks that would violate the Constitution or Standards.

### 7.3. Mission Control

Mission Control provides operational command and monitoring:
- Can trigger or halt workflows.
- Displays Compliance Scores and audit dashboards.
- Does not override knowledge governance without a documented CDR and human authorization.

---

## 8. APIs and Events

### 8.1. Core API Surface

| Endpoint | Purpose |
|----------|---------|
| `POST /knowledge` | Create a knowledge object. |
| `GET /knowledge/{bko_id}` | Retrieve a knowledge object. |
| `POST /knowledge/{bko_id}/evidence` | Attach evidence to a knowledge object. |
| `POST /knowledge/{bko_id}/promote` | Request maturity-stage promotion. |
| `POST /knowledge/{bko_id}/review` | Submit human review. |
| `GET /knowledge/{bko_id}/compliance` | Retrieve compliance score. |
| `POST /evidence/ingest` | Ingest an evidence item. |
| `GET /evidence/{evidence_id}/custody` | Retrieve chain of custody. |
| `GET /cdr` | List constitutional decision records. |
| `GET /audit` | Query audit trail. |

### 8.2. Core Events

| Event | Description |
|-------|-------------|
| `knowledge.created` | A knowledge object was created. |
| `knowledge.promoted` | A knowledge object advanced in maturity. |
| `knowledge.demoted` | A knowledge object was demoted. |
| `evidence.ingested` | An evidence item was ingested. |
| `evidence.verified` | An evidence item passed or failed verification. |
| `review.requested` | Human review was requested. |
| `review.completed` | Human review was completed. |
| `compliance.scored` | A compliance score was computed. |

---

## 9. Storage and Persistence

### 9.1. Recommended Storage

- Knowledge objects and evidence metadata: relational or graph database.
- Evidence content: object storage with integrity hashes.
- Audit trail: append-only log with tamper-evident checksums.
- CDRs and registry entries: version-controlled files in the Blackstone Knowledge Registry.

### 9.2. Versioning

- Knowledge objects use semantic versioning.
- Evidence items use simple integer versions.
- CDRs are immutable once ratified; superseded CDRs retain their original identifiers.

---

## 10. Security Considerations

10.1. All engine-to-engine communication should be authenticated and authorized.

10.2. Privileged or confidential knowledge objects shall be encrypted at rest and in transit.

10.3. Audit logs shall be append-only and integrity-protected.

10.4. Human review interfaces shall require strong authentication for high-risk actions.

10.5. Agent credentials shall follow least-privilege principles.

---

## 11. Future Extensions

11.1. **Knowledge Graph.** Link related claims, authorities, and evidence items.

11.2. **Automated Jurisdiction Detection.** Infer jurisdiction from source metadata and claim context.

11.3. **Differential Privacy.** Protect sensitive litigant or client information in aggregate analytics.

11.4. **Model Cards.** Document the capabilities, limitations, and training provenance of AI models used by the Reasoning Engine.

---

## 12. Mapping to Volumes I and II

| BRA Section | BKGC Articles | BGS Sections |
|-------------|---------------|--------------|
| Knowledge Kernel | VI, VII, VIII | 4, 5, 6, 7 |
| Authority Engine | IX, X, XIV, XVI | 6, 9 |
| Reasoning Engine | V, XVII, XVIII, XXIII | 7, 8, 14 |
| Provenance Engine | VIII, XII | 8 |
| Risk Engine | XXIX | 10, 16 |
| Decision Layer | XX, XXI | 10 |
| Audit Layer | XXV, XXVI, XXVII | 3, 12, 13 |
| Registry Layer | XXV, XXXV | 3, 5, 6 |

---

*Blackstone Reference Architecture, Volume III — Technical Implementation Guidance, Version 2.0*
