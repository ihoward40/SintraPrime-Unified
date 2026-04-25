# SintraPrime Unified — Client Portal

> **Secure multi-tenant document vault and collaboration platform for attorneys, financial advisors, and their clients.**

---

## Overview

The SintraPrime Client Portal replaces the back office of an entire law firm. It provides:

- **Multi-tenant architecture** — one deployment serves all firms via subdomain routing (`firm.sintraprime.ai`)
- **Secure document vault** — AES-256 at rest, TLS in transit, virus scanning, OCR, version history
- **End-to-end encrypted messaging** — real-time via WebSocket, no external email
- **Case management** — full lifecycle from intake to appeal with deadline tracking
- **Billing & invoicing** — time tracking, expenses, invoice generation, trust accounting (IOLTA-compliant)
- **7 RBAC roles** — from SUPER_ADMIN to CLIENT, with row-level security in PostgreSQL
- **Immutable audit log** — hash-chained, append-only, 7-year retention

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Client Browser                       │
│            (React SPA / Mobile App)                      │
└─────────────────────────┬───────────────────────────────┘
                          │ HTTPS / WSS
┌─────────────────────────▼───────────────────────────────┐
│                FastAPI Application                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │  Routers │  │ Services │  │ WebSocket│  │  Auth  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───┬────┘  │
└───────┼─────────────┼─────────────┼─────────────┼───────┘
        │             │             │             │
   ┌────▼───┐   ┌─────▼──┐   ┌────▼────┐  ┌────▼────┐
   │Postgres│   │ MinIO  │   │  Redis  │  │ Redis   │
   │(RLS)   │   │(S3)    │   │ (WS)    │  │(Sessions│
   └────────┘   └────────┘   └─────────┘  └─────────┘
```

**Stack:**
- **Backend:** FastAPI (Python 3.12) — fully async
- **Auth:** JWT (15min access) + refresh tokens (30d httpOnly cookie) + TOTP MFA
- **Database:** PostgreSQL 15 with Row-Level Security + pgvector ready
- **File Storage:** MinIO (S3-compatible)
- **Encryption:** AES-256-GCM at rest, TLS in transit
- **Cache / Sessions:** Redis
- **Real-time:** WebSocket with connection pooling
- **Logging:** structlog (JSON structured logs)

---

## Quick Start

### Prerequisites

```bash
# Required services
docker-compose up -d postgres redis minio
```

### Environment Variables

Copy `.env.example` and configure:

```bash
cp .env.example .env
```

Key variables:

```env
# Database
DATABASE_URL=postgresql+asyncpg://portal:secret@localhost:5432/portal_db

# Security
SECRET_KEY=your-256-bit-secret-key-here
JWT_ALGORITHM=HS256

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false

# Email (SMTP)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-key

# Environment
ENVIRONMENT=development
```

### Install & Run

```bash
cd /path/to/portal

# Install dependencies
pip install -r requirements.txt

# Run database migrations
psql $DATABASE_URL < migrations/portal_schema.sql

# Start the application
uvicorn portal.main:app --host 0.0.0.0 --port 8000 --reload
```

### API Documentation

Once running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## RBAC Roles

| Role | Description | Key Permissions |
|------|-------------|-----------------|
| `SUPER_ADMIN` | Full system access | Everything |
| `FIRM_ADMIN` | Manage their firm | Users, clients, cases, billing, settings |
| `ATTORNEY` | Full case/document access | Cases, docs, messages, billing read |
| `PARALEGAL` | Limited case access | Cases read/update, doc upload |
| `CLIENT` | Own data only | Own cases/docs/invoices, messaging |
| `ACCOUNTANT` | Financial data | Billing full access, financial docs |
| `VIEWER` | Read-only | Assigned documents only |

Row-level security is enforced at the PostgreSQL level via `tenant_id` policies. Clients are additionally filtered to only see records linked to their `client_id`.

---

## API Reference

### Authentication

```
POST /auth/login              — Email + password login
POST /auth/refresh            — Refresh access token (httpOnly cookie)
POST /auth/logout             — Revoke session
POST /auth/mfa/enable         — Generate TOTP secret + QR code
POST /auth/mfa/verify         — Verify TOTP code + activate MFA
POST /auth/mfa/backup         — Use backup code
```

### Clients

```
GET    /clients               — List clients (tenant-scoped)
POST   /clients               — Create client
GET    /clients/{id}          — Get client
PUT    /clients/{id}          — Update client
DELETE /clients/{id}          — Soft delete client
```

### Cases

```
GET    /cases                 — List cases
POST   /cases                 — Create case
GET    /cases/{id}            — Get case detail
PUT    /cases/{id}            — Update case
DELETE /cases/{id}            — Close/archive case
GET    /cases/{id}/deadlines  — List deadlines
POST   /cases/{id}/deadlines  — Create deadline
GET    /cases/conflict-check  — Check party conflict
GET    /cases/deadlines/upcoming — Upcoming deadlines (30 days)
```

### Documents

```
POST   /documents/upload             — Upload document
GET    /documents                    — List documents
GET    /documents/{id}               — Get document metadata
GET    /documents/{id}/download      — Download (presigned URL)
POST   /documents/{id}/share         — Create share link
GET    /documents/{id}/versions      — Version history
POST   /documents/{id}/versions      — Upload new version
GET    /documents/search             — Full-text search
GET    /documents/share/{token}      — Access shared document (public)
DELETE /documents/{id}               — Soft delete
```

### Messaging

```
GET    /messages/threads             — List threads
POST   /messages/threads             — Create thread
GET    /messages/threads/{id}        — Get thread + messages
POST   /messages/threads/{id}/send   — Send message
PUT    /messages/threads/{id}/read   — Mark as read
```

### Billing

```
GET    /billing/time-entries         — List time entries
POST   /billing/time-entries         — Create time entry
POST   /billing/time-entries/timer/start — Start timer
POST   /billing/time-entries/timer/stop  — Stop timer
GET    /billing/invoices             — List invoices
POST   /billing/invoices             — Generate invoice
GET    /billing/invoices/{id}        — Get invoice
PUT    /billing/invoices/{id}        — Update invoice
GET    /billing/invoices/{id}/pdf    — Download invoice PDF
POST   /billing/payments             — Record payment
GET    /billing/trust                — Trust account ledger
POST   /billing/trust                — Record trust transaction
GET    /billing/reports/monthly      — Monthly report
```

### Notifications

```
GET    /notifications                — List notifications
PUT    /notifications/{id}/read      — Mark as read
PUT    /notifications/read-all       — Mark all read
```

### WebSocket

```
WS     /ws                          — Authenticated real-time events
```

**WebSocket events emitted:**
- `notification` — new notification
- `case_update` — case status change
- `document_event` — document uploaded/shared
- `message` — new secure message
- `typing` — typing indicator in thread

---

## Security

### Token Security
- Access tokens expire in **15 minutes**
- Refresh tokens expire in **30 days**, stored in httpOnly cookies (not accessible via JavaScript)
- Refresh token rotation on use
- Session revocation on logout

### Rate Limiting
- Auth endpoints: **10 requests/minute per IP**
- All other endpoints: **100 requests/minute per user**
- Exceeding limit returns `429 Too Many Requests` with `Retry-After` header

### MFA
- TOTP (RFC 6238) — compatible with Google Authenticator, Authy, 1Password
- 8 single-use backup codes generated on enable
- Required for all firm staff when `mfa_required=true` on tenant

### File Security
- Files scanned for viruses (ClamAV) before storage
- Allowlisted MIME types only (no `.exe`, `.bat`, `.sh`, etc.)
- AES-256-GCM encryption with per-file IV
- Secure share links: token, expiry, password, download limit, view-only

### SQL Injection Protection
- SQLAlchemy ORM only — no raw SQL in application code (except migrations)
- PostgreSQL prepared statements

### Audit Trail
- Every authenticated action logged
- Hash-chained entries (tamper-evident)
- PostgreSQL RLS: audit_logs is append-only, no UPDATE/DELETE
- 7-year retention policy (legal compliance)

---

## Database Schema

The schema is in `migrations/portal_schema.sql`. Key design decisions:

- **UUID v4 primary keys** — no sequential IDs that could be enumerated
- **Soft deletes** — `deleted_at TIMESTAMPTZ` column, no hard deletes
- **Row-Level Security** — PostgreSQL RLS policies per tenant
- **Audit triggers** — auto-log INSERT/UPDATE/DELETE on sensitive tables
- **FTS indexes** — `tsvector` columns with GIN indexes for fast full-text search
- **Trigram indexes** — `pg_trgm` for fuzzy name matching

### Key Tables

| Table | Description |
|-------|-------------|
| `tenants` | Firms / organizations |
| `users` | All users (staff + clients) |
| `clients` | Client profiles |
| `matters` | Client engagements |
| `cases` | Individual cases/matters |
| `case_deadlines` | Deadlines with reminder config |
| `documents` | Document vault (metadata) |
| `document_versions` | Full version history |
| `document_shares` | Secure share links |
| `message_threads` | Encrypted message threads |
| `messages` | Individual messages |
| `time_entries` | Billable time |
| `expenses` | Billable expenses |
| `invoices` | Generated invoices |
| `payments` | Recorded payments |
| `trust_accounts` | IOLTA trust transactions |
| `notifications` | In-app notification center |
| `audit_logs` | Immutable audit chain |

---

## Running Tests

```bash
pip install pytest pytest-asyncio httpx

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_auth.py -v

# Run with coverage
pytest tests/ --cov=portal --cov-report=html
```

### Test Coverage Areas
- `test_auth.py` — Login, refresh, MFA, token validation, rate limiting
- `test_rbac.py` — Role boundaries, tenant isolation, permission checks
- `test_documents.py` — Upload, download, versioning, share links, search
- `test_cases.py` — CRUD, stage transitions, deadlines, conflict check
- `test_billing.py` — Time entries, invoice math, payments, trust accounting

---

## Project Structure

```
portal/
├── main.py                    # FastAPI app factory, middleware, WebSocket endpoint
├── config.py                  # Pydantic-settings config
├── database.py                # SQLAlchemy async engine
├── auth/                      # JWT, RBAC, MFA, sessions, password hashing
├── models/                    # SQLAlchemy ORM models
├── schemas/                   # Pydantic v2 request/response schemas
├── routers/                   # API route handlers
├── services/                  # Business logic layer
├── websocket/                 # WebSocket connection pool + handlers
├── middleware/                # Auth, rate limiting, audit, CORS
├── migrations/                # PostgreSQL schema SQL
└── tests/                     # pytest test suite
```

---

## Docker Deployment

```dockerfile
# Dockerfile (root of portal/)
FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
CMD ["uvicorn", "portal.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

```yaml
# docker-compose.yml
services:
  portal:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [postgres, redis, minio]

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: portal_db
      POSTGRES_USER: portal
      POSTGRES_PASSWORD: secret
    volumes: ["pgdata:/var/lib/postgresql/data"]

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass redispassword

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes: ["miniodata:/data"]
    ports: ["9000:9000", "9001:9001"]

volumes:
  pgdata:
  miniodata:
```

---

## Compliance

- **IOLTA** — Trust accounting with full ledger, overdraft prevention
- **HIPAA-ready** — Encryption at rest + in transit, audit log, access controls
- **SOC 2 Type II ready** — Audit logging, RBAC, MFA, rate limiting
- **GDPR** — Soft deletes, data export, right-to-erasure support
- **7-year audit retention** — Legal requirement for law firms

---

## License

Proprietary — SintraPrime-Unified. All rights reserved.
