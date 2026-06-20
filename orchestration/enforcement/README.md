# Enforcement Mode + Court Filing System (Draft-only)

This folder provides a **draft-only** courtroom bundle generator that turns your existing SintraPrime case fixtures into consistent, evidence-indexed “pressure machine” packages.

## What it generates (report-only)
For each case under `clients/<case_id>/` it writes:
- `artifacts/court/<case_id>/court_bundle_draft.md`
- `artifacts/court/<case_id>/court_bundle_draft.json`

## Receipts / audit
Every generated output is recorded via:
- `ledger/record_ledger_entry.py`

Receipts go to:
- `ledger/logs/LEDGER-*.json`

## Notion integration
If (and only if) the environment variable **`NOTION_RUNS_WEBHOOK`** is set, the runner POSTs a small receipt payload to the Make.com webhook (`court-filing-draft-center` scenario).

> Your current `.env` did not include `NOTION_RUNS_WEBHOOK`, so Notion logging is being skipped.

## Hermes automation
A cron job runs the wrapper:
- Hermes script: `run_enforcement_court_drafts.py`
- Repo runner: `orchestration/enforcement/court_filing_draft_center.py`

Cron schedule:
- `0 11 * * 1-5` (Mon–Fri at 11:00)

Cron job name:
- `Daily Enforcement & Court Filing Drafts`
