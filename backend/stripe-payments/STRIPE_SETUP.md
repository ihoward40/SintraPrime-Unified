# Stripe Setup Guide for SintraPrime

Complete guide to setting up Stripe payment processing for SintraPrime.

## Overview

This document explains how to:
1. Create Stripe products and pricing
2. Configure API keys
3. Set up webhooks
4. Test payment flows

## 1. Getting Stripe API Keys

### Step 1: Create a Stripe Account

1. Go to https://dashboard.stripe.com
2. Sign up or log in to your account
3. Complete your account setup

### Step 2: Get API Keys

1. Go to Dashboard > Developers > API Keys
2. You'll see two keys:
   - **Publishable Key** (starts with `pk_`) - Safe to use in frontend
   - **Secret Key** (starts with `sk_`) - Keep this secret, use only on backend

3. For testing, use test keys (they have "test" in them)
4. For production, use live keys (they have "live" in them)

### Step 3: Save Keys to Environment

Create a `.env` file in the stripe-payments directory:

```env
# Stripe API Keys (Test Keys for development)
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here

# Webhook Secret (generated after creating webhook)
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here

# Application settings
ENVIRONMENT=test
AIRTABLE_BASE_ID=appYourBaseId
AIRTABLE_API_TOKEN=patYourToken
```

## 2. Creating Products and Prices

### Pricing Structure

SintraPrime offers three tiers:

| Tier | Price | Trial | Features |
|------|-------|-------|----------|
| **Starter** | $99/month | 14 days | Limited reviews, basic analysis, email support |
| **Pro** | $499/month | 7 days | Unlimited reviews, advanced optimization, 5 filings/month, 24h support |
| **Enterprise** | Custom | None | All Pro + white-label, dedicated agent, custom integrations, phone support |

### Creating Products in Stripe Dashboard

1. Go to Dashboard > Products
2. Click "Create Product"

#### Starter Product

- **Name:** SintraPrime Starter
- **Description:** Limited legal document reviews and basic credit analysis
- **Image:** (Optional - add SintraPrime logo)

3. Click "Create Product"
4. In the pricing section, click "Add a Price"
   - **Billing Period:** Monthly
   - **Price:** $99.00 USD
   - **Check:** "This is a recurring price"
   - **Trial Period:** 14 days
   - Click "Save Price"

5. Note the Price ID (format: `price_xxxxx`) - you'll need this

#### Pro Product

1. Create another product:
   - **Name:** SintraPrime Pro
   - **Description:** Unlimited document reviews with advanced features
   
2. Add price:
   - **Price:** $499.00 USD
   - **Billing Period:** Monthly
   - **Trial Period:** 7 days

#### Enterprise Product

1. Create final product:
   - **Name:** SintraPrime Enterprise
   - **Description:** Custom solution with white-label and dedicated support

2. Add price:
   - **Billing Mode:** Custom pricing (price left blank)
   - No trial period

### Configure Price IDs in Environment

Add the price IDs to your `.env` file:

```env
STRIPE_PRICE_STARTER=price_1234567890abc
STRIPE_PRICE_PRO=price_0987654321xyz
STRIPE_PRICE_ENTERPRISE=price_enterprise_abc
```

## 3. Webhook Configuration

Webhooks allow Stripe to notify your application of payment events.

### Create Webhook Endpoint

1. Go to Dashboard > Developers > Webhooks
2. Click "Add endpoint"
3. **Endpoint URL:** `https://your-domain.com/webhooks/stripe`
   - For local testing: Use ngrok to expose local server
   - Example: `https://abc123.ngrok.io/webhooks/stripe`

4. Select events to listen for:
   - ✓ `payment_intent.succeeded`
   - ✓ `payment_intent.payment_failed`
   - ✓ `customer.subscription.created`
   - ✓ `customer.subscription.updated`
   - ✓ `customer.subscription.deleted`
   - ✓ `invoice.paid`
   - ✓ `invoice.payment_failed`
   - ✓ `invoice.upcoming`

5. Click "Create endpoint"
6. Click on the endpoint to view details
7. Copy the "Signing secret" (starts with `whsec_`)
8. Save to `.env`:
   ```env
   STRIPE_WEBHOOK_SECRET=whsec_your_secret_here
   ```

