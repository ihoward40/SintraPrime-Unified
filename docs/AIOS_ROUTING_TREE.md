# AIOS Routing Tree — SintraPrime-Unified Mothership OS

> **Position:** SintraPrime-Unified is the mothership operating system for IKE Solutions. This document is the master router/navigation map for the entire AIOS. All agents, automations, and human operators use this tree to orient, navigate, and respect boundaries.

---

## Root Contract

**AGENTS.md** (repo root) is the root DOX contract. Every file, folder, and agent in this system is governed by the DOX framework defined there. Before editing any path:

1. Read the root `AGENTS.md`
2. Walk from repo root to the target path
3. Read every `AGENTS.md` found along the route
4. Use the nearest `AGENTS.md` as the local work contract

See: [`/AGENTS.md`](../AGENTS.md)

---

## Directory Map

### `apps/` — Application Frontends
| Path | Purpose |
|------|---------|
| `apps/SintraPrime/` | SintraPrime web app (TypeScript/Node.js) — client-facing dashboard |

### `agents/` — Autonomous Agent System
| Agent | Role | Approval Gate |
|-------|------|---------------|
| **Nova** | Real-world execution engine — dispatches legal/financial actions | Human-in-the-loop via `approval_gateway.py` |
| **Sigma** | Mandatory test-gating guardian — blocks merges below quality thresholds | CI gate |
| **Zero** | Self-healing maintenance agent — monitors code health, applies revertible patches | Autonomous (rollback-supported) |
| **Chat** | General-purpose chat interface | N/A |
| **Howard** | Domain-specific intake/recovery/template agents (consumer evidence workflows) | **Approval-gated** — evidence-intake only |

See: [`agents/AGENTS.md`](../agents/AGENTS.md)

### `skills/` — Hermes Agent Skills
Skills live at `~/.hermes/skills/` (not in this repo). Active skills include:
- `ike-safe-agent-lab` — Hard safety rules, approval gates, draft-only enforcement
- `github-pr-workflow` (hardened) — IKE-specific PR pipeline with DOX guardrails
- `ike-credit-command-center` — Evidence intake, dispute drafting, tracker updates
- `tca-preservation-packet` — Civil rights/TCA packet workflow *(pending)*
- `sintraprime-dox-maintainer` — AGENTS.md upkeep *(pending)*
- `revenue-sprint` — Offer building, content drafting *(pending)*
- `brand-visibility-cleanup` — Brand audit and cleanup *(pending)*

### `policies/` — Safety & Governance Policies
| Path | Purpose |
|------|---------|
| `docs/policies/PERMISSION_LAYER.md` | Permission layer definitions |
| `.safety-policy.yml` | Safety CLI configuration for vulnerability scanning |
| `.github/workflows/sigma-gate.yml` | CI gate workflow |

### `docs/` — Documentation Hub
| Subdirectory | Contents |
|-------------|----------|
| `docs/ci/` | CI policies, ruff baselines, bandit baselines, dependency matrix |
| `docs/api/` | OpenAPI spec, API index |
| `docs/second-brain/` | **Knowledge map** — MASTER_INDEX, CONTEXT_MAP, CONNECTIONS_MAP |
| `docs/workflows/` | Workflow documentation (e.g., SELF_VERIFICATION.md) |
| Root docs | CLAIMS.md, DEPLOYMENT.md, FEATURES.md, IKE_HERMES_OPERATING_MANUAL.md, etc. |

### `scripts/` — Automation Scripts
| Path | Purpose |
|------|---------|
| `scripts/smoke/repo_truth_check.py` | Smoke test — verifies repo integrity |

### `artifacts/` — Build & Compliance Artifacts
*(Planned — for compliance reports, audit receipts, signed documents)*

### `automations/` — Cron & Scheduled Jobs
Cron jobs defined in the IKE Hermes Operating Manual:
| Job | Schedule | Purpose |
|-----|----------|---------|
| Daily Repo Health | Mon-Fri 9 AM | Git status, open PRs, CI failures |
| Daily Credit Evidence Inbox | Mon-Fri 10 AM | Scan for new evidence, classify, update tracker |
| Weekly Revenue Sprint | Fri 4 PM | Completed assets, draft offers, next priorities |

**Rule:** All cron jobs are report-only. No sends, posts, merges, or modifications.

### `portal/` — Client Portal (FastAPI)
| Component | Purpose |
|-----------|---------|
| `portal/main.py` | FastAPI application entry point |
| `portal/routers/` | API route handlers (SSO, recovery, trust compliance) |
| `portal/services/` | Business logic (trust compliance service) |
| `portal/middleware/` | Session & timestamp middleware |
| `portal/tests/` | Portal-level tests |

See: [`portal/AGENTS.md`](../portal/AGENTS.md), [`portal/routers/AGENTS.md`](../portal/routers/AGENTS.md)

### `governance/` — Governance & Risk
| Path | Purpose |
|------|---------|
| `governance/risk_assessor.py` | Risk assessment engine |
| `governance/risk_types.py` | Risk type definitions |
| `governance/tests/` | Governance tests |

