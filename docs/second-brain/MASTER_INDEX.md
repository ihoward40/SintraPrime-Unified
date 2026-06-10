# MASTER INDEX — SintraPrime-Unified Second Brain

> **Purpose:** Navigable knowledge map for the entire IKE Solutions / SintraPrime-Unified operating system. Every knowledge domain links to its relevant folders, docs, and agents. Use this as your starting point for any topic.

---

## 1. Trust Administration

**Owner:** Isiah Tarik Howard (Trustee)
**Trust:** ISIAH TARIK HOWARD TRUST

| Resource | Location | Description |
|----------|----------|-------------|
| Trust README | [`trust/README.md`](../trust/README.md) | Overview, record-keeping rules, folder structure |
| Beneficiary Registry | [`trust/beneficiaries/beneficiary_registry.md`](../trust/beneficiaries/beneficiary_registry.md) | Beneficiary tracking, advancement lanes |
| Asset Inventory | [`trust/assets/asset_inventory.md`](../trust/assets/asset_inventory.md) | Trust asset tracking (IP, claims, accounts) |
| Governance Checklist | [`trust/governance/trust_governance_checklist.md`](../trust/governance/trust_governance_checklist.md) | Annual review checklist |
| Trust Compliance API | [`portal/routers/trust_compliance.py`](../portal/routers/trust_compliance.py) | Portal trust compliance routes |
| Trust Compliance Tests | [`portal/tests/test_trust_compliance.py`](../portal/tests/test_trust_compliance.py) | Trust compliance test suite |

**Key Agents:** Howard (evidence intake), Nova (execution)

---

## 2. Consumer Law Education

**Focus:** FCRA, FDCPA, TCPA, UCC Article 9, CFPB complaint processes

| Resource | Location | Description |
|----------|----------|-------------|
| Consumer Law Matter — UACC | [`matters/consumer-law/C-0001-UACC/`](../matters/consumer-law/C-0001-UACC/) | Active UACC deficiency case |
| Readiness Scorecard | [`matters/consumer-law/C-0001-UACC/readiness_scorecard.md`](../matters/consumer-law/C-0001-UACC/readiness_scorecard.md) | Case readiness assessment |
| Master Timeline | [`matters/consumer-law/C-0001-UACC/master_timeline.md`](../matters/consumer-law/C-0001-UACC/master_timeline.md) | Case chronology |
| Evidence Manifest | [`matters/consumer-law/C-0001-UACC/evidence_manifest.md`](../matters/consumer-law/C-0001-UACC/evidence_manifest.md) | Evidence inventory |
| Credit Report Issue Map | [`matters/consumer-law/C-0001-UACC/credit_report_issue_map.md`](../matters/consumer-law/C-0001-UACC/credit_report_issue_map.md) | Map of credit report errors |
| Next Actions | [`matters/consumer-law/C-0001-UACC/next_actions.md`](../matters/consumer-law/C-0001-UACC/next_actions.md) | Immediate next steps |
| Evidence Needed | [`matters/consumer-law/C-0001-UACC/evidence_needed.md`](../matters/consumer-law/C-0001-UACC/evidence_needed.md) | Gap analysis |
| CFPB Case File | [`matters/consumer-law/C-0001-UACC/cfpb_case_file_needed.md`](../matters/consumer-law/C-0001-UACC/cfpb_case_file_needed.md) | CFPB complaint preparation |
| Client UACC Folder | [`clients/isiah-howard/uacc/`](../clients/isiah-howard/uacc/) | Full client case file |
| UACC Timeline | [`clients/isiah-howard/uacc/timeline.md`](../clients/isiah-howard/uacc/timeline.md) | Client-level timeline |
| Violation Scorecard | [`clients/isiah-howard/uacc/violation_scorecard.md`](../clients/isiah-howard/uacc/violation_scorecard.md) | Violation tracking |

**Templates:**
- [`templates/consumer-law/violation_scorecard_template.md`](../templates/consumer-law/violation_scorecard_template.md)
- [`templates/consumer-law/cfpb_complaint_prep_checklist.md`](../templates/consumer-law/cfpb_complaint_prep_checklist.md)
- [`templates/consumer-law/fcra_dispute_evidence_template.md`](../templates/consumer-law/fcra_dispute_evidence_template.md)

**Key Agents:** Howard intake/recovery agents, Nova

---

## 3. Credit Command Center

