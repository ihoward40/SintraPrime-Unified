"""
Portal FastAPI application entry point.

This module must stay import-safe: `from portal.main import create_app` is the
P0 startup smoke gate for the portal service.
"""

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware as StarletteSessionMiddleware

from portal.config import get_settings
from portal.middleware.cors_middleware import setup_cors
from portal.middleware.rate_limiter import RateLimiterMiddleware
from portal.routers import admin, sso, trust_compliance
from portal.sso.jwt_service import JWTTokenService
from portal.sso.session_config import SessionConfig
from portal.sso.session_manager import SessionManager

# Load environment variables before settings are resolved.
load_dotenv()

logger = logging.getLogger(__name__)


def build_session_config() -> SessionConfig:
    """Build a boot-safe SSO session config from application settings."""
    settings = get_settings()
    jwt_secret_key = settings.JWT_SECRET_KEY

    # The shipped development JWT placeholder can be shorter than the SSO
    # config requires. Fall back to the SSO session secret for local smoke tests
    # while still respecting an explicitly configured JWT_SECRET_KEY.
    if len(jwt_secret_key) < 32:
        jwt_secret_key = settings.SSO_SESSION_SECRET

    return SessionConfig(
        jwt_secret_key=jwt_secret_key,
        jwt_algorithm=settings.JWT_ALGORITHM,
        jwt_expiration_seconds=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        jwt_refresh_expiration_seconds=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        redis_url=settings.REDIS_URL,
        session_store_type="memory",
        session_ttl_seconds=settings.SSO_SESSION_TTL_SECONDS,
        refresh_token_ttl_seconds=settings.SSO_REFRESH_TTL_SECONDS,
        issuer=settings.SSO_ISSUER,
        audience=settings.SSO_AUDIENCE,
        require_https=settings.ENVIRONMENT == "production",
        secure_cookies=settings.ENVIRONMENT == "production",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("Portal starting up...")

    session_config = build_session_config()
    app.state.session_manager = SessionManager(session_config)
    app.state.jwt_service = JWTTokenService(session_config)

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

    setup_cors(app)

    # SSO routes use request.session for OAuth state; Starlette's session
    # middleware provides that contract without relying on missing local modules.
    app.add_middleware(
        StarletteSessionMiddleware,
        secret_key=settings.SECRET_KEY,
        https_only=settings.ENVIRONMENT == "production",
        same_site="strict",
    )

    app.add_middleware(RateLimiterMiddleware)

    # Register routers. Keep paths explicit and boot-safe.
    app.include_router(sso.router, prefix="/api/v1/sso", tags=["sso"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
    app.include_router(trust_compliance.router)

    @app.get("/health")
    async def health_check():
        return {
            "status": "ok",
            "service": "portal",
            "environment": settings.ENVIRONMENT,
        }

    @app.get("/")
    async def root():
        return {"message": "SintraPrime Unified Portal", "version": "1.0.0"}

    return app


if __name__ == "__main__":
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)
