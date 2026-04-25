"""Billing calculations, invoice number generation, and PDF export."""

from __future__ import annotations

import io
import uuid
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger()


async def generate_invoice_number(db: AsyncSession, tenant_id: uuid.UUID | str) -> str:
    """Generate a sequential invoice number: INV-2026-0001."""
    from ..models.billing import Invoice
    year = date.today().year
    count_result = await db.execute(
        select(func.count(Invoice.id)).where(
            Invoice.tenant_id == uuid.UUID(str(tenant_id))
        )
    )
    count = (count_result.scalar() or 0) + 1
    return f"INV-{year}-{count:04d}"


def calculate_invoice_totals(
    line_items: list,
    tax_rate: Optional[float] = None,
    discount_amount: Optional[float] = None,
) -> Tuple[float, float, float]:
    """
    Calculate subtotal, tax, and total for an invoice.

    Returns:
        (subtotal, tax_amount, total)
    """
    subtotal = Decimal("0")
    for item in line_items:
        qty = Decimal(str(item.quantity))
        price = Decimal(str(item.unit_price))
        subtotal += (qty * price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    discount = Decimal(str(discount_amount or 0))
    taxable = subtotal - discount

    if tax_rate:
        tax_decimal = Decimal(str(tax_rate)) / Decimal("100")
        tax_amount = (taxable * tax_decimal).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        tax_amount = Decimal("0")

    total = (taxable + tax_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return float(subtotal), float(tax_amount), float(total)


async def generate_invoice_pdf(invoice: object) -> bytes:
    """
    Generate a professional PDF invoice.
    Uses reportlab if available, otherwise returns a minimal PDF placeholder.
    """
    try:
        from reportlab.lib import colors  # type: ignore
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        )

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )
        styles = getSampleStyleSheet()
        story = []

        # Header
        story.append(Paragraph("INVOICE", styles["Title"]))
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(f"Invoice #: {invoice.invoice_number}", styles["Normal"]))
        story.append(Paragraph(f"Date: {invoice.invoice_date}", styles["Normal"]))
        story.append(Paragraph(f"Due Date: {invoice.due_date}", styles["Normal"]))
        story.append(Spacer(1, 0.5*cm))

        # Totals
        data = [
            ["Subtotal", f"${invoice.subtotal:,.2f}"],
            ["Tax", f"${invoice.tax_amount:,.2f}"],
            ["Total", f"${invoice.total:,.2f}"],
            ["Amount Due", f"${invoice.amount_due:,.2f}"],
        ]
        table = Table(data, colWidths=[10*cm, 5*cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 3), (-1, 3), colors.lightgrey),
            ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.5*cm))

        if invoice.notes:
            story.append(Paragraph(f"Notes: {invoice.notes}", styles["Normal"]))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    except ImportError:
        log.warning("reportlab.not_installed", msg="Returning placeholder PDF")
        return _minimal_pdf_placeholder(invoice)


def _minimal_pdf_placeholder(invoice: object) -> bytes:
    """Minimal valid PDF if reportlab is not installed."""
    content = f"""Invoice #{getattr(invoice, 'invoice_number', 'N/A')}
Total: ${getattr(invoice, 'total', 0):,.2f}
Amount Due: ${getattr(invoice, 'amount_due', 0):,.2f}
"""
    return content.encode()


def hours_to_decimal(hours: int, minutes: int) -> float:
    """Convert hours + minutes to decimal hours (e.g. 1h 30m → 1.5)."""
    return round(hours + minutes / 60, 2)


def statute_of_limitations_deadline(
    incident_date: date,
    jurisdiction: str,
    case_type: str,
) -> Optional[date]:
    """
    Calculate statute of limitations deadline.
    Simplified lookup — in production this would use a comprehensive legal database.
    """
    from datetime import timedelta
    from dateutil.relativedelta import relativedelta  # type: ignore

    # Default periods (in years) — simplified
    LIMITATIONS = {
        ("personal_injury", "CA"): 2,
        ("personal_injury", "NY"): 3,
        ("personal_injury", "TX"): 2,
        ("contract", "CA"): 4,
        ("contract", "NY"): 6,
        ("medical_malpractice", "CA"): 3,
        ("fraud", "CA"): 3,
        ("default", "default"): 3,
    }

    key = (case_type.lower(), jurisdiction.upper())
    years = LIMITATIONS.get(key, LIMITATIONS.get(("default", "default"), 3))

    try:
        return incident_date + relativedelta(years=years)
    except Exception:
        return None