**Focus:** Credit report analysis, dispute drafting, FCRA compliance, bureau correspondence

| Resource | Location | Description |
|----------|----------|-------------|
| Credit Command Package | [`packages/credit_command_center/`](../packages/credit_command_center/) | Python package for credit analysis |
| Models | [`packages/credit_command_center/models.py`](../packages/credit_command_center/models.py) | Data models |
| Helpers | [`packages/credit_command_center/helpers.py`](../packages/credit_command_center/helpers.py) | Utility functions |
| Client Fixture | [`packages/credit_command_center/fixtures/client_0001.json`](../packages/credit_command_center/fixtures/client_0001.json) | Test fixture |
| Credit Tests | [`tests/test_credit_command_center.py`](../tests/test_credit_command_center.py) | Test suite |

**External Path:** `~/credit-command-center/` — credit reports, evidence, dispute drafts, tracker

**Credit Reports on File:**
- `clients/isiah-howard/uacc/credit-reports/Experian.pdf`
- `clients/isiah-howard/uacc/credit-reports/ExperianMay17.pdf`
- `clients/isiah-howard/uacc/credit-reports/Experian 5-6-26.pdf`
- `matters/consumer-law/C-0001-UACC/evidence/credit-reports/` (same reports, mirrored)

**Key Agent:** IKE Credit Command Center skill

---

## 4. UCC / Affidavit Workflows

**Focus:** UCC Article 9 compliance, affidavit drafting, evidence chain of custody

| Resource | Location | Description |
|----------|----------|-------------|
| Client UACC Folder | [`clients/isiah-howard/uacc/`](../clients/isiah-howard/uacc/) | Full UACC case file |
| Next Actions | [`clients/isiah-howard/uacc/next_actions.md`](../clients/isiah-howard/uacc/next_actions.md) | UACC-specific next actions |
| Money Docs Checklist | [`clients/isiah-howard/uacc/money_docs_checklist.md`](../clients/isiah-howard/uacc/money_docs_checklist.md) | Financial document checklist |
| Document Request | [`clients/isiah-howard/uacc/document_request_uacc.md`](../clients/isiah-howard/uacc/document_request_uacc.md) | Document request tracker |
| CFPB Evidence Checklist | [`clients/isiah-howard/uacc/cfpb_evidence_checklist.md`](../clients/isiah-howard/uacc/cfpb_evidence_checklist.md) | Evidence preparation |

**Evidence Intake Templates:** [`intake_templates/`](../intake_templates/) — JSON schemas for structured evidence intake (16+ templates covering UACC, Verizon, Chase, PayPal, Merrick, First Premier, and more)

---

## 5. Music / Social Media Growth Engine

**Focus:** Music catalog, content calendar, social platform growth, monetization

| Resource | Location | Description |
|----------|----------|-------------|
| Music Catalog | [`music-content/releases/music_catalog_tracker.md`](../music-content/releases/music_catalog_tracker.md) | Track music releases |
| Content Calendar | [`music-content/content-calendar/weekly_media_sprint.md`](../music-content/content-calendar/weekly_media_sprint.md) | Weekly media sprint plan |
| Music-to-Content Workflow | [`social-media/repurposing-workflows/music_to_content_workflow.md`](../social-media/repurposing-workflows/music_to_content_workflow.md) | Repurpose music into social content |
| Social Growth Tracker | [`social-media/analytics/social_growth_tracker.md`](../social-media/analytics/social_growth_tracker.md) | Growth metrics dashboard |
| Platform Profiles | [`social-media/platform-profiles/platform_profile_tracker.md`](../social-media/platform-profiles/platform_profile_tracker.md) | Cross-platform profile status |
| Platform Links Needed | [`social-media/platform-profiles/platform_links_needed.md`](../social-media/platform-profiles/platform_links_needed.md) | Missing links audit |
| Media Monetization Map | [`business-revenue/media-products/media_monetization_map.md`](../business-revenue/media-products/media_monetization_map.md) | Revenue model for media |
| 7-Day Growth Plan | [`reports/think-tank/social_music_growth_7_day_plan.md`](../reports/think-tank/social_music_growth_7_day_plan.md) | Strategic growth plan |

**Platforms:** TikTok, YouTube, Spotify (tracking planned/exploring)

---

## 6. Client Intake

**Focus:** New client onboarding, evidence intake, case creation