### Testing Webhooks Locally

Use ngrok to expose your local server:

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com

# Start ngrok
ngrok http 8000

# Copy the HTTPS URL and use in webhook settings
```

Use Stripe CLI for local testing:

```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe  # macOS

# Login to your Stripe account
stripe login

# Listen for webhooks
stripe listen --forward-to localhost:8000/webhooks/stripe

# Trigger test events
stripe trigger invoice.paid
stripe trigger payment_intent.succeeded
```

## 4. Testing Payment Flows

### Test Card Numbers

Use these cards in test mode (will be declined in production):

| Card | Status | Use Case |
|------|--------|----------|
| `4242 4242 4242 4242` | Success | Standard payment success |
| `4000 0000 0000 0002` | Decline | Test payment decline |
| `5555 5555 5555 4444` | Success | Mastercard test |
| `3782 822463 10005` | Success | American Express test |

**Expiry:** Any future date (e.g., 12/25)  
**CVC:** Any 3 digits (e.g., 123)

### Test Checkout Flow

```bash
# 1. Start your backend
python -m uvicorn stripe_payments.main:app --reload

# 2. Create a checkout session
curl -X POST http://localhost:8000/api/checkout \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@example.com",
    "tier": "starter"
  }'

# 3. Visit the returned checkout_url
# 4. Use test card 4242 4242 4242 4242
```

### Test Subscription Creation

```bash
curl -X POST http://localhost:8000/api/subscribe \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@example.com",
    "tier": "pro",
    "trial_days": 7
  }'
```

### Test Upgrade

```bash
curl -X POST http://localhost:8000/api/subscription/sub_test123/upgrade \
  -H "Content-Type: application/json" \
  -d '{
    "new_tier": "pro",
    "prorated": true
  }'
```

## 5. Implementation Guide

### Adding Stripe to Your FastAPI App

```python
from fastapi import FastAPI
from stripe_payments.api import router as payment_router
from stripe_payments.webhooks import router as webhook_router

app = FastAPI()

