"""
Application configuration via pydantic-settings.
All settings read from environment variables with sensible defaults.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import AnyHttpUrl, EmailStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ─────────────────────────────────────────────────────────────
    APP_NAME: str = "SintraPrime Portal"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"  # development | staging | production
    BASE_URL: str = "https://portal.sintraprime.ai"
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION-USE-256-BIT-RANDOM-KEY"

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://portal:portal@localhost:5432/sintra_portal"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_ECHO: bool = False

    # ── JWT ──────────────────────────────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    JWT_SECRET_KEY: str = "CHANGE-ME-JWT-SECRET-256-BIT"
    JWT_REFRESH_SECRET_KEY: str = "CHANGE-ME-REFRESH-SECRET-256-BIT"

    # ── MinIO / S3 ───────────────────────────────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "sintra-documents"
    MINIO_SECURE: bool = False  # True in production

    # ── Encryption ───────────────────────────────────────────────────────
    ENCRYPTION_KEY: str = "CHANGE-ME-AES-256-KEY-32-BYTES!!"  # Must be 32 bytes
    ENCRYPTION_SALT: str = "CHANGE-ME-ENCRYPTION-SALT"

    # ── Email ────────────────────────────────────────────────────────────
    SMTP_HOST: str = "smtp.sendgrid.net"
    SMTP_PORT: int = 587
    SMTP_USER: str = "apikey"
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@sintraprime.ai"
    SMTP_FROM_NAME: str = "SintraPrime Portal"
    SMTP_TLS: bool = True

    # ── Twilio SMS ───────────────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    # ── Stripe ───────────────────────────────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""

    # ── ClamAV virus scanning ────────────────────────────────────────────
    CLAMAV_HOST: str = "localhost"
    CLAMAV_PORT: int = 3310
    CLAMAV_ENABLED: bool = True

    # ── Redis (rate limiting + sessions) ────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_SESSION_DB: int = 1

    # ── Rate Limiting ────────────────────────────────────────────────────
    RATE_LIMIT_DEFAULT: int = 100       # requests per minute per user
    RATE_LIMIT_AUTH: int = 10           # requests per minute on auth endpoints
    RATE_LIMIT_UPLOAD: int = 20         # file uploads per minute

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = [
        "https://portal.sintraprime.ai",
        "https://*.sintraprime.ai",
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # ── File Storage ─────────────────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 500
    ALLOWED_FILE_TYPES: List[str] = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/plain",
        "text/csv",
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/tiff",
        "video/mp4",
        "video/webm",
        "audio/mpeg",
        "audio/wav",
        "application/zip",
        "application/x-zip-compressed",
    ]

    # ── Audit ────────────────────────────────────────────────────────────
    AUDIT_RETENTION_YEARS: int = 7
    AUDIT_HASH_ALGORITHM: str = "sha256"

    # ── OCR ──────────────────────────────────────────────────────────────
    OCR_ENABLED: bool = True
    OCR_LANGUAGE: str = "eng"

    # ── Notifications ────────────────────────────────────────────────────
    NOTIFICATION_EMAIL_ENABLED: bool = True
    NOTIFICATION_SMS_ENABLED: bool = False
    NOTIFICATION_PUSH_ENABLED: bool = False

    # ── Tenant defaults ──────────────────────────────────────────────────
    DEFAULT_STORAGE_QUOTA_GB: int = 100
    DEFAULT_USER_QUOTA: int = 50

    # ── Share links ──────────────────────────────────────────────────────
    SHARE_LINK_MAX_EXPIRY_DAYS: int = 90
    SHARE_LINK_BASE_URL: str = "https://share.sintraprime.ai"

    @field_validator("ENCRYPTION_KEY")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        if len(v.encode()) < 32:
            raise ValueError("ENCRYPTION_KEY must be at least 32 bytes")
        return v

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def encryption_key_bytes(self) -> bytes:
        return self.ENCRYPTION_KEY.encode()[:32]


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance — call this everywhere instead of Settings()."""
    return Settings()
