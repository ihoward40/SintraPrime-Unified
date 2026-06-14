# Violation Registry

**Status:** DESIGN SPECIFICATION  
**Created:** 2026-06-14  
**Purpose:** Structured violation tracking with statute references, evidence linkage, and remedies

---

## What is a Violation?

A **violation** is a specific, legally actionable breach of a statute, regulation, or contract term that:
1. Is supported by documented evidence
2. References a specific legal provision (statute, section, subsection)
3. Has defined remedies (statutory damages, actual damages, injunctive relief)
4. Can be articulated in legal filings (complaints, disputes, affidavits)

**Examples:**
- **FCRA § 1681s-2(b):** Failure to investigate dispute within 30 days
- **FDCPA § 1692g:** Failure to provide debt validation notice
- **TCPA § 227(b)(1)(A)(iii):** Unsolicited call to cell phone without prior consent
- **RESPA § 2605(e):** Failure to respond to qualified written request within 30 days

---

## Core Design Principles

1. **Statute-First:** Every violation maps to specific legal authority
2. **Evidence-Backed:** Violations must link to supporting evidence
3. **Remedy-Aware:** Each violation type has defined remedies
4. **Confidence-Scored:** AI and human review produce confidence scores
5. **Composable:** Multiple violations can combine into comprehensive cases
6. **Extensible:** New statutes and violation types can be added without schema changes

---

## Violation Lifecycle

```
┌──────────────┐
│  DETECTED    │  AI or human identifies potential violation
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  ANALYZED    │  Evidence reviewed, statute matched
└──────┬───────┘
       │
       ├─────────────┐
       ▼             ▼
┌──────────┐   ┌──────────┐
│CONFIRMED │   │ REJECTED │  Insufficient evidence or not actionable
└────┬─────┘   └──────────┘
     │
     ▼
┌──────────┐
│  LINKED  │  Linked to evidence and exhibits
└────┬─────┘
     │
     ▼
┌──────────┐
│ APPROVED │  Attorney approves for inclusion in case
└────┬─────┘
     │
     ▼
┌──────────┐
│  FILED   │  Included in legal filing (complaint, dispute, etc.)
└────┬─────┘
     │
     ▼
┌──────────┐
│ RESOLVED │  Settlement, judgment, or dismissal
└──────────┘
```

---

## Data Model

### Core Fields

#### Identity
- **violation_id** (UUID, primary key)
  - Globally unique identifier
  - Format: `VIO-{statute}-{year}-{sequence}` (e.g., `VIO-FCRA-2024-00001`)

- **case_id** (UUID, required)
  - Links violation to legal case
  - One violation belongs to one case (but can support multiple filings)

- **client_id** (UUID, required)
  - Client who suffered the violation

#### Statute & Legal Basis

- **statute** (enum, required)
  - Primary statute violated
  - Values: `FCRA`, `FDCPA`, `TCPA`, `RESPA`, `TILA`, `ECOA`, `UCC`, `STATE_CONSUMER`, `CONTRACT`, `OTHER`

- **statute_full_name** (text, required)
  - Full name of statute
  - Examples:
    - "Fair Credit Reporting Act (FCRA)"
    - "Fair Debt Collection Practices Act (FDCPA)"
    - "Telephone Consumer Protection Act (TCPA)"

- **statute_citation** (text, required)
  - Precise legal citation
  - Examples:
    - "15 U.S.C. § 1681s-2(b)"
    - "15 U.S.C. § 1692g(a)"
    - "47 U.S.C. § 227(b)(1)(A)(iii)"

- **subsection** (text, optional)
  - Specific subsection or clause
  - Example: "(a)(1)(A)" for detailed citations

- **state_statute** (text, optional)
  - State-specific statute if applicable
  - Example: "California Consumer Privacy Act § 1798.150"

#### Violation Details

- **violation_type** (text, required)
  - Short name/category
  - Examples:
    - "failure_to_investigate"
    - "missing_validation_notice"
    - "unauthorized_call"
    - "failure_to_respond_qwr"

- **violation_description** (text, required)
  - Human-readable description
  - Example: "Creditor failed to investigate consumer dispute within 30 days as required by FCRA § 1681s-2(b)"

- **violation_date** (date, optional)
  - When violation occurred (if single event)
  - Example: Date collection letter was sent without validation notice

- **violation_date_range** (date range, optional)
  - For ongoing violations
  - Example: Repeated unauthorized calls from 2023-01-15 to 2024-03-20

