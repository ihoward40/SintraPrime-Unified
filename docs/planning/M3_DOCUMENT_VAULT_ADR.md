# Architecture Decision Record (ADR): M3 Document Vault

**Status:** Approved  
**Date:** 2026-07-06  
**Author:** Hermes Agent  
**Decision ID:** ADR-M3-001  
**Scope:** Phase 2 / M3 Operational Platform — Document Vault page

---

## 1. Context

Phase 1 of the SintraPrime Unified Portal established an immutable evidence platform (EvidenceSnapshot, HashBoundary, PacketRenderer, AuditRecord). Phase 2 / M3 requires operational pages that consume that trust foundation. The first page is the **Document Vault**: a case file repository and exhibit manager that lets users upload, organize, version, and export documents into evidence packets.

---

## 2. Decision

Build Document Vault as a vertical slice with:

- **Backend:** FastAPI routers + SQLAlchemy async models + GCS file storage + Phase 1 evidence services for packet export.
- **Frontend:** React + TypeScript + Vite + Zustand + TanStack Query + Tailwind + Radix primitives.
- **Storage:** Google Cloud Storage (GCS) for file blobs; PostgreSQL for metadata, versions, and case linkage.
- **Export:** Reuse `PacketRenderer` and `AuditService` to generate a verifiable evidence packet from selected documents.
- **Tests:** Unit tests for services, API tests for routers, Playwright E2E for the user flow.

---

## 3. Consequences

### Positive
- Directly leverages the live Phase 1 evidence pipeline.
- Single source of truth: metadata in Postgres, immutable blobs in GCS.
- Packet export is deterministic and auditable (ED-003, ED-005, ED-007).
- File size limits and allowed types prevent abuse and simplify indexing.

### Negative / Risks
- GCS bucket and service account must be provisioned.
- Async GCS uploads add latency; requires background processing for large files.
- Versioning storage can grow; lifecycle rules should be set on the bucket.

### Mitigations
- Use signed URLs for direct browser upload where possible.
- Store only metadata + GCS object names in Postgres; never store raw file content in DB.
- Implement virus scanning / content validation before GCS write.
- Set bucket retention and object lifecycle policies.

---

## 4. Alternatives Considered

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Store files in Postgres bytea | Simpler backups | DB bloat, slow, expensive | ❌ Rejected |
| Use local filesystem | Cheap | Not Cloud Run compatible, no HA | ❌ Rejected |
| Use Supabase Storage | Managed | Adds vendor lock-in, not in current stack | ❌ Rejected |
| **Use GCS** | Native GCP, Cloud Run compatible, scalable, signed URLs | Requires IAM setup | ✅ Approved |

---

## 5. Architecture

```
Frontend (React + Zustand + TanStack Query)
        │
        ▼
FastAPI Router: /api/v1/vault/*
        │
        ├── DocumentService (metadata, versions, indexing)
        ├── GCSStorageService (blob upload/download/signed URLs)
        └── PacketExportService → PacketRenderer + AuditService
        │
        ▼
PostgreSQL (metadata)          GCS (blobs)
```

---

## 6. Data Model

### `Document` (SQLAlchemy)
- `id` (UUID, PK)
- `case_id` (UUID, FK, indexed)
- `tenant_id` (UUID, indexed, RLS)
- `filename` (str)
- `content_type` (str)
- `gcs_path` (str, unique)
- `gcs_bucket` (str)
- `size_bytes` (int)
- `checksum_sha256` (str)
- `exhibit_label` (str, nullable, e.g., "A", "B-1")
- `document_type` (enum: FACT, AUTHORITY, EXHIBIT, REQUEST, ANALYSIS, OTHER)
- `title` (str)
- `description` (text, nullable)
- `date_created` (timestamp)
- `date_modified` (timestamp)
- `uploaded_by` (UUID)
- `is_deleted` (bool, soft delete)

### `DocumentVersion`
- `id` (UUID, PK)
- `document_id` (UUID, FK)
- `version_number` (int)
- `gcs_path` (str)
- `checksum_sha256` (str)
- `size_bytes` (int)
- `created_by` (UUID)
- `created_at` (timestamp)
- `change_note` (text, nullable)

### `DocumentTag` + `DocumentDocumentTag` (optional v1.1)
Deferred to keep MVP scope tight.

---

## 7. API Surface

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/vault/cases/{case_id}/documents` | List documents for a case |
| POST | `/api/v1/vault/cases/{case_id}/documents` | Create document record + get upload URL |
| PUT | `/api/v1/vault/documents/{document_id}` | Update metadata |
| DELETE | `/api/v1/vault/documents/{document_id}` | Soft delete |
| POST | `/api/v1/vault/documents/{document_id}/versions` | Upload new version |
| GET | `/api/v1/vault/documents/{document_id}/versions` | List versions |
| GET | `/api/v1/vault/documents/{document_id}/download` | Get signed download URL |
| POST | `/api/v1/vault/cases/{case_id}/export-packet` | Export selected documents as evidence packet |

---

## 8. File Constraints

- **Max file size:** 50 MB per upload (configurable via `VAULT_MAX_FILE_SIZE_MB`).
- **Allowed MIME types:**
  - `application/pdf`
  - `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
  - `text/plain`
  - `text/markdown`
  - `image/png`
  - `image/jpeg`
- **Naming:** Original filename preserved in metadata; GCS object name is `tenants/{tenant_id}/cases/{case_id}/documents/{document_id}/{version}.{ext}`.

---

## 9. Engineering Doctrines

- **ED-003:** Blobs are immutable; presentation/metadata can change.
- **ED-005:** Postgres metadata is authoritative; GCS path is derived from metadata.
- **ED-007:** Every upload and export creates an audit record via `AuditService`.

---

## 10. Implementation Sequence

1. Add `google-cloud-storage` dependency.
2. Create SQLAlchemy models (`Document`, `DocumentVersion`).
3. Add Alembic migration.
4. Implement `GCSStorageService` and `DocumentService`.
5. Implement FastAPI router.
6. Add unit/API tests.
7. Scaffold React `DocumentVault` page.
8. Add Playwright E2E test.
9. Update CI / Cloud Build if needed.

---

## 11. Open Questions

- GCS bucket name and service account key location? (To be set in `.env` / Cloud Run secrets.)
- Virus scanning: deferred; document `status` field reserved for `pending`, `clean`, `quarantined`.
- Multi-part upload for files > 50 MB: deferred to v1.1.

---

## 12. Signatures

| Role | Name | Date | Decision |
|------|------|------|----------|
| Project Owner | Isiah Howard | 2026-07-06 | Approved |
| External Reviewer | ChatGPT | 2026-07-06 | Approved |
| Implementer | Hermes Agent | 2026-07-06 | Approved |
