\"\"\"
FastAPI dependencies for SSO router — session, rate limiting, CSRF.
\"\"\"

from fastapi import Depends, HTTPException, Request
from ..session import SessionManager

async def get_session_manager(request: Request) -> SessionManager:
    \"\"\"Inject SessionManager from app.state.\"\"\"
    if not hasattr(request.app.state, \"session_manager\"):
        raise HTTPException(status_code=500, detail=\"SessionManager not initialized\")
    return request.app.state.session_manager
