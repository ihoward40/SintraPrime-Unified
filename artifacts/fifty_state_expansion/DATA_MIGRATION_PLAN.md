# Phase 0 Data Migration Plan

Status: proposed plan only
Production migration executed: no

## Existing Data Locations

Trust and legal-reference material:

- `trust_law/trust_knowledge_base.py`;
- `trust_law/jurisdiction_analyzer.py`;
- `trust_law/trust_reasoning_engine.py`;
- `trust_law/trust_document_generator.py`;
- `web/src/pages/TrustLaw.tsx`;
- `developer_experience/cookbook.py`;
- `developer_experience/openapi_spec.py`;
- `governance/blackstone/volume-*`.

UCC and financing-statement material:

- `trust_law/ucc_filing_assistant.py`;
- static UI material in `web/src/pages/TrustLaw.tsx`;
- source documents or examples referenced by Blackstone case materials.

Jurisdiction coverage material:

- static jurisdiction references in `trust_law/jurisdiction_analyzer.py`;
- static UI jurisdiction arrays in `web/src/pages/TrustLaw.tsx`;
- Phase 0 coverage scaffold in `data/jurisdictions/coverage.json`.

Parliament and multi-agent material:

- `trust_law/trust_parliament.py`;
- `web/src/pages/AIParliament.tsx`;
- `parl/`;
- `agent_protocol/`;
- `agents/`.

Document, evidence, and audit material:

- `portal/models/document.py`;
- `portal/models/evidence_snapshot.py`;
- `portal/models/audit_record.py`;
- `portal/services/evidence_hash_boundary.py`;
- `portal/services/evidence_snapshot_service.py`;
- `portal/services/evidence_audit_service.py`;
- `portal/services/audit_service.py`;
- `portal/services/packet_renderer.py`.

## Static Content That Can Be Migrated

The following can be migrated as source material, not verified rules:

- doctrine summaries from `trust_law/trust_knowledge_base.py`;
- jurisdiction ranking factors from `trust_law/jurisdiction_analyzer.py`;
- UCC educational summaries from `trust_law/ucc_filing_assistant.py`;
- UI doctrine cards and example jurisdictions from `web/src/pages/TrustLaw.tsx`;
- governance source-taxonomy concepts from Blackstone documents.

Imported records must default to `verification_status='unverified'` and `requires_human_review=true`.

## Content Requiring Reclassification

Reclassify source records into:

- `PRIMARY_LEGAL_AUTHORITY`;
- `OFFICIAL_FORM`;
- `OFFICIAL_GUIDANCE`;
- `COURT_DECISION`;
- `SECONDARY_LEGAL_SOURCE`;
- `PROFESSIONAL_STANDARD`;
- `CLIENT_DOCUMENT`;
- `EDUCATIONAL_MATERIAL`;
- `PRIVATE_TEMPLATE`;
- `UNVERIFIED_PRIVATE_LAW_CLAIM`;
- `UNKNOWN`.

Static repository files should not be promoted above `EDUCATIONAL_MATERIAL`, `PRIVATE_TEMPLATE`, or `UNKNOWN` without source verification.

## Content Requiring Quarantine

Quarantine claims involving:

- accepted-for-value debt discharge;
- secret Treasury or birth-certificate accounts;
- birth-certificate securities;
- automatic acquiescence by silence;
- all-capital-letter separate-entity theories;
- automatic debt discharge by endorsement;
- universal admiralty-court theories;
- automatic lien creation from private notices;
- UCC filings as ownership of persons, names, government accounts, or unrelated property;
- manufactured tax offsets or credits.

Do not delete original source material. Preserve it as evidence while excluding it from production rule evaluation.

## Content That Must Remain Read-Only

- Historical source documents and uploaded client evidence;
- evidence snapshots and content hashes;
- audit records;
- superseded authority records;
- quarantined unsupported claims;
- governance Blackstone materials unless separately migrated into product schemas.

Corrections should append a review or supersession record rather than mutate the original source record.

## Proposed Identifiers

- `SRC-{jurisdiction_or_scope}-{hash_prefix}` for source documents;
- `AUTH-{jurisdiction}-{domain}-{sequence}` for legal authorities;
- `RULE-{jurisdiction}-{domain}-{topic}-{sequence}` for jurisdiction rules;
- `JUR-{code}` for jurisdiction coverage records;
- `CLAIMQ-{hash_prefix}` for quarantined unsupported claims;
- `CONFLICT-{jurisdiction}-{sequence}` for conflicting-authority records;
- `PREVIEW-{hash_prefix}` for non-execution-ready generated clause drafts.

Identifiers should be stable across imports when source content hash and normalized citation match.

## Schema Versioning

- Start with `schema_version=1` for coverage and source-ingestion fixtures.
- Add `model_version` to rule logic and scoring outputs.
- Add `migration_batch_id` to imported records.
- Retain prior schema versions in read-only migration manifests.
- Reject imports with unknown future schema versions unless a compatibility adapter exists.

## Rollback Plan

- Every migration run writes a manifest with source hashes, target IDs, counts, and validation results.
- Rollback deactivates imported records by migration batch rather than deleting them.
- Evidence snapshots, audit records, and source hashes are retained.
- If a rule was promoted incorrectly, create a supersession/deactivation record and preserve the original as audit evidence.

## Duplicate Handling

- Deduplicate by content hash first.
- Deduplicate citations by normalized citation plus jurisdiction plus authority type.
- Preserve duplicate source appearances as provenance links even when the underlying document hash already exists.
- Treat conflicting summaries of the same citation as review issues, not automatic duplicates.

## Citation Normalization

Normalize:

- reporter and statutory abbreviations;
- jurisdiction code;
- section symbols and punctuation;
- year and effective-date markers where available;
- official source URL canonical form.

Do not normalize away material distinctions between official statutes, court decisions, regulations, administrative rules, and secondary summaries.

## Preservation of Source Provenance

Each migrated record should retain:

- original file path or source document ID;
- content hash;
- extraction timestamp;
- importer version;
- classification decision;
- verification status;
- citation extraction output;
- reviewer notes;
- audit event ID.

## Migration Validation Strategy

Validate before enabling Phase 1 rule encoding:

- all imported records have a source class;
- all production-candidate rules link to at least one authority;
- no `UNVERIFIED_PRIVATE_LAW_CLAIM` record is reachable by the rule evaluator;
- no jurisdiction support status exceeds the verified evidence state;
- deactivated and superseded records remain queryable but inactive;
- imports are idempotent by hash;
- tenant-private documents cannot leak through global authority APIs.
