# Exhibit Registry

**Status:** DESIGN SPECIFICATION  
**Created:** 2026-06-14  
**Purpose:** Transform raw evidence into courtroom-ready exhibits with numbering, indexing, and manifest generation

---

## What is an Exhibit?

An **exhibit** is a formally designated piece of evidence prepared for presentation in legal proceedings, settlement negotiations, or administrative filings. It differs from raw evidence in that it:

1. **Has a formal designation** (Exhibit A, Exhibit 1, Ex-001, etc.)
2. **Is contextualized** (described with purpose and relevance)
3. **Is court-ready** (properly formatted, Bates-numbered if needed)
4. **Is indexed** (appears in table of exhibits)
5. **Is traceable** (links back to original evidence with chain of custody)

**Raw Evidence vs. Exhibit:**
```
Evidence: credit_report_experian_2024_06_14.pdf
          ↓
Exhibit A: Experian Credit Report dated June 14, 2024
          (Bates stamped PLAINTIFF-001 through PLAINTIFF-015)
          Showing disputed tradeline for ABC Collections
```

---

## Core Design Principles

1. **Evidence-Based:** Every exhibit traces to evidence in Evidence Registry
2. **Context-Aware:** Exhibits include description of relevance and purpose
3. **Auto-Numbered:** System assigns exhibit numbers (manual override available)
4. **Manifest-Ready:** All exhibits auto-populate exhibit manifests/indexes
5. **Multi-Use:** Same evidence can become different exhibits in different contexts
6. **Bates-Ready:** Support for Bates numbering when required
7. **Packet-Linked:** Exhibits are grouped into packets for filing

---

## Exhibit Lifecycle

```
┌─────────────┐
│  CREATED    │  Evidence selected and designated as exhibit
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  NUMBERED   │  Exhibit number/label assigned
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  DESCRIBED  │  Context and relevance documented
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  FORMATTED  │  Bates numbering, page breaks, headers applied
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ INCLUDED    │  Added to packet (dispute, affidavit, court filing)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  FILED      │  Submitted to court, bureau, or agency
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  ARCHIVED   │  Retained per retention policy
└─────────────┘
```

---

## Data Model

### Core Fields

#### Identity
- **exhibit_id** (UUID, primary key)
  - Globally unique identifier
  - Format: `EX-{case}-{year}-{sequence}` (e.g., `EX-C001-2024-00001`)

- **case_id** (UUID, required)
  - Links exhibit to legal case
  - One exhibit belongs to one case (but can be in multiple packets)

- **evidence_id** (UUID, required)
  - Links to original evidence in Evidence Registry
  - One evidence item can generate multiple exhibits

#### Exhibit Designation

- **exhibit_number** (text, required)
  - Human-readable exhibit label
  - Formats:
    - **Letter-based:** "A", "B", "C", ... "Z", "AA", "AB", etc.
    - **Number-based:** "1", "2", "3", ... "99", "100", etc.
    - **Prefix-based:** "Plaintiff-A", "Defendant-1", "Ex-001"
  - Example: "Exhibit A"

- **exhibit_label_format** (enum, required)
  - Numbering scheme to use
  - Values: `LETTER`, `NUMBER`, `PREFIX_LETTER`, `PREFIX_NUMBER`, `CUSTOM`
  - Set at case or packet level, then auto-applied

- **sequence_number** (integer, required)
  - Internal sequence for ordering (1, 2, 3...)
  - Used to auto-generate exhibit_number
  - Example: sequence_number=1 → Exhibit A (if LETTER format)

- **exhibit_prefix** (text, optional)
  - Prefix for exhibit number
  - Examples: "Plaintiff", "Def", "Ex", "Attachment"
  - Full label: `{prefix}-{number}` → "Plaintiff-A"

#### Description & Context

- **exhibit_title** (text, required)
  - Short title of exhibit
  - Examples:
    - "Experian Credit Report"
    - "Collection Letter dated January 15, 2023"
    - "Affidavit of John Doe"
    - "Audio Recording of Collection Call"

