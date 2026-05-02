"""
CORS middleware for portal.
 """
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware as FastAPICORSMiddleware

from portal.config import get_settings

settings = get_settings()

# Alias for backward compatibility
CORSMiddleware = FastAPICORSMiddleware


def setup_cors(app: FastAPI) -> None:
    """Configure CORS based on environment settings."""
    allowed_origins = settings.CORS_ORIGINS

    # Multi-tenant: also allow *.sintraprime.ai subdomains
    if settings.ENVIRONMENT == "production":
        # Use a custom allow_origin_regex instead of static list
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r"https://.*\.sintraprime\.ai",
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "X-Tenant-ID",
                "X-Request-ID",
                "Accept",
                "Origin",
            ],
            expose_headers=[
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset",
                "X-Request-ID",
            ],
            max_age=600,
        )
    else:
        # Development/testing: allow configured origins
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins or ["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
