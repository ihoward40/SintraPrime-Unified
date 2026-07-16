"""
Gate 4.6 — Test Database Isolation Guard (Fail-Closed)

Refuses to run destructive, migration, concurrency, kill-switch, or backfill
tests unless ALL of the following conditions are satisfied:

1. Database name matches an approved disposable-test pattern
2. Explicit test-environment variable (GATE4_TEST_DATABASE_URL) is set
3. Production mode is false (GATE4_TEST_MODE=true must be explicit)
4. Connection URL does not match the configured production database
5. Database contains an approved test marker table
6. The URL was explicitly authorized by the test runner (not auto-discovered)

BEHAVIOR MATRIX:
    ┌─────────────────────────────────────┬──────────────────────────────┐
    │ Configuration                        │ Behavior                     │
    ├─────────────────────────────────────┼──────────────────────────────┤
    │ Authorized disposable PG database    │ RUN — tests execute          │
    │ Unauthorized / production database   │ BLOCK — session exits failed │
    │ Missing test marker                  │ BLOCK — session exits failed │
    │ Missing explicit test flag           │ BLOCK — session exits failed │
    │ Prohibited / deceptive database name │ BLOCK — session exits failed │
    │ PG suite requested, no URL supplied │ BLOCK — session exits failed │
    │ Optional PG suite, not requested     │ SKIP — with explicit reason  │
    └─────────────────────────────────────┴──────────────────────────────┘

A dangerous database selection must produce a clear hard failure BEFORE any
fixture setup, migration, table creation, cleanup, or test data insertion.
"""

from __future__ import annotations

import os
import re
import socket
from urllib.parse import urlparse, unquote
from typing import Optional


class DatabaseIsolationError(RuntimeError):
    """Raised when a test attempts to use a non-disposable or unauthorized database.

    This error is fatal to the test session — it must not be caught and
    converted to a skip. The session must exit with a nonzero status code.
    """


# ── Approved disposable database name patterns ─────────────────────────────

DISPOSABLE_NAME_PATTERNS: list[re.Pattern] = [
    re.compile(r"^gate4_test$", re.IGNORECASE),
    re.compile(r"^gate4_clean$", re.IGNORECASE),
    re.compile(r"^gate3_bootstrap$", re.IGNORECASE),
    re.compile(r"^sintraprime_test", re.IGNORECASE),
    re.compile(r"^tmp_test_", re.IGNORECASE),
    re.compile(r"^test_", re.IGNORECASE),
    # Stress-test disposable databases
    re.compile(r"^gate4_stress_\d+$", re.IGNORECASE),
]

# Names that are NEVER allowed (production-like)
PROHIBITED_NAMES = {
    "sintraprime",
    "production",
    "prod",
    "staging",
    "stage",
}

# Environment variables
ENV_TEST_URL = "GATE4_TEST_DATABASE_URL"
ENV_TEST_MODE = "GATE4_TEST_MODE"
ENV_PRODUCTION_URL = "DATABASE_URL"  # The production connection URL
ENV_PG_SUITE_REQUESTED = "GATE4_PG_SUITE_REQUESTED"  # Set to "true" when PG tests are explicitly requested

# Test marker table name — used for error messages and display.
# The actual verification logic (read-only, schema + value check) lives in
# portal.tests.db_bootstrap (verify_test_marker / verify_test_marker_sync).
TEST_MARKER_TABLE = "__gate4_test_marker"


def _extract_db_name(url: str) -> str:
    """Extract the database name from a connection URL."""
    if not url:
        return ""
    # Handle sqlite paths
    if url.startswith("sqlite"):
        path = url.split("///")[-1] if ":///" in url else url.split(":")[-1]
        return os.path.basename(path) if path else ""
    # Handle postgresql://user:***@host:port/dbname
    parsed = urlparse(url)
    path = parsed.path or ""
    return path.lstrip("/").split("?")[0] if path else ""


def _is_disposable_name(db_name: str) -> bool:
    """Check if the database name matches an approved disposable pattern."""
    if not db_name:
        return False
    for pattern in DISPOSABLE_NAME_PATTERNS:
        if pattern.search(db_name):
            return True
    return False


def _is_prohibited_name(db_name: str) -> bool:
    """Check if the database name is explicitly prohibited."""
    if not db_name:
        return True
    normalized = db_name.lower().strip()
    for prohibited in PROHIBITED_NAMES:
        if normalized == prohibited or normalized.startswith(prohibited + "_"):
            if prohibited == "sintraprime" and "test" in normalized:
                continue
            return True
    return False


def _urls_match(url_a: str, url_b: str) -> bool:
    """Check if two database URLs point to the same database (host+port+name)."""
    if not url_a or not url_b:
        return False
    try:
        pa = urlparse(url_a)
        pb = urlparse(url_b)
        return (
            (pa.hostname or "") == (pb.hostname or "")
            and (pa.port or 5432) == (pb.port or 5432)
            and (pa.path or "") == (pb.path or "")
        )
    except Exception:
        return url_a == url_b


