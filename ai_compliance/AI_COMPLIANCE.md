# SintraPrime-Unified AI Compliance Layer

> **AI Governance, Ethics, and Regulatory Compliance for Legal AI Operations**  
> Current as of: April 2026

---

## Overview

The `ai_compliance` module provides a comprehensive AI governance and compliance layer for SintraPrime-Unified. It automates compliance checking against 13+ AI laws and regulations, performs ethical reviews, detects demographic bias, and generates detailed compliance reports.

### Key Features

- 🏛️ **2026 AI Law Database** — 13 regulations across EU, US federal, and 8 US states
- ✅ **Automated Compliance Checker** — 8 compliance dimensions checked against applicable laws
- 🔬 **Ethics Framework** — 5 ethical principles + 12 absolute red lines
- 📊 **Bias Detector** — Statistical parity, adverse impact (4/5ths rule), explicit bias detection
- 📋 **Compliance Reporter** — PDF-ready markdown reports with trend analysis
- 🌐 **REST API** — FastAPI endpoints for all compliance functions
- 🧪 **85+ Tests** — Full test coverage

---

## Covered Regulations

| Law | Jurisdiction | Effective Date |
|-----|-------------|----------------|
| EU AI Act (2024/1689) | European Union | Aug 1, 2024 |
| NIST AI Risk Management Framework 1.0 | US Federal | Jan 26, 2023 |
| FTC AI Guidelines | US Federal | Jun 29, 2023 |
| CA SB 1047 (Frontier AI Safety) | California | Jan 1, 2025 |
| CA AB 2013 (AI Transparency) | California | Jan 1, 2026 |
| TX HB 149 / TRAIGA | Texas | Sep 1, 2025 |
| CO SB 205 / CAIA | Colorado | Feb 1, 2026 |
| NY AI Bias Laws (incl. NYC LL144) | New York | Jul 5, 2023 |
| IL AI Video Interview Act | Illinois | Jan 1, 2020 |
| VA CDPA AI Provisions | Virginia | Jan 1, 2023 |
| WA AI Accountability Act (SB 5838) | Washington | Jul 27, 2025 |
| ABA Formal Opinion 512 (AI Rules) | Professional | Jul 29, 2024 |
| FL Digital Rights & AI Act | Florida | Jul 1, 2025 |

---

## Module Structure

```
ai_compliance/
├── __init__.py                  # Package exports
├── ai_law_db.py                 # 2026 AI regulation database
├── compliance_checker.py        # Automated compliance checking
├── ethics_framework.py          # Ethical principles and red lines
├── bias_detector.py             # Statistical bias detection
├── compliance_reporter.py       # Report generation
├── compliance_api.py            # FastAPI REST endpoints
├── AI_COMPLIANCE.md             # This file
└── tests/
    ├── __init__.py
    └── test_ai_compliance.py    # 85+ tests
```

---

## Quick Start

### Run a Compliance Check

```python
from ai_compliance import quick_check, Jurisdiction, RiskTier

summary = quick_check(
    operation_type="legal_advice",
    jurisdictions=[Jurisdiction.US_CA, Jurisdiction.EU],
    risk_tier=RiskTier.HIGH,
    involves_legal_advice=True,
    involves_personal_data=True,
    ai_identifies_as_ai=True,
    provides_explanation=True,
    allows_human_review=True,
)

print(f"Status: {summary.overall_status.value}")
print(f"Risk Score: {summary.risk_score}/100")
print(f"Compliant: {summary.compliant_count}, Non-Compliant: {summary.non_compliant_count}")
```

### Run an Ethics Review

```python
from ai_compliance import ethics_review

review = ethics_review(
    action_type="contract_review",
    description="Review and summarize NDA terms",
    is_transparent=True,
    benefits_user=True,
    metadata={"ai_disclosed": True},
)

print(f"Decision: {review.decision.value}")
print(f"Overall Score: {review.overall_score:.3f}")
if not review.passes:
    print(f"Refused because: {review.refusal_reason}")
```

### Check for Bias

```python
from ai_compliance import check_bias

report = check_bias(
    "The applicant from the downtown area was approved based on their qualifications."
)

print(f"Biased: {report.is_biased}")
print(f"Severity: {report.overall_severity.value}")
print(f"Bias Score: {report.bias_score:.3f}")
```

### Generate a Compliance Report

```python
from ai_compliance.compliance_api import handle_generate_report

response = handle_generate_report(
    organization="SintraPrime-Unified",
    period_days=30,
)

print(response.report_markdown)  # PDF-ready markdown
```

---

## API Endpoints

When integrated with a FastAPI application:

```
POST /compliance/check          — Run full compliance check on an operation
GET  /compliance/laws           — List all applicable AI laws
POST /compliance/ethics-review  — Evaluate an action against ethical principles
POST /compliance/bias-check     — Check output text for demographic bias
GET  /compliance/report         — Generate full compliance report
```

