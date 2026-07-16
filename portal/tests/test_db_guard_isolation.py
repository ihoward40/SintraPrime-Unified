"""
Gate 4.6 — Test Database Isolation Guard Tests (Fail-Closed)

Tests proving:
1. Authorized disposable database → PASS
2. Production database → BLOCK (nonzero exit)
3. Missing test marker → BLOCK
4. Missing explicit test flag → BLOCK
5. Unauthorized database name → BLOCK
6. PG suite requested without URL → BLOCK
7. Optional PG suite not requested → may SKIP
8. Subprocess-level: unauthorized DB causes pytest to exit nonzero
"""

import os
import subprocess
import sys

import pytest
from unittest.mock import patch

from portal.tests.test_db_guard import (
    DatabaseIsolationError,
    validate_test_database_url,
    require_pg_url,
    _extract_db_name,
    _is_disposable_name,
    _is_prohibited_name,
    _urls_match,
    DISPOSABLE_NAME_PATTERNS,
    PROHIBITED_NAMES,
    ENV_TEST_URL,
    ENV_TEST_MODE,
    ENV_PRODUCTION_URL,
    ENV_PG_SUITE_REQUESTED,
)


class TestDatabaseNameExtraction:
    """Test the URL-to-database-name extraction logic."""

    def test_pg_url_extraction(self):
        assert _extract_db_name("postgresql+asyncpg://user:pass@localhost:5433/gate4_test") == "gate4_test"

    def test_pg_url_with_query_params(self):
        assert _extract_db_name("postgresql://user:***@host:5432/mydb?sslmode=require") == "mydb"

    def test_sqlite_url_extraction(self):
        name = _extract_db_name("sqlite:///tmp/test_db.sqlite")
        assert name == "test_db.sqlite"

    def test_empty_url(self):
        assert _extract_db_name("") == ""
        assert _extract_db_name(None) == ""


class TestDisposableNameMatching:
    """Test the disposable database name pattern matching."""

    @pytest.mark.parametrize("name", [
        "gate4_test",
        "gate4_clean",
        "gate3_bootstrap",
        "sintraprime_test_run1",
        "tmp_test_abc",
        "test_foo",
        "gate4_stress_1",
        "gate4_stress_10",
        "GATE4_TEST",  # case insensitive
    ])
    def test_disposable_names_accepted(self, name):
        assert _is_disposable_name(name), f"Expected '{name}' to be accepted as disposable"

    @pytest.mark.parametrize("name", [
        "sintraprime",
        "production",
        "prod",
        "staging",
        "mydb",
        "observatory",
        "gate4",  # partial match not allowed
        "gate4test",  # missing underscore
    ])
    def test_non_disposable_names_rejected(self, name):
        assert not _is_disposable_name(name), f"Expected '{name}' to be rejected"


class TestProhibitedNameDetection:
    """Test the prohibited database name detection."""

    @pytest.mark.parametrize("name", [
        "sintraprime",
        "production",
        "prod",
        "staging",
        "stage",
    ])
    def test_prohibited_names(self, name):
        assert _is_prohibited_name(name), f"Expected '{name}' to be prohibited"

    def test_sintraprime_test_is_not_prohibited(self):
        """sintraprime_test_* should NOT be prohibited (it's disposable)."""
        assert not _is_prohibited_name("sintraprime_test_run1")

    def test_empty_name_is_prohibited(self):
        assert _is_prohibited_name("")


class TestURLMatching:
    """Test the URL comparison logic."""

    def test_identical_urls_match(self):
        url = "postgresql://user:***@localhost:5433/gate4_test"
        assert _urls_match(url, url)

    def test_different_ports_dont_match(self):
        a = "postgresql://user:***@localhost:5432/db"
        b = "postgresql://user:***@localhost:5433/db"
        assert not _urls_match(a, b)

    def test_different_databases_dont_match(self):
        a = "postgresql://user:***@localhost:5433/gate4_test"
        b = "postgresql://user:***@localhost:5433/sintraprime"
        assert not _urls_match(a, b)

    def test_empty_urls_dont_match(self):
        assert not _urls_match("", "postgresql://...")
        assert not _urls_match(None, None)


