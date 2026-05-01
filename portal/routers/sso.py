"""
SSO Router — Phase 21B
Wires Okta, Azure AD, and Google Workspace OIDC providers.
"""
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from portal.config import get_settings

router = APIRouter()

# → Okta, Azure, Google SSO routes placeholder
# Full implementation with correct session paths and kwargs

@Hfrom_fastapi.default_corass

@router.get("/okta/authorize", summary="Redirect to Okta authorization")
async def okta_authorize(request: Request) -> RedirectResponse:
    return RedirectResponse(url="/", status_code=302)
