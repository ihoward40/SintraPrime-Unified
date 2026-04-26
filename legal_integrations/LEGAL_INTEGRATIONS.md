# Legal Integrations — SintraPrime-Unified

Complete legal ecosystem integration layer providing connectors for Document Management Systems, Court E-Filing, Legal Research platforms, and Financial Data sources.

---

## Table of Contents

1. [Package Overview](#package-overview)
2. [Which DMS to Use for Different Firm Sizes](#which-dms-to-use)
3. [Court E-Filing Setup Guide](#court-e-filing-setup)
4. [Legal Research Setup](#legal-research-setup)
5. [Financial Data Setup](#financial-data-setup)
6. [API Endpoints](#api-endpoints)
7. [API Key Setup Guide](#api-key-setup-guide)
8. [Running Tests](#running-tests)
9. [Architecture](#architecture)

---

## Package Overview

```
legal_integrations/
├── __init__.py
├── dms_connectors.py        # Document Management System connectors (~500 lines)
├── court_efiling.py         # Court e-filing system connectors (~480 lines)
├── legal_research.py        # Legal research platform connectors (~420 lines)
├── financial_connectors.py  # Financial data connectors (~380 lines)
├── integrations_api.py      # FastAPI router (~280 lines)
├── LEGAL_INTEGRATIONS.md    # This file
└── tests/
    └── test_legal_integrations.py  # 80+ tests
```

---

## Which DMS to Use

### Solo Practitioners / Very Small Firms (1–3 attorneys)

**Recommended: Clio Manage or MyCase**

| Criterion | Clio | MyCase |
|-----------|------|--------|
| Price | ~$49–$109/mo | ~$39–$79/mo |
| Mobile app | ✅ Excellent | ✅ Good |
| Billing integration | ✅ Full | ✅ Full |
| Client portal | ✅ | ✅ |
| Document automation | Basic | Basic |

- **Clio** is the industry leader with the largest app ecosystem (Clio App Directory)
- **MyCase** is more affordable with a comparable feature set
- Both are cloud-native with REST APIs — easiest to integrate

### Small to Mid-Size Firms (4–50 attorneys)

**Recommended: Clio Manage or PracticePanther**

| Criterion | Clio | PracticePanther |
|-----------|------|-----------------|
| Price | ~$49–$109/user/mo | ~$49/user/mo |
| DMS depth | Moderate | Moderate |
| Automation | Clio Grow (marketing) | Zapier/built-in |
| LEDES billing | ✅ | ✅ |

- **PracticePanther** excels in automation and Zapier integrations
- **Clio** has a broader ecosystem and better litigation support

### Mid-Size Firms (50–200 attorneys)

**Recommended: NetDocuments or iManage Work**

| Criterion | NetDocuments | iManage Work |
|-----------|--------------|--------------|
| On-premises option | ❌ (cloud only) | ✅ (Work 10) |
| Email management | ✅ ndMail | ✅ iManage Email Management |
| Conflict checking | via partner | via partner |
| Security | SOC 2 Type II, ITAR | SOC 2 Type II |
| Microsoft 365 integration | ✅ Excellent | ✅ Excellent |

- **NetDocuments** is the go-to for cloud-first firms — no on-prem infrastructure
- **iManage Work** preferred by firms with on-premises requirements or complex governance

### Large Law Firms (200+ attorneys / BigLaw)

**Recommended: iManage Work or NetDocuments (enterprise tier)**

- Large firms generally use **iManage Work 10** (on-prem) or **iManage Cloud** (SaaS)
- **NetDocuments** enterprise is strong for global distributed teams
- Some BigLaw firms use **Worldox** for its desktop-native performance and low per-seat cost, especially in document-intensive practice areas

### Corporate Legal Departments

**Recommended: iManage Work (cloud) + matter management overlay**

- iManage integrates with most enterprise matter management platforms (TeamConnect, Mitratech, etc.)
- Consider **Clio for Clients** if the department also manages external counsel via Clio's portal

---

## Court E-Filing Setup

### Federal Courts — PACER

PACER (Public Access to Court Electronic Records) handles federal court filing.

1. **Create a PACER account** at [pacer.uscourts.gov](https://pacer.uscourts.gov/register.html)
2. Enable **CM/ECF** (Case Management/Electronic Case Files) access for your district
3. Set environment variables:
   ```bash
   export PACER_USERNAME="your_pacer_login"
   export PACER_PASSWORD="your_pacer_password"
   export PACER_CLIENT_CODE="optional_client_code"   # for billing
   ```
4. Note: PACER charges $0.10/page for document access

### State Courts — Tyler Technologies (Odyssey File & Serve)

Most U.S. state courts use Tyler's Odyssey platform.

1. Register at your state's e-filing portal (e.g., IL: [efile.illinoiscourts.gov](https://efile.illinoiscourts.gov))
2. Obtain a **Firm API Token** from Tyler's developer program
3. Set environment variables:
   ```bash
   export TYLER_CLIENT_TOKEN="your_client_token"
   export TYLER_SERVER_URL="https://il.tylertech.cloud"   # state-specific URL
   export TYLER_FIRM_ID="your_firm_id"
   ```

### California / Texas — File & Serve Xpress

1. Register at [fileandservexpress.com](https://www.fileandservexpress.com)
2. Obtain API access from their business team
3. Set environment variables:
   ```bash
   export FSX_USERNAME="your_username"
   export FSX_PASSWORD="your_password"
   export FSX_BASE_URL="https://efile.fileandservexpress.com"
   ```

### Illinois / Ohio — Odyssey eFile

1. Register through the state court portal
2. Obtain API key from Odyssey developer portal
3. Set environment variables:
   ```bash
   export ODYSSEY_API_KEY="your_api_key"
   export ODYSSEY_BASE_URL="https://il.tylertech.cloud"
   export ODYSSEY_JURISDICTION="IL"
   ```

### Filing Fee Reference (Federal)

| Filing Type | Base Fee |
|-------------|----------|
| Civil complaint | $402.00 |
| Appeal | $505.00 |
| Bankruptcy petition (Ch. 7) | $338.00 |
| Bankruptcy petition (Ch. 11) | $1,738.00 |
| Motions | $0.00 (usually) |

---

## Legal Research Setup

### Westlaw Edge

1. Subscribe via [Thomson Reuters](https://legal.thomsonreuters.com/en/products/westlaw)
2. Request API access through your account manager
3. Set environment variables:
   ```bash
   export WESTLAW_CLIENT_ID="your_client_id"
   export WESTLAW_CLIENT_SECRET="your_client_secret"
   ```

### LexisNexis

1. Subscribe via [LexisNexis](https://www.lexisnexis.com/en-us/products/lexis-plus.page)
2. Request API credentials from your LexisNexis sales rep
3. Set environment variables:
   ```bash
   export LEXISNEXIS_CLIENT_ID="your_client_id"
   export LEXISNEXIS_CLIENT_SECRET="your_client_secret"
   ```

### Fastcase (Free for Bar Members)

1. Most state bar associations provide free Fastcase access to members
2. Request API key at [fastcase.com/developer](https://fastcase.com)
3. Set environment variables:
   ```bash
   export FASTCASE_API_KEY="your_api_key"
   ```

### CourtListener (Free / Open Source)

1. Register at [courtlistener.com](https://www.courtlistener.com)
2. Generate API token in account settings
3. Set environment variables:
   ```bash
   export COURTLISTENER_API_TOKEN="your_token"
   ```

### Google Scholar Legal (No Setup Required)

Google Scholar connector is scraper-based and requires no API key.  
⚠️ Subject to rate limiting — set `request_delay=2.0` (default) to avoid blocks.

---

## Financial Data Setup

### Plaid (Asset Reports)

1. Create account at [plaid.com](https://dashboard.plaid.com/signup)
2. Get credentials from dashboard → Keys
3. Set environment variables:
   ```bash
   export PLAID_CLIENT_ID="your_client_id"
   export PLAID_SECRET="your_secret"
   export PLAID_ENV="production"   # or sandbox / development
   ```
4. Asset reports require **Production** access (separate approval)

### Yodlee

1. Register at [developer.yodlee.com](https://developer.yodlee.com)
2. Set environment variables:
   ```bash
   export YODLEE_CLIENT_ID="your_client_id"
   export YODLEE_SECRET="your_secret"
   export YODLEE_BASE_URL="https://production.api.yodlee.com/ysl"
   ```

### Finicity

1. Register at [finicity.com](https://www.finicity.com)
2. Set environment variables:
   ```bash
   export FINICITY_PARTNER_ID="your_partner_id"
   export FINICITY_PARTNER_SECRET="your_partner_secret"
   export FINICITY_APP_KEY="your_app_key"
   ```

### SEC EDGAR (No API Key Required)

EDGAR is a public API. Only set:
```bash
export EDGAR_USER_AGENT="Your Name your@email.com"   # required by SEC ToS
```

### Bloomberg Law

1. Subscribe via [Bloomberg Law](https://pro.bloomberglaw.com)
2. Contact your Bloomberg rep for API access
3. Set environment variable:
   ```bash
   export BLOOMBERG_LAW_API_KEY="your_api_key"
   ```

---

## API Endpoints

Mount the router in your FastAPI application:

```python
from fastapi import FastAPI
from legal_integrations.integrations_api import router

app = FastAPI()
app.include_router(router)
```

### Available Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/integrations/dms/connect` | Connect to a DMS platform |
| `POST` | `/integrations/dms/upload` | Upload document to DMS |
| `POST` | `/integrations/court/file` | E-file document(s) with a court |
| `GET` | `/integrations/court/status/{id}` | Check filing status |
| `POST` | `/integrations/research/search` | Search all research sources |
| `GET` | `/integrations/financial/assets` | Generate Plaid asset report |
| `GET` | `/integrations/financial/edgar/filings` | Search SEC EDGAR filings |
| `POST` | `/integrations/research/cite/validate` | Validate a legal citation |

### Example: Connect to Clio

```bash
curl -X POST http://localhost:8000/integrations/dms/connect \
  -H "Content-Type: application/json" \
  -d '{"platform": "clio", "options": {}}'
```

### Example: Search Legal Research

```bash
curl -X POST http://localhost:8000/integrations/research/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "negligence duty of care",
    "jurisdiction": "ca9",
    "sources": ["courtlistener", "fastcase"],
    "limit_per_source": 10
  }'
```

### Example: E-File a Document

```bash
curl -X POST http://localhost:8000/integrations/court/file \
  -F "system=pacer" \
  -F "case_number=21-cv-1234" \
  -F "court_id=nysd" \
  -F "filing_type=civil_motion" \
  -F "files=@motion_to_dismiss.pdf"
```

---

## API Key Setup Guide

### Security Best Practices

1. **Never commit credentials to source control** — use `.env` files or secrets managers
2. Use `python-dotenv` for local development:
   ```bash
   pip install python-dotenv
   ```
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```
3. In production, use a secrets manager:
   - **AWS**: Secrets Manager or SSM Parameter Store
   - **GCP**: Secret Manager
   - **Azure**: Key Vault
   - **HashiCorp**: Vault

### Recommended `.env` Template

```bash
# DMS Credentials
CLIO_CLIENT_ID=
CLIO_CLIENT_SECRET=
CLIO_REFRESH_TOKEN=

NETDOCUMENTS_CLIENT_ID=
NETDOCUMENTS_CLIENT_SECRET=
NETDOCUMENTS_CABINET_ID=

IMANAGE_CLIENT_ID=
IMANAGE_CLIENT_SECRET=
IMANAGE_SERVER_URL=
IMANAGE_CUSTOMER_ID=
IMANAGE_LIBRARY=

# E-Filing
PACER_USERNAME=
PACER_PASSWORD=
TYLER_CLIENT_TOKEN=
TYLER_SERVER_URL=
TYLER_FIRM_ID=
FSX_USERNAME=
FSX_PASSWORD=
ODYSSEY_API_KEY=
ODYSSEY_BASE_URL=
ODYSSEY_JURISDICTION=

# Legal Research
WESTLAW_CLIENT_ID=
WESTLAW_CLIENT_SECRET=
LEXISNEXIS_CLIENT_ID=
LEXISNEXIS_CLIENT_SECRET=
FASTCASE_API_KEY=
COURTLISTENER_API_TOKEN=

# Financial
PLAID_CLIENT_ID=
PLAID_SECRET=
PLAID_ENV=sandbox
EDGAR_USER_AGENT=SintraPrime research@yourfirm.com
BLOOMBERG_LAW_API_KEY=
```

---

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov requests fastapi httpx pydantic

# Run all tests with coverage
python -m pytest legal_integrations/tests/ -v --cov=legal_integrations --cov-report=term-missing

# Run a specific test class
python -m pytest legal_integrations/tests/ -v -k "TestClioConnector"

# Run with short output
python -m pytest legal_integrations/tests/ -q
```

All tests mock external APIs — **no real credentials are needed** to run the test suite.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              integrations_api.py (FastAPI)           │
│  /dms/connect  /dms/upload  /court/file             │
│  /court/status  /research/search  /financial/assets  │
└────────────────────────┬────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
 dms_connectors.py  court_efiling.py  legal_research.py
 ──────────────────  ────────────────  ────────────────
 NetDocuments        PACER             Westlaw Edge
 iManage Work        Tyler Tech        LexisNexis
 Worldox             File&Serve Xpress Fastcase
 Clio Manage         Odyssey eFile     Google Scholar
 MyCase                                CourtListener
 PracticePanther                       UnifiedSearch

         financial_connectors.py
         ───────────────────────
         Plaid (+ Asset Reports)
         Yodlee
         Finicity
         EDGAR (SEC)
         Bloomberg Law
         PACER Bankruptcy
```

Each connector:
- Loads credentials from **environment variables only**
- Uses **OAuth2 or API key auth** (never stored in code)
- Implements **retry logic** with exponential backoff
- Raises descriptive errors when APIs are unavailable
- Is independently testable with mocks
