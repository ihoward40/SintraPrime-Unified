# Blackstone Reference Architecture (BRA) — Volume III

> **Blackstone Governance Library · Volume III**
> Version 1.0 · Effective 2026-07-06
> Governed by BKGC v2.0 · BGS v1.0 · BCCM v1.0 · BKR v1.0

---

## What Is BRA?

Volume III is the **codebase-resident implementation layer** of the Blackstone Governance Library. Unlike Volumes I, II, IV, and V (which are print-ready PDF governance documents), BRA lives in this repository as authoritative code and schemas.

**The codebase is the authoritative source for BRA.** If a schema or module conflicts with a prose description in another volume, the code controls — unless a Constitutional Decision Record (CDR) specifies otherwise.

---

## Package Structure

```
blackstone/bra/
├── __init__.py          # Package entry: exports CCSScorer, CEL, CDRFiler, KOValidator
├── ccs.py               # CCS Scorer — BGS-01 weighted scoring engine
├── cel.py               # Constitutional Evidence Ledger — BKGC Art. XIII–XIV
├── cdr.py               # CDR Filer — BKGC Art. XXXIII, BKR-11
├── ko.py                # Knowledge Object Validator — BGS-01 through BGS-04
├── disclaimers.py       # Standard Disclaimer Library — BKR-14, BKR-15
├── schemas/
│   ├── knowledge_object.schema.json     # JSON Schema for KO metadata (BKR-06)
│   ├── evidence_item.schema.json        # JSON Schema for CEL evidence items (BKR-03)
│   ├── cdr.schema.json                  # JSON Schema for CDR records (BKR-11)
│   └── agent_certification.schema.json  # JSON Schema for BCCM agent records (BKR-12)
├── tests/
│   ├── test_ccs.py          # CCS scoring tests
│   ├── test_cel.py          # CEL tests
│   ├── test_cdr.py          # CDR filer tests
│   └── test_disclaimers.py  # Disclaimer library tests
└── README.md            # This file — BRA entry point
```

---

## Core Modules

### `bra.ccs` — CCS Scorer

Computes the Constitutional Compliance Score (CCS) for a knowledge object using the BGS-01 weighted dimension model.

**Dimension weights (BGS-01 — immutable without CDR):**

| Dimension | Weight |
|---|---|
| Citation Integrity | 20% |
| Provenance Completeness | 18% |
| Jurisdiction Accuracy | 14% |
| Temporal Accuracy | 12% |
| Counter-Evidence Review | 12% |
| Confidence Calibration | 10% |
| Transparency | 6% |
| Auditability | 4% |
| Reproducibility | 2% |
| Evidence Preservation | 2% |

**Maturity stage minimum CCS (BGS-01, BKR-06):**

| Stage | Code | Min CCS | Key Gate |
|---|---|---|---|
| Hypothesis | STG-1 | 40 | ≥ 1 source in CEL |
| Research | STG-2 | 55 | Counter-evidence assessed |
| Corroborated | STG-3 | 68 | ≥ 1 independent source |
| Verified | STG-4 | 78 | No dimension = 0 |
| Operational | STG-5 | 82 | Citation Integrity ≥ 90, Provenance ≥ 85 |
| Litigation Ready | STG-6 | 92 | Citation Integrity = 100; all dims ≥ 80 |

```python
from blackstone.bra import CCSScorer

scorer = CCSScorer()
result = scorer.score({
    "citation_integrity": 95,
    "provenance_completeness": 88,
    "jurisdiction_accuracy": 90,
    "temporal_accuracy": 85,
    "counter_evidence_review": 82,
    "confidence_calibration": 80,
    "transparency": 85,
    "auditability": 80,
    "reproducibility": 78,
    "evidence_preservation": 85,
})
print(result.total)            # → 88.46
print(result.confidence_code)  # → "CONF-H"
print(result.maturity_floor)   # → "STG-5"
print(result.litigation_ready) # → False (Citation Integrity < 100)
```

---

### `bra.cel` — Constitutional Evidence Ledger

**Constitutional rules enforced in code:**

1. **No deletion — ever.** `cel.delete()` raises `EvidenceDeletionProhibited`. Use `cel.deprecate()`.
2. **Legal holds block modification.** `LegalHoldViolation` raised on any modification of a held item.
3. **AI-generated content is SC-06 only.** `CDR-00001` encoded — cannot add AI content as SC-01 through SC-05.
4. **Chain of custody is append-only.** Every state change is logged automatically.
5. **Re-verification intervals enforced:** SC-01/02 = 180 days, SC-03/04 = 90 days, SC-06 = 30 days.

