# M3 Document Export API Tests — PR #152 Receipt

**Commit:** `d635048`  
**PR:** #152 — merged to `main`  
**Status:** ✅ Live on Cloud Run

---

## ⚠️ Critical Discovery: Router Was Registered in Code but Never Wired into the App

### Symptom
Commit `6569db8` added the M3 Document Vault endpoint and the `documents` FastAPI router, but the live service returned **HTTP 404** for:

```
POST /api/v1/documents/cases/{case_id}/export-packet
```

### Root Cause
`portal/main.py` never called `app.include_router(documents.router, ...)`. The router and endpoint existed in source control, but FastAPI did not mount them. As a result, the endpoint was **dead code** from the perspective of any HTTP client, including the deployed Cloud Run service.

### Fix (in this PR)
Added a single line to `create_app()`:

```python
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
```

### Verification That It Works
Post-merge live probe against Cloud Run (no auth):

```bash
curl -X POST https://sintraprime-unified-404665636267.us-central1.run.app/api/v1/documents/cases/11111111-1111-1111-1111-111111111111/export-packet \
  -H "Content-Type: application/json" \
  -d '{"document_ids": []}'
```

**Response:** `HTTP 401` with body `{"detail":"Authentication required"}`

The 401 proves the router is now mounted: the endpoint exists, reaches the `require_permissions(Permission.DOC_READ)` dependency, and correctly rejects unauthenticated requests. Before this PR the same request returned **HTTP 404**.

---

## What Was Delivered

### 1. Bug Fix: Register Documents Router
`portal/main.py` now mounts `documents.router` under `/api/v1/documents`.

### 2. API Integration Tests
File: `portal/tests/test_document_export_endpoint.py` (9 tests)

| Test | Purpose |
|------|---------|
| `test_export_packet_happy_path` | Full export returns snapshot_id, packet_hash, audit_id, evidence_hash |
| `test_export_packet_client_with_doc_read` | Client role with DOC_READ can export |
| `test_export_packet_missing_permission_returns_403` | Missing DOC_READ returns 403 |
| `test_export_packet_missing_document_returns_404` | Unknown document returns 404 |
| `test_export_packet_cross_tenant_document_not_accessible` | Cross-tenant documents are filtered out |
| `test_export_packet_no_auth_returns_401` | Missing Authorization returns 401 |
| `test_export_packet_multiple_documents` | Multiple docs produce single packet |
| `test_export_packet_response_contains_distinct_hashes` | ED-003: evidence_hash != packet_hash |
| `test_export_packet_invalid_payload_returns_422` | Empty document_ids triggers schema validation |

---

## Verification Results

| Check | Result |
|-------|--------|
| Targeted tests | ✅ 137/137 passed |
| Ruff lint | ✅ All checks passed |
| App loads | ✅ OK |
| Live `/health` | ✅ HTTP 200, valid JSON |
| Live export-packet (no auth) | ✅ HTTP 401 (endpoint mounted, auth enforced) |

---

## Doctrine Compliance

- **ED-003:** evidence_hash (immutable content) ≠ packet_hash (mutable presentation) — tested
- **ED-005:** Snapshot as single source of truth
- **ED-007:** Audit record created for every export

---

## Cloud Build

Build triggered by commit `d635048`. Monitor at:
`https://console.cloud.google.com/cloud-build/builds?project=ike-bot-automation`

---

## Next Steps

1. Confirm Cloud Build success for `d635048`
2. Continue Phase 2 Playwright E2E on branch `pr-153-playwright-e2e`
3. Triage Dependabot alerts (133 total, 2 critical, 23 high)
