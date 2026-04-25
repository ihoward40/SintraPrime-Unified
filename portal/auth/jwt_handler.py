"""
JWT access + refresh token management.
- Access tokens: 15-minute expiry, signed with JWT_SECRET_KEY
- Refresh tokens: 30-day expiry, signed with JWT_REFRESH_SECRET_KEY
- Token family rotation to detect refresh token reuse attacks
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
import structlog

from ..config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

# Token types
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


class TokenError(Exception):
    """Raised for any JWT validation failure."""
    pass


class TokenExpiredError(TokenError):
    """Raised specifically when a token has expired."""
    pass


# ── Creation ──────────────────────────────────────────────────────────────────

def create_access_token(
    *,
    user_id: str,
    tenant_id: str,
    role: str,
    permissions: list[str],
    jti: Optional[str] = None,
) -> str:
    """Create a short-lived access JWT."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "permissions": permissions,
        "type": ACCESS_TOKEN_TYPE,
        "jti": jti or str(uuid.uuid4()),
        "iat": now,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    logger.debug("jwt.access_token_created", user_id=user_id, expires=expire.isoformat())
    return token


def create_refresh_token(
    *,
    user_id: str,
    tenant_id: str,
    family: Optional[str] = None,
) -> tuple[str, str]:
    """
    Create a long-lived refresh JWT.
    Returns (token, family_id) — family enables rotation attack detection.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    family_id = family or str(uuid.uuid4())
    jti = str(uuid.uuid4())
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "type": REFRESH_TOKEN_TYPE,
        "family": family_id,
        "jti": jti,
        "iat": now,
        "exp": expire,
    }
    token = jwt.encode(
        payload, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    logger.debug("jwt.refresh_token_created", user_id=user_id, family=family_id)
    return token, family_id


# ── Verification ──────────────────────────────────────────────────────────────

def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate an access token. Raises TokenError on failure."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != ACCESS_TOKEN_TYPE:
            raise TokenError("Wrong token type")
        return payload
    except ExpiredSignatureError:
        raise TokenExpiredError("Access token has expired")
    except InvalidTokenError as exc:
        raise TokenError(f"Invalid access token: {exc}") from exc


def decode_refresh_token(token: str) -> Dict[str, Any]:
    """Decode and validate a refresh token. Raises TokenError on failure."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_REFRESH_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != REFRESH_TOKEN_TYPE:
            raise TokenError("Wrong token type")
        return payload
    except ExpiredSignatureError:
        raise TokenExpiredError("Refresh token has expired")
    except InvalidTokenError as exc:
        raise TokenError(f"Invalid refresh token: {exc}") from exc


def get_token_jti(token: str, *, is_refresh: bool = False) -> Optional[str]:
    """Extract JTI from a token without full verification (for blacklisting)."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_REFRESH_SECRET_KEY if is_refresh else settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},
        )
        return payload.get("jti")
    except Exception:
        return None
