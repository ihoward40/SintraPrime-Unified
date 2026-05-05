# Changelog

All notable changes to SintraPrime-Unified are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-05-05

### Added
- **Trust Law Engine** — 19 US jurisdictions (CA, NY, TX, FL, IL, PA, OH, MI, NC, VA, AZ, CO, WA, OR, MA, MD, NJ, CT, DE)
  - Revocable, irrevocable, special needs, charitable remainder trusts
  - Statute-based reasoning and citation generation
  - 247 tests covering all trust types
  
- **Legal Document Generator** — 40+ professional templates
  - Trust memos, powers of attorney, wills, corporate bylaws
  - IRAC-structured legal motions
  - PDF/DOCX/HTML output rendering
  - 189 tests validating all templates
  
- **Financial Statement Builder** — GAAP-compliant outputs
  - P&L, balance sheet, cash flow statements
  - Revenue recognition rules and journal entry validation
  - Credit building roadmaps (0–700+ score)
  - 156 tests on financial accuracy
  
- **Payment Integration** — Stripe test + production
  - One-time and subscription payment intents
  - Refund and dispute handling
  - Webhook-based async processing
  - 89 tests with live payment proof (Phase 19F)
  
- **Multi-Tenant Dashboard** — Role-based access control
  - Case management interface
  - Real-time document generation updates
  - Audit trail visibility per tenant
  - 134 tests on dashboard functionality
  
- **Audit & Compliance** — Immutable logging
  - Write-once audit logs
  - RBAC with role isolation
  - HIPAA/SOC 2/PCI-DSS audit reports
  - 118 tests on log immutability
  
- **Multi-Agent Parliament** — Democratic consensus reasoning
  - 3+ specialized agents (trust, finance, compliance)
  - Weighted voting with minority opinions
  - 99 tests on agent coordination
  
- **Cloud Deployment** — Multi-cloud infrastructure
  - AWS Terraform (ECS Fargate + RDS, ~$400/mo)
  - Azure Bicep (App Service + SQL, ~$250/mo)
  - GCP Terraform (Cloud Run + Cloud SQL, ~$350/mo)

### Fixed
- **P0-BOOT** — Import-time blockers preventing app startup (PR #62)
- **Documentation Credibility** — Removed broken links, added claims→evidence mapping

### Security
- GitHub Secrets for all API keys (no local .env in repo)
- TLS in transit, AES-256 at rest
- Role-based access control enforced at API layer
- Immutable audit logs stored in write-once PostgreSQL views

### Documentation
- `docs/CLAIMS.md` — Every claim paired with test files and demo commands
- `docs/ARCHITECTURE.md` — System design, agent patterns, security boundaries
- `QUICK_START.md` — Developer setup and local deployment
- `README.md` — Reframed for compliance, added "Proof in 10 Minutes" section

### Limitations
- Trust law covers 19 jurisdictions (not all 50 US states yet)
- Document templates are starting points (require attorney customization)
- Financial analysis uses simplified GAAP (not full audit-grade complexity)
- Multi-agent parliament is POC (not production-scale for 1000+ documents)

---

## [0.9.0] - 2025-04-30

### Added
- Phase 25: Multi-cloud infrastructure deployment (AWS, Azure, GCP)
- Phase 24: Admin Dashboard + Windows deployment + production load testing
- Phase 23: Session monitoring, load testing, Windows refinement
- Phase 22: Baseline debt cleanup (ruff, test, coverage normalization)
- Phase 21: Enterprise integration (SAML, audit logging, multi-tenant, onboarding)
- Phase 20: Production maturity verification (capability matrix, architecture review, documentation)

---

## How to Report Issues

- **Security issues:** Email sintraprime-security@ikesolutions.org
- **Feature requests:** Open a GitHub issue with label `feature-request`
- **Bug reports:** Open a GitHub issue with label `bug` and reproduction steps

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

All contributions must include tests. See [docs/CLAIMS.md](./docs/CLAIMS.md) for the test→claim mapping pattern.