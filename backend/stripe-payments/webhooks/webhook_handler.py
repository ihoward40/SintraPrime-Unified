"""
Stripe Webhook Handler
Processes Stripe webhook events and updates local system
"""

import logging
import json
from fastapi import APIRouter, Request, HTTPException
import stripe

from ..config import STRIPE_WEBHOOK_SECRET
from ..stripe_client import stripe_client
from ..services.airtable_sync import airtable_sync_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post(
    "/stripe",
    summary="Stripe webhook receiver",
    responses={
        200: {"description": "Webhook processed successfully"},
        400: {"description": "Invalid signature"},
        500: {"description": "Processing error"}
    }
)
async def handle_webhook(request: Request):
    """
    Handle Stripe webhook events
    
    Supported events:
    - payment_intent.succeeded: Payment completed
    - customer.subscription.updated: Subscription changed
    - customer.subscription.deleted: Subscription canceled
    - invoice.paid: Invoice paid
    - invoice.payment_failed: Payment failed
    - invoice.upcoming: Upcoming invoice (for reminders)
    
    Args:
        request: HTTP request containing Stripe webhook event
        
    Returns:
        Response confirming webhook receipt
        
    Raises:
        HTTPException: If signature verification fails
    """
    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")

        # Verify webhook signature
        try:
            event = stripe_client.verify_webhook_signature(
                payload,
                sig_header,
                STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {e}")
            raise HTTPException(status_code=400, detail="Invalid signature")

        logger.info(f"Processing webhook event: {event['type']}")

        # Handle different event types
        event_type = event["type"]

        if event_type == "payment_intent.succeeded":
            await _handle_payment_intent_succeeded(event)

        elif event_type == "customer.subscription.updated":
            await _handle_subscription_updated(event)

        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(event)

        elif event_type == "invoice.paid":
            await _handle_invoice_paid(event)

        elif event_type == "invoice.payment_failed":
            await _handle_invoice_payment_failed(event)

        elif event_type == "invoice.upcoming":
            await _handle_invoice_upcoming(event)

        else:
            logger.info(f"Unhandled event type: {event_type}")

        return {"status": "received"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        # Return 200 anyway to prevent Stripe from retrying
        return {"status": "error", "detail": str(e)}


async def _handle_payment_intent_succeeded(event: dict):
    """Handle successful payment"""
    try:
        payment_intent = event["data"]["object"]
        logger.info(f"Payment succeeded: {payment_intent['id']}")

        # Fetch subscription if available
        if payment_intent.get("metadata", {}).get("subscription_id"):
            subscription_id = payment_intent["metadata"]["subscription_id"]
            subscription = await stripe_client.get_subscription(subscription_id)
            await airtable_sync_service.update_subscription_in_airtable(subscription)

        # Log payment success
        logger.info(f"Payment {payment_intent['id']} recorded in Airtable")

    except Exception as e:
        logger.error(f"Error handling payment_intent.succeeded: {e}")


async def _handle_subscription_updated(event: dict):
    """Handle subscription updates"""
    try:
        subscription = event["data"]["object"]
        subscription_id = subscription["id"]
        logger.info(f"Subscription updated: {subscription_id}")

        # Fetch full subscription details
        full_subscription = await stripe_client.get_subscription(subscription_id)

        # Sync to Airtable
        await airtable_sync_service.update_subscription_in_airtable(full_subscription)

        logger.info(f"Subscription {subscription_id} synced to Airtable")

    except Exception as e:
        logger.error(f"Error handling customer.subscription.updated: {e}")


async def _handle_subscription_deleted(event: dict):
    """Handle subscription cancellations"""
    try:
        subscription = event["data"]["object"]
        subscription_id = subscription["id"]
        logger.info(f"Subscription deleted: {subscription_id}")

        # The subscription object should have canceled status
        # Update Airtable with cancellation
        await airtable_sync_service.record_failed_payment(
            subscription_id,
            "Subscription canceled"
        )

        logger.info(f"Subscription {subscription_id} marked as canceled in Airtable")

    except Exception as e:
        logger.error(f"Error handling customer.subscription.deleted: {e}")


async def _handle_invoice_paid(event: dict):
    """Handle paid invoices"""
    try:
        invoice = event["data"]["object"]
        invoice_id = invoice["id"]
        logger.info(f"Invoice paid: {invoice_id}")

        # Get invoice details
        invoice_data = await stripe_client.get_invoice(invoice_id)

        if invoice_data.get("subscription"):
            subscription_id = invoice_data["subscription"]
            subscription = await stripe_client.get_subscription(subscription_id)
            await airtable_sync_service.update_subscription_in_airtable(subscription)

        logger.info(f"Invoice {invoice_id} recorded in Airtable")

    except Exception as e:
        logger.error(f"Error handling invoice.paid: {e}")


async def _handle_invoice_payment_failed(event: dict):
    """Handle failed payments"""
    try:
        invoice = event["data"]["object"]
        invoice_id = invoice["id"]
        logger.error(f"Invoice payment failed: {invoice_id}")

        # Get invoice details
        invoice_data = await stripe_client.get_invoice(invoice_id)

        if invoice_data.get("subscription"):
            subscription_id = invoice_data["subscription"]

            # Record failure in Airtable
            await airtable_sync_service.record_failed_payment(
                subscription_id,
                f"Invoice {invoice_id} payment failed"
            )

            logger.info(f"Invoice {invoice_id} failure recorded in Airtable")

        # TODO: Send email notification to customer
        # TODO: Create alert for support team

    except Exception as e:
        logger.error(f"Error handling invoice.payment_failed: {e}")


async def _handle_invoice_upcoming(event: dict):
    """Handle upcoming invoices (billing reminders)"""
    try:
        invoice = event["data"]["object"]
        invoice_id = invoice["id"]
        logger.info(f"Upcoming invoice: {invoice_id}")

        # TODO: Send reminder email to customer
        # This is optional but helps reduce failed payments

    except Exception as e:
        logger.error(f"Error handling invoice.upcoming: {e}")
