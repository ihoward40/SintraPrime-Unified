# IKE BOT – Trust Automation Engine

A comprehensive backend API for trust automation, enforcement actions, and beneficiary management.

## Features

- 🔐 **Full CRUD APIs** - Beneficiaries and credit disputes with validation
- 📊 **Supabase Integration** - PostgreSQL database with migrations
- 🔗 **Webhook Hub** - Stripe, Make.com, SendGrid, Postmark integrations
- 🤖 **OpenAI Agent-Ready** - Tool definitions for AI agent integration
- 📝 **Audit Logging** - Complete request/response logging with trace IDs
- ⚡ **Production-Ready** - Error handling, pagination, filtering, sorting

## Setup

### Prerequisites
- Node.js 18+ 
- npm or yarn
- Supabase account (for database)

### Installation

1. Clone this repo
```bash
git clone https://github.com/ihoward40/ike-bot.git
cd ike-bot
```

2. Install dependencies
```bash
npm install
```

3. Create `.env` file
```env
PORT=3000
NODE_ENV=development
LOG_LEVEL=info

# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# Stripe (for webhooks)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

4. Run database migrations
```bash
npm run db:init
npm run db:seed
```

5. Start development server
```bash
npm run dev
```

6. Build for production
```bash
npm run build
npm start
```

## API Documentation

### Beneficiaries

#### List Beneficiaries
```http
GET /api/beneficiaries
```

Query parameters:
- `page` (number): Page number (default: 1)
- `limit` (number): Results per page (default: 10, max: 100)
- `sortBy` (string): Field to sort by (default: created_at)
- `sortOrder` (string): asc or desc (default: desc)
- `search` (string): Search by name or email

Example response:
```json
{
  "data": [
    {
      "id": "uuid",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john@example.com",
      "phone": "555-0100",
      "relationship": "Primary",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 50,
    "totalPages": 5
  }
}
```

#### Get Beneficiary
```http
GET /api/beneficiaries/:id
```

#### Create Beneficiary
```http
POST /api/beneficiaries
Content-Type: application/json

{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "phone": "555-0100",
  "relationship": "Primary"
}
```

#### Update Beneficiary
```http
PUT /api/beneficiaries/:id
Content-Type: application/json

{
  "phone": "555-0200"
}
```

#### Delete Beneficiary
```http
DELETE /api/beneficiaries/:id
```

### Credit Disputes

#### List Credit Disputes
```http
GET /api/credit-disputes
```

Query parameters:
- `page` (number): Page number
- `limit` (number): Results per page
- `sortBy` (string): Field to sort by
- `sortOrder` (string): asc or desc
- `status` (string): Filter by status (pending, submitted, investigating, resolved, rejected)
- `beneficiary_id` (string): Filter by beneficiary UUID

#### Get Credit Dispute
```http
GET /api/credit-disputes/:id
```

#### Create Credit Dispute
```http
POST /api/credit-disputes
Content-Type: application/json

{
  "beneficiary_id": "uuid",
  "creditor_name": "Example Credit Corp",
  "dispute_reason": "This account does not belong to me",
  "dispute_type": "not_mine"
}
```

Dispute types: `identity_theft`, `not_mine`, `inaccurate`, `duplicate`, `paid`, `other`

#### Update Credit Dispute
```http
PUT /api/credit-disputes/:id
Content-Type: application/json

{
  "status": "resolved",
  "resolution_notes": "Successfully removed from credit report"
}
```

#### Delete Credit Dispute
```http
DELETE /api/credit-disputes/:id
```

## Webhooks

All webhook endpoints accept POST requests.

### Stripe Webhook
```http
POST /webhooks/stripe
```
Handles Stripe events with signature verification. Supported events:
- `payment_intent.succeeded`
- `payment_intent.payment_failed`
- `charge.succeeded`
- `charge.failed`
- `invoice.payment_succeeded`
- `invoice.payment_failed`

### Make.com Webhook
```http
POST /webhooks/make
```
Receives automation triggers from Make.com scenarios.

Example payload:
```json
{
  "action": "create_beneficiary",
  "data": {
    "first_name": "Jane",
    "last_name": "Smith",
    "email": "jane@example.com"
  }
}
```

Supported actions: `create_beneficiary`, `create_dispute`, `create_enforcement_packet`, `billing_alert`

### SendGrid Webhook
```http
POST /webhooks/sendgrid
```
Processes SendGrid email events (delivered, bounced, opened, clicked).

### Postmark Webhook
```http
POST /webhooks/postmark
```
Processes Postmark email events.

### Inbound Email
```http
POST /webhooks/inbound-email
```
Handles inbound emails from SendGrid or Postmark.

### Billing Alert
```http
POST /webhooks/billing-alert
```
Generic billing alert endpoint.

Example payload:
```json
{
  "source": "payment-gateway",
  "alert_type": "payment_overdue",
  "beneficiary_id": "uuid",
  "amount": 150.00,
  "currency": "USD",
  "status": "pending",
  "severity": "warn",
  "message": "Payment is 30 days overdue"
}
```

## OpenAI Agent Tools

Tool definitions are available in `/agent-tools/` directory. Use the utility functions to load them:

```typescript
import { loadAllTools, getOpenAITools, getToolByName } from './src/utils/tools';

// Get all tools formatted for OpenAI API
const tools = getOpenAITools();

// Get specific tool
const createBeneficiaryTool = getToolByName('create_beneficiary');
```

Available tools:
- `list_beneficiaries` - List all beneficiaries with filtering
- `create_beneficiary` - Create a new beneficiary
- `list_credit_disputes` - List credit disputes
- `create_credit_dispute` - Create a new credit dispute
- `run_enforcement_packet` - Create enforcement packet (future implementation)

## Database

### Migrations

Migrations are stored in `supabase/migrations/`. 

Run migrations:
```bash
npm run db:init      # Initialize schema
npm run db:seed      # Seed test data
npm run db:migrate   # Run all migrations
npm run db:reset     # Reset database (caution!)
```

See [supabase/README.md](./supabase/README.md) for detailed migration documentation.

### Tables

- `beneficiaries` - Trust beneficiaries
- `credit_disputes` - Credit dispute tracking
- `billing_events` - Payment and billing events
- `enforcement_packets` - Enforcement actions (UCC liens, FOIA, etc.)
- `agent_logs` - Audit trail and request logs

## Logging & Audit Trail

Every API request is logged with:
- **Trace ID** - Unique identifier for each request
- **Correlation ID** - Groups related requests
- **Request/Response logging** - Method, path, status, duration
- **Error logging** - Full stack traces
- **Database persistence** - All logs saved to `agent_logs` table

Access trace IDs via response headers:
```
X-Trace-Id: uuid
X-Correlation-Id: uuid
```

## Development

### Project Structure
```
ike-bot/
├── src/
│   ├── config/          # Configuration (Supabase, logger)
│   ├── controllers/     # Request handlers
│   ├── services/        # Business logic
│   ├── models/          # Zod schemas & types
│   ├── middleware/      # Express middleware
│   ├── routes/          # API routes
│   ├── webhooks/        # Webhook handlers
│   ├── utils/           # Utility functions
│   └── queue/           # Job queue (future)
├── agent-tools/         # OpenAI agent tool definitions
├── supabase/            # Database migrations
└── dist/                # Compiled output
```

### Scripts

- `npm run dev` - Start development server with hot reload
- `npm run build` - Compile TypeScript to JavaScript
- `npm start` - Run production server
- `npm run db:init` - Initialize database schema
- `npm run db:seed` - Seed test data
- `npm run db:migrate` - Run migrations
- `npm run db:reset` - Reset database

## Technology Stack

- **Runtime**: Node.js
- **Language**: TypeScript
- **Framework**: Express.js
- **Database**: PostgreSQL (via Supabase)
- **Validation**: Zod
- **Logging**: Pino
- **Payments**: Stripe
- **ORM**: Supabase Client

## Security

- Input validation with Zod schemas
- Stripe webhook signature verification
- Structured error handling
- SQL injection protection via Supabase client
- CORS enabled
- Request logging and audit trails

## Future Enhancements

- [ ] Job queue for background processing (Bull/BullMQ)
- [ ] Authentication & authorization (JWT)
- [ ] Rate limiting
- [ ] API documentation with Swagger/OpenAPI
- [ ] Enforcement packet generation
- [ ] Document management
- [ ] Email notifications
- [ ] Unit and integration tests

## License

MIT

## Support

For issues or questions, please open an issue on GitHub.
