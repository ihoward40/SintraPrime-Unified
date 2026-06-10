# CONNECTIONS MAP — Live System Integrations

> **Purpose:** This document tracks every live, planned, or exploring connection between SintraPrime-Unified / IKE Solutions and external systems. For each integration: connection status, what it's used for, and access boundaries.

---

## Legend

| Icon | Status | Meaning |
|------|--------|---------|
| 🟢 | **Active** | Connected and in regular use |
| 🟡 | **Planned** | Configured or scoped but not yet active |
| 🔵 | **Exploring** | Under evaluation — not yet configured |

**Boundary Key:**
- **Read** — Can read/ingest data from this system
- **Write** — Can create/update data in this system
- **Draft** — Can create drafts but not send/publish (Tier 1)
- **Write-gated** — Write requires explicit Tier 2 approval
- **Read-only** — Strictly read-only (Tier 1 safe)

---

## 🟢 Active Connections

### 1. Gmail — Google Mail

| Field | Detail |
|-------|--------|
| **Status** | 🟢 **Active** |
| **Purpose** | Case correspondence intake, evidence collection, client communication tracking |
| **Boundaries** | **Read:** ✅ Active — read emails for evidence and case info |
| | **Write (Draft):** 🟡 Draft only — can compose emails but **never send** |
| | **Write (Send):** 🚫 **Tier 3 Hard Stop** — cannot send without explicit approval |
| **Key Paths** | Evidence extracted → filed in `matters/` or `clients/` |

### 2. Google Drive

| Field | Detail |
|-------|--------|
| **Status** | 🟢 **Active** |
| **Purpose** | Document storage, evidence vault, draft storage, case file repository |
| **Boundaries** | **Read:** ✅ Active — can read/ingest documents |
| | **Write:** 🚫 **Write-gated** — cannot create/modify files without Tier 2 approval |
| | **Delete:** 🚫 **Tier 3 Hard Stop** — no deletion |
| **Note** | Primary evidence repository; files are ingested into local repo for processing |

### 3. GitHub

| Field | Detail |
|-------|--------|
| **Status** | 🟢 **Active** |
| **Purpose** | Source code management, CI/CD, documentation, PR workflow |
| **Boundaries** | **Read:** ✅ Active — clone, pull, inspect |
| | **Write (Commit):** 🟡 Tier 2 approval required |
| | **Write (Push):** 🟡 Tier 2 approval required |
| | **Write (PR):** 🟡 Tier 2 approval required |
| | **Write (Merge):** 🟡 Tier 2 approval + all CI green |
| **CI Gates** | Sigma: ruff check, pytest, npm audit, coverage thresholds |
| **Key Files** | `.github/workflows/sigma-gate.yml`, `pyproject.toml`, `pytest.ini` |

### 4. Calendar (Google Calendar)

| Field | Detail |
|-------|--------|
| **Status** | 🟢 **Active** |
| **Purpose** | Deadline tracking, scheduling, reminder management |
| **Boundaries** | **Read:** ✅ Active — read calendar events and deadlines |
| | **Write:** 🟡 Tier 2 approval required for event creation/modification |
| **Key Deadlines** | TCA 90-day clock, OPRA 7-business-day clock, court dates |

### 5. Slack

| Field | Detail |
|-------|--------|
| **Status** | 🟢 **Active** |
| **Purpose** | Command center, approvals, audit logging, channel-based workflow orchestration |
| **Boundaries** | **Read:** ✅ Active — read all designated channels |
| | **Write (Messages):** ✅ Active — can post messages, summaries, reports |
| | **Write (Approvals):** 🟡 Can request approvals — approval authority is Isiah only |
| | **Delete/Edit:** 🚫 Tier 3 — no deletion without explicit approval |
| **Channels** | |
| | `#ike-command-center` — **Execution approvals** (one throne room) |
| | `#credit-command-center` — Credit evidence intake, dispute drafts |
| | `#sintraprime-dev` — PR workflow, CI status, DOX maintenance |
| | `#case-packets` — Civil rights/TCA packet, OPRA drafts |
| | `#revenue-sprint` — Offer drafts, content queue, revenue dashboard |
| | `#brand-visibility` — Brand audit, cleanup tasks |
| | `#hermes-audit-log` — Automated cron reports, receipts, summaries |

### 6. Stripe

| Field | Detail |
|-------|--------|
| **Status** | 🟢 **Active** (test mode) |
| **Purpose** | Payment processing, subscription management, billing |
| **Boundaries** | **Read:** ✅ Active — read payment data, subscription status |
| | **Write:** 🚫 **Write-gated** — Tier 2 required for any configuration changes |
| | **Production keys:** 🚫 **Tier 3 Hard Stop** — never access live production keys |
| **Key Files** | `backend/stripe-payments/` (client, webhooks, services, models, API routes) |
| **Tests** | `backend/stripe-payments/tests/test_stripe.py` |
| **Note** | Webhook behavior is a **hard safety boundary** — do not modify webhook handlers without explicit approval |

---

## 🟡 Planned Connections

### 7. Notion

| Field | Detail |
|-------|--------|
| **Status** | 🟡 **Planned** |
| **Purpose** | Documentation, project planning, knowledge base, content calendar |
| **Boundaries** | To be determined on activation |
| **Use Case** | Centralized wiki for IKE Solutions procedures, client onboarding docs, SOPs |

### 8. Website (IKE Solutions)