- **severity** (enum, required)
  - Violation severity
  - Values: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`
  - Determines prioritization and settlement strategy

#### Evidence Linkage

- **linked_evidence** (array of UUIDs, required)
  - Evidence items supporting this violation
  - Minimum 1 evidence item required for `CONFIRMED` status
  - Example: `["EV-2024-00001", "EV-2024-00023"]`

- **primary_evidence_id** (UUID, optional)
  - Most critical piece of evidence for this violation
  - Used for exhibit selection

- **evidence_strength** (enum, required)
  - How well does evidence support violation?
  - Values: `STRONG`, `MODERATE`, `WEAK`, `CIRCUMSTANTIAL`

#### AI Analysis

- **ai_detected** (boolean, default false)
  - Was violation detected by AI?

- **ai_confidence** (float, 0.0-1.0, optional)
  - AI confidence score
  - Example: 0.89 = 89% confident this is a violation

- **ai_analysis** (JSONB, optional)
  - AI-generated analysis
  ```json
  {
    "model": "gpt-4",
    "timestamp": "2024-06-14T10:00:00Z",
    "reasoning": "Letter dated 2023-01-15 does not contain required validation notice per FDCPA § 1692g(a)(3)...",
    "supporting_quotes": ["This is an attempt to collect a debt..."],
    "confidence_breakdown": {
      "statute_match": 0.95,
      "evidence_quality": 0.85,
      "precedent_alignment": 0.87
    }
  }
  ```

#### Human Review

- **human_reviewed** (boolean, default false)
  - Has attorney reviewed this violation?

- **reviewed_by** (UUID, optional)
  - Attorney who reviewed

- **reviewed_at** (timestamp, optional)
  - When review occurred

- **attorney_confidence** (enum, optional)
  - Attorney's assessment
  - Values: `CERTAIN`, `LIKELY`, `POSSIBLE`, `UNLIKELY`

- **review_notes** (text, optional)
  - Attorney notes on violation strength, strategy, etc.

#### Status & Workflow

- **status** (enum, required, default `DETECTED`)
  - Current violation status
  - Values: `DETECTED`, `ANALYZED`, `CONFIRMED`, `REJECTED`, `LINKED`, `APPROVED`, `FILED`, `RESOLVED`

- **rejection_reason** (text, optional)
  - Why violation was rejected (if status = `REJECTED`)
  - Examples:
    - "Evidence insufficient"
    - "Statute of limitations expired"
    - "Not actually a violation upon closer review"

#### Remedies & Damages

- **statutory_damages_min** (decimal, optional)
  - Minimum statutory damages (if applicable)
  - Example: $100 for FCRA willful violation

- **statutory_damages_max** (decimal, optional)
  - Maximum statutory damages (if applicable)
  - Example: $1,000 for FCRA willful violation

- **actual_damages** (decimal, optional)
  - Estimated actual damages
  - Example: $500 for emotional distress, time spent disputing

- **punitive_damages_eligible** (boolean, default false)
  - Is this violation eligible for punitive damages?

- **injunctive_relief** (boolean, default false)
  - Is injunctive relief available?
  - Example: Order to correct credit report

- **attorneys_fees_eligible** (boolean, default false)
  - Can client recover attorney's fees?
  - Most consumer statutes allow this

- **remedy_notes** (text, optional)
  - Notes on available remedies
  - Example: "FCRA § 1681n allows actual damages OR statutory damages of $100-$1000, plus attorney's fees"

#### Precedent & Strategy

- **precedent_cases** (JSONB array, optional)
  - Relevant case law
  ```json
  [
    {
      "case_name": "Smith v. ABC Collections",
      "citation": "123 F.3d 456 (9th Cir. 2020)",
      "holding": "Failure to provide validation notice is per se violation",
      "damages_awarded": 1000.00,
      "relevance": "Similar facts, same circuit"
    }
  ]
  ```

- **settlement_value** (decimal, optional)
  - Estimated settlement value
  - Based on: severity, evidence strength, precedent, attorney fees

- **litigation_strategy** (text, optional)
  - Strategy notes
  - Example: "Lead with this violation in complaint; strong evidence, clear statute"

#### Metadata

- **tags** (array of text)
  - Flexible tagging
  - Examples: `["credit_reporting", "willful", "pattern_of_conduct"]`

- **metadata** (JSONB, optional)
  - Type-specific data
  ```json
  {
    "tradeline": "ABC Collections - $1,250",
    "dispute_method": "online",
    "furnisher": "ABC Collections LLC",
    "credit_bureau": "Experian"
  }
  ```

#### Audit Trail

- **created_at** (timestamp, required)
- **created_by** (UUID, required)
- **updated_at** (timestamp, required)
- **updated_by** (UUID, optional)
- **deleted_at** (timestamp, optional)  // Soft delete
- **deleted_by** (UUID, optional)

---

## Supported Statutes

### Federal Consumer Protection

#### 1. Fair Credit Reporting Act (FCRA)

**Statute:** 15 U.S.C. § 1681 et seq.

**Common Violations:**

| Violation Type | Citation | Statutory Damages | Example |
|----------------|----------|-------------------|---------|
| Failure to investigate dispute | § 1681s-2(b) | $100-$1,000 | Credit bureau doesn't investigate within 30 days |
| Failure to correct inaccurate info | § 1681i(a) | $100-$1,000 | Bureau keeps reporting disputed account |
| Failure to provide notice of rights | § 1681g(c) | $100-$1,000 | No disclosure of dispute rights |
| Willful noncompliance | § 1681n | $100-$1,000 + actual + punitive | Knowing violation |
| Negligent noncompliance | § 1681o | Actual damages only | Careless violation |

**Remedies:**
- Actual damages OR statutory damages ($100-$1,000)
- Punitive damages (for willful violations)
- Attorney's fees and costs
- Injunctive relief (order to correct)

---

#### 2. Fair Debt Collection Practices Act (FDCPA)

**Statute:** 15 U.S.C. § 1692 et seq.

**Common Violations:**

| Violation Type | Citation | Statutory Damages | Example |
|----------------|----------|-------------------|---------|
| Missing validation notice | § 1692g(a) | $1,000 | Letter doesn't include debt validation notice |
| False/misleading representation | § 1692e | $1,000 | Threat of arrest for unpaid debt |
| Unfair practices | § 1692f | $1,000 | Threatening to seize exempt property |
| Harassment | § 1692d | $1,000 | Repeated calls intended to annoy |
| Communication with third parties | § 1692c(b) | $1,000 | Telling employer about debt |
| Time/place restrictions | § 1692c(a)(1) | $1,000 | Calling before 8am or after 9pm |

**Remedies:**
- Statutory damages up to $1,000
- Actual damages
- Attorney's fees and costs

---

#### 3. Telephone Consumer Protection Act (TCPA)

**Statute:** 47 U.S.C. § 227

**Common Violations:**

| Violation Type | Citation | Statutory Damages | Example |
|----------------|----------|-------------------|---------|
| Unauthorized autodialed call | § 227(b)(1)(A)(iii) | $500-$1,500 per call | Robocall without consent |
| Unauthorized prerecorded call | § 227(b)(1)(B) | $500-$1,500 per call | Prerecorded message without consent |
| Do Not Call violation | § 227(c) | $500-$1,500 per call | Call after consumer requested no contact |

**Remedies:**
- Statutory damages: $500 per violation
- Treble damages: $1,500 for willful/knowing violations
- Injunctive relief

---

#### 4. Real Estate Settlement Procedures Act (RESPA)

**Statute:** 12 U.S.C. § 2601 et seq.

**Common Violations:**

| Violation Type | Citation | Statutory Damages | Example |
|----------------|----------|-------------------|---------|
| Failure to respond to QWR | § 2605(e) | $1,000 + actual | Servicer ignores qualified written request |
| Failure to provide escrow statement | § 2605(f) | $1,000 + actual | No annual escrow account statement |

**Remedies:**
- Statutory damages up to $1,000
- Actual damages
- Attorney's fees and costs

---

#### 5. Truth in Lending Act (TILA)

**Statute:** 15 U.S.C. § 1601 et seq.

**Common Violations:**

| Violation Type | Citation | Statutory Damages | Example |
|----------------|----------|-------------------|---------|
| Failure to disclose APR | § 1638(a)(4) | Twice finance charge (min $200, max $2,000) | Credit card doesn't show APR |
| Improper rescission notice | § 1635 | Actual + statutory | No rescission notice for home equity loan |

**Remedies:**
- Statutory damages (varies by violation)
- Actual damages
- Rescission rights (for certain loans)
- Attorney's fees and costs

---

#### 6. Equal Credit Opportunity Act (ECOA)

**Statute:** 15 U.S.C. § 1691 et seq.

**Common Violations:**

| Violation Type | Citation | Statutory Damages | Example |
|----------------|----------|-------------------|---------|
| Discrimination based on protected class | § 1691(a) | $10,000 + actual | Denial based on race, age, marital status |
| Failure to provide adverse action notice | § 1691(d) | Actual damages | No notice of credit denial |

**Remedies:**
- Actual damages
- Punitive damages (up to $10,000 individual, $500,000 class action)
- Attorney's fees and costs

---

### State Consumer Protection

#### California Consumer Privacy Act (CCPA)

**Statute:** Cal. Civ. Code § 1798.100 et seq.

**Common Violations:**
- Failure to disclose data collection
- Failure to honor opt-out requests
- Data breach without proper notification

**Remedies:**
- Statutory damages: $100-$750 per incident
- Actual damages (if higher)
- Injunctive relief

---

### Contract Law

#### Uniform Commercial Code (UCC)

**Statute:** UCC Article 3, 9 (varies by state)

**Common Violations:**
- Defective negotiable instrument
- Improper perfection of security interest
- Failure to provide required notices

**Remedies:**
- Actual damages
- Rescission
- Reformation

---

## Violation Detection Patterns

### AI Detection Rules

**Pattern 1: Missing Validation Notice (FDCPA)**
```python
def detect_missing_validation_notice(evidence: Evidence) -> Optional[Violation]:
    """
    Detect FDCPA § 1692g(a) violation in collection letters.
    """
    if evidence.category != "collection_letter":
        return None
    
    text = evidence.metadata.get("ocr_text", "").lower()
    
    # Required elements of validation notice
    required_elements = [
        "amount of debt",
        "name of creditor",
        "dispute",
        "verification",
        "30 days"
    ]
    
    missing = [elem for elem in required_elements if elem not in text]
    
    if len(missing) > 0:
        return Violation(
            statute="FDCPA",
            statute_citation="15 U.S.C. § 1692g(a)",
            violation_type="missing_validation_notice",
            violation_description=f"Collection letter missing required validation notice elements: {', '.join(missing)}",
            linked_evidence=[evidence.evidence_id],
            ai_detected=True,
            ai_confidence=0.85 if len(missing) >= 3 else 0.65,
            severity="HIGH",
            statutory_damages_max=1000.00,
            attorneys_fees_eligible=True
        )
    
    return None
