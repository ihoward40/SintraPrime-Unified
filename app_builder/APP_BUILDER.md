# SintraPrime App Builder + Digital Twin

> **"What no other AI agent can do: manage your entire life portfolio."**

The SintraPrime App Builder is a Manus-style autonomous web and app builder designed for legal and financial use cases. Combined with the **Digital Twin** — a living AI model of your complete life situation — it is the most comprehensive AI governance platform ever built.

---

## Table of Contents

1. [Overview](#overview)
2. [Build a Legal Portal in One Command](#build-a-legal-portal-in-one-command)
3. [Digital Twin — The Most Unique AI Feature](#digital-twin)
4. [Available Templates](#available-templates)
5. [Stripe Billing Setup](#stripe-billing-setup)
6. [Database Builder](#database-builder)
7. [API Reference](#api-reference)
8. [Comparison to Manus AI](#comparison-to-manus-ai)
9. [What No Other AI Can Do](#what-no-other-ai-can-do)

---

## Overview

The App Builder takes a natural language description — or a pre-built template — and generates a complete, deployable web application with:

- **Full HTML/React frontend** (Tailwind CSS + DaisyUI)
- **SQLite/PostgreSQL database** with auto-generated schema
- **Stripe billing integration** (subscriptions, flat fees, retainers)
- **SEO optimization** (meta tags, og:tags, structured data)
- **FastAPI backend** with auto-generated REST endpoints
- **Authentication** (for portals and dashboards)

```python
from app_builder import AppBuilder

builder = AppBuilder()

# Build from natural language
result = builder.build_from_description(
    "Build a law firm website for Smith & Associates specializing in estate planning in New Jersey"
)

# Or one-command specialty builds
result = builder.build_legal_portal(
    client_name="Smith & Associates",
    practice_areas=["Estate Planning", "Trust Administration", "Probate"],
    jurisdiction="New Jersey",
)

print(result.app_url)       # http://localhost:3000
print(result.files_created) # ['index.html', 'contact.html', 'schema.sql', ...]
```

---

## Build a Legal Portal in One Command

### Legal Firm Website

```python
result = builder.build_legal_portal(
    client_name="Johnson Law Firm",
    practice_areas=["Estate Planning", "Trust Law", "Probate"],
    jurisdiction="New Jersey",
)
```

**Generates:**
- `index.html` — Hero, practice areas, testimonials, CTA
- `practice-areas.html` — Individual practice area pages
- `attorneys.html` — Attorney profiles and bios
- `contact.html` — Client intake form with validation
- `schema.sql` — Clients, matters, appointments, billing tables
- `api.py` — FastAPI routes for all data models
- `stripe_config.py` — Billing integration setup

### Financial Dashboard

```python
result = builder.build_financial_dashboard({
    "name": "Personal Finance Dashboard",
    "monthly_income": 8000,
    "total_debts": 45000,
    "credit_score": 680,
})
```

### Trust Management Portal

```python
result = builder.build_trust_manager({
    "trust_name": "Thompson Family Trust",
    "trustee_name": "Michael Thompson",
    "beneficiaries": ["Alice Thompson", "Bob Thompson"],
    "trust_value": 1_200_000,
})
```

### From Natural Language

```python
spec = builder.build_from_description(
    "I need a client portal for my debt settlement law firm. It should have "
    "secure document sharing, a tracker for each creditor negotiation, and "
    "Stripe billing for flat fees and payment plans."
)
result = builder.build(spec)
```

### Iterative Improvement

```python
result = builder.iterate(app_id, "Add dark mode, improve the intake form, add Stripe payments")
```

---

## Digital Twin

> The Digital Twin is the most unique feature in all of AI.

Unlike any other AI tool, the Digital Twin maintains a **living, persistent model of your entire life**: your legal standing, financial profile, relationships, health directives, business interests, and digital assets.

It doesn't just store data — it **reasons** about your situation, identifies vulnerabilities, and guides you toward a fully governed life.

### Create a Twin

```python
from app_builder import DigitalTwin

twin = DigitalTwin()
twin.create("user_001", "James Thompson")
```

### Update with Life Events

```python
from app_builder.app_types import LifeEvent

# Add a legal matter
twin.update("user_001", LifeEvent(
    event_type="legal",
    title="Family Trust Established",
    impact_level="high",
    data={
        "legal_matter": {
            "matter_id": "M001",
            "title": "Thompson Family Trust",
            "matter_type": "trust",
            "status": "active",
            "jurisdiction": "New Jersey",
        }
    }
))

# Add financial profile
twin.update("user_001", LifeEvent(
    event_type="financial",
    title="Financial Profile Update",
    impact_level="medium",
    data={
        "total_assets": 850_000,
        "total_debts": 125_000,
        "monthly_income": 12_000,
        "credit_score": 740,
    }
))

# Add healthcare directive
twin.update("user_001", LifeEvent(
    event_type="health",
    title="Healthcare Proxy Executed",
    impact_level="high",
    data={
        "directive": {
            "directive_type": "healthcare_proxy",
            "title": "Healthcare Proxy",
            "status": "signed",
            "designated_agent": "Patricia Thompson",
        }
    }
))
```

### Life Snapshot

```python
snapshot = twin.life_snapshot("user_001")

print(f"Net Worth: ${snapshot.financial_profile.net_worth:,.2f}")
print(f"Active Legal Matters: {len(snapshot.legal_matters)}")
print(f"Estate Readiness: {snapshot.estate_readiness_score}/100")
print(f"Risk Score: {snapshot.risk_score}/100")
```

### Risk Assessment

```python
report = twin.life_risk_assessment("user_001")

print(f"Risk Level: {report.risk_level}")  # low / medium / high / critical
print(f"Score: {report.overall_risk_score}/100")

for gap in report.critical_gaps:
    print(f"⚠️  {gap}")

for rec in report.recommendations:
    print(f"→ {rec}")
```

**What it checks:**
- Debt-to-income ratio (flags DTI > 43%)
- Missing healthcare proxy or living will
- Missing executor or trustee designation
- Digital assets without beneficiaries
- Business interests without entity protection
- Active legal matter volume

### Estate Readiness

```python
report = twin.estate_readiness("user_001")

print(f"Estate Readiness: {report.readiness_level} ({report.readiness_score}/100)")
print(f"Has Will: {report.has_will}")
print(f"Has Trust: {report.has_trust}")
print(f"Has POA: {report.has_poa}")
print(f"Has Healthcare Directive: {report.has_healthcare_directive}")

for doc in report.missing_documents:
    print(f"Missing: {doc}")
```

### What-If Scenarios

```python
analysis = twin.what_if("user_001", "What if I start a business?")

for risk in analysis.risks:
    print(f"Risk: {risk}")

for opp in analysis.opportunities:
    print(f"Opportunity: {opp}")

for action in analysis.recommended_actions:
    print(f"→ {action}")
```

**Scenarios supported:**
- "What if I start a business?"
- "What if I get divorced?"
- "What if I inherit $500,000?"
- "What if I become disabled?"
- "What if I move to Florida?"

### Export Life Portfolio

```python
portfolio = twin.export_life_portfolio("user_001")

print(portfolio.summary)
# "Life Portfolio for James Thompson — Risk Level: LOW (12.5/100) |
#  Estate Readiness: Mostly Ready (75.0/100) | Active Legal Matters: 1 |
#  Net Worth: $725,000.00"
```

---

## Available Templates

| Template | Description | App Type |
|----------|-------------|----------|
| `legal_firm_website` | Full law firm marketing site with SEO, intake forms, attorney bios | LEGAL_PORTAL |
| `client_document_portal` | Secure authenticated doc sharing between attorneys and clients | DOCUMENT_PORTAL |
| `trust_management_portal` | Trust administration with beneficiary management and compliance | TRUST_MANAGER |
| `estate_planning_intake` | 5-step estate planning questionnaire for will, trust, POA prep | LEGAL_PORTAL |
| `debt_settlement_tracker` | Debt negotiation progress, offers, creditor comms, payment plans | CASE_TRACKER |
| `business_formation_wizard` | Step-by-step LLC/S-Corp/C-Corp formation guide and doc generator | LEGAL_PORTAL |
| `court_deadline_tracker` | Docket management for court deadlines and matter milestones | CASE_TRACKER |
| `financial_health_dashboard` | Net worth, accounts, budgets, debts, credit, investments | FINANCIAL_DASHBOARD |

### Using Templates

```python
from app_builder import TemplateLibrary, AppBuilder

library = TemplateLibrary()
builder = AppBuilder()

# List all templates
for template in library.list_templates():
    print(f"{template.name}: {template.description}")

# Get a template
spec = library.get_template("legal_firm_website")

# Customize it
spec = library.customize_template("legal_firm_website", {
    "name": "Smith & Associates",
    "styling": {"primary_color": "#1a4f2a"},
    "features": ["stripe_billing", "appointment_booking"],
})

# Build it
result = builder.build(spec)
```

---

## Stripe Billing Setup

```python
from app_builder import StripeIntegrator

stripe = StripeIntegrator()  # Reads STRIPE_SECRET_KEY from env

# Legal billing setup
config = stripe.setup_legal_billing(
    firm_name="Smith & Associates",
    practice_areas=["Estate Planning", "Trust Law"],
)

# Create a monthly retainer
retainer_id = stripe.setup_retainer(
    name="Monthly Legal Retainer",
    monthly_amount=2000,
)

# Create a flat fee product
flat_fee_id = stripe.setup_flat_fee_product(
    name="LLC Formation Package",
    amount=1500,
)

# Create a subscription
sub_id = stripe.create_subscription_product(
    name="Estate Planning Plus",
    price_monthly=500,
    features=["Monthly strategy call", "Document review", "Priority support"],
)

# Generate embeddable payment form
html = stripe.generate_payment_form(sub_id)

# Generate invoice template
invoice_html = stripe.generate_invoice_template({
    "firm_name": "Smith & Associates",
    "address": "123 Main St, Newark, NJ 07102",
    "phone": "(973) 555-0100",
})
```

### Environment Variables

```bash
STRIPE_SECRET_KEY=sk_live_...       # Live mode
STRIPE_SECRET_KEY=sk_test_...       # Test mode
STRIPE_PUBLISHABLE_KEY=pk_...       # Frontend key
STRIPE_WEBHOOK_SECRET=whsec_...     # Webhook validation
```

No secrets are hardcoded anywhere in the codebase.

---

## Database Builder

```python
from app_builder import DatabaseBuilder

db = DatabaseBuilder()

# Create schema from description
schema = db.from_description("law firm with clients, matters, documents, and billing")

# Generate SQLite database
db.generate_sqlite(schema, "/data/firm.db")

# Generate SQL migration
sql = db.generate_migration(schema)

# Seed with realistic demo data
db.seed_sample_data("/data/firm.db", schema)

# Generate FastAPI endpoints for the schema
api_code = db.generate_api_endpoints(schema)
```

### Legal-Specific Tables

- `clients` — Contact info, intake date, matter assignments
- `matters` — Case type, status, jurisdiction, attorney
- `documents` — Title, type, status, S3 path, signers
- `deadlines` — Matter deadlines, court dates, statutes of limitations
- `billing` — Invoices, retainer balances, payment status
- `trusts` — Trust details, trustee, beneficiaries, distributions

### Financial Tables

- `accounts` — Bank accounts, investment accounts, retirement
- `transactions` — Deposits, withdrawals, categories
- `budgets` — Category budgets, monthly targets
- `investments` — Holdings, cost basis, current value
- `credit` — Credit report entries, disputes, accounts

---

## API Reference

### App Builder Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/builder/build` | Build app from natural language description |
| `POST` | `/builder/build/legal-portal` | One-command legal portal |
| `POST` | `/builder/build/financial-dashboard` | Personal finance app |
| `POST` | `/builder/build/trust-manager` | Trust management portal |
| `POST` | `/builder/build/client-crm` | Law firm CRM |
| `GET`  | `/builder/apps` | List all built apps |
| `GET`  | `/builder/templates` | List available templates |
| `GET`  | `/builder/templates/{name}` | Get template spec |
| `POST` | `/builder/templates/{name}/build` | Build from template |
| `GET`  | `/builder/preview/{app_id}` | HTML preview |
| `POST` | `/builder/deploy/{app_id}` | Deploy app |
| `POST` | `/builder/iterate/{app_id}` | Improve existing app |

### Digital Twin Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/twin/{user_id}` | Create Digital Twin |
| `GET`  | `/twin/{user_id}` | Life snapshot |
| `PUT`  | `/twin/{user_id}/event` | Update with life event |
| `GET`  | `/twin/{user_id}/risks` | Risk assessment |
| `GET`  | `/twin/{user_id}/estate` | Estate readiness |
| `GET`  | `/twin/{user_id}/recommendations` | Governance recommendations |
| `POST` | `/twin/{user_id}/what-if` | What-if scenario analysis |
| `GET`  | `/twin/{user_id}/portfolio` | Export life portfolio |
| `GET`  | `/twin` | List all twins |
| `DELETE` | `/twin/{user_id}` | Delete twin |

---

## Comparison to Manus AI

| Feature | Manus AI | SintraPrime App Builder |
|---------|----------|------------------------|
| Natural language app building | ✅ | ✅ |
| Auto-generated database | ✅ | ✅ |
| Stripe integration | ✅ | ✅ |
| SEO optimization | ✅ | ✅ |
| React/HTML generation | ✅ | ✅ |
| Pre-built templates | ✅ | ✅ (8 legal/financial) |
| Legal-specific features | ❌ | ✅ |
| Trust management | ❌ | ✅ |
| Estate planning intake | ❌ | ✅ |
| Debt settlement tracking | ❌ | ✅ |
| Court deadline docket | ❌ | ✅ |
| **Digital Twin AI** | ❌ | ✅ |
| Life risk assessment | ❌ | ✅ |
| Estate readiness scoring | ❌ | ✅ |
| What-if scenario planning | ❌ | ✅ |
| Life portfolio export | ❌ | ✅ |
| Governance recommendations | ❌ | ✅ |

---

## What No Other AI Can Do

SintraPrime's Digital Twin is the only AI system in the world that:

### 1. Models Your Entire Legal Life
Not just one case — every matter, every contract, every trust, every deadline, every jurisdiction. A living map of your legal standing.

### 2. Understands Your Estate Position in Real-Time
"You have a living trust but no healthcare proxy. You're 60% protected. Here are the three documents you need to execute this week."

### 3. Simulates Life Decisions Before You Make Them
"If you start a business without an LLC, your personal assets are exposed. If you move to Florida, your homestead protects $500,000 from creditors. Here's how to get there."

### 4. Maintains Financial + Legal Integration
Your debt-to-income ratio, your trust distribution timing, your business equity, and your estate value — all in one coherent picture.

### 5. Produces a Life Portfolio on Demand
A complete life governance document: risk report, estate analysis, recommendations, document manifest, executive summary — exportable and shareable with your attorney.

### 6. Grows With You
Every life event — marriage, inheritance, new business, health crisis, real estate purchase — updates the model and recalibrates your entire life governance strategy.

---

> *SintraPrime doesn't just build apps. It builds the infrastructure for your life.*

---

**Version:** 1.0.0  
**Module:** `SintraPrime-Unified/app_builder`  
**License:** Proprietary — SintraPrime Inc.
