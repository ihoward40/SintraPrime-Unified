"""Session middleware for portal."""
import logging
from typing import Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SessionMiddleware(BaseHTTPMiddleware):
    """Validate session on incoming requests."""

    def __init__(self, app: Callable):
        super().__init__(app)
        self.app = app

    async def dispatch(self, request: Request, call_next: Callable) -> any:
        """Validate session and attach to request state."""
        # Extract session ID from cookies or headers
        session_id = request.cookies.get("session_id") or request.headers.get("X-Session-ID")
        if session_id:
            request.state.session_id = session_id
        response = await call_next(request)
        return response
