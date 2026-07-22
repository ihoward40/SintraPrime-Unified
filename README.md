<div align="center">

# ⚖️ SintraPrime-Unified
### The Legal & Financial Automation Platform — for Professional Review

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue?style=for-the-badge&logo=python)](https://python.org)
[![MIT License](https://img.shields.io/badge/License-MIT-gold?style=for-the-badge)](LICENSE)
[![Status: Integration-Ready](https://img.shields.io/badge/status-integration%2Dready-brightgreen?style=for-the-badge)](https://github.com/ihoward40/SintraPrime-Unified)

---

**A unified platform for automating legal documentation, financial analysis, and governance workflows — designed to augment licensed professionals, not replace them.**

*Generates first-draft legal templates, financial documents, and workflow automation. All outputs require attorney, CPA, or appropriate licensed professional review before use.*

> **Accuracy Notice:** This system augments professional expertise with AI-assisted documentation and analysis. See [Limitations](#limitations) and [Disclaimer](#disclaimer) below.

</div>

---

## 🚀 Proof in 10 Minutes

**Start here.** Clone, install the verified dependencies, and run the supported verification commands.

### Quick Start

```bash
# Clone repo
git clone https://github.com/ihoward40/SintraPrime-Unified.git
cd SintraPrime-Unified

# Setup (1 min)
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Verified commands

These commands define the currently supported local verification lane:

```bash
# Python supported test lane
python -m pytest --tb=short -q

# Web verification
cd web && npm install
cd web && npm run lint
cd web && npm run type-check
cd web && npm run build
```

> **Test counts are reported dynamically by CI** (see `scripts/ci/report_test_inventory.py`
> and `docs/ARCHITECTURE.md`). The repository does **not** assert a hardcoded total in
> this README; historically cited figures (e.g. "333", "4,681") were inconsistent and
> have been removed. The current authoritative count is emitted by the CI inventory
> step and recorded as a generated artifact.

### Docker image build verification

The `Docker Image Build Verification` workflow builds the canonical portal image from the root `Dockerfile` without runtime secrets, registry login, image push, service startup, or deployment. This verifies image construction only.

### Full-stack Docker boot

The repository contains `docker-compose.yml` for a local full-stack runtime (PostgreSQL, Redis, Elasticsearch, MinIO, Prometheus, Grafana, Nginx, API, Airlock, Twin display). Running this stack requires configured environment variables and external services. Runtime secrets such as `POSTGRES_PASSWORD`, `SECRET_KEY`, `JWT_SECRET`, MinIO credentials, and `TWIN_AUTH_TOKEN` intentionally remain fail-closed. Full-stack Compose startup is **not** part of the supported quick-start until it is independently verified on your environment. See `docs/DEPLOYMENT.md` for setup details.

### Known limitations / deferred work

- Scheduler arming tests (`tests/test_scheduler_core.py::TestArming`) are verified in the default CI lane following the APScheduler trigger adapter fix in PR #164.
- Optional integrations (Plaid, predictive analytics, advanced LLM providers) are documented in `docs/ci/DEPENDENCY_MATRIX.md` but are not installed or tested in the default supported CI lane.

**See [docs/CLAIMS.md](docs/CLAIMS.md) for detailed claims with test references.**

---

## 📊 What SintraPrime Can Do

SintraPrime combines capabilities not commonly found together in a single platform:

- 📋 **Generate legal document templates** — trust memos, motions, entity formation docs (requires attorney review)
- 💰 **Build financial statements** — P&L, balance sheets, cash flow analysis (requires CPA review)
- 🏛️ **Navigate legal jurisdictions** — analyze law across **19 US jurisdictions** currently supported (federal court system also covered; expansion to all 50 states is planned, not complete)
- 💳 **Automate payment workflows** — Stripe integration for document fees + service charges (test-mode verified; production enablement requires configuration)
- 🔐 **Audit-ready compliance** — receipt generation, role-based access, immutable logging
- 👥 **Multi-tenant administration** — dashboard for case management, team collaboration, client intake
- 🤖 **Multi-agent reasoning** — specialized agents for trust law, financial analysis, compliance
- 📄 **Professional document rendering** — PDF/DOCX/HTML output formatted to law-firm standards

**See [docs/CLAIMS.md](docs/CLAIMS.md) for detailed claims with test references.**

---

## ⚠️ What SintraPrime Is NOT

- ❌ **NOT a licensed attorney, CPA, or financial advisor**
- ❌ **NOT a substitute for professional consultation**
- ❌ **NOT legal/financial/tax advice** (outputs are templates for professional review)
- ❌ **NOT suitable for autonomous government/court filing** (humans-in-loop required)
- ❌ **NOT production-certified** — this is an **integration-ready foundation** for enterprises. Production deployment requires independent hardening, compliance certification, and customization.

---

## 📚 Architecture & Documentation

**For integrators and developers:**

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** — Canonical system design, authority matrix, security boundaries
- **[QUICK_START.md](docs/QUICK_START.md)** — Developer setup, running tests, local deployment
- **[CAPABILITY_INDEX.md](docs/CAPABILITY_INDEX.md)** — Honest capability index (not a marketing matrix)
- **[REPOSITORY_STATUS.md](docs/REPOSITORY_STATUS.md)** — Subsystem status taxonomy
- **[docs/CLAIMS.md](docs/CLAIMS.md)** — Every feature claim → test file → proof
- **[SECURITY.md](docs/SECURITY.md)** — Security architecture and current controls
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Code style, domain knowledge requirements, testing standards

**For governance:**

- **[docs/governance/MISSION_CONTROL_OBSERVATORY_AUTHORITY.md](docs/governance/MISSION_CONTROL_OBSERVATORY_AUTHORITY.md)** — Execution-authority boundary
- **[docs/governance/OPEN_PR_DISPOSITION.md](docs/governance/OPEN_PR_DISPOSITION.md)** — Open PR classification
- **[docs/DATABASE_AUTHORITY.md](docs/DATABASE_AUTHORITY.md)** — Schema/migration authority

---

## 🔧 Core Capabilities

> Status reflects the current `main` tree and CI, not marketing. See
> [CAPABILITY_INDEX.md](docs/CAPABILITY_INDEX.md) for the full, honest index with
> limitations and next-certification requirements.

| Capability | Status | Path |
|-----------|--------|------|
| Trust law analysis (19 jurisdictions) | FUNCTIONAL | [trust_law/](trust_law/) |
| Legal document templates | PARTIAL (module path being restored) | [legal_integrations/](legal_integrations/) |
| Financial statement generation | FUNCTIONAL (simplified GAAP) | [financial_mastery/](financial_mastery/) |
| Payment intake (Stripe) | DUPLICATED (unify required) | [backend/stripe-payments/](backend/stripe-payments/) |
| Multi-tenant dashboard | SUPPORTED | [portal/](portal/) |
| Audit logging & compliance | SUPPORTED | [portal/models](portal/models) + [Mission Control](portal/services) |
| Agent orchestration | EXPERIMENTAL | [agents/](agents/) |

**Test coverage:** reported dynamically by CI (see above). Do not trust hardcoded totals in old receipts.

---

## 🚀 Deployment

**Development:**

```bash
docker-compose -f docker-compose.dev.yml up
```

**Staging/Production:**

- **AWS:** [infrastructure/aws/](infrastructure/aws/) — Terraform (ECS Fargate + RDS)
- **Azure:** [infrastructure/azure/](infrastructure/azure/) — Bicep (App Service + SQL)
- **GCP:** [infrastructure/gcp/](infrastructure/gcp/) — Terraform (Cloud Run + Cloud SQL)

> Image construction is verified separately from deployment. Deployment definitions are
> **DOCUMENTED ONLY** — they are not verified by the image-build workflow. Independent
> deployment testing is required before any production claim. See [DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## 🛡️ Security & Compliance

- **Audit logging:** Immutable records of actions (user, timestamp, action, result) via Mission Control event chain.
- **RBAC:** Role-based access control with tenant isolation (`portal/auth/rbac.py`).
- **Encryption:** TLS in transit; AES-256 at rest is **configurable** via KMS — confirm your deployment enables it.
- **Compliance posture:** HIPAA / SOC 2 / PCI-DSS readiness is **NOT established**. The repository contains audit logging and RBAC scaffolding that *support* future certification, but no completed compliance certification exists. Do not represent the platform as meeting HIPAA, SOC 2, or PCI-DSS requirements.
- **Third-party:** No secrets in code; all keys via environment variables / secret stores.

See [SECURITY.md](docs/SECURITY.md) for the full security architecture and current controls.

---

## 📋 Limitations

**Current version (v1.0):**

- ✅ Works on Python 3.11+ (Linux, macOS, Windows)
- ✅ Stripe **test-mode** verified; production payment enablement requires your own configured keys and compliance review (no live production payment-intent identifiers are published here)
- ⚠️ Trust law limited to **19 US jurisdictions** (not all 50 yet)
- ⚠️ Document templates are starting points (require customization per jurisdiction)
- ⚠️ Financial analysis uses **simplified GAAP rules** (not full audit-grade; requires CPA review)
- ⚠️ Multi-agent parliament is **POC** (not production-scale voting on 1000+ documents)

**See [CAPABILITY_INDEX.md](docs/CAPABILITY_INDEX.md) for the full capability index and next-certification requirements.**

---

## 📄 License

MIT License — See [LICENSE](LICENSE) for full terms.

Built by the SintraPrime-Unified community. **Govern everything. Fear nothing.**

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Code style & testing requirements
- Domain knowledge guidelines (trust law, finance, compliance)
- Agent integration patterns
- PR process & review gates

**Before submitting a PR:** All claims must have corresponding tests. See [docs/CLAIMS.md](docs/CLAIMS.md) for the pattern. Documentation and claim changes must pass `scripts/ci/validate_repository_claims.py`.

---

<div align="center">

[![Star this repo](https://img.shields.io/github/stars/ihoward40/SintraPrime-Unified?style=social)](https://github.com/ihoward40/SintraPrime-Unified)
[![Follow](https://img.shields.io/github/followers/ihoward40?style=social)](https://github.com/ihoward40)

**For questions:** Open an issue or email sintraprime@ikesolutions.org

</div>