```

**Pattern 2: Late Investigation (FCRA)**
```python
def detect_late_investigation(dispute_date: date, response_date: date, evidence: Evidence) -> Optional[Violation]:
    """
    Detect FCRA § 1681s-2(b) violation for late dispute investigation.
    """
    days_elapsed = (response_date - dispute_date).days
    
    if days_elapsed > 30:
        return Violation(
            statute="FCRA",
            statute_citation="15 U.S.C. § 1681s-2(b)",
            violation_type="failure_to_investigate",
            violation_description=f"Creditor failed to complete investigation within 30 days (actual: {days_elapsed} days)",
            violation_date=dispute_date,
            linked_evidence=[evidence.evidence_id],
            ai_detected=True,
            ai_confidence=0.95,  # Date math is highly reliable
            severity="HIGH",
            statutory_damages_min=100.00,
            statutory_damages_max=1000.00,
            attorneys_fees_eligible=True
        )
    
    return None
```

**Pattern 3: Unauthorized Call (TCPA)**
```python
def detect_unauthorized_call(call_log: Evidence) -> Optional[Violation]:
    """
    Detect TCPA § 227(b)(1)(A)(iii) violation for unauthorized calls.
    """
    metadata = call_log.metadata
    
    # Check if consent was given
    if not metadata.get("prior_consent", False):
        # Check if cell phone
        if metadata.get("phone_type") == "cell":
            # Check if autodialed or prerecorded
            if metadata.get("autodialed") or metadata.get("prerecorded"):
                return Violation(
                    statute="TCPA",
                    statute_citation="47 U.S.C. § 227(b)(1)(A)(iii)",
                    violation_type="unauthorized_call",
                    violation_description="Autodialed call to cell phone without prior express consent",
                    violation_date=metadata.get("call_date"),
                    linked_evidence=[call_log.evidence_id],
                    ai_detected=True,
                    ai_confidence=0.90,
                    severity="HIGH",
                    statutory_damages_min=500.00,
                    statutory_damages_max=1500.00,  # Treble for willful
                    attorneys_fees_eligible=True
                )
    
    return None
