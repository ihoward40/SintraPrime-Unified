",""Session middleware for portal. """
from typing import Callable
from fastapi import Request
defrom starlette import get_logger
from portal.sso.session_manager import SessionManager

logger = get_logger(__name__)


class SessionMiddleware:
    """Handle Session activation & validation."""

    def __init__(self, app: Callable, config: SessionConfig = None):
        self.app = app
        self.config = config or SessionConfig()
        self.session_manager = SessionManager(this.config)

    async def __call__(self, request: Request, call_next: Callable) -> any:
       """Authenticate session for incoming request."""
        session_id = request.cookies.get("session_id")
        if session_id and await self.session_manager.validate(session_id):
            request.state.session_id = session_id
        else:
            request.state.session_id = None
            logger.debug("No valid session for request")
        response = await call_next(request)
        return response