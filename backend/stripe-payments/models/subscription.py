"""
Pydantic models for Stripe subscription system
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class SubscriptionStatus(str, Enum):
    """Subscription status values"""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    TRIALING = "trialing"
    PENDING = "pending"


class PaymentStatus(str, Enum):
    """Payment status values"""
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class Tier(str, Enum):
    """Subscription tier options"""
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Customer(BaseModel):
    """Stripe customer model"""
    stripe_customer_id: str
    email: EmailStr
    name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class Payment(BaseModel):
    """Payment record model"""
    payment_id: str
    stripe_customer_id: str
    stripe_payment_intent_id: Optional[str] = None
    amount: int  # In cents
    currency: str = "usd"
    status: PaymentStatus = PaymentStatus.PENDING
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class Subscription(BaseModel):
    """Subscription model"""
    subscription_id: str
    stripe_customer_id: str
    tier: Tier
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    current_period_start: datetime
    current_period_end: datetime
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    cancel_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    payment_method: Optional[str] = None
    last_payment_status: Optional[PaymentStatus] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CheckoutRequest(BaseModel):
    """Request to create a checkout session"""
    email: EmailStr
    tier: Tier
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class SubscriptionRequest(BaseModel):
    """Request to create a subscription"""
    customer_id: Optional[str] = None  # Stripe customer ID
    email: Optional[EmailStr] = None  # If creating new customer
    tier: Tier
    payment_method_id: Optional[str] = None
    trial_days: Optional[int] = None


class UpgradeRequest(BaseModel):
    """Request to upgrade subscription"""
    new_tier: Tier
    prorated: bool = True  # Calculate prorated amount


class RefundRequest(BaseModel):
    """Request to process a refund"""
    reason: str = "requested_by_customer"
    amount: Optional[int] = None  # If partial refund


class WebhookEvent(BaseModel):
    """Webhook event from Stripe"""
    id: str
    object: str
    api_version: str
    created: int
    data: dict
    livemode: bool
    pending_webhooks: int
    request: Optional[dict] = None
    type: str


# Request/Response Models for API Endpoints

class CheckoutResponse(BaseModel):
    """Response for checkout session creation"""
    session_id: str
    checkout_url: str
    expires_at: int


class SubscriptionResponse(BaseModel):
    """Response for subscription operations"""
    subscription_id: str
    status: SubscriptionStatus
    tier: Tier
    current_period_end: datetime
    trial_end: Optional[datetime] = None
    next_billing_date: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class UpgradeResponse(BaseModel):
    """Response for upgrade operation"""
    subscription_id: str
    new_tier: Tier
    prorated_credit: int  # In cents
    new_price: int  # In cents
    next_charge_date: datetime

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CancelResponse(BaseModel):
    """Response for subscription cancellation"""
    subscription_id: str
    status: SubscriptionStatus
    canceled_at: datetime
    refund_eligible: bool
    refund_amount: Optional[int] = None  # In cents

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