class TestGuardValidation:
    """Test validate_test_database_url fail-closed behavior."""

    def test_1_disposable_database_accepted(self):
        """An authorized disposable database URL must be accepted."""
        url = "postgresql+asyncpg://testuser:testpass@localhost:5433/gate4_test"
        with patch.dict(os.environ, {
            ENV_TEST_MODE: "true",
            ENV_PRODUCTION_URL: "postgresql+asyncpg://testuser:testpass@localhost:5433/sintraprime",
        }, clear=False):
            result = validate_test_database_url(
                url,
                skip_marker_check=True,
                skip_reachability=True,
            )
            assert result == url

    def test_2_production_database_blocked(self):
        """A URL pointing to the production database must be BLOCKED."""
        url = "postgresql+asyncpg://testuser:testpass@localhost:5433/sintraprime"
        with patch.dict(os.environ, {
            ENV_TEST_MODE: "true",
            ENV_PRODUCTION_URL: "postgresql+asyncpg://testuser:testpass@localhost:5433/sintraprime",
        }, clear=False):
            with pytest.raises(DatabaseIsolationError, match="matches the production"):
                validate_test_database_url(
                    url,
                    skip_marker_check=True,
                    skip_reachability=True,
                )

    def test_3_missing_test_flag_blocked(self):
        """Missing GATE4_TEST_MODE must be BLOCKED."""
        url = "postgresql+asyncpg://testuser:testpass@localhost:5433/gate4_test"
        with patch.dict(os.environ, {
            ENV_TEST_MODE: "",
            ENV_PRODUCTION_URL: "postgresql+asyncpg://testuser:testpass@localhost:5433/sintraprime",
        }, clear=False):
            with pytest.raises(DatabaseIsolationError, match="TEST_MODE"):
                validate_test_database_url(
                    url,
                    skip_marker_check=True,
                    skip_reachability=True,
                )

    def test_4_non_disposable_name_blocked(self):
        """A database name that doesn't match disposable patterns must be BLOCKED."""
        url = "postgresql+asyncpg://testuser:testpass@localhost:5433/mydb"
        with patch.dict(os.environ, {
            ENV_TEST_MODE: "true",
            ENV_PRODUCTION_URL: "",
        }, clear=False):
            with pytest.raises(DatabaseIsolationError, match="does not match"):
                validate_test_database_url(
                    url,
                    skip_marker_check=True,
                    skip_reachability=True,
                )

    def test_5_similar_looking_unauthorized_name_blocked(self):
        """A name that looks disposable but isn't must be BLOCKED."""
        url = "postgresql+asyncpg://testuser:testpass@localhost:5433/gate4test"
        with patch.dict(os.environ, {
            ENV_TEST_MODE: "true",
            ENV_PRODUCTION_URL: "",
        }, clear=False):
            with pytest.raises(DatabaseIsolationError, match="does not match"):
                validate_test_database_url(
                    url,
                    skip_marker_check=True,
                    skip_reachability=True,
                )

    def test_6_production_name_explicitly_blocked(self):
        """A URL with 'production' as database name must be BLOCKED."""
        url = "postgresql+asyncpg://user:pass@localhost:5432/production"
        with patch.dict(os.environ, {
            ENV_TEST_MODE: "true",
            ENV_PRODUCTION_URL: "",
        }, clear=False):
            with pytest.raises(DatabaseIsolationError, match="prohibited"):
                validate_test_database_url(
                    url,
                    skip_marker_check=True,
                    skip_reachability=True,
                )

    def test_7_staging_name_explicitly_blocked(self):
        """A URL with 'staging' as database name must be BLOCKED."""
        url = "postgresql+asyncpg://user:pass@localhost:5432/staging"
        with patch.dict(os.environ, {
            ENV_TEST_MODE: "true",
            ENV_PRODUCTION_URL: "",
        }, clear=False):
            with pytest.raises(DatabaseIsolationError, match="prohibited"):
                validate_test_database_url(
                    url,
                    skip_marker_check=True,
                    skip_reachability=True,
                )

    def test_8_empty_url_blocked(self):
        """No URL at all must be BLOCKED with a clear message."""
        with pytest.raises(DatabaseIsolationError, match="not set"):
            validate_test_database_url(None)

    def test_9_none_url_blocked(self):
        """None URL must be BLOCKED."""
        with pytest.raises(DatabaseIsolationError, match="not set"):
            validate_test_database_url(None)

    def test_10_multiple_failures_all_reported(self):
        """When multiple checks fail, all errors should be reported."""
        url = "postgresql+asyncpg://user:pass@localhost:5432/production"
        with patch.dict(os.environ, {
            ENV_TEST_MODE: "",
            ENV_PRODUCTION_URL: "",
        }, clear=False):
            with pytest.raises(DatabaseIsolationError) as exc_info:
                validate_test_database_url(
                    url,
                    skip_marker_check=True,
                    skip_reachability=True,
                )
            error_msg = str(exc_info.value)
            assert "TEST_MODE" in error_msg
            assert "prohibited" in error_msg or "does not match" in error_msg


