"""
SQLAlchemy async database engine and session factory.
Supports per-tenant row-level security via PostgreSQL SET LOCAL.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


# ── Engine ────────────────────────────────────────────────────────────────────

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
    pool_recycle=3600,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Session dependency ─────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.
    Usage: db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_tenant_db(
    tenant_id: str,
    user_id: str | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a session with PostgreSQL row-level security context set.
    Must be used for all tenant-scoped queries.
    """
    async with AsyncSessionLocal() as session:
        try:
            # Set RLS context variables
            await session.execute(
                text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                {"tid": str(tenant_id)},
            )
            if user_id:
                await session.execute(
                    text("SELECT set_config('app.current_user_id', :uid, true)"),
                    {"uid": str(user_id)},
                )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def tenant_session(
    tenant_id: str,
    user_id: str | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Context manager version of tenant_db for use outside FastAPI."""
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(
                text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                {"tid": str(tenant_id)},
            )
            if user_id:
                await session.execute(
                    text("SELECT set_config('app.current_user_id', :uid, true)"),
                    {"uid": str(user_id)},
                )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Lifecycle ─────────────────────────────────────────────────────────────────

async def init_db() -> None:
    """Create all tables (for testing / first run). In prod use Alembic."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database.initialized")


async def close_db() -> None:
    """Dispose engine connections on shutdown."""
    await engine.dispose()
    logger.info("database.closed")


async def check_db_connection() -> bool:
    """Health check: returns True if DB is reachable."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("database.health_check_failed", error=str(exc))
        return False
