"""
SSO Router — Phase 21B
Wires Okta, Azure AD, and Google Workspace OIDC providers into FastAPI.

Routes per provider (prefix: /api/v1/sso/{provider}):
  GET  /authorize          → redirect to IdP authorization URL
  GET  /callback           → exchange code, create session, set secure cookie
  POST /refresh            → rotate refresh token, return new access token
  POST /logout             → revoke session, clear cookie
  GET  /me                 → return current SSO session info

Security:
  - CSRF state validated on callback (constant-time comparison)
  - Refresh token in HttpOnly, Secure, SameSite=Lax cookie
  - State stored in signed server-side session (Starlette SessionMiddleware)
  - All errors logged; no IdP internals leaked to client
"""
from __future__ import annotations

import hmac
import logging
import secrets
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ..config import get_settings
from ..sso import (
    OktaConfig,
    OktaProvider,
    SessionConfig,
    SessionManager,
    InMemorySessionStore,
)
from ..sso.providers.azure import AzureADProvider, AzureConfig
from ..sso.providers.google import GoogleWorkspaceProvider, GoogleConfig

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()

# ── Cookie / session constants ────────────────────────────────────────────────
SSO_REFRESH_COOKIE = "sso_refresh_token"
SSO_STATE_SESSION_KEY = "sso_oauth_state"
COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days in seconds

ProviderName = Literal["okta", "azure", "google"]


# ── Response schemas ──────────────────────────────────────────────────────────
class SSOTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    provider: str
    email: str
    name: Optional[str] = None


class SSOSessionResponse(BaseModel):
    user_id: str
    email: str
    provider: str
    session_id: str
    expires_at: str


class SSORefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ── Provider / SessionManager factories ──────────────────────────────────────
def _get_session_manager() -> SessionManager:
    """Build a SessionManager from app settings."""
    cfg = SessionConfig(
        secret_key=settings.SSO_SESSION_SECRET,
        issuer=settings.SSO_ISSUER,
        audience=settings.SSO_AUDIENCE,
        session_ttl_seconds=settings.SSO_SESSION_TTL_SECONDS,
        refresh_token_ttl_seconds=settings.SSO_REFRESH_TTL_SECONDS,
    )
    return SessionManager(cfg, store=InMemorySessionStore())


def _get_okta_provider() -> OktaProvider:
    cfg = OktaConfig.from_env()
    return OktaProvider(cfg)


def _get_azure_provider() -> AzureADProvider:
    cfg = AzureConfig(
        tenant_id=settings.AZURE_TENANT_ID,
        client_id=settings.AZURE_CLIENT_ID,
        client_secret=settings.AZURE_CLIENT_SECRET,
        redirect_uri=settings.AZURE_REDIRECT_URI,
    )
    return AzureADProvider(cfg)


def _get_google_provider() -> GoogleWorkspaceProvider:
    cfg = GoogleConfig(
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        hosted_domain=settings.GOOGLE_HOSTED_DOMAIN or None,
    )
    return GoogleWorkspaceProvider(cfg)


# ── CSRF helpers ──────────────────────────────────────────────────────────────
def _generate_state() -> str:
    return secrets.token_urlsafe(32)


def _verify_state(received: str, expected: str) -> bool:
    """Constant-time state comparison to prevent timing attacks."""
    return hmac.compare_digest(received.encode(), expected.encode())


def _store_state(request: Request, state: str) -> None:
    request.session[SSO_STATE_SESSION_KEY] = state


def _pop_state(request: Request) -> Optional[str]:
    return request.session.pop(SSO_STATE_SESSION_KEY, None)


# ── Shared dependency: validate SSO refresh cookie ───────────────────────────
def _get_sso_refresh_token(
    sso_refresh_token: Annotated[Optional[str], Cookie()] = None,
) -> str:
    if not sso_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No SSO refresh token",
        )
    return sso_refresh_token


