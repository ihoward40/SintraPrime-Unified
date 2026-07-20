# SintraPrime-Unified Claims → Evidence Map

**Purpose:** Every capability claim is paired with implementation authority, test path,
verification command, CI coverage, known limitations, and last-verified commit.

**Authoritative as of commit:** `48e2caa759661cc75617cc752bcc26eaad666647`
**Tree:** `9ee6d193dd7f607cd59487df9ef26d46b9593803`

> **Reconciliation note (Convergence Increment Two):** Updated to reflect security
> certifications from PRs #214–#217. Three new certification claims added. Existing
> claims updated with current evidence. Test counts cited from original claims are
> not independently re-collected; the authoritative count is emitted dynamically by CI
> (`scripts/ci/report_test_inventory.py`). Where a test path could not be confirmed on
> current main, it is marked UNKNOWN and the claim status is downgraded.

> **Reconciliation note (Convergence Increment One, historical):** This file was
> originally rewritten to remove stale source paths from a former package layout, remove
> a published live Stripe payment-intent identifier, drop unverified hardcoded test totals,
> and qualify overclaimed statuses. The former top-level `src/` package layout and the
> old top-level `tests/` tree no longer exist on main; current packages live at the
> repository root.

---

## Required fields per claim
- **Implementation authority** — package that owns the capability
- **Verification command** — how to exercise it
- **CI coverage** — whether a CI lane exercises it
- **Known limitations** — honest constraints
- **Last verified commit** — `48e2caa7…` unless noted
- **Status** — ✅ SUPPORTED / ✅ CERTIFIED FOR RECORDED SCOPE / ⚠️ PARTIAL / ❌ ASPIRATIONAL

---

## Security Certification Claims (PRs #214–#217)

