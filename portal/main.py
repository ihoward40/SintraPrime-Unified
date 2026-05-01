"""
Portal FastAPI application entry point with integrated trust layer.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Import settings and services using get_settings() instead of module-level constants
from portal.config import get_settings
from portal.sso.session_manager import SessionManager, SessionConfig
from portal.sso.jwt_service import JWTTokenService
from portal.middleware.rate_limiter import RateLimiterMiddleware
from portal.middleware.cors_middleware import CORSMiddleware
from portal.middleware.session_middleware import SessionMiddleware
from portal.middleware.timestamp_middleware import TimestampMiddleware
from portal.routers import sso, admin, webhooks
from portal.security.security_layer import SecurityLayer

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("Portal starting up...")
    
    # Initialize services
    settings = get_settings()
    jwt_service = JWTTokenService(settings.JWT_SECRET_KEY)
    
    # Setup session manager with proper config
    session_config = SessionConfig(
        jwt_secret_key=settings.JWT_SECRET_KEY,
        session_timeout_seconds=settings.SESSION_TIMEOUT_SECONDS
    )
    app.state.session_manager = SessionManager(session_config)
    app.state.jwt_service = jwt_service
    
    # Initialize security layer
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
        version="1.0.0"
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
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY
    )
    
    # Rate Limiter Middleware
    app.add_middleware(RateLimiterMiddleware)
    
    # Timestamp Middleware
    app.add_middleware(TimestampMiddleware)
    
    # Register routers
    app.include_router(sso.router, prefix="/api/v1/sso", tags=["sso"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
    app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
    
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
