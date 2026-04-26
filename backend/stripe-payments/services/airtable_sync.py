"""
Airtable Sync Service
Synchronizes payment and subscription data to Airtable
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
import sys
import os

# Add parent directory to path to import airtable_client
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from ..models import Subscription
from ..config import AIRTABLE_PAYMENTS_TABLE

logger = logging.getLogger(__name__)


class AirtableSyncService:
    """Service for syncing payment data to Airtable"""

    def __init__(self):
        """Initialize Airtable client"""
        try:
            # Try to import the airtable_client from parent directory
            import airtable_client
            self.airtable = airtable_client
            logger.info("Airtable client initialized")
        except ImportError:
            logger.warning("Airtable client not available, sync operations will be logged only")
            self.airtable = None

    async def create_payment_record(
        self,
        subscription: Subscription,
        email: str
    ) -> Optional[Dict[str, Any]]:
        """Create a payment record in Airtable"""
        try:
            if not self.airtable:
                logger.warning(f"Airtable not available, skipping record creation for {email}")
                return None

            amount = subscription.metadata.get("amount", 0)

            record_data = {
                "PaymentID": subscription.subscription_id,
                "ClientEmail": email,
                "Tier": subscription.tier.value.capitalize(),
                "Amount": amount,
                "Frequency": "Monthly",
                "Status": "Trialing" if subscription.trial_end else "Active",
                "NextBillingDate": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                "TrialEndsAt": subscription.trial_end.isoformat() if subscription.trial_end else None,
                "StripeSubscriptionID": subscription.subscription_id,
                "StripeCustomerID": subscription.stripe_customer_id,
                "CreatedAt": datetime.utcnow().isoformat()
            }

            logger.info(f"Creating Airtable payment record for {email}")

            # Use upsert to avoid duplicates
            if hasattr(self.airtable, 'upsert'):
                result = self.airtable.upsert(
                    AIRTABLE_PAYMENTS_TABLE,
                    records=[record_data],
                    key_fields=["PaymentID"]
                )
            else:
                result = await self.airtable.create_record(
                    AIRTABLE_PAYMENTS_TABLE,
                    record_data
                )

            logger.info(f"Airtable record created for subscription: {subscription.subscription_id}")
            return result

        except Exception as e:
            logger.error(f"Error creating Airtable payment record: {e}")
            # Don't raise - payment was successful in Stripe even if Airtable sync fails
            return None

    async def update_subscription_in_airtable(
        self,
        subscription: Subscription
    ) -> Optional[Dict[str, Any]]:
        """Update subscription status in Airtable"""
        try:
            if not self.airtable:
                logger.warning("Airtable not available, skipping subscription update")
                return None

            record_data = {
                "PaymentID": subscription.subscription_id,
                "Status": subscription.status.value.capitalize(),
                "UpdatedAt": datetime.utcnow().isoformat()
            }

            if subscription.canceled_at:
                record_data["CanceledAt"] = subscription.canceled_at.isoformat()

            logger.info(f"Updating Airtable subscription record: {subscription.subscription_id}")

            if hasattr(self.airtable, 'upsert'):
                result = self.airtable.upsert(
                    AIRTABLE_PAYMENTS_TABLE,
                    records=[record_data],
                    key_fields=["PaymentID"]
                )
            else:
                # Find record and update
                result = await self.airtable.update_record(
                    AIRTABLE_PAYMENTS_TABLE,
                    subscription.subscription_id,
                    record_data
                )

            logger.info(f"Airtable subscription updated: {subscription.subscription_id}")
            return result

        except Exception as e:
            logger.error(f"Error updating Airtable subscription: {e}")
            return None

    async def record_failed_payment(
        self,
        subscription_id: str,
        error_message: str
    ) -> Optional[Dict[str, Any]]:
        """Record a failed payment in Airtable"""
        try:
            if not self.airtable:
                logger.warning("Airtable not available, skipping failed payment record")
                return None

            record_data = {
                "PaymentID": subscription_id,
                "Status": "Failed",
                "FailureReason": error_message,
                "FailedAt": datetime.utcnow().isoformat(),
                "UpdatedAt": datetime.utcnow().isoformat()
            }

            logger.info(f"Recording failed payment for subscription: {subscription_id}")

            if hasattr(self.airtable, 'upsert'):
                result = self.airtable.upsert(
                    AIRTABLE_PAYMENTS_TABLE,
                    records=[record_data],
                    key_fields=["PaymentID"]
                )
            else:
                result = await self.airtable.update_record(
                    AIRTABLE_PAYMENTS_TABLE,
                    subscription_id,
                    record_data
                )

            logger.info(f"Failed payment recorded: {subscription_id}")
            return result

        except Exception as e:
            logger.error(f"Error recording failed payment: {e}")
            return None

    async def record_refund(
        self,
        subscription_id: str,
        amount: int
    ) -> Optional[Dict[str, Any]]:
        """Record a refund in Airtable"""
        try:
            if not self.airtable:
                logger.warning("Airtable not available, skipping refund record")
                return None

            record_data = {
                "PaymentID": subscription_id,
                "Status": "Refunded",
                "RefundAmount": amount / 100,  # Convert cents to dollars
                "RefundedAt": datetime.utcnow().isoformat(),
                "UpdatedAt": datetime.utcnow().isoformat()
            }

            logger.info(f"Recording refund for subscription: {subscription_id}")

            if hasattr(self.airtable, 'upsert'):
                result = self.airtable.upsert(
                    AIRTABLE_PAYMENTS_TABLE,
                    records=[record_data],
                    key_fields=["PaymentID"]
                )
            else:
                result = await self.airtable.update_record(
                    AIRTABLE_PAYMENTS_TABLE,
                    subscription_id,
                    record_data
                )

            logger.info(f"Refund recorded: {subscription_id}")
            return result

        except Exception as e:
            logger.error(f"Error recording refund: {e}")
            return None

    async def update_deal_stage(
        self,
        email: str,
        stage: str
    ) -> Optional[Dict[str, Any]]:
        """Update deal stage in Deals table when payment is received"""
        try:
            if not self.airtable:
                logger.warning("Airtable not available, skipping deal stage update")
                return None

            logger.info(f"Updating deal stage for {email} to {stage}")

            # Find deal by client email and update stage
            # This assumes Airtable has a Deals table with email field
            if hasattr(self.airtable, 'find_records'):
                deals = self.airtable.find_records(
                    "Deals",
                    filter_by_formula=f"{{ClientEmail}}='{email}'"
                )

                if deals:
                    deal = deals[0]
                    result = self.airtable.update_record(
                        "Deals",
                        deal["id"],
                        {"Stage": stage}
                    )
                    logger.info(f"Deal stage updated for {email}")
                    return result

            return None

        except Exception as e:
            logger.error(f"Error updating deal stage: {e}")
            return None


# Create singleton instance
airtable_sync_service = AirtableSyncService()