- **exhibit_description** (text, required)
  - Detailed description of exhibit and relevance
  - Example:
    ```
    Experian credit report dated June 14, 2024, showing disputed 
    tradeline for ABC Collections account #123456. Demonstrates 
    creditor's failure to investigate dispute within 30 days as 
    required by FCRA § 1681s-2(b).
    ```

- **purpose** (text, optional)
  - Why this exhibit is being presented
  - Example: "Proves failure to investigate consumer dispute"

- **relevance_to_violation** (UUID, optional)
  - Links exhibit to specific violation
  - Multiple exhibits can support one violation

#### File & Format Information

- **page_count** (integer, required)
  - Number of pages in exhibit
  - For multi-page documents only

- **page_range** (text, optional)
  - Which pages from original evidence
  - Example: "Pages 1-5, 12-15" (if extracting subset)

- **file_format** (text, required)
  - Format of exhibit file
  - Values: `PDF`, `IMAGE`, `AUDIO`, `VIDEO`, `TEXT`
  - Most exhibits are PDF for court submission

- **storage_key** (text, required)
  - MinIO/S3 key for formatted exhibit file
  - Format: `exhibits/{case_id}/{exhibit_id}/{exhibit_number}.pdf`

- **original_storage_key** (text, required)
  - Links to original evidence file (from Evidence Registry)

#### Bates Numbering

- **bates_numbering** (boolean, default false)
  - Is Bates numbering applied?

- **bates_prefix** (text, optional)
  - Prefix for Bates stamps
  - Examples: "PLAINTIFF", "DEF", "SMITH"

- **bates_start** (integer, optional)
  - Starting Bates number
  - Example: 1 → PLAINTIFF-0001

- **bates_end** (integer, optional)
  - Ending Bates number
  - Example: 15 → PLAINTIFF-0015

- **bates_format** (text, optional)
  - Format string for Bates stamps
  - Example: "{prefix}-{number:06d}" → PLAINTIFF-000001

**Bates Example:**
```json
{
  "exhibit_number": "A",
  "bates_numbering": true,
  "bates_prefix": "PLAINTIFF",
  "bates_start": 1,
  "bates_end": 15,
  "bates_format": "{prefix}-{number:04d}",
  "result": "Pages stamped PLAINTIFF-0001 through PLAINTIFF-0015"
}
```

#### Packet Association

- **packet_ids** (array of UUIDs)
  - Which packets include this exhibit
  - One exhibit can appear in multiple packets
  - Examples:
    - Dispute packet to credit bureau
    - Affidavit packet for court
    - Settlement packet to opposing counsel

- **primary_packet_id** (UUID, optional)
  - Primary packet this exhibit was created for

#### Metadata

- **tags** (array of text)
  - Flexible tagging
  - Examples: `["credit_report", "fcra", "dispute"]`

- **metadata** (JSONB, optional)
  - Type-specific data
  ```json
  {
    "court": "U.S. District Court, Northern District of California",
    "filing_type": "Motion to Compel",
    "exhibit_type": "supporting_document",
    "redacted": false,
    "certified": true,
    "notarized": false
  }
  ```

#### Status & Workflow

- **status** (enum, required, default `CREATED`)
  - Values: `CREATED`, `NUMBERED`, `DESCRIBED`, `FORMATTED`, `INCLUDED`, `FILED`, `ARCHIVED`

- **filed_date** (date, optional)
  - When exhibit was filed with court/agency

- **filed_with** (text, optional)
  - Where exhibit was filed
  - Examples: "U.S. District Court", "FTC", "CFPB", "Experian"

#### Audit Trail

- **created_at** (timestamp, required)
- **created_by** (UUID, required)
- **updated_at** (timestamp, required)
- **updated_by** (UUID, optional)
- **deleted_at** (timestamp, optional)  // Soft delete
- **deleted_by** (UUID, optional)

