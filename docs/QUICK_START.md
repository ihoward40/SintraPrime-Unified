# Quick Start

> Companion to [ARCHITECTURE.md](ARCHITECTURE.md). Authoritative as of commit `48e2caa759661cc75617cc752bcc26eaad666647` (tree `9ee6d193dd7f607cd59487df9ef26d46b9593803`).

## 1. Prerequisites
- Python 3.11+
- Node.js 18+ (for `web/`)
- PostgreSQL (optional; SQLite used by default test lane)
- `git`

## 2. Backend setup
```bash
git clone https://github.com/ihoward40/SintraPrime-Unified.git
cd SintraPrime-Unified
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Run the supported verification lane
```bash
# Python (default CI-equivalent)
python -m pytest --tb=short -q

# Security certification suites (PRs #214–#217)
python -m pytest portal/tests/test_auth_tenant_rbac_certification.py -q
python -m pytest portal/tests/test_audit_correlation_non_http_certification.py -q
python -m pytest portal/tests/test_http_correlation_ws_hardening_certification.py -q

# Web frontend
cd web && npm install
cd web && npm run lint
cd web && npm run type-check
cd web && npm run build
```

> Test counts are reported dynamically by CI (`scripts/ci/report_test_inventory.py`).
> Do not rely on hardcoded totals in old receipts.

## 4. Run the API (local)
```bash
# portal/ is the authoritative backend
uvicorn portal.main:app --reload
# Health: http://localhost:8000/health
```

## 5. Documentation validation
```bash
python scripts/ci/validate_repository_claims.py
```
This fails if README links are broken, `src/` paths appear, forbidden test totals
exist, or public payment identifiers are present.

## 6. Deployment
See [DEPLOYMENT.md](DEPLOYMENT.md). The Docker stack is **DOCUMENTED ONLY** and not
verified by CI.

## 7. Governance
- Architecture authority: [ARCHITECTURE.md](ARCHITECTURE.md)
- Capability index: [CAPABILITY_INDEX.md](CAPABILITY_INDEX.md)
- Claims/evidence: [CLAIMS.md](CLAIMS.md)
- Execution authority boundary: [docs/governance/MISSION_CONTROL_OBSERVATORY_AUTHORITY.md](docs/governance/MISSION_CONTROL_OBSERVATORY_AUTHORITY.md)