```

---

## Violation Composition & Strategy

### Composing Multiple Violations

**Scenario:** Credit report shows furnisher violations

```python
case_violations = [
    Violation(
        violation_type="failure_to_investigate",
        statute="FCRA",
        statute_citation="15 U.S.C. § 1681s-2(b)",
        severity="HIGH",
        statutory_damages_max=1000.00
    ),
    Violation(
        violation_type="continued_reporting_disputed_info",
        statute="FCRA",
        statute_citation="15 U.S.C. § 1681s-2(b)(1)(D)",
        severity="MEDIUM",
        statutory_damages_max=1000.00
    ),
    Violation(
        violation_type="failure_to_notify_consumer",
        statute="FCRA",
        statute_citation="15 U.S.C. § 1681s-2(b)(1)(E)",
        severity="MEDIUM",
        statutory_damages_max=1000.00
    )
]

# Settlement value estimation
total_statutory_max = sum(v.statutory_damages_max for v in case_violations)
# = $3,000

# Attorney's fees estimate (if litigation required)
estimated_attorney_fees = 5000.00  # Typical for FCRA case

# Total leverage
total_case_value = total_statutory_max + estimated_attorney_fees
# = $8,000

# Settlement strategy: Demand 70% of max value
settlement_demand = total_case_value * 0.70
# = $5,600
```

---

### Strategic Violation Selection

**Priority Matrix:**

| Severity | Evidence Strength | Settlement Value | Litigation Risk | Priority |
|----------|-------------------|------------------|-----------------|----------|
| CRITICAL | STRONG | High | Low | **Lead Claim** |
| HIGH | STRONG | Medium | Low | **Supporting Claim** |
| HIGH | MODERATE | Medium | Medium | **Include if strong case** |
| MEDIUM | WEAK | Low | High | **Omit** |

**Example Case Strategy:**

**Case:** FCRA dispute not investigated

**Violations Detected:**
1. Failure to investigate (CRITICAL, STRONG evidence)
2. Continued reporting (HIGH, STRONG evidence)
3. Missing consumer notice (MEDIUM, MODERATE evidence)
4. Inaccurate information (MEDIUM, WEAK evidence - hard to prove)

**Strategy:**
- **Lead with:** Violation #1 (failure to investigate)
- **Include:** Violations #2 and #3 (strengthen case)
- **Omit:** Violation #4 (weak evidence, not worth litigation risk)

---

## Relationships

### Violation → Evidence (Many-to-Many)

One violation can be supported by multiple evidence items.
One evidence item can support multiple violations.

**Example:**
- Evidence: Collection letter dated 2023-01-15
- Supports:
  - Violation #1: Missing validation notice (FDCPA § 1692g)
  - Violation #2: False representation of amount (FDCPA § 1692e)
  - Violation #3: Unfair practice (FDCPA § 1692f)

---

### Violation → Exhibits (One-to-Many)

Violations generate exhibits for court filings.

**Example:**
- Violation: Failure to investigate dispute
- Exhibits:
  - Exhibit A: Dispute letter to credit bureau
  - Exhibit B: Credit report showing unresolved dispute
  - Exhibit C: Bureau's inadequate response

---

### Violation → Remedies (One-to-Many)

One violation can have multiple remedy options.

**Example:**
- Violation: FCRA § 1681s-2(b)
- Remedies:
  1. Statutory damages: $100-$1,000
  2. Actual damages: $500 (emotional distress, time)
  3. Attorney's fees: $5,000 (estimated)
  4. Injunctive relief: Order to delete tradeline

**Total Potential Recovery:** $6,500

---

## Quality Scoring

### Violation Strength Score (0-100)

| Factor | Weight | Criteria |
|--------|--------|----------|
| **Evidence Quality** | 35 | Strength, quantity, authenticity of supporting evidence |
| **Statute Clarity** | 25 | How clearly statute applies to facts |
| **Precedent Support** | 20 | Relevant case law supports claim |
| **Damages Certainty** | 15 | Can damages be easily calculated? |
| **Defense Weaknesses** | 5 | How easily can defendant dispute? |

**Score Bands:**
- 0-39: Weak (high litigation risk)
- 40-69: Moderate (negotiate settlement)
- 70-84: Strong (high settlement value)
- 85-100: Excellent (likely win at trial)

**Example:**
```json
{
  "violation_strength_score": 82,
  "strength_breakdown": {
    "evidence_quality": 32,  // out of 35 (strong documents, clear dates)
    "statute_clarity": 23,  // out of 25 (FCRA § 1681s-2(b) is very clear)
    "precedent_support": 17,  // out of 20 (several favorable cases)
    "damages_certainty": 12,  // out of 15 (statutory damages well-defined)
    "defense_weaknesses": 3  // out of 5 (defendant has few defenses)
  },
  "litigation_recommendation": "HIGH settlement value; strong case if litigation required"
}
```

---

## Integration Points

### Evidence Registry
- Violations link to evidence via `linked_evidence` array
- Evidence quality affects violation strength score

### Exhibit Registry
- Violations generate exhibits for court filings
- Exhibit A-Z correspond to violations 1-N

### Packet Generator
- Dispute packets include violations + supporting evidence
- Affidavits reference violations with statutory citations
- Complaint drafts organize violations by severity

### Readiness Scoring
- Number of confirmed violations affects case readiness
- Violation strength scores feed into overall case score

---

## API Requirements (Future Implementation)

### Create Violation
```http
POST /api/violations
Content-Type: application/json

