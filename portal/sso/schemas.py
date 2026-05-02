"""
Pydantic schemas for SSO router responses.
"""

from pydantic import BaseModel


class AuthorizeRequest(BaseModel):
    provider: str
    redirect_after_auth: str | None = None


class AuthorizeResponse(BaseModel):
    auth_url: str
    state: str
    csrf_token: str
    expires_in: int
