# Engine Specification — Reasoning Engine

## Responsibility

Produce inspectable reasoning chains from a question to a recommendation.

## Derived From

BRA § 2.3, BKGC Article XVIII.

## Pipeline

```text
Question
    ↓
Evidence
    ↓
Authorities
    ↓
Jurisdiction
    ↓
Counter-Evidence
    ↓
Alternative Interpretations
    ↓
Risk Analysis
    ↓
Reasoning
    ↓
Confidence
    ↓
Recommendation
    ↓
Audit
```

## Stage Requirements

| Stage | Input | Output | Record |
|-------|-------|--------|--------|
| Question | User or system query | Formalized question | Query record |
| Evidence | Evidence Engine results | Evidence list | Evidence set record |
| Authorities | Authority Engine results | Authority list | Authority set record |
| Jurisdiction | Relevant jurisdictions | Jurisdiction mapping | Jurisdiction record |
| Counter-Evidence | Evidence set | Counter-evidence list | Counter-evidence record |
| Alternative Interpretations | Evidence + authorities | Interpretation list | Interpretation record |
| Risk Analysis | Failure mode catalog | Risk scores | Risk record |
| Reasoning | All prior stages | Reasoning chain | Reasoning record |
| Confidence | Evidence + reasoning | Confidence score | Confidence record |
| Recommendation | Reasoning + confidence | Recommendation | Recommendation record |
| Audit | All records | Audit trail | Audit record |

## Conformance

The Reasoning Engine MUST preserve every stage output. It MUST NOT collapse the chain into a single opaque conclusion.