---

## Exhibit Numbering Schemes

### 1. Letter-Based (Most Common)

**Format:** A, B, C, ..., Z, AA, AB, AC, ...

**Use Case:** Court filings, affidavits, most legal documents

**Example:**
```
Exhibit A: Credit Report
Exhibit B: Dispute Letter
Exhibit C: Bureau Response
```

**Auto-generation:**
```python
def generate_letter_label(sequence: int) -> str:
    """Generate letter-based exhibit label (A, B, ..., Z, AA, AB, ...)"""
    result = ""
    while sequence > 0:
        sequence -= 1
        result = chr(65 + (sequence % 26)) + result
        sequence //= 26
    return result

# Examples:
# generate_letter_label(1) → "A"
# generate_letter_label(26) → "Z"
# generate_letter_label(27) → "AA"
```

---

### 2. Number-Based

**Format:** 1, 2, 3, ..., 99, 100, ...

**Use Case:** Administrative filings, settlements, large exhibit sets

**Example:**
```
Exhibit 1: Collection Letter
Exhibit 2: Payment History
Exhibit 3: Bank Statement
```

**Auto-generation:**
```python
def generate_number_label(sequence: int) -> str:
    """Generate number-based exhibit label."""
    return str(sequence)
```

---

### 3. Prefix-Based

**Format:** {Prefix}-{Letter/Number}

**Use Cases:**
- **Plaintiff-A, Defendant-A:** When both parties submit exhibits
- **Ex-001, Ex-002:** Formal government/corporate style
- **Attachment-1:** For email attachments or supporting docs

**Example:**
```
Plaintiff-A: Credit Report
Plaintiff-B: Dispute Letter
Defendant-1: Account Statement
Defendant-2: Payment Records
```

**Auto-generation:**
```python
def generate_prefix_label(prefix: str, sequence: int, format_type: str) -> str:
    """Generate prefixed exhibit label."""
    if format_type == "LETTER":
        label = generate_letter_label(sequence)
    else:  # NUMBER
        label = f"{sequence:03d}"  # Zero-padded to 3 digits
    return f"{prefix}-{label}"

# Examples:
# generate_prefix_label("Plaintiff", 1, "LETTER") → "Plaintiff-A"
# generate_prefix_label("Ex", 1, "NUMBER") → "Ex-001"
```

---

### 4. Custom

**Format:** User-defined

**Use Case:** Special circumstances, specific court rules

**Example:**
```
Schedule A: Real Property
Schedule B: Personal Property
Attachment 1-A: Supporting Document
```

---

## Exhibit Manifest Generation

### Table of Exhibits

Every packet includes a **Table of Exhibits** listing all included exhibits.

**Format:**

```
TABLE OF EXHIBITS

Exhibit | Description                                    | Pages
--------|------------------------------------------------|--------
A       | Experian Credit Report dated June 14, 2024     | 1-15
B       | Dispute Letter to Experian dated May 1, 2024   | 16-17
C       | Experian Response dated May 15, 2024           | 18-19
D       | Collection Letter from ABC Collections         | 20-21
E       | Affidavit of John Doe                          | 22-24
```

**Auto-generation:**
```python
def generate_exhibit_manifest(exhibits: List[Exhibit]) -> str:
    """Generate table of exhibits for packet."""
    lines = ["TABLE OF EXHIBITS\n"]
    lines.append(f"{'Exhibit':<10} | {'Description':<50} | {'Pages':<10}")
    lines.append("-" * 75)
    
    page_offset = 1  # Starting page number
    
    for exhibit in sorted(exhibits, key=lambda e: e.sequence_number):
        page_end = page_offset + exhibit.page_count - 1
        lines.append(
            f"{exhibit.exhibit_number:<10} | "
            f"{exhibit.exhibit_title:<50} | "
            f"{page_offset}-{page_end}"
        )
        page_offset = page_end + 1
    
    return "\n".join(lines)
```