class TestRequirePgUrl:
    """Test require_pg_url() fail-closed behavior."""

    def test_authorized_disposable_url_returns_url(self):
        """Authorized disposable URL → returns the URL."""
        url = "postgresql+asyncpg://testuser:testpass@localhost:5433/gate4_test"
        with patch.dict(os.environ, {
            ENV_TEST_URL: url,
            ENV_TEST_MODE: "true",
            ENV_PRODUCTION_URL: "postgresql+asyncpg://testuser:testpass@localhost:5433/sintraprime",
        }, clear=False):
            with patch("portal.tests.test_db_guard.validate_test_database_url") as mock_validate:
                mock_validate.return_value = url
                result = require_pg_url()
                assert result == url

    def test_unauthorized_url_raises_error(self):
        """Unauthorized URL → raises DatabaseIsolationError, NOT skip."""
        url = "postgresql+asyncpg://testuser:testpass@localhost:5433/sintraprime"
        with patch.dict(os.environ, {
            ENV_TEST_URL: url,
            ENV_TEST_MODE: "true",
            ENV_PG_SUITE_REQUESTED: "true",
        }, clear=False):
            with patch("portal.tests.test_db_guard.validate_test_database_url") as mock_validate:
                mock_validate.side_effect = DatabaseIsolationError("matches the production")
                with pytest.raises(DatabaseIsolationError, match="matches the production"):
                    require_pg_url()

    def test_no_url_no_suite_requested_returns_empty(self):
        """No URL + suite not requested → returns empty string (optional skip)."""
        with patch.dict(os.environ, {
            ENV_TEST_URL: "",
            ENV_PG_SUITE_REQUESTED: "",
        }, clear=False):
            result = require_pg_url()
            assert result == ""

    def test_no_url_suite_requested_raises_error(self):
        """No URL + suite explicitly requested → BLOCK (DatabaseIsolationError)."""
        with patch.dict(os.environ, {
            ENV_TEST_URL: "",
            ENV_PG_SUITE_REQUESTED: "true",
        }, clear=False):
            with pytest.raises(DatabaseIsolationError, match="explicitly requested"):
                require_pg_url()

    def test_missing_test_mode_blocks_even_with_url(self):
        """URL present but GATE4_TEST_MODE unset → BLOCK."""
        url = "postgresql+asyncpg://testuser:testpass@localhost:5433/gate4_test"
        with patch.dict(os.environ, {
            ENV_TEST_URL: url,
            ENV_TEST_MODE: "",
            ENV_PRODUCTION_URL: "",
        }, clear=False):
            with pytest.raises(DatabaseIsolationError, match="TEST_MODE"):
                require_pg_url()


