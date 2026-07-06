# M3 Document Vault Endpoint — Deployment Receipt

**Commit:** `6569db8`  
**Branch:** `main`  
**Pushed:** 2026-07-06  
**Status:** ✅ Live on Cloud Run

---

## What Was Delivered

**POST /api/v1/documents/cases/{case_id}/export-packet**

Bridges the Document Vault to the Phase 1 Evidence Platform:

```
Document (mutable)
  ↓
EvidenceCollection
  ↓
EvidenceSnapshot (immutable — evidence_hash)
  ↓
EvidencePacket (mutable presentation — packet_hash)
  ↓
AuditRecord (immutable ledger)
```

### Files in commit `6569db8`
- `portal/schemas/document.py` — `DocumentExportRequest`, `DocumentExportResponse`
- `portal/routers/documents.py` — export-packet endpoint
- `web/src/pages/DocumentVault.tsx` — real API fetch + export button + result display
- `portal/services/document_export_service.py` — bridge service (from prior commit `b91b54b`)
- `portal/tests/test_document_export_service.py` — 4 integration tests
- `web/src/api/documents.ts` — typed API client

---

## Verification Results

| Check | Result | Evidence |
|-------|--------|----------|
| Live `/health` | ✅ HTTP 200, valid JSON | `{"status":"ok","service":"portal"}` |
| Targeted tests | ✅ 128/128 passed | Phase 1 (124) + Document Export (4) |
| Ruff lint | ✅ All checks passed | `ruff check portal/` |
| App import | ✅ Loads without error | `from portal.main import create_app` |

---

## Engineering Doctrine Compliance

- **ED-003:** Immutable evidence (`evidence_hash`) ≠ mutable presentation (`packet_hash`) — verified in export chain
- **ED-005:** Snapshot is the single source of truth for evidence content
- **ED-007:** Audit record creates immutable ledger entry for every export

---

## Next Steps

1. Add Playwright E2E test for the export-packet flow
2. Replace mock-document fallback in frontend once production auth/session flow is verified
3. Address the 133 Dependabot alerts (2 critical, 23 high)
4. Remediate AGENT_CONTRACT violations from prior direct-to-main commits
