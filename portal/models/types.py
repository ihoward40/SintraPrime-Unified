"""Shared SQLAlchemy column types for portal models."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import String, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.sql.type_api import TypeEngine


class PortableUUID(TypeDecorator[uuid.UUID]):
    """UUID stored as native PostgreSQL UUID and SQLite-compatible text.

    Python code sees ``uuid.UUID`` consistently. Bind parameters accept either
    ``uuid.UUID`` instances or canonical UUID strings so existing callers do not
    need database-specific branches.
    """

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value: Any, dialect: Dialect) -> uuid.UUID | str | None:
        if value is None:
            return None
        parsed = value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        if dialect.name == "postgresql":
            return parsed
        return str(parsed)

    def process_result_value(self, value: Any, _dialect: Dialect) -> uuid.UUID | None:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))
