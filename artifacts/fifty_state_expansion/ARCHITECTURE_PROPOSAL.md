# Phase 0 Architecture Proposal

Status: proposal only
Scope: fifty-state trust intelligence, creditor response, audit readiness, privacy, and parliament expansion
Production code changes in this phase: none

## Existing Reusable Components

- `portal/` is the authoritative API, identity, RBAC, audit, and persistence boundary.
- `portal/auth/rbac.py` provides role and tenant enforcement patterns to reuse for new legal, creditor, privacy, and review APIs.
- `portal/services/audit_service.py` and `portal/models/audit_record.py` provide hash-chained audit logging patterns.
- `portal/services/evidence_hash_boundary.py`, `portal/services/evidence_snapshot_service.py`, `portal/services/evidence_audit_service.py`, and `portal/services/packet_renderer.py` provide evidence integrity and packet rendering primitives.
- `portal/models/document.py`, `portal/routers/documents.py`, `portal/services/document_processor.py`, `portal/services/storage_service.py`, `portal/services/share_service.py`, and `portal/services/document_export_service.py` provide document vault foundations.
- `blackstone/models.py` provides useful source, claim, evidence, confidence, and provenance concepts, but should be treated as a design reference rather than production persistence.
- `portal/routers/trust_compliance.py` provides phrase detection for risky private-law theories and should be reused as an initial classifier input.
- `web/src/pages/TrustLaw.tsx` and `web/src/pages/AIParliament.tsx` are usable UI prototypes, but embedded legal content must move behind verified APIs.

## Proposed Legal Authority Model

Create a portal-native `legal_authorities` model with tenant-aware access rules for private source material and global read semantics for approved public authority records.

Required fields:

- stable `id`;
- `jurisdiction`;
- `authority_type`;
- `citation`;
- `title`;
- `source_url`;
- `source_document_id`;
- `effective_date`;
- `repeal_date`;
- `last_verified_at`;
- `verifier`;
- `verification_status`;
- `quoted_text`;
- `summary`;
- `limitations`;
- `tags`;
- created, updated, and audit metadata.

Supported verification states:

- `verified_primary`;
- `verified_secondary`;
- `unverified`;
- `superseded`;
- `conflicting`.

Default import behavior must be `unverified` unless a source verifier records controlling primary authority.

## Proposed Jurisdiction Rule Model

Create `jurisdiction_rules` linked to one or more `legal_authorities`.

Required fields:

- stable `id`;
- `jurisdiction`;
- `domain`;
- `topic`;
- `rule_statement`;
- machine-readable `rule_logic`;
- `authority_ids`;
- `confidence`;
- `requires_human_review`;
- `effective_from`;
- `effective_to`;
- `exceptions`;
- `conflicting_rule_ids`;
- `version`;
- status and audit metadata.

Rules must never be activated solely from static tables, workbooks, templates, or uploaded private manuals.

## Provenance Model

Create `legal_source_documents` and `source_provenance_links` to preserve:

- document title, author, publisher, date, jurisdiction, and class;
- content hash;
- ingestion timestamp;
- extracted citations;
- verified citations;
- invalid or stale citations;
- unsupported claims;
- privacy classification;
- permitted use and copyright notes;
- links to evidence snapshots.

Provenance must be immutable for ingested content. Corrections should create new review records rather than overwrite original evidence.

## Effective-Date Handling

Rule evaluation must select the rule active on the requested analysis date:

- future-effective authorities cannot support current conclusions;
- repealed authorities remain queryable but inactive after repeal;
- rules with missing effective dates require human review;
- jurisdiction coverage cannot advance beyond `PRIMARY_AUTHORITY_PARTIAL` if date metadata is incomplete for required topics.

## Supersession Handling

Authority and rule records should support:

- `supersedes_authority_ids`;
- `superseded_by_authority_ids`;
- `supersedes_rule_ids`;
- `superseded_by_rule_ids`;
- repeal date and transition notes;
- migration notes explaining why the old rule remains inactive.

Superseded rules remain in the evidence trail for auditability.

## Conflicting-Authority Handling

Conflicts should be explicit records, not hidden scoring adjustments.

Each conflict record should include:

