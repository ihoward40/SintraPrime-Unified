"""
FastAPI routes for Stripe payment processing
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional

from ..models import (
    CheckoutRequest,
    CheckoutResponse,
    SubscriptionRequest,
    SubscriptionResponse,
    UpgradeRequest,
    UpgradeResponse,
    CancelResponse,
    RefundRequest
)
from ..services.subscription_service import subscription_service
from ..stripe_client import stripe_client
from ..config import TIER_AMOUNTS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["payments"])


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    summary="Create checkout session",
    responses={
        200: {"description": "Checkout session created successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"}
    }
)
async def create_checkout(request: CheckoutRequest):
    """
    Create a Stripe checkout session for subscription signup
    
    Args:
        request: CheckoutRequest with email, tier, and optional URLs
        
    Returns:
        CheckoutResponse with session_id and checkout_url
        
    Raises:
        HTTPException: If checkout creation fails
    """
    try:
        logger.info(f"Creating checkout for {request.email}, tier {request.tier.value}")

        result = await stripe_client.create_checkout_session(
            customer_email=request.email,
            tier=request.tier.value,
            success_url=request.success_url,
            cancel_url=request.cancel_url
        )

        return CheckoutResponse(
            session_id=result["session_id"],
            checkout_url=result["checkout_url"],
            expires_at=result["expires_at"]
        )

    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating checkout: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post(
    "/subscribe",
    response_model=SubscriptionResponse,
    summary="Create subscription",
    responses={
        200: {"description": "Subscription created successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"}
    }
)
async def create_subscription(request: SubscriptionRequest):
    """
    Create a new subscription for a customer
    
    Args:
        request: SubscriptionRequest with email or customer_id, tier, and optional trial days
        
    Returns:
        SubscriptionResponse with subscription details
        
    Raises:
        HTTPException: If subscription creation fails
    """
    try:
        if not request.email and not request.customer_id:
            raise ValueError("Either email or customer_id is required")

        logger.info(f"Creating subscription for tier {request.tier.value}")

        subscription = await subscription_service.create_subscription(
            email=request.email,
            tier=request.tier.value,
            trial_days=request.trial_days,
            payment_method_id=request.payment_method_id
        )

        return SubscriptionResponse(
            subscription_id=subscription.subscription_id,
            status=subscription.status,
            tier=subscription.tier,
            current_period_end=subscription.current_period_end,
            trial_end=subscription.trial_end,
            next_billing_date=subscription.current_period_end
        )

    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to create subscription")


@router.get(
    "/subscription/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Get subscription details",
    responses={
        200: {"description": "Subscription retrieved successfully"},
        404: {"description": "Subscription not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_subscription(subscription_id: str):
    """
    Retrieve subscription details
    
    Args:
        subscription_id: Stripe subscription ID
        
    Returns:
        SubscriptionResponse with subscription details
        
    Raises:
        HTTPException: If subscription not found or retrieval fails
    """
    try:
        logger.info(f"Retrieving subscription: {subscription_id}")

        subscription = await subscription_service.get_subscription(subscription_id)

        return SubscriptionResponse(
            subscription_id=subscription.subscription_id,
            status=subscription.status,
            tier=subscription.tier,
            current_period_end=subscription.current_period_end,
            trial_end=subscription.trial_end,
            next_billing_date=subscription.current_period_end
        )

    except Exception as e:
        logger.error(f"Error retrieving subscription: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Subscription not found")
        raise HTTPException(status_code=500, detail="Failed to retrieve subscription")


@router.post(
    "/subscription/{subscription_id}/upgrade",
    response_model=UpgradeResponse,
    summary="Upgrade subscription tier",
    responses={
        200: {"description": "Subscription upgraded successfully"},
        400: {"description": "Invalid tier or downgrade attempt"},
        404: {"description": "Subscription not found"},
        500: {"description": "Internal server error"}
    }
)
async def upgrade_subscription(
    subscription_id: str,
    request: UpgradeRequest
):
    """
    Upgrade subscription to higher tier
    
    Args:
        subscription_id: Stripe subscription ID
        request: UpgradeRequest with new tier
        
    Returns:
        UpgradeResponse with upgrade details
        
    Raises:
        HTTPException: If upgrade fails
    """
    try:
        logger.info(f"Upgrading subscription {subscription_id} to {request.new_tier.value}")

        result = await subscription_service.upgrade_subscription(
            subscription_id=subscription_id,
            new_tier=request.new_tier.value
        )

        return UpgradeResponse(
            subscription_id=result["subscription_id"],
            new_tier=request.new_tier,
            prorated_credit=result["prorated_credit"],
            new_price=result["new_price"],
            next_charge_date=result["next_charge_date"]
        )

    except ValueError as e:
        logger.error(f"Invalid upgrade: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error upgrading subscription: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Subscription not found")
        raise HTTPException(status_code=500, detail="Failed to upgrade subscription")


@router.post(
    "/subscription/{subscription_id}/cancel",
    response_model=CancelResponse,
    summary="Cancel subscription",
    responses={
        200: {"description": "Subscription canceled successfully"},
        404: {"description": "Subscription not found"},
        500: {"description": "Internal server error"}
    }
)
async def cancel_subscription(
    subscription_id: str,
    at_period_end: bool = False
):
    """
    Cancel a subscription
    
    Args:
        subscription_id: Stripe subscription ID
        at_period_end: If True, cancel at end of billing period
        
    Returns:
        CancelResponse with cancellation details
        
    Raises:
        HTTPException: If cancellation fails
    """
    try:
        logger.info(f"Canceling subscription {subscription_id}")

        result = await subscription_service.cancel_subscription(
            subscription_id=subscription_id,
            at_period_end=at_period_end
        )

        return CancelResponse(
            subscription_id=result["subscription_id"],
            status=result["status"],
            canceled_at=result["canceled_at"],
            refund_eligible=result["refund_eligible"],
            refund_amount=result["refund_amount"]
        )

    except Exception as e:
        logger.error(f"Error canceling subscription: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Subscription not found")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")


@router.post(
    "/subscription/{subscription_id}/refund",
    summary="Request refund",
    responses={
        200: {"description": "Refund processed successfully"},
        400: {"description": "Refund not eligible"},
        404: {"description": "Subscription not found"},
        500: {"description": "Internal server error"}
    }
)
async def refund_subscription(
    subscription_id: str,
    request: RefundRequest
):
    """
    Request a refund for a subscription
    
    Args:
        subscription_id: Stripe subscription ID
        request: RefundRequest with reason and optional amount
        
    Returns:
        Refund details
        
    Raises:
        HTTPException: If refund fails or not eligible
    """
    try:
        logger.info(f"Processing refund for subscription {subscription_id}")

        result = await subscription_service.process_refund(
            subscription_id=subscription_id,
            reason=request.reason,
            amount=request.amount
        )

        return {
            "status": "success",
            "data": result
        }

    except ValueError as e:
        logger.error(f"Refund not eligible: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing refund: {e}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Subscription not found")
        raise HTTPException(status_code=500, detail="Failed to process refund")


@router.get(
    "/health",
    summary="Health check",
    responses={200: {"description": "Service is healthy"}}
)
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "stripe-payments"}
