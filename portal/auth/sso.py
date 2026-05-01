"""SSO Router with timezone-aware session management (DTZ011 compliant)."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, Response, HTTPException, Depends
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/auth", tags=["auth"])


class SessionConfig(BaseModel):
    """Session management configuration."""
    jwt_secret_key: str
    session_timeout_minutes: int = 60
    cookie_path: str = "/api/v1/sso"
    cookie_secure: bool = True
    cookie_httponly: bool = True
    cookie_samesite: str = "lax"


class LoginRequest(BaseModel):
    username: str
    password: str


class SessionData(BaseModel):
    user_id: str
    username: str
    email: Optional[EmailStr] = None
    created_at: datetime
    expires_at: datetime


class SessionManager:
    """Manages user sessions with timezone-aware timestamps (UTC, DTZ011)."""

    def __init__(self, config: SessionConfig):
        self.config = config
        self.sessions = {}

    def create_session(self, user_id: str, username: str, 
                       email: Optional[str] = None) -> SessionData:
        """Create a timezone-aware session (UTC only)."""
        now_utc = datetime.now(timezone.utc)
        expires_at = datetime.fromtimestamp(
            now_utc.timestamp() + self.config.session_timeout_minutes * 60,
            tz=timezone.utc
        )

        session = SessionData(
            user_id=user_id,
            username=username,
            email=email,
            created_at=now_utc,
            expires_at=expires_at,
        )
        self.sessions[user_id] = session
        return session

    def validate_session(self, user_id: str) -> bool:
        """Check if session is valid and not expired."""
        if user_id not in self.sessions:
            return False
        
        session = self.sessions[user_id]
        now_utc = datetime.now(timezone.utc)
        return session.expires_at > now_utc

    def invalidate_session(self, user_id: str) -> None:
        """Invalidate a session."""
        self.sessions.pop(user_id, None)


_session_manager = None


def get_session_manager() -> SessionManager:
    """Dependency injection for SessionManager."""
    if _session_manager is None:
        raise RuntimeError("Session manager not initialized")
    return _session_manager


def init_session_manager(config: SessionConfig) -> None:
    """Initialize the global session manager (called once at app startup)."""
    global _session_manager
    _session_manager = SessionManager(config)


@router.post("/login")
async def login(request: LoginRequest, session_manager: SessionManager = Depends(get_session_manager)):
    """Login endpoint."""
    if not request.username or not request.password:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    session = session_manager.create_session(
        user_id=request.username,
        username=request.username,
    )
    return {
        "user_id": session.user_id,
        "message": "Login successful",
        "session_expires_at": session.expires_at.isoformat(),
    }


@router.post("/logout")
async def logout(request: Request, session_manager: SessionManager = Depends(get_session_manager)):
    """Logout endpoint."""
    user_id = request.session.get("user_id")
    if user_id:
        session_manager.invalidate_session(user_id)
    return {"message": "Logout successful"}


@router.get("/me")
async def get_current_user(request: Request, session_manager: SessionManager = Depends(get_session_manager)):
    """Get current user info."""
    user_id = request.session.get("user_id")
    if not user_id or not session_manager.validate_session(user_id):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    session = session_manager.sessions[user_id]
    return {
        "user_id": session.user_id,
        "username": session.username,
        "email": session.email,
        "created_at": session.created_at.isoformat(),
        "expires_at": session.expires_at.isoformat(),
    }
