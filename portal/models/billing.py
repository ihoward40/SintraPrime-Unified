"""
Billing models: Invoice, InvoiceLineItem, Payment, TimeEntry, Expense, TrustAccount.
IOLTA-compliant trust accounting support.
"""

from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import List, Optional

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric,
    String, Text, func, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class TimeEntry(Base):
    """Billable time entries for attorney/staff work on cases."""
    __tablename__ = "time_entries"

    id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    case_id: Mapped[Optional[uuid.UUID]]   = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=True)
    matter_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("matters.id"), nullable=True)
    invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)

    description: Mapped[str]        = mapped_column(Text, nullable=False)
    activity_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # UTBMS activity codes

    # Time tracking
    work_date: Mapped[date]         = mapped_column(Date, nullable=False)
    hours: Mapped[float]            = mapped_column(Numeric(8, 2), nullable=False)
    hourly_rate: Mapped[float]      = mapped_column(Numeric(10, 2), nullable=False)
    amount: Mapped[float]           = mapped_column(Numeric(12, 2), nullable=False)  # hours * rate

    # Timer support
    timer_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    timer_stopped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_timer_entry: Mapped[bool]    = mapped_column(Boolean, default=False)

    # Billing state
    is_billable: Mapped[bool]       = mapped_column(Boolean, default=True)
    is_billed: Mapped[bool]         = mapped_column(Boolean, default=False)
    is_approved: Mapped[bool]       = mapped_column(Boolean, default=False)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"]            = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_time_entries_tenant_id", "tenant_id"),
        Index("ix_time_entries_user_id", "user_id"),
        Index("ix_time_entries_case_id", "case_id"),
        Index("ix_time_entries_work_date", "work_date"),
        Index("ix_time_entries_billed", "is_billed"),
    )


