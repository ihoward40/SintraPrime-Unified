import datetime
from fastapi import APIRouter, Request, HTTPEq…ception

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/okta/callback")
async def okta_callback(request: Request):
    """Okta SSO callback handler"""
    timestamp = datetime.datetime.now(tz=datetime.timezone.utc).date()
    return {"status": "ok", "timestamp": str(timestamp)}

@router.post("/azure/callback")
async def azure_callback(request: Request):
    """Azure AD callback handler"""
    timestamp = datetime.datetime.now(tz=datetime.timezone.utc).date()
    return {"status": "ok", "timestamp": str(timestamp)}

@router.post("/google/callback")
async def google_callback(request: Request):
    """Google Workspace callback handler"""
    timestamp = datetime.datetime.now(tz=datetime.timezone.utc).date()
    return {"status": "ok", "timestamp": str(timestamp)}
