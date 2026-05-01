"""Pydantic v2 schemas for Billing — Time entries, Expenses, Invoices, Payments."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    import uuid
    from datetime import date, datetime

# ── Time entries ──────────────────────────────────────────────────────────────

class TimeEntryCreate(BaseModel):
    client_id: uuid.UUID | None = None
    case_id: uuid.UUID | None = None
    matter_id: uuid.UUID | None = None
    description: str = Field(..., min_length=1)
    activity_code: str | None = None
    work_date: date
    hours: float = Field(..., gt=0, le=24)
    hourly_rate: float = Field(..., gt=0)
    is_billable: bool = True


class TimeEntryStartTimer(BaseModel):
    client_id: uuid.UUID | None = None
    case_id: uuid.UUID | None = None
    description: str = Field(..., min_length=1)
    activity_code: str | None = None
    hourly_rate: float = Field(..., gt=0)


class TimeEntryStopTimer(BaseModel):
    description: str | None = None  # override description


class TimeEntryResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    client_id: uuid.UUID | None = None
    case_id: uuid.UUID | None = None
    description: str
    work_date: date
    hours: float
    hourly_rate: float
    amount: float
    is_billable: bool
    is_billed: bool
    is_approved: bool
    is_timer_entry: bool
    timer_started_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Expenses ──────────────────────────────────────────────────────────────────

class ExpenseCreate(BaseModel):
    client_id: uuid.UUID | None = None
    case_id: uuid.UUID | None = None
    description: str = Field(..., min_length=1)
    expense_date: date
    amount: float = Field(..., gt=0)
    category: str
    is_billable: bool = True
    receipt_document_id: uuid.UUID | None = None


class ExpenseResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    client_id: uuid.UUID | None = None
    case_id: uuid.UUID | None = None
    description: str
    expense_date: date
    amount: float
    category: str
    is_billable: bool
    is_billed: bool
    receipt_document_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Invoices ──────────────────────────────────────────────────────────────────

class InvoiceLineItemCreate(BaseModel):
    description: str
    item_type: str = Field(..., pattern=r"^(time|expense|flat_fee|discount)$")
    quantity: float = Field(1.0, gt=0)
    unit_price: float
    time_entry_id: uuid.UUID | None = None
    expense_id: uuid.UUID | None = None


class InvoiceCreate(BaseModel):
    client_id: uuid.UUID
    matter_id: uuid.UUID | None = None
    case_id: uuid.UUID | None = None
    invoice_date: date
    due_date: date
    line_items: list[InvoiceLineItemCreate]
    tax_rate: float = Field(0.0, ge=0, le=1)
    discount_amount: float = Field(0.0, ge=0)
    notes: str | None = None
    terms: str | None = None
    footer: str | None = None
    time_entry_ids: list[uuid.UUID] | None = None  # auto-include time entries
    expense_ids: list[uuid.UUID] | None = None


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: uuid.UUID
    matter_id: uuid.UUID | None = None
    invoice_number: str
    invoice_date: date
    due_date: date
    subtotal: float
    tax_rate: float
    tax_amount: float
    discount_amount: float
    total: float
    amount_paid: float
    amount_due: float
    currency: str
    status: str
    notes: str | None = None
    payment_url: str | None = None
    sent_at: datetime | None = None
    paid_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceListResponse(BaseModel):
    items: list[InvoiceResponse]
    total: int
    page: int
    page_size: int
    total_outstanding: float


# ── Payments ──────────────────────────────────────────────────────────────────

class PaymentCreate(BaseModel):
    invoice_id: uuid.UUID | None = None
    client_id: uuid.UUID
    amount: float = Field(..., gt=0)
    payment_method: str
    payment_date: date
    check_number: str | None = None
    reference: str | None = None
    notes: str | None = None


class PaymentResponse(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID | None = None
    client_id: uuid.UUID
    amount: float
    currency: str
    payment_method: str
    status: str
    payment_date: date
    reference: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Trust Accounting ──────────────────────────────────────────────────────────

class TrustTransactionCreate(BaseModel):
    client_id: uuid.UUID
    matter_id: uuid.UUID | None = None
    transaction_type: str = Field(..., pattern=r"^(deposit|withdrawal|disbursement|transfer|refund)$")
    amount: float = Field(..., gt=0)
    description: str = Field(..., min_length=1)
    reference: str | None = None
    transaction_date: date


class TrustTransactionResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    matter_id: uuid.UUID | None = None
    transaction_type: str
    amount: float
    balance_after: float
    description: str
    reference: str | None = None
    transaction_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Reports ───────────────────────────────────────────────────────────────────

class BillingReportRequest(BaseModel):
    date_from: date
    date_to: date
    attorney_id: uuid.UUID | None = None
    client_id: uuid.UUID | None = None
    case_id: uuid.UUID | None = None
    report_type: str = Field("summary", pattern=r"^(summary|detailed|aging|trust)$")
