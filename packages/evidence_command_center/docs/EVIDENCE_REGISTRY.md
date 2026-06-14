# Evidence Registry

**Status:** DESIGN SPECIFICATION  
**Created:** 2026-06-14  
**Purpose:** Canonical inventory model for all evidence in Evidence Command Center

---

## What is Evidence?

**Evidence** is any document, file, recording, or artifact that:
1. Supports or refutes a legal claim
2. Has a verifiable source and acquisition date
3. Maintains an unbroken chain of custody
4. Can be authenticated for court admissibility

**Examples:**
- Credit reports (Experian, Equifax, TransUnion)
- Collection letters and notices
- Contracts and agreements
- Bank statements and payment records
- Screenshots and email correspondence
- Audio/video recordings
- Legal documents (complaints, motions, orders)
- Generated documents (affidavits, scorecards, analyses)

---

## Core Design Principles

1. **Unique Identification:** Every evidence item has a globally unique ID
2. **Immutable Core:** Once acquired, evidence content never changes (only metadata)
3. **Hash Verification:** SHA-256 hash ensures file integrity
4. **Chain of Custody:** Every action on evidence is recorded (see CHAIN_OF_CUSTODY.md)
5. **Source Traceability:** Clear record of where evidence originated
6. **Status Tracking:** Evidence progresses through defined lifecycle stages
7. **Multi-Linkage:** Evidence can link to multiple cases, violations, and exhibits

---

## Evidence Lifecycle

```
┌─────────────┐
│  ACQUIRED   │  Evidence enters system (upload, email, API, generated)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│PENDING      │  Awaiting initial review
│REVIEW       │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  REVIEWED   │  Human or AI review complete
└──────┬──────┘
       │
       ├────────────┐
       ▼            ▼
┌──────────┐  ┌──────────┐
│  TAGGED  │  │ REJECTED │  Evidence excluded from case
└────┬─────┘  └──────────┘
     │
     ▼
┌──────────┐
│  LINKED  │  Evidence linked to violations/exhibits
└────┬─────┘
     │
     ▼
┌──────────┐
│ APPROVED │  Attorney approves for case use
└────┬─────┘
     │
     ▼
┌──────────┐
│ ARCHIVED │  Case complete, evidence retained per policy
└──────────┘
```

---

## Data Model

### Core Fields

#### Identity
- **evidence_id** (UUID, primary key)
  - Globally unique identifier
  - Format: `EV-{year}-{sequence}` (e.g., `EV-2024-00001`)
  - Never reused, even if evidence deleted

- **case_id** (UUID, required)
  - Links evidence to legal case
  - One evidence item can link to multiple cases (junction table)

- **client_id** (UUID, optional)
  - Links evidence to specific client
  - May be null for general evidence (e.g., legal templates)

#### Source Information

- **source_type** (enum, required)
  - Values: `upload`, `email`, `fax`, `api`, `scan`, `generated`, `subpoena`, `discovery`
  - Determines acquisition workflow

- **source_reference** (text, optional)
  - Original filename for uploads
  - Email message ID for email attachments
  - API endpoint for automated acquisition
  - Document ID for generated content

- **date_acquired** (timestamp with timezone, required)
  - When evidence first entered system
  - Immutable after creation
  - Used for timeline analysis

- **acquired_by** (UUID, required)
  - User, client, or agent who acquired evidence
  - Links to users table or agent registry

#### File Information

- **file_name** (text, required)
  - Original or generated filename
  - Example: `credit_report_experian_2024_06_14.pdf`

- **file_size_bytes** (integer, required)
  - Size in bytes for storage accounting

- **mime_type** (text, required)
  - Examples: `application/pdf`, `image/png`, `audio/mp3`, `video/mp4`
  - Used for viewer selection and validation

- **storage_key** (text, required)
  - MinIO/S3 object key or file path
  - Format: `evidence/{case_id}/{evidence_id}/{filename}`

- **page_count** (integer, optional)
  - For PDF and document files
  - Used for exhibit indexing

#### Hash & Integrity

- **sha256_hash** (text, 64 chars, required, unique)
  - SHA-256 hash of file content
  - Used for:
    - Deduplication (detect identical uploads)
    - Integrity verification
    - Chain of custody verification
  - Computed on upload, never changes

- **integrity_verified** (boolean, default false)
  - Has hash been recently verified against stored file?

- **last_verified_at** (timestamp, optional)
  - When integrity was last checked
  - Schedule: Daily for active cases, weekly for archived

#### Classification

