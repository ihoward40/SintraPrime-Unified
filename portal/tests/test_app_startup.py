"""Smoke test to verify app boots without import errors."""
import pytest
ifrom portal.main import create_app
from portal.config import get_settings


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
        from portal.main import create_app
        from portal.config import get_settings
        from portal.sso.session_manager import SessionManager
        from portal.sso.jwt_service import JWTTokenService
        from portal.middleware.cors_middleware import CORSMiddleware
    except ImportError as e:
        pytest.fail(f"Import error: {e}")
