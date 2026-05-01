"""
FastAPI application factory for SintraPrime Unified Client Portal.

Multi-tenant, JWT-secured, real-time case management with:
- SAML/OAuth 2.0 SSO (Okta, Azure AD, Google)
- Role-based access control (RBAC)
- Async WebSocket support for live collaboration
- Stripe billing integration
"""

import logging
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from portal.config import (
    ENVIRONMENT,
    POSTGRES_URL,
    REDIS_URL,
    STRIPE_PUBLIC_KEY,
    STRIPE_SECRET_KEY,
    JWT_SECRET,
    CORS_ORIGINS,
)
from portal.database import Base
from portal.middleware.audit_middleware import AuditMiddleware
from portal.middleware.auth_middleware import AuthMiddleware
from portal.middleware.cors_middleware import setup_cors
from portal.middleware.rate_limiter import RateLimiter
from portal.routers import (
    admin,
    auth,
    billing,
    cases,
    clients,
    documents,
    messages,
    notifications,
    sso,
    users,
)
from portal.sso.session_store import SessionStore, SessionManager
from portal.sso.jwt_service import JWTService

logger = logging.getLogger(__name__)

# Global instances
engine = None
Session = None
session_store = None
session_manager = None
jwt_service = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan context for startup/shutdown."""
    global engine, Session, session_store, session_manager, jwt_service

    # Startup
    try:
        logger.info(f"Starting SintraPrime Portal (env={ENVIRONMENT})")
        
        # Database
        engine = create_async_engine(POSTGRES_URL, echo=ENVIRONMENT == "development")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        logger.info("Database initialized")

        # SSO
        session_store = SessionStore(redis_url=REDIS_URL, ttl_seconds=3600)
        await session_store.connect()
        session_manager = SessionManager(session_store, JWT_SECRET)
        jwt_service = JWTService(JWT_SECRET)
        logger.info("SSO services initialized")

    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise

    yield

    # Shutdown
    try:
        logger.info("Shutting down SintraPrime Portal")
        if session_store:
            await session_store.disconnect()
        if engine:
            await engine.dispose()
        logger.info("Shutdown complete")
    except Exception as e:
        logger.error(f"Shutdown error: {e}", exc_info=True)


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="SintraPrime Unified Client Portal",
        description="Multi-tenant case management with SSO, RBAC, and real-time collaboration",
        version="2.0.0",
        docs_url="/docs" if ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # CORS
    setup_cors(app, origins=CORS_ORIGINS)

    # Middleware (order matters)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(AuthMiddleware, jwt_service=jwt_service)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimiter, requests_per_minute=60)

    # Exception handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # Health check
    @app.get("/health")
    async def health_check():
        return {"status": "ok", "environment": ENVIRONMENT}

    # Root
    @app.get("/")
    async def root():
        return {"message": "SintraPrime Unified Client Portal", "version": "2.0.0"}

    # Routes
    app.include_router(sso.router, prefix="/auth", tags=["SSO"])
    app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
    app.include_router(users.router, prefix="/users", tags=["Users"])
    app.include_router(clients.router, prefix="/clients", tags=["Clients"])
    app.include_router(cases.router, prefix="/cases", tags=["Cases"])
    app.include_router(documents.router, prefix="/documents", tags=["Documents"])
    app.include_router(messages.router, prefix="/messages", tags=["Messages"])
    app.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
    app.include_router(billing.router, prefix="/billing", tags=["Billing"])
    app.include_router(admin.router, prefix="/admin", tags=["Admin"])

    return app


# Application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