def _decode_refresh_token_session_id(refresh_token: str, sm: SessionManager) -> str:
    """Decode a refresh token and return its session_id."""
    try:
        payload = sm.jwt_service.validate_token(refresh_token, token_type="refresh")  # nosec B106
        session_id = payload.get("session_id")
        if not session_id:
            raise ValueError("No session_id in refresh token")
        return session_id
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc


def _get_sso_access_token(request: Request) -> str:
    """Extract Bearer access token from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth[7:]


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SSO_REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        path="/api/v1/sso",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SSO_REFRESH_COOKIE,
        path="/api/v1/sso",
        httponly=True,
        secure=True,
        samesite="lax",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# OKTA ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/okta/authorize", summary="Redirect to Okta authorization endpoint")
async def okta_authorize(request: Request) -> RedirectResponse:
    """Generate a CSRF state token, store it in the session, and redirect to Okta."""
    try:
        provider = _get_okta_provider()
        state = _generate_state()
        _store_state(request, state)
        auth_url, _ = provider.get_authorization_url(state=state)
        logger.info("sso.okta.authorize", extra={"ip": request.client.host if request.client else "unknown"})
        return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)
    except (ValueError, KeyError) as exc:
        logger.error("sso.okta.authorize.error", extra={"error": str(exc)})
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Okta SSO not configured")


@router.get("/okta/callback", response_model=SSOTokenResponse, summary="Handle Okta OAuth callback")
async def okta_callback(
    code: str,
    state: str,
    request: Request,
    response: Response,
) -> SSOTokenResponse:
    """Validate CSRF state, exchange code for tokens, create session, set cookie."""
    stored_state = _pop_state(request)
    if not stored_state or not _verify_state(state, stored_state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state parameter")

    try:
        async with OktaProvider(_get_okta_provider().config) as provider:
            token_resp = await provider.exchange_code_for_token(code)
            user_info = await provider.get_user_info(token_resp.access_token)
    except ValueError as exc:
        logger.error("sso.okta.callback.error", extra={"error": str(exc)})
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Okta token exchange failed")

    sm = _get_session_manager()
    token_pair = await sm.create_session(
        user_id=user_info.sub,
        email=user_info.email,
        identity_provider="okta",
        auth_method="oidc",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    _set_refresh_cookie(response, token_pair.refresh_token)
    logger.info("sso.okta.callback.success", extra={"sub": user_info.sub})
    return SSOTokenResponse(
        access_token=token_pair.access_token,
        expires_in=settings.SSO_SESSION_TTL_SECONDS,
        provider="okta",
        email=user_info.email,
        name=getattr(user_info, "preferred_username", None),
    )


@router.post("/okta/refresh", response_model=SSORefreshResponse, summary="Refresh Okta SSO session")
async def okta_refresh(
    response: Response,
    refresh_token: str = Depends(_get_sso_refresh_token),
) -> SSORefreshResponse:
    """Rotate the SSO refresh token and return a new access token."""
    sm = _get_session_manager()
    token_pair = await sm.refresh_session(refresh_token)
    if not token_pair:
        logger.warning("sso.okta.refresh.failed")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    _set_refresh_cookie(response, token_pair.refresh_token)
    return SSORefreshResponse(
        access_token=token_pair.access_token,
        expires_in=settings.SSO_SESSION_TTL_SECONDS,
    )


@router.post("/okta/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Logout from Okta SSO")
async def okta_logout(
    response: Response,
    refresh_token: str = Depends(_get_sso_refresh_token),
) -> None:
    """Revoke the SSO session and clear the refresh cookie."""
    sm = _get_session_manager()
    session_id = _decode_refresh_token_session_id(refresh_token, sm)
    try:
        await sm.revoke_session(session_id)
    except Exception as exc:  # fail-open on logout
        logger.warning("sso.okta.logout.revoke_failed", extra={"error": str(exc)})
    _clear_refresh_cookie(response)


@router.get("/okta/me", response_model=SSOSessionResponse, summary="Get current Okta SSO session")
async def okta_me(
    request: Request,
    access_token: str = Depends(_get_sso_access_token),
) -> SSOSessionResponse:
    """Return current SSO session information from the access token."""
    sm = _get_session_manager()
    session = await sm.validate_session(access_token)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    return SSOSessionResponse(
        user_id=session.user_id,
        email=session.email,
        provider="okta",
        session_id=session.session_id,
        expires_at=session.expires_at.isoformat() if hasattr(session, "expires_at") else "",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# AZURE AD ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/azure/authorize", summary="Redirect to Azure AD authorization endpoint")
async def azure_authorize(request: Request) -> RedirectResponse:
    """Generate CSRF state and redirect to Azure AD."""
    try:
        provider = _get_azure_provider()
        state = _generate_state()
        _store_state(request, state)
        auth_url = provider.get_authorization_url(state=state)
        logger.info("sso.azure.authorize", extra={"ip": request.client.host if request.client else "unknown"})
        return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)
    except (ValueError, KeyError) as exc:
        logger.error("sso.azure.authorize.error", extra={"error": str(exc)})
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Azure SSO not configured")


@router.get("/azure/callback", response_model=SSOTokenResponse, summary="Handle Azure AD OAuth callback")
async def azure_callback(
    code: str,
    state: str,
    request: Request,
    response: Response,
) -> SSOTokenResponse:
    """Validate CSRF state, exchange code for tokens, create session."""
    stored_state = _pop_state(request)
    if not stored_state or not _verify_state(state, stored_state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state parameter")

    try:
        provider = _get_azure_provider()
        tokens = provider.exchange_code_for_tokens(code)
        user_info = provider.get_user_info(tokens["access_token"])
    except Exception as exc:
        logger.error("sso.azure.callback.error", extra={"error": str(exc)})
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Azure token exchange failed")

    email = user_info.get("email") or user_info.get("preferred_username", "")
    sub = user_info.get("sub", "")

    sm = _get_session_manager()
    token_pair = await sm.create_session(
        user_id=sub,
        email=email,
        identity_provider="azure",
        auth_method="oidc",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    _set_refresh_cookie(response, token_pair.refresh_token)
    logger.info("sso.azure.callback.success", extra={"sub": sub})
    return SSOTokenResponse(
        access_token=token_pair.access_token,
        expires_in=settings.SSO_SESSION_TTL_SECONDS,
        provider="azure",
        email=email,
        name=user_info.get("name"),
    )


@router.post("/azure/refresh", response_model=SSORefreshResponse, summary="Refresh Azure SSO session")
async def azure_refresh(
    response: Response,
    refresh_token: str = Depends(_get_sso_refresh_token),
) -> SSORefreshResponse:
    sm = _get_session_manager()
    token_pair = await sm.refresh_session(refresh_token)
    if not token_pair:
        logger.warning("sso.azure.refresh.failed")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    _set_refresh_cookie(response, token_pair.refresh_token)
    return SSORefreshResponse(
        access_token=token_pair.access_token,
        expires_in=settings.SSO_SESSION_TTL_SECONDS,
    )


@router.post("/azure/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Logout from Azure SSO")
async def azure_logout(
    response: Response,
    refresh_token: str = Depends(_get_sso_refresh_token),
) -> None:
    sm = _get_session_manager()
    session_id = _decode_refresh_token_session_id(refresh_token, sm)
    try:
        await sm.revoke_session(session_id)
    except Exception as exc:
        logger.warning("sso.azure.logout.revoke_failed", extra={"error": str(exc)})
    _clear_refresh_cookie(response)


@router.get("/azure/me", response_model=SSOSessionResponse, summary="Get current Azure SSO session")
async def azure_me(
    request: Request,
    access_token: str = Depends(_get_sso_access_token),
) -> SSOSessionResponse:
    sm = _get_session_manager()
    session = await sm.validate_session(access_token)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    return SSOSessionResponse(
        user_id=session.user_id,
        email=session.email,
        provider="azure",
        session_id=session.session_id,
        expires_at=session.expires_at.isoformat() if hasattr(session, "expires_at") else "",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# GOOGLE WORKSPACE ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/google/authorize", summary="Redirect to Google authorization endpoint")
async def google_authorize(request: Request) -> RedirectResponse:
    """Generate CSRF state and redirect to Google OAuth."""
    try:
        provider = _get_google_provider()
        state = _generate_state()
        _store_state(request, state)
        auth_url = provider.get_authorization_url(state=state)
        logger.info("sso.google.authorize", extra={"ip": request.client.host if request.client else "unknown"})
        return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)
    except (ValueError, KeyError) as exc:
        logger.error("sso.google.authorize.error", extra={"error": str(exc)})
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google SSO not configured")


@router.get("/google/callback", response_model=SSOTokenResponse, summary="Handle Google OAuth callback")
async def google_callback(
    code: str,
    state: str,
    request: Request,
    response: Response,
) -> SSOTokenResponse:
    """Validate CSRF state, exchange code for tokens, create session."""
    stored_state = _pop_state(request)
    if not stored_state or not _verify_state(state, stored_state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state parameter")

    try:
        provider = _get_google_provider()
        tokens = provider.exchange_code_for_tokens(code)
        user_info = provider.get_user_info(tokens["access_token"])
    except Exception as exc:
        logger.error("sso.google.callback.error", extra={"error": str(exc)})
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Google token exchange failed")

    email = user_info.get("email", "")
    sub = user_info.get("sub", "")

    sm = _get_session_manager()
    token_pair = await sm.create_session(
        user_id=sub,
        email=email,
        identity_provider="google",
        auth_method="oidc",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    _set_refresh_cookie(response, token_pair.refresh_token)
    logger.info("sso.google.callback.success", extra={"sub": sub})
    return SSOTokenResponse(
        access_token=token_pair.access_token,
        expires_in=settings.SSO_SESSION_TTL_SECONDS,
        provider="google",
        email=email,
        name=user_info.get("name"),
    )


@router.post("/google/refresh", response_model=SSORefreshResponse, summary="Refresh Google SSO session")
async def google_refresh(
    response: Response,
    refresh_token: str = Depends(_get_sso_refresh_token),
) -> SSORefreshResponse:
    sm = _get_session_manager()
    token_pair = await sm.refresh_session(refresh_token)
    if not token_pair:
        logger.warning("sso.google.refresh.failed")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    _set_refresh_cookie(response, token_pair.refresh_token)
    return SSORefreshResponse(
        access_token=token_pair.access_token,
        expires_in=settings.SSO_SESSION_TTL_SECONDS,
    )


@router.post("/google/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Logout from Google SSO")
async def google_logout(
    response: Response,
    refresh_token: str = Depends(_get_sso_refresh_token),
) -> None:
    sm = _get_session_manager()
    session_id = _decode_refresh_token_session_id(refresh_token, sm)
    try:
        await sm.revoke_session(session_id)
    except Exception as exc:
        logger.warning("sso.google.logout.revoke_failed", extra={"error": str(exc)})
    _clear_refresh_cookie(response)


@router.get("/google/me", response_model=SSOSessionResponse, summary="Get current Google SSO session")
async def google_me(
    request: Request,
    access_token: str = Depends(_get_sso_access_token),
) -> SSOSessionResponse:
    sm = _get_session_manager()
    session = await sm.validate_session(access_token)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    return SSOSessionResponse(
        user_id=session.user_id,
        email=session.email,
        provider="google",
        session_id=session.session_id,
        expires_at=session.expires_at.isoformat() if hasattr(session, "expires_at") else "",
    )