---

### Certificate of Service

When exhibits are filed, include certificate of service:

```
CERTIFICATE OF SERVICE

I hereby certify that on June 14, 2024, I caused to be served a true 
and correct copy of the foregoing Motion to Compel Discovery, including 
Exhibits A through E, upon the following parties by [method of service]:

[Recipient Name]
[Recipient Address]

[Attorney Signature]
[Attorney Name]
[Bar Number]
```

---

## Exhibit Formatting

### PDF Generation

**Requirements for Court-Ready Exhibits:**

1. **Header/Footer:**
   - Exhibit number on every page
   - Case name and number
   - Page numbers (Page X of Y)

2. **Bates Numbering:**
   - Stamped on bottom right corner
   - Format: PLAINTIFF-0001
   - Sequential across all exhibits

3. **Bookmarks:**
   - PDF bookmarks for each exhibit
   - Easy navigation in large packets

4. **Page Breaks:**
   - Each exhibit starts on new page
   - No mid-page exhibit transitions

**Example PDF Structure:**
```
[Cover Page]
  Motion to Compel Discovery
  
[Table of Contents]
  
[Table of Exhibits]
  
[Exhibit A - Page 1]
  Header: Exhibit A - Experian Credit Report
  Footer: Page 1 of 15 | PLAINTIFF-0001
  
[Exhibit A - Page 2]
  Header: Exhibit A - Experian Credit Report
  Footer: Page 2 of 15 | PLAINTIFF-0002
  
...

[Exhibit B - Page 1]
  Header: Exhibit B - Dispute Letter
  Footer: Page 16 of 17 | PLAINTIFF-0016
```

---

### Redaction

**Redact Sensitive Information:**

- Social Security Numbers
- Account numbers (last 4 digits only)
- Dates of birth (year only)
- Personal contact information

**Redaction Process:**
1. Create redacted copy of evidence file
2. Create exhibit from redacted copy (new evidence record)
3. Link: `redacted_version_of` field points to original
4. Mark: `metadata.redacted = true`

**Example:**
```json
{
  "exhibit_id": "EX-C001-2024-00001",
  "exhibit_number": "A",
  "evidence_id": "EV-2024-00002",  // Redacted version
  "original_evidence_id": "EV-2024-00001",  // Original unredacted
  "metadata": {
    "redacted": true,
    "redaction_reason": "Privacy protection per Fed. R. Civ. P. 5.2",
    "redacted_fields": ["ssn", "account_number", "dob"]
  }
}
```

---

## Exhibit Types by Use Case

### 1. Credit Dispute Packet

**Target:** Credit bureaus (Experian, Equifax, TransUnion)

**Exhibits:**
- **Exhibit A:** Credit report showing disputed items
- **Exhibit B:** Dispute letter (consumer to bureau)
- **Exhibit C:** Previous dispute correspondence
- **Exhibit D:** Supporting documentation (receipts, proof of payment, etc.)

**Numbering:** Letter-based (A, B, C, D)

---

### 2. FDCPA Complaint

**Target:** U.S. District Court

**Exhibits:**
- **Plaintiff-A:** Collection letter violating FDCPA
- **Plaintiff-B:** Consumer's cease communication letter
- **Plaintiff-C:** Subsequent collection calls (call log)
- **Plaintiff-D:** Audio recording of harassing call

**Numbering:** Prefix-based (Plaintiff-A, Plaintiff-B, etc.)

---

### 3. Affidavit of Facts

**Target:** Court or regulatory agency

**Exhibits:**
- **Exhibit 1:** Credit report
- **Exhibit 2:** Collection letter
- **Exhibit 3:** Bank statement showing incorrect charge
- **Exhibit 4:** Email correspondence

**Numbering:** Number-based (1, 2, 3, 4)

---

### 4. Settlement Package

**Target:** Opposing counsel

