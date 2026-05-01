\"\"\"
Pydantic schemas for SSO router responses.
\"\"\"

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class AuthorizeRequest(BaseModel):
    provider: str
    redirect_after_auth: Optional[str] = None

class AuthorizeResponse(BaseModel):
    auth_url: str
    state: str
    csrf_token: str
    expires_in: int
