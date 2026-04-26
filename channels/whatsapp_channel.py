"""
WhatsApp Business API integration for SintraPrime-Unified.

Supports:
- Twilio WhatsApp API (sandbox + production)
- Meta WhatsApp Business Cloud API
- Message templates for legal notifications
- Automated follow-up sequences

Inspired by Manus AI WhatsApp channel and Hermes Agent enterprise WhatsApp.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from .message_types import Attachment, AttachmentType, ChannelConfig, ChannelType, IncomingMessage

logger = logging.getLogger(__name__)


class WhatsAppChannel:
    """
    WhatsApp channel adapter.

    Supports two backends:
    - ``twilio`` (default) — uses Twilio WhatsApp Sandbox / Business API
    - ``meta`` — uses Meta WhatsApp Business Cloud API directly
    """

    LEGAL_TEMPLATES: Dict[str, str] = {
        "case_update": "Your case {{1}} has been updated. New status: {{2}}. Reply STOP to unsubscribe.",
        "hearing_reminder": "Reminder: Your hearing for case {{1}} is scheduled for {{2}} at {{3}}.",
        "document_ready": "Your document {{1}} is ready. Reply VIEW to access it securely.",
        "payment_due": "Invoice {{1}} for ${{2}} is due on {{3}}. Reply PAY to settle.",
    }

    def __init__(self, config: ChannelConfig, backend: str = "twilio") -> None:
        self.config = config
        self.backend = backend
        self.token: str = config.token or ""
        self.account_sid: str = config.extra.get("account_sid", "")
        self.from_number: str = config.extra.get("from_number", "")
        self.connected: bool = bool(self.token)
        self._handler: Optional[Callable] = None

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    async def send_message(self, to: str, text: str) -> Dict:
        """Send a free-form text message to a WhatsApp number."""
        if self.backend == "twilio":
            return await self._twilio_send(to, text)
        return await self._meta_send(to, {"type": "text", "text": {"body": text}})

    async def send_template(
        self, to: str, template_name: str, params: List[str]
    ) -> Dict:
        """
        Send a pre-approved WhatsApp template message.

        :param to: Recipient phone number (E.164 format).
        :param template_name: Key from LEGAL_TEMPLATES or custom template name.
        :param params: Ordered parameter values to substitute into {{1}}, {{2}}…
        """
        if self.backend == "meta":
            components = [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": p} for p in params],
                }
            ]
            return await self._meta_send(
                to,
                {
                    "type": "template",
                    "template": {
                        "name": template_name,
                        "language": {"code": "en_US"},
                        "components": components,
                    },
                },
            )
        # Twilio: render template locally and send as free-form text
        template = self.LEGAL_TEMPLATES.get(template_name, "")
        for i, p in enumerate(params, start=1):
            template = template.replace(f"{{{{{i}}}}}", p)
        return await self._twilio_send(to, template)

    async def send_document(self, to: str, file_path: str, caption: str = "") -> Dict:
        """Send a document file to a WhatsApp contact."""
        if self.backend == "twilio":
            return await self._twilio_send(to, caption, media_url=f"file://{file_path}")
        # Meta: upload media first, then send
        media_id = await self._meta_upload_media(file_path)
        return await self._meta_send(
            to,
            {
                "type": "document",
                "document": {"id": media_id, "caption": caption},
            },
        )

    # ------------------------------------------------------------------
    # Automated sequences
    # ------------------------------------------------------------------

    async def send_follow_up_sequence(
        self,
        to: str,
        messages: List[str],
        delay_seconds: float = 3600.0,
    ) -> None:
        """
        Send a series of follow-up messages with delays between each.

        :param to: Recipient number.
        :param messages: List of message texts in order.
        :param delay_seconds: Pause between each message.
        """
        for msg in messages:
            await self.send_message(to, msg)
            await asyncio.sleep(delay_seconds)

    # ------------------------------------------------------------------
    # Listening (webhook)
    # ------------------------------------------------------------------

    async def listen(self, handler_fn: Callable) -> None:
        """
        For WhatsApp, listening is event-driven via webhook.
        This coroutine simply marks the channel ready and waits; actual
        webhook delivery is handled by WebhookChannel / channel_api.py.
        """
        self._handler = handler_fn
        self.connected = True
        logger.info("WhatsAppChannel: webhook listener registered (awaiting inbound webhooks).")
        while True:
            await asyncio.sleep(60)

    def parse_twilio_webhook(self, form_data: Dict) -> Optional[IncomingMessage]:
        """Parse an inbound Twilio WhatsApp webhook POST body."""
        body = form_data.get("Body", "")
        from_number = form_data.get("From", "").replace("whatsapp:", "")
        num_media = int(form_data.get("NumMedia", 0))

        attachments = []
        for i in range(num_media):
            url = form_data.get(f"MediaUrl{i}", "")
            content_type = form_data.get(f"MediaContentType{i}", "")
            att_type = AttachmentType.DOCUMENT
            if "image" in content_type:
                att_type = AttachmentType.IMAGE
            elif "audio" in content_type:
                att_type = AttachmentType.AUDIO
            attachments.append(Attachment(type=att_type, url=url, mime_type=content_type))

        return IncomingMessage(
            id=form_data.get("SmsMessageSid", ""),
            channel=ChannelType.WHATSAPP,
            user_id=from_number,
            text=body,
            chat_id=from_number,
            attachments=attachments,
            metadata={"raw": form_data},
        )

    def parse_meta_webhook(self, payload: Dict) -> Optional[IncomingMessage]:
        """Parse an inbound Meta Cloud API webhook payload."""
        try:
            entry = payload["entry"][0]
            change = entry["changes"][0]["value"]
            message = change["messages"][0]
            contact = change["contacts"][0]
            from_number = message["from"]
            msg_id = message["id"]
            text = message.get("text", {}).get("body", "")
            attachments = []
            for att_type in ("image", "document", "audio", "video"):
                if att_type in message:
                    media = message[att_type]
                    attachments.append(
                        Attachment(
                            type=AttachmentType(att_type if att_type != "video" else "video"),
                            url=f"meta://media/{media.get('id')}",
                            mime_type=media.get("mime_type"),
                        )
                    )
            return IncomingMessage(
                id=msg_id,
                channel=ChannelType.WHATSAPP,
                user_id=from_number,
                username=contact.get("profile", {}).get("name"),
                text=text,
                chat_id=from_number,
                attachments=attachments,
                metadata={"raw": payload},
            )
        except (KeyError, IndexError) as exc:
            logger.error("Failed to parse Meta webhook: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Backends
    # ------------------------------------------------------------------

    async def _twilio_send(self, to: str, body: str, media_url: Optional[str] = None) -> Dict:
        import aiohttp  # type: ignore[import]
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        payload: Dict[str, Any] = {
            "From": f"whatsapp:{self.from_number}",
            "To": f"whatsapp:{to}",
            "Body": body,
        }
        if media_url:
            payload["MediaUrl"] = media_url
        auth = aiohttp.BasicAuth(self.account_sid, self.token)
        async with aiohttp.ClientSession(auth=auth) as session:
            async with session.post(url, data=payload) as resp:
                return await resp.json()

    async def _meta_send(self, to: str, message: Dict) -> Dict:
        import aiohttp  # type: ignore[import]
        phone_number_id = self.config.extra.get("phone_number_id", "")
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload = {"messaging_product": "whatsapp", "to": to, **message}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(url, json=payload) as resp:
                return await resp.json()

    async def _meta_upload_media(self, file_path: str) -> str:
        """Upload media to Meta and return the media_id."""
        import aiohttp  # type: ignore[import]
        phone_number_id = self.config.extra.get("phone_number_id", "")
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}/media"
        headers = {"Authorization": f"Bearer {self.token}"}
        async with aiohttp.ClientSession(headers=headers) as session:
            with open(file_path, "rb") as fh:
                form = aiohttp.FormData()
                form.add_field("messaging_product", "whatsapp")
                form.add_field("file", fh, filename=file_path.split("/")[-1])
                async with session.post(url, data=form, headers=headers) as resp:
                    data = await resp.json()
                    return data.get("id", "")
