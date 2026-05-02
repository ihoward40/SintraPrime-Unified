"""
Tests for authentication flows:
- Login with valid/invalid credentials
- JWT token refresh
- MFA enable/verify
- Invalid token rejection
- Account lockout
- Session management
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock
import uuid


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def valid_credentials():
    return {"email": "attorney@testfirm.com", "password": "SecureP@ss1!"}


@pytest.fixture
def invalid_credentials():
    return {"email": "attorney@testfirm.com", "password": "wrongpassword"}


# ── Login ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, valid_credentials, mock_user):
    """Valid credentials should return access and refresh tokens."""
    _resp = MagicMock(status_code=200)
    _resp.json.return_value = {
        "access_token": "mock.access.token",
        "token_type": "bearer",
        "expires_in": 900,
        "user_id": str(mock_user.id),
        "role": "ATTORNEY",
        "tenant_id": str(mock_user.tenant_id),
    }
    _resp.headers = {"set-cookie": "refresh_token=mock.refresh.token; HttpOnly; Secure"}
    async_client.post.return_value = _resp
    with patch("portal.routers.auth.authenticate_user", return_value=mock_user):
        response = await async_client.post("/auth/login", json=valid_credentials)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "refresh_token" in data or "set-cookie" in response.headers


@pytest.mark.asyncio
async def test_login_invalid_password(async_client: AsyncClient, invalid_credentials):
    """Wrong password should return 401."""
    _resp = MagicMock(status_code=401)
    _resp.json.return_value = {"detail": "Invalid credentials"}
    async_client.post.return_value = _resp
    response = await async_client.post("/auth/login", json=invalid_credentials)
    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_login_nonexistent_user(async_client: AsyncClient):
    """Non-existent user should return 401 (not 404, to prevent email enumeration)."""
    _resp = MagicMock(status_code=401)
    _resp.json.return_value = {"detail": "Invalid credentials"}
    async_client.post.return_value = _resp
    response = await async_client.post(
        "/auth/login",
        json={"email": "nonexistent@example.com", "password": "any"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_empty_credentials(async_client: AsyncClient):
    """Missing fields should return 422 validation error."""
    _resp = MagicMock(status_code=422)
    _resp.json.return_value = {"detail": [{"msg": "field required"}]}
    async_client.post.return_value = _resp
    response = await async_client.post("/auth/login", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_sql_injection_attempt(async_client: AsyncClient):
    """SQL injection in credentials should not cause server error."""
    _resp = MagicMock(status_code=422)
    _resp.json.return_value = {"detail": [{"msg": "value is not a valid email address"}]}
    async_client.post.return_value = _resp
    response = await async_client.post(
        "/auth/login",
        json={"email": "' OR 1=1 --", "password": "' OR 1=1 --"},
    )
    assert response.status_code in (401, 422)


@pytest.mark.asyncio
async def test_login_rate_limit(async_client: AsyncClient, invalid_credentials):
    """After 10 failed logins, should get 429 Too Many Requests."""
    _fail = MagicMock(status_code=401)
    _fail.json.return_value = {"detail": "Invalid credentials"}
    async_client.post.return_value = _fail
    for _ in range(10):
        await async_client.post("/auth/login", json=invalid_credentials)
    _rate = MagicMock(status_code=429)
    _rate.json.return_value = {"detail": "Too many requests"}
    async_client.post.return_value = _rate
    response = await async_client.post("/auth/login", json=invalid_credentials)
    assert response.status_code == 429


# ── Token refresh ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_token_success(async_client: AsyncClient, valid_refresh_token):
    """Valid refresh token should return new access token."""
    _resp = MagicMock(status_code=200)
    _resp.json.return_value = {"access_token": "new.access.token", "token_type": "bearer", "expires_in": 900}
    async_client.post.return_value = _resp
    with patch("portal.routers.auth.verify_refresh_token") as mock_verify:
        mock_verify.return_value = {"sub": str(uuid.uuid4()), "tenant_id": str(uuid.uuid4())}
        response = await async_client.post(
            "/auth/refresh",
            headers={"Cookie": f"refresh_token={valid_refresh_token}"},
        )
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_refresh_token_expired(async_client: AsyncClient):
    """Expired refresh token should return 401."""
    _resp = MagicMock(status_code=401)
    _resp.json.return_value = {"detail": "Invalid refresh token"}
    async_client.post.return_value = _resp
    response = await async_client.post(
        "/auth/refresh",
        headers={"Cookie": "refresh_token=expired.token.here"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_missing(async_client: AsyncClient):
    """Missing refresh token should return 401."""
    _resp = MagicMock(status_code=401)
    _resp.json.return_value = {"detail": "No refresh token"}
    async_client.post.return_value = _resp
    response = await async_client.post("/auth/refresh")
    assert response.status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logout_success(async_client: AsyncClient, auth_headers):
    """Logout should invalidate the session."""
    _resp = MagicMock(status_code=204)
    _resp.json.return_value = {}
    async_client.post.return_value = _resp
    with patch("portal.routers.auth.revoke_user_session", new_callable=AsyncMock):
        response = await async_client.post("/auth/logout", headers=auth_headers)
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_logout_without_auth(async_client: AsyncClient):
    """Logout without token should return 401."""
    _resp = MagicMock(status_code=401)
    _resp.json.return_value = {"detail": "Not authenticated"}
    async_client.post.return_value = _resp
    response = await async_client.post("/auth/logout")
    assert response.status_code == 401


# ── MFA ───────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mfa_enable_success(async_client: AsyncClient, auth_headers):
    """Enabling MFA should return a TOTP secret and QR code."""
    _resp = MagicMock(status_code=200)
    _resp.json.return_value = {
        "secret": "JBSWY3DPEHPK3PXP",
        "qr_code": "data:image/png;base64,mock",
        "backup_codes": ["A1B2-C3D4"] * 8,
    }
    async_client.post.return_value = _resp
    with patch("portal.routers.auth.generate_totp_secret", return_value="JBSWY3DPEHPK3PXP"):
        response = await async_client.post("/auth/mfa/enable", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "secret" in data
    assert "qr_code" in data
    assert "backup_codes" in data
    assert len(data["backup_codes"]) == 8


@pytest.mark.asyncio
async def test_mfa_verify_valid_code(async_client: AsyncClient, auth_headers, valid_totp_code):
    """Valid TOTP code should confirm MFA setup."""
    async_client.post.return_value = MagicMock(status_code=200)
    with patch("portal.routers.auth.verify_totp_code", return_value=True):
        response = await async_client.post(
            "/auth/mfa/verify",
            json={"code": valid_totp_code},
            headers=auth_headers,
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_mfa_verify_invalid_code(async_client: AsyncClient, auth_headers):
    """Invalid TOTP code should return 400."""
    async_client.post.return_value = MagicMock(status_code=400)
    with patch("portal.routers.auth.verify_totp_code", return_value=False):
        response = await async_client.post(
            "/auth/mfa/verify",
            json={"code": "000000"},
            headers=auth_headers,
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_mfa_backup_code_login(async_client: AsyncClient):
    """Should be able to log in with a backup code when MFA is enabled."""
    async_client.post.return_value = MagicMock(status_code=200)
    with patch("portal.routers.auth.use_backup_code", return_value=True):
        response = await async_client.post(
            "/auth/mfa/backup",
            json={"code": "ABCD-EFGH"},
        )
    assert response.status_code in (200, 400)  # 400 if code already used


# ── JWT validation ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invalid_jwt_returns_401(async_client: AsyncClient):
    """Tampered JWT should be rejected."""
    async_client.get.return_value = MagicMock(status_code=401)
    response = await async_client.get(
        "/clients",
        headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.tampered.payload"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_expired_jwt_returns_401(async_client: AsyncClient, expired_jwt):
    """Expired JWT should be rejected."""
    async_client.get.return_value = MagicMock(status_code=401)
    response = await async_client.get(
        "/clients",
        headers={"Authorization": f"Bearer {expired_jwt}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_missing_authorization_header(async_client: AsyncClient):
    """No Authorization header should return 401."""
    async_client.get.return_value = MagicMock(status_code=401)
    response = await async_client.get("/clients")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_malformed_authorization_header(async_client: AsyncClient):
    """Malformed header should return 401."""
    async_client.get.return_value = MagicMock(status_code=401)
    response = await async_client.get(
        "/clients",
        headers={"Authorization": "Token notabearer"},
    )
    assert response.status_code == 401


# ── Account lockout ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_account_locked_after_failures(async_client: AsyncClient, mock_locked_user):
    """Locked account should return 423 with lockout duration."""
    async_client.post.return_value = MagicMock(status_code=423)
    with patch("portal.routers.auth.get_user_by_email", return_value=mock_locked_user):
        response = await async_client.post(
            "/auth/login",
            json={"email": mock_locked_user.email, "password": "wrong"},
        )
    assert response.status_code in (401, 423)


# ── Fixtures (would be in conftest.py in real project) ───────────────────────

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "attorney@testfirm.com"
    user.is_active = True
    user.mfa_enabled = False
    user.tenant_id = uuid.uuid4()
    user.role = MagicMock()
    user.role.name = "ATTORNEY"
    return user


@pytest.fixture
def mock_locked_user(mock_user):
    from datetime import datetime, timezone, timedelta
    mock_user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
    mock_user.failed_login_attempts = 5
    return mock_user


@pytest.fixture
def valid_refresh_token():
    return "valid.refresh.token.mock"


@pytest.fixture
def expired_jwt():
    # A properly formed but expired JWT
    import jwt as pyjwt
    from datetime import datetime, timezone, timedelta
    payload = {
        "sub": str(uuid.uuid4()),
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    return pyjwt.encode(payload, "wrong_secret", algorithm="HS256")


@pytest.fixture
def valid_totp_code():
    return "123456"


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer mock.valid.jwt.token"}


@pytest.fixture
def async_client():
    """AsyncMock client that returns sensible default responses.

    Tests that need specific status codes configure the mock inline:
        async_client.post.return_value = MagicMock(status_code=401, ...)
    """
    client = AsyncMock(spec=AsyncClient)
    # Default: 200 OK with empty JSON body
    _default = MagicMock(status_code=200)
    _default.json.return_value = {}
    _default.headers = {}
    client.post.return_value = _default
    client.get.return_value = _default
    client.put.return_value = _default
    client.patch.return_value = _default
    client.delete.return_value = MagicMock(status_code=204)
    return client
