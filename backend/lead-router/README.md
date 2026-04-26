# SintraPrime Lead Router

Backend service that receives lead submissions, routes them to the best specialist agent, and triggers automated follow-up sequences.

## Phase 10.3 Deliverable

This implements the **Lead Router + Agent Assignment Engine** for SintraPrime, consisting of:

### Features

1. **Lead Intake Processing** — Receive and validate intake form submissions
2. **Smart Routing Algorithm** — Match leads to best specialist (Legal, Financial, or Combined)
3. **Airtable CRM Integration** — Log all leads in central database
4. **Automated Email Confirmation** — Send welcome email with scheduling link
5. **Agent Dispatch** — Alert assigned specialist to review case
6. **Callback Scheduling** — Provide Calendly link for self-scheduling
7. **Follow-up Sequences** — Auto-triggered reminders at 3 and 7 days

### Architecture

```
lead-router/
├── models/
│   └── lead.py           # Pydantic data models (IntakeData, Lead, RoutingResult)
├── api/
│   └── routes.py         # FastAPI endpoints (/api/leads, /api/leads/{id}, /api/agents)
├── services/
│   ├── airtable_service.py    # Write leads to Airtable CRM
│   ├── email_service.py       # Send confirmation and follow-up emails
│   └── agent_service.py       # Dispatch leads to agents
├── utils/
│   └── matching.py       # Routing algorithm (legal, financial, combined scoring)
├── tests/
│   └── test_router.py    # Unit tests for routing logic
├── router.py             # Main orchestration logic
├── config.py             # Environment variables and configuration
├── main.py              # FastAPI application entry point
└── requirements.txt     # Python dependencies
```

## Routing Algorithm

The lead router uses a three-dimensional scoring system:

### Scoring Dimensions

1. **Legal Score (0-100)** — Detects legal needs
   - Keywords: trust, estate, will, business formation, contract, litigation, etc.
   - Signals: business ownership, asset protection mentions
   - Higher score = stronger legal focus

2. **Financial Score (0-100)** — Detects financial needs
   - Keywords: debt, credit, investment, tax, retirement, restructuring, etc.
   - Signals: financial complexity, wealth management
   - Higher score = stronger financial focus

3. **Urgency Score (0-100)** — Detects time sensitivity
   - Keywords: immediate, urgent, crisis, foreclosure, lawsuit, collection, etc.
   - Timeline mentions: "this week", "immediately", etc.
   - Higher score = more urgent

### Routing Logic

```
if legal_score > 70 AND financial_score < 40:
    → Agent: Zero (Legal Specialist)
    
elif financial_score > 70 AND legal_score < 40:
    → Agent: Sigma (Financial Specialist)
    
elif legal_score > 50 AND financial_score > 50:
    → Agent: Nova (Combined Specialist)
    
else:
    → Queue: General Inquiry (manual review)
```

### Confidence Score

Calculated from dimension scores with urgency boost:
```
confidence = (legal + financial + urgency) / 3
+ urgency_bonus (if urgency_score > 70, +10 points)
```

## API Endpoints

### 1. Submit Lead

```http
POST /api/leads
Content-Type: application/json

{
  "name": "John Smith",
  "email": "john@example.com",
  "phone": "+1-555-1234",
  "legal_situation": "I need to set up a trust for my family business...",
  "financial_snapshot": "I have significant assets...",
  "goals": "Plan for succession and asset protection...",
  "company_name": "Smith Industries",
  "industry": "Manufacturing",
  "timeline": "within 6 months"
}
```

**Response:**
```json
{
  "status": "success",
  "lead_id": "550e8400-e29b-41d4-a716-446655440000",
  "assigned_agent": "Zero (Legal Specialist)",
  "confidence": 87.5,
  "next_step": "Expect a call within 24 hours. You can also schedule a demo directly.",
  "callback_url": "https://calendly.com/sintraprime/demo",
  "email_sent": true,
  "message": "Welcome John Smith! Your intake has been received and routed to Zero (Legal Specialist)."
}
```

### 2. Get Lead Status

```http
GET /api/leads/{lead_id}
```

**Response:**
```json
{
  "success": true,
  "lead_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "John Smith",
  "status": "new",
  "assigned_agent": "legal-specialist",
  "contacted_at": null,
  "demo_scheduled_at": null,
  "qualification_score": 75.0
}
```

### 3. List Agents

```http
GET /api/agents
```

**Response:**
```json
{
  "success": true,
  "agents": {
    "legal-specialist": {
      "name": "Zero",
      "display_name": "Zero (Legal Specialist)",
      "email": "zero@sintraprime.ai",
      "specialty": "Legal Planning & Asset Protection",
      "phone": "+1-555-ZERO-LEG"
    },
    "financial-specialist": {
      "name": "Sigma",
      "display_name": "Sigma (Financial Specialist)",
      "email": "sigma@sintraprime.ai",
      "specialty": "Financial Strategy & Wealth Management",
      "phone": "+1-555-SIGMA-FIN"
    },
    "combined-specialist": {
      "name": "Nova",
      "display_name": "Nova (Combined Specialist)",
      "email": "nova@sintraprime.ai",
      "specialty": "Integrated Legal & Financial Planning",
      "phone": "+1-555-NOVA-INT"
    }
  }
}
```