- proposition;
- supporting authority;
- opposing authority;
- authority hierarchy;
- jurisdiction relevance;
- effective dates;
- recency;
- unresolved questions;
- final disposition;
- human-review status.

Rules with unresolved controlling conflicts should evaluate to `CONFLICTING_AUTHORITY` or `HUMAN_REVIEW_REQUIRED`, not a definitive legal conclusion.

## State Support Lifecycle

Use only the approved support statuses:

- `NOT_STARTED`;
- `RESEARCH_IN_PROGRESS`;
- `PRIMARY_AUTHORITY_PARTIAL`;
- `PRIMARY_AUTHORITY_COMPLETE`;
- `RULES_ENCODED`;
- `TESTED`;
- `HUMAN_REVIEWED`;
- `PRODUCTION_ELIGIBLE`.

No jurisdiction is production eligible in Phase 0. Static mentions in code, UI, or documents do not advance support status.

## Professional-Review Gates

Require professional review before:

- marking legal rules `HUMAN_REVIEWED`;
- generating execution-ready trust clauses;
- publishing UCC filing instructions as anything beyond draft education;
- presenting tax, audit, or accounting conclusions;
- resolving conflicting authority;
- removing `UNVERIFIED_PRIVATE_LAW_CLAIM` quarantine from a source claim.

Professional review records should include reviewer role, jurisdiction, timestamp, reviewed evidence, decision rationale, limitations, and expiry or re-review triggers.

## API Boundaries

Proposed portal APIs:

- `/api/v1/legal-intelligence/coverage`;
- `/api/v1/legal-intelligence/authorities`;
- `/api/v1/legal-intelligence/rules`;
- `/api/v1/legal-intelligence/compare`;
- `/api/v1/legal-intelligence/conflicts`;
- `/api/v1/source-ingestion/documents`;
- `/api/v1/source-ingestion/quarantine`;
- `/api/v1/trust-health/assessments`;
- `/api/v1/creditor-response/matters`;
- `/api/v1/audit-readiness/workpapers`;
- `/api/v1/privacy/disclosures`;
- `/api/v1/professional-review/items`;
- `/api/v1/parliament/jobs`.

Every endpoint must be RBAC-gated, tenant-scoped where private data is involved, paginated where collections are returned, and audit logged for sensitive reads or exports.

## Frontend Surfaces

The existing web app should consume verified APIs for:

- Fifty-State Coverage Map;
- Jurisdiction Comparison;
- Trust Health Report;
- Creditor Evidence Workspace;
- Financial Audit Readiness;
- Multi-Agent Parliament;
- Simulation Lab;
- Evolution Timeline;
- Beneficiary Portal;
- Privacy Command Center;
- Document Provenance Viewer;
- Professional Review Queue.

Static legal arrays in UI components should be replaced with API-backed data that displays verification status, support level, limitations, and human-review state.

## Migration Sequence

1. Add schemas and tests for source documents, legal authorities, jurisdiction rules, coverage, conflicts, and unsupported-claim quarantine.
2. Import existing static trust, UCC, and UI content as `unverified` source material or quarantine records.
3. Build read-only coverage and authority APIs.
4. Build warning-aware frontend surfaces that refuse to label any jurisdiction complete without support status.
5. Begin New Jersey primary-authority research pilot after Phase 0 review.
6. Encode a narrow New Jersey rule set with effective dates, tests, and review gates.
7. Expand by region only after the rule lifecycle is proven.

## Rejected Alternatives

- Do not treat `trust_law/*` static dictionaries as production legal rules.
- Do not mount legacy legal modules directly into portal APIs.
- Do not keep legal rules embedded in React component constants.
- Do not use simple parliament majority voting as the sole decision rule.
- Do not broaden `.gitignore` exceptions for the whole `data/` tree merely to track one coverage file.
- Do not represent uploaded manuals, templates, or workbooks as controlling law without primary authority verification.

## Architecture Risks

- Legal authority verification can become stale without a statutory drift monitor and re-verification workflow.
- Professional review may become a bottleneck unless review queues and expiry metadata are designed early.
- Source ingestion is prompt-injection sensitive and must treat model output as untrusted.
- Jurisdiction comparison is high risk if support levels differ across states but the UI hides incomplete coverage.
- Static legacy modules may continue to be imported accidentally unless production APIs explicitly exclude them.
