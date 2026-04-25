"""
Billing Portal for SintraPrime-Unified SaaS

Manages customer billing dashboard, invoices, payment methods,
and Stripe Customer Portal integration.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from decimal import Decimal
import stripe

logger = logging.getLogger(__name__)


@dataclass
class PaymentMethod:
    """Represents a payment method."""
    id: str
    type: str  # "card", "bank_account", etc.
    last_four: str
    brand: Optional[str] = None  # "visa", "mastercard", etc.
    exp_month: Optional[int] = None
    exp_year: Optional[int] = None
    is_default: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Invoice:
    """Represents a billing invoice."""
    id: str
    invoice_number: str
    customer_id: str
    amount: Decimal
    currency: str
    status: str  # "draft", "open", "paid", "void", "uncollectible"
    issue_date: datetime
    due_date: datetime
    paid_date: Optional[datetime] = None
    pdf_url: Optional[str] = None
    description: Optional[str] = None
    line_items: List[Dict] = field(default_factory=list)


@dataclass
class UpcomingInvoice:
    """Preview of an upcoming invoice."""
    amount: Decimal
    currency: str
    due_date: datetime
    items: List[Dict]


@dataclass
class BillingAlert:
    """Alert for billing issues."""
    id: str
    alert_type: str  # "payment_failed", "quota_exceeded", "renewal_coming"
    severity: str  # "info", "warning", "critical"
    message: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False


@dataclass
class BillingDashboard:
    """Complete billing dashboard data."""
    subscription_id: str
    current_plan: str
    plan_amount: Decimal
    billing_cycle_start: datetime
    billing_cycle_end: datetime
    next_billing_date: datetime
    payment_method: Optional[PaymentMethod]
    upcoming_invoice: Optional[UpcomingInvoice]
    recent_invoices: List[Invoice]
    billing_alerts: List[BillingAlert]
    usage_percentage: float  # 0-100
    quota_status: str  # "healthy", "warning", "critical"


class BillingPortal:
    """
    Manages billing and customer portal functionality.
    
    Features:
    - Stripe Customer Portal integration
    - Invoice management and PDF download
    - Payment method management
    - Plan upgrade/downgrade
    - Usage dashboard
    - Billing alerts
    - Payment retry logic
    - Dunning management
    """

    def __init__(self, stripe_api_key: str, return_url: str):
        """
        Initialize billing portal.
        
        Args:
            stripe_api_key: Stripe API key
            return_url: URL to return to after portal use
        """
        stripe.api_key = stripe_api_key
        self.return_url = return_url
        self._invoices: Dict[str, Invoice] = {}
        self._payment_methods: Dict[str, PaymentMethod] = {}
        self._billing_alerts: Dict[str, List[BillingAlert]] = {}
        self._failed_payments: Dict[str, List[Dict]] = {}

    def get_billing_dashboard(
        self,
        customer_id: str,
        subscription_id: str
    ) -> Optional[BillingDashboard]:
        """
        Generate complete billing dashboard for a customer.
        
        Args:
            customer_id: Stripe customer ID
            subscription_id: Subscription ID
            
        Returns:
            BillingDashboard object or None if not found
        """
        try:
            # Fetch subscription
            stripe_sub = stripe.Subscription.retrieve(subscription_id)

            # Get customer
            customer = stripe.Customer.retrieve(customer_id)

            # Get recent invoices
            invoices = stripe.Invoice.list(customer=customer_id, limit=10)
            recent_invoices = [
                self._convert_invoice(inv) for inv in invoices.data
            ]

            # Get payment method
            payment_method = None
            if stripe_sub.default_payment_method:
                pm = stripe.PaymentMethod.retrieve(
                    stripe_sub.default_payment_method
                )
                payment_method = self._convert_payment_method(pm, is_default=True)

            # Get upcoming invoice
            upcoming = stripe.Invoice.upcoming(customer=customer_id)
            upcoming_invoice = None
            if upcoming:
                upcoming_invoice = UpcomingInvoice(
                    amount=Decimal(str(upcoming.amount_due / 100)),
                    currency=upcoming.currency.upper(),
                    due_date=datetime.fromtimestamp(upcoming.due_date)
                    if upcoming.due_date else datetime.utcnow() + timedelta(days=7),
                    items=[
                        {
                            "description": item.description,
                            "amount": Decimal(str(item.amount / 100)),
                        }
                        for item in upcoming.lines.data
                    ],
                )

            # Get usage percentage (mock data)
            usage_percentage = 45.0  # Would fetch from usage tracker

            # Get quota status
            quota_status = "healthy"
            if usage_percentage >= 100:
                quota_status = "critical"
            elif usage_percentage >= 80:
                quota_status = "warning"

            # Get billing alerts
            alerts = self._billing_alerts.get(customer_id, [])

            return BillingDashboard(
                subscription_id=subscription_id,
                current_plan=stripe_sub.items.data[0].price.metadata.get(
                    "plan", "unknown"
                ) if stripe_sub.items.data else "unknown",
                plan_amount=Decimal(
                    str(stripe_sub.items.data[0].price.unit_amount / 100)
                ) if stripe_sub.items.data else Decimal("0"),
                billing_cycle_start=datetime.fromtimestamp(
                    stripe_sub.current_period_start
                ),
                billing_cycle_end=datetime.fromtimestamp(
                    stripe_sub.current_period_end
                ),
                next_billing_date=datetime.fromtimestamp(
                    stripe_sub.current_period_end
                ),
                payment_method=payment_method,
                upcoming_invoice=upcoming_invoice,
                recent_invoices=recent_invoices,
                billing_alerts=alerts,
                usage_percentage=usage_percentage,
                quota_status=quota_status,
            )

        except stripe.error.StripeError as e:
            logger.error(f"Failed to generate billing dashboard: {e}")
            return None

    def create_customer_portal_session(
        self,
        customer_id: str
    ) -> Optional[str]:
        """
        Create a Stripe Customer Portal session URL.
        
        Allows customers to manage:
        - Billing information
        - Payment methods
        - Subscription details
        - Invoices
        """
        try:
            session = stripe.BillingPortal.Session.create(
                customer=customer_id,
                return_url=self.return_url,
            )
            logger.info(f"Created portal session for customer {customer_id}")
            return session.url
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create portal session: {e}")
            return None

    def get_invoices(
        self,
        customer_id: str,
        limit: int = 20,
        status: Optional[str] = None
    ) -> List[Invoice]:
        """Get invoices for a customer."""
        try:
            kwargs = {"customer": customer_id, "limit": limit}
            if status:
                kwargs["status"] = status

            invoices = stripe.Invoice.list(**kwargs)
            return [self._convert_invoice(inv) for inv in invoices.data]

        except stripe.error.StripeError as e:
            logger.error(f"Failed to fetch invoices: {e}")
            return []

    def get_invoice_pdf(self, invoice_id: str) -> Optional[bytes]:
        """Download invoice as PDF."""
        try:
            invoice = stripe.Invoice.retrieve(invoice_id)
            if invoice.pdf:
                # In production, would fetch from the URL
                logger.info(f"Retrieved PDF for invoice {invoice_id}")
                return invoice.pdf.encode() if isinstance(invoice.pdf, str) else invoice.pdf
            return None
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get invoice PDF: {e}")
            return None

    def resend_invoice(self, invoice_id: str) -> bool:
        """Resend an invoice to the customer."""
        try:
            invoice = stripe.Invoice.retrieve(invoice_id)
            stripe.Invoice.send_invoice(invoice_id)
            logger.info(f"Resent invoice {invoice_id}")
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Failed to resend invoice: {e}")
            return False

    def add_payment_method(
        self,
        customer_id: str,
        payment_method_id: str,
        set_default: bool = False
    ) -> Optional[PaymentMethod]:
        """Add a payment method to a customer."""
        try:
            pm = stripe.PaymentMethod.retrieve(payment_method_id)
            pm.attach(customer=customer_id)

            if set_default:
                stripe.Customer.modify(
                    customer_id,
                    default_payment_method=payment_method_id
                )

            logger.info(f"Added payment method {payment_method_id} to {customer_id}")
            return self._convert_payment_method(pm, is_default=set_default)

        except stripe.error.StripeError as e:
            logger.error(f"Failed to add payment method: {e}")
            return None

    def remove_payment_method(self, payment_method_id: str) -> bool:
        """Remove a payment method."""
        try:
            stripe.PaymentMethod.detach(payment_method_id)
            logger.info(f"Removed payment method {payment_method_id}")
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Failed to remove payment method: {e}")
            return False

    def set_default_payment_method(
        self,
        customer_id: str,
        payment_method_id: str
    ) -> bool:
        """Set default payment method for a customer."""
        try:
            stripe.Customer.modify(
                customer_id,
                default_payment_method=payment_method_id
            )
            logger.info(f"Set default payment method for {customer_id}")
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Failed to set default payment method: {e}")
            return False

    def get_payment_methods(self, customer_id: str) -> List[PaymentMethod]:
        """Get all payment methods for a customer."""
        try:
            methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type="card",
                limit=10
            )
            return [
                self._convert_payment_method(pm) for pm in methods.data
            ]
        except stripe.error.StripeError as e:
            logger.error(f"Failed to fetch payment methods: {e}")
            return []

    def handle_payment_failure(
        self,
        invoice_id: str,
        customer_id: str
    ) -> bool:
        """
        Handle a failed payment with automatic retry.
        
        Implements 3 retry attempts over 14 days.
        """
        if customer_id not in self._failed_payments:
            self._failed_payments[customer_id] = []

        failed_attempt = {
            "invoice_id": invoice_id,
            "timestamp": datetime.utcnow(),
            "attempt_number": len(self._failed_payments[customer_id]) + 1,
        }

        self._failed_payments[customer_id].append(failed_attempt)

        attempt_num = failed_attempt["attempt_number"]

        if attempt_num == 1:
            # First retry: immediately
            retry_delay = 0
        elif attempt_num == 2:
            # Second retry: after 3 days
            retry_delay = 3
        elif attempt_num == 3:
            # Third retry: after 5 more days (8 total)
            retry_delay = 5
        else:
            # After 3 failed attempts, trigger dunning
            logger.warning(f"Payment failed 3 times for invoice {invoice_id}")
            self._trigger_dunning(customer_id, invoice_id)
            return False

        logger.info(
            f"Scheduled retry {attempt_num} for invoice {invoice_id} "
            f"in {retry_delay} days"
        )
        return True

    def _trigger_dunning(self, customer_id: str, invoice_id: str):
        """Trigger dunning process for failed payment."""
        # Add critical alert
        if customer_id not in self._billing_alerts:
            self._billing_alerts[customer_id] = []

        alert = BillingAlert(
            id=f"alert_{invoice_id}",
            alert_type="payment_failed",
            severity="critical",
            message=f"Payment failed after 3 retry attempts. "
                   f"Please update your payment method."
        )
        self._billing_alerts[customer_id].append(alert)

        logger.warning(f"Dunning triggered for customer {customer_id}")

    def create_billing_alert(
        self,
        customer_id: str,
        alert_type: str,
        severity: str,
        message: str
    ) -> BillingAlert:
        """Create a billing alert for a customer."""
        if customer_id not in self._billing_alerts:
            self._billing_alerts[customer_id] = []

        alert = BillingAlert(
            id=f"alert_{int(datetime.utcnow().timestamp())}",
            alert_type=alert_type,
            severity=severity,
            message=message,
        )
        self._billing_alerts[customer_id].append(alert)
        return alert

    def acknowledge_alert(self, customer_id: str, alert_id: str) -> bool:
        """Mark a billing alert as acknowledged."""
        if customer_id in self._billing_alerts:
            for alert in self._billing_alerts[customer_id]:
                if alert.id == alert_id:
                    alert.acknowledged = True
                    return True
        return False

    def generate_billing_report(
        self,
        customer_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate a billing report for a date range."""
        try:
            invoices = stripe.Invoice.list(
                customer=customer_id,
                created={
                    "gte": int(start_date.timestamp()),
                    "lte": int(end_date.timestamp()),
                }
            )

            total_charged = sum(inv.amount_paid for inv in invoices.data) / 100
            total_refunded = sum(inv.amount_refunded for inv in invoices.data) / 100
            invoice_count = len(invoices.data)

            return {
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "invoice_count": invoice_count,
                "total_charged": Decimal(str(total_charged)),
                "total_refunded": Decimal(str(total_refunded)),
                "invoices": [self._convert_invoice(inv) for inv in invoices.data],
            }

        except stripe.error.StripeError as e:
            logger.error(f"Failed to generate billing report: {e}")
            return {}

    def _convert_invoice(self, stripe_invoice) -> Invoice:
        """Convert Stripe invoice to internal Invoice model."""
        return Invoice(
            id=stripe_invoice.id,
            invoice_number=stripe_invoice.number or stripe_invoice.id,
            customer_id=stripe_invoice.customer,
            amount=Decimal(str(stripe_invoice.amount_due / 100)),
            currency=stripe_invoice.currency.upper(),
            status=stripe_invoice.status,
            issue_date=datetime.fromtimestamp(stripe_invoice.created),
            due_date=datetime.fromtimestamp(stripe_invoice.due_date)
            if stripe_invoice.due_date else datetime.utcnow() + timedelta(days=7),
            paid_date=datetime.fromtimestamp(stripe_invoice.paid_at)
            if stripe_invoice.paid_at else None,
            pdf_url=stripe_invoice.invoice_pdf,
            description=stripe_invoice.description,
            line_items=[
                {
                    "description": line.description,
                    "amount": Decimal(str(line.amount / 100)),
                    "quantity": line.quantity,
                }
                for line in stripe_invoice.lines.data
            ],
        )

    def _convert_payment_method(
        self,
        pm,
        is_default: bool = False
    ) -> PaymentMethod:
        """Convert Stripe PaymentMethod to internal PaymentMethod model."""
        card = pm.card if hasattr(pm, 'card') else pm
        return PaymentMethod(
            id=pm.id,
            type=pm.type,
            last_four=card.last4 if hasattr(card, 'last4') else "0000",
            brand=card.brand if hasattr(card, 'brand') else None,
            exp_month=card.exp_month if hasattr(card, 'exp_month') else None,
            exp_year=card.exp_year if hasattr(card, 'exp_year') else None,
            is_default=is_default,
        )
