# Agent Mode Engine

## AI Provider Integrations

### ClawdBot Integration

SintraPrime now includes a complete ClawdBot software integration package with governance-compliant installation, configuration, and monitoring.

**Quick Start:** [`clawdbot-integration/QUICK_START.md`](clawdbot-integration/QUICK_START.md)  
**Installation Guide:** [`INSTALL_CLAWDBOT.md`](INSTALL_CLAWDBOT.md)  
**Status Overview:** [`CLAWDBOT_STATUS.md`](CLAWDBOT_STATUS.md)

ClawdBot provides:
- Self-hosted AI assistant gateway
- Multi-platform chat integration (Telegram/WhatsApp/Discord/Slack/Signal/iMessage)
- Persistent memory and skills ecosystem
- Full governance compliance (isolation, least privilege, execute consent)

### Kimi K 2.5 (Moonshot AI)

Kimi K 2.5 from Moonshot AI is now integrated as an AI provider for reasoning and analysis tasks.

**Documentation:** [`agents/kimi/README.md`](agents/kimi/README.md)  
**Configuration:** [`config/kimi-config.json`](config/kimi-config.json)

Kimi K 2.5 provides:
- Advanced language model with up to 128K context window
- Chat completion and streaming APIs
- Alternative reasoning engine for DeepThink operations
- Full governance compliance with secure API key management

## Docker Deployment (Phase 3)

SintraPrime Phase 3 introduces a fully containerized deployment architecture with 5 core services orchestrated via Docker Compose.

**Quick Start:**
```bash
# Clone and configure
git clone https://github.com/ihoward40/SintraPrime.git
cd SintraPrime
cp .env.example .env.docker

# Edit .env.docker with your configuration
# Then start all services
docker-compose up -d

# Verify deployment
docker-compose ps
curl http://localhost:3000/health  # Airlock
curl http://localhost:8011/health  # Brain
curl http://localhost:8000/health  # FastAPI
curl http://localhost:3002/health  # WebApp
```

**Phase 3 Achievements:**
- ✅ 5/5 containers (MySQL, Airlock, Brain, FastAPI, WebApp)
- ✅ 100% health check pass rate
- ✅ Zero manual intervention deployment
- ✅ Production-ready baseline captured

**Documentation:**
- **Deployment Guide:** [`DOCKER_DEPLOYMENT.md`](DOCKER_DEPLOYMENT.md)
- **Best Practices:** [`docs/DOCKER_BEST_PRACTICES.md`](docs/DOCKER_BEST_PRACTICES.md)
- **Baseline Snapshot:** [`docs/snapshots/phase3-baseline/`](docs/snapshots/phase3-baseline/)

## Agent Mode (API-only)

Validator → Planner → Executor pipeline and receipt logging: [docs/agent-mode-executor-v1.md](docs/agent-mode-executor-v1.md)

## Governance

GOVERNANCE_RELEASE: SintraPrime_Mode_Governance_v1.1
SUPERSEDES: SintraPrime_Mode_Governance_v1.0

GOVERNANCE_RELEASES (CITEABLE)

- SintraPrime_Mode_Governance_v1.0 (baseline; frozen)
- SintraPrime_Mode_Governance_v1.1 (delta; active)


Change Control:
All governance changes are tracked via explicit release deltas.
See governance-history.v1.md for a chronological index.

### Governance (Authoritative)

- Governance documents: [docs/governance/index.md](docs/governance/index.md)
  - Governance release record: [docs/governance/releases/SintraPrime_Mode_Governance_v1.0.md](docs/governance/releases/SintraPrime_Mode_Governance_v1.0.md)
  - Governance release record: [docs/governance/releases/SintraPrime_Mode_Governance_v1.1.md](docs/governance/releases/SintraPrime_Mode_Governance_v1.1.md)

For Watch Mode auditability, see the **Watch Mode v1 Spec → Implementation Map**, which documents implemented features and intentional non-implementations:  
[docs/watch-mode-spec-implementation-map.v1.md](docs/watch-mode-spec-implementation-map.v1.md)

### Governance Index

All governance, verification, transparency, and integrity specifications are enumerated in a single index for auditability and ease of review:

- **Governance Index (v1)**  
  [`docs/governance-index.v1.md`](docs/governance-index.v1.md)

The index is descriptive and versioned. Absence of a document implies non-implementation by design.

External reviewers can follow a read-only verification path in the **Public Verifier How-To**: [`docs/public-verifier-how-to.v1.md`](docs/public-verifier-how-to.v1.md).

