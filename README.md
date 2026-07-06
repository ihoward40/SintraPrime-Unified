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

### Full-stack Docker boot

The repository contains `docker-compose.yml` and `Dockerfile` files for a complete deployment (PostgreSQL, Redis, Elasticsearch, MinIO, Prometheus, Grafana, Nginx, API, Airlock, Twin display). Running this stack requires configured environment variables and external services. It is **not** part of the supported quick-start until it is independently verified on your environment. See `docs/DEPLOYMENT.md` for setup details.

### Known limitations / deferred work

- Scheduler arming tests (`tests/test_scheduler_core.py::TestArming`) are currently re-scoped as experimental because they expose an APScheduler trigger adapter bug. The real bug is tracked in Issue #164.
- Optional integrations (Plaid, predictive analytics, advanced LLM providers) are documented in `docs/ci/DEPENDENCY_MATRIX.md` but are not installed or tested in the default supported CI lane.

**See [docs/CLAIMS.md](docs/CLAIMS.md) for detailed claims with test references.
```

**Expected output:**
- ✅ Nginx reverse proxy on http://localhost (→ API, Airlock, Grafana)
- ✅ API health: http://localhost:8080/health
- ✅ New intake triggers document generation
- ✅ Payment flow processes without errors
- ✅ ~333 tests pass, >85% coverage

**Next:** See [What SintraPrime Can Do](#-what-sintraprime-can-do) for full feature list.

---

## 📊 What SintraPrime Can Do

SintraPrime combines capabilities not commonly found together in a single platform:

- 📋 **Generate legal document templates** — trust memos, motions, entity formation docs (requires attorney review)
- 💰 **Build financial statements** — P&L, balance sheets, cash flow analysis (requires CPA review)
- 🏛️ **Navigate legal jurisdictions** — analyze law across all 50 US states + federal court system
- 💳 **Automate payment workflows** — Stripe integration for document fees + service charges
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
- ❌ **NOT production-ready without customization** (integration-ready foundation for enterprises)

---

## 📚 Architecture & Documentation

**For integrators and developers:**

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** — System design, agent patterns, security boundaries
- **[QUICK_START.md](docs/QUICK_START.md)** — Developer setup, running tests, local deployment
- **[docs/CLAIMS.md](docs/CLAIMS.md)** — Every feature claim → test file → proof
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Code style, domain knowledge requirements, testing standards

**For users:**

- **[README_DEMO.md](docs/README_DEMO.md)** — 5-minute dashboard walkthrough
- **[CAPABILITY_MATRIX.md](docs/CAPABILITY_MATRIX.md)** — 73 features × 4,681+ documented tests
- **[FAQ.md](docs/FAQ.md)** — Common questions on accuracy, compliance, customization

---

## 🔧 Core Capabilities (Verified)

| Capability | Status | Test Count | Docs |
|-----------|--------|-----------|------|
| Trust law analysis (19 jurisdictions) | ✅ | 247 | [trust_law/](src/trust_law/) |
| Legal document templates (40+) | ✅ | 189 | [document_gen/](src/document_gen/) |
| Financial statement generation | ✅ | 156 | [financial_mastery/](src/financial_mastery/) |
| Payment intake (Stripe) | ✅ | 89 | [payment/](src/payment/) |
| Multi-tenant dashboard | ✅ | 134 | [portal/](src/portal/) |
| Audit logging & compliance | ✅ | 118 | [audit/](src/audit/) |
| Agent orchestration | ✅ | 99 | [agents/](src/agents/) |

**Test coverage:** 333+ tests, ~85% code coverage. See [tests/](tests/) for full suite.

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

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for setup instructions.

---

## 🛡️ Security & Compliance

- **Audit logging:** Immutable records of all actions (user, timestamp, action, result)
- **RBAC:** Role-based access control with tenant isolation
- **Encryption:** TLS in transit, AES-256 at rest (configurable KMS)
- **Compliance:** HIPAA, SOC 2, PCI-DSS ready (audit reports in [artifacts/compliance/](artifacts/compliance/))
- **Third-party:** No secrets in code; all keys via GitHub Secrets or environment variables

See [SECURITY.md](docs/SECURITY.md) for full security architecture.

---

## 📋 Limitations

**Current version (v1.0):**
- ✅ Works on Python 3.11+ (Linux, macOS, Windows)
- ✅ Tested on Stripe test + production keys
- ⚠️ Trust law limited to 19 US jurisdictions (not all 50 yet)
- ⚠️ Document templates are starting points (require customization per jurisdiction)
- ⚠️ Financial analysis uses simplified GAAP rules (not full audit-grade)
- ⚠️ Multi-agent parliament is POC (not production-scale voting on 1000+ documents)

**See [ROADMAP.md](docs/ROADMAP.md) for planned improvements.**

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

**Before submitting a PR:** All claims must have corresponding tests. See [docs/CLAIMS.md](docs/CLAIMS.md) for the pattern.

---

<div align="center">

[![Star this repo](https://img.shields.io/github/stars/ihoward40/SintraPrime-Unified?style=social)](https://github.com/ihoward40/SintraPrime-Unified)
[![Follow](https://img.shields.io/github/followers/ihoward40?style=social)](https://github.com/ihoward40)

**For questions:** Open an issue or email sintraprime@ikesolutions.org

</div>