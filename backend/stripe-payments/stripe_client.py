"""
Stripe API client wrapper
Handles all interactions with Stripe API
"""

import stripe
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from .config import (
    STRIPE_SECRET_KEY,
    TIER_PRICE_IDS,
    TIER_AMOUNTS,
    TIER_NAMES,
    TRIAL_DAYS,
    DEFAULT_PAYMENT_BEHAVIOR,
    API_BASE_URL,
    IS_PRODUCTION
)
from .models import Customer, Subscription, Payment, SubscriptionStatus, PaymentStatus

# Initialize Stripe
stripe.api_key = STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)


class StripeClient:
    """Stripe API client wrapper"""

    @staticmethod
    async def get_or_create_customer(
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Customer:
        """Get existing customer or create new one"""
        try:
            # Search for existing customer
            customers = stripe.Customer.list(email=email, limit=1)

            if customers.data:
                cust = customers.data[0]
                logger.info(f"Found existing customer: {cust.id}")
                return Customer(
                    stripe_customer_id=cust.id,
                    email=cust.email,
                    name=cust.name,
                    metadata=cust.metadata or {}
                )

            # Create new customer
            logger.info(f"Creating new customer for {email}")
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {},
                description=f"SintraPrime customer - {email}"
            )

            return Customer(
                stripe_customer_id=customer.id,
                email=customer.email,
                name=customer.name,
                metadata=customer.metadata or {}
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating/fetching customer: {e}")
            raise


    @staticmethod
    async def create_subscription(
        customer_id: str,
        tier: str,
        trial_days: Optional[int] = None,
        payment_method_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Subscription:
        """Create a subscription with optional trial"""
        try:
            if trial_days is None:
                trial_days = TRIAL_DAYS.get(tier, 0)

            price_id = TIER_PRICE_IDS.get(tier)
            if not price_id:
                raise ValueError(f"Invalid tier: {tier}")

            logger.info(f"Creating subscription for customer {customer_id}, tier {tier}")

            items = [{"price": price_id}]

            subscription_params = {
                "customer": customer_id,
                "items": items,
                "payment_behavior": DEFAULT_PAYMENT_BEHAVIOR,
                "metadata": metadata or {"tier": tier},
            }

            if trial_days > 0:
                subscription_params["trial_period_days"] = trial_days

            if payment_method_id:
                subscription_params["default_payment_method"] = payment_method_id

            subscription = stripe.Subscription.create(**subscription_params)

            status = SubscriptionStatus.TRIALING if trial_days > 0 else SubscriptionStatus.ACTIVE

            return Subscription(
                subscription_id=subscription.id,
                stripe_customer_id=subscription.customer,
                tier=tier,
                status=status,
                current_period_start=datetime.fromtimestamp(subscription.current_period_start),
                current_period_end=datetime.fromtimestamp(subscription.current_period_end),
                trial_start=datetime.fromtimestamp(subscription.trial_start) if subscription.trial_start else None,
                trial_end=datetime.fromtimestamp(subscription.trial_end) if subscription.trial_end else None,
                metadata=subscription.metadata or {}
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating subscription: {e}")
            raise


    @staticmethod
    async def get_subscription(subscription_id: str) -> Subscription:
        """Retrieve subscription details"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)

            # Determine tier from metadata
            tier = subscription.metadata.get("tier", "starter")

            return Subscription(
                subscription_id=subscription.id,
                stripe_customer_id=subscription.customer,
                tier=tier,
                status=SubscriptionStatus(subscription.status),
                current_period_start=datetime.fromtimestamp(subscription.current_period_start),
                current_period_end=datetime.fromtimestamp(subscription.current_period_end),
                trial_start=datetime.fromtimestamp(subscription.trial_start) if subscription.trial_start else None,
                trial_end=datetime.fromtimestamp(subscription.trial_end) if subscription.trial_end else None,
                cancel_at=datetime.fromtimestamp(subscription.cancel_at) if subscription.cancel_at else None,
                canceled_at=datetime.fromtimestamp(subscription.canceled_at) if subscription.canceled_at else None,
                metadata=subscription.metadata or {}
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error retrieving subscription: {e}")
            raise


    @staticmethod
    async def upgrade_subscription(
        subscription_id: str,
        new_tier: str
    ) -> Subscription:
        """Upgrade subscription to higher tier"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            old_item_id = subscription.items.data[0].id
            new_price_id = TIER_PRICE_IDS.get(new_tier)

            if not new_price_id:
                raise ValueError(f"Invalid tier: {new_tier}")

            logger.info(f"Upgrading subscription {subscription_id} to {new_tier}")

            # Update subscription with new price
            upgraded = stripe.Subscription.modify(
                subscription_id,
                items=[
                    {
                        "id": old_item_id,
                        "price": new_price_id,
                    }
                ],
                proration_behavior="create_prorations",
                metadata={"tier": new_tier}
            )

            return Subscription(
                subscription_id=upgraded.id,
                stripe_customer_id=upgraded.customer,
                tier=new_tier,
                status=SubscriptionStatus(upgraded.status),
                current_period_start=datetime.fromtimestamp(upgraded.current_period_start),
                current_period_end=datetime.fromtimestamp(upgraded.current_period_end),
                trial_start=datetime.fromtimestamp(upgraded.trial_start) if upgraded.trial_start else None,
                trial_end=datetime.fromtimestamp(upgraded.trial_end) if upgraded.trial_end else None,
                metadata=upgraded.metadata or {}
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error upgrading subscription: {e}")
            raise


    @staticmethod
    async def cancel_subscription(
        subscription_id: str,
        at_period_end: bool = False
    ) -> Subscription:
        """Cancel a subscription"""
        try:
            logger.info(f"Canceling subscription {subscription_id}, at_period_end={at_period_end}")

            if at_period_end:
                canceled = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                canceled = stripe.Subscription.delete(subscription_id)

            tier = canceled.metadata.get("tier", "starter")

            return Subscription(
                subscription_id=canceled.id,
                stripe_customer_id=canceled.customer,
                tier=tier,
                status=SubscriptionStatus(canceled.status),
                current_period_start=datetime.fromtimestamp(canceled.current_period_start),
                current_period_end=datetime.fromtimestamp(canceled.current_period_end),
                trial_start=datetime.fromtimestamp(canceled.trial_start) if canceled.trial_start else None,
                trial_end=datetime.fromtimestamp(canceled.trial_end) if canceled.trial_end else None,
                cancel_at=datetime.fromtimestamp(canceled.cancel_at) if canceled.cancel_at else None,
                canceled_at=datetime.fromtimestamp(canceled.canceled_at) if canceled.canceled_at else None,
                metadata=canceled.metadata or {}
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error canceling subscription: {e}")
            raise


    @staticmethod
    async def create_checkout_session(
        customer_email: str,
        tier: str,
        success_url: str,
        cancel_url: str
    ) -> Dict[str, Any]:
        """Create a Stripe checkout session"""
        try:
            price_id = TIER_PRICE_IDS.get(tier)
            if not price_id:
                raise ValueError(f"Invalid tier: {tier}")

            logger.info(f"Creating checkout session for {customer_email}, tier {tier}")

            trial_days = TRIAL_DAYS.get(tier, 0)

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                customer_email=customer_email,
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                success_url=success_url or f"{API_BASE_URL}/dashboard?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=cancel_url or f"{API_BASE_URL}/pricing",
                subscription_data={
                    "trial_period_days": trial_days if trial_days > 0 else None,
                    "metadata": {"tier": tier}
                },
                metadata={"tier": tier}
            )

            return {
                "session_id": session.id,
                "checkout_url": session.url,
                "expires_at": session.expires_at
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            raise


    @staticmethod
    async def refund_payment(
        payment_intent_id: str,
        amount: Optional[int] = None,
        reason: str = "requested_by_customer"
    ) -> Payment:
        """Refund a payment"""
        try:
            logger.info(f"Processing refund for payment intent {payment_intent_id}")

            refund = stripe.Refund.create(
                payment_intent=payment_intent_id,
                amount=amount,
                reason=reason
            )

            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            return Payment(
                payment_id=refund.id,
                stripe_customer_id=payment_intent.customer,
                stripe_payment_intent_id=payment_intent_id,
                amount=refund.amount,
                currency=refund.currency,
                status=PaymentStatus.REFUNDED,
                description=f"Refund: {reason}",
                metadata=refund.metadata or {}
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error processing refund: {e}")
            raise


    @staticmethod
    async def get_invoice(invoice_id: str) -> Dict[str, Any]:
        """Get invoice details"""
        try:
            invoice = stripe.Invoice.retrieve(invoice_id)
            return {
                "id": invoice.id,
                "amount_due": invoice.amount_due,
                "amount_paid": invoice.amount_paid,
                "currency": invoice.currency,
                "customer": invoice.customer,
                "status": invoice.status,
                "subscription": invoice.subscription,
                "paid": invoice.paid,
                "payment_failed": invoice.payment_failed,
                "created": invoice.created,
                "number": invoice.number,
                "pdf": invoice.pdf
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error retrieving invoice: {e}")
            raise


    @staticmethod
    def verify_webhook_signature(
        payload: bytes,
        sig_header: str,
        webhook_secret: str
    ) -> Dict[str, Any]:
        """Verify Stripe webhook signature"""
        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                webhook_secret
            )
            return event
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise


# Create singleton instance
stripe_client = StripeClient()
