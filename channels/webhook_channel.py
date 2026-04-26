"""
Generic Webhook channel for SintraPrime-Unified.

Supports:
- Inbound webhook endpoints (n8n, Zapier, Make.com, custom)
- Outbound webhook delivery with retry logic
- HMAC-SHA256 signature verification
- Rate limiting per source IP / endpoint

Inspired by ChatGPT Connected Apps webhook support and OpenClaw integration bus.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

from .message_types import ChannelConfig, ChannelType, IncomingMessage

logger = logging.getLogger(__name__)


class RetryPolicy:
    """Exponential back-off retry configuration."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ) -> None:
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay

    def delay_for(self, attempt: int) -> float:
        return min(self.base_delay * (2 ** attempt), self.max_delay)


class WebhookChannel:
    """
    Generic inbound / outbound webhook adapter.

    Inbound: register named endpoints and attach handlers.
    Outbound: send HTTP POST (or GET/PUT) requests to remote URLs with
              optional HMAC signing and automatic retry.
    """

    def __init__(self, config: ChannelConfig) -> None:
        self.config = config
        self.connected: bool = True
        self._endpoints: Dict[str, Callable] = {}
        self._secrets: Dict[str, str] = {}
        self._rate_counts: Dict[str, List[float]] = defaultdict(list)
        self._retry_policy = RetryPolicy()
        self._handler: Optional[Callable] = None

    # ------------------------------------------------------------------
    # Endpoint registration
    # ------------------------------------------------------------------

    def register_endpoint(
        self,
        path: str,
        handler_fn: Callable,
        secret: Optional[str] = None,
    ) -> None:
        """
        Register an inbound webhook path and its handler.

        :param path: URL path fragment, e.g. ``/hooks/n8n``.
        :param handler_fn: Async callable that receives the raw payload dict.
        :param secret: Optional HMAC secret for signature verification.
        """
        self._endpoints[path] = handler_fn
        if secret:
            self._secrets[path] = secret
        logger.info("WebhookChannel: registered endpoint %s", path)

    def get_registered_endpoints(self) -> List[str]:
        """List all registered endpoint paths."""
        return list(self._endpoints.keys())

    async def handle_incoming(self, path: str, payload: Dict, signature: Optional[str] = None) -> bool:
        """
        Route an inbound webhook payload to the appropriate handler.

        :returns: True if successfully handled.
        """
        handler = self._endpoints.get(path)
        if not handler:
            logger.warning("WebhookChannel: no handler for path %s", path)
            return False

        secret = self._secrets.get(path)
        if secret and signature:
            if not self.verify_signature(json.dumps(payload, separators=(",", ":")), signature, secret):
                logger.warning("WebhookChannel: signature verification failed for %s", path)
                return False

        try:
            await handler(payload)
            return True
        except Exception as exc:
            logger.error("WebhookChannel handler error on %s: %s", path, exc)
            return False

    # ------------------------------------------------------------------
    # Outbound sending
    # ------------------------------------------------------------------

    async def send(
        self,
        url: str,
        payload: Dict,
        headers: Optional[Dict[str, str]] = None,
        method: str = "POST",
        sign_secret: Optional[str] = None,
    ) -> Dict:
        """
        Send an HTTP request to an external webhook URL with retry logic.

        :param url: Target URL.
        :param payload: JSON-serialisable dict to send.
        :param headers: Extra HTTP headers.
        :param method: HTTP method (POST, GET, PUT, PATCH).
        :param sign_secret: If provided, add an HMAC-SHA256 signature header.
        :returns: Response dict with status code and body.
        """
        import aiohttp  # type: ignore[import]

        request_headers: Dict[str, str] = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)

        body_str = json.dumps(payload, separators=(",", ":"))

        if sign_secret:
            sig = self._compute_signature(body_str, sign_secret)
            request_headers["X-SintraPrime-Signature"] = sig

        last_exc: Optional[Exception] = None
        for attempt in range(self._retry_policy.max_attempts):
            try:
                async with aiohttp.ClientSession(headers=request_headers) as session:
                    method_fn = getattr(session, method.lower())
                    async with method_fn(url, data=body_str) as resp:
                        body = await resp.text()
                        result = {"status": resp.status, "body": body}
                        if resp.status < 400:
                            return result
                        logger.warning("Webhook %s returned %d (attempt %d)", url, resp.status, attempt + 1)
            except Exception as exc:
                last_exc = exc
                logger.error("Webhook send error (attempt %d): %s", attempt + 1, exc)

            if attempt < self._retry_policy.max_attempts - 1:
                await asyncio.sleep(self._retry_policy.delay_for(attempt))

        return {"status": 0, "error": str(last_exc)}

    # ------------------------------------------------------------------
    # Signature helpers
    # ------------------------------------------------------------------

    def verify_signature(self, body: str, signature: str, secret: str) -> bool:
        """
        Verify HMAC-SHA256 signature.

        Supports ``sha256=<hex>`` format (GitHub-style) as well as raw hex.
        """
        if signature.startswith("sha256="):
            signature = signature[7:]
        expected = self._compute_signature(body, secret)
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def _compute_signature(body: str, secret: str) -> str:
        return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def check_rate_limit(self, source_key: str, max_per_minute: int = 60) -> bool:
        """Return True if the source is within rate limits."""
        now = time.monotonic()
        window_start = now - 60
        ts = self._rate_counts[source_key]
        ts[:] = [t for t in ts if t > window_start]
        if len(ts) >= max_per_minute:
            return False
        ts.append(now)
        return True

    # ------------------------------------------------------------------
    # Listening
    # ------------------------------------------------------------------

    async def listen(self, handler_fn: Callable) -> None:
        """
        For webhook mode, listening is driven by the web server (channel_api.py).
        This coroutine stores the fallback handler and stays alive.
        """
        self._handler = handler_fn
        self.connected = True
        logger.info("WebhookChannel: ready for inbound webhooks.")
        while True:
            await asyncio.sleep(60)
