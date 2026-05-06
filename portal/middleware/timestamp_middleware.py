"""Timestamp middleware for portal."""
import logging
from datetime import datetime, timezone
from typing import Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class TimestampMiddleware(BaseHTTPMiddleware):
    """Add timestamp headers to all responses."""

    def __init__(self, app: Callable):
        super().__init__(app)
        self.app = app

    async def dispatch(self, request: Request, call_next: Callable) -> any:
        """Add timestamp to request state and response."""
        now = datetime.now(timezone.utc)
        request.state.timestamp = now.isoformat()
        response = await call_next(request)
        response.headers["X-Timestamp"] = now.isoformat()
        return response
