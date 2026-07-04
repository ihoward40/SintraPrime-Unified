"""
Portal FastAPI application entry point with integrated trust layer.
"""
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

# Load environment variables
load_dotenv()

# Import settings and services using get_settings() instead of module-level constants
from portal.config import get_settings
from portal.middleware.cors_middleware import CORSMiddleware
from portal.middleware.rate_limiter import RateLimiterMiddleware
from portal.middleware.session_middleware import SessionMiddleware
from portal.middleware.timestamp_middleware import TimestampMiddleware
from portal.routers import admin, recovery, sso, trust_compliance, system_health
from portal.security.security_layer import SecurityLayer
from portal.sso.jwt_service import JWTTokenService
from portal.sso.session_manager import SessionConfig, SessionManager

logger = logging.getLogger(__name__)


def build_session_config() -> SessionConfig:
    """Build a boot-safe SSO session config from application settings."""
    settings = get_settings()
    jwt_secret_key = settings.JWT_SECRET_KEY

    # The shipped development JWT placeholder can be shorter than the SSO
    # config requires. Fall back to the app SECRET_KEY for local smoke tests
    # while still respecting an explicitly configured JWT_SECRET_KEY.
    if len(jwt_secret_key) < 32:
        jwt_secret_key = settings.SECRET_KEY

    return SessionConfig(
        jwt_secret_key=jwt_secret_key,
        jwt_algorithm=settings.JWT_ALGORITHM,
        jwt_expiration_seconds=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        jwt_refresh_expiration_seconds=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        redis_url=settings.REDIS_URL,
        session_store_type="memory",
        session_ttl_seconds=3600,
        refresh_token_ttl_seconds=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        issuer="sintraprime-portal",
        audience="sintraprime-api",
        require_https=settings.ENVIRONMENT == "production",
        secure_cookies=settings.ENVIRONMENT == "production",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("Portal starting up...")

    # Initialize services
    session_config = build_session_config()
    app.state.session_manager = SessionManager(session_config)
    app.state.jwt_service = JWTTokenService(session_config)

    # Initialize security layer
    settings = get_settings()
    app.state.security_layer = SecurityLayer(settings)

    logger.info("Portal startup complete")
    yield
    logger.info("Portal shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="SintraPrime Unified Portal",
        description="Unified authentication, trust compliance, and admin interface",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS Middleware (single path only - use settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"]
    )

    # Session Middleware (must come before routers that use request.session)
    app.add_middleware(SessionMiddleware)

    # Rate Limiter Middleware
    app.add_middleware(RateLimiterMiddleware)

    # Timestamp Middleware
    app.add_middleware(TimestampMiddleware)

    # Register routers
    app.include_router(sso.router, prefix="/api/v1/sso", tags=["sso"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
    app.include_router(trust_compliance.router)
    app.include_router(recovery.router)
    app.include_router(system_health.router)
    
    # Health check
    @app.get("/health")
    async def health_check():
        return {"status": "ok", "service": "portal"}

    # Root
    @app.get("/")
    async def root():
        return {"message": "SintraPrime Unified Portal", "version": "1.0.0"}

    return app


if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)

