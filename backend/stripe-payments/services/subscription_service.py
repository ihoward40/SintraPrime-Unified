"""
Subscription Service
Handles subscription creation, upgrades, and cancellations
"""

import logging
from typing import Optional
from datetime import datetime, timedelta

from ..stripe_client import stripe_client
from ..models import (
    Subscription,
    Customer,
    SubscriptionStatus,
    SubscriptionRequest,
    UpgradeRequest,
    RefundRequest
)
from ..config import TIER_AMOUNTS, TRIAL_DAYS, REFUND_WINDOW_DAYS, REFUND_PERCENTAGE
from .airtable_sync import AirtableSyncService

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for managing subscriptions"""

    def __init__(self):
        self.airtable_sync = AirtableSyncService()

    async def create_subscription(
        self,
        email: str,
        tier: str,
        trial_days: Optional[int] = None,
        name: Optional[str] = None,
        payment_method_id: Optional[str] = None
    ) -> Subscription:
        """Create a new subscription"""
        try:
            logger.info(f"Creating subscription for {email}, tier {tier}")

            # Get or create customer
            customer = await stripe_client.get_or_create_customer(
                email=email,
                name=name,
                metadata={"tier": tier}
            )

            # Use provided trial days or default for tier
            if trial_days is None:
                trial_days = TRIAL_DAYS.get(tier, 0)

            # Create subscription
            subscription = await stripe_client.create_subscription(
                customer_id=customer.stripe_customer_id,
                tier=tier,
                trial_days=trial_days,
                payment_method_id=payment_method_id
            )

            # Sync to Airtable
            await self.airtable_sync.create_payment_record(
                subscription=subscription,
                email=email
            )

            logger.info(f"Subscription created: {subscription.subscription_id}")
            return subscription

        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            raise

    async def get_subscription(self, subscription_id: str) -> Subscription:
        """Retrieve subscription details"""
        try:
            subscription = await stripe_client.get_subscription(subscription_id)
            logger.info(f"Retrieved subscription: {subscription_id}")
            return subscription
        except Exception as e:
            logger.error(f"Error retrieving subscription: {e}")
            raise

    async def upgrade_subscription(
        self,
        subscription_id: str,
        new_tier: str
    ) -> dict:
        """Upgrade subscription to higher tier"""
        try:
            logger.info(f"Upgrading subscription {subscription_id} to {new_tier}")

            # Get current subscription
            current_sub = await stripe_client.get_subscription(subscription_id)

            # Calculate proration credit
            prorated_credit = self._calculate_prorated_credit(
                current_sub.tier,
                new_tier,
                current_sub.current_period_end
            )

            # Upgrade subscription
            upgraded = await stripe_client.upgrade_subscription(
                subscription_id=subscription_id,
                new_tier=new_tier
            )

            # Sync to Airtable
            await self.airtable_sync.update_subscription_in_airtable(upgraded)

            new_price = TIER_AMOUNTS.get(new_tier, 0)

            result = {
                "subscription_id": upgraded.subscription_id,
                "new_tier": new_tier,
                "prorated_credit": prorated_credit,
                "new_price": new_price,
                "next_charge_date": upgraded.current_period_end.isoformat()
            }

            logger.info(f"Subscription upgraded: {subscription_id}")
            return result

        except Exception as e:
            logger.error(f"Error upgrading subscription: {e}")
            raise

    async def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = False
    ) -> dict:
        """Cancel a subscription"""
        try:
            logger.info(f"Canceling subscription {subscription_id}, at_period_end={at_period_end}")

            # Get subscription before cancellation
            current_sub = await stripe_client.get_subscription(subscription_id)

            # Check refund eligibility
            refund_eligible = self._check_refund_eligibility(current_sub)

            # Calculate refund amount
            refund_amount = None
            if refund_eligible:
                refund_amount = self._calculate_refund_amount(
                    subscription_id,
                    current_sub.tier
                )

            # Cancel subscription
            canceled = await stripe_client.cancel_subscription(
                subscription_id=subscription_id,
                at_period_end=at_period_end
            )

            # Sync to Airtable
            await self.airtable_sync.update_subscription_in_airtable(canceled)

            result = {
                "subscription_id": canceled.subscription_id,
                "status": canceled.status,
                "canceled_at": canceled.canceled_at.isoformat() if canceled.canceled_at else None,
                "refund_eligible": refund_eligible,
                "refund_amount": refund_amount
            }

            logger.info(f"Subscription canceled: {subscription_id}")
            return result

        except Exception as e:
            logger.error(f"Error canceling subscription: {e}")
            raise

    async def process_refund(
        self,
        subscription_id: str,
        reason: str = "requested_by_customer",
        amount: Optional[int] = None
    ) -> dict:
        """Process a refund for a subscription"""
        try:
            logger.info(f"Processing refund for subscription {subscription_id}")

            subscription = await stripe_client.get_subscription(subscription_id)

            # Check refund eligibility
            if not self._check_refund_eligibility(subscription):
                raise ValueError(
                    f"Subscription {subscription_id} is not eligible for refund. "
                    f"Refunds must be requested within {REFUND_WINDOW_DAYS} days of subscription start."
                )

            # Get payment intent from latest invoice
            import stripe
            invoices = stripe.Invoice.list(subscription=subscription_id, limit=1)

            if not invoices.data:
                raise ValueError(f"No invoices found for subscription {subscription_id}")

            invoice = invoices.data[0]
            payment_intent_id = invoice.payment_intent

            if not payment_intent_id:
                raise ValueError(f"No payment intent found for subscription {subscription_id}")

            # Calculate refund amount
            if amount is None:
                amount = self._calculate_refund_amount(subscription_id, subscription.tier)

            # Process refund via Stripe
            from ..stripe_client import stripe_client as client
            refund_result = await client.refund_payment(
                payment_intent_id=payment_intent_id,
                amount=amount,
                reason=reason
            )

            # Update Airtable
            await self.airtable_sync.record_refund(subscription_id, amount)

            result = {
                "subscription_id": subscription_id,
                "refund_id": refund_result.payment_id,
                "amount": amount,
                "status": "processed"
            }

            logger.info(f"Refund processed for subscription: {subscription_id}")
            return result

        except Exception as e:
            logger.error(f"Error processing refund: {e}")
            raise

    def _calculate_prorated_credit(
        self,
        current_tier: str,
        new_tier: str,
        period_end: datetime
    ) -> int:
        """Calculate prorated credit when upgrading"""
        current_amount = TIER_AMOUNTS.get(current_tier, 0)
        new_amount = TIER_AMOUNTS.get(new_tier, 0)

        if new_amount <= current_amount:
            return 0  # No credit for downgrades or same tier

        # Calculate remaining days in billing period
        now = datetime.utcnow()
        days_remaining = (period_end - now).days
        days_in_period = 30  # Approximate month

        # Prorated difference
        daily_current = current_amount / days_in_period
        daily_new = new_amount / days_in_period
        daily_difference = daily_new - daily_current

        prorated_credit = int(daily_difference * days_remaining)
        return prorated_credit

    def _check_refund_eligibility(self, subscription: Subscription) -> bool:
        """Check if subscription is eligible for refund"""
        # Check if within refund window
        days_since_start = (
            datetime.utcnow() - subscription.created_at
        ).days

        return days_since_start <= REFUND_WINDOW_DAYS

    def _calculate_refund_amount(
        self,
        subscription_id: str,
        tier: str
    ) -> int:
        """Calculate refund amount based on tier and time used"""
        amount = TIER_AMOUNTS.get(tier, 0)
        return int(amount * REFUND_PERCENTAGE / 100)


# Create singleton instance
subscription_service = SubscriptionService()
