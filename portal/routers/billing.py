"""Billing router — time entries, expenses, invoices, payments, trust accounting."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.rbac import CurrentUser, Permission, require_permissions
from ..database import get_db
from ..models.billing import (
    Expense, Invoice, InvoiceLineItem, Payment, TimeEntry, TrustAccount
)
from ..schemas.billing import (
    BillingReportRequest,
    ExpenseCreate, ExpenseResponse,
    InvoiceCreate, InvoiceListResponse, InvoiceResponse,
    PaymentCreate, PaymentResponse,
    TimeEntryCreate, TimeEntryResponse, TimeEntryStartTimer,
    TrustTransactionCreate, TrustTransactionResponse,
)
from ..services.audit_service import audit
from ..services.billing_service import (
    calculate_invoice_totals,
    generate_invoice_number,
    generate_invoice_pdf,
)
from ..services.notification_service import notify_users

router = APIRouter()


# ── Time Entries ──────────────────────────────────────────────────────────────

@router.post("/time-entries", response_model=TimeEntryResponse, status_code=201)
async def create_time_entry(
    body: TimeEntryCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.BILLING_TIME_TRACK)),
    db: AsyncSession = Depends(get_db),
):
    amount = round(body.hours * body.hourly_rate, 2)
    entry = TimeEntry(
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        amount=amount,
        **body.model_dump(),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return TimeEntryResponse.model_validate(entry)


@router.post("/time-entries/start-timer", response_model=TimeEntryResponse, status_code=201)
async def start_timer(
    body: TimeEntryStartTimer,
    current_user: CurrentUser = Depends(require_permissions(Permission.BILLING_TIME_TRACK)),
    db: AsyncSession = Depends(get_db),
):
    """Start a running timer for a time entry."""
    entry = TimeEntry(
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        client_id=body.client_id,
        case_id=body.case_id,
        description=body.description,
        activity_code=body.activity_code,
        work_date=date.today(),
        hours=0.0,
        hourly_rate=body.hourly_rate,
        amount=0.0,
        is_timer_entry=True,
        timer_started_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return TimeEntryResponse.model_validate(entry)


@router.post("/time-entries/{entry_id}/stop-timer", response_model=TimeEntryResponse)
async def stop_timer(
    entry_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permissions(Permission.BILLING_TIME_TRACK)),
    db: AsyncSession = Depends(get_db),
):
    """Stop a running timer and calculate hours."""
    result = await db.execute(
        select(TimeEntry).where(
            TimeEntry.id == entry_id,
            TimeEntry.user_id == current_user.user_id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry or not entry.is_timer_entry or not entry.timer_started_at:
        raise HTTPException(status_code=404, detail="Timer not found")

    stop_time = datetime.now(timezone.utc)
    duration = stop_time - entry.timer_started_at
    hours = round(duration.total_seconds() / 3600, 2)

    entry.timer_stopped_at = stop_time
    entry.hours = hours
    entry.amount = round(hours * entry.hourly_rate, 2)
    entry.work_date = stop_time.date()

    await db.commit()
    await db.refresh(entry)
    return TimeEntryResponse.model_validate(entry)


@router.get("/time-entries", response_model=List[TimeEntryResponse])
async def list_time_entries(
    case_id: Optional[uuid.UUID] = Query(None),
    client_id: Optional[uuid.UUID] = Query(None),
    user_id: Optional[uuid.UUID] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    is_billed: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(require_permissions(Permission.BILLING_READ)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(TimeEntry).where(
        TimeEntry.tenant_id == current_user.tenant_id,
        TimeEntry.deleted_at.is_(None),
    )
    if case_id:
        stmt = stmt.where(TimeEntry.case_id == case_id)
    if client_id:
        stmt = stmt.where(TimeEntry.client_id == client_id)
    if user_id:
        # Non-admin can only see their own
        if not current_user.is_staff() or current_user.is_client():
            user_id = uuid.UUID(current_user.user_id)
        stmt = stmt.where(TimeEntry.user_id == user_id)
    if date_from:
        stmt = stmt.where(TimeEntry.work_date >= date_from)
    if date_to:
        stmt = stmt.where(TimeEntry.work_date <= date_to)
    if is_billed is not None:
        stmt = stmt.where(TimeEntry.is_billed == is_billed)

    stmt = stmt.offset((page-1)*page_size).limit(page_size).order_by(TimeEntry.work_date.desc())
    result = await db.execute(stmt)
    return [TimeEntryResponse.model_validate(e) for e in result.scalars().all()]


# ── Expenses ──────────────────────────────────────────────────────────────────

@router.post("/expenses", response_model=ExpenseResponse, status_code=201)
async def create_expense(
    body: ExpenseCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.BILLING_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    expense = Expense(
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        **body.model_dump(),
    )
    db.add(expense)
    await db.commit()
    await db.refresh(expense)
    return ExpenseResponse.model_validate(expense)


# ── Invoices ──────────────────────────────────────────────────────────────────

@router.post("/invoices", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    body: InvoiceCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.BILLING_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    invoice_number = await generate_invoice_number(db, current_user.tenant_id)
    subtotal, tax_amount, total = calculate_invoice_totals(
        body.line_items, body.tax_rate, body.discount_amount
    )

    invoice = Invoice(
        tenant_id=current_user.tenant_id,
        invoice_number=invoice_number,
        created_by=current_user.user_id,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total=total,
        amount_due=total,
        **body.model_dump(exclude={"line_items", "time_entry_ids", "expense_ids"}),
    )
    db.add(invoice)
    await db.flush()

    # Create line items
    for i, item in enumerate(body.line_items):
        line = InvoiceLineItem(
            invoice_id=invoice.id,
            sort_order=i,
            amount=round(item.quantity * item.unit_price, 2),
            **item.model_dump(),
        )
        db.add(line)

    # Mark time entries as billed
    if body.time_entry_ids:
        entries_result = await db.execute(
            select(TimeEntry).where(TimeEntry.id.in_(body.time_entry_ids))
        )
        for entry in entries_result.scalars().all():
            entry.is_billed = True
            entry.invoice_id = invoice.id

    await db.commit()
    await db.refresh(invoice)

    await audit(db, action="invoice_create", user_id=current_user.user_id,
                tenant_id=current_user.tenant_id,
                resource_type="invoice", resource_id=str(invoice.id),
                resource_name=invoice.invoice_number)
    return InvoiceResponse.model_validate(invoice)


@router.get("/invoices", response_model=InvoiceListResponse)
async def list_invoices(
    client_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_permissions(Permission.BILLING_READ)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Invoice).where(
        Invoice.tenant_id == current_user.tenant_id,
        Invoice.deleted_at.is_(None),
    )
    if client_id:
        stmt = stmt.where(Invoice.client_id == client_id)
    if status:
        stmt = stmt.where(Invoice.status == status)
    if date_from:
        stmt = stmt.where(Invoice.invoice_date >= date_from)
    if date_to:
        stmt = stmt.where(Invoice.invoice_date <= date_to)

    # CLIENT: only their invoices
    if current_user.is_client():
        from ..models.client import Client
        cl_result = await db.execute(
            select(Client.id).where(Client.portal_user_id == current_user.user_id)
        )
        client_ids = cl_result.scalars().all()
        stmt = stmt.where(Invoice.client_id.in_(client_ids))

    total_q = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_q.scalar() or 0

    outstanding_q = await db.execute(
        select(func.sum(Invoice.amount_due)).select_from(stmt.subquery())
    )
    total_outstanding = float(outstanding_q.scalar() or 0)

    stmt = stmt.offset((page-1)*page_size).limit(page_size).order_by(Invoice.invoice_date.desc())
    result = await db.execute(stmt)
    invoices = result.scalars().all()

    return InvoiceListResponse(
        items=[InvoiceResponse.model_validate(inv) for inv in invoices],
        total=total,
        page=page,
        page_size=page_size,
        total_outstanding=total_outstanding,
    )


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permissions(Permission.BILLING_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.tenant_id == current_user.tenant_id,
        )
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404)
    return InvoiceResponse.model_validate(inv)


@router.post("/invoices/{invoice_id}/send", response_model=InvoiceResponse)
async def send_invoice(
    invoice_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permissions(Permission.BILLING_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.tenant_id == current_user.tenant_id,
        )
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404)
    if inv.status != "draft":
        raise HTTPException(status_code=400, detail="Can only send draft invoices")

    inv.status = "sent"
    inv.sent_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(inv)

    # Notify client
    await notify_users(
        db=db,
        tenant_id=current_user.tenant_id,
        event_type="invoice_sent",
        resource_id=str(inv.id),
        resource_name=inv.invoice_number,
        actor_id=current_user.user_id,
        related_client_id=str(inv.client_id),
    )
    await audit(db, action="invoice_send", user_id=current_user.user_id,
                tenant_id=current_user.tenant_id,
                resource_type="invoice", resource_id=str(inv.id))
    return InvoiceResponse.model_validate(inv)


@router.get("/invoices/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permissions(Permission.BILLING_READ)),
    db: AsyncSession = Depends(get_db),
):
    """Generate and download invoice as PDF."""
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.tenant_id == current_user.tenant_id,
        )
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404)

    from fastapi.responses import StreamingResponse
    import io
    pdf_bytes = await generate_invoice_pdf(inv)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="invoice-{inv.invoice_number}.pdf"'},
    )


# ── Payments ──────────────────────────────────────────────────────────────────

@router.post("/payments", response_model=PaymentResponse, status_code=201)
async def record_payment(
    body: PaymentCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.PAYMENT_PROCESS)),
    db: AsyncSession = Depends(get_db),
):
    payment = Payment(
        tenant_id=current_user.tenant_id,
        received_by=current_user.user_id,
        status="succeeded",
        processed_at=datetime.now(timezone.utc),
        **body.model_dump(),
    )
    db.add(payment)

    # Update invoice if linked
    if body.invoice_id:
        inv_result = await db.execute(select(Invoice).where(Invoice.id == body.invoice_id))
        inv = inv_result.scalar_one_or_none()
        if inv:
            inv.amount_paid += body.amount
            inv.amount_due = max(0, inv.total - inv.amount_paid)
            if inv.amount_due <= 0:
                inv.status = "paid"
                inv.paid_at = datetime.now(timezone.utc)
            elif inv.amount_paid > 0:
                inv.status = "partial"

    await db.commit()
    await db.refresh(payment)
    await audit(db, action="payment_received", user_id=current_user.user_id,
                tenant_id=current_user.tenant_id,
                resource_type="payment", resource_id=str(payment.id),
                details={"amount": body.amount})
    return PaymentResponse.model_validate(payment)


# ── Trust Accounting ──────────────────────────────────────────────────────────

@router.post("/trust-transactions", response_model=TrustTransactionResponse, status_code=201)
async def record_trust_transaction(
    body: TrustTransactionCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.BILLING_TRUST)),
    db: AsyncSession = Depends(get_db),
):
    # Calculate new balance
    balance_q = await db.execute(
        select(func.max(TrustAccount.balance_after)).where(
            TrustAccount.tenant_id == current_user.tenant_id,
            TrustAccount.client_id == body.client_id,
        )
    )
    current_balance = float(balance_q.scalar() or 0)
    signed_amount = body.amount if body.transaction_type == "deposit" else -body.amount
    new_balance = current_balance + signed_amount

    if new_balance < 0:
        raise HTTPException(status_code=400, detail="Insufficient trust funds")

    tx = TrustAccount(
        tenant_id=current_user.tenant_id,
        balance_after=new_balance,
        created_by=current_user.user_id,
        approved_by=current_user.user_id,
        **body.model_dump(),
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    await audit(db, action="trust_transaction", user_id=current_user.user_id,
                tenant_id=current_user.tenant_id,
                details={"type": body.transaction_type, "amount": body.amount, "balance_after": new_balance})
    return TrustTransactionResponse.model_validate(tx)


@router.get("/trust-transactions/{client_id}", response_model=List[TrustTransactionResponse])
async def get_trust_ledger(
    client_id: uuid.UUID,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    current_user: CurrentUser = Depends(require_permissions(Permission.BILLING_TRUST)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(TrustAccount).where(
        TrustAccount.tenant_id == current_user.tenant_id,
        TrustAccount.client_id == client_id,
    )
    if date_from:
        stmt = stmt.where(TrustAccount.transaction_date >= date_from)
    if date_to:
        stmt = stmt.where(TrustAccount.transaction_date <= date_to)
    result = await db.execute(stmt.order_by(TrustAccount.transaction_date.asc()))
    return [TrustTransactionResponse.model_validate(t) for t in result.scalars().all()]