| Resource | Location | Description |
|----------|----------|-------------|
| Intake Templates (JSON) | [`intake_templates/`](../intake_templates/) | 16+ structured evidence intake templates |
| Template Usage Guide | [`intake_templates/README_HOW_TO_USE_TEMPLATES.txt`](../intake_templates/README_HOW_TO_USE_TEMPLATES.txt) | How to use intake templates |
| Intake AGENTS.md | [`intake_templates/AGENTS.md`](../intake_templates/AGENTS.md) | DOX contract for intake templates |
| Client 0001 Intake Report | [`clients/isiah-howard/client_0001_intake_report.md`](../clients/isiah-howard/client_0001_intake_report.md) | Sample client intake |
| Consumer Evidence Command Center | [`business-revenue/consumer-evidence-command-center/`](../business-revenue/consumer-evidence-command-center/) | Intake forms, scorecards, offer stack |
| Intake Form | [`business-revenue/consumer-evidence-command-center/intake_form.md`](../business-revenue/consumer-evidence-command-center/intake_form.md) | Client intake form |
| Sample Scorecard | [`business-revenue/consumer-evidence-command-center/sample_scorecard.md`](../business-revenue/consumer-evidence-command-center/sample_scorecard.md) | Sample credit scorecard |

**Evidence Templates:**
- [`intake_templates/generic_evidence_template.json`](../intake_templates/generic_evidence_template.json)
- [`intake_templates/batch_evidence_template.json`](../intake_templates/batch_evidence_template.json)
- [`intake_templates/expungement_evidence_template.json`](../intake_templates/expungement_evidence_template.json)
- *(See full list in [`intake_templates/`](../intake_templates/))*

**Key Agent:** Howard intake agent (`agents/howard_intake_agent.py`)

---

## 7. Public Records Remedy

**Focus:** OPRA requests, court filings, public records retrieval, civil rights / TCA

| Resource | Location | Description |
|----------|----------|-------------|
| TCA / Civil Rights Matter | [`matters/court-legal/isionnah-howard/`](../matters/court-legal/isionnah-howard/) | Isionnah Howard TCA case |
| Master Timeline | [`matters/court-legal/isionnah-howard/master_timeline.md`](../matters/court-legal/isionnah-howard/master_timeline.md) | Case chronology |
| Evidence Manifest | [`matters/court-legal/isionnah-howard/evidence_manifest.md`](../matters/court-legal/isionnah-howard/evidence_manifest.md) | Evidence inventory |
| Evidence Drafts | [`matters/court-legal/isionnah-howard/evidence/drafts/`](../matters/court-legal/isionnah-howard/evidence/drafts/) | Draft TCA notices, preservation demands |
| Issue List | [`matters/court-legal/isionnah-howard/issue_list.md`](../matters/court-legal/isionnah-howard/issue_list.md) | Legal issues tracker |
| Party List | [`matters/court-legal/isionnah-howard/party_list.md`](../matters/court-legal/isionnah-howard/party_list.md) | Parties to the matter |
| Next Actions | [`matters/court-legal/isionnah-howard/next_actions.md`](../matters/court-legal/isionnah-howard/next_actions.md) | Immediate legal next steps |
| Evidence Needed | [`matters/court-legal/isionnah-howard/evidence_needed.md`](../matters/court-legal/isionnah-howard/evidence_needed.md) | Evidence gap analysis |
| Deadline Risk Review | [`matters/court-legal/isionnah-howard/deadline_risk_review.md`](../matters/court-legal/isionnah-howard/deadline_risk_review.md) | Deadline tracking |

**Key Agent:** Howard recovery agent (`agents/howard_recovery_agent.py`)

---

## 8. Website / Business Operations

**Focus:** IKE Solutions website, business infrastructure, pricing, operations

