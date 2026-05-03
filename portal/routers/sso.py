"""
SSO Router — Phase 21B.

Minimal boot-safe endpoints for Okta, Azure AD, and Google Workspace OIDC.
The full provider callback implementation should remain behind tests; this file
must never break portal import/startup smoke checks.
"""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

router = APIRouter()


@router.get("/okta/authorize", summary="Redirect to Okta authorization")
async def okta_authorize(request: Request) -> RedirectResponse:
    """Placeholder Okta authorization route."""
    return RedirectResponse(url="/", status_code=302)


@router.get("/azure/authorize", summary="Redirect to Azure AD authorization")
async def azure_authorize(request: Request) -> RedirectResponse:
    """Placeholder Azure AD authorization route."""
    return RedirectResponse(url="/", status_code=302)


@router.get("/google/authorize", summary="Redirect to Google Workspace authorization")
async def google_authorize(request: Request) -> RedirectResponse:
    """Placeholder Google Workspace authorization route."""
    return RedirectResponse(url="/", status_code=302)


@router.get("/health", summary="SSO router health")
async def sso_health() -> dict[str, str]:
    """Health check for SSO router registration."""
    return {"status": "ok", "service": "sso"}