### `orchestration/` — Agent Orchestration
*(Planned — for multi-agent coordination, task routing, workflow orchestration)*

### Supporting Directories

| Directory | Purpose |
|-----------|---------|
| `backend/` | Backend services (Stripe payments, lead router) |
| `business-revenue/` | Revenue operations, consumer evidence command center, media products |
| `clients/` | Client-specific case files (e.g., `isiah-howard/uacc/`) |
| `intake_templates/` | Evidence intake JSON template library |
| `legal_intelligence/` | Legal analysis engines (credit dispute engine) |
| `matters/` | Active legal matters (consumer law, court/legal) |
| `music-content/` | Music catalog, content calendar, releases |
| `packages/` | Python packages (credit command center) |
| `reports/` | Execution reports, think tank outputs |
| `scheduler/` | Task scheduler system |
| `social-media/` | Platform profiles, repurposing workflows, analytics |
| `templates/` | Reusable templates (consumer law, evidence, beneficiary education) |
| `tests/` | Root-level test suite |
| `trust/` | Trust records, assets, beneficiaries, governance |

---

## Safety Boundaries

### 🚫 DO NOT TOUCH — Hard Boundaries

| Area | Reason |
|------|--------|
| **Webhook behavior** | Stripe webhooks (`backend/stripe-payments/webhooks/`) handle live payment events — modifying them can cause financial errors |
| **Billing logic** | `backend/stripe-payments/` contains subscription, pricing, and payment processing — changes require explicit approval |
| **Stripe production keys** | Never read, log, or transmit Stripe live keys. Test mode only in code. |
| **Gmail/Drive write paths** | Agents may draft emails but **never send**. May read Drive files but **never write** without explicit approval. |
| **Untracked data dirs** | `~/credit-command-center/`, `~/Isionnah-TCA-Packet/`, `~/.hermes/` — external data directories not under repo control |
| **Production deployments** | No changes to production deploys without explicit approval |
| **Secrets rotation** | Document the procedure only — never rotate secrets |
| **Third-party contact** | Never contact creditors, courts, agencies, or third parties |

### ⚠️ CAUTION — Approval Required (Tier 2)

| Action | Gate |
|--------|------|
| Committing code | Isiah: "commit it" |
| Pushing branches | Isiah: "push it" |
| Opening/merging PRs | Isiah approval + all CI green |
| Creating cron jobs | Isiah: "set it up" |
| Editing config/workflows | Isiah: "make the change" |

### ✅ SAFE — No Approval Needed (Tier 1)

| Action | Examples |
|--------|---------|
| Summarize | Condense documents, reports, logs |
| Classify | Tag evidence by bureau, account, type |
| Organize | Sort files, create folder structure |
| Draft | Write letters, reports, packets (draft only — never sent) |
| Inspect | Read files, check git status, review diffs |
| Read-only checks | npm audit, ruff check, pytest dry-run |
| Create local reports | Markdown summaries, tracker updates |
| Update internal trackers | Add rows to evidence tracker, update status fields |

---

## How to Verify Work

### 1. Run Smoke Tests
```bash
# Repo truth check — verifies file integrity and structure
python scripts/smoke/repo_truth_check.py
```

### 2. Check Receipts
Every action produces a receipt. Verify receipts exist in the relevant mission directory:
```bash
# Credit command center receipts
ls ~/credit-command-center/07-correspondence-log/receipts/

# TCA packet receipts
ls ~/Isionnah-TCA-Packet/04-mail-control/receipts/

# IKE solutions receipts
ls ~/ike-solutions/receipts/
```

Receipt format: `RECEIPT_[TYPE]_[YYYY-MM-DD]_[HHMM].md`

### 3. Run Test Suites
```bash
# Full test suite
pytest tests/ -v --cov=src --cov-report=term-missing

# Specific test areas
pytest tests/test_scheduler_core.py -v
pytest tests/test_nova_agent.py -v
pytest tests/test_sigma_agent.py -v
pytest tests/test_zero_agent.py -v
pytest tests/test_credit_command_center.py -v
pytest portal/tests/ -v
pytest governance/tests/ -v
```

### 4. CI Gate Verification
```bash
# Sigma gate checks
ruff check .
npm audit
pytest tests/ --cov --cov-fail-under=85
```

### 5. DOX Compliance Check
Before closing any task:
1. Re-check changed paths against the DOX chain
2. Update nearest owning AGENTS.md and any affected parents/children
3. Refresh every affected Child DOX Index
4. Remove stale or contradictory text
5. Run existing verification when relevant

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `pytest tests/ -v` | Run all root-level tests |
| `ruff check .` | Lint check |
| `python scripts/smoke/repo_truth_check.py` | Repo integrity smoke test |
| `git status` | Check current branch state |
| `git log --oneline -10` | Recent commit history |

---

*Last updated: 2026-06-10*
*Root contract: [`/AGENTS.md`](../AGENTS.md)*