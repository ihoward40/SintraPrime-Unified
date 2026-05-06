",""Timestamp middleware for portal."""
from datetime import datetime, timezone
from typing import Callable
from fastapi import Request
from starlette import get_logger

logger = get_logger(__name__)


class TimestampMiddleware:
    """Add timestamp headers to all responses."""

    def __init__(self, app: Callable):
        self.app = app

    async def __call__(self, request: Request, call_next: Callable) -> any:
       """Add timestamp to request state and response."""
        now = datetime.now(timezone.utc)
        request.state.timestamp = now.isoformat()
        response = await call_next(request)
        response.headers["X-Timestamp"] = now.isoformat()
        return response