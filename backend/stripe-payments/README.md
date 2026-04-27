# SintraPrime Stripe Payments Module

Complete payment processing and subscription management system using Stripe.

## Features

✅ **Subscription Management**
- Create subscriptions with trial periods
- Upgrade/downgrade tiers with proration
- Cancel subscriptions with refund eligibility
- Automatic trial-to-paid conversion

✅ **Payment Processing**
- Secure checkout sessions
- Multiple payment methods
- Automatic invoice generation
- Refund processing

✅ **Webhook Integration**
- Real-time payment status updates
- Automatic Airtable synchronization
- Failed payment alerts
- Subscription lifecycle events

✅ **Multi-Tier Pricing**
- Starter: $99/month (14-day trial)
- Pro: $499/month (7-day trial)
- Enterprise: Custom pricing (sales conversation)

✅ **Airtable Sync**
- Automatic payment record creation
- Real-time status updates
- Refund tracking
- Deal stage updates

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:

```env
# Stripe API Keys
STRIPE_SECRET_KEY=sk_test_your_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_secret_here

# Price IDs (from Stripe dashboard)
STRIPE_PRICE_STARTER=price_xxx
STRIPE_PRICE_PRO=price_yyy
STRIPE_PRICE_ENTERPRISE=price_zzz

# Airtable
AIRTABLE_BASE_ID=app_xxx
AIRTABLE_API_TOKEN=pat_xxx

# Application
ENVIRONMENT=test
DASHBOARD_URL=https://app.sintraprime.com
API_BASE_URL=http://localhost:8000
```

### 3. Run the Application

```bash
python main.py
```

API will be available at `http://localhost:8000`

## API Endpoints

### Payment Endpoints

#### Create Checkout Session
```
POST /api/checkout
{
  "email": "customer@example.com",
  "tier": "starter",
  "success_url": "https://app.example.com/dashboard",
  "cancel_url": "https://app.example.com/pricing"
}
```

#### Create Subscription
```
POST /api/subscribe
{
  "email": "customer@example.com",
  "tier": "pro",
  "trial_days": 7
}
```

#### Get Subscription Details
```
GET /api/subscription/{subscription_id}
```

#### Upgrade Subscription
```
POST /api/subscription/{subscription_id}/upgrade
{
  "new_tier": "pro",
  "prorated": true
}
```

#### Cancel Subscription
```
POST /api/subscription/{subscription_id}/cancel?at_period_end=false
```

#### Request Refund
```
POST /api/subscription/{subscription_id}/refund
{
  "reason": "requested_by_customer",
  "amount": 9900
}
```

### Webhook Endpoint

```
POST /webhooks/stripe
```

Receives events:
- `payment_intent.succeeded` - Payment completed
- `customer.subscription.updated` - Subscription changed
- `customer.subscription.deleted` - Subscription canceled
- `invoice.paid` - Invoice paid
- `invoice.payment_failed` - Payment failed
- `invoice.upcoming` - Reminder for upcoming invoice

## Testing

### Run Tests

```bash
pytest tests/test_stripe.py -v
```

### Test Checkout Flow

```bash
curl -X POST http://localhost:8000/api/checkout \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "tier": "starter"
  }'
```

### Test with Stripe CLI

```bash
# Listen for webhooks locally
stripe listen --forward-to localhost:8000/webhooks/stripe

# Trigger test events
stripe trigger payment_intent.succeeded
stripe trigger invoice.paid
```

## Testing with Test Cards

Use these card numbers in test mode:

| Card | Status |
|------|--------|
| `4242 4242 4242 4242` | Success |
| `4000 0000 0000 0002` | Decline |
| `5555 5555 5555 4444` | Mastercard |

**Expiry:** Any future date (e.g., 12/25)
**CVC:** Any 3 digits (e.g., 123)

## Project Structure

```
stripe-payments/
├── __init__.py
├── config.py              # Configuration and constants
├── stripe_client.py       # Stripe API wrapper
├── main.py               # FastAPI app entry point
├── requirements.txt      # Python dependencies
├── STRIPE_SETUP.md       # Setup guide
├── README.md            # This file
│
├── models/
│   ├── __init__.py
│   └── subscription.py   # Pydantic models
│
├── api/
│   ├── __init__.py
│   └── routes.py        # FastAPI endpoints
│
├── services/
│   ├── __init__.py
│   ├── subscription_service.py    # Business logic
│   └── airtable_sync.py          # Airtable integration
│
├── webhooks/
│   ├── __init__.py
│   └── webhook_handler.py        # Stripe webhook receiver
│
├── utils/
│   ├── __init__.py
│   └── pricing.py                # Pricing calculations
│
└── tests/
    ├── __init__.py
    └── test_stripe.py            # Unit tests
```