| Resource | Location | Description |
|----------|----------|-------------|
| SintraPrime Web App | [`apps/SintraPrime/`](../apps/SintraPrime/) | TypeScript/Node.js web application |
| Consumer Evidence Command Center | [`business-revenue/consumer-evidence-command-center/`](../business-revenue/consumer-evidence-command-center/) | Revenue operations |
| README | [`business-revenue/consumer-evidence-command-center/README.md`](../business-revenue/consumer-evidence-command-center/README.md) | Command center overview |
| Offer Stack | [`business-revenue/consumer-evidence-command-center/offer_stack.md`](../business-revenue/consumer-evidence-command-center/offer_stack.md) | Pricing tiers |
| Landing Page Draft | [`business-revenue/consumer-evidence-command-center/landing_page_draft.md`](../business-revenue/consumer-evidence-command-center/landing_page_draft.md) | Marketing page draft |
| TikTok Script | [`business-revenue/consumer-evidence-command-center/tiktok_script_001.md`](../business-revenue/consumer-evidence-command-center/tiktok_script_001.md) | Marketing content |
| Media Monetization | [`business-revenue/media-products/media_monetization_map.md`](../business-revenue/media-products/media_monetization_map.md) | Revenue model |
| Lead Router | [`backend/lead-router/`](../backend/lead-router/) | Lead routing service |
| Stripe Payments | [`backend/stripe-payments/`](../backend/stripe-payments/) | Payment processing |

**Key Agents:** Nova (execution), Chat (user interface)

---

## 9. Evidence Command Center

**Focus:** Centralized evidence management, intake, classification, chain of custody

| Resource | Location | Description |
|----------|----------|-------------|
| Consumer Evidence Command Center | [`business-revenue/consumer-evidence-command-center/`](../business-revenue/consumer-evidence-command-center/) | Revenue-facing evidence operations |
| Consumer Law Evidence | [`matters/consumer-law/C-0001-UACC/evidence/`](../matters/consumer-law/C-0001-UACC/evidence/) | Consumer law evidence files |
| Court/Legal Evidence | [`matters/court-legal/isionnah-howard/evidence/`](../matters/court-legal/isionnah-howard/evidence/) | TCA/court evidence files |
| Intake Templates | [`intake_templates/`](../intake_templates/) | Structured evidence intake schemas |
| Template Usage Guide | [`intake_templates/README_HOW_TO_USE_TEMPLATES.txt`](../intake_templates/README_HOW_TO_USE_TEMPLATES.txt) | Intake instructions |
| Evidence Templates | [`templates/evidence/`](../templates/evidence/) | Exhibit index, intake checklist, correspondence log, master timeline |
| Evidence Intake Checklist | [`templates/evidence/evidence_intake_checklist.md`](../templates/evidence/evidence_intake_checklist.md) | Standard intake checklist |
| Exhibit Index Template | [`templates/evidence/exhibit_index_template.md`](../templates/evidence/exhibit_index_template.md) | Evidence organization |
| Correspondence Log | [`templates/evidence/correspondence_log_template.md`](../templates/evidence/correspondence_log_template.md) | Communication tracking |
| Master Timeline Template | [`templates/evidence/master_timeline_template.md`](../templates/evidence/master_timeline_template.md) | Chronology building |

**Key Agents:** Howard intake agent, Howard recovery agent

---

## Cross-Reference: Agent ↔ Domain

| Agent | Primary Domains | Key Files |
|-------|----------------|-----------|
| Nova | Trust Admin, Consumer Law, Business Ops | `agents/nova/` |
| Sigma | All (test gate) | Root `tests/`, CI workflows |
| Zero | All (code health) | Root-level monitoring |
| Chat | All (user interface) | `agents/chat/` |
| Howard (Intake) | Client Intake, Evidence Command Center | `agents/howard_intake_agent.py` |
| Howard (Recovery) | Public Records, Consumer Law | `agents/howard_recovery_agent.py` |
| Howard (Template) | Intake Templates | `agents/howard_template_agent.py` |

---

## Cross-Reference: External Systems

| System | Domain | Connection Status |
|--------|--------|-------------------|
| Gmail | Communication, case correspondence | Active (read) / Planned (draft) |
| Google Drive | Document storage, evidence vault | Active (read) / Write-gated |
| GitHub | Code, CI/CD, documentation | Active |
| Slack | Command center, approvals, audit log | Active |
| Stripe | Payment processing, billing | Active (test mode) |
| Calendar | Deadline tracking, scheduling | Active |
| TikTok | Content growth | Exploring |
| YouTube | Content growth | Exploring |
| Spotify | Music distribution | Exploring |
| Credit Bureaus | Credit monitoring exports | Active (read) |
| Court Systems | Public records, filings | Exploring |
| Notion | Documentation, planning | Planned |

---

*Last updated: 2026-06-10*
*See also: [CONTEXT_MAP.md](CONTEXT_MAP.md), [CONNECTIONS_MAP.md](CONNECTIONS_MAP.md), [AIOS_ROUTING_TREE.md](../AIOS_ROUTING_TREE.md)*