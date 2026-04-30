"""
Comprehensive Session Management Test Suite
Tests configuration, models, JWT, storage, and session manager.
17+ tests covering fail-closed behavior and security properties.
"""
import pytest
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
import jwt as pyjwt

from portal.sso import (
    SessionManager,
    SessionConfig,
    JWTTokenService,
    SessionData,
    RefreshToken,
    TokenPair,
    InMemorySessionStore,
)


# ==============================================================================
# SessionConfig Tests (Fail-Closed Configuration)
# ==============================================================================

class TestSessionConfig:
    """Test session configuration and fail-closed behavior."""
    
    def test_config_validation_requires_jwt_secret(self):
        """Config must have JWT secret."""
        config = SessionConfig(
            jwt_secret_key="",  # Empty
            issuer="https://example.com",
            audience="app",
        )
        with pytest.raises(ValueError, match="jwt_secret_key is required"):
            config.validate()
    
    def test_config_validation_requires_min_secret_length(self):
        """JWT secret must be at least 32 characters."""
        config = SessionConfig(
            jwt_secret_key="short",
            issuer="https://example.com",
            audience="app",
        )
        with pytest.raises(ValueError, match="at least 32 characters"):
            config.validate()
    
    def test_config_validation_requires_issuer(self):
        """Config must have issuer."""
        config = SessionConfig(
            jwt_secret_key="a" * 32,
            issuer="",  # Empty
            audience="app",
        )
        with pytest.raises(ValueError, match="issuer is required"):
            config.validate()
    
    def test_config_validation_requires_audience(self):
        """Config must have audience."""
        config = SessionConfig(
            jwt_secret_key="a" * 32,
            issuer="https://example.com",
            audience="",  # Empty
        )
        with pytest.raises(ValueError, match="audience is required"):
            config.validate()
    
    def test_config_validation_valid_config(self):
        """Valid config passes validation."""
        config = SessionConfig(
            jwt_secret_key="a" * 32,
            issuer="https://example.com",
            audience="app",
        )
        config.validate()  # Should not raise


# ==============================================================================
# SessionData Tests (Model Validation)
# ==============================================================================

class TestSessionData:
    """Test session data models and expiry logic."""
    
    def test_session_data_create(self):
        """SessionData.create() generates valid session."""
        session = SessionData.create(
            user_id="user123",
            email="user@example.com",
            issuer="https://example.com",
            audience="app",
            ttl_seconds=3600,
        )
        assert session.session_id
        assert session.user_id == "user123"
        assert session.email == "user@example.com"
        assert not session.is_expired()
        assert session.is_valid()
    
    def test_session_data_is_expired(self):
        """is_expired() detects expired sessions."""
        session = SessionData.create(
            user_id="user123",
            email="user@example.com",
            issuer="https://example.com",
            audience="app",
            ttl_seconds=-1,  # Already expired
        )
        assert session.is_expired()
        assert not session.is_valid()
    
    def test_session_data_is_revoked(self):
        """is_valid() respects revoke flag."""
        session = SessionData.create(
            user_id="user123",
            email="user@example.com",
            issuer="https://example.com",
            audience="app",
            ttl_seconds=3600,
        )
        session.is_revoked = True
        session.revoked_at = datetime.utcnow()
        assert not session.is_valid()


# ==============================================================================
# RefreshToken Tests (Model Validation)
# ==============================================================================

class TestRefreshToken:
    """Test refresh token models."""
    
    def test_refresh_token_create(self):
        """RefreshToken.create() generates valid token."""
        token = RefreshToken.create(
            session_id="session123",
            user_id="user123",
            ttl_seconds=604800,
        )
        assert token.token_id
        assert token.session_id == "session123"
        assert not token.is_expired()
        assert token.is_valid()
    
    def test_refresh_token_is_expired(self):
        """is_expired() detects expired refresh tokens."""
        token = RefreshToken.create(
            session_id="session123",
            user_id="user123",
            ttl_seconds=-1,  # Already expired
        )
        assert token.is_expired()
        assert not token.is_valid()
    
    def test_refresh_token_is_revoked(self):
        """is_valid() respects revoke flag."""
        token = RefreshToken.create(
            session_id="session123",
            user_id="user123",
            ttl_seconds=604800,
        )
        token.is_revoked = True
        token.revoked_at = datetime.utcnow()
        assert not token.is_valid()