class Expense(Base):
    """Cost advances and disbursements for cases."""
    __tablename__ = "expenses"

    id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    case_id: Mapped[Optional[uuid.UUID]]   = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=True)
    invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)

    description: Mapped[str]        = mapped_column(Text, nullable=False)
    expense_date: Mapped[date]      = mapped_column(Date, nullable=False)
    amount: Mapped[float]           = mapped_column(Numeric(12, 2), nullable=False)
    category: Mapped[str]           = mapped_column(String(50), nullable=False)
    # filing_fee | travel | copies | deposition | expert | other

    is_billable: Mapped[bool]       = mapped_column(Boolean, default=True)
    is_billed: Mapped[bool]         = mapped_column(Boolean, default=False)
    receipt_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)

    created_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_expenses_tenant_id", "tenant_id"),
        Index("ix_expenses_case_id", "case_id"),
    )


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    matter_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("matters.id"), nullable=True)
    case_id: Mapped[Optional[uuid.UUID]]   = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=True)
    created_by: Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    invoice_number: Mapped[str]     = mapped_column(String(50), nullable=False)
    invoice_date: Mapped[date]      = mapped_column(Date, nullable=False)
    due_date: Mapped[date]          = mapped_column(Date, nullable=False)

    # Amounts
    subtotal: Mapped[float]         = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tax_rate: Mapped[float]         = mapped_column(Numeric(5, 4), nullable=False, default=0)
    tax_amount: Mapped[float]       = mapped_column(Numeric(12, 2), nullable=False, default=0)
    discount_amount: Mapped[float]  = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total: Mapped[float]            = mapped_column(Numeric(12, 2), nullable=False, default=0)
    amount_paid: Mapped[float]      = mapped_column(Numeric(12, 2), nullable=False, default=0)
    amount_due: Mapped[float]       = mapped_column(Numeric(12, 2), nullable=False, default=0)
    currency: Mapped[str]           = mapped_column(String(3), default="USD")

    # Status
    status: Mapped[str]             = mapped_column(String(20), default="draft")
    # draft | sent | viewed | partial | paid | overdue | voided | refunded

    # Notes
    notes: Mapped[Optional[str]]    = mapped_column(Text, nullable=True)
    terms: Mapped[Optional[str]]    = mapped_column(Text, nullable=True)
    footer: Mapped[Optional[str]]   = mapped_column(Text, nullable=True)

    # PDF
    pdf_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)

    # Payment link
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    payment_url: Mapped[Optional[str]]               = mapped_column(Text, nullable=True)

    # Sent/viewed timestamps
    sent_at: Mapped[Optional[datetime]]    = mapped_column(DateTime(timezone=True), nullable=True)
    viewed_at: Mapped[Optional[datetime]]  = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[Optional[datetime]]    = mapped_column(DateTime(timezone=True), nullable=True)
    voided_at: Mapped[Optional[datetime]]  = mapped_column(DateTime(timezone=True), nullable=True)
    void_reason: Mapped[Optional[str]]     = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    line_items: Mapped[List["InvoiceLineItem"]] = relationship("InvoiceLineItem", back_populates="invoice", lazy="selectin")
    payments: Mapped[List["Payment"]]           = relationship("Payment", back_populates="invoice", lazy="select")

    __table_args__ = (
        Index("ix_invoices_tenant_id", "tenant_id"),
        Index("ix_invoices_client_id", "client_id"),
        Index("ix_invoices_status", "status"),
        Index("ix_invoices_due_date", "due_date"),
        UniqueConstraint("tenant_id", "invoice_number", name="uq_invoices_number"),
    )


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    time_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("time_entries.id"), nullable=True)
    expense_id: Mapped[Optional[uuid.UUID]]    = mapped_column(UUID(as_uuid=True), ForeignKey("expenses.id"), nullable=True)

    description: Mapped[str]        = mapped_column(Text, nullable=False)
    item_type: Mapped[str]          = mapped_column(String(20), nullable=False)  # time | expense | flat_fee | discount
    quantity: Mapped[float]         = mapped_column(Numeric(10, 2), default=1)
    unit_price: Mapped[float]       = mapped_column(Numeric(12, 2), nullable=False)
    amount: Mapped[float]           = mapped_column(Numeric(12, 2), nullable=False)
    sort_order: Mapped[int]         = mapped_column(Integer, default=0)

    invoice: Mapped["Invoice"]      = relationship("Invoice", back_populates="line_items")

    __table_args__ = (Index("ix_invoice_items_invoice_id", "invoice_id"),)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    client_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)

    amount: Mapped[float]           = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str]           = mapped_column(String(3), default="USD")
    payment_method: Mapped[str]     = mapped_column(String(30), nullable=False)
    # stripe | ach | check | wire | cash | trust

    status: Mapped[str]             = mapped_column(String(20), default="pending")
    # pending | processing | succeeded | failed | refunded

    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_charge_id: Mapped[Optional[str]]         = mapped_column(String(255), nullable=True)
    check_number: Mapped[Optional[str]]             = mapped_column(String(50), nullable=True)
    reference: Mapped[Optional[str]]                = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]]                    = mapped_column(Text, nullable=True)

    payment_date: Mapped[date]      = mapped_column(Date, nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[Optional[datetime]]  = mapped_column(DateTime(timezone=True), nullable=True)
    refund_amount: Mapped[Optional[float]]   = mapped_column(Numeric(12, 2), nullable=True)
    refund_reason: Mapped[Optional[str]]     = mapped_column(Text, nullable=True)

    received_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now())

    invoice: Mapped[Optional["Invoice"]] = relationship("Invoice", back_populates="payments")

    __table_args__ = (
        Index("ix_payments_tenant_id", "tenant_id"),
        Index("ix_payments_invoice_id", "invoice_id"),
        Index("ix_payments_client_id", "client_id"),
        Index("ix_payments_status", "status"),
    )


class TrustAccount(Base):
    """IOLTA trust account ledger entries."""
    __tablename__ = "trust_accounts"

    id: Mapped[uuid.UUID]           = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    matter_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("matters.id"), nullable=True)

    transaction_type: Mapped[str]   = mapped_column(String(20), nullable=False)
    # deposit | withdrawal | disbursement | transfer | refund

    amount: Mapped[float]           = mapped_column(Numeric(12, 2), nullable=False)
    balance_after: Mapped[float]    = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str]        = mapped_column(Text, nullable=False)
    reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    transaction_date: Mapped[date]  = mapped_column(Date, nullable=False)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_by: Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    created_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_trust_tenant_id", "tenant_id"),
        Index("ix_trust_client_id", "client_id"),
        Index("ix_trust_date", "transaction_date"),
    )