**Exhibits:**
- **Attachment A:** Demand letter
- **Attachment B:** Supporting evidence summary
- **Attachment C:** Damages calculation worksheet
- **Attachment D:** Settlement authorization

**Numbering:** Prefix-based (Attachment-A, Attachment-B, etc.)

---

### 5. Trust Administration Evidence Binder

**Target:** Trustee, beneficiaries, court

**Exhibits:**
- **Schedule A:** Real property inventory
- **Schedule B:** Personal property inventory
- **Exhibit 1:** Trust agreement
- **Exhibit 2:** Death certificate
- **Exhibit 3:** Probate court order
- **Exhibit 4:** Banking binder

**Numbering:** Mixed (Schedules + Exhibits)

---

## Relationships

### Exhibit → Evidence (Many-to-One)

Multiple exhibits can reference the same evidence.

**Example:**
- Evidence: `credit_report_experian.pdf`
- Becomes:
  - Exhibit A in Dispute Packet #1
  - Plaintiff-A in Court Filing #2
  - Attachment 1 in Settlement Package #3

---

### Exhibit → Violation (Many-to-Many)

One exhibit can support multiple violations.
One violation can be supported by multiple exhibits.

**Example:**
- Exhibit A: Collection letter
- Supports:
  - Violation 1: Missing validation notice (FDCPA § 1692g)
  - Violation 2: False representation (FDCPA § 1692e)

---

### Exhibit → Packet (Many-to-Many)

One exhibit can appear in multiple packets.

**Junction Table:** `packet_exhibit_links`
```
packet_id (UUID)
exhibit_id (UUID)
sequence_in_packet (integer)  // Order within this packet
```

**Example:**
- Exhibit A appears in:
  - Dispute Packet (sequence 1)
  - Affidavit Packet (sequence 3)
  - Court Filing Packet (sequence 2)

---

## Quality Checks

### Exhibit Readiness Checklist

Before marking exhibit as `FORMATTED`:

- [ ] Evidence file exists and is accessible
- [ ] Exhibit number assigned (no duplicates in case)
- [ ] Title and description populated
- [ ] Page count accurate
- [ ] Redactions applied (if required)
- [ ] Bates numbering applied (if required)
- [ ] PDF generated and stored
- [ ] Chain of custody verified (evidence → exhibit)

### Validation Rules

```python
def validate_exhibit(exhibit: Exhibit) -> (bool, List[str]):
    """Validate exhibit is ready for inclusion in packet."""
    errors = []
    
    # Check required fields
    if not exhibit.exhibit_number:
        errors.append("Exhibit number missing")
    
    if not exhibit.exhibit_title:
        errors.append("Exhibit title missing")
    
    if not exhibit.exhibit_description:
        errors.append("Exhibit description missing")
    
    # Check evidence exists
    evidence = get_evidence(exhibit.evidence_id)
    if not evidence:
        errors.append("Linked evidence not found")
    
    # Check for duplicates in case
    duplicates = get_exhibits_by_number(exhibit.case_id, exhibit.exhibit_number)
    if len(duplicates) > 1:
        errors.append(f"Duplicate exhibit number {exhibit.exhibit_number} in case")
    
    # Check file exists
    if not file_exists(exhibit.storage_key):
        errors.append("Exhibit file not found in storage")
    
    # Check Bates numbering consistency
    if exhibit.bates_numbering:
        if not exhibit.bates_start or not exhibit.bates_end:
            errors.append("Bates numbering enabled but start/end not set")
        if exhibit.bates_end - exhibit.bates_start + 1 != exhibit.page_count:
            errors.append("Bates range doesn't match page count")
    
    return (len(errors) == 0, errors)
```

---

## Integration Points

### Evidence Registry
- Exhibits pull files from Evidence Registry
- Chain of custody flows from evidence to exhibit
- Quality score of evidence affects exhibit usability

### Violation Registry
- Exhibits link to violations they support
- Violation strength score considers exhibit quality

### Packet Generator
- Packets assemble exhibits in order
- Auto-generate table of exhibits
- Apply Bates numbering across all exhibits in packet