# ==============================================================================
# JWTTokenService Tests (Token Generation and Validation)
# ==============================================================================

class TestJWTTokenService:
    """Test JWT token generation and validation."""
    
    @pytest.fixture
    def config(self):
        """Standard test config."""
        return SessionConfig(
            jwt_secret_key="a" * 32,
            issuer="https://example.com",
            audience="test-app",
            jwt_expiration_seconds=3600,
        )
    
    @pytest.fixture
    def service(self, config):
        """JWT service instance."""
        return JWTTokenService(config)
    
    def test_generate_access_token(self, service):
        """generate_access_token() produces valid JWT."""
        token = service.generate_access_token(
            session_id="sess123",
            user_id="user123",
            email="user@example.com",
        )
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_validate_access_token(self, service):
        """validate_token() decodes and validates access tokens."""
        token = service.generate_access_token(
            session_id="sess123",
            user_id="user123",
            email="user@example.com",
        )
        payload = service.validate_token(token, token_type="access")
        assert payload["sub"] == "user123"
        assert payload["email"] == "user@example.com"
        assert payload["session_id"] == "sess123"
        assert payload["type"] == "access"
    
    def test_validate_expired_token(self):
        """validate_token() rejects expired tokens."""
        config = SessionConfig(
            jwt_secret_key="a" * 32,
            issuer="https://example.com",
            audience="test-app",
            jwt_expiration_seconds=1,  # 1 second
        )
        service = JWTTokenService(config)
        
        token = service.generate_access_token(
            session_id="sess123",
            user_id="user123",
            email="user@example.com",
        )
        
        # Wait for token to expire
        import time
        time.sleep(2)
        
        with pytest.raises(pyjwt.ExpiredSignatureError):
            service.validate_token(token, token_type="access")
    
    def test_validate_invalid_issuer(self, service):
        """validate_token() rejects tokens with wrong issuer."""
        token = service.generate_access_token(
            session_id="sess123",
            user_id="user123",
            email="user@example.com",
        )
        
        # Create new service with different issuer
        config2 = SessionConfig(
            jwt_secret_key="a" * 32,
            issuer="https://other.com",  # Different issuer
            audience="test-app",
        )
        service2 = JWTTokenService(config2)
        
        with pytest.raises(pyjwt.InvalidIssuerError):
            service2.validate_token(token, token_type="access")
    
    def test_validate_invalid_audience(self, service):
        """validate_token() rejects tokens with wrong audience."""
        token = service.generate_access_token(
            session_id="sess123",
            user_id="user123",
            email="user@example.com",
        )
        
        # Create new service with different audience
        config2 = SessionConfig(
            jwt_secret_key="a" * 32,
            issuer="https://example.com",
            audience="different-app",  # Different audience
        )
        service2 = JWTTokenService(config2)
        
        with pytest.raises(pyjwt.InvalidAudienceError):
            service2.validate_token(token, token_type="access")
    
    def test_validate_token_type_mismatch(self, service):
        """validate_token() rejects tokens with wrong type."""
        access_token = service.generate_access_token(
            session_id="sess123",
            user_id="user123",
            email="user@example.com",
        )
        
        with pytest.raises(pyjwt.InvalidTokenError, match="Token type mismatch"):
            service.validate_token(access_token, token_type="refresh")
    
    def test_validate_malformed_token(self, service):
        """validate_token() rejects malformed tokens."""
        with pytest.raises(pyjwt.InvalidTokenError):
            service.validate_token("not.a.token", token_type="access")
    
    def test_generate_token_pair(self, service):
        """generate_token_pair() produces both access and refresh tokens."""
        token_pair = service.generate_token_pair(
            session_id="sess123",
            user_id="user123",
            email="user@example.com",
            refresh_token_id="rt123",
        )
        assert isinstance(token_pair, TokenPair)
        assert token_pair.access_token
        assert token_pair.refresh_token
        assert token_pair.token_type == "Bearer"


# ==============================================================================
# SessionManager Tests (Full Session Lifecycle)
# ==============================================================================

