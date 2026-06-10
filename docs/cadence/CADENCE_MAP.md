# Cadence Map

> Defined cadences for SintraPrime operations.

## Overview

Cadences are recurring operational rhythms that keep the SintraPrime system healthy, the work product current, and the records accurate. Each cadence has a defined trigger, a set of actions, an owner, and a verification step.

---

## Cadences

### 1. Daily Inbox Triage

| Field | Value |
|---|---|
| **Trigger** | Every day at 09:00 local time |
| **Actions** | 1. Check all monitored inboxes (email, Slack, portal submissions) |
| | 2. Categorize each item: urgent / action-required / FYI / spam |
| | 3. Create or update tasks in the task tracker |
| | 4. Flag items requiring escalation to the owner |
| **Owner** | Nova agent (automated triage); human review for urgent items |
| **Verification** | Receipt generated at `reports/cadence/daily-triage-<date>.md` with item count and category breakdown |

### 2. Weekly Credit Command Center Review

| Field | Value |
|---|---|
| **Trigger** | Every Monday at 10:00 local time |
| **Actions** | 1. Review all active credit report disputes and their status |
| | 2. Check for new credit report data (Experian, TransUnion, Equifax) |
| | 3. Update violation scorecards for each active case |
| | 4. Generate weekly progress summary |
| | 5. Flag any deadlines or response windows at risk |
| **Owner** | Howard agent (evidence-intake); human oversight |
| **Verification** | Updated scorecards exist; weekly summary written to `reports/cadence/credit-review-<date>.md` |

### 3. Weekly Social Media / Music Content Sprint

| Field | Value |
|---|---|
| **Trigger** | Every Wednesday at 14:00 local time |
| **Actions** | 1. Review social media analytics from the past week |
| | 2. Select and repurpose music content for social posts |
| | 3. Schedule posts for the upcoming week |
| | 4. Update content calendar and platform profile trackers |
| | 5. Log growth metrics |
| **Owner** | Sigma agent (content); human approval for publishing |
| **Verification** | Content calendar updated; posts scheduled; growth metrics logged in `social-media/analytics/` |

### 4. Weekly Repo Smoke Check

| Field | Value |
|---|---|
| **Trigger** | Every Friday at 16:00 local time |
| **Actions** | 1. Run `python scripts/smoke/repo_truth_check.py` |
| | 2. Run `python scripts/smoke/verify_aios_output.py` |
| | 3. Run `pytest` (if test suite exists and is stable) |
| | 4. Check for any uncommitted changes or stale branches |
| | 5. Generate weekly repo health report |
| **Owner** | Zero agent (system health); automated |
| **Verification** | Smoke check exit code 0; report written to `reports/cadence/repo-smoke-<date>.md` |

### 5. Monthly Trust / Admin Records Audit

| Field | Value |
|---|---|
| **Trigger** | First day of each month at 09:00 local time |
| **Actions** | 1. Audit all trust-related documents (Howard Trust, IKE Solutions) |
| | 2. Verify evidence manifests are current for all active matters |
| | 3. Check that all admin records (invoices, receipts, filings) are filed |
| | 4. Identify any missing or stale records |
| | 5. Generate monthly audit report |
| **Owner** | Human (admin/legal); agent support for data gathering |
| **Verification** | Audit report written to `reports/cadence/monthly-audit-<date>.md` with checklist of all verified records |

### 6. Monthly Public Records / Evidence Archive Update

| Field | Value |
|---|---|
| **Trigger** | 15th of each month at 10:00 local time |
| **Actions** | 1. Check for new public records relevant to active matters |
| | 2. Download and archive any new evidence documents |
| | 3. Update evidence manifests with new entries |
| | 4. Verify chain of custody for all archived evidence |
| | 5. Generate evidence archive update report |
| **Owner** | Howard agent (evidence-intake); human verification |
| **Verification** | Evidence manifests updated; archive report written to `reports/cadence/evidence-archive-<date>.md` |

---

## Cadence Registry

All cadences are registered in `automations/cadence_registry.json`. The registry is the source of truth for scheduling, and any changes to cadence definitions must be reflected there first, then documented here.

## Verification

Each cadence run must produce a verification receipt as defined in `docs/workflows/SELF_VERIFICATION.md`. The receipt is written to `reports/cadence/<cadence-name>-<date>.md` and includes the status of all applicable checks.