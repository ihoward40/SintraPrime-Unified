# SintraPrime-Unified API Reference

**Version:** 2.0.0  
**Base URL:** `https://api.sintraprime.com/v2`  
**Auth:** Bearer JWT (obtain from `/auth/token`)

---

## Quick Start

```bash
# 1. Get a token
TOKEN=$(curl -s -X POST https://api.sintraprime.com/v2/auth/token \
  -H "Content-Type: application/json" \
  -d '{"user_id":"your-id","password":"your-password"}' \
  | jq -r '.access_token')

# 2. Make an authenticated request
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.sintraprime.com/v2/api/trust"
```

---

## Authentication

All endpoints (except `/auth/token`, `/api/llm/health`) require a Bearer JWT.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/token` | POST | Obtain JWT token |
| `/auth/refresh` | POST | Refresh token |
| `/auth/revoke` | POST | Revoke token |

**Roles** (ascending privilege): `viewer` → `client` → `auditor` → `attorney` → `admin` → `system`

---

## Endpoints Summary

### 🏛️ Trust Law (`/api/trust`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/trust` | client+ | List trust documents |
| POST | `/api/trust` | client+ | Create trust document |
| GET | `/api/trust/{id}` | client+ | Get trust document |
| PUT | `/api/trust/{id}` | attorney+ | Update trust document |
| DELETE | `/api/trust/{id}` | admin | Delete trust document |
| POST | `/api/trust/{id}/analyze` | attorney+ | AI trust analysis |

**Create Trust Example:**
```json
POST /api/trust
{
  "trust_name": "Smith Family Living Trust",
  "grantor": {"name": "John Smith", "dob": "1960-05-15"},
  "trustee": {"name": "Jane Smith"},
  "beneficiaries": [{"name": "Alice Smith", "share_percent": 100}],
  "state": "CA",
  "trust_type": "revocable"
}
```

---

### ⚖️ Legal Intelligence (`/api/legal`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/legal` | viewer+ | Query legal intelligence |
| GET | `/api/legal/statutes` | viewer+ | Search statutes |

**Query Parameters:**
- `q` — Legal question (required, 3-2000 chars)
- `jurisdiction` — State code (e.g., `CA`, `NY`)
- `area_of_law` — `trusts`, `estates`, `tax`, `corporate`, `criminal`, `civil`, `family`, `bankruptcy`

---

### 📚 Case Law Search (`/api/cases`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/cases` | viewer+ | Search case law |
| GET | `/api/cases/{id}` | viewer+ | Get case details |
| GET | `/api/cases/{id}/similar` | viewer+ | Find similar cases |

**Rate Limit:** 30 requests/minute

**Search Example:**
```
GET /api/cases?q=trustee+fiduciary+duty&court=ca9&date_from=2020-01-01
```

---

### 📋 Court Dockets (`/api/docket`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/docket` | client+ | List monitored dockets |
| POST | `/api/docket/subscribe` | attorney+ | Subscribe to docket |

**Subscribe Example:**
```json
POST /api/docket/subscribe
{
  "court": "ca9",
  "case_number": "23-12345",
  "webhook_url": "https://your-app.com/webhooks/docket",
  "notification_events": ["filing", "order", "hearing_scheduled"]
}
```

---

### 🏦 Banking & Finance (`/api/banking`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/banking` | client+ | List linked accounts |
| POST | `/api/banking/link` | client+ | Initiate Plaid Link |
| POST | `/api/banking/sync` | client+ | Sync transactions |
| GET | `/api/banking/transactions` | client+ | Get transactions |

**Rate Limit:** 5 syncs per 5 minutes

---

### 🎙️ Voice Interface (`/api/voice`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/api/voice` | client+ | Submit voice query |
| POST | `/api/voice/tts` | client+ | Text to speech |

**Audio Formats:** WAV, MP3, OGG, FLAC (max 10MB)  
**Rate Limit:** 100 requests/minute

---

### 🏛️ Federal Agency Navigator (`/api/federal`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/federal` | viewer+ | Search agencies/regulations |
| GET | `/api/federal/forms` | viewer+ | Search federal forms |

**Supported Agencies:** IRS, SSA, DOL, HHS, SEC, FDIC, OCC, CFPB, FinCEN

---

### 🤖 ML Predictions (`/api/predict`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/api/predict` | attorney+ | Run prediction |
| POST | `/api/predict/batch` | attorney+ | Batch predictions (max 50) |