def validate_test_database_url(
    url: Optional[str],
    *,
    skip_marker_check: bool = False,
    skip_reachability: bool = False,
) -> str:
    """
    Validate that the given URL is safe for destructive test operations.

    Returns the validated URL if all checks pass.
    Raises DatabaseIsolationError if any check fails.

    This function is FAIL-CLOSED: any invalid configuration raises an error
    that must propagate to a test session failure, never a skip.
    """
    errors: list[str] = []

    # ── Condition 1: URL must be explicitly set ──
    if not url:
        raise DatabaseIsolationError(
            f"Test database URL is not set. "
            f"Set {ENV_TEST_URL} to a disposable test database URL."
        )

    # ── Condition 2: Explicit test-mode flag must be set ──
    test_mode = os.environ.get(ENV_TEST_MODE, "").lower()
    if test_mode not in ("true", "1", "yes"):
        errors.append(
            f"{ENV_TEST_MODE} is not set to 'true'. "
            f"Explicit test-mode confirmation required."
        )

    # ── Condition 3: Database name must match disposable pattern ──
    db_name = _extract_db_name(url)
    if not _is_disposable_name(db_name):
        errors.append(
            f"Database name '{db_name}' does not match any approved disposable "
            f"pattern. Allowed patterns: gate4_test, gate4_clean, gate4_stress_N, "
            f"sintraprime_test_*, tmp_test_*, test_*"
        )

    # ── Condition 4: Database name must not be prohibited ──
    if _is_prohibited_name(db_name):
        errors.append(
            f"Database name '{db_name}' is in the prohibited list "
            f"({PROHIBITED_NAMES}). Tests cannot run against production-like databases."
        )

    # ── Condition 5: URL must not match production DATABASE_URL ──
    prod_url = os.environ.get(ENV_PRODUCTION_URL, "")
    if prod_url and _urls_match(url, prod_url):
        errors.append(
            f"Test database URL matches the production DATABASE_URL. "
            f"Tests cannot run against the production database."
        )

    # ── Condition 6: Socket reachability (skip for unit tests) ──
    if not skip_reachability and "postgresql" in (url or ""):
        try:
            parsed = urlparse(url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 5432
            sock = socket.create_connection((host, port), timeout=3)
            sock.close()
        except (OSError, ConnectionRefusedError) as e:
            errors.append(f"Cannot reach PostgreSQL at {url}: {e}")

    # ── Condition 7: Test marker table must exist in the database (READ-ONLY) ──
    if not skip_marker_check and "postgresql" in (url or ""):
        try:
            from portal.tests.db_bootstrap import verify_test_marker_sync

            marker_ok = verify_test_marker_sync(url)

            if not marker_ok:
                errors.append(
                    f"Test marker table '{TEST_MARKER_TABLE}' not found or invalid "
                    f"in database '{db_name}'. The database may not be an authorized "
                    f"test database. Marker verification is read-only: missing table, "
                    f"wrong schema, wrong marker value, or wrong version."
                )
        except Exception as e:
            errors.append(f"Failed to verify test marker: {e}")

    if errors:
        raise DatabaseIsolationError(
            f"Database isolation check FAILED for '{url}' (db='{db_name}'):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    return url


def require_pg_url(*, skip_marker: bool = False) -> str:
    """
    Fail-closed PostgreSQL URL requirement for GATE 4 test suites.

    This is the ONLY function that test modules should use to obtain PG_URL.
    It enforces the full isolation guard and BLOCKS the session on failure.

    Behavior:
        - GATE4_TEST_DATABASE_URL set + passes guard → returns URL
        - GATE4_TEST_DATABASE_URL set + fails guard → raises DatabaseIsolationError
        - GATE4_TEST_DATABASE_URL unset + GATE4_PG_SUITE_REQUESTED=true → raises DatabaseIsolationError
        - GATE4_TEST_DATABASE_URL unset + GATE4_PG_SUITE_REQUESTED unset/false → returns "" (optional, may skip)

    The caller must NOT convert a DatabaseIsolationError into a skip.
    The caller MUST convert a "" return into an explicit pytest.skip with reason.

    Parameters
    ----------
    skip_marker : bool
        If True, skip the test marker table check. Use during module-level
        import when the DB may not be reachable. The full marker check runs
        at fixture setup time.
    """
    url = os.environ.get(ENV_TEST_URL)
    suite_requested = os.environ.get(ENV_PG_SUITE_REQUESTED, "").lower() in ("true", "1", "yes")

    if not url:
        if suite_requested:
            raise DatabaseIsolationError(
                f"{ENV_TEST_URL} is not set, but {ENV_PG_SUITE_REQUESTED}=true "
                f"indicates the PostgreSQL test suite was explicitly requested. "
                f"Set {ENV_TEST_URL} to a disposable test database URL."
            )
        # Optional PG suite not requested — return empty string
        # The caller should pytest.skip("PostgreSQL suite not requested")
        return ""

    # URL is set — validate it fail-closed
    return validate_test_database_url(url, skip_marker_check=skip_marker)


def get_validated_pg_url(skip_marker: bool = False) -> Optional[str]:
    """
    DEPRECATED: Use require_pg_url() instead.

    This function returns None on missing URL, which allows callers to skip.
    For fail-closed behavior, use require_pg_url().
    Kept for backward compatibility during migration.
    """
    url = os.environ.get(ENV_TEST_URL)
    if not url:
        return None
    return validate_test_database_url(url, skip_marker_check=skip_marker)