- **category** (text, required)
  - Primary classification
  - Examples:
    - `credit_report`
    - `collection_letter`
    - `contract`
    - `bank_statement`
    - `correspondence`
    - `legal_document`
    - `screenshot`
    - `recording`
    - `affidavit`
    - `scorecard`
    - `other`

- **subcategory** (text, optional)
  - Secondary classification
  - Examples for `credit_report`:
    - `experian`
    - `equifax`
    - `transunion`
    - `specialty_bureau`

- **tags** (array of text)
  - Flexible tagging for search
  - Examples: `["fcra_violation", "debt_validation", "disputed"]`
  - Can be added/removed (tracked in chain of custody)

#### Status & Workflow

- **status** (enum, required, default `pending_review`)
  - Values: `pending_review`, `reviewed`, `tagged`, `linked`, `approved`, `rejected`, `archived`
  - Determines available actions

- **review_status** (enum, optional)
  - Values: `unreviewed`, `ai_reviewed`, `human_reviewed`, `verified`
  - Distinguishes AI vs. human review

- **reviewed_by** (UUID, optional)
  - User or agent who performed review

- **reviewed_at** (timestamp, optional)
  - When review completed

- **rejection_reason** (text, optional)
  - Why evidence was rejected (if status = `rejected`)
  - Examples: "Duplicate of EV-2024-00023", "Not relevant to case", "Poor quality scan"

#### Violation Linkage

- **linked_violations** (array of UUIDs)
  - Violations this evidence supports
  - Many-to-many relationship (one evidence item can support multiple violations)

- **violation_confidence** (float, 0.0-1.0, optional)
  - AI-generated confidence score
  - How strongly does this evidence support the violation?

#### Metadata (Flexible)

- **metadata** (JSONB object)
  - Flexible storage for type-specific data
  - Examples:

**Credit Report:**
```json
{
  "bureau": "experian",
  "report_date": "2024-06-01",
  "tradelines": 15,
  "negative_items": 3,
  "score": 650,
  "consumer_statement": true
}
```

**Collection Letter:**
```json
{
  "collector": "ABC Collections LLC",
  "debt_amount": 1250.50,
  "debt_date": "2023-01-15",
  "violations_detected": ["mini_miranda", "validation_rights"],
  "ai_summary": "Letter fails to provide debt validation notice..."
}
```

**Recording:**
```json
{
  "duration_seconds": 180,
  "caller_id": "+1-555-123-4567",
  "transcription": "Hello, this is ABC Collections...",
  "violations_detected": ["tcpa_consent", "time_of_call"]
}
```

#### Chain of Custody

- **chain_of_custody** (JSONB array)
  - Full chain of custody for this evidence
  - See CHAIN_OF_CUSTODY.md for structure
  - Example:
```json
[
  {
    "timestamp": "2024-06-14T10:00:00Z",
    "actor": "client-uuid",
    "action": "upload",
    "details": {...},
    "prev_hash": "",
    "entry_hash": "a1b2c3..."
  }
]
```

#### Audit Trail

- **created_at** (timestamp with timezone, default NOW())
  - When evidence record created
  - Immutable

- **created_by** (UUID, required)
  - Who created the record

- **updated_at** (timestamp with timezone, default NOW())
  - Last metadata update (not file content)
  - Auto-updated on any change

- **updated_by** (UUID, optional)
  - Who last updated metadata

- **deleted_at** (timestamp, optional)
  - Soft delete timestamp
  - Evidence never truly deleted (compliance requirement)

- **deleted_by** (UUID, optional)
  - Who soft-deleted the evidence

#### Legal Hold

- **legal_hold** (boolean, default false)
  - Is evidence under legal hold? (cannot be deleted/modified)

- **legal_hold_reason** (text, optional)
  - Why evidence is on hold
  - Example: "Pending litigation in Case #2024-CV-1234"

- **legal_hold_expires_at** (timestamp, optional)
  - When hold can be released (if known)

#### Retention Policy

- **retention_expires_at** (timestamp, optional)
  - When evidence can be purged
  - Typically 7 years for legal documents
  - Null = retain indefinitely

---

## Relationships

### Evidence → Cases (Many-to-Many)

One evidence item can support multiple cases.

**Junction Table:** `evidence_case_links`
```
evidence_id (UUID)
case_id (UUID)
linkage_date (timestamp)
linkage_reason (text)
```

**Example:** Credit report shows violations across 3 separate collection accounts → used in 3 different cases.

---

### Evidence → Violations (Many-to-Many)

One evidence item can support multiple violations.

**Stored in:** `linked_violations` array field + violation_registry references

