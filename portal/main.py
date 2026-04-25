"""
FastAPI application factory for SintraPrime Unified Client Portal.
Multi-tenant, JWT-secured, real-time document vault.
"""

import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from .config import get_settings
from .database import close_db, init_db, check_db_connection
from .middleware.audit_middleware import AuditMiddleware
from .middleware.rate_limiter import RateLimitMiddleware
from .routers import (
    admin,
    auth,
    billing,
    cases,
    clients,
    documents,
    messages,
    notifications,
    users,
)
from .websocket.connection_manager import ws_manager

logger = structlog.get_logger(__name__)
settings = get_settings()


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("portal.startup", version=settings.APP_VERSION, env=settings.ENVIRONMENT)

    # Initialise database connection pool
    await init_db()

    # Warm WebSocket manager
    await ws_manager.startup()

    logger.info("portal.ready")
    yield

    # Teardown
    logger.info("portal.shutdown")
    await ws_manager.shutdown()
    await close_db()
    logger.info("portal.stopped")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "SintraPrime Unified Client Portal — "
            "Secure multi-tenant document vault for law firms and financial advisors."
        ),
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # ── Security headers ──────────────────────────────────────────────────────
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self'; "
            "connect-src 'self' wss:;"
        )
        return response

    # ── Request ID middleware ──────────────────────────────────────────────────
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        logger.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
            request_id=request_id,
        )
        return response

    # ── CORS ───────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
        expose_headers=["X-Request-ID", "X-Response-Time", "X-Total-Count"],
    )

    # ── Rate limiting ───────────────────────────────────────────────────────────
    app.add_middleware(RateLimitMiddleware)

    # ── Audit logging ───────────────────────────────────────────────────────────
    app.add_middleware(AuditMiddleware)

    # ── Compression ─────────────────────────────────────────────────────────────
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    # ── Session (for MFA state) ──────────────────────────────────────────────────
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

    # ── Routers ──────────────────────────────────────────────────────────────────
    API_PREFIX = "/api/v1"

    app.include_router(auth.router, prefix=f"{API_PREFIX}/auth", tags=["Authentication"])
    app.include_router(users.router, prefix=f"{API_PREFIX}/users", tags=["Users"])
    app.include_router(clients.router, prefix=f"{API_PREFIX}/clients", tags=["Clients"])
    app.include_router(cases.router, prefix=f"{API_PREFIX}/cases", tags=["Cases"])
    app.include_router(documents.router, prefix=f"{API_PREFIX}/documents", tags=["Documents"])
    app.include_router(messages.router, prefix=f"{API_PREFIX}/messages", tags=["Messaging"])
    app.include_router(billing.router, prefix=f"{API_PREFIX}/billing", tags=["Billing"])
    app.include_router(notifications.router, prefix=f"{API_PREFIX}/notifications", tags=["Notifications"])
    app.include_router(admin.router, prefix=f"{API_PREFIX}/admin", tags=["Administration"])

    # ── WebSocket ─────────────────────────────────────────────────────────────────
    from .websocket.message_handler import websocket_endpoint
    app.add_api_websocket_route("/ws", websocket_endpoint)

    # ── Health endpoints ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def health_check():
        db_ok = await check_db_connection()
        return {
            "status": "healthy" if db_ok else "degraded",
            "version": settings.APP_VERSION,
            "database": "connected" if db_ok else "unavailable",
            "environment": settings.ENVIRONMENT,
        }

    @app.get("/", tags=["Root"], include_in_schema=False)
    async def root():
        return {"message": "SintraPrime Unified Portal API", "version": settings.APP_VERSION}

    # ── Global exception handlers ─────────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            error=str(exc),
            request_id=getattr(request.state, "request_id", None),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal error occurred. Please contact support."},
        )

    return app


# ── Entry point ───────────────────────────────────────────────────────────────

app = create_app()