### 4. Health Check

```http
GET /api/health
```

## Installation & Setup

### Prerequisites

- Python 3.9+
- Airtable account with CRM base
- SendGrid or AWS SES account (optional, uses stubs by default)
- FastAPI and dependencies

### Installation

```bash
cd /agent/home/apps/sintraprime-backend/lead-router
pip install -r requirements.txt
```

### Configuration

Set environment variables:

```bash
# Airtable
export AIRTABLE_API_KEY="pat_your_key_here"
export AIRTABLE_BASE_ID="appXXXXXXXXXXXXXX"

# Email (optional)
export EMAIL_PROVIDER="sendgrid"  # or "ses"
export SENDGRID_API_KEY="SG.your_key_here"
export FROM_EMAIL="leads@sintraprime.ai"

# Optional integrations
export TASKLET_API_ENABLED="true"
export SLACK_ENABLED="true"

# Calendly
export CALENDLY_URL="https://calendly.com/sintraprime/demo"

# Server
export PORT="8000"
export HOST="0.0.0.0"
export DEBUG="false"
```

### Running the Server

```bash
# Development
python main.py

# Production (using uvicorn)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# With environment file
env $(cat .env) python main.py
```

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test class
python -m pytest tests/test_router.py::TestLeadRouting -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html

# Run test script directly
python tests/test_router.py
```

## Test Coverage

The test suite includes:

- ✅ **TestLegalScoring** — Validates legal score calculation
- ✅ **TestFinancialScoring** — Validates financial score calculation
- ✅ **TestUrgencyScoring** — Validates urgency detection
- ✅ **TestQualificationScore** — Validates overall lead quality scoring
- ✅ **TestLeadRouting** — Tests routing to all agent types
- ✅ **TestLeadModel** — Tests lead data model
- ✅ **TestIntakeDataValidation** — Tests input validation

## Airtable Integration

### Base Configuration

**Base Name:** `SintraPrime-CRM`
**Table Name:** `Leads`

### Fields

| Field | Type | Description |
|-------|------|-------------|
| LeadID | Single line text | UUID of the lead |
| Name | Single line text | Prospect name |
| Email | Email | Email address |
| Phone | Phone number | Phone number |
| LegalSituation | Long text | Description of legal needs |
| FinancialSnapshot | Long text | Description of financial situation |
| Goals | Long text | What prospect wants to achieve |
| CompanyName | Single line text | Business name (if applicable) |
| Industry | Single line text | Industry/sector |
| ReferralSource | Single line text | How they heard about us |
| AssignedAgent | Single line text | Assigned agent type |
| LegalScore | Number | Legal dimension score (0-100) |
| FinancialScore | Number | Financial dimension score (0-100) |
| UrgencyScore | Number | Urgency score (0-100) |
| QualificationScore | Number | Overall qualification (0-100) |
| Status | Single select | new / contacted / demo-scheduled / won / lost |
| SubmittedAt | Date | When form was submitted |
| ContactedAt | Date | When agent contacted lead |
| DemoScheduledAt | Date | When demo was scheduled |

## Email Templates

### Confirmation Email

Sent immediately after lead submission includes:
- Welcome message personalized with prospect name
- Assigned agent introduction
- 24-hour follow-up timeline
- Calendly scheduling link
- Call-to-action button

### Follow-up Reminder #1 (3 days)

Sent if no response within 3 days:
- "We haven't heard from you yet" message
- Agent contact information
- Scheduling link with urgency

### Follow-up Reminder #2 (7 days)

Final reminder sent at 7 days:
- "Final reminder" message
- Direct agent contact
- Scheduling link

## Service Integrations

### Airtable Service

Handles all CRM operations:
- Writing new leads
- Updating lead status
- Recording demo scheduling
- Retrieving lead records

### Email Service

Handles email operations:
- Send confirmation emails
- Send follow-up reminders
- Compose HTML and plain text
- Support for SendGrid and AWS SES

### Agent Service

Handles agent assignment:
- Dispatch leads to agents
- Create Tasklet tasks (optional)
- Send Slack notifications (optional)
- Retrieve agent information

## Error Handling

- **Validation Errors** (422) — Invalid input data
- **Not Found** (404) — Lead doesn't exist
- **Server Errors** (500) — Unexpected failures
- All errors logged with context for debugging

## Performance & Scalability

- Asynchronous FastAPI endpoints
- Connection pooling for external APIs
- Efficient keyword matching (regex-based)
- Stateless design supports horizontal scaling
- Database queries indexed on LeadID

## Security Considerations

- API key management via environment variables
- Email validation (Pydantic EmailStr)
- Phone number validation (regex)
- CORS configuration (configure for production)
- No sensitive data in logs

## Contributing

- Follow existing code style
- Add tests for new features
- Update README with changes
- Run test suite before committing

## License

SintraPrime Backend — Internal Use Only