> **v1.0 is frozen for evidentiary use. No semantic changes permitted.**
>
> Freeze/fork procedure: [docs/governance/freeze-v1-fork-v2.md](docs/governance/freeze-v1-fork-v2.md)

- **Current Governance Checkpoint:**  
  Phase X Lock v1.4 — Read-Only Analysis Integration  
  [phaseX-lock-v1.4](https://github.com/ihoward40/SintraPrime/releases/tag/phaseX-lock-v1.4)

## Monitoring & Forensics (Make.com Automation)

SintraPrime includes a plug-and-play credit forensics system for Make.com, designed for non-coders to monitor runs, classify severity, and receive alerts.

- **Operator Guide**: [`automations/OPERATOR_GUIDE.md`](automations/OPERATOR_GUIDE.md) — Step-by-step instructions for extracting top 5 scenarios from Make.com usage UI
- **Environment Config**: [`automations/fieldmap.manifest.v1.json`](automations/fieldmap.manifest.v1.json) — Field mapping for Make.com scenarios
- **Make.com Scenarios**:
  - [`automations/make/1-runs-logger.md`](automations/make/1-runs-logger.md) — Monitors runs directory and logs new artifacts
  - [`automations/make/2-severity-classifier.md`](automations/make/2-severity-classifier.md) — Analyzes and classifies run severity
  - [`automations/make/3-slack-alerts.md`](automations/make/3-slack-alerts.md) — Sends high-severity alerts to Slack
  - [`automations/make/4-weekly-credit-review.md`](automations/make/4-weekly-credit-review.md) — Generates weekly usage summaries

For full documentation, see [`monitoring/README.md`](monitoring/README.md).

## Airlock Server (ManusLite Gateway)

SintraPrime Airlock is a production-ready HMAC-verified gateway that replaces paid Manus credits with owned infrastructure. It securely receives portal automation payloads, validates signatures and file integrity, and forwards sanitized receipts to Make.com workflows.

**Key Features:**
- HMAC-SHA256 signature verification (sender → Airlock → Make)
- SHA-256 file hash validation
- Temporary file storage for Make.com downloads
- Security guardrails (no_submit_pay flag, size limits)
- Health check endpoint for monitoring

**Quick Start:**
```bash
cd airlock_server
npm install
cp .env.example .env
# Configure environment variables
npm start
```

**Documentation:**
- **Server README**: [`airlock_server/README.md`](airlock_server/README.md) — Architecture and API reference
- **Deployment Guide**: [`docs/AIRLOCK_DEPLOYMENT.md`](docs/AIRLOCK_DEPLOYMENT.md) — Step-by-step Render.com deployment
- **Make.com Setup**: [`docs/MAKE_SCENARIO_SETUP.md`](docs/MAKE_SCENARIO_SETUP.md) — Configure Make.com scenario with HMAC verification
- **Test Script**: [`scripts/send_to_airlock.mjs`](scripts/send_to_airlock.mjs) — Send test PDFs through Airlock

## Windows path note

You may see the repo at both:

- `C:\Users\admin\agent-mode-engine`
- `C:\Users\admin\.sintraprime esm project\agent-mode-engine`

On this machine, the second path is a Windows junction that points to the first.
They are the same working tree.

Run commands from either path, but prefer `C:\Users\admin\agent-mode-engine` to avoid confusion.

## Speech tiers (stderr-only)

The CLI can emit optional "speech" lines to **stderr** for operator visibility.
Speech is derived-only (non-authoritative), does not change behavior, and does not affect the JSON emitted on stdout.

Enable speech with `SPEECH_TIERS` (comma-separated):

- `S3`: delta speech (notable changes)
- `S5`: autonomy/status speech
- `S6`: requalification + confidence feedback (threshold crossings)

Speech is also artifact-backed for auditability:

- `runs/speech-deltas/`
- `runs/speech-status/`
- `runs/speech-feedback/`

Example:

- `set SPEECH_TIERS=S3,S5,S6` (Windows `cmd`)

## Run Integrity Verification (CI)

To verify run artifact integrity in CI, use the built-in verifier.
Gate on the exit code only.

```bash
node verify-run.js runs --json > verify.json
```

GitHub Actions (one line, gate on exit code):

```yaml
- run: node verify-run.js runs --json > verify.json
```

Make.com (one line, Command module):

```bash
node verify-run.js runs --json > verify.json
```

- Exit code 0: all verified
- Exit code 1: verification failed or no verifiable runs present

The JSON output is informational and may be archived or parsed for reporting.
Verification is non-governing and does not initiate or block execution.

Additional one-page artifacts (for outsiders / regulators):

- System layers diagram: docs/system-layers-diagram.v1.md
- Audit integrity statement: docs/audit-integrity-statement.v1.md
- Audit integrity statements (by audience): docs/audit-integrity-statements.by-audience.v1.md
- System Layers Diagram (print-ready PDF): releases/diagrams/system-layers/v1.0.0/system-layers.pdf (SHA-256: releases/diagrams/system-layers/v1.0.0/system-layers.pdf.sha256)
- System Layers Diagram (vector SVG): releases/diagrams/system-layers/v1.0.0/system-layers.svg (SHA-256: releases/diagrams/system-layers/v1.0.0/system-layers.svg.sha256)
- System Layers Diagram (Court, Landscape PDF): releases/diagrams/system-layers-court-landscape/v1.0.0/system-layers.court.landscape.pdf (SHA-256: releases/diagrams/system-layers-court-landscape/v1.0.0/system-layers.court.landscape.pdf.sha256)

Watch Mode (outsider-facing):

- Watch Mode overview: docs/watch-mode-overview.v1.md
- Watch Mode platform & safety framing: docs/watch-mode-platform-safety.v1.md
- Watch Mode policy appendix (MD): docs/policy/watch-mode-policy-appendix.v1.md
- Watch Mode policy appendix (PDF): releases/policy-appendix/watch-mode/v1.0.2/SintraPrime_Policy_Appendix_Watch_Mode.pdf (SHA-256: releases/policy-appendix/watch-mode/v1.0.2/SintraPrime_Policy_Appendix_Watch_Mode.pdf.sha256)
- Watch Mode policy appendix (PDF, with diagram): releases/policy-appendix/watch-mode/v1.0.2/SintraPrime_Policy_Appendix_Watch_Mode_with_Diagram.pdf (SHA-256: releases/policy-appendix/watch-mode/v1.0.2/SintraPrime_Policy_Appendix_Watch_Mode_with_Diagram.pdf.sha256)

## DeepThink (Analysis Runner)

DeepThink is a deterministic, local-only **analysis runner** that produces auditable artifacts under `runs/`.
It has **no execution authority** and performs **no network** operations.

- Run: `npm run deepthink -- deepthink/fixtures/deepthink_request.example.json`
- Outputs: `runs/DEEPTHINK_<analysis_id>/` with `request.json`, `output.json`, `manifest.json` and `*.sha256` sidecars
- Verify hashes: recompute SHA-256 and compare to the `*.sha256` sidecars (see `scripts/verify.js` patterns)

## Operator Signing (Tier-1 / Tier-2)

SintraPrime separates **analysis**, **evidence**, and **authority** by design.

DeepThink analysis never signs artifacts.
Signing is an explicit **operator action**, performed after a run completes.

### Tier-1 (Ed25519 signature)

Tier-1 is derived when a run directory contains:

- `manifest.json`
- `manifest.json.sig`

To sign a completed DeepThink run:

```bash
SINTRAPRIME_SIGNING_KEY=/secure/path/secret.ed25519.key \
npm run sign:run -- --run runs/DEEPTHINK_<id> --backend software
```

This:

- signs only `manifest.json`
- emits `manifest.json.sig`
- does not modify inputs, outputs, or hashes

CI verifies signatures only if a `.sig` file is present.

### Tier-2 (TPM attestation, optional)

Tier-2 is derived only when attestation artifacts exist (e.g. `tpm_attestation.json` + `tpm_attestation.json.sig`).

TPM signing/attestation backends are intentionally not implemented in-repo.
CI never assumes TPM use; it only verifies artifacts if present.

### Dry-run mode

To validate a run without writing any files:

```bash
npm run sign:run -- --run runs/DEEPTHINK_<id> --backend software --dry-run
```

Governance note: tiers are derived from artifact presence, never asserted by configuration or flags.

## Operator Fast UI (Tier-14)

Local-only “thin skin” UI that reads `runs/` and forwards existing `/<command>` calls.

- Start: `npx tsx src/cli/run-operator-ui.ts "/operator-ui web serve --port 3000"`
- Open: <http://127.0.0.1:3000>
- Selftest: `npx tsx src/cli/run-operator-ui.ts "/operator-ui web selftest"`
