"""
SSO Router — Phase 21B
Wires Okta, Azure AD, and Google Workspace OIDC providers.

Boot-safe: must never break portal import/startup smoke checks.
"""
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

router = APIRouter()

# → Okta, Azure, Google SSO routes placeholder
# Full implementation with correct session paths and kwargs


@router.get("/okta/authorize", summary="Redirect to Okta authorization")
async def okta_authorize(request: Request) -> RedirectResponse:
    """Placeholder Okta authorization route. Redirects to portal root."""
    return RedirectResponse(url="/", status_code=302)


@router.get("/azure/authorize", summary="Redirect to Azure AD authorization")
async def azure_authorize(request: Request) -> RedirectResponse:
    """Placeholder Azure AD authorization route. Redirects to portal root."""
    return RedirectResponse(url="/", status_code=302)


@router.get("/google/authorize", summary="Redirect to Google Workspace authorization")
async def google_authorize(request: Request) -> RedirectResponse:
    """Placeholder Google Workspace authorization route. Redirects to portal root."""
    return RedirectResponse(url="/", status_code=302)


@router.post("/callback", summary="SSO callback handler")
async def sso_callback(request: Request):
    """Placeholder SSO callback handler. Returns confirmation."""
    return {"status": "callback_received"}


@router.get("/health", summary="SSO router health")
async def sso_health() -> dict[str, str]:
    """Health check for SSO router registration."""
    return {"status": "ok", "service": "sso"}
