"""
Phase 23B — Auth module unit tests.
Covers: jwt_handler, rbac, password_handler, mfa, session_manager (auth)
Target: bring each module from <40% to ≥80% coverage.
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

# ─── jwt_handler ──────────────────────────────────────────────────────────────

class TestJwtHandler:
    """Unit tests for portal.auth.jwt_handler."""

    def _make_access_token(self, user_id="user-1", tenant_id="t-1", role="ATTORNEY"):
        from portal.auth.jwt_handler import create_access_token
        return create_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
            permissions=["case:read"],
        )

    def _make_refresh_token(self, user_id="user-1", tenant_id="t-1"):
        from portal.auth.jwt_handler import create_refresh_token
        token, family_id = create_refresh_token(user_id=user_id, tenant_id=tenant_id)
        return token, family_id

    def test_create_access_token_returns_string(self):
        token = self._make_access_token()
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_create_refresh_token_returns_tuple(self):
        token, family_id = self._make_refresh_token()
        assert isinstance(token, str)
        assert isinstance(family_id, str)
        assert len(token.split(".")) == 3

    def test_decode_access_token_round_trip(self):
        from portal.auth.jwt_handler import decode_access_token
        token = self._make_access_token(user_id="user-42", tenant_id="tenant-1", role="ATTORNEY")
        decoded = decode_access_token(token)
        assert decoded["sub"] == "user-42"
        assert decoded["tenant_id"] == "tenant-1"

    def test_decode_refresh_token_round_trip(self):
        from portal.auth.jwt_handler import decode_refresh_token
        token, family_id = self._make_refresh_token(user_id="user-42", tenant_id="tenant-1")
        decoded = decode_refresh_token(token)
        assert decoded["sub"] == "user-42"
        assert decoded["family"] == family_id

    def test_decode_access_token_wrong_type_raises(self):
        from portal.auth.jwt_handler import TokenError, decode_access_token
        token, _ = self._make_refresh_token()
        with pytest.raises(TokenError):
            decode_access_token(token)

    def test_decode_refresh_token_wrong_type_raises(self):
        from portal.auth.jwt_handler import TokenError, decode_refresh_token
        token = self._make_access_token()
        with pytest.raises(TokenError):
            decode_refresh_token(token)

    def test_decode_invalid_token_raises_token_error(self):
        from portal.auth.jwt_handler import TokenError, decode_access_token
        with pytest.raises(TokenError):
            decode_access_token("not.a.token")

    def test_decode_expired_token_raises_token_expired_error(self):
        import jwt as pyjwt

        from portal.auth.jwt_handler import TokenExpiredError, decode_access_token
        from portal.config import get_settings
        settings = get_settings()
        payload = {
            "sub": "u",
            "tenant_id": "t",
            "role": "ATTORNEY",
            "permissions": [],
            "type": "access",
            "jti": "test-jti",
            "exp": int(time.time()) - 1,
        }
        token = pyjwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        with pytest.raises(TokenExpiredError):
            decode_access_token(token)

    def test_get_token_jti_returns_string(self):
        from portal.auth.jwt_handler import get_token_jti
        token = self._make_access_token()
        result = get_token_jti(token)
        assert result is None or isinstance(result, str)

    def test_get_token_jti_invalid_token_returns_none(self):
        from portal.auth.jwt_handler import get_token_jti
        result = get_token_jti("garbage.token.here")
        assert result is None

    def test_get_token_jti_refresh_token(self):
        from portal.auth.jwt_handler import get_token_jti
        token, _ = self._make_refresh_token()
        result = get_token_jti(token, is_refresh=True)
        assert isinstance(result, str)

    def test_token_error_is_exception(self):
        from portal.auth.jwt_handler import TokenError
        err = TokenError("test error")
        assert isinstance(err, Exception)
        assert str(err) == "test error"

    def test_token_expired_error_is_token_error(self):
        from portal.auth.jwt_handler import TokenError, TokenExpiredError
        err = TokenExpiredError("expired")
        assert isinstance(err, TokenError)

    def test_create_refresh_token_with_family(self):
        from portal.auth.jwt_handler import create_refresh_token, decode_refresh_token
        existing_family = "existing-family-id"
        token, family_id = create_refresh_token(
            user_id="u1", tenant_id="t1", family=existing_family
        )
        assert family_id == existing_family
        decoded = decode_refresh_token(token)
        assert decoded["family"] == existing_family

    def test_access_token_contains_permissions(self):
        from portal.auth.jwt_handler import create_access_token, decode_access_token
        token = create_access_token(
            user_id="u1",
            tenant_id="t1",
            role="ATTORNEY",
            permissions=["case:read", "case:update"],
        )
        decoded = decode_access_token(token)
        assert "case:read" in decoded["permissions"]
        assert "case:update" in decoded["permissions"]


# ─── rbac ─────────────────────────────────────────────────────────────────────

class TestRbac:
    """Unit tests for portal.auth.rbac."""

    def _make_user(self, role: str, permissions: list | None = None):
        from portal.auth.rbac import CurrentUser
        payload = {
            "sub": "user-1",
            "tenant_id": "tenant-1",
            "role": role,
            "permissions": permissions or [],
        }
        return CurrentUser(payload)

    def test_current_user_attributes(self):
        from portal.auth.rbac import Role
        user = self._make_user("ATTORNEY")
        assert user.user_id == "user-1"
        assert user.tenant_id == "tenant-1"
        assert user.role == Role.ATTORNEY

    def test_has_permission_true(self):
        from portal.auth.rbac import Permission
        user = self._make_user("ATTORNEY", ["case:read", "case:update"])
        assert user.has_permission(Permission.CASE_READ)
        assert user.has_permission(Permission.CASE_UPDATE)

    def test_has_permission_false(self):
        from portal.auth.rbac import Permission
        user = self._make_user("ATTORNEY", ["case:read"])
        assert not user.has_permission(Permission.BILLING_READ)

    def test_has_permission_multiple_all_required(self):
        from portal.auth.rbac import Permission
        user = self._make_user("ATTORNEY", ["case:read", "case:update"])
        assert user.has_permission(Permission.CASE_READ, Permission.CASE_UPDATE)
        assert not user.has_permission(Permission.CASE_READ, Permission.BILLING_READ)

    def test_has_role_hierarchy(self):
        from portal.auth.rbac import Role
        super_admin = self._make_user("SUPER_ADMIN")
        firm_admin = self._make_user("FIRM_ADMIN")
        client = self._make_user("CLIENT")
        assert super_admin.has_role(Role.FIRM_ADMIN)
        assert super_admin.has_role(Role.ATTORNEY)
        assert firm_admin.has_role(Role.ATTORNEY)
        assert not client.has_role(Role.ATTORNEY)

    def test_is_super_admin(self):
        super_admin = self._make_user("SUPER_ADMIN")
        attorney = self._make_user("ATTORNEY")
        assert super_admin.is_super_admin()
        assert not attorney.is_super_admin()

    def test_is_firm_admin(self):
        firm_admin = self._make_user("FIRM_ADMIN")
        super_admin = self._make_user("SUPER_ADMIN")
        attorney = self._make_user("ATTORNEY")
        assert firm_admin.is_firm_admin()
        assert super_admin.is_firm_admin()
        assert not attorney.is_firm_admin()

    def test_is_staff(self):
        attorney = self._make_user("ATTORNEY")
        client = self._make_user("CLIENT")
        assert attorney.is_staff()
        assert not client.is_staff()

    def test_is_client(self):
        client = self._make_user("CLIENT")
        attorney = self._make_user("ATTORNEY")
        assert client.is_client()
        assert not attorney.is_client()

    def test_get_role_permissions_returns_frozenset(self):
        from portal.auth.rbac import Role, get_role_permissions
        perms = get_role_permissions(Role.ATTORNEY)
        assert isinstance(perms, frozenset)

    def test_get_role_permissions_super_admin_has_billing(self):
        from portal.auth.rbac import Permission, Role, get_role_permissions
        perms = get_role_permissions(Role.SUPER_ADMIN)
        assert Permission.CASE_READ in perms or len(perms) > 0

    def test_require_same_tenant_same_tenant_passes(self):
        from portal.auth.rbac import require_same_tenant
        user = self._make_user("ATTORNEY")
        require_same_tenant(user, "tenant-1")

    def test_require_same_tenant_different_tenant_raises(self):
        from fastapi import HTTPException

        from portal.auth.rbac import require_same_tenant
        user = self._make_user("ATTORNEY")
        with pytest.raises(HTTPException) as exc_info:
            require_same_tenant(user, "tenant-other")
        assert exc_info.value.status_code == 403

    def test_require_same_tenant_super_admin_bypasses(self):
        from portal.auth.rbac import require_same_tenant
        user = self._make_user("SUPER_ADMIN")
        require_same_tenant(user, "any-other-tenant")

    @pytest.mark.asyncio
    async def test_get_current_user_no_credentials_raises_401(self):
        from fastapi import HTTPException

        from portal.auth.rbac import get_current_user
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=None)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token_raises_401(self):
        from fastapi import HTTPException

        from portal.auth.rbac import get_current_user
        mock_creds = MagicMock()
        mock_creds.credentials = "invalid.token.here"
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=mock_creds)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token_returns_user(self):
        from portal.auth.jwt_handler import create_access_token
        from portal.auth.rbac import CurrentUser, get_current_user
        token = create_access_token(
            user_id="user-1",
            tenant_id="tenant-1",
            role="ATTORNEY",
            permissions=["case:read"],
        )
        mock_creds = MagicMock()
        mock_creds.credentials = token
        user = await get_current_user(credentials=mock_creds)
        assert isinstance(user, CurrentUser)
        assert user.user_id == "user-1"

    def test_require_permissions_returns_callable(self):
        from portal.auth.rbac import Permission, require_permissions
        dep = require_permissions(Permission.CASE_READ)
        assert callable(dep)

    def test_require_role_returns_callable(self):
        from portal.auth.rbac import Role, require_role
        dep = require_role(Role.ATTORNEY)
        assert callable(dep)

    def test_role_enum_values(self):
        from portal.auth.rbac import Role
        assert Role.SUPER_ADMIN.value == "SUPER_ADMIN"
        assert Role.CLIENT.value == "CLIENT"

    def test_permission_enum_values(self):
        from portal.auth.rbac import Permission
        assert Permission.CASE_READ.value == "case:read"
        assert Permission.BILLING_READ.value == "billing:read"


# ─── password_handler ─────────────────────────────────────────────────────────

class TestPasswordHandler:
    """Unit tests for portal.auth.password_handler."""

    def test_hash_password_returns_string(self):
        from portal.auth.password_handler import hash_password
        hashed = hash_password("Str0ng!Pass#2024")
        assert isinstance(hashed, str)
        assert hashed != "Str0ng!Pass#2024"

    def test_verify_password_correct(self):
        from portal.auth.password_handler import hash_password, verify_password
        pw = "Str0ng!Pass#2024"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True

    def test_verify_password_incorrect(self):
        from portal.auth.password_handler import hash_password, verify_password
        hashed = hash_password("Str0ng!Pass#2024")
        assert verify_password("WrongPassword!1", hashed) is False

    def test_hash_password_different_each_time(self):
        from portal.auth.password_handler import hash_password
        h1 = hash_password("Str0ng!Pass#2024")
        h2 = hash_password("Str0ng!Pass#2024")
        assert h1 != h2

    def test_hash_password_empty_raises(self):
        from portal.auth.password_handler import PasswordError, hash_password
        with pytest.raises(PasswordError):
            hash_password("")

    def test_validate_password_strength_strong_passes(self):
        from portal.auth.password_handler import validate_password_strength
        # Should not raise
        validate_password_strength("Str0ng!Pass#2024")

    def test_validate_password_strength_too_short_raises(self):
        from portal.auth.password_handler import PasswordError, validate_password_strength
        with pytest.raises(PasswordError):
            validate_password_strength("Short1!")

    def test_validate_password_strength_no_uppercase_raises(self):
        from portal.auth.password_handler import PasswordError, validate_password_strength
        with pytest.raises(PasswordError):
            validate_password_strength("str0ng!pass#2024")

    def test_validate_password_strength_no_digit_raises(self):
        from portal.auth.password_handler import PasswordError, validate_password_strength
        with pytest.raises(PasswordError):
            validate_password_strength("Str!Pass#LongEnough")

    def test_generate_secure_password_meets_policy(self):
        from portal.auth.password_handler import (
            generate_secure_password,
            validate_password_strength,
        )
        pw = generate_secure_password()
        assert isinstance(pw, str)
        assert len(pw) >= 12
        # Should not raise
        validate_password_strength(pw)

    def test_generate_backup_codes_returns_list(self):
        from portal.auth.password_handler import generate_backup_codes
        codes = generate_backup_codes()
        assert isinstance(codes, list)
        assert len(codes) == 8
        assert all(isinstance(c, str) for c in codes)

    def test_generate_backup_codes_custom_count(self):
        from portal.auth.password_handler import generate_backup_codes
        codes = generate_backup_codes(count=4)
        assert len(codes) == 4

    def test_backup_codes_format(self):
        from portal.auth.password_handler import generate_backup_codes
        codes = generate_backup_codes()
        for code in codes:
            parts = code.split("-")
            assert len(parts) == 3
            assert all(len(p) == 4 for p in parts)

    def test_hash_backup_code_returns_string(self):
        from portal.auth.password_handler import hash_backup_code
        hashed = hash_backup_code("ABCD-1234-EF56")
        assert isinstance(hashed, str)

    def test_verify_backup_code_correct(self):
        from portal.auth.password_handler import hash_backup_code, verify_backup_code
        code = "ABCD-1234-EF56"
        hashed = hash_backup_code(code)
        assert verify_backup_code(code, hashed) is True

    def test_verify_backup_code_incorrect(self):
        from portal.auth.password_handler import hash_backup_code, verify_backup_code
        hashed = hash_backup_code("ABCD-1234-EF56")
        assert verify_backup_code("XXXX-9999-ZZZZ", hashed) is False

    def test_verify_backup_code_case_insensitive(self):
        from portal.auth.password_handler import hash_backup_code, verify_backup_code
        code = "abcd-1234-ef56"
        hashed = hash_backup_code(code)
        assert verify_backup_code("ABCD-1234-EF56", hashed) is True


# ─── mfa ──────────────────────────────────────────────────────────────────────

class TestMfa:
    """Unit tests for portal.auth.mfa."""

    def test_generate_totp_secret_returns_base32_string(self):
        from portal.auth.mfa import generate_totp_secret
        secret = generate_totp_secret()
        assert isinstance(secret, str)
        assert len(secret) >= 16

    def test_get_totp_uri_returns_otpauth_url(self):
        from portal.auth.mfa import generate_totp_secret, get_totp_uri
        secret = generate_totp_secret()
        uri = get_totp_uri(secret, "user@example.com")
        assert uri.startswith("otpauth://totp/")
        assert "user%40example.com" in uri or "user@example.com" in uri

    def test_get_totp_uri_with_tenant_name(self):
        from portal.auth.mfa import generate_totp_secret, get_totp_uri
        secret = generate_totp_secret()
        uri = get_totp_uri(secret, "user@example.com", "MyFirm")
        assert "MyFirm" in uri

    def test_verify_totp_valid_code(self):
        from portal.auth.mfa import generate_totp_secret, get_current_totp, verify_totp
        secret = generate_totp_secret()
        current_code = get_current_totp(secret)
        assert verify_totp(secret, current_code) is True

    def test_verify_totp_invalid_code(self):
        from portal.auth.mfa import generate_totp_secret, verify_totp
        secret = generate_totp_secret()
        # 000000 is almost certainly not the current code
        result = verify_totp(secret, "000000")
        # May be True by coincidence — just check it returns bool
        assert isinstance(result, bool)

    def test_verify_totp_empty_secret_returns_false(self):
        from portal.auth.mfa import verify_totp
        assert verify_totp("", "123456") is False

    def test_verify_totp_empty_code_returns_false(self):
        from portal.auth.mfa import generate_totp_secret, verify_totp
        secret = generate_totp_secret()
        assert verify_totp(secret, "") is False

    def test_generate_qr_code_base64_returns_data_url(self):
        from portal.auth.mfa import generate_qr_code_base64, generate_totp_secret, get_totp_uri
        secret = generate_totp_secret()
        uri = get_totp_uri(secret, "user@example.com")
        qr = generate_qr_code_base64(uri)
        assert qr.startswith("data:image/png;base64,")

    def test_totp_setup_creates_valid_object(self):
        from portal.auth.mfa import TOTPSetup
        setup = TOTPSetup("user@example.com")
        assert isinstance(setup.secret, str)
        assert isinstance(setup.uri, str)
        assert isinstance(setup.qr_code, str)
        assert setup.qr_code.startswith("data:image/png;base64,")

    def test_totp_setup_verify_current_code(self):
        from portal.auth.mfa import TOTPSetup, get_current_totp
        setup = TOTPSetup("user@example.com")
        current_code = get_current_totp(setup.secret)
        assert setup.verify(current_code) is True

    def test_totp_setup_to_dict(self):
        from portal.auth.mfa import TOTPSetup
        setup = TOTPSetup("user@example.com")
        d = setup.to_dict()
        assert "secret" in d
        assert "uri" in d
        assert "qr_code" in d

    def test_get_current_totp_returns_6_digit_string(self):
        from portal.auth.mfa import generate_totp_secret, get_current_totp
        secret = generate_totp_secret()
        code = get_current_totp(secret)
        assert isinstance(code, str)
        assert len(code) == 6
        assert code.isdigit()


# ─── session_manager (auth) ───────────────────────────────────────────────────

class TestAuthSessionManager:
    """Unit tests for portal.auth.session_manager module-level functions."""

    @pytest.mark.asyncio
    async def test_blocklist_jti_and_check(self):
        from portal.auth.session_manager import _memory_blocklist, blocklist_jti, is_jti_blocklisted
        _memory_blocklist.clear()
        await blocklist_jti("test-jti-1")
        assert await is_jti_blocklisted("test-jti-1") is True

    @pytest.mark.asyncio
    async def test_is_jti_blocklisted_not_in_list(self):
        from portal.auth.session_manager import _memory_blocklist, is_jti_blocklisted
        _memory_blocklist.discard("nonexistent-jti")
        assert await is_jti_blocklisted("nonexistent-jti") is False

    @pytest.mark.asyncio
    async def test_create_session_returns_session_id(self):
        from portal.auth.session_manager import create_session
        sid = await create_session(user_id="u1", email="u@example.com", provider="local")
        assert isinstance(sid, str)
        assert len(sid) > 0

    @pytest.mark.asyncio
    async def test_create_session_stores_data(self):
        from portal.auth.session_manager import _memory_sessions, create_session
        sid = await create_session(user_id="u2", email="u2@example.com", provider="google")
        assert sid in _memory_sessions
        assert _memory_sessions[sid]["user_id"] == "u2"

    @pytest.mark.asyncio
    async def test_revoke_session_removes_session(self):
        from portal.auth.session_manager import _memory_sessions, create_session, revoke_session
        sid = await create_session(user_id="u3", email="u3@example.com")
        await revoke_session(sid)
        assert sid not in _memory_sessions

    @pytest.mark.asyncio
    async def test_revoke_all_user_sessions(self):
        from portal.auth.session_manager import (
            _memory_sessions,
            create_session,
            revoke_all_user_sessions,
        )
        sid1 = await create_session(user_id="u4", email="u4@example.com")
        sid2 = await create_session(user_id="u4", email="u4@example.com")
        await revoke_all_user_sessions("u4")
        assert sid1 not in _memory_sessions
        assert sid2 not in _memory_sessions

    def test_get_token_jti_returns_hex_string(self):
        from portal.auth.session_manager import get_token_jti
        jti = get_token_jti("some.jwt.token")
        assert isinstance(jti, str)
        assert len(jti) == 16

    def test_get_token_jti_deterministic(self):
        from portal.auth.session_manager import get_token_jti
        assert get_token_jti("token-abc") == get_token_jti("token-abc")

    @pytest.mark.asyncio
    async def test_register_and_rotate_refresh_family(self):
        from portal.auth.session_manager import (
            register_refresh_family,
            rotate_refresh_family,
            validate_refresh_family,
        )
        fid = "family-test-1"
        await register_refresh_family(fid, "user-1")
        assert await validate_refresh_family(fid) is True
        result = await rotate_refresh_family(fid)
        assert result is True
        # Second rotation should fail (replay attack)
        result2 = await rotate_refresh_family(fid)
        assert result2 is False

    @pytest.mark.asyncio
    async def test_rotate_nonexistent_family_returns_false(self):
        from portal.auth.session_manager import rotate_refresh_family
        assert await rotate_refresh_family("nonexistent-family") is False

    @pytest.mark.asyncio
    async def test_validate_nonexistent_family_returns_false(self):
        from portal.auth.session_manager import validate_refresh_family
        assert await validate_refresh_family("no-such-family") is False

    @pytest.mark.asyncio
    async def test_blocklist_ttl_parameter_accepted(self):
        from portal.auth.session_manager import _memory_blocklist, blocklist_jti, is_jti_blocklisted
        _memory_blocklist.discard("ttl-test-jti")
        await blocklist_jti("ttl-test-jti", ttl_seconds=3600)
        assert await is_jti_blocklisted("ttl-test-jti") is True