**Example:** Single collection letter violates:
- FDCPA § 1692g (validation notice)
- FDCPA § 1692e (false representation)
- State consumer protection act

---

### Evidence → Exhibits (One-to-Many)

One evidence item can become multiple exhibits (e.g., in different cases).

**Stored in:** `exhibit_registry` references evidence_id

**Example:** 
- Evidence: `credit_report_experian.pdf`
- Becomes:
  - Exhibit A in Case #1
  - Exhibit C in Case #2

---

### Evidence → Packets (Many-to-Many)

One evidence item can appear in multiple packets.

**Junction Table:** `packet_evidence_links`

**Example:** Same credit report included in:
- Dispute packet (to credit bureau)
- Affidavit packet (for court)
- Settlement packet (to opposing counsel)

---

## Admissibility Requirements

Before evidence is considered **admissible** (status = `approved`), it must meet:

1. **Authentication:** 
   - Source verified (who provided it?)
   - Hash computed and verified
   - Chain of custody initiated

2. **Relevance:**
   - Linked to at least one violation OR
   - Tagged with case-relevant category

3. **Reliability:**
   - File integrity verified (hash matches)
   - Not rejected by reviewing attorney
   - Chain of custody unbroken (verified)

4. **Compliance:**
   - Not under legal hold (unless hold permits use)
   - Retention policy allows access

**Readiness Check Function:**
```python
def is_admissible(evidence: Evidence) -> (bool, List[str]):
    """
    Check if evidence meets admissibility requirements.
    
    Returns:
        (admissible, reasons)
    """
    reasons = []
    
    # Check authentication
    if not evidence.sha256_hash:
        reasons.append("Missing SHA-256 hash")
    if not evidence.source_reference:
        reasons.append("Source not documented")
    if not evidence.chain_of_custody:
        reasons.append("No chain of custody")
    
    # Check relevance
    if not evidence.linked_violations and not evidence.tags:
        reasons.append("Not linked to violations or case")
    
    # Check reliability
    if evidence.status == "rejected":
        reasons.append("Rejected by reviewer")
    chain_valid, _, _ = verify_chain_of_custody(evidence.chain_of_custody)
    if not chain_valid:
        reasons.append("Chain of custody broken")
    
    # Check compliance
    if evidence.legal_hold and not evidence.legal_hold_permits_use:
        reasons.append("Under legal hold")
    
    return (len(reasons) == 0, reasons)
```

---

## Search & Discovery

### Full-Text Search

Evidence must be searchable by:
- File name
- Category/subcategory
- Tags
- Metadata fields (AI summary, transcription, etc.)
- Date ranges (acquisition date, report date, etc.)

**Search Vector:** Composite of:
- file_name (weight A - highest)
- category (weight B)
- subcategory (weight B)
- tags (weight C)
- metadata.ai_summary (weight D - lowest)

### Advanced Queries

**Find all credit reports for a client:**
```
category = "credit_report"
AND client_id = "client-uuid"
AND status != "rejected"
ORDER BY date_acquired DESC
```

**Find evidence supporting specific violation:**
```
"violation-uuid" = ANY(linked_violations)
AND status = "approved"
```

**Find duplicate uploads:**
```
SELECT sha256_hash, COUNT(*)
FROM evidence_registry
GROUP BY sha256_hash
HAVING COUNT(*) > 1
```

**Find evidence needing review:**
```
status = "pending_review"
AND date_acquired < NOW() - INTERVAL '7 days'
ORDER BY date_acquired ASC
```

---

## Deduplication Strategy

**Problem:** Client uploads same credit report twice.

**Detection:** Match SHA-256 hash

**Resolution Options:**

1. **Link to Existing:**
   - Don't create new evidence record
   - Add case linkage to existing evidence
   - Append chain of custody entry: "Duplicate upload ignored"

2. **Create Reference:**
   - Create new evidence record with `duplicate_of` field
   - Points to original evidence
   - Maintains separate chain of custody

**Recommended:** Option 1 (link to existing) to avoid storage bloat.

---

## Quality Scoring

Each evidence item receives a **Quality Score** (0-100):

| Factor | Weight | Criteria |
|--------|--------|----------|
| **File Quality** | 30 | Resolution, readability, completeness |
| **Metadata Completeness** | 25 | All required fields populated |
| **Chain of Custody** | 20 | Unbroken, verified |
| **Source Reliability** | 15 | Direct source vs. copy, authentication |
| **Relevance** | 10 | Linked to violations, tagged appropriately |

