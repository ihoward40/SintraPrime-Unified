# Pytest configuration for Slack integration tests
import pytest


@pytest.fixture(autouse=True)
def clear_shared_connections():
    """Clear shared database connections before each test."""
    yield
    
    # After test, clear the shared connection pools
    try:
        from universe.integrations.slack_auth import _SHARED_DB_CONNECTIONS as auth_conns
        for conn in auth_conns.values():
            try:
                conn.close()
            except Exception:
                pass
        auth_conns.clear()
    except Exception:
        pass
    
    try:
        from universe.integrations.slack_handlers import _SHARED_DB_CONNECTIONS as handler_conns
        for conn in handler_conns.values():
            try:
                conn.close()
            except Exception:
                pass
        handler_conns.clear()
    except Exception:
        pass
