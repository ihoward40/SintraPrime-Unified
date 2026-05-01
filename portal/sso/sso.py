"""
FastAPI SSO Router for PHASE 21B - Session Management & AuthN Integration.

Routes:
  POST /auth/authorize — Initiate SSO (redirect to IdP)
  GET /auth/callback — Handle IdP callback (OAuth 2.0 code exchange)
  GET /auth/refresh — Refresh access token
  POST /auth/logout — Destroy session
  GET /auth/me — Current user profile
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, EmailStr

from portal.sso.middleware import (
    SessionMiddlewareManager,
    TokenRefreshManager,
    IdPErrorHandler,
)
from portal.sso.providers import okta, azure, google

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["SSO"])


class AuthorizeRequest(BaseModel):
    """SSO authorize request."""
    provider: str  # okta, azure, google
    redirect_uri: str


class UserProfile(BaseModel):
    """Current user profile from session."""
    user_id: str
    email: EmailStr
    name: str
    provider: str
    session_id: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


@router.post("/authorize")
async def authorize(
    request: Request,
    req: AuthorizeRequest,
) -> dict:
    """Initiate SSO with specified provider."""
    provider = req.provider.lower()
    
    if provider == "okta":
        auth_url = okta.get_authorization_url(redirect_uri=req.redirect_uri)
    elif provider == "azure":
        auth_url = azure.get_authorization_url(redirect_uri=req.redirect_uri)
    elif provider == "google":
        auth_url = google.get_authorization_url(redirect_uri=req.redirect_uri)
    else:
        raise HTTPException(status_code=400, detail="Unsupported provider")
    
    logger.info(f"SSO authorize initiated for provider {provider}")
    return {"authorization_url": auth_url, "provider": provider}


@router.get("/callback")
async def callback(
    request: Request,
    code: str,
    state: str,
    session_manager: SessionMiddlewareManager = Depends(),
) -> Response:
    """Handle OAuth 2.0 callback from IdP."""
    try:
        # Detect provider from state or request context
        provider = request.query_params.get("provider", "okta").lower()
        
        # Exchange code for tokens
        if provider == "okta":
            user_info = await okta.exchange_code(code)
        elif provider == "azure":
            user_info = await azure.exchange_code(code)
        elif provider == "google":
            user_info = await google.exchange_code(code)
        else:
            raise HTTPException(status_code=400, detail="Unsupported provider")
        
        # Create session
        session_id = await session_manager.create_session(
            user_id=user_info["sub"],
            email=user_info["email"],
            provider=provider,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        
        # Set secure session cookie
        response = Response(status_code=302)
        response.headers["location"] = "/app/dashboard"  # Redirect to app
        response.set_cookie(
            "session_id",
            session_id,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=3600,  # 1 hour
        )
        
        logger.info(f"SSO callback completed for {user_info.get('email')} via {provider}")
        return response
    
    except Exception as e:
        logger.error(f"SSO callback failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


@router.get("/refresh")
async def refresh(
    request: Request,
    token_manager: TokenRefreshManager = Depends(),
) -> TokenResponse:
    """Refresh access token using refresh token."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    
    # Get current access token from Authorization header
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    
    access_token = auth_header[7:]
    
    # Refresh
    new_token = await token_manager.refresh_token(access_token, refresh_token)
    if not new_token:
        raise HTTPException(status_code=401, detail="Token refresh failed")
    
    return TokenResponse(access_token=new_token, expires_in=3600)


@router.post("/logout")
async def logout(
    request: Request,
    session_manager: SessionMiddlewareManager = Depends(),
) -> dict:
    """Destroy session and logout."""
    session_id = request.cookies.get("session_id")
    if session_id:
        await session_manager.destroy_session(session_id)
    
    # Clear cookies
    response = Response(content="{\"message\": \"Logged out\"}")
    response.delete_cookie("session_id")
    response.delete_cookie("refresh_token")
    
    logger.info(f"User logged out, session {session_id}")
    return {"message": "Logged out"}


@router.get("/me", response_model=UserProfile)
async def get_current_user(request: Request) -> UserProfile:
    """Get current user profile from session."""
    session = getattr(request.state, "session", None)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return UserProfile(
        user_id=session["user_id"],
        email=session["email"],
        name=session.get("name", session["email"]),
        provider=session["provider"],
        session_id=session["session_id"],
    )
