# Unsupported Claim Containment

Status: Phase 0 containment design
Production quarantine implemented: no

## Classification

Use this source and claim class:

```text
UNVERIFIED_PRIVATE_LAW_CLAIM
```

This class means a claim is preserved as source material or historical evidence but is not accepted as controlling law, not emitted as automated legal advice, and not used as creditor-defense or filing logic.

## Claim Families to Identify

Classify the following as `UNVERIFIED_PRIVATE_LAW_CLAIM` unless independently verified against controlling primary authority:

- accepted-for-value theories;
- secret Treasury accounts;
- birth-certificate securities;
- automatic acquiescence by silence;
- all-capital-letter separate-entity claims;
- automatic debt discharge by endorsement;
- universal admiralty-court theories;
- automatic lien creation from private notices;
- UCC filings as ownership of persons, names, government accounts, or unrelated property;
- tax-form offset or manufactured-credit theories.

## Ingestion Behavior

On source ingestion:

- preserve the original document and content hash;
- classify the source document and each extracted unsupported claim;
- store the extracted claim text as evidence subject to copyright and privacy limits;
- mark `rule_engine_excluded=true`;
- mark `requires_human_review=true`;
- link to evidence snapshots and audit records;
- prevent promotion to `LegalAuthority` without primary-authority verification and professional review.

The system should not delete or alter original source material.

## UI Warnings

Any UI surface showing this material must display:

```text
UNVERIFIED PRIVATE-LAW CLAIM - PRESERVED AS SOURCE MATERIAL ONLY
```

The warning should also state that the material is not verified legal authority, not a filing instruction, not a debt-discharge conclusion, and not professional legal, tax, accounting, or audit advice.

## Search Visibility

Default search should exclude quarantined claims from ordinary legal-rule lookup and user-facing recommendations.

Permitted visibility:

- source reviewers;
- professional reviewers;
- compliance administrators;
- audit users with explicit permission;
- users viewing their own uploaded evidence where access is otherwise allowed.

Search results must show the quarantine warning and source class.

## Rule-Engine Exclusion

The rule engine must not:

- cite quarantined claims as authority;
- use quarantined claims to satisfy rule elements;
- calculate creditor defenses from quarantined theories;
- generate UCC filing instructions from quarantined theories;
- mark debts discharged based on quarantined theories;
- generate tax offsets or credits based on quarantined theories.

## Citation Treatment

Citations inside quarantined documents should be extracted and classified separately.

- Verified primary citations may become authority records only through normal verification.
- Invalid or unsupported citations remain linked to the quarantine record.
- A correct citation inside an unsupported document does not validate the unsupported proposition.

## Professional-Review Requirements

Professional review is required before:

- changing a claim out of quarantine;
- linking a quarantined source to an authority record;
- using a claim in an educational explanation;
- including a claim in a creditor-response issue list;
- producing any user-facing conclusion that references the claim.

The review record must preserve the original classification and the reason for any change.

## Audit Logging

Audit events are required for:

- initial classification;
- quarantine creation;
- reviewer access;
- classification changes;
- attempted rule-engine use;
- export or disclosure of quarantined material;
- professional challenge and disposition.

## Test Requirements

Create tests for:

- accepted-for-value detection;
- secret Treasury account detection;
- birth-certificate security detection;
- automatic acquiescence by silence;
- all-capital-letter separate-entity claims;
- automatic debt discharge by endorsement;
- admiralty jurisdiction theories;
- automatic lien creation from private notices;
- UCC ownership-of-person or government-account theories;
- tax-form offset or manufactured-credit theories;
- exclusion from rule evaluation;
- warning display;
- audit logging.
