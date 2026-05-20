"""
Unit tests for Stripe payment system
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any

# Import modules to test
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import (
    Subscription,
    Customer,
    Payment,
    SubscriptionStatus,
    PaymentStatus,
    Tier
)
from config import TIER_AMOUNTS, TRIAL_DAYS, TIER_PRICE_IDS
from stripe_client import StripeClient
from utils.pricing import PricingCalculator


class TestStripeClient:
    """Test Stripe API client"""

    @pytest.mark.asyncio
    async def test_get_or_create_customer_existing(self):
        """Test retrieving existing customer"""
        with patch('stripe.Customer.list') as mock_list:
            mock_customer = Mock()
            mock_customer.id = "cus_123"
            mock_customer.email = "test@example.com"
            mock_customer.name = "John Doe"
            mock_customer.metadata = {"test": "data"}

            mock_list.return_value.data = [mock_customer]

            client = StripeClient()
            customer = await client.get_or_create_customer("test@example.com")

            assert customer.stripe_customer_id == "cus_123"
            assert customer.email == "test@example.com"
            mock_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_customer_new(self):
        """Test creating new customer"""
        with patch('stripe.Customer.list') as mock_list, \
             patch('stripe.Customer.create') as mock_create:

            mock_list.return_value.data = []

            mock_customer = Mock()
            mock_customer.id = "cus_456"
            mock_customer.email = "newuser@example.com"
            mock_customer.name = "Jane Doe"
            mock_customer.metadata = {}

            mock_create.return_value = mock_customer

            client = StripeClient()
            customer = await client.get_or_create_customer("newuser@example.com")

            assert customer.stripe_customer_id == "cus_456"
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_subscription_with_trial(self):
        """Test creating subscription with trial"""
        with patch('stripe.Subscription.create') as mock_create:
            mock_subscription = Mock()
            mock_subscription.id = "sub_123"
            mock_subscription.customer = "cus_123"
            mock_subscription.status = "trialing"
            mock_subscription.current_period_start = int(datetime.utcnow().timestamp())
            mock_subscription.current_period_end = int((datetime.utcnow() + timedelta(days=30)).timestamp())
            mock_subscription.trial_start = int(datetime.utcnow().timestamp())
            mock_subscription.trial_end = int((datetime.utcnow() + timedelta(days=14)).timestamp())
            mock_subscription.metadata = {"tier": "starter"}

            mock_create.return_value = mock_subscription

            client = StripeClient()
            subscription = await client.create_subscription(
                customer_id="cus_123",
                tier="starter",
                trial_days=14
            )

            assert subscription.subscription_id == "sub_123"
            assert subscription.status == SubscriptionStatus.TRIALING
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_upgrade_subscription(self):
        """Test upgrading subscription"""
        with patch('stripe.Subscription.retrieve') as mock_get, \
             patch('stripe.Subscription.modify') as mock_modify:

            mock_current = Mock()
            mock_current.id = "sub_123"
            mock_current.items.data = [Mock(id="item_123")]

            mock_get.return_value = mock_current

            mock_upgraded = Mock()
            mock_upgraded.id = "sub_123"
            mock_upgraded.customer = "cus_123"
            mock_upgraded.status = "active"
            mock_upgraded.current_period_start = int(datetime.utcnow().timestamp())
            mock_upgraded.current_period_end = int((datetime.utcnow() + timedelta(days=30)).timestamp())
            mock_upgraded.trial_start = None
            mock_upgraded.trial_end = None
            mock_upgraded.metadata = {"tier": "pro"}

            mock_modify.return_value = mock_upgraded

            client = StripeClient()
            subscription = await client.upgrade_subscription(
                subscription_id="sub_123",
                new_tier="pro"
            )

            assert subscription.tier == "pro"
            mock_modify.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_subscription(self):
        """Test canceling subscription"""
        with patch('stripe.Subscription.delete') as mock_delete:
            mock_canceled = Mock()
            mock_canceled.id = "sub_123"
            mock_canceled.customer = "cus_123"
            mock_canceled.status = "canceled"
            mock_canceled.current_period_start = int(datetime.utcnow().timestamp())
            mock_canceled.current_period_end = int((datetime.utcnow() + timedelta(days=30)).timestamp())
            mock_canceled.trial_start = None
            mock_canceled.trial_end = None
            mock_canceled.cancel_at = None
            mock_canceled.canceled_at = int(datetime.utcnow().timestamp())
            mock_canceled.metadata = {"tier": "starter"}

            mock_delete.return_value = mock_canceled

            client = StripeClient()
            subscription = await client.cancel_subscription(subscription_id="sub_123")

            assert subscription.status == SubscriptionStatus.CANCELED
            mock_delete.assert_called_once()


class TestPricingCalculator:
    """Test pricing calculations"""

    def test_apply_discount(self):
        """Test applying percentage discount"""
        calculator = PricingCalculator()

        # Test 10% discount on $99
        result = calculator.apply_discount(9900, 10)

        assert result["original"] == 9900
        assert result["discount"] == 990
        assert result["final"] == 8910

    def test_apply_promotional_code(self):
        """Test applying promotional code"""
        calculator = PricingCalculator()

        # Test SAVE10 code
        result = calculator.apply_promotional_code(9900, "SAVE10")

        assert result["discount"] == 990
        assert result["final"] == 8910

    def test_apply_invalid_promotional_code(self):
        """Test invalid promotional code"""
        calculator = PricingCalculator()

        with pytest.raises(ValueError):
            calculator.apply_promotional_code(9900, "INVALID")

    def test_calculate_annual_savings(self):
        """Test annual savings calculation"""
        calculator = PricingCalculator()

        monthly = 9900  # $99
        annual = 108900  # $1089 (2 months free)

        result = calculator.calculate_annual_savings(monthly, annual)

        assert result["monthly_price"] == 9900
        assert result["annual_price"] == 108900
        assert result["savings"] == 10800  # $108 saved

    def test_get_tier_pricing(self):
        """Test getting tier pricing"""
        calculator = PricingCalculator()

        result = calculator.get_tier_pricing("starter")

        assert result["tier"] == "starter"
        assert result["monthly"]["price"] == 9900
        assert result["annual"]["price"] == 108900

    def test_compare_tiers(self):
        """Test pricing comparison for all tiers"""
        calculator = PricingCalculator()

        result = calculator.compare_tiers()

        assert "starter" in result
        assert "pro" in result
        assert "enterprise" in result


class TestWebhookSignature:
    """Test webhook signature verification"""

    def test_verify_webhook_signature_valid(self):
        """Test valid webhook signature verification"""
        with patch('stripe.Webhook.construct_event') as mock_verify:
            mock_event = {
                "id": "evt_123",
                "type": "payment_intent.succeeded",
                "data": {"object": {"id": "pi_123"}}
            }
            mock_verify.return_value = mock_event

            client = StripeClient()
            event = client.verify_webhook_signature(
                b"payload",
                "sig_test",
                "whsec_test"
            )

            assert event["type"] == "payment_intent.succeeded"
            mock_verify.assert_called_once()

    def test_verify_webhook_signature_invalid(self):
        """Test invalid webhook signature"""
        import stripe as stripe_module

        with patch('stripe.Webhook.construct_event') as mock_verify:
            mock_verify.side_effect = stripe_module.error.SignatureVerificationError(
                "Invalid signature",
                "sig_test"
            )

            client = StripeClient()

            with pytest.raises(stripe_module.error.SignatureVerificationError):
                client.verify_webhook_signature(
                    b"payload",
                    "sig_invalid",
                    "whsec_test"
                )


class TestPaymentModels:
    """Test Pydantic models"""

    def test_subscription_model(self):
        """Test subscription model creation"""
        now = datetime.utcnow()
        future = now + timedelta(days=30)

        subscription = Subscription(
            subscription_id="sub_123",
            stripe_customer_id="cus_123",
            tier=Tier.STARTER,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=now,
            current_period_end=future
        )

        assert subscription.subscription_id == "sub_123"
        assert subscription.tier == Tier.STARTER
        assert subscription.status == SubscriptionStatus.ACTIVE

    def test_customer_model(self):
        """Test customer model creation"""
        customer = Customer(
            stripe_customer_id="cus_123",
            email="test@example.com",
            name="John Doe"
        )

        assert customer.stripe_customer_id == "cus_123"
        assert customer.email == "test@example.com"

    def test_payment_model(self):
        """Test payment model creation"""
        payment = Payment(
            payment_id="pay_123",
            stripe_customer_id="cus_123",
            amount=9900,
            status=PaymentStatus.SUCCEEDED
        )

        assert payment.payment_id == "pay_123"
        assert payment.amount == 9900
        assert payment.status == PaymentStatus.SUCCEEDED


class TestPricingConfig:
    """Test pricing configuration"""

    def test_tier_amounts(self):
        """Test tier amounts are configured"""
        assert TIER_AMOUNTS["starter"] == 9900  # $99/month
        assert TIER_AMOUNTS["pro"] == 49900     # $499/month
        assert TIER_AMOUNTS["enterprise"] is None

    def test_trial_days(self):
        """Test trial days configuration"""
        assert TRIAL_DAYS["starter"] == 14
        assert TRIAL_DAYS["pro"] == 7
        assert TRIAL_DAYS["enterprise"] == 0

    def test_price_ids_configured(self):
        """Test price IDs are configured"""
        assert "starter" in TIER_PRICE_IDS
        assert "pro" in TIER_PRICE_IDS
        assert "enterprise" in TIER_PRICE_IDS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
