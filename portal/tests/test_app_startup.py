"""Smoke test to verify app boots without import errors."""

import pytest

from portal.config import get_settings
from portal.main import create_app


def test_app_creation():
    """Test that app can be created without errors."""
    app = create_app()
    assert app is not None
    assert app.title == "SintraPrime Unified Portal"


def test_settings_loads():
    """Test that settings load correctly."""
    settings = get_settings()
    assert settings is not None
    assert hasattr(settings, "DATABASE_URL")
    assert hasattr(settings, "JWT_SECRET_KEY")


def test_no_import_errors():
    """Test that all imports resolve without errors."""
    try:
        from portal.config import get_settings
        from portal.main import create_app
        from portal.middleware.cors_middleware import CORSMiddleware
        from portal.sso.jwt_service import JWTTokenService
        from portal.sso.session_manager import SessionManager
    except ImportError as e:
        pytest.fail(f"Import error: {e}")



def test_create_app_does_not_use_in_memory_durable_store():
    """The canonical durable engine must use a persistent path in production."""
    from portal.services.orchestration_runtime import _durable_db_path
    path = _durable_db_path()
    assert path != ":memory:"
    assert path.endswith(".db")
