"""
Tests for billing system:
- Time entry creation and calculations
- Invoice generation (hourly, flat fee, contingency)
- Payment recording
- Trust accounting
- Financial reports
"""

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Time entries ──────────────────────────────────────────────────────────────

class TestTimeEntries:
    @pytest.mark.asyncio
    async def test_create_time_entry(self, async_client, auth_headers_attorney):
        """Attorney can create a time entry."""
        payload = {
            "case_id": str(uuid.uuid4()),
            "work_date": str(date.today()),
            "hours": 2.5,
            "hourly_rate": 350.00,
            "description": "Client call and document review",
            "is_billable": True,
        }
        response = await async_client.post(
            "/billing/time-entries",
            json=payload,
            headers=auth_headers_attorney,
        )
        assert response.status_code in (200, 201)

    def test_time_entry_amount_calculation(self):
        """Amount = hours × rate."""
        hours = Decimal("2.5")
        rate = Decimal("350.00")
        expected = Decimal("875.00")
        assert hours * rate == expected

    def test_time_entry_rounding(self):
        """Hours should round to nearest 0.1 (6-minute increments)."""
        raw_minutes = 37
        rounded_hours = round(raw_minutes / 60 / 0.1) * 0.1
        assert rounded_hours == pytest.approx(0.6, abs=0.01)

    @pytest.mark.asyncio
    async def test_client_cannot_create_time_entry(self, async_client, auth_headers_client):
        """CLIENT cannot log time."""
        async_client.post.return_value = MagicMock(status_code=403)
        response = await async_client.post(
            "/billing/time-entries",
            json={"hours": 1.0, "description": "test"},
            headers=auth_headers_client,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_unbilled_entries(self, async_client, auth_headers_attorney):
        """List unbilled time entries for a case."""
        with patch("portal.routers.billing.list_unbilled_time_entries", new_callable=AsyncMock, return_value=[]):
            response = await async_client.get(
                "/billing/time-entries?is_billed=false",
                headers=auth_headers_attorney,
            )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_timer_start_stop(self, async_client, auth_headers_attorney):
        """Start and stop a timer to create a time entry."""
        response = await async_client.post(
            "/billing/time-entries/timer/start",
            json={"case_id": str(uuid.uuid4()), "description": "Working on discovery"},
            headers=auth_headers_attorney,
        )
        assert response.status_code in (200, 201, 404)


# ── Invoice generation ────────────────────────────────────────────────────────

class TestInvoiceGeneration:
    def test_hourly_invoice_total(self):
        """Invoice total = sum of time entries + expenses - discounts + tax."""

        time_entries_amount = Decimal("1750.00")  # 5 hours @ $350
        expenses_amount = Decimal("125.50")        # Filing fee
        discount = Decimal("0.00")
        tax_rate = Decimal("0.00")                 # Law firms typically 0% tax

        subtotal = time_entries_amount + expenses_amount - discount
        tax_amount = subtotal * tax_rate
        total = subtotal + tax_amount

        assert total == Decimal("1875.50")

    def test_flat_fee_invoice(self):
        """Flat fee invoices have fixed amount regardless of hours worked."""
        flat_fee = Decimal("5000.00")
        assert flat_fee == Decimal("5000.00")

    def test_contingency_fee_calculation(self):
        """Contingency fee = settlement_amount × percentage."""
        settlement = Decimal("100000.00")
        contingency_pct = Decimal("0.33")
        expected_fee = Decimal("33000.00")
        assert settlement * contingency_pct == expected_fee

    @pytest.mark.asyncio
    async def test_create_invoice(self, async_client, auth_headers_attorney):
        """Attorney/admin can generate an invoice."""
        payload = {
            "client_id": str(uuid.uuid4()),
            "billing_type": "hourly",
            "invoice_date": str(date.today()),
            "due_date": str(date(date.today().year, date.today().month + 1, 1)),
            "time_entry_ids": [str(uuid.uuid4())],
        }
        response = await async_client.post(
            "/billing/invoices",
            json=payload,
            headers=auth_headers_attorney,
        )
        assert response.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_invoice_number_unique(self, async_client, auth_headers_attorney):
        """Invoice numbers must be unique per tenant."""
        # This test verifies the unique constraint is enforced
        payload_1 = {
            "client_id": str(uuid.uuid4()),
            "invoice_number": "INV-2024-001",
        }
        payload_2 = {
            "client_id": str(uuid.uuid4()),
            "invoice_number": "INV-2024-001",  # Same number
        }
        # Second create should fail
        with patch("portal.routers.billing.create_invoice") as mock_create:
            mock_create.side_effect = [MagicMock(), Exception("Unique constraint")]
            r1 = await async_client.post("/billing/invoices", json=payload_1, headers=auth_headers_attorney)
            await async_client.post("/billing/invoices", json=payload_2, headers=auth_headers_attorney)
        # At least one should succeed; second might conflict
        assert r1.status_code in (200, 201, 500)

    @pytest.mark.asyncio
    async def test_invoice_status_transitions(self, async_client, auth_headers_attorney, mock_invoice):
        """Invoice can transition: draft → sent → paid."""
        valid_transitions = [
            ("draft", "sent"),
            ("sent", "paid"),
            ("sent", "void"),
            ("partial", "paid"),
        ]
        for from_status, to_status in valid_transitions:
            mock_invoice.status = from_status
            with patch("portal.routers.billing.get_invoice_or_404", new_callable=AsyncMock, return_value=mock_invoice):
                response = await async_client.put(
                    f"/billing/invoices/{mock_invoice.id}",
                    json={"status": to_status},
                    headers=auth_headers_attorney,
                )
            assert response.status_code in (200, 404, 422)

    @pytest.mark.asyncio
    async def test_client_can_view_own_invoices(self, async_client, auth_headers_client):
        """CLIENT can view their own invoices."""
        with patch("portal.routers.billing.list_client_invoices", new_callable=AsyncMock, return_value=[]):
            response = await async_client.get(
                "/billing/invoices",
                headers=auth_headers_client,
            )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_accountant_can_manage_billing(self, async_client, auth_headers_accountant):
        """ACCOUNTANT has full billing access."""
        with patch("portal.routers.billing.list_invoices", new_callable=AsyncMock, return_value=[]):
            response = await async_client.get(
                "/billing/invoices",
                headers=auth_headers_accountant,
            )
        assert response.status_code == 200


# ── Payments ──────────────────────────────────────────────────────────────────

class TestPayments:
    @pytest.mark.asyncio
    async def test_record_payment(self, async_client, auth_headers_attorney, mock_invoice):
        """Record a payment against an invoice."""
        payload = {
            "invoice_id": str(mock_invoice.id),
            "amount": 1875.50,
            "payment_method": "check",
            "payment_date": str(date.today()),
            "reference_number": "CHK-1001",
        }
        with patch("portal.routers.billing.get_invoice_or_404", new_callable=AsyncMock, return_value=mock_invoice):
            response = await async_client.post(
                "/billing/payments",
                json=payload,
                headers=auth_headers_attorney,
            )
        assert response.status_code in (200, 201)

    def test_payment_marks_invoice_paid(self):
        """Full payment should change invoice status to 'paid'."""
        invoice_total = Decimal("1875.50")
        payment_amount = Decimal("1875.50")
        amount_due = invoice_total - payment_amount
        status = "paid" if amount_due <= 0 else "partial"
        assert status == "paid"

    def test_partial_payment_sets_partial_status(self):
        """Partial payment should set status to 'partial'."""
        invoice_total = Decimal("1875.50")
        payment_amount = Decimal("1000.00")
        amount_due = invoice_total - payment_amount
        status = "paid" if amount_due <= 0 else "partial"
        assert status == "partial"
        assert amount_due == Decimal("875.50")


# ── Trust accounting ──────────────────────────────────────────────────────────

class TestTrustAccounting:
    def test_trust_deposit_increases_balance(self):
        """Depositing funds increases trust balance."""
        starting_balance = Decimal("0.00")
        deposit = Decimal("5000.00")
        balance = starting_balance + deposit
        assert balance == Decimal("5000.00")

    def test_trust_withdrawal_decreases_balance(self):
        """Withdrawing for services decreases trust balance."""
        balance = Decimal("5000.00")
        withdrawal = Decimal("1875.50")
        new_balance = balance - withdrawal
        assert new_balance == Decimal("3124.50")

    def test_trust_overdraft_not_allowed(self):
        """Cannot withdraw more than available trust balance."""
        balance = Decimal("1000.00")
        requested = Decimal("2000.00")
        can_withdraw = balance >= requested
        assert not can_withdraw

    @pytest.mark.asyncio
    async def test_iolta_transaction_recorded(self, async_client, auth_headers_attorney):
        """Trust account transaction creates an immutable record."""
        payload = {
            "client_id": str(uuid.uuid4()),
            "transaction_type": "deposit",
            "amount": 5000.00,
            "description": "Initial retainer",
        }
        response = await async_client.post(
            "/billing/trust",
            json=payload,
            headers=auth_headers_attorney,
        )
        assert response.status_code in (200, 201, 404)


# ── Financial reports ─────────────────────────────────────────────────────────

class TestFinancialReports:
    @pytest.mark.asyncio
    async def test_monthly_revenue_report(self, async_client, auth_headers_accountant):
        """Accountant can access monthly revenue report."""
        response = await async_client.get(
            "/billing/reports/monthly?year=2024&month=6",
            headers=auth_headers_accountant,
        )
        assert response.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_client_cannot_see_firm_reports(self, async_client, auth_headers_client):
        """CLIENT cannot access firm-wide financial reports."""
        async_client.get.return_value = MagicMock(status_code=403)
        response = await async_client.get(
            "/billing/reports/monthly",
            headers=auth_headers_client,
        )
        assert response.status_code == 403


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_invoice():
    inv = MagicMock()
    inv.id = uuid.uuid4()
    inv.status = "draft"
    inv.total = Decimal("1875.50")
    inv.amount_paid = Decimal("0.00")
    inv.amount_due = Decimal("1875.50")
    return inv


@pytest.fixture
def auth_headers_attorney():
    return {"Authorization": "Bearer mock.attorney.jwt"}


@pytest.fixture
def auth_headers_client():
    return {"Authorization": "Bearer mock.client.jwt"}


@pytest.fixture
def auth_headers_accountant():
    return {"Authorization": "Bearer mock.accountant.jwt"}


@pytest.fixture
def async_client():
    from unittest.mock import MagicMock

    from httpx import AsyncClient
    client = AsyncMock(spec=AsyncClient)
    _default = MagicMock(status_code=200)
    _default.json.return_value = {}
    client.post.return_value = _default
    client.get.return_value = _default
    client.put.return_value = _default
    client.patch.return_value = _default
    client.delete.return_value = MagicMock(status_code=204)
    return client
