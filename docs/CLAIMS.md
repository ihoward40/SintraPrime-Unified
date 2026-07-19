# SintraPrime-Unified Claims → Evidence Map

**Purpose:** Every capability claim is paired with implementation authority, test path,
verification command, CI coverage, known limitations, and last-verified commit.

**Authoritative as of commit:** `10cad07f046b5675ed10a1fba1aa4a955636f739`
**Tree:** `66f59a5bf832e9f3ce3c484c64891fd543359abf`

> **Reconciliation note (Convergence Increment One):** This file was rewritten to remove
> stale source paths from a former package layout, remove a published live Stripe
> payment-intent identifier, drop unverified hardcoded test totals, and qualify
> overclaimed statuses. Test counts cited below are taken from the original claims and
> are **not independently re-collected**; the authoritative count is now emitted
> dynamically by CI (`scripts/ci/report_test_inventory.py`). Where a test path could not
> be confirmed on current main, it is marked UNKNOWN and the claim status is downgraded.
> The former top-level `src/` package layout and the old top-level `tests/` tree no
> longer exist on main; current packages live at the repository root.

---

## Required fields per claim
- **Implementation authority** — package that owns the capability
- **Verification command** — how to exercise it
- **CI coverage** — whether a CI lane exercises it
- **Known limitations** — honest constraints
- **Last verified commit** — `10cad07f…` unless noted
- **Status** — ✅ SUPPORTED / ⚠️ PARTIAL / ❌ ASPIRATIONAL

---

## Trust Law Capabilities

### Claim: "Trust law analysis across 19 U.S. jurisdictions"
- **Implementation authority:** `trust_law/`
- **Test files:** `trust_law/tests/` (original claim cited 247 in the original claims (retired layout))
- **Verification command:** `python -m pytest trust_law/tests/ -q` (old demo module import is stale)
- **CI coverage:** not in default `pytest` lane unless collected; UNKNOWN
- **Known limitations:** 19 jurisdictions only (CA, NY, TX, FL, IL, PA, OH, MI, NC, VA, AZ, CO, WA, OR, MA, MD, NJ, CT, DE); not all 50 states
- **Status:** ⚠️ PARTIAL (implementation present; exact test count unverified on current tree)

---

### Claim: "Generate legal motions using IRAC structure"
- **Implementation authority:** `legal_integrations/` (original referenced a retired legal-docs test location)
- **Test files:** UNKNOWN (cited 189 in the original claims)
- **Verification command:** UNKNOWN (API path unverified)
- **CI coverage:** UNKNOWN
- **Known limitations:** templates require attorney review
- **Status:** ⚠️ PARTIAL

---

## Financial Capabilities

### Claim: "Financial statements (simplified GAAP)"
- **Implementation authority:** `financial_mastery/`
- **Test files:** UNKNOWN (cited 156 in the original claims (retired layout))
- **Verification command:** `python -m pytest financial_mastery/ -q` (demo module path stale)
- **CI coverage:** UNKNOWN
- **Known limitations:** simplified GAAP rules, NOT full audit-grade; CPA review required
- **Status:** ⚠️ PARTIAL (self-qualified; not audit-grade)

### Claim: "Credit building roadmap"
- **Implementation authority:** `financial_mastery/`
- **Test files:** UNKNOWN (cited 134 in the original claims)
- **CI coverage:** UNKNOWN
- **Known limitations:** educational roadmap, not credit advice
- **Status:** ⚠️ PARTIAL

---

## Payment & Integration

### Claim: "Stripe payment integration (test mode)"
- **Implementation authority:** `backend/stripe-payments/` (NOTE: the former payment package under the legacy layout is MISSING; `legal_integrations/` also touches billing)
- **Test files:** UNKNOWN (cited 89 in the original claims (retired layout))
- **Verification command:** run against Stripe **test** keys only
- **CI coverage:** NOT in default lane (no payment CI verified)
- **Known limitations:** production enablement requires your own configured keys + compliance review
- **Public identifiers:** REMOVED in this reconciliation. No live payment-intent identifiers are published.
- **Status:** ⚠️ PARTIAL (test-mode integration present; production unverified; authority duplicated)

---

## Compliance & Audit

### Claim: "Immutable audit logs with RBAC"
- **Implementation authority:** `portal/models` + Mission Control event chain (`portal/services/mission_control_run_control_service.py`)
- **Test files:** UNKNOWN (cited 118 in the original claims; the legacy audit package is MISSING on main)
- **Verification command:** `python -m pytest portal/tests/test_mission_control_run_controls.py -q` (immutable hash-chained events proven in PG race lane)
- **CI coverage:** YES (postgresql-race lane proves immutability + hash chain)
- **Known limitations:** multiple event logs exist; unified audit authority pending convergence
- **Status:** ✅ SUPPORTED (Mission Control event chain); PARTIAL (legacy audit module path unverified)

---

## Document Generation

### Claim: "40+ professional legal document templates"
- **Implementation authority:** `legal_integrations/` (the former document-generation package and its retired test location are MISSING)
- **Test files:** UNKNOWN (cited 189 in the original claims)
- **Verification command:** UNKNOWN
- **CI coverage:** UNKNOWN
- **Known limitations:** templates require customization per jurisdiction
- **Status:** ⚠️ PARTIAL (module path being restored; not verified on current tree)

---

## Dashboard & Administration

### Claim: "Multi-tenant dashboard with case management"
- **Implementation authority:** `portal/` + `web/`
- **Test files:** UNKNOWN (cited 134 in the original claims in a retired layout)
- **Verification command:** `cd web && npm run build`
- **CI coverage:** web lint/type/build only (no behavior tests)
- **Known limitations:** demo credentials in old receipts must not be reused
- **Status:** ✅ SUPPORTED (frontend + backend present; no exec mutation)

---

## Summary (reconciled)

| Claim | Original cited tests | Status (reconciled) | Path verified on main |
|-------|---------------------|---------------------|-----------------------|
| Trust law (19 jurisdictions) | 247 | ⚠️ PARTIAL | `trust_law/` exists |
| Legal motion generation | 189 | ⚠️ PARTIAL | `legal_integrations/` exists |
| Financial statements | 156 | ⚠️ PARTIAL | `financial_mastery/` exists |
| Payment integration | 89 | ⚠️ PARTIAL | `backend/stripe-payments/` exists |
| Audit logs | 118 | ✅ SUPPORTED (MC) | Mission Control proven |
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
5. Set status: ✅ SUPPORTED / ⚠️ PARTIAL / ❌ ASPIRATIONAL.
6. Update README only after tests pass and `scripts/ci/validate_repository_claims.py` is green.

**Rule:** No claim in README without corresponding test file and entry in this document.
