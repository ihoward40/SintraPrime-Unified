"""
Database Configuration Module
==============================

Manages database connection pooling and configuration for the SaaS backend.
"""

import os
import logging
from typing import Optional

try:
    from psycopg2.pool import SimpleConnectionPool, ThreadedConnectionPool
except ImportError:
    SimpleConnectionPool = None
    ThreadedConnectionPool = None

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration for SaaS backend."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "sintraprime",
        user: str = "postgres",
        password: str = "",
        min_connections: int = 2,
        max_connections: int = 20,
    ):
        """
        Initialize database configuration.
        
        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Database user
            password: Database password
            min_connections: Minimum connections in pool
            max_connections: Maximum connections in pool
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.min_connections = min_connections
        self.max_connections = max_connections
        self._pool: Optional[ThreadedConnectionPool] = None
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create configuration from environment variables."""
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "sintraprime"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            min_connections=int(os.getenv("DB_MIN_CONNECTIONS", "2")),
            max_connections=int(os.getenv("DB_MAX_CONNECTIONS", "20")),
        )
    
    def get_connection_string(self) -> str:
        """Get PostgreSQL connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    def get_pool(self) -> Optional[ThreadedConnectionPool]:
        """Get or create connection pool."""
        if self._pool is None and ThreadedConnectionPool is not None:
            try:
                self._pool = ThreadedConnectionPool(
                    self.min_connections,
                    self.max_connections,
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                )
                logger.info("Database connection pool created")
            except Exception as e:
                logger.error(f"Failed to create connection pool: {e}")
        return self._pool
    
    def close_pool(self) -> None:
        """Close connection pool."""
        if self._pool is not None:
            try:
                self._pool.closeall()
                self._pool = None
                logger.info("Database connection pool closed")
            except Exception as e:
                logger.error(f"Failed to close connection pool: {e}")


def get_database_pool() -> Optional[ThreadedConnectionPool]:
    """
    Get the database connection pool.
    
    Returns:
        ThreadedConnectionPool instance or None if psycopg2 not available
    """
    config = DatabaseConfig.from_env()
    return config.get_pool()


__all__ = [
    "DatabaseConfig",
    "get_database_pool",
    "ThreadedConnectionPool",
    "SimpleConnectionPool",
]