| Field | Detail |
|-------|--------|
| **Status** | 🟡 **Planned** |
| **Purpose** | Client acquisition, service listing, landing pages, content marketing |
| **Boundaries** | **Read:** ✅ Planned |
| | **Write (Content):** 🟡 Draft only — Tier 2 for publishing |
| **Key Assets** | Landing page draft: `business-revenue/consumer-evidence-command-center/landing_page_draft.md` |
| **Note** | Website content follows the 4-topic marketing framework |

---

## 🔵 Exploring Connections

### 9. TikTok

| Field | Detail |
|-------|--------|
| **Status** | 🔵 **Exploring** |
| **Purpose** | Content growth, brand awareness, client acquisition funnel |
| **Boundaries** | **Read:** 🔵 Under evaluation |
| | **Write (Post):** 🚫 Draft-only — Tier 3 for publishing |
| **Tracking** | `social-media/analytics/social_growth_tracker.md` |
| **Note** | Content pipeline: Topic → hook → body → CTA → Isiah review → [approval gate] → post |

### 10. YouTube

| Field | Detail |
|-------|--------|
| **Status** | 🔵 **Exploring** |
| **Purpose** | Long-form content, music video distribution, educational series |
| **Boundaries** | To be determined on activation |
| **Note** | Music-content pipeline connects here for video releases |

### 11. Spotify

| Field | Detail |
|-------|--------|
| **Status** | 🔵 **Exploring** |
| **Purpose** | Music distribution, artist profile, podcast potential |
| **Boundaries** | To be determined on activation |
| **Tracking** | `music-content/releases/music_catalog_tracker.md` |
| **Note** | Distribution strategy ties into music catalog and content calendar |

### 12. Credit Monitoring Exports

| Field | Detail |
|-------|--------|
| **Status** | 🟢 **Active** (import) / 🔵 **Exploring** (automated export) |
| **Purpose** | Import credit reports for analysis, dispute preparation, evidence tracking |
| **Boundaries** | **Read:** ✅ Active — ingest credit report PDFs |
| | **Export (Automated):** 🔵 Exploring — no automated export pipeline yet |
| **Key Files** | Credit reports in `clients/isiah-howard/uacc/credit-reports/` and `matters/consumer-law/C-0001-UACC/evidence/credit-reports/` |
| **Bureaus Tracked** | Experian (PDFs on file), Equifax/TransUnion (planned) |

### 13. Court / Public Records

| Field | Detail |
|-------|--------|
| **Status** | 🔵 **Exploring** |
| **Purpose** | Docket monitoring, case law research, public records retrieval (OPRA) |
| **Boundaries** | **Read:** 🔵 Under evaluation |
| | **Write (Filing):** 🚫 **Tier 3 Hard Stop** — cannot file with courts |
| **Key Deadlines** | TCA 90-day clock, OPRA 7-business-day clock |
| **Key Files** | `matters/court-legal/isionnah-howard/` — full case tracking |

---

## Connection Map Summary

| System | Status | Read | Write (Draft) | Write (Live) | Delete | Tier |
|--------|--------|------|---------------|--------------|--------|------|
| Gmail | 🟢 Active | ✅ | 🟡 Draft only | 🚫 Hard stop | 🚫 | T1/T3 |
| Google Drive | 🟢 Active | ✅ | 🟡 Write-gated | 🟡 Write-gated | 🚫 | T1/T2 |
| GitHub | 🟢 Active | ✅ | 🟡 Tier 2 | 🟡 Tier 2 | 🚫 | T1/T2 |
| Calendar | 🟢 Active | ✅ | 🟡 Tier 2 | 🟡 Tier 2 | 🚫 | T1/T2 |
| Slack | 🟢 Active | ✅ | ✅ Active | 🟡 Tier 2 | 🚫 | T1/T2/T3 |
| Stripe | 🟢 Active | ✅ | 🚫 Write-gated | 🚫 Write-gated | 🚫 | T1/T2/T3 |
| Notion | 🟡 Planned | 🔄 TBD | 🔄 TBD | 🔄 TBD | 🔄 TBD | TBD |
| Website | 🟡 Planned | ✅ Planned | 🟡 Draft only | 🟡 Tier 2 | 🚫 | T1/T2 |
| TikTok | 🔵 Exploring | 🔵 TBD | 🔵 Draft only | 🚫 Hard stop | 🚫 | T1/T3 |
| YouTube | 🔵 Exploring | 🔵 TBD | 🔵 TBD | 🔵 TBD | 🚫 | TBD |
| Spotify | 🔵 Exploring | 🔵 TBD | 🔵 TBD | 🔵 TBD | 🚫 | TBD |
| Credit Bureaus | 🟢/🔵 | ✅ Active (import) | 🔵 Exploring | 🚫 Hard stop | 🚫 | T1/T3 |
| Court Records | 🔵 Exploring | 🔵 TBD | 🔵 Draft only | 🚫 Hard stop | 🚫 | T1/T3 |

---

## Safety Rules — All Connections

1. **No third-party contact** — agents never contact creditors, courts, agencies, or external parties
2. **No spending** — agents cannot spend money or initiate payments
3. **No deletion** — data cannot be deleted without explicit approval
4. **Draft-first** — everything starts as a draft; nothing ships without Isiah's approval
5. **Receipts** — every external action produces an auditable receipt
6. **One throne room** — all approvals in `#ike-command-center`

---

*Last updated: 2026-06-10*
*See also: [MASTER_INDEX.md](MASTER_INDEX.md), [CONTEXT_MAP.md](CONTEXT_MAP.md), [AIOS_ROUTING_TREE.md](../AIOS_ROUTING_TREE.md)*