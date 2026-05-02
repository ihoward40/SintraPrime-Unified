"""
Security module test suite — 25+ tests.
Tests: SecretsScanner, InputValidator, AuthGuard (JWT + password hashing).
Sierra-4 Security Module
"""

import pytest
import time
import os
import tempfile
from pathlib import Path

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from security.secrets_scanner import SecretsScanner, Finding, PATTERNS
from security.input_validator import InputValidator
from security.auth_guard import AuthGuard, TokenExpiredError, TokenInvalidError, VALID_ROLES


# ═══════════════════════════════════════════════════════════════════════════════
# SecretsScanner Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecretsScanner:
    """Tests for the SecretsScanner class."""

    @pytest.fixture
    def scanner(self):
        return SecretsScanner(verbose=False)

    @pytest.fixture
    def temp_dir(self, tmp_path):
        return tmp_path

    # ─── Pattern Detection Tests ──────────────────────────────────────────────

    def _write_test_file(self, path, prefix, suffix, char, length):
        """Helper: write a synthetic test file without literal secret values."""
        # Build the value at runtime so it's not a literal in source
        val = char * length
        path.write_text(f'KEY = "{prefix}{val}{suffix}"')

    def test_detects_openai_key(self, scanner, temp_dir):
        """Should detect an OpenAI-format API key."""
        test_file = temp_dir / "config.py"
        # Construct pattern at runtime: prefix + 48 alphanumeric chars
        prefix = "sk" + chr(45)  # sk-
        self._write_test_file(test_file, prefix, "", "a", 48)
        findings = scanner.scan_directory(str(temp_dir))
        assert any(f.pattern == "openai_key" for f in findings), "OpenAI-format key not detected"

    def test_detects_stripe_live_key(self, scanner, temp_dir):
        """Should detect a Stripe live API key format."""
        test_file = temp_dir / "payment.py"
        # Build: sk_live_ + alphanumeric (not a real key)
        prefix = "sk" + chr(95) + "live" + chr(95)
        self._write_test_file(test_file, prefix, "", "a", 24)
        findings = scanner.scan_directory(str(temp_dir))
        assert any(f.pattern == "stripe_key" for f in findings), "Stripe key format not detected"

    def test_detects_aws_key(self, scanner, temp_dir):
        """Should detect an AWS access key ID format."""
        test_file = temp_dir / "aws_config.py"
        # AWS key IDs start with AKIA + 16 uppercase alphanumeric
        prefix = "AKIA"
        self._write_test_file(test_file, prefix, "", "A", 16)
        findings = scanner.scan_directory(str(temp_dir))
        assert any(f.pattern == "aws_key" for f in findings), "AWS key format not detected"

    def test_detects_github_token(self, scanner, temp_dir):
        """Should detect a GitHub PAT format."""
        test_file = temp_dir / "ci.py"
        # GitHub PAT: ghp_ + 36 alphanumeric
        prefix = "ghp" + chr(95)
        self._write_test_file(test_file, prefix, "", "x", 36)
        findings = scanner.scan_directory(str(temp_dir))
        assert any(f.pattern == "github_token" for f in findings), "GitHub token format not detected"

    def test_detects_private_key(self, scanner, temp_dir):
        """Should detect a PEM private key header."""
        test_file = temp_dir / "keys.py"
        # PEM header (split to avoid triggering GitHub scanner on this source file)
        header = "-----BEGIN RSA " + "PRIVATE KEY-----"
        test_file.write_text(f'key = """{header}\nMIIEowIBAAKCAQ...\n"""')
        findings = scanner.scan_directory(str(temp_dir))
        assert any(f.pattern == "private_key" for f in findings), "Private key header not detected"

    def test_detects_password_in_code(self, scanner, temp_dir):
        """Should detect hardcoded password assignments."""
        test_file = temp_dir / "db.py"
        # password = "longvalue" pattern
        test_file.write_text('password = "supersecretpassword123"')
        findings = scanner.scan_directory(str(temp_dir))
        assert any(f.pattern == "password_in_code" for f in findings), "Password pattern not detected"

    def test_detects_api_key_in_code(self, scanner, temp_dir):
        """Should detect hardcoded api_key assignments."""
        test_file = temp_dir / "service.py"
        test_file.write_text('api_key = "my-very-long-api-key-value-here"')
        findings = scanner.scan_directory(str(temp_dir))
        assert any(f.pattern == "api_key_in_code" for f in findings), "API key pattern not detected"

    def test_clean_code_no_findings(self, scanner, temp_dir):
        """Should return no findings for clean code using env vars."""
        test_file = temp_dir / "clean.py"
        test_file.write_text(
            'import os\n'
            'API_KEY = os.environ.get("API_KEY")\n'
            'SECRET = os.environ.get("SECRET_KEY")\n'
        )
        findings = scanner.scan_directory(str(temp_dir))
        assert len(findings) == 0, f"False positives found: {findings}"

    def test_finding_has_correct_fields(self, scanner, temp_dir):
        """Finding objects should have all required fields."""
        test_file = temp_dir / "test.py"
        # Use password pattern (less likely to trigger scanner than key patterns)
        test_file.write_text('password = "mysupersecretpassword123"')
        findings = scanner.scan_directory(str(temp_dir))
        assert len(findings) > 0
        f = findings[0]
        assert hasattr(f, 'file')
        assert hasattr(f, 'line')
        assert hasattr(f, 'pattern')
        assert hasattr(f, 'severity')
        assert f.line == 1
        assert f.severity in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}

    def test_severity_sorting(self, scanner, temp_dir):
        """Findings should be sorted CRITICAL first."""
        test_file = temp_dir / "mixed.py"
        # Use password + api_key patterns (both detectable, different severities)
        test_file.write_text(
            'api_key = "my-very-long-api-key-value-here"\n'
            'password = "anothersecretpassword456"\n'
        )
        findings = scanner.scan_directory(str(temp_dir))
        severities = [f.severity for f in findings]
        order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        for i in range(len(severities) - 1):
            assert order.get(severities[i], 4) <= order.get(severities[i+1], 4), \
                f"Findings not sorted by severity: {severities}"

    def test_skips_binary_files(self, scanner, temp_dir):
        """Should skip binary/non-text files."""
        bin_file = temp_dir / "image.jpg"
        bin_file.write_bytes(bytes(range(256)))
        findings = scanner.scan_directory(str(temp_dir))
        assert len(findings) == 0

    def test_generate_report_no_findings(self, scanner):
        """Report with no findings should indicate clean state."""
        report = scanner.generate_report([])
        assert "No secrets detected" in report

    def test_generate_report_with_findings(self, scanner, temp_dir):
        """Report with findings should include severity sections."""
        test_file = temp_dir / "bad.py"
        # Use password pattern to trigger a finding
        prefix = "sk" + chr(45)
        val = "e" * 48
        test_file.write_text(f'OPENAI_KEY = "{prefix}{val}"')
        findings = scanner.scan_directory(str(temp_dir))
        report = scanner.generate_report(findings)
        assert "CRITICAL" in report
        assert "Remediation Steps" in report

    def test_gitignore_additions(self, scanner):
        """Should return non-empty list of gitignore patterns."""
        additions = scanner.create_gitignore_additions()
        assert isinstance(additions, list)
        assert len(additions) > 5
        assert any(".env" in line for line in additions)
        assert any("*.pem" in line for line in additions)