## Integration with Main App

Add to your main FastAPI application:

```python
from fastapi import FastAPI
from stripe_payments.api import router as payment_router
from stripe_payments.webhooks import router as webhook_router

app = FastAPI()

# Include payment routes
app.include_router(payment_router)
app.include_router(webhook_router)
```

## Database Schema

### Airtable - Payments Table

| Field | Type | Required |
|-------|------|----------|
| PaymentID | Text (Primary) | Yes |
| ClientEmail | Email | Yes |
| Tier | Single select | Yes |
| Amount | Number | Yes |
| Frequency | Single select | Yes |
| Status | Single select | Yes |
| NextBillingDate | Date | No |
| TrialEndsAt | Date | No |
| StripeSubscriptionID | Text | Yes |
| StripeCustomerID | Text | Yes |
| CreatedAt | Date | Yes |
| UpdatedAt | Date | No |
| CanceledAt | Date | No |
| RefundAmount | Number | No |

## Pricing Logic

### Tier Pricing

- **Starter:** $99/month
  - Limited legal document reviews (5/month)
  - Basic credit analysis
  - Email support
  - 14-day free trial

- **Pro:** $499/month
  - Unlimited document reviews
  - Advanced credit optimization
  - Autonomous filing (5 cases/month)
  - Priority 24-hour support
  - 7-day free trial

- **Enterprise:** Custom pricing
  - All Pro features plus:
  - White-label client portal
  - Dedicated agent access
  - Custom integrations
  - Phone support
  - No automatic trial (sales conversation)

### Proration Rules

When upgrading mid-cycle:
1. Calculate remaining days in current period
2. Calculate daily rate for both tiers
3. Charge difference immediately
4. Applied as credit on next invoice

Example:
```
Old: Starter $99/month
New: Pro $499/month
Days remaining: 15 days

Daily old: $99/30 = $3.30
Daily new: $499/30 = $16.63
Daily difference: $13.33
Prorated charge: $13.33 × 15 = $200
```

## Webhook Events

All webhook events are:
1. **Verified** - Signature checked against webhook secret
2. **Processed** - Event-specific logic executed
3. **Logged** - Full event details logged
4. **Synced** - Data updated in Airtable
5. **Monitored** - Failures tracked and alerted

## Security

- ✅ Webhook signature verification
- ✅ API key in environment variables only
- ✅ HTTPS required for production
- ✅ No raw card data stored
- ✅ PCI-DSS compliant via Stripe

## Monitoring

### Logs

Check logs for:
- Payment processing status
- Webhook events
- Airtable sync operations
- Error conditions

### Stripe Dashboard

Monitor:
- Customer list
- Subscription status
- Invoice history
- Refund requests
- Failed payments

### Airtable

Check:
- Payment records
- Subscription status
- Trial periods
- Refund amounts

## Error Handling

The system handles:
- ✅ Invalid card numbers
- ✅ Expired cards
- ✅ Insufficient funds
- ✅ Network failures
- ✅ Webhook delivery failures
- ✅ Airtable sync errors

All errors are logged and can trigger alerts.

## Troubleshooting

### Webhook Not Received

1. Check endpoint URL is correct
2. Verify webhook secret in config
3. Ensure server is running and accessible
4. Check Stripe Dashboard > Webhooks > Events

### Subscription Not Created

1. Verify price IDs are correct
2. Check customer email is valid
3. Ensure API key is correct
4. Check logs for detailed error

### Payment Failed

1. Use valid test card: `4242 4242 4242 4242`
2. Verify expiry date is in future
3. Check CVC is 3 digits
4. See Stripe Dashboard for decline reason

## Documentation

- `STRIPE_SETUP.md` - Complete setup guide
- API docs - Available at `/api/docs` (Swagger UI)
- Code comments - Inline documentation

## Contributing

To add features:

1. Add tests in `tests/test_stripe.py`
2. Implement feature
3. Update documentation
4. Run tests: `pytest tests/ -v`

## License

SintraPrime - All rights reserved

## Support

For issues or questions:
1. Check `STRIPE_SETUP.md`
2. Review code comments
3. Check logs for errors
4. Contact dev team

---

**Last Updated:** 2024
**Version:** 1.0.0
