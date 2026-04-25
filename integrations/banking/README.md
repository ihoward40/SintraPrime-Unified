# SintraPrime Banking & Financial Intelligence

Real-time banking integration and financial analytics powered by the Plaid API. This module gives SintraPrime advisors a complete, unified view of every client's financial life — across checking, savings, credit, investments, loans, and retirement accounts.

---

## Architecture Overview

```
integrations/banking/
├── plaid_client.py              # Plaid API gateway (Link + Data products)
├── account_aggregator.py        # Unified account view across all institutions
├── transaction_engine.py        # Categorization, search, anomaly detection
├── credit_intelligence.py       # Credit score analysis + improvement plans
├── investment_tracker.py        # Brokerage + retirement portfolio tracking
├── liability_manager.py         # Debt summary: mortgages, loans, credit cards
├── cash_flow_analyzer.py        # Income, expenses, patterns, forecasting
├── budget_engine.py             # Budget creation, tracking, AI recommendations
├── net_worth_calculator.py      # Real-time net worth across all accounts
├── fraud_detector.py            # Anomalous transaction detection
├── financial_health_scorer.py   # Composite financial health score (0–100)
├── funding_matcher.py           # Match client to SBA, CDFI, VC, grant sources
├── tax_optimizer.py             # Tax-loss harvesting, deductions, strategies
├── wealth_builder.py            # Personalized wealth-building roadmap
├── debt_eliminator.py           # Avalanche / snowball / hybrid payoff engine
├── credit_optimizer.py          # Credit score improvement action plan
├── business_banking.py          # SMB account analysis + business cash flow
└── reports/
    ├── financial_statement_generator.py  # P&L, Balance Sheet, Cash Flow
    ├── net_worth_report.py               # Formatted net worth reports
    ├── credit_report_analyzer.py         # Credit intelligence reports
    └── tax_summary_report.py             # Tax summary for clients + CPAs
```

---

## Quick Setup

### 1. Get Plaid API Credentials

