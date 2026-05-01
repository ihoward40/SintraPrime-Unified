"""
Session Storage Abstraction
Support for Redis and in-memory backends.
Fail-closed: operations raise explicit errors on unavailable backends.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict
import json
from datetime import datetime

from .session_models import SessionData, RefreshToken


class SessionStore(ABC):
    """Abstract base for session storage."""
    
    @abstractmethod
    async def save_session(self, session: SessionData, ttl_seconds: int) -> None:
        """Save session data. ttl_seconds overrides session.expires_at."""
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Retrieve session by ID."""
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """Delete session."""
        pass
    
    @abstractmethod
    async def revoke_session(self, session_id: str) -> None:
        """Mark session as revoked (soft delete)."""
        pass
    
    @abstractmethod
    async def save_refresh_token(self, token: RefreshToken, ttl_seconds: int) -> None:
        """Save refresh token."""
        pass
    
    @abstractmethod
    async def get_refresh_token(self, token_id: str) -> Optional[RefreshToken]:
        """Retrieve refresh token by ID."""
        pass
    
    @abstractmethod
    async def revoke_refresh_token(self, token_id: str) -> None:
        """Revoke refresh token."""
        pass


class InMemorySessionStore(SessionStore):
    """In-memory session store for testing."""
    
    def __init__(self):
        self._sessions: Dict[str, tuple] = {}  # session_id -> (SessionData, expiry_time)
        self._refresh_tokens: Dict[str, tuple] = {}  # token_id -> (RefreshToken, expiry_time)
    
    async def save_session(self, session: SessionData, ttl_seconds: int) -> None:
        """Save session in memory."""
        self._sessions[session.session_id] = (session, datetime.utcnow().timestamp() + ttl_seconds)
    
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session from memory."""
        if session_id not in self._sessions:
            return None
        
        session, expiry_time = self._sessions[session_id]
        if datetime.utcnow().timestamp() > expiry_time:
            del self._sessions[session_id]
            return None
        
        return session
    
    async def delete_session(self, session_id: str) -> None:
        """Delete session from memory."""
        self._sessions.pop(session_id, None)
    
    async def revoke_session(self, session_id: str) -> None:
        """Revoke session in memory."""
        if session_id in self._sessions:
            session, expiry_time = self._sessions[session_id]
            session.is_revoked = True
            session.revoked_at = datetime.utcnow()
    
    async def save_refresh_token(self, token: RefreshToken, ttl_seconds: int) -> None:
        """Save refresh token in memory."""
        self._refresh_tokens[token.token_id] = (token, datetime.utcnow().timestamp() + ttl_seconds)
    
    async def get_refresh_token(self, token_id: str) -> Optional[RefreshToken]:
        """Get refresh token from memory."""
        if token_id not in self._refresh_tokens:
            return None
        
        token, expiry_time = self._refresh_tokens[token_id]
        if datetime.utcnow().timestamp() > expiry_time:
            del self._refresh_tokens[token_id]
            return None
        
        return token
    
    async def revoke_refresh_token(self, token_id: str) -> None:
        """Revoke refresh token in memory."""
        if token_id in self._refresh_tokens:
            token, expiry_time = self._refresh_tokens[token_id]
            token.is_revoked = True
            token.revoked_at = datetime.utcnow()
    
    def clear(self) -> None:
        """Clear all stored sessions and tokens (for testing)."""
        self._sessions.clear()
        self._refresh_tokens.clear()


class RedisSessionStore(SessionStore):
    """Redis-backed session store for production."""

    def __init__(self, redis_client=None, *, redis_url: str = ""):
        """Initialize with a Redis client object or a redis_url string.

        Accepts either:
          - ``redis_client``: a pre-constructed ``redis.Redis`` instance, or
          - ``redis_url``: a connection URL (e.g. ``redis://localhost:6379/1``)
            from which a client is created automatically.
        """
        if redis_client is None and not redis_url:
            raise ValueError(
                "RedisSessionStore requires either redis_client or redis_url"
            )
        if redis_client is None:
            import redis as _redis
            redis_client = _redis.Redis.from_url(redis_url, decode_responses=True)
        self.redis = redis_client
        self.session_key_prefix = "sso:session:"
        self.refresh_token_key_prefix = "sso:refresh_token:"
    
    async def save_session(self, session: SessionData, ttl_seconds: int) -> None:
        """Save session to Redis with TTL."""
        key = f"{self.session_key_prefix}{session.session_id}"
        data = json.dumps(session.to_dict(), default=str)
        await self.redis.setex(key, ttl_seconds, data)
    
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session from Redis."""
        key = f"{self.session_key_prefix}{session_id}"
        data = await self.redis.get(key)
        
        if not data:
            return None
        
        session_dict = json.loads(data)
        return self._dict_to_session(session_dict)
    
    async def delete_session(self, session_id: str) -> None:
        """Delete session from Redis."""
        key = f"{self.session_key_prefix}{session_id}"
        await self.redis.delete(key)
    
    async def revoke_session(self, session_id: str) -> None:
        """Revoke session in Redis."""
        session = await self.get_session(session_id)
        if session:
            session.is_revoked = True
            session.revoked_at = datetime.utcnow()
            key = f"{self.session_key_prefix}{session_id}"
            ttl = max(1, int((session.expires_at - datetime.utcnow()).total_seconds()))
            data = json.dumps(session.to_dict(), default=str)
            await self.redis.setex(key, ttl, data)
    
    async def save_refresh_token(self, token: RefreshToken, ttl_seconds: int) -> None:
        """Save refresh token to Redis with TTL."""
        key = f"{self.refresh_token_key_prefix}{token.token_id}"
        data = json.dumps(token.to_dict(), default=str)
        await self.redis.setex(key, ttl_seconds, data)
    
    async def get_refresh_token(self, token_id: str) -> Optional[RefreshToken]:
        """Get refresh token from Redis."""
        key = f"{self.refresh_token_key_prefix}{token_id}"
        data = await self.redis.get(key)
        
        if not data:
            return None
        
        token_dict = json.loads(data)
        return self._dict_to_refresh_token(token_dict)
    
    async def revoke_refresh_token(self, token_id: str) -> None:
        """Revoke refresh token in Redis."""
        token = await self.get_refresh_token(token_id)
        if token:
            token.is_revoked = True
            token.revoked_at = datetime.utcnow()
            key = f"{self.refresh_token_key_prefix}{token_id}"
            ttl = max(1, int((token.expires_at - datetime.utcnow()).total_seconds()))
            data = json.dumps(token.to_dict(), default=str)
            await self.redis.setex(key, ttl, data)
    
    @staticmethod
    def _dict_to_session(data: Dict) -> SessionData:
        """Convert dict to SessionData."""
        return SessionData(
            session_id=data["session_id"],
            user_id=data["user_id"],
            email=data["email"],
            issuer=data["issuer"],
            audience=data["audience"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            name_id=data.get("name_id"),
            identity_provider=data.get("identity_provider"),
            auth_method=data.get("auth_method"),
            attributes=data.get("attributes", {}),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            is_revoked=data.get("is_revoked", False),
            revoked_at=datetime.fromisoformat(data["revoked_at"]) if data.get("revoked_at") else None,
        )
    
    @staticmethod
    def _dict_to_refresh_token(data: Dict) -> RefreshToken:
        """Convert dict to RefreshToken."""
        return RefreshToken(
            token_id=data["token_id"],
            session_id=data["session_id"],
            user_id=data["user_id"],
            issued_at=datetime.fromisoformat(data["issued_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            is_revoked=data.get("is_revoked", False),
            revoked_at=datetime.fromisoformat(data["revoked_at"]) if data.get("revoked_at") else None,
        )