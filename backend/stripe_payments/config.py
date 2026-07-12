"""
Stripe Configuration and Constants
"""
import os
from typing import Dict

# Stripe API Keys (use environment variables in production)
STRIPE_SECRET_KEY = os.getenv(
    "STRIPE_SECRET_KEY",
    "sk_test_your_test_secret_key_here"
)
STRIPE_PUBLISHABLE_KEY = os.getenv(
    "STRIPE_PUBLISHABLE_KEY",
    "pk_test_your_test_publishable_key_here"
)
STRIPE_WEBHOOK_SECRET = os.getenv(
    "STRIPE_WEBHOOK_SECRET",
    "whsec_test_your_webhook_secret_here"
)

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "test")
IS_PRODUCTION = ENVIRONMENT == "production"

# Tier Configuration
TIER_NAMES = {
    "starter": "Starter",
    "pro": "Pro",
    "enterprise": "Enterprise"
}

# Monthly prices in cents (USD)
TIER_AMOUNTS = {
    "starter": 9900,      # $99/month
    "pro": 49900,         # $499/month
    "enterprise": None    # Custom pricing
}

# Stripe Price IDs (to be created in Stripe dashboard)
TIER_PRICE_IDS = {
    "starter": os.getenv("STRIPE_PRICE_STARTER", "price_starter_test"),
    "pro": os.getenv("STRIPE_PRICE_PRO", "price_pro_test"),
    "enterprise": os.getenv("STRIPE_PRICE_ENTERPRISE", "price_enterprise_test")
}

# Trial period in days
TRIAL_DAYS = {
    "starter": 14,
    "pro": 7,
    "enterprise": 0  # Sales conversation required
}

# Tier Features
TIER_FEATURES = {
    "starter": {
        "name": "Starter",
        "price": "$99/month",
        "trial_days": 14,
        "features": [
            "Limited legal document reviews",
            "Basic credit analysis",
            "Email support"
        ]
    },
    "pro": {
        "name": "Pro",
        "price": "$499/month",
        "trial_days": 7,
        "features": [
            "Unlimited legal document reviews",
            "Advanced credit optimization",
            "Autonomous filing (up to 5 cases/month)",
            "Priority 24h support"
        ]
    },
    "enterprise": {
        "name": "Enterprise",
        "price": "Custom",
        "trial_days": 0,
        "features": [
            "All Pro features",
            "White-label client portal",
            "Dedicated agent access",
            "Custom integrations",
            "Phone support"
        ]
    }
}

# Airtable Configuration
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "appYourBaseId")
AIRTABLE_API_TOKEN = os.getenv("AIRTABLE_API_TOKEN", "patYourToken")
AIRTABLE_PAYMENTS_TABLE = "Payments"

# Email Configuration
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "payments@sintraprime.com")

# URLs
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "https://app.sintraprime.com")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Refund Policy
REFUND_WINDOW_DAYS = 30  # Days after subscription start to allow refunds
REFUND_PERCENTAGE = 100  # Full refund within window

# Default Payment Behavior
DEFAULT_PAYMENT_BEHAVIOR = "default_incomplete"  # Requires payment confirmation for trials