class TestSessionManager:
    """Test session manager and complete workflows."""
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        """create_session() generates session and token pair."""
        config = SessionConfig(
            jwt_secret_key="a" * 32,
            issuer="https://example.com",
            audience="test-app",
            jwt_expiration_seconds=3600,
            session_ttl_seconds=3600,
            refresh_token_ttl_seconds=604800,
            session_store_type="memory",
        )
        store = InMemorySessionStore()
        manager = SessionManager(config, store=store)
        
        token_pair = await manager.create_session(
            user_id="user123",
            email="user@example.com",
            identity_provider="okta",
            auth_method="saml",
        )
        
        assert isinstance(token_pair, TokenPair)
        assert token_pair.access_token
        assert token_pair.refresh_token
    
    @pytest.mark.asyncio
    async def test_validate_session_with_valid_token(self):
        """validate_session() retrieves valid session."""
        config = SessionConfig(
            jwt_secret_key="a" * 32,
            issuer="https://example.com",
            audience="test-app",
            jwt_expiration_seconds=3600,
            session_ttl_seconds=3600,
            refresh_token_ttl_seconds=604800,
            session_store_type="memory",
        )
        store = InMemorySessionStore()
        manager = SessionManager(config, store=store)
        
        token_pair = await manager.create_session(
            user_id="user123",
            email="user@example.com",
        )
        
        session = await manager.validate_session(token_pair.access_token)
        assert session is not None
        assert session.user_id == "user123"
        assert session.email == "user@example.com"
    
    @pytest.mark.asyncio
    async def test_validate_session_with_invalid_token(self):
        """validate_session() returns None for invalid token."""
        config = SessionConfig(
            jwt_secret_key="a" * 32,
            issuer="https://example.com",
            audience="test-app",
            jwt_expiration_seconds=3600,
            session_ttl_seconds=3600,
            refresh_token_ttl_seconds=604800,
            session_store_type="memory",
        )
        store = InMemorySessionStore()
        manager = SessionManager(config, store=store)
        
        session = await manager.validate_session("invalid.token.here")
        assert session is None
    
    @pytest.mark.asyncio
    async def test_refresh_session_with_valid_token(self):
        """refresh_session() creates new token pair."""
        config = SessionConfig(
            jwt_secret_key="a" * 32,
            issuer="https://example.com",
            audience="test-app",
            jwt_expiration_seconds=3600,
            session_ttl_seconds=3600,
            refresh_token_ttl_seconds=604800,
            session_store_type="memory",
        )
        store = InMemorySessionStore()
        manager = SessionManager(config, store=store)
        
        token_pair1 = await manager.create_session(
            user_id="user123",
            email="user@example.com",
        )
        
        # Refresh
        token_pair2 = await manager.refresh_session(token_pair1.refresh_token)
        assert token_pair2 is not None
        # Verify new refresh token ID is different (proves new token was created)
        payload1 = manager.jwt_service.validate_token(token_pair1.refresh_token, token_type="refresh")
        payload2 = manager.jwt_service.validate_token(token_pair2.refresh_token, token_type="refresh")
        assert payload1["refresh_token_id"] != payload2["refresh_token_id"]


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestSessionIntegration:
    """Integration tests for complete workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_auth_flow(self):
        """Test complete authentication and refresh flow."""
        config = SessionConfig(
            jwt_secret_key="a" * 32,
            issuer="https://example.com",
            audience="test-app",
            jwt_expiration_seconds=3600,
            session_ttl_seconds=3600,
            refresh_token_ttl_seconds=604800,
            session_store_type="memory",
        )
        
        store = InMemorySessionStore()
        manager = SessionManager(config, store=store)
        
        # 1. Create session
        token_pair1 = await manager.create_session(
            user_id="user123",
            email="user@example.com",
            identity_provider="okta",
            auth_method="saml",
        )
        
        # 2. Validate access token
        session1 = await manager.validate_session(token_pair1.access_token)
        assert session1 is not None
        assert session1.user_id == "user123"
        
        # 3. Refresh tokens
        token_pair2 = await manager.refresh_session(token_pair1.refresh_token)
        assert token_pair2 is not None
        assert token_pair2.access_token != token_pair1.access_token
        
        # 4. Validate new access token
        session2 = await manager.validate_session(token_pair2.access_token)
        assert session2 is not None
        assert session2.user_id == "user123"
        
        # 5. Logout (revoke)
        payload = manager.jwt_service.validate_token(
            token_pair2.access_token,
            token_type="access"
        )
        session_id = payload["session_id"]
        await manager.revoke_session(session_id)
        
        # 6. Access token should now fail
        session3 = await manager.validate_session(token_pair2.access_token)
        assert session3 is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])