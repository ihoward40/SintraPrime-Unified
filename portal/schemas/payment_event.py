"""Pydantic schemas for payment webhook events."""

from __future__ import annotations

from pydantic import BaseModel


class WebhookAcknowledgment(BaseModel):
    """Deterministic acknowledgment returned for a processed webhook event."""

    status: str
    event_id: str
    receipt_id: str | None = None


class WebhookRejection(BaseModel):
    """Rejection response for invalid webhook events."""

    error: str
    detail: str | None = None


class WebhookReplay(BaseModel):
    """Replay response for a previously completed event."""

    status: str
    event_id: str
    result_reference: str | None = None