{
  "case_id": "case-uuid",
  "statute": "FCRA",
  "statute_citation": "15 U.S.C. § 1681s-2(b)",
  "violation_type": "failure_to_investigate",
  "violation_description": "Creditor failed to investigate within 30 days",
  "linked_evidence": ["EV-2024-00001"],
  "severity": "HIGH"
}

Response:
{
  "violation_id": "VIO-FCRA-2024-00001",
  "status": "DETECTED",
  "statutory_damages_max": 1000.00
}
```

### Get Violations for Case
```http
GET /api/cases/{case_id}/violations?status=CONFIRMED

Response:
{
  "total": 5,
  "violations": [
    {
      "violation_id": "VIO-FCRA-2024-00001",
      "statute": "FCRA",
      "violation_type": "failure_to_investigate",
      "severity": "HIGH",
      "strength_score": 82,
      "statutory_damages_max": 1000.00
    }
  ],
  "total_statutory_damages": 5000.00,
  "estimated_settlement_value": 8500.00
}
```

### AI Detection Scan
```http
POST /api/violations/scan
Content-Type: application/json

{
  "evidence_id": "EV-2024-00001"
}

Response:
{
  "violations_detected": 2,
  "violations": [
    {
      "violation_type": "missing_validation_notice",
      "statute": "FDCPA",
      "ai_confidence": 0.89,
      "severity": "HIGH"
    },
    {
      "violation_type": "false_representation",
      "statute": "FDCPA",
      "ai_confidence": 0.72,
      "severity": "MEDIUM"
    }
  ]
}
```

---

## Compliance & Legal Considerations

### Statute of Limitations

Track expiration dates to avoid filing time-barred claims:

| Statute | Limitations Period | Starts From |
|---------|-------------------|-------------|
| FCRA | 2 years (negligent), 5 years (willful) | Discovery of violation |
| FDCPA | 1 year | Violation occurred |
| TCPA | 4 years | Call occurred |
| RESPA | 3 years | Violation occurred |
| TILA | 1 year | Violation occurred |

**Implementation:**
- Add `statute_of_limitations_expires` field
- Alert attorney when expiration approaches
- Auto-reject violations past limitations period

---

### Ethical Considerations

**Frivolous Claims:** Do not file violations without reasonable basis.

**Verification:**
- AI detection requires human review (attorney responsibility)
- `attorney_confidence` field documents attorney's assessment
- `review_notes` documents reasoning

**Example Safeguard:**
```python
def can_file_violation(violation: Violation) -> (bool, str):
    """Check if violation meets ethical standards for filing."""
    
    if not violation.human_reviewed:
        return (False, "Attorney review required before filing")
    
    if violation.attorney_confidence in ["UNLIKELY", "POSSIBLE"]:
        return (False, "Attorney confidence too low for filing")
    
    if violation.evidence_strength == "WEAK":
        return (False, "Evidence insufficient for filing")
    
    if violation.violation_strength_score < 40:
        return (False, "Overall violation strength below threshold")
    
    return (True, "Violation meets filing standards")
```

---

**END VIOLATION REGISTRY SPECIFICATION**