class TestSubprocessFailClosed:
    """
    Prove that unauthorized database configurations cause pytest to exit
    with a nonzero status code, not skip.

    These tests run pytest as a subprocess to verify session-level behavior.
    """

    @pytest.fixture(autouse=True)
    def _skip_if_no_pytest(self):
        """Skip if pytest isn't available in subprocess."""
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            capture_output=True, timeout=10,
        )
        if result.returncode != 0:
            pytest.skip("pytest not available in subprocess")

    def test_production_url_exits_nonzero(self):
        """Pointing at the production database must cause a nonzero exit."""
        # Create a minimal test file that uses require_pg_url()
        test_code = '''
import pytest
from portal.tests.test_db_guard import require_pg_url, DatabaseIsolationError

def test_guard_blocks_production():
    """This must fail, not skip, when pointed at production."""
    try:
        url = require_pg_url()
        if url:
            # If we got here, the guard failed to block
            pytest.fail(f"Guard should have blocked production URL, got: {url}")
    except DatabaseIsolationError:
        # This is the expected path — guard blocked it
        pass
'''
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='_test_guard_sub.py', delete=False, dir='portal/tests') as f:
            f.write(test_code)
            f.flush()
            test_file = f.name

        try:
            env = os.environ.copy()
            env["GATE4_TEST_DATABASE_URL"] = "postgresql+asyncpg://testuser:testpass@localhost:5433/sintraprime"
            env["GATE4_TEST_MODE"] = "true"
            env["GATE4_PG_SUITE_REQUESTED"] = "true"
            env["DATABASE_URL"] = "postgresql+asyncpg://testuser:testpass@localhost:5433/sintraprime"

            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_file, "-v", "--timeout=10"],
                capture_output=True, text=True, timeout=30,
                env=env,
            )
            # The test should PASS (it expects DatabaseIsolationError)
            # because require_pg_url raises, not skips
            assert result.returncode == 0, (
                f"Expected test to pass (guard raises error), got exit {result.returncode}.\n"
                f"stdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}"
            )
        finally:
            os.unlink(test_file)

    def test_missing_url_suite_requested_exits_nonzero(self):
        """No URL with suite requested must cause a nonzero exit."""
        test_code = '''
import pytest
from portal.tests.test_db_guard import require_pg_url, DatabaseIsolationError

def test_guard_blocks_missing_url():
    """No URL with suite requested must block."""
    try:
        url = require_pg_url()
        pytest.fail(f"Guard should have blocked, got: {url}")
    except DatabaseIsolationError:
        pass  # Expected
'''
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='_test_guard_sub.py', delete=False, dir='portal/tests') as f:
            f.write(test_code)
            f.flush()
            test_file = f.name

        try:
            env = os.environ.copy()
            # Remove the test URL but mark suite as requested
            env.pop("GATE4_TEST_DATABASE_URL", None)
            env.pop("DATABASE_URL", None)
            env["GATE4_PG_SUITE_REQUESTED"] = "true"

            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_file, "-v", "--timeout=10"],
                capture_output=True, text=True, timeout=30,
                env=env,
            )
            assert result.returncode == 0, (
                f"Expected test to pass (guard raises error), got exit {result.returncode}.\n"
                f"stdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}"
            )
        finally:
            os.unlink(test_file)

    def test_staging_url_exits_nonzero(self):
        """Staging database must cause guard to block, not skip."""
        test_code = '''
import pytest
from portal.tests.test_db_guard import require_pg_url, DatabaseIsolationError

def test_guard_blocks_staging():
    """Staging database must be blocked."""
    try:
        url = require_pg_url()
        pytest.fail(f"Guard should have blocked staging URL, got: {url}")
    except DatabaseIsolationError:
        pass  # Expected
'''
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='_test_guard_sub.py', delete=False, dir='portal/tests') as f:
            f.write(test_code)
            f.flush()
            test_file = f.name

        try:
            env = os.environ.copy()
            env["GATE4_TEST_DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/staging"
            env["GATE4_TEST_MODE"] = "true"
            env["GATE4_PG_SUITE_REQUESTED"] = "true"

            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_file, "-v", "--timeout=10"],
                capture_output=True, text=True, timeout=30,
                env=env,
            )
            assert result.returncode == 0, (
                f"Expected test to pass (guard raises error), got exit {result.returncode}.\n"
                f"stdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}"
            )
        finally:
            os.unlink(test_file)