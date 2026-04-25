"""Pydantic v2 schemas for Billing — Time entries, Expenses, Invoices, Payments."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Time entries ──────────────────────────────────────────────────────────────

class TimeEntryCreate(BaseModel):
    client_id: Optional[uuid.UUID] = None
    case_id: Optional[uuid.UUID] = None
    matter_id: Optional[uuid.UUID] = None
    description: str = Field(..., min_length=1)
    activity_code: Optional[str] = None
    work_date: date
    hours: float = Field(..., gt=0, le=24)
    hourly_rate: float = Field(..., gt=0)
    is_billable: bool = True


class TimeEntryStartTimer(BaseModel):
    client_id: Optional[uuid.UUID] = None
    case_id: Optional[uuid.UUID] = None
    description: str = Field(..., min_length=1)
    activity_code: Optional[str] = None
    hourly_rate: float = Field(..., gt=0)


class TimeEntryStopTimer(BaseModel):
    description: Optional[str] = None  # override description


class TimeEntryResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    client_id: Optional[uuid.UUID] = None
    case_id: Optional[uuid.UUID] = None
    description: str
    work_date: date
    hours: float
    hourly_rate: float
    amount: float
    is_billable: bool
    is_billed: bool
    is_approved: bool
    is_timer_entry: bool
    timer_started_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Expenses ──────────────────────────────────────────────────────────────────

class ExpenseCreate(BaseModel):
    client_id: Optional[uuid.UUID] = None
    case_id: Optional[uuid.UUID] = None
    description: str = Field(..., min_length=1)
    expense_date: date
    amount: float = Field(..., gt=0)
    category: str
    is_billable: bool = True
    receipt_document_id: Optional[uuid.UUID] = None


class ExpenseResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    client_id: Optional[uuid.UUID] = None
    case_id: Optional[uuid.UUID] = None
    description: str
    expense_date: date
    amount: float
    category: str
    is_billable: bool
    is_billed: bool
    receipt_document_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Invoices ──────────────────────────────────────────────────────────────────

class InvoiceLineItemCreate(BaseModel):
    description: str
    item_type: str = Field(..., pattern=r"^(time|expense|flat_fee|discount)$")
    quantity: float = Field(1.0, gt=0)
    unit_price: float
    time_entry_id: Optional[uuid.UUID] = None
    expense_id: Optional[uuid.UUID] = None


class InvoiceCreate(BaseModel):
    client_id: uuid.UUID
    matter_id: Optional[uuid.UUID] = None
    case_id: Optional[uuid.UUID] = None
    invoice_date: date
    due_date: date
    line_items: List[InvoiceLineItemCreate]
    tax_rate: float = Field(0.0, ge=0, le=1)
    discount_amount: float = Field(0.0, ge=0)
    notes: Optional[str] = None
    terms: Optional[str] = None
    footer: Optional[str] = None
    time_entry_ids: Optional[List[uuid.UUID]] = None  # auto-include time entries
    expense_ids: Optional[List[uuid.UUID]] = None


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: uuid.UUID
    matter_id: Optional[uuid.UUID] = None
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
    notes: Optional[str] = None
    payment_url: Optional[str] = None
    sent_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceListResponse(BaseModel):
    items: List[InvoiceResponse]
    total: int
    page: int
    page_size: int
    total_outstanding: float


# ── Payments ──────────────────────────────────────────────────────────────────

class PaymentCreate(BaseModel):
    invoice_id: Optional[uuid.UUID] = None
    client_id: uuid.UUID
    amount: float = Field(..., gt=0)
    payment_method: str
    payment_date: date
    check_number: Optional[str] = None
    reference: Optional[str] = None
    notes: Optional[str] = None


class PaymentResponse(BaseModel):
    id: uuid.UUID
    invoice_id: Optional[uuid.UUID] = None
    client_id: uuid.UUID
    amount: float
    currency: str
    payment_method: str
    status: str
    payment_date: date
    reference: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Trust Accounting ──────────────────────────────────────────────────────────

class TrustTransactionCreate(BaseModel):
    client_id: uuid.UUID
    matter_id: Optional[uuid.UUID] = None
    transaction_type: str = Field(..., pattern=r"^(deposit|withdrawal|disbursement|transfer|refund)$")
    amount: float = Field(..., gt=0)
    description: str = Field(..., min_length=1)
    reference: Optional[str] = None
    transaction_date: date


class TrustTransactionResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    matter_id: Optional[uuid.UUID] = None
    transaction_type: str
    amount: float
    balance_after: float
    description: str
    reference: Optional[str] = None
    transaction_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Reports ───────────────────────────────────────────────────────────────────

class BillingReportRequest(BaseModel):
    date_from: date
    date_to: date
    attorney_id: Optional[uuid.UUID] = None
    client_id: Optional[uuid.UUID] = None
    case_id: Optional[uuid.UUID] = None
    report_type: str = Field("summary", pattern=r"^(summary|detailed|aging|trust)$")