### Case Readiness Scoring
- Number of exhibits affects readiness score
- Exhibit quality (description completeness, formatting) factored in

---

## API Requirements (Future Implementation)

### Create Exhibit
```http
POST /api/exhibits
Content-Type: application/json

{
  "case_id": "case-uuid",
  "evidence_id": "EV-2024-00001",
  "exhibit_title": "Experian Credit Report",
  "exhibit_description": "Credit report showing disputed tradeline...",
  "exhibit_label_format": "LETTER",
  "bates_numbering": true,
  "bates_prefix": "PLAINTIFF"
}

Response:
{
  "exhibit_id": "EX-C001-2024-00001",
  "exhibit_number": "A",
  "bates_start": 1,
  "bates_end": 15,
  "storage_key": "exhibits/case-uuid/EX-C001-2024-00001/Exhibit_A.pdf"
}
```

### Get Exhibits for Case
```http
GET /api/cases/{case_id}/exhibits?status=FORMATTED

Response:
{
  "total": 5,
  "exhibits": [
    {
      "exhibit_id": "EX-C001-2024-00001",
      "exhibit_number": "A",
      "exhibit_title": "Experian Credit Report",
      "page_count": 15,
      "bates_range": "PLAINTIFF-0001 to PLAINTIFF-0015"
    }
  ]
}
```

### Generate Exhibit Manifest
```http
GET /api/cases/{case_id}/exhibits/manifest

Response:
{
  "manifest_text": "TABLE OF EXHIBITS\n\nExhibit | Description | Pages\n...",
  "total_exhibits": 5,
  "total_pages": 42
}
```

### Batch Create Exhibits
```http
POST /api/exhibits/batch
Content-Type: application/json

{
  "case_id": "case-uuid",
  "evidence_ids": ["EV-001", "EV-002", "EV-003"],
  "label_format": "LETTER",
  "bates_numbering": true,
  "bates_prefix": "PLAINTIFF"
}

Response:
{
  "created": 3,
  "exhibits": [
    {"exhibit_number": "A", "bates_range": "PLAINTIFF-0001 to PLAINTIFF-0015"},
    {"exhibit_number": "B", "bates_range": "PLAINTIFF-0016 to PLAINTIFF-0017"},
    {"exhibit_number": "C", "bates_range": "PLAINTIFF-0018 to PLAINTIFF-0025"}
  ]
}
```

---

## Compliance & Legal Considerations

### Federal Rules of Civil Procedure

**Rule 5.2:** Privacy protection for filings made with the court

**Redaction Requirements:**
- Social Security Numbers: Use last 4 digits only
- Taxpayer ID: Use last 4 digits only
- Birth dates: Use year only
- Financial account numbers: Use last 4 digits only
- Names of minor children: Use initials only

**Implementation:**
```python
AUTO_REDACT_PATTERNS = {
    "ssn": r"\b\d{3}-\d{2}-(\d{4})\b",  # Keep last 4
    "account": r"\b\d{4,16}\b",  # Replace all but last 4
    "dob": r"\b\d{1,2}/\d{1,2}/(\d{4})\b",  # Keep year only
}

def auto_redact(text: str) -> str:
    """Apply automatic redactions per Rule 5.2."""
    for field, pattern in AUTO_REDACT_PATTERNS.items():
        text = re.sub(pattern, "[REDACTED]", text)
    return text
```

---

### Authentication (Fed. R. Evid. 901)

Every exhibit must be authenticated:

**Methods:**
1. **Testimony:** Witness testifies this is what it purports to be
2. **Self-Authenticating:** Public records, certified copies
3. **Chain of Custody:** Documented handling from acquisition to filing

**Implementation:**
- Exhibit links to evidence with chain of custody
- Exhibit description includes authentication basis
- Certificate of authenticity can be generated

---

**END EXHIBIT REGISTRY SPECIFICATION**