**Score Bands:**
- 0-39: Poor (may be challenged in court)
- 40-69: Adequate (usable but improvable)
- 70-84: Good (court-ready with minor gaps)
- 85-100: Excellent (litigation-ready)

**Example:**
```json
{
  "quality_score": 78,
  "quality_breakdown": {
    "file_quality": 25,  // out of 30 (good scan, readable)
    "metadata_completeness": 20,  // out of 25 (missing some optional fields)
    "chain_of_custody": 20,  // out of 20 (perfect)
    "source_reliability": 10,  // out of 15 (client upload, not direct from bureau)
    "relevance": 8  // out of 10 (tagged but not yet linked to violations)
  },
  "improvement_suggestions": [
    "Link to specific FCRA violations",
    "Add AI-generated summary to metadata",
    "Obtain direct bureau copy for higher source reliability"
  ]
}
```

---

## Integration Points

### Portal Document Vault
- Evidence uploads flow through secure document vault
- Vault generates SHA-256 hash on upload
- Vault triggers Evidence Registry entry creation
- Vault storage_key links to MinIO object

### Violation Registry
- Evidence links to violations via `linked_violations` array
- Violation Registry queries: "Show all evidence supporting this violation"
- Confidence scoring: AI determines strength of evidence-violation link

### Exhibit Registry
- Exhibit creation pulls from Evidence Registry
- One evidence item → one or more exhibits
- Exhibit tracks: exhibit number, case context, inclusion in packets

### Packet Generator
- Packets assemble evidence based on filters:
  - All evidence for case_id
  - All evidence for specific violation_ids
  - Evidence with quality_score > threshold
- Packet includes chain of custody for each evidence item

### Chain of Custody
- Every action on evidence appends to chain_of_custody array
- Chain verified before including evidence in court packets

---

## API Requirements (Future Implementation)

### Create Evidence
```http
POST /api/evidence
Content-Type: multipart/form-data

{
  "case_id": "case-uuid",
  "client_id": "client-uuid",
  "file": <binary>,
  "source_type": "upload",
  "category": "credit_report",
  "tags": ["fcra", "experian"]
}

Response:
{
  "evidence_id": "EV-2024-00001",
  "sha256_hash": "a1b2c3d4...",
  "storage_key": "evidence/case-uuid/EV-2024-00001/credit_report.pdf",
  "chain_of_custody": [...]
}
```

### Get Evidence
```http
GET /api/evidence/{evidence_id}

Response:
{
  "evidence_id": "EV-2024-00001",
  "case_id": "case-uuid",
  "file_name": "credit_report_experian.pdf",
  "status": "approved",
  "quality_score": 78,
  "linked_violations": ["VIO-001", "VIO-002"],
  "chain_of_custody": [...],
  "is_admissible": true
}
```

### Search Evidence
```http
GET /api/evidence/search?q=credit report&case_id=case-uuid&status=approved

Response:
{
  "total": 15,
  "results": [
    {
      "evidence_id": "EV-2024-00001",
      "file_name": "credit_report_experian.pdf",
      "category": "credit_report",
      "date_acquired": "2024-06-14T10:00:00Z",
      "quality_score": 78
    }
  ]
}
```

### Update Evidence Metadata
```http
PATCH /api/evidence/{evidence_id}
Content-Type: application/json

{
  "tags": ["fcra", "experian", "disputed"],
  "linked_violations": ["VIO-001", "VIO-002", "VIO-003"]
}

Response:
{
  "updated": true,
  "chain_of_custody_updated": true
}
```

---

## Compliance & Legal Considerations

### Retention Policies

**Consumer Law Cases:** 7 years minimum (statute of limitations)  
**Trust Administration:** Permanent (trustee liability)  
**Criminal Defense:** Permanent (potential appeals)

**Implementation:**
- Set `retention_expires_at` on creation based on case type
- Automated purge job checks `retention_expires_at` + `legal_hold = false`
- Soft delete only (move to archive storage, don't destroy)

### Privacy (GDPR, CCPA)

**Client Data Requests:**
- "Show all evidence for my case" → Query `client_id`
- "Delete my data" → Soft delete + anonymize metadata (keep hash chain for integrity)

**Redaction:**
- Store redacted version separately (new evidence record)
- Link: `redacted_version_of` field
- Original retained under legal hold

### Discovery Obligations

**Litigation Hold:**
- Set `legal_hold = true` on all evidence for case
- Prevents deletion, requires preservation
- Audit trail tracks hold placement and release

---

**END EVIDENCE REGISTRY SPECIFICATION**