### Claim: "Authenticated actor and tenant binding with RBAC"
- **Implementation authority:** `portal/auth/rbac.py` + `portal/routers/{billing,blackstone,users}.py`
- **Test files:** `portal/tests/test_auth_tenant_rbac_certification.py`
- **Verification command:** `python -m pytest portal/tests/test_auth_tenant_rbac_certification.py -q`
- **CI coverage:** YES (`auth-tenant-rbac-certification` lane in `.github/workflows/ci.yml`)
- **Known limitations:** Refresh edge cases untested; session revocation not implemented; no token rotation; no logout invalidation; no concurrent session policy
- **Last verified commit:** `48e2caa7` (PR #214 merge `a93d2513`)
- **Status:** ✅ CERTIFIED FOR RECORDED SCOPE

---

### Claim: "Audit correlation and non-HTTP authorization"
- **Implementation authority:** `portal/auth/audit_envelope.py` + `portal/auth/correlation.py` + `portal/auth/websocket_auth.py`
- **Test files:** `portal/tests/test_audit_correlation_non_http_certification.py`
- **Verification command:** `python -m pytest portal/tests/test_audit_correlation_non_http_certification.py -q`
- **CI coverage:** YES (`audit-correlation-non-http-certification` lane)
- **Known limitations:** Multiple event logs still exist; unified audit schema pending; WebSocket authorization is process-local
- **Last verified commit:** `48e2caa7` (PR #215 merge `a0d9900b`)
- **Status:** ✅ CERTIFIED FOR RECORDED SCOPE

---

### Claim: "HTTP request correlation and WebSocket transport hardening"
- **Implementation authority:** `portal/middleware/correlation_middleware.py` + `portal/auth/ws_hardening.py`
- **Test files:** `portal/tests/test_http_correlation_ws_hardening_certification.py`
- **Verification command:** `python -m pytest portal/tests/test_http_correlation_ws_hardening_certification.py -q`
- **CI coverage:** YES (`http-correlation-ws-hardening-certification` lane)
- **Known limitations:** Process-local WebSocket enforcement; deprecated query-token support; incomplete request-ID coverage for exceptions outside application control; no distributed enforcement
- **Last verified commit:** `48e2caa7` (PR #217 merge `48e2caa7`)
- **Status:** ✅ CERTIFIED FOR RECORDED SCOPE

---

## Trust Law Capabilities

### Claim: "Trust law analysis across 19 U.S. jurisdictions"
- **Implementation authority:** `trust_law/`
- **Test files:** `trust_law/tests/` (original claim cited 247 in the original claims (retired layout))
- **Verification command:** `python -m pytest trust_law/tests/ -q` (old demo module import is stale)
- **CI coverage:** not in default `pytest` lane unless collected; UNKNOWN
- **Known limitations:** 19 jurisdictions only (CA, NY, TX, FL, IL, PA, OH, MI, NC, VA, AZ, CO, WA, OR, MA, MD, NJ, CT, DE); not all 50 states
- **Last verified commit:** `48e2caa7`
- **Status:** ⚠️ PARTIAL (implementation present; exact test count unverified on current tree)

---

### Claim: "Generate legal motions using IRAC structure"
- **Implementation authority:** `legal_integrations/` (original referenced a retired legal-docs test location)
- **Test files:** UNKNOWN (cited 189 in the original claims)
- **Verification command:** UNKNOWN (API path unverified)
- **CI coverage:** UNKNOWN
- **Known limitations:** templates require attorney review
- **Last verified commit:** `48e2caa7`
- **Status:** ⚠️ PARTIAL

---

## Financial Capabilities

### Claim: "Financial statements (simplified GAAP)"
- **Implementation authority:** `financial_mastery/`
- **Test files:** UNKNOWN (cited 156 in the original claims (retired layout))
- **Verification command:** `python -m pytest financial_mastery/ -q` (demo module path stale)
- **CI coverage:** UNKNOWN
- **Known limitations:** simplified GAAP rules, NOT full audit-grade; CPA review required
- **Last verified commit:** `48e2caa7`
- **Status:** ⚠️ PARTIAL (self-qualified; not audit-grade)

### Claim: "Credit building roadmap"
- **Implementation authority:** `financial_mastery/`
- **Test files:** UNKNOWN (cited 134 in the original claims)
- **CI coverage:** UNKNOWN
- **Known limitations:** educational roadmap, not credit advice
- **Last verified commit:** `48e2caa7`
- **Status:** ⚠️ PARTIAL

---

## Payment & Integration

### Claim: "Stripe payment integration (test mode)"
- **Implementation authority:** `backend/stripe-payments/` (NOTE: the former payment package under the legacy layout is MISSING; `legal_integrations/` also touches billing)
- **Test files:** UNKNOWN (cited 89 in the original claims (retired layout))
- **Verification command:** run against Stripe **test** keys only
- **CI coverage:** NOT in default lane (no payment CI verified)
- **Known limitations:** production enablement requires your own configured keys + compliance review; annual savings pricing mismatch (issue #185); payment authority duplicated
- **Public identifiers:** REMOVED in this reconciliation. No live payment-intent identifiers are published.
- **Last verified commit:** `48e2caa7`
- **Status:** ⚠️ PARTIAL (test-mode integration present; production unverified; authority duplicated)

---

## Compliance & Audit

### Claim: "Immutable audit logs with RBAC"
- **Implementation authority:** `portal/models` + Mission Control event chain (`portal/services/mission_control_run_control_service.py`) + `portal/auth/audit_envelope.py` (PR #215)
- **Test files:** `portal/tests/test_mission_control_run_controls.py` + `portal/tests/test_audit_correlation_non_http_certification.py`
- **Verification command:** `python -m pytest portal/tests/test_mission_control_run_controls.py -q` (immutable hash-chained events proven in PG race lane); `python -m pytest portal/tests/test_audit_correlation_non_http_certification.py -q` (audit envelope certification)
- **CI coverage:** YES (postgresql-race lane proves immutability + hash chain; `audit-correlation-non-http-certification` lane proves envelope correlation)
- **Known limitations:** multiple event logs exist; unified audit authority pending convergence
- **Last verified commit:** `48e2caa7`
- **Status:** ✅ CERTIFIED FOR RECORDED SCOPE (audit envelope correlation certified in PR #215; Mission Control hash chain proven in PG race lane)

---

## Document Generation

### Claim: "40+ professional legal document templates"
- **Implementation authority:** `legal_integrations/` (the former document-generation package and its retired test location are MISSING)
- **Test files:** UNKNOWN (cited 189 in the original claims)
- **Verification command:** UNKNOWN
- **CI coverage:** UNKNOWN
- **Known limitations:** templates require customization per jurisdiction
- **Last verified commit:** `48e2caa7`
- **Status:** ⚠️ PARTIAL (module path being restored; not verified on current tree)

---

## Dashboard & Administration

### Claim: "Multi-tenant dashboard with case management"
- **Implementation authority:** `portal/` + `web/`
- **Test files:** UNKNOWN (cited 134 in the original claims in a retired layout)
- **Verification command:** `cd web && npm run build`
- **CI coverage:** web lint/type/build only (no behavior tests)
- **Known limitations:** demo credentials in old receipts must not be reused
- **Last verified commit:** `48e2caa7`
- **Status:** ✅ SUPPORTED (frontend + backend present; no exec mutation)

---

## Summary (reconciled)

| Claim | Original cited tests | Status (reconciled) | Path verified on main |
|-------|---------------------|---------------------|-----------------------|
| Auth + tenant binding + RBAC | — | ✅ CERTIFIED FOR RECORDED SCOPE | `portal/auth/rbac.py` + cert test |
| Audit correlation + non-HTTP auth | — | ✅ CERTIFIED FOR RECORDED SCOPE | `portal/auth/audit_envelope.py` + cert test |
| HTTP correlation + WS hardening | — | ✅ CERTIFIED FOR RECORDED SCOPE | `portal/middleware/correlation_middleware.py` + cert test |
| Trust law (19 jurisdictions) | 247 | ⚠️ PARTIAL | `trust_law/` exists |
| Legal motion generation | 189 | ⚠️ PARTIAL | `legal_integrations/` exists |
| Financial statements | 156 | ⚠️ PARTIAL | `financial_mastery/` exists |
| Payment integration | 89 | ⚠️ PARTIAL | `backend/stripe-payments/` exists |
| Audit logs | 118 | ✅ CERTIFIED FOR RECORDED SCOPE | Mission Control + audit envelope proven |
| Dashboard | 134 | ✅ SUPPORTED | `portal/` + `web/` |
| Document templates | 189 | ⚠️ PARTIAL | `legal_integrations/` |

**Total:** the prior hardcoded total (about 1.1 thousand) is RETIRED. The authoritative
count is emitted dynamically by CI and must not be hardcoded. See
`scripts/ci/report_test_inventory.py`.

---

## How to Add a New Claim
1. Define "done" (specific, measurable).
2. Write tests (in the owning package's `tests/`).
3. Add verification command (run without secrets).
4. Link here with all required fields.
5. Set status: ✅ SUPPORTED / ✅ CERTIFIED FOR RECORDED SCOPE / ⚠️ PARTIAL / ❌ ASPIRATIONAL.
6. Update README only after tests pass and `scripts/ci/validate_repository_claims.py` is green.

**Rule:** No claim in README without corresponding test file and entry in this document.