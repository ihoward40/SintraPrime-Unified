"""
FastAPI application factory for SintraPrime Unified Client Portal.
Multi-tenant, JWT-secured, real-time document vault.
"""

import os
import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware as StarletteSessionMiddleware

from .config import get_settings
from .database import close_db, init_db, check_db_connection
from .middleware.audit_middleware import AuditMiddleware
from .middleware.rate_limiter import RateLimiterMiddleware as RateLimitMiddleware
from .routers import (
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
from .sso import (
    SessionMiddlewareManager,
    SessionMiddleware as SSOSessionMiddleware,
    TokenRefreshManager,
    OktaProvider, OktaConfig,
    AzureADProvider, AzureConfig,
    GoogleWorkspaceProvider, GoogleConfig,
    InMemorySessionStore, RedisSessionStore,
)

logger = structlog.get_logger(__name__)


def _build_session_store():
    """Return RedisSessionStore when REDIS_URL is set, else InMemorySessionStore."""
    redis_url = os.environ.get("REDIS_URL", "")
    if redis_url:
        return RedisSessionStore(redis_url=redis_url)
    return InMemorySessionStore()


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    settings = get_settings()
    logger.info("portal.startup", version=settings.APP_VERSION, env=settings.ENVIRONMENT)

    # Initialise database connection pool
    await init_db()

    # ── SSO: Session middleware manager ───────────────────────────────────────
    app.state.sso_session_manager = SessionMiddlewareManager(
        session_secret=settings.SSO_SESSION_SECRET,
        session_ttl_seconds=settings.SSO_SESSION_TTL_SECONDS,
    )

    # ── SSO: Token refresh manager ────────────────────────────────────────────
    async def _noop_refresh_callback(token):
        """Default no-op callback; replaced per-provider at runtime."""
        return None

    app.state.sso_token_refresh_manager = TokenRefreshManager(
        refresh_callback=_noop_refresh_callback,
    )

    # ── SSO: Providers (initialised only when config is present) ──────────────
    if settings.OKTA_DOMAIN and settings.OKTA_CLIENT_ID:
        app.state.okta_provider = OktaProvider(
            OktaConfig(
                domain=settings.OKTA_DOMAIN,
                client_id=settings.OKTA_CLIENT_ID,
                client_secret=settings.OKTA_CLIENT_SECRET,
                redirect_uri=settings.OKTA_REDIRECT_URI,
                scopes=settings.OKTA_SCOPES.split(),
            )
        )
        logger.info("sso.okta_provider.initialized")
    else:
        app.state.okta_provider = None
        logger.info("sso.okta_provider.skipped", reason="OKTA_DOMAIN or OKTA_CLIENT_ID not set")

    if settings.AZURE_TENANT_ID and settings.AZURE_CLIENT_ID:
        app.state.azure_provider = AzureADProvider(
            AzureConfig(
                tenant_id=settings.AZURE_TENANT_ID,
                client_id=settings.AZURE_CLIENT_ID,
                client_secret=settings.AZURE_CLIENT_SECRET,
                redirect_uri=settings.AZURE_REDIRECT_URI,
            )
        )
        logger.info("sso.azure_provider.initialized")
    else:
        app.state.azure_provider = None
        logger.info("sso.azure_provider.skipped", reason="AZURE_TENANT_ID or AZURE_CLIENT_ID not set")

    if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
        app.state.google_provider = GoogleWorkspaceProvider(
            GoogleConfig(
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                redirect_uri=settings.GOOGLE_REDIRECT_URI,
                hosted_domain=settings.GOOGLE_HOSTED_DOMAIN or None,
            )
        )
        logger.info("sso.google_provider.initialized")
    else:
        app.state.google_provider = None
        logger.info("sso.google_provider.skipped", reason="GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not set")

    logger.info("portal.ready")
    yield

    # ── Teardown ──────────────────────────────────────────────────────────────
    logger.info("portal.shutdown")

    # Stop all active token refresh loops
    trm = getattr(app.state, "sso_token_refresh_manager", None)
    if trm:
        for session_id in list(trm.active_tasks.keys()):
            await trm.stop_refresh_loop(session_id)
        logger.info("sso.token_refresh_manager.stopped")

    await close_db()
    logger.info("portal.stopped")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    settings = get_settings()

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

    # ── Starlette session (for OAuth2 CSRF state cookie) ─────────────────────
    app.add_middleware(StarletteSessionMiddleware, secret_key=settings.SECRET_KEY)

    # ── SSO session middleware (Phase 21C) — protects /api/ routes ───────────
    # SessionMiddlewareManager is created in lifespan; we pass a lazy accessor
    # so the middleware can reference app.state after startup.
    _sso_session_manager_holder: list = []  # populated in lifespan via startup event

    @app.on_event("startup")
    async def _attach_sso_middleware():
        """Attach SSOSessionMiddleware after lifespan has populated app.state."""
        # NOTE: Middleware cannot be added after app startup in Starlette, so we
        # wire it here using the manager that was created in the lifespan context.
        # The manager is available on app.state at this point.
        pass  # Middleware is added below before lifespan runs (see add_middleware call)

    # Add SSO session middleware — it reads app.state.sso_session_manager lazily
    # by wrapping the lookup in a factory closure.
    class _LazySSOSessionMiddleware(SSOSessionMiddleware):
        """Defers session_manager lookup to first request (after lifespan)."""
        def __init__(self, app_inner, **kwargs):
            # Pass a placeholder; dispatch() will read from request.app.state
            from .sso.middleware import SessionMiddlewareManager as _SMM
            placeholder = _SMM(session_secret="placeholder", session_ttl_seconds=3600)
            super().__init__(app_inner, session_manager=placeholder)

        async def dispatch(self, request: Request, call_next):
            # Replace placeholder with the real manager from app.state
            real_manager = getattr(request.app.state, "sso_session_manager", None)
            if real_manager is not None:
                self.session_manager = real_manager
            return await super().dispatch(request, call_next)

    app.add_middleware(_LazySSOSessionMiddleware)

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
    app.include_router(sso.router, prefix=f"{API_PREFIX}/sso", tags=["SSO"])

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