**Prediction Types:**
- `case_outcome` — Predict litigation outcome probability
- `settlement_value` — Estimate settlement range
- `filing_deadline` — Calculate applicable deadlines
- `tax_liability` — Estimate trust tax obligations
- `trust_validity` — Assess trust document validity

**Rate Limit:** 20 requests/minute

---

### ✍️ eSignature (`/api/esign`)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/esign` | client+ | List signature requests |
| POST | `/api/esign` | attorney+ | Create signature request |
| GET | `/api/esign/{id}` | client+ | Get request status |
| POST | `/api/esign/{id}/void` | attorney+ | Void request |

**Rate Limit:** 5 per minute  
**Document Format:** PDF only, max 50MB

---

### 🔍 RAG Legal Q&A (`/api/rag`) — New in v2

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/api/rag` | viewer+ | Ask a legal question |
| POST | `/api/rag/ingest` | admin | Ingest document |
| GET | `/api/rag/search` | viewer+ | Semantic search |

**Performance Targets:**
- Retrieval: <200ms
- Full response (with LLM): <5000ms

**Ask a Question Example:**
```json
POST /api/rag
{
  "question": "What are the fiduciary duties of a trustee under California law?",
  "jurisdiction": "CA",
  "area_of_law": "trusts",
  "max_sources": 5,
  "include_citations": true
}
```

**Response:**
```json
{
  "question": "What are the fiduciary duties...",
  "answer": "Under California Probate Code §16000 et seq., a trustee owes...",
  "sources": [
    {
      "title": "California Probate Code §16000",
      "document_type": "statute",
      "relevance_score": 0.97,
      "citation": "Cal. Prob. Code § 16000"
    }
  ],
  "confidence": 0.94,
  "retrieval_time_ms": 87,
  "generation_time_ms": 1243
}
```

---

### 🧠 Local LLM Interface (`/api/llm`) — New in v2

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/api/llm` | attorney+ | Query local LLM |
| GET | `/api/llm/models` | admin | List models |
| GET | `/api/llm/health` | public | Health check |

**Use Cases:**
- Air-gapped / offline legal analysis
- Confidential document review (data never leaves premises)
- High-volume processing without cloud API costs

**Query Example:**
```json
POST /api/llm
{
  "prompt": "Analyze this trust clause for ambiguity...",
  "system_prompt": "You are a trust law expert.",
  "max_tokens": 2000,
  "temperature": 0.1,
  "stream": false
}
```

---

## Error Codes

| HTTP Status | Error | Meaning |
|-------------|-------|---------|
| 400 | `validation_error` | Input validation failed |
| 401 | `unauthorized` | Missing or invalid token |
| 403 | `forbidden` | Insufficient role/permissions |
| 404 | `not_found` | Resource not found |
| 409 | `conflict` | Resource already exists |
| 422 | `unprocessable` | Valid format, invalid data |
| 429 | `rate_limited` | Too many requests |
| 500 | `internal_error` | Server error |
| 503 | `service_unavailable` | Dependency down |

**Error Response Format:**
```json
{
  "error": "validation_error",
  "message": "Query too long (maximum 2000 characters)",
  "code": 400,
  "request_id": "req_abc123xyz"
}
```

---

## Rate Limits

| Endpoint Group | Limit | Window |
|----------------|-------|--------|
| Auth | 10 | 1 minute |
| Trust (read) | 60 | 1 minute |
| Trust (write) | 10 | 1 minute |
| Case search | 30 | 1 minute |
| Predictions | 20 | 1 minute |
| Banking sync | 5 | 5 minutes |
| Voice | 100 | 1 minute |
| eSign create | 5 | 1 minute |
| RAG queries | 30 | 1 minute |
| LLM queries | 10 | 1 minute |

Rate limit headers are included in all responses:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1714176000
```

---

## SDKs & Tools

- **Python SDK:** `pip install sintraprime-sdk`
- **JavaScript SDK:** `npm install @sintraprime/sdk`
- **OpenAPI Spec:** `/docs/api/openapi.yaml`
- **Postman Collection:** Available in the developer portal
- **Interactive Docs:** `https://api.sintraprime.com/docs`

---

## Changelog

### v2.0.0 (2026-04-26)
- ✨ New: `/api/rag` — RAG-powered legal Q&A with citations
- ✨ New: `/api/llm` — Local LLM interface for air-gapped deployments
- 🔐 Security: JWT with role hierarchy enforcement
- ⚡ Performance: All endpoints meet SLA targets
- 📝 Docs: Full OpenAPI 3.1 spec

### v1.5.0 (2025-10-01)
- Added batch predictions endpoint
- Added docket subscription webhooks
- Improved Plaid integration error handling