# ═══════════════════════════════════════════════════════════════════════════════
# InputValidator Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestInputValidator:
    """Tests for the InputValidator class."""

    @pytest.fixture
    def validator(self):
        return InputValidator()

    # ─── Legal Query Tests ────────────────────────────────────────────────────

    def test_valid_legal_query(self, validator):
        """Normal legal query should pass validation."""
        valid, err = validator.validate_legal_query("What are the trust administration requirements in California?")
        assert valid is True
        assert err == ""

    def test_query_too_short(self, validator):
        """Very short query should fail."""
        valid, err = validator.validate_legal_query("a")
        assert valid is False
        assert "short" in err.lower()

    def test_query_too_long(self, validator):
        """Query over 2000 chars should fail."""
        valid, err = validator.validate_legal_query("x" * 2001)
        assert valid is False
        assert "long" in err.lower()

    def test_sql_injection_rejected(self, validator):
        """SQL injection patterns should be rejected."""
        for payload in ["'; DROP TABLE users; --", "UNION SELECT * FROM users"]:
            valid, err = validator.validate_legal_query(payload)
            assert valid is False, f"SQL injection not caught: {payload}"

    def test_xss_rejected(self, validator):
        """XSS patterns should be rejected."""
        valid, err = validator.validate_legal_query("<script>alert('xss')</script>")
        assert valid is False

    def test_empty_query_rejected(self, validator):
        """Empty/None query should fail."""
        valid, err = validator.validate_legal_query("")
        assert valid is False
        valid, err = validator.validate_legal_query(None)
        assert valid is False

    # ─── HTML Sanitization Tests ──────────────────────────────────────────────

    def test_strip_html_tags(self, validator):
        """HTML tags should be stripped."""
        result = validator.sanitize_html("<p>Hello <b>World</b></p>")
        assert "<" not in result
        assert "Hello" in result
        assert "World" in result

    def test_strip_script_tags(self, validator):
        """Script tags should be removed."""
        result = validator.sanitize_html("<script>alert('xss')</script>Safe text")
        assert "script" not in result.lower()
        assert "Safe text" in result

    def test_empty_html_input(self, validator):
        """Empty input should return empty string."""
        assert validator.sanitize_html("") == ""
        assert validator.sanitize_html(None) == ""

    # ─── SSN Validation Tests ─────────────────────────────────────────────────

    def test_valid_ssn(self, validator):
        """Standard SSN formats should pass."""
        assert validator.validate_ssn("123-45-6789") is True
        assert validator.validate_ssn("123456789") is True

    def test_invalid_ssn_all_zeros(self, validator):
        """All-zero segments should fail."""
        assert validator.validate_ssn("000-45-6789") is False
        assert validator.validate_ssn("123-00-6789") is False
        assert validator.validate_ssn("123-45-0000") is False

    def test_invalid_ssn_too_short(self, validator):
        """Wrong length SSN should fail."""
        assert validator.validate_ssn("12-345-678") is False
        assert validator.validate_ssn("1234") is False

    # ─── EIN Validation Tests ─────────────────────────────────────────────────

    def test_valid_ein(self, validator):
        """Valid EIN should pass."""
        assert validator.validate_ein("12-3456789") is True
        assert validator.validate_ein("123456789") is True

    def test_invalid_ein(self, validator):
        """Invalid EIN should fail."""
        assert validator.validate_ein("00-0000000") is False
        assert validator.validate_ein("abc-defghi") is False

    # ─── Trust Document Tests ─────────────────────────────────────────────────

    def test_valid_trust_document(self, validator):
        """A complete trust document should validate."""
        doc = {
            "trust_name": "Smith Family Living Trust",
            "grantor": {"name": "John Smith"},
            "trustee": {"name": "Jane Smith"},
            "beneficiaries": [{"name": "Alice Smith"}],
            "state": "CA",
            "trust_type": "revocable",
        }
        valid, errors = validator.validate_trust_document(doc)
        assert valid is True, f"Valid doc failed: {errors}"

    def test_trust_document_missing_fields(self, validator):
        """Missing required fields should produce errors."""
        doc = {"trust_name": "Test Trust"}
        valid, errors = validator.validate_trust_document(doc)
        assert valid is False
        assert len(errors) > 0

    def test_trust_document_invalid_state(self, validator):
        """Invalid state code should produce error."""
        doc = {
            "trust_name": "Bad State Trust",
            "grantor": {"name": "John"},
            "trustee": {"name": "Jane"},
            "beneficiaries": [{"name": "Alice"}],
            "state": "XX",
            "trust_type": "revocable",
        }
        valid, errors = validator.validate_trust_document(doc)
        assert valid is False
        assert any("state" in e.lower() for e in errors)

    def test_trust_document_empty_beneficiaries(self, validator):
        """Trust with no beneficiaries should fail."""
        doc = {
            "trust_name": "No Beneficiary Trust",
            "grantor": {"name": "John"},
            "trustee": {"name": "Jane"},
            "beneficiaries": [],
            "state": "NY",
            "trust_type": "irrevocable",
        }
        valid, errors = validator.validate_trust_document(doc)
        assert valid is False

    # ─── Rate Limiting Tests ──────────────────────────────────────────────────

    def test_rate_limit_allows_within_limit(self, validator):
        """Requests within rate limit should be allowed."""
        user_id = f"test_user_{time.time()}"
        for _ in range(5):
            result = validator.rate_limit_check(user_id, "trust_create")
            assert result is True

    def test_rate_limit_blocks_over_limit(self, validator):
        """Requests over rate limit should be blocked."""
        user_id = f"test_user_heavy_{time.time()}"
        # trust_create limit is 10/minute
        for _ in range(10):
            validator.rate_limit_check(user_id, "trust_create")
        result = validator.rate_limit_check(user_id, "trust_create")
        assert result is False