```python
from blackstone.bra import ConstitutionalEvidenceLedger

cel = ConstitutionalEvidenceLedger()

# Add evidence
ev_id = cel.add(
    "26 U.S.C. § 6213 — Restrictions on Assessment",
    source_class="SC-01",
    collected_by="hermes",
    citation="26 U.S.C. § 6213",
    jurisdiction_code="US-FED",
)

# Authenticate
cel.authenticate(ev_id, "viktor", content_hash="sha256:...")

# Deprecate (NOT delete)
cel.deprecate(ev_id, "viktor", reason="Superseded", successor_ev_id="EV-20260801-0001")

# Attempting deletion raises EvidenceDeletionProhibited
# cel.delete(ev_id)  ← RAISES — never use

# Audit
print(cel.audit_report())
```

---

### `bra.cdr` — CDR Filer

Files and retrieves Constitutional Decision Records. Founding CDRs (CDR-00001 through CDR-00003) are seeded automatically.

```python
from blackstone.bra import CDRFiler

filer = CDRFiler()  # seeds CDR-00001 through CDR-00003

# File a new CDR
num = filer.file(
    title="Adoption of Volume VI",
    filed_by="Isiah Howard, Founder/CEO, IKE Solutions LLC",
    trigger="Volume VI completion",
    decision="Volume VI is formally adopted...",
    scope="All agents",
)
# num → "CDR-00004"

# Records are frozen (dataclass frozen=True)
# Any modification attempt raises FrozenInstanceError

print(filer.register())  # Full CDR register, ordered
```

---

### `bra.ko` — Knowledge Object Validator

Validates KO metadata against BKGC and BGS rules before maturity stage advancement.

```python
from blackstone.bra import KnowledgeObjectValidator

validator = KnowledgeObjectValidator()
result = validator.validate(ko_dict)

if result.valid:
    print("✓ KO passes constitutional validation")
else:
    for err in result.errors:
        print(f"✗ {err}")
```

---

### `bra.disclaimers` — Standard Disclaimer Library

```python
from blackstone.bra.disclaimers import get_disclaimer, select_disclaimers

# Get approved text
text = get_disclaimer("DIS-NLA-01")

# Auto-select applicable disclaimers for an output
ids = select_disclaimers(
    claim_status_code="EDU",
    confidence_code="CONF-P",
    temporal_current=False,
)
# → ["DIS-NLA-01", "DIS-UNC-01", "DIS-UNC-04"]
```

---

## JSON Schemas

The `schemas/` directory contains JSON Schema (2020-12) definitions for all primary data structures. Use these for:
- Validating KO records before CEL submission
- Validating CDR records before filing
- Validating evidence item records
- Validating agent certification records

All schemas use `"additionalProperties": false` to prevent undocumented field drift.

---

## Running Tests

```bash
# From repo root
pytest blackstone/bra/tests/ -v
```

All four test modules (`test_ccs`, `test_cel`, `test_cdr`, `test_disclaimers`) must pass before any BRA module is considered compliant per BCCM-05.

---

## Governance

| Rule | Source | Implementation |
|---|---|---|
| CCS weights are immutable without CDR | BGS-01 | `assert` at import time in `ccs.py` |
| Evidence items never deleted | BKGC Art. XIII | `delete()` raises `EvidenceDeletionProhibited` |
| Legal holds block modification | BGS-19 | `_require_mutable()` checks in `cel.py` |
| AI content is SC-06 only | CDR-00001 | Enforced in `cel.add()` |
| CDRs immutable after filing | BKGC Art. XXXIII | `@dataclass(frozen=True)` in `cdr.py` |
| $500 financial trigger | BGS-11 | Checked in `ko.py` validator |
| Litigation Ready all-dims ≥ 80 | BGS-01 | CCS scorer and KO validator both enforce |

---

## Amendment Process

BRA modules may not be modified to relax constitutional constraints without a CDR. Changes that:
- Alter CCS dimension weights
- Remove deletion protection from the CEL
- Remove legal hold enforcement
- Change CDR immutability

...require a supermajority CDR per BKGC Art. XXXV.

Non-constitutional improvements (new helper methods, performance optimizations, additional validation checks) may be made via standard PR process with Governance Board approval.

---

*Volume III — Blackstone Reference Architecture · v1.0 · 2026-07-06*
*Governed by BKGC v2.0 · BGS v1.0 · BCCM v1.0 · BKR v1.0*