# Include payment routes
app.include_router(payment_router)
app.include_router(webhook_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Creating a Subscription Programmatically

```python
from stripe_payments.services.subscription_service import subscription_service

# Create subscription
subscription = await subscription_service.create_subscription(
    email="customer@example.com",
    tier="pro",
    trial_days=7,
    name="John Doe"
)

print(f"Subscription ID: {subscription.subscription_id}")
print(f"Status: {subscription.status}")
print(f"Trial ends: {subscription.trial_end}")
```

### Handling Webhooks

The webhook handler automatically:
1. Verifies Stripe's signature
2. Routes events to appropriate handlers
3. Syncs subscription data to Airtable
4. Logs all events

### Syncing to Airtable

Payment data is automatically synced to Airtable when:
- Subscription is created
- Subscription is updated
- Invoice is paid
- Payment fails

Required Airtable fields in "Payments" table:
- `PaymentID` (Primary key - Stripe subscription ID)
- `ClientEmail` (Email address)
- `Tier` (starter/pro/enterprise)
- `Amount` (Price in cents)
- `Frequency` (Monthly/Annual)
- `Status` (Active/Trialing/Canceled/Failed)
- `NextBillingDate` (ISO date)
- `StripeSubscriptionID` (Subscription ID)
- `StripeCustomerID` (Customer ID)

## 6. Monitoring and Troubleshooting

### Viewing Logs

Check webhook delivery status in Stripe Dashboard:
1. Go to Developers > Webhooks
2. Click on your endpoint
3. View "Events" tab
4. Click any event to see payload and response

### Common Issues

#### Webhook Not Received
- Check endpoint URL is correct and publicly accessible
- Verify signature secret is correct
- Check firewall/proxy settings

#### Payment Intent Fails
- Verify test card is formatted correctly: `4242 4242 4242 4242`
- Check expiration date is in future
- Verify CVC is 3 digits

#### Subscription Not Created
- Ensure price IDs are correct
- Verify customer doesn't already exist
- Check Stripe account is in live mode (test vs live)

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("stripe_payments")
logger.setLevel(logging.DEBUG)
```

## 7. Production Deployment

### Before Going Live

1. **Switch to Live Keys**
   - Get live API keys from Stripe Dashboard
   - Update `.env` with live keys

2. **Update Webhook URL**
   - Change webhook endpoint to production domain
   - Example: `https://api.sintraprime.com/webhooks/stripe`

3. **Enable SSL/TLS**
   - Ensure your domain uses HTTPS
   - Required for webhook signature verification

4. **Test with Live Cards**
   - Use real card with small amount (test transactions)
   - Verify webhook is delivered to production endpoint

5. **Monitor Failures**
   - Set up alerts for failed payments
   - Monitor webhook delivery status
   - Set up email notifications

### Monitoring

```python
# Monitor payment failures
from stripe_payments.services.airtable_sync import airtable_sync_service

# Failures are automatically logged and synced to Airtable
# Set up email alerts for high failure rates
```

## 8. Pricing Rules and Prorations

### Upgrade Prorations

When upgrading mid-cycle:
- Calculate remaining days in billing period
- Charge prorated difference immediately
- No refunds for upgrades

Example:
- Current: Starter ($99/month)
- Upgrade to: Pro ($499/month) after 15 days
- Prorated credit: ~$200 applied to next invoice

### Trial Periods

- **Starter:** 14-day free trial
- **Pro:** 7-day free trial
- **Enterprise:** Sales conversation (no automatic trial)

Trial periods:
- Start on subscription creation
- Don't charge during trial
- Require valid payment method
- Can be canceled during trial (no charge)

### Refund Policy

- **Window:** 30 days from subscription start
- **Amount:** 100% refund if within window
- **Process:** Manual review + approval

## 9. Compliance and Security

### PCI Compliance

- Never store raw card data
- Stripe handles all payment processing
- Use tokenized payment methods only

### Data Security

- Keep `STRIPE_SECRET_KEY` in environment variables only
- Use HTTPS for all API endpoints
- Verify webhook signatures
- Log sensitive data carefully

### GDPR Compliance

- Stripe is GDPR compliant
- Implement data deletion on customer request
- Log all access to customer payment data

## 10. API Reference

### Create Checkout Session

```
POST /api/checkout
Content-Type: application/json

{
  "email": "customer@example.com",
  "tier": "pro",
  "success_url": "https://app.example.com/dashboard",
  "cancel_url": "https://app.example.com/pricing"
}

Response:
{
  "session_id": "cs_test_...",
  "checkout_url": "https://checkout.stripe.com/...",
  "expires_at": 1234567890
}
```

### Create Subscription

```
POST /api/subscribe
Content-Type: application/json

{
  "email": "customer@example.com",
  "tier": "pro",
  "trial_days": 7
}

Response:
{
  "subscription_id": "sub_...",
  "status": "trialing",
  "tier": "pro",
  "current_period_end": "2024-02-15T12:00:00",
  "trial_end": "2024-02-08T12:00:00"
}
```

### Get Subscription

```
GET /api/subscription/{subscription_id}

Response:
{
  "subscription_id": "sub_...",
  "status": "active",
  "tier": "pro",
  "current_period_end": "2024-02-15T12:00:00",
  "trial_end": null
}
```

### Upgrade Subscription

```
POST /api/subscription/{subscription_id}/upgrade
Content-Type: application/json

{
  "new_tier": "enterprise",
  "prorated": true
}

Response:
{
  "subscription_id": "sub_...",
  "new_tier": "enterprise",
  "prorated_credit": 15000,
  "new_price": 0,
  "next_charge_date": "2024-02-15T12:00:00"
}
```

### Cancel Subscription

```
POST /api/subscription/{subscription_id}/cancel?at_period_end=false

Response:
{
  "subscription_id": "sub_...",
  "status": "canceled",
  "canceled_at": "2024-01-20T12:00:00",
  "refund_eligible": true,
  "refund_amount": 9900
}
```

## Support

For questions about:
- **Stripe API:** https://stripe.com/docs
- **SintraPrime Integration:** Contact dev team
- **Airtable Sync:** Check Airtable configuration

Last Updated: 2024
