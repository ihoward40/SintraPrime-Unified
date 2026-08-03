# Phase 0 Security and Privacy Review

Status: review of current repository evidence
Production security changes in this phase: none

## Review Summary

The portal already has useful RBAC, tenant, audit, encryption, document, and storage primitives. The expansion would introduce much higher-risk legal, financial, creditor, and document-ingestion workflows. Those workflows are not safe to expose until support status, source classification, privacy classification, professional review, and audit logging are enforced server-side.

No personal identifiers from source documents are reproduced in this review.

## Findings

| ID | Severity | Area | Finding | Evidence |
|---|---|---|---|---|
| SEC-001 | Critical | Legal output integrity | Static trust and UCC modules can produce confident legal or filing language without primary-authority verification, effective-date handling, or professional review. | `trust_law/trust_knowledge_base.py`, `trust_law/ucc_filing_assistant.py` |
| SEC-002 | Critical | Unsupported claims | Risky private-law theories are detected in one router, but there is no durable quarantine store or UI containment boundary. | `portal/routers/trust_compliance.py` |
| SEC-003 | High | Data classification | No integrated server-side taxonomy for `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `HIGHLY_CONFIDENTIAL`, `RESTRICTED_PII`, `RESTRICTED_FINANCIAL`, or `RESTRICTED_LEGAL` was found. | `portal/models`, `portal/services` |
| SEC-004 | High | Export controls | Document export primitives exist, but no Phase 0 evidence shows purpose-bound access, privacy budget, watermarking, or sensitive-field exposure tracking for the proposed legal/financial exports. | `portal/services/document_export_service.py`, `portal/services/share_service.py` |
| SEC-005 | High | Model-output trust | Future source ingestion and parliament workflows would be vulnerable if extracted citations or generated conclusions are trusted without verifier state and evidence links. | `blackstone/models.py`, `trust_law/trust_parliament.py` |
| SEC-006 | Medium | Tenant boundaries | Existing portal RBAC and tenant tests are reusable, but the proposed legal-rule, creditor, privacy, and parliament APIs do not yet exist and therefore have no tenant-boundary tests. | `portal/auth/rbac.py`, `portal/tests` |
| SEC-007 | Medium | Audit coverage | Audit services exist, but new legal-rule reads, source imports, quarantines, professional reviews, privacy disclosures, and exports require explicit audit event definitions. | `portal/services/audit_service.py`, `portal/models/audit_record.py` |
| SEC-008 | Medium | Prompt injection | Document ingestion is not yet designed to isolate malicious instructions embedded in uploaded legal or creditor documents from model prompts and downstream actions. | `portal/services/document_processor.py` |
| SEC-009 | Medium | Administrative overrides | New professional review and administrative correction workflows need dual-control or immutable audit records to prevent silent promotion of unverified rules. | `portal/auth/rbac.py`, `portal/services/audit_service.py` |
| SEC-010 | Medium | Ignored jurisdiction data | `data/jurisdictions/coverage.json` is hidden by a broad `data/` ignore rule, which can cause core coverage scaffolding to be omitted unless force-added or narrowly unignored. | `.gitignore:63:data/` |

## Tenant Isolation

Current portal primitives indicate tenant-aware identity and RBAC patterns. New records must distinguish:

- global public authority records;
- tenant-private client documents;
- tenant-private creditor matters;
- tenant-private trust assessments;
- professional review records scoped to authorized reviewers.

Tenant-private source documents must never become globally visible merely because a citation was extracted from them.

## Authorization Boundaries

Add explicit permissions for:

- source ingestion;
- legal authority creation and review;
- jurisdiction rule activation;
- creditor workspace access;
- audit-readiness workpapers;
- professional review;
- privacy disclosures and exports;
- parliament job creation and review;
- unsupported-claim quarantine access.

Read-only education access should not imply authority to view client documents or private evidence.

## Document Permissions

Document reads, downloads, shares, and exports should be logged. Selective disclosure packets should expose only approved fields and must not include full instruments unless the user role and purpose permit it.

## Sensitive-Field Handling

The expansion should classify and protect:

- Social Security numbers;
- account numbers;
- tax identifiers;
- birth dates;
- creditor account details;
- trust beneficiary identities;
- asset schedules;
- professional workpapers;
- litigation and creditor evidence.

Use field-level encryption or redaction where justified by data class.

## Audit Logging

Audit events should be mandatory for:

- source import;
- classification change;
- unsupported-claim quarantine;
- authority verification;
- rule activation or deactivation;
- professional challenge;
- privacy export;
- selective disclosure;
- document view/download;
- parliament conclusion approval.

## Encryption and Secrets Assumptions

The portal contains encryption and storage services, but Phase 0 did not verify runtime key management, rotation, backup encryption, or restore tests. Treat these as required verification items for later security hardening.

## Prompt-Injection and Malicious Documents

Document ingestion must treat uploaded content as untrusted. It should isolate extracted facts from instructions, preserve raw text as evidence, and require independent verification before model output changes rules or advice.

## Privacy Risks in Current Static Files

Static source and UI files can mix educational statements, legal propositions, and examples without classification. Before migration, classify each source and redact or restrict any private client evidence. This Phase 0 artifact references files generically and does not reproduce personal identifiers.
