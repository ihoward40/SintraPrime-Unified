"""
FastAPI router for SintraPrime Multi-Channel Messaging Hub.

Endpoints:
  POST /channels/send        — send to one or more channels
  POST /channels/broadcast   — send to all registered channels
  GET  /channels/status      — channel connection status
  POST /channels/webhook/{channel} — receive inbound webhooks
  GET  /channels/history/{channel} — message history

This module is mounted inside the main SintraPrime FastAPI application.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from .channel_hub import ChannelHub
from .message_types import ChannelType, IncomingMessage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/channels", tags=["channels"])

# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------


class SendRequest(BaseModel):
    text: str = Field(..., description="Message text body")
    channels: Optional[List[str]] = Field(None, description="Target channel type names")
    recipient: Optional[str] = Field(None, description="Recipient id / phone / channel")
    buttons: Optional[List[List[Dict[str, Any]]]] = None
    attachments: Optional[List[Dict[str, Any]]] = None


class BroadcastRequest(BaseModel):
    text: str = Field(..., description="Message text to broadcast")
    channels: Optional[List[str]] = Field(None, description="Limit to these channels")


class SendResponse(BaseModel):
    success: bool
    results: Dict[str, bool]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ChannelStatusResponse(BaseModel):
    running: bool
    channels: Dict[str, Any]
    timestamp: str


class MessageHistoryResponse(BaseModel):
    channel: str
    messages: List[Dict[str, Any]]
    count: int


# ---------------------------------------------------------------------------
# Dependency — hub singleton injected via app.state
# ---------------------------------------------------------------------------


async def get_hub(request: Request) -> ChannelHub:
    hub: Optional[ChannelHub] = getattr(request.app.state, "channel_hub", None)
    if hub is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ChannelHub not initialised",
        )
    return hub


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/send", response_model=SendResponse, summary="Send a message to one or more channels")
async def send_message(
    body: SendRequest,
    hub: ChannelHub = Depends(get_hub),
) -> SendResponse:
    """
    Send *text* to one or more channels.

    Provide *channels* (list of channel type names) or omit to send to all
    registered channels. *recipient* specifies the destination (chat_id,
    phone number, etc.).
    """
    channel_types: Optional[List[ChannelType]] = None
    if body.channels:
        try:
            channel_types = [ChannelType(c.lower()) for c in body.channels]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid channel type: {exc}")

    raw_results = await hub.send(
        text=body.text,
        channels=channel_types,
        recipient=body.recipient,
    )
    results = {ct.value: ok for ct, ok in raw_results.items()}
    return SendResponse(success=all(results.values()), results=results)


@router.post("/broadcast", response_model=SendResponse, summary="Broadcast to all channels")
async def broadcast(
    body: BroadcastRequest,
    hub: ChannelHub = Depends(get_hub),
) -> SendResponse:
    """Send *text* to every registered (or specified) channel."""
    channel_types: Optional[List[ChannelType]] = None
    if body.channels:
        try:
            channel_types = [ChannelType(c.lower()) for c in body.channels]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid channel type: {exc}")

    raw_results = await hub.broadcast(body.text, channels=channel_types)
    results = {ct.value: ok for ct, ok in raw_results.items()}
    return SendResponse(success=all(results.values()), results=results)


@router.get("/status", response_model=ChannelStatusResponse, summary="Channel connection status")
async def channel_status(hub: ChannelHub = Depends(get_hub)) -> ChannelStatusResponse:
    """Return live connection status for all registered channels."""
    data = hub.status()
    return ChannelStatusResponse(**data)


@router.post(
    "/webhook/{channel}",
    summary="Receive inbound webhooks",
    status_code=status.HTTP_202_ACCEPTED,
)
async def receive_webhook(
    channel: str,
    request: Request,
    background_tasks: BackgroundTasks,
    hub: ChannelHub = Depends(get_hub),
    x_sintra_signature: Optional[str] = Header(None),
) -> Dict[str, str]:
    """
    Unified webhook endpoint for inbound messages.

    Each channel type has its own path: ``/channels/webhook/telegram``,
    ``/channels/webhook/whatsapp``, ``/channels/webhook/slack``, etc.
    """
    try:
        channel_type = ChannelType(channel.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown channel: {channel}")

    payload = await request.json()
    ch = hub._channels.get(channel_type)

    if ch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel {channel} not registered",
        )

    # Dispatch to channel-specific parser in the background
    async def _dispatch():
        try:
            incoming: Optional[IncomingMessage] = None

            if channel_type == ChannelType.TELEGRAM and hasattr(ch, "_parse_update"):
                incoming = ch._parse_update({"message": payload})
            elif channel_type == ChannelType.WHATSAPP:
                if hasattr(ch, "parse_meta_webhook"):
                    incoming = ch.parse_meta_webhook(payload)
                elif hasattr(ch, "parse_twilio_webhook"):
                    incoming = ch.parse_twilio_webhook(payload)
            elif channel_type == ChannelType.SLACK and hasattr(ch, "_parse_event"):
                incoming = ch._parse_event(payload)
            elif channel_type == ChannelType.WEBHOOK and hasattr(ch, "handle_incoming"):
                path = request.url.path
                await ch.handle_incoming(path, payload, x_sintra_signature)
                return

            if incoming:
                await hub._enqueue(incoming)
        except Exception as exc:
            logger.error("Webhook dispatch error for %s: %s", channel, exc)

    background_tasks.add_task(_dispatch)
    return {"status": "accepted"}


@router.get(
    "/history/{channel}",
    response_model=MessageHistoryResponse,
    summary="Retrieve message history",
)
async def message_history(
    channel: str,
    limit: int = 50,
    hub: ChannelHub = Depends(get_hub),
) -> MessageHistoryResponse:
    """
    Return recent message history for a channel.

    Note: history is stored in-memory unless a persistence layer is attached.
    """
    try:
        channel_type = ChannelType(channel.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown channel: {channel}")

    # In production, replace with actual DB query
    history: List[Dict[str, Any]] = []
    return MessageHistoryResponse(channel=channel, messages=history, count=len(history))