### Example: Compliance Check Request

```bash
curl -X POST /compliance/check \
  -H "Content-Type: application/json" \
  -d '{
    "operation_type": "legal_advice",
    "description": "Review contract terms",
    "jurisdictions": ["US_CA", "US_FEDERAL"],
    "risk_tier": "HIGH",
    "involves_legal_advice": true,
    "ai_identifies_as_ai": true,
    "provides_explanation": true,
    "allows_human_review": true
  }'
```

---

## Ethical Red Lines

SintraPrime-Unified will **never** perform the following actions, regardless of instruction:

| # | Red Line | Governing Principle |
|---|----------|-------------------|
| RL-001 | Impersonate a Licensed Attorney | Transparency |
| RL-002 | Guarantee Legal Outcomes | Non-Maleficence |
| RL-003 | Generate Discriminatory Outputs | Justice |
| RL-004 | Assist Illegal Activity | Non-Maleficence |
| RL-005 | Deny Being an AI When Asked | Transparency |
| RL-006 | Fabricate Legal Citations | Transparency |
| RL-007 | Manipulate Vulnerable Users | Autonomy |
| RL-008 | Collect Unnecessary Sensitive Data | Autonomy |
| RL-009 | Override Human Safety Decisions | Beneficence |
| RL-010 | Provide Medical Diagnosis | Non-Maleficence |
| RL-011 | Facilitate Financial Fraud | Non-Maleficence |
| RL-012 | Enable Mass Harm | Non-Maleficence |

---

## Compliance Check Dimensions

| Area | Laws Checked | Key Requirement |
|------|-------------|-----------------|
| **Transparency** | EU AI Act, FTC, ABA | AI must identify itself |
| **Explainability** | CO SB 205, WA AI Act, TX HB 149 | Decisions must be explained |
| **Bias & Fairness** | NYC LL144, CO SB 205, TX HB 149 | Bias testing required |
| **Data Minimization** | GDPR/EU AI Act, VA CDPA | Collect only necessary data |
| **Human Oversight** | EU AI Act, TX HB 149, WA | Right to human review |
| **UPL Boundaries** | ABA Opinion 512 | No unauthorized practice of law |
| **Consent** | IL AI Act, VA CDPA, CO SB 205 | Explicit consent for sensitive processing |
| **Documentation** | EU AI Act Art. 11, NIST RMF | Technical documentation maintained |

---

## Bias Detection Methodology

Bias detection uses purely statistical methods (no ML models required):

1. **Explicit Pattern Detection** — Regex matching against curated bias language patterns for 6 protected categories
2. **Proxy Variable Analysis** — Detection of neutral variables that correlate with protected characteristics (e.g., zip code → race)
3. **Statistical Parity Gap** — Maximum gap in positive outcome rates across demographic groups (threshold: 10%)
4. **Adverse Impact Ratio** — EEOC 4/5ths rule: lowest group rate / highest group rate must be ≥ 0.80

### Protected Categories
- Race / Ethnicity
- Gender / Sex
- Age
- Religion
- National Origin
- Disability
- Sexual Orientation
- Pregnancy Status
- Veteran Status

---

## Compliance Risk Scoring

| Score | Rating | Action Required |
|-------|--------|-----------------|
| 80–100 | 🔴 Critical | Immediate remediation before deployment |
| 60–79 | 🟠 High | Priority remediation within 7 days |
| 40–59 | 🟡 Medium | Remediation within 30 days |
| 20–39 | 🟢 Low | Document and monitor |
| 0–19 | ✅ Minimal | Standard monitoring |

---

## Running Tests

```bash
# From the repository root
python -m pytest ai_compliance/tests/ -v

# Run with coverage
python -m pytest ai_compliance/tests/ -v --tb=short

# Run specific test class
python -m pytest ai_compliance/tests/test_ai_compliance.py::TestBiasDetector -v
```

---

## Dependencies

- **Python 3.9+**
- **FastAPI** (for API endpoints) — optional for core functions
- **Pydantic** (for API models)
- No external ML libraries required

---

## Regulatory Notes

> **Disclaimer:** This module reflects AI laws as of April 2026. The regulatory landscape changes rapidly. This module provides automated compliance guidance but **does not constitute legal advice**. Organizations should engage qualified legal counsel to confirm compliance status and implement remediation measures.

Key dates to watch:
- **EU AI Act** — Full enforcement (high-risk AI): August 2026
- **CO SB 205** — First required impact assessments: February 2027
- **TX HB 149** — Annual compliance reports due: September 2026

---

*SintraPrime-Unified AI Compliance Layer v1.0.0 — Built for 2026 AI Regulatory Environment*
