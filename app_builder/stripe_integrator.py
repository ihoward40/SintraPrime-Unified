"""
StripeIntegrator — Stripe Payment Integration for SintraPrime App Builder
=========================================================================
Generates Stripe configuration, payment forms, subscription products,
and invoice templates for legal and financial applications.

All keys are loaded from environment variables — NO hardcoded secrets.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from .app_types import StripeConfig


class StripeIntegrator:
    """
    Stripe payment integration builder for SintraPrime apps.

    Supports:
    - Legal billing: retainers, flat fees, hourly billing
    - Subscription products for SaaS apps
    - Client billing portals
    - Professional invoice templates
    - Webhook configuration

    Config loads from environment:
    - STRIPE_SECRET_KEY: server-side secret key
    - STRIPE_PUBLISHABLE_KEY: client-side publishable key
    - STRIPE_WEBHOOK_SECRET: webhook signing secret
    - STRIPE_PRICE_ID: default price ID (optional)
    """

    def __init__(self):
        self._secret_key = os.environ.get("STRIPE_SECRET_KEY", "sk_test_placeholder")
        self._pub_key = os.environ.get("STRIPE_PUBLISHABLE_KEY", "pk_test_placeholder")
        self._webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")
        self._configs: Dict[str, StripeConfig] = {}
        self._products: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Setup Methods
    # ------------------------------------------------------------------

    def setup_legal_billing(
        self,
        firm_name: str,
        practice_areas: List[str],
    ) -> StripeConfig:
        """
        Set up complete Stripe billing for a law firm.

        Creates products for:
        - Initial consultation
        - Retainer agreement
        - Flat-fee services per practice area
        """
        products = []
        subscription_products = []

        # Consultation product
        products.append({
            "id": f"prod_consult_{uuid.uuid4().hex[:8]}",
            "name": f"{firm_name} — Initial Consultation",
            "amount": 25000,  # $250.00 in cents
            "currency": "usd",
            "type": "one_time",
            "description": "30-minute legal consultation",
        })

        # Practice area flat fees
        flat_fees = {
            "estate_planning": 150000,   # $1,500
            "trust_formation": 200000,    # $2,000
            "will_preparation": 75000,    # $750
            "probate": 350000,           # $3,500
            "debt_settlement": 100000,   # $1,000
            "business_formation": 125000, # $1,250
            "contract_review": 50000,    # $500
        }

        for area in practice_areas:
            area_key = area.lower().replace(" ", "_")
            amount = flat_fees.get(area_key, 100000)
            products.append({
                "id": f"prod_{area_key}_{uuid.uuid4().hex[:8]}",
                "name": f"{firm_name} — {area}",
                "amount": amount,
                "currency": "usd",
                "type": "one_time",
                "description": f"Flat-fee service: {area}",
            })

        # Monthly retainer subscription
        subscription_products.append({
            "id": f"prod_retainer_{uuid.uuid4().hex[:8]}",
            "name": f"{firm_name} — Monthly Retainer",
            "amount": 50000,  # $500/month
            "currency": "usd",
            "interval": "month",
            "type": "subscription",
            "features": [
                "Unlimited email consultations",
                "Monthly legal review",
                "Document review (up to 5/month)",
                "Priority scheduling",
            ],
        })

        webhook_events = [
            "payment_intent.succeeded",
            "payment_intent.payment_failed",
            "customer.subscription.created",
            "customer.subscription.deleted",
            "invoice.paid",
            "invoice.payment_failed",
        ]

        config = StripeConfig(
            firm_name=firm_name,
            products=products,
            subscription_products=subscription_products,
            customer_portal_enabled=True,
            invoice_prefix=firm_name[:3].upper(),
            currency="usd",
            webhook_events=webhook_events,
        )

        config_id = uuid.uuid4().hex[:8]
        self._configs[config_id] = config
        return config

    def create_subscription_product(
        self,
        name: str,
        price_monthly: float,
        features: List[str],
    ) -> str:
        """
        Create a subscription product definition.
        Returns a mock product_id (real creation requires Stripe API call).

        In production: use stripe.Product.create() and stripe.Price.create()
        """
        product_id = f"prod_{uuid.uuid4().hex[:16]}"
        price_id = f"price_{uuid.uuid4().hex[:16]}"

        self._products[product_id] = {
            "id": product_id,
            "name": name,
            "price_monthly": price_monthly,
            "price_monthly_cents": int(price_monthly * 100),
            "price_id": price_id,
            "features": features,
            "currency": "usd",
            "interval": "month",
            "stripe_config": {
                "product": {
                    "name": name,
                    "type": "service",
                    "metadata": {"source": "sintra_prime"},
                },
                "price": {
                    "unit_amount": int(price_monthly * 100),
                    "currency": "usd",
                    "recurring": {"interval": "month"},
                },
            },
        }
        return product_id

    def setup_flat_fee_product(self, name: str, amount: float) -> str:
        """Create a one-time flat-fee product. Returns product_id."""
        product_id = f"prod_{uuid.uuid4().hex[:16]}"
        self._products[product_id] = {
            "id": product_id,
            "name": name,
            "amount": amount,
            "amount_cents": int(amount * 100),
            "type": "one_time",
            "currency": "usd",
        }
        return product_id

    def setup_retainer(self, name: str, monthly_amount: float) -> str:
        """Create a recurring monthly retainer. Returns product_id."""
        product_id = f"prod_{uuid.uuid4().hex[:16]}"
        self._products[product_id] = {
            "id": product_id,
            "name": name,
            "monthly_amount": monthly_amount,
            "monthly_amount_cents": int(monthly_amount * 100),
            "type": "subscription",
            "interval": "month",
            "currency": "usd",
        }
        return product_id

    # ------------------------------------------------------------------
    # HTML Generators
    # ------------------------------------------------------------------

    def generate_payment_form(self, product_id: str) -> str:
        """Generate a Stripe-ready payment form HTML."""
        product = self._products.get(product_id, {
            "name": "Legal Service",
            "amount": 99.00,
            "type": "one_time",
        })

        product_name = product.get("name", "Service")
        amount = product.get("amount", product.get("monthly_amount", 99.00))
        is_subscription = product.get("type") == "subscription"
        button_text = "Subscribe Now" if is_subscription else "Pay Securely"
        interval = " / month" if is_subscription else ""

        return f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Payment — {product_name}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://js.stripe.com/v3/"></script>
  <style>
    body {{ font-family: 'Inter', sans-serif; }}
    #payment-element {{ margin: 1.5rem 0; }}
    .StripeElement {{ padding: 12px; border: 1px solid #e5e7eb; border-radius: 8px; }}
    #submit:disabled {{ opacity: 0.6; cursor: not-allowed; }}
  </style>
</head>
<body class="min-h-screen bg-gradient-to-br from-blue-900 to-indigo-900 flex items-center justify-center p-4">
  <div class="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
    <div class="text-center mb-8">
      <h1 class="text-2xl font-bold text-gray-900">{product_name}</h1>
      <p class="text-4xl font-bold text-blue-700 mt-2">${amount:,.2f}<span class="text-lg text-gray-400 font-normal">{interval}</span></p>
      <p class="text-sm text-gray-500 mt-1">Secure payment powered by Stripe</p>
    </div>

    <form id="payment-form">
      <div class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
        <input type="text" id="cardholder-name" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Jane Doe" required/>
      </div>
      <div class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
        <input type="email" id="email" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="jane@example.com" required/>
      </div>
      <div id="payment-element" class="mb-4">
        <!-- Stripe Payment Element will mount here -->
      </div>

      <button id="submit" type="submit" class="w-full bg-blue-700 hover:bg-blue-800 text-white font-bold py-3 px-6 rounded-lg transition">
        🔒 {button_text}
      </button>

      <div id="error-message" class="mt-4 text-red-600 text-sm hidden"></div>
      <div id="success-message" class="mt-4 text-green-600 text-sm hidden">✅ Payment successful! Confirmation sent to your email.</div>

      <p class="text-xs text-gray-400 text-center mt-4">
        🔒 256-bit SSL encrypted. Your information is secure. By paying, you agree to our Terms of Service.
      </p>
    </form>
  </div>

  <script>
    const stripe = Stripe('{self._pub_key}');
    let elements;

    async function initializeStripe() {{
      const response = await fetch('/api/create-payment-intent', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{
          amount: {int(amount * 100)},
          currency: 'usd',
          product_id: '{product_id}',
          is_subscription: {'true' if is_subscription else 'false'}
        }})
      }});
      const {{ clientSecret }} = await response.json();

      elements = stripe.elements({{ clientSecret }});
      const paymentElement = elements.create('payment');
      paymentElement.mount('#payment-element');
    }}

    document.getElementById('payment-form').addEventListener('submit', async function(e) {{
      e.preventDefault();
      const btn = document.getElementById('submit');
      btn.disabled = true;
      btn.textContent = 'Processing...';

      const {{ error }} = await stripe.confirmPayment({{
        elements,
        confirmParams: {{
          return_url: window.location.origin + '/payment-success',
          payment_method_data: {{
            billing_details: {{
              name: document.getElementById('cardholder-name').value,
              email: document.getElementById('email').value,
            }}
          }}
        }}
      }});

      if (error) {{
        document.getElementById('error-message').textContent = error.message;
        document.getElementById('error-message').classList.remove('hidden');
        btn.disabled = false;
        btn.textContent = '{button_text}';
      }}
    }});

    initializeStripe().catch(console.error);
  </script>
</body>
</html>"""

    def setup_client_portal(self, stripe_config: StripeConfig) -> str:
        """
        Return the URL/HTML snippet to launch the Stripe Customer Portal.
        In production this redirects to a stripe.com hosted portal.
        """
        return f"""<!-- Stripe Customer Portal for {stripe_config.firm_name} -->
<div class="card bg-base-100 shadow-xl p-6">
  <h3 class="text-lg font-bold text-primary mb-2">Manage Your Billing</h3>
  <p class="text-gray-600 mb-4">Update payment methods, view invoices, and manage subscriptions.</p>
  <a href="/api/create-portal-session" class="btn btn-primary">
    💳 Open Billing Portal
  </a>
</div>

<script>
// POST to your server to create a portal session
async function openPortal() {{
  const res = await fetch('/api/create-portal-session', {{method: 'POST'}});
  const {{ url }} = await res.json();
  window.location.href = url;
}}
</script>"""

    def generate_invoice_template(self, firm_details: Dict[str, Any]) -> str:
        """Generate a professional HTML invoice template."""
        firm_name = firm_details.get("name", "Law Firm")
        firm_address = firm_details.get("address", "123 Main St, Newark, NJ 07102")
        firm_phone = firm_details.get("phone", "(555) 000-0000")
        firm_email = firm_details.get("email", "billing@lawfirm.com")
        firm_website = firm_details.get("website", "www.lawfirm.com")
        bar_number = firm_details.get("bar_number", "")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>Invoice — {firm_name}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Inter', sans-serif; color: #1a202c; background: #fff; font-size: 14px; line-height: 1.6; }}
    .container {{ max-width: 800px; margin: 0 auto; padding: 40px; }}
    .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 40px; }}
    .firm-name {{ font-size: 28px; font-weight: 700; color: #1e40af; }}
    .invoice-title {{ font-size: 32px; font-weight: 700; color: #1e40af; text-align: right; }}
    .invoice-number {{ color: #6b7280; font-size: 13px; text-align: right; }}
    .divider {{ height: 3px; background: linear-gradient(90deg, #1e40af, #7c3aed); margin: 20px 0; border-radius: 2px; }}
    .billing-section {{ display: flex; justify-content: space-between; margin: 30px 0; }}
    .billing-box {{ width: 45%; }}
    .billing-box h4 {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; color: #6b7280; margin-bottom: 8px; }}
    .billing-box p {{ font-size: 14px; color: #1a202c; line-height: 1.5; }}
    table {{ width: 100%; border-collapse: collapse; margin: 30px 0; }}
    th {{ background: #1e40af; color: white; padding: 12px 16px; text-align: left; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; }}
    td {{ padding: 12px 16px; border-bottom: 1px solid #e5e7eb; }}
    tr:last-child td {{ border-bottom: none; }}
    tr:nth-child(even) {{ background: #f9fafb; }}
    .totals {{ margin-left: auto; width: 300px; }}
    .total-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #e5e7eb; }}
    .grand-total {{ display: flex; justify-content: space-between; padding: 12px 0; font-weight: 700; font-size: 18px; color: #1e40af; border-top: 2px solid #1e40af; margin-top: 8px; }}
    .footer {{ margin-top: 50px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 12px; color: #6b7280; text-align: center; }}
    .payment-terms {{ background: #eff6ff; border-left: 4px solid #1e40af; padding: 16px; margin: 20px 0; border-radius: 0 8px 8px 0; }}
    @media print {{ .container {{ padding: 20px; }} }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <div class="firm-name">{firm_name}</div>
        <div style="color:#6b7280;margin-top:8px;line-height:1.8;">
          {firm_address}<br/>
          {firm_phone} | {firm_email}<br/>
          {firm_website}
          {f'<br/>Bar #: {bar_number}' if bar_number else ''}
        </div>
      </div>
      <div>
        <div class="invoice-title">INVOICE</div>
        <div class="invoice-number">
          Invoice #: {{{{invoice_number}}}}<br/>
          Date: {{{{invoice_date}}}}<br/>
          Due: {{{{due_date}}}}
        </div>
      </div>
    </div>

    <div class="divider"></div>

    <div class="billing-section">
      <div class="billing-box">
        <h4>Bill To</h4>
        <p>
          <strong>{{{{client_name}}}}</strong><br/>
          {{{{client_address}}}}<br/>
          {{{{client_email}}}}
        </p>
      </div>
      <div class="billing-box" style="text-align:right;">
        <h4>Matter</h4>
        <p>
          {{{{matter_title}}}}<br/>
          Matter #: {{{{matter_number}}}}<br/>
          Attorney: {{{{attorney_name}}}}
        </p>
      </div>
    </div>

    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Description</th>
          <th>Hours / Units</th>
          <th>Rate</th>
          <th>Amount</th>
        </tr>
      </thead>
      <tbody>
        {{{{#line_items}}}}
        <tr>
          <td>{{{{date}}}}</td>
          <td>{{{{description}}}}</td>
          <td>{{{{hours}}}}</td>
          <td>${{{{rate}}}}</td>
          <td>${{{{amount}}}}</td>
        </tr>
        {{{{/line_items}}}}
      </tbody>
    </table>

    <div class="totals">
      <div class="total-row"><span>Subtotal</span><span>${{{{subtotal}}}}</span></div>
      <div class="total-row"><span>Tax ({{{{tax_rate}}}}%)</span><span>${{{{tax}}}}</span></div>
      <div class="total-row"><span>Previous Balance</span><span>${{{{previous_balance}}}}</span></div>
      <div class="grand-total"><span>TOTAL DUE</span><span>${{{{total_due}}}}</span></div>
    </div>

    <div class="payment-terms">
      <strong>Payment Terms:</strong> Net 30. Please make payment within 30 days of invoice date.<br/>
      <strong>Payment Methods:</strong> Check, ACH, Zelle, or credit card (3% fee applies).<br/>
      Make checks payable to: <strong>{firm_name}</strong>
    </div>

    <div class="footer">
      <p>Thank you for trusting {firm_name} with your legal needs.</p>
      <p>Questions? Contact us at {firm_email} | {firm_phone}</p>
      <p style="margin-top:8px;font-size:11px;">This invoice constitutes a statement of professional services rendered under attorney-client privilege.</p>
    </div>
  </div>
</body>
</html>"""

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        return self._products.get(product_id)

    def list_products(self) -> List[Dict[str, Any]]:
        return list(self._products.values())

    def generate_webhook_handler(self) -> str:
        """Generate a FastAPI webhook handler for Stripe events."""
        return '''"""
Stripe Webhook Handler — SintraPrime
"""
import os
import stripe
from fastapi import APIRouter, HTTPException, Request

router = APIRouter()
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
webhook_secret = os.environ["STRIPE_WEBHOOK_SECRET"]


@router.post("/webhooks/stripe", tags=["stripe"])
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    handlers = {
        "payment_intent.succeeded": handle_payment_succeeded,
        "customer.subscription.created": handle_subscription_created,
        "customer.subscription.deleted": handle_subscription_cancelled,
        "invoice.paid": handle_invoice_paid,
        "invoice.payment_failed": handle_invoice_failed,
    }

    handler = handlers.get(event["type"])
    if handler:
        await handler(event["data"]["object"])

    return {"status": "ok"}


async def handle_payment_succeeded(payment_intent):
    # TODO: Update payment status in DB, send confirmation email
    print(f"Payment succeeded: {payment_intent['id']}")

async def handle_subscription_created(subscription):
    # TODO: Activate user subscription in DB
    print(f"Subscription created: {subscription['id']}")

async def handle_subscription_cancelled(subscription):
    # TODO: Deactivate user subscription in DB
    print(f"Subscription cancelled: {subscription['id']}")

async def handle_invoice_paid(invoice):
    # TODO: Mark invoice as paid in DB
    print(f"Invoice paid: {invoice['id']}")

async def handle_invoice_failed(invoice):
    # TODO: Notify client of failed payment
    print(f"Invoice payment failed: {invoice['id']}")
'''
