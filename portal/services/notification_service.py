"""
Notification service: email + push + in-app.
Sends notifications based on system events.
"""

from __future__ import annotations

import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings

log = structlog.get_logger()
settings = get_settings()


EVENT_TITLES = {
    "document_uploaded": "New document uploaded",
    "document_shared": "A document has been shared with you",
    "new_message": "New message received",
    "case_stage_changed": "Case status updated",
    "invoice_sent": "New invoice generated",
    "invoice_paid": "Invoice payment received",
    "deadline_approaching": "Upcoming deadline reminder",
    "new_case_assigned": "You have been assigned a new case",
}


async def notify_users(
    db: AsyncSession,
    tenant_id: uuid.UUID | str,
    event_type: str,
    resource_id: str,
    resource_name: str,
    actor_id: str,
    recipient_ids: Optional[List[str]] = None,
    related_client_id: Optional[str] = None,
    related_case_id: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """Create in-app notifications and optionally send email/push."""
    from ..routers.notifications import Notification  # lazy to avoid circular import
    from ..models.user import User

    title = EVENT_TITLES.get(event_type, event_type.replace("_", " ").title())
    body = f"{resource_name}" if resource_name else None

    # Determine recipients if not specified
    if recipient_ids is None:
        recipient_ids = await _resolve_recipients(
            db, tenant_id, event_type, related_client_id, related_case_id
        )

    for user_id in recipient_ids:
        # Skip notifying the actor themselves
        if user_id == str(actor_id):
            continue

        notif = Notification(
            tenant_id=uuid.UUID(str(tenant_id)),
            user_id=uuid.UUID(user_id),
            event_type=event_type,
            title=title,
            body=body,
            resource_id=resource_id,
            actor_id=str(actor_id),
            extra_data=details,
        )
        db.add(notif)

    await db.commit()

    # Push email (non-blocking fire-and-forget style)
    if settings.SMTP_HOST and recipient_ids:
        user_result = await db.execute(
            select(User.email, User.first_name, User.notify_email).where(
                User.id.in_([uuid.UUID(r) for r in recipient_ids if r != str(actor_id)])
            )
        )
        for email, fname, notify_email in user_result.all():
            if notify_email:
                await send_email(
                    to=email,
                    subject=title,
                    body=f"Hello {fname},\n\n{body or title}\n\nLogin to view: {settings.BASE_URL}",
                )


async def _resolve_recipients(
    db: AsyncSession,
    tenant_id: uuid.UUID | str,
    event_type: str,
    client_id: Optional[str] = None,
    case_id: Optional[str] = None,
) -> List[str]:
    """Auto-resolve who should receive a notification based on event context."""
    from ..models.user import User
    # For now: return all staff in tenant
    from ..models.user import Role as RoleModel
    result = await db.execute(
        select(User.id).where(
            User.tenant_id == uuid.UUID(str(tenant_id)),
            User.is_active == True,
        ).limit(50)
    )
    return [str(r[0]) for r in result.all()]


async def send_email(to: str, subject: str, body: str) -> None:
    """Send a plain-text email via SMTP."""
    if not settings.SMTP_HOST:
        log.debug("email.skip", reason="SMTP not configured", to=to, subject=subject)
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = to
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_TLS:
                server.starttls()
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, [to], msg.as_string())

        log.info("email.sent", to=to, subject=subject)
    except Exception as exc:
        log.error("email.failed", to=to, subject=subject, error=str(exc))


async def send_sms(to: str, message: str) -> None:
    """Send SMS via Twilio (if configured)."""
    if not settings.TWILIO_ACCOUNT_SID:
        log.debug("sms.skip", reason="Twilio not configured", to=to)
        return
    try:
        from twilio.rest import Client  # type: ignore
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(body=message, from_=settings.TWILIO_FROM_NUMBER, to=to)
        log.info("sms.sent", to=to)
    except Exception as exc:
        log.error("sms.failed", to=to, error=str(exc))