1. Sign up at [plaid.com](https://plaid.com) and create an application.
2. Start in **Sandbox** mode (free, unlimited test data).
3. Copy your **Client ID** and **Secret** from the Plaid Dashboard.

### 2. Configure Environment Variables

```bash
export PLAID_CLIENT_ID="your_client_id"
export PLAID_SECRET="your_secret"
export PLAID_ENV="sandbox"           # sandbox | development | production
```

Or using a `.env` file (recommended for local development):

```env
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_secret
PLAID_ENV=sandbox
```

### 3. Install Dependencies

```bash
pip install plaid-python pydantic httpx python-dotenv
```

---

## Plaid Link Flow (Frontend → Backend)

### Step 1: Generate a Link Token (Backend)

```python
from integrations.banking.plaid_client import PlaidClient, PlaidConfig

config = PlaidConfig.from_env()
plaid = PlaidClient(config=config)

# Call this from your API endpoint
link_response = await plaid.create_link_token(user_id="user_12345")
link_token = link_response.link_token
# → Send link_token to frontend
```

### Step 2: Open Plaid Link (Frontend)

```javascript
// Use @plaidinc/react-plaid-link or the JS SDK
const { open } = usePlaidLink({
  token: linkToken,
  onSuccess: async (publicToken, metadata) => {
    await fetch('/api/plaid/exchange', {
      method: 'POST',
      body: JSON.stringify({ publicToken }),
    });
  },
});
```

### Step 3: Exchange Public Token (Backend)

```python
exchange = await plaid.exchange_public_token(public_token)
access_token = exchange.access_token
item_id = exchange.item_id

# Store access_token securely (encrypted in DB)
# Never expose it to the frontend
```

### Step 4: Fetch Data

```python
# Get all accounts with balances
accounts = await plaid.get_accounts(access_token)

# Get 90 days of transactions
from datetime import date, timedelta
end = date.today()
start = end - timedelta(days=90)
transactions, total = await plaid.get_transactions(access_token, start, end)

# Get all transactions (handles pagination automatically)
all_txns = await plaid.get_all_transactions(access_token, start, end)
```

---

## Key Features by Module

### Transaction Engine

```python
from integrations.banking.transaction_engine import TransactionEngine

engine = TransactionEngine()

# Enrich and categorize transactions
enriched = [engine.enrich(t) for t in raw_transactions]

# Search transactions
results = engine.search(enriched, query="amazon", min_amount=50)

# Detect recurring subscriptions
recurring = engine.detect_recurring(enriched)

# Find anomalies
anomalies = engine.detect_anomalies(enriched)

# Monthly summary
summary = engine.monthly_summary(enriched, year=2025, month=3)
```

### Financial Health Score

```python
from integrations.banking.financial_health_scorer import FinancialHealthScorer, FinancialHealthInput

scorer = FinancialHealthScorer()
report = scorer.score(FinancialHealthInput(
    monthly_income=8_000,
    monthly_expenses=5_500,
    liquid_savings=18_000,
    total_debt=25_000,
    monthly_debt_payments=700,
    credit_score=720,
    net_worth=85_000,
    net_worth_prior_year=70_000,
    budget_adherence_pct=82.0,
    has_life_insurance=True,
    has_health_insurance=True,
    has_disability_insurance=False,
    has_property_insurance=True,
))

print(f"Score: {report.composite_score}/100 ({report.letter_grade})")
for dim in report.dimensions:
    print(f"  {dim.name}: {dim.score:.0f}/100")
```

### Debt Elimination

```python
from integrations.banking.debt_eliminator import DebtEliminator, DebtItem

eliminator = DebtEliminator()
debts = [
    DebtItem(debt_id="cc1", name="Visa", current_balance=5_000, apr=0.22, minimum_payment=100),
    DebtItem(debt_id="sl1", name="Student Loan", current_balance=18_000, apr=0.065, minimum_payment=200),
]
report = eliminator.analyze("client_001", debts, extra_monthly_payment=200)
print(f"Recommended: {report.comparison.recommended_strategy}")
print(f"Payoff date (avalanche): {report.comparison.avalanche.payoff_date}")
print(f"Interest saved vs snowball: ${report.comparison.interest_difference:,.0f}")
```

### Credit Optimizer

```python
from integrations.banking.credit_optimizer import CreditOptimizer, OptimizationGoal

optimizer = CreditOptimizer()
plan = optimizer.create_plan(
    client_id="client_001",
    report=credit_report,        # CreditReport from credit_intelligence.py
    goal=OptimizationGoal.MORTGAGE_APPROVAL,
)
for action in plan.actions:
    print(f"[{action.priority}] {action.title} — {action.estimated_point_gain}")
```

### Net Worth Calculator

```python
from integrations.banking.net_worth_calculator import NetWorthCalculator

calc = NetWorthCalculator()
report = calc.calculate(
    client_id="client_001",
    accounts=plaid_accounts,          # from plaid_client.get_accounts()
    liabilities=plaid_liabilities,    # from plaid_client.get_liabilities()
    investment_holdings=holdings,     # from plaid_client.get_investments()
    custom_assets=[
        {"name": "Primary Home", "type": "real_estate", "value": 750_000},
        {"name": "Tesla Model 3", "type": "vehicle", "value": 28_000},
    ],
    client_age=38,
    annual_expenses=66_000,
)
print(f"Net Worth: ${report.net_worth:,.0f}")
print(f"FIRE Progress: {report.fire_analysis['pct_of_fire_goal']:.1f}%")
```

### Funding Matcher

```python
from integrations.banking.funding_matcher import FundingMatcher, ClientFundingProfile

matcher = FundingMatcher()
matches = matcher.match(ClientFundingProfile(
    client_id="biz_001",
    credit_score=690,
    annual_revenue=350_000,
    months_in_business=36,
    industry="technology",
    state="CA",
    is_minority_owned=True,
    is_woman_owned=False,
    loan_purpose="equipment",
    requested_amount=75_000,
))
for m in matches[:5]:
    print(f"{m.source_name}: {m.eligibility_pct:.0f}% eligible | ${m.amount_min:,.0f}–${m.amount_max:,.0f} | APR: {m.rate_range}")
```

### Financial Statements (Reports)

```python
from integrations.banking.reports.financial_statement_generator import FinancialStatementGenerator

gen = FinancialStatementGenerator()
pnl = gen.generate_pnl(
    entity_name="Acme Digital LLC",
    period_label="Q1 2025",
    revenue_by_stream={"Consulting": 45_000, "Software Licenses": 12_500},
    cogs_by_category={"Contractor Costs": 15_000},
    opex_by_category={"Payroll": 18_000, "Software": 3_200, "Marketing": 2_500},
)

# Export to HTML
html = gen.to_html(pnl, brand_color="#1a1a2e")
with open("q1_pnl.html", "w") as f:
    f.write(html)

# Export to Markdown
md = gen.to_markdown(pnl)
```

---

## Plaid Products Reference

| Product | What You Get | Plaid Endpoint |
|---------|-------------|---------------|
| `transactions` | 24 months of categorized transactions | `transactions/get` |
| `auth` | Account + routing numbers (ACH) | `auth/get` |
| `identity` | Account owner name, address, phone | `identity/get` |
| `assets` | Asset reports for lending (Fan Freddie format) | `asset_report/create` |
| `investments` | Holdings + transaction history | `investments/holdings/get` |
| `liabilities` | Student loans, mortgage, credit card details | `liabilities/get` |

---

## Webhook Events

Plaid sends webhooks for real-time updates. Handle them in your API:

```python
# In your FastAPI/Django/Flask webhook handler
event = await plaid_client.handle_webhook(
    webhook_type=request.json["webhook_type"],
    webhook_code=request.json["webhook_code"],
    data=request.json,
)

if event.webhook_type == "TRANSACTIONS" and event.webhook_code == "DEFAULT_UPDATE":
    # Trigger transaction sync for this item
    await sync_transactions(item_id=event.item_id)
```

### Key Webhook Types

| Type | Code | Meaning |
|------|------|---------|
| `TRANSACTIONS` | `DEFAULT_UPDATE` | New transactions available |
| `TRANSACTIONS` | `INITIAL_UPDATE` | First batch ready after Link |
| `ITEM` | `ERROR` | User needs to re-authenticate |
| `ITEM` | `PENDING_EXPIRATION` | Access token expiring soon |
| `INVESTMENTS_TRANSACTIONS` | `DEFAULT_UPDATE` | Investment transactions updated |

---

## Security Best Practices

1. **Never log or expose access tokens** — treat like passwords.
2. **Encrypt at rest** — store access tokens encrypted in your database.
3. **Rotate tokens** — use `item/access_token/invalidate` when a user disconnects.
4. **Verify webhooks** — validate the `Plaid-Verification` header signature.
5. **Use HTTPS only** — for both your API and webhook endpoints.
6. **Sandbox for testing** — never use production credentials in development.

---

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest integrations/banking/tests/ -v

# Run specific test file
pytest integrations/banking/tests/test_debt_eliminator.py -v

# Run with coverage
pytest integrations/banking/tests/ --cov=integrations/banking --cov-report=html
```

---

## Environment Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `PLAID_CLIENT_ID` | Your Plaid Client ID | Required |
| `PLAID_SECRET` | Your Plaid Secret | Required |
| `PLAID_ENV` | `sandbox`, `development`, or `production` | `sandbox` |
| `PLAID_WEBHOOK_URL` | URL for Plaid to send webhooks | Optional |
| `PLAID_REDIRECT_URI` | OAuth redirect URI (for OAuth institutions) | Optional |

---

## Support & Resources

- [Plaid API Documentation](https://plaid.com/docs/)
- [Plaid Python SDK](https://github.com/plaid/plaid-python)
- [Plaid Dashboard](https://dashboard.plaid.com)
- [Plaid Status Page](https://status.plaid.com)
- SintraPrime Internal: `#sintra-banking-integration` Slack channel