# ═══════════════════════════════════════════════════════════════════════════════
# AuthGuard Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthGuard:
    """Tests for the AuthGuard JWT implementation."""

    @pytest.fixture
    def guard(self):
        return AuthGuard(secret="test-secret-key-for-unit-tests-only")

    # ─── Token Creation Tests ─────────────────────────────────────────────────

    def test_create_token_returns_string(self, guard):
        """create_token should return a string."""
        token = guard.create_token("user123", "client")
        assert isinstance(token, str)
        assert len(token) > 50

    def test_create_token_has_three_parts(self, guard):
        """JWT should have three dot-separated parts."""
        token = guard.create_token("user123", "attorney")
        parts = token.split('.')
        assert len(parts) == 3

    def test_invalid_role_raises(self, guard):
        """Invalid role should raise ValueError."""
        with pytest.raises(ValueError):
            guard.create_token("user123", "superadmin")

    # ─── Token Verification Tests ─────────────────────────────────────────────

    def test_verify_valid_token(self, guard):
        """Valid token should decode correctly."""
        token = guard.create_token("user456", "attorney")
        payload = guard.verify_token(token)
        assert payload is not None
        assert payload["sub"] == "user456"
        assert payload["role"] == "attorney"
        assert payload["iss"] == "sintraprime"

    def test_verify_expired_token_raises(self, guard):
        """Expired token should raise TokenExpiredError."""
        token = guard.create_token("user789", "client", expires_in=-1)
        with pytest.raises(TokenExpiredError):
            guard.verify_token(token)

    def test_verify_tampered_token_raises(self, guard):
        """Tampered token should raise TokenInvalidError."""
        token = guard.create_token("user123", "client")
        tampered = token[:-10] + "tampered!!"
        with pytest.raises(TokenInvalidError):
            guard.verify_token(tampered)

    def test_verify_wrong_secret_raises(self, guard):
        """Token signed with different secret should fail."""
        other_guard = AuthGuard(secret="completely-different-secret")
        token = other_guard.create_token("user123", "client")
        with pytest.raises(TokenInvalidError):
            guard.verify_token(token)

    def test_verify_malformed_token(self, guard):
        """Malformed token should raise TokenInvalidError."""
        with pytest.raises(TokenInvalidError):
            guard.verify_token("not.a.valid.jwt.token")

    # ─── Role Tests ───────────────────────────────────────────────────────────

    def test_require_role_exact_match(self, guard):
        """User with exact role should pass role check."""
        token = guard.create_token("user1", "attorney")
        assert guard.require_role(token, "attorney") is True

    def test_require_role_higher_role_passes(self, guard):
        """Admin should pass attorney role check (hierarchy)."""
        token = guard.create_token("admin1", "admin")
        assert guard.require_role(token, "attorney") is True
        assert guard.require_role(token, "client") is True
        assert guard.require_role(token, "viewer") is True

    def test_require_role_lower_role_fails(self, guard):
        """Viewer should fail attorney role check."""
        token = guard.create_token("viewer1", "viewer")
        assert guard.require_role(token, "attorney") is False
        assert guard.require_role(token, "admin") is False

    def test_require_role_expired_token_fails(self, guard):
        """Expired token should fail role check."""
        token = guard.create_token("user1", "admin", expires_in=-1)
        assert guard.require_role(token, "viewer") is False

    # ─── Password Hashing Tests ───────────────────────────────────────────────

    def test_hash_password_returns_string(self, guard):
        """hash_password should return a string."""
        hashed = guard.hash_password("SecurePassword123!")
        assert isinstance(hashed, str)
        assert "pbkdf2:sha256" in hashed

    def test_verify_password_correct(self, guard):
        """Correct password should verify successfully."""
        password = "MySecurePassword@2024"
        hashed = guard.hash_password(password)
        assert guard.verify_password(password, hashed) is True

    def test_verify_password_wrong(self, guard):
        """Wrong password should fail verification."""
        hashed = guard.hash_password("CorrectPassword123!")
        assert guard.verify_password("WrongPassword456!", hashed) is False

    def test_hash_password_unique_salts(self, guard):
        """Same password should produce different hashes (random salt)."""
        pwd = "SamePassword123!"
        hash1 = guard.hash_password(pwd)
        hash2 = guard.hash_password(pwd)
        assert hash1 != hash2, "Hashes should differ due to random salt"
        # But both should verify correctly
        assert guard.verify_password(pwd, hash1) is True
        assert guard.verify_password(pwd, hash2) is True

    def test_hash_short_password_raises(self, guard):
        """Password under 8 chars should raise ValueError."""
        with pytest.raises(ValueError):
            guard.hash_password("short")

    def test_verify_empty_password_fails(self, guard):
        """Empty password should fail verification."""
        hashed = guard.hash_password("ValidPassword123!")
        assert guard.verify_password("", hashed) is False
        assert guard.verify_password(None, hashed) is False

    # ─── Token Utility Tests ──────────────────────────────────────────────────

    def test_get_user_id(self, guard):
        """get_user_id should extract user ID from valid token."""
        token = guard.create_token("user_abc", "client")
        assert guard.get_user_id(token) == "user_abc"

    def test_get_role(self, guard):
        """get_role should extract role from valid token."""
        token = guard.create_token("user_def", "attorney")
        assert guard.get_role(token) == "attorney"

    def test_is_expired_false_for_valid(self, guard):
        """is_expired should return False for valid token."""
        token = guard.create_token("user1", "client")
        assert guard.is_expired(token) is False

    def test_is_expired_true_for_expired(self, guard):
        """is_expired should return True for expired token."""
        token = guard.create_token("user1", "client", expires_in=-1)
        assert guard.is_expired(token) is True

    def test_token_refresh(self, guard):
        """refresh_token should produce a new valid token."""
        original = guard.create_token("user_refresh", "attorney")
        refreshed = guard.refresh_token(original)
        assert refreshed is not None
        assert refreshed != original
        payload = guard.verify_token(refreshed)
        assert payload["sub"] == "user_refresh"
        assert payload["role"] == "attorney"

    def test_all_valid_roles_work(self, guard):
        """All VALID_ROLES should create tokens without error."""
        for role in VALID_ROLES:
            token = guard.create_token(f"user_{role}", role)
            payload = guard.verify_token(token)
            assert payload["role"] == role


# ═══════════════════════════════════════════════════════════════════════════════
# Run tests directly
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
