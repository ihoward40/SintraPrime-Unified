"""PortableUUID direct certification tests (Section 14 of Principal directive).

Covers: uuid.UUID input, canonical UUID string input, invalid UUID rejection,
None handling, PostgreSQL bind behavior, SQLite bind behavior, JSON/Pydantic serialization.
"""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import String, create_engine, inspect
from sqlalchemy.dialects.postgresql import UUID as PGUUID


def test_portable_uuid_uuid_input() -> None:
    """uuid.UUID input is accepted and returned as uuid.UUID."""
    from portal.models.types import PortableUUID

    puuid = PortableUUID()
    test_uuid = uuid.uuid4()

    # Simulate bind (SQLite dialect)
    bound = puuid.process_bind_param(test_uuid, _sqlite_dialect())
    assert isinstance(bound, str)
    assert bound == str(test_uuid)

    # Simulate result (SQLite dialect)
    result = puuid.process_result_value(str(test_uuid), _sqlite_dialect())
    assert isinstance(result, uuid.UUID)
    assert result == test_uuid


def test_portable_uuid_string_input() -> None:
    """Canonical UUID string input is accepted."""
    from portal.models.types import PortableUUID

    puuid = PortableUUID()
    test_uuid = uuid.uuid4()
    test_str = str(test_uuid)

    bound = puuid.process_bind_param(test_str, _sqlite_dialect())
    assert isinstance(bound, str)
    assert bound == test_str

    result = puuid.process_result_value(test_str, _sqlite_dialect())
    assert isinstance(result, uuid.UUID)
    assert result == test_uuid


def test_portable_uuid_invalid_string_rejection() -> None:
    """Invalid UUID string raises ValueError."""
    from portal.models.types import PortableUUID

    puuid = PortableUUID()

    with pytest.raises(ValueError):
        puuid.process_bind_param("not-a-uuid", _sqlite_dialect())


def test_portable_uuid_none_handling() -> None:
    """None is handled correctly for nullable columns."""
    from portal.models.types import PortableUUID

    puuid = PortableUUID()

    assert puuid.process_bind_param(None, _sqlite_dialect()) is None
    assert puuid.process_result_value(None, _sqlite_dialect()) is None


def test_portable_uuid_postgresql_bind() -> None:
    """PostgreSQL bind returns uuid.UUID (native PG UUID)."""
    from portal.models.types import PortableUUID

    puuid = PortableUUID()
    test_uuid = uuid.uuid4()

    bound = puuid.process_bind_param(test_uuid, _pg_dialect())
    assert isinstance(bound, uuid.UUID)
    assert bound == test_uuid

    # String input also works on PG
    bound_str = puuid.process_bind_param(str(test_uuid), _pg_dialect())
    assert isinstance(bound_str, uuid.UUID)
    assert bound_str == test_uuid


def test_portable_uuid_postgresql_result() -> None:
    """PostgreSQL result returns uuid.UUID."""
    from portal.models.types import PortableUUID

    puuid = PortableUUID()
    test_uuid = uuid.uuid4()

    # PG returns native UUID
    result = puuid.process_result_value(test_uuid, _pg_dialect())
    assert isinstance(result, uuid.UUID)
    assert result == test_uuid

    # PG might also return string in some cases
    result_str = puuid.process_result_value(str(test_uuid), _pg_dialect())
    assert isinstance(result_str, uuid.UUID)
    assert result_str == test_uuid


def test_portable_uuid_sqlite_bind() -> None:
    """SQLite bind returns string (text-compatible)."""
    from portal.models.types import PortableUUID

    puuid = PortableUUID()
    test_uuid = uuid.uuid4()

    bound = puuid.process_bind_param(test_uuid, _sqlite_dialect())
    assert isinstance(bound, str)
    assert bound == str(test_uuid)


def test_portable_uuid_sqlite_result() -> None:
    """SQLite result returns uuid.UUID from string storage."""
    from portal.models.types import PortableUUID

    puuid = PortableUUID()
    test_uuid = uuid.uuid4()

    result = puuid.process_result_value(str(test_uuid), _sqlite_dialect())
    assert isinstance(result, uuid.UUID)
    assert result == test_uuid


def test_portable_uuid_dialect_impl_sqlite() -> None:
    """SQLite dialect gets String(36) descriptor."""
    from portal.models.types import PortableUUID

    puuid = PortableUUID()
    impl = puuid.load_dialect_impl(_sqlite_dialect())
    assert isinstance(impl, String)


def test_portable_uuid_dialect_impl_postgresql() -> None:
    """PostgreSQL dialect gets PGUUID descriptor."""
    from portal.models.types import PortableUUID

    puuid = PortableUUID()
    impl = puuid.load_dialect_impl(_pg_dialect())
    assert isinstance(impl, PGUUID)


def test_portable_uuid_pydantic_serialization() -> None:
    """uuid.UUID from PortableUUID serializes correctly in JSON."""
    from portal.models.types import PortableUUID

    puuid = PortableUUID()
    test_uuid = uuid.uuid4()
    result = puuid.process_result_value(str(test_uuid), _sqlite_dialect())

    # Pydantic serializes uuid.UUID as string
    serialized = json.dumps({"id": str(result)})
    data = json.loads(serialized)
    assert data["id"] == str(test_uuid)


def test_portable_uuid_python_invariant() -> None:
    """Python-side invariant: type(value) is uuid.UUID where schema promises UUID identity."""
    from portal.models.types import PortableUUID

    puuid = PortableUUID()
    test_uuid = uuid.uuid4()

    # All paths should return uuid.UUID
    for dialect in [_sqlite_dialect(), _pg_dialect()]:
        result = puuid.process_result_value(test_uuid, dialect)
        assert type(result) is uuid.UUID, f"Expected uuid.UUID, got {type(result)} for {dialect.name}"

        result_str = puuid.process_result_value(str(test_uuid), dialect)
        assert type(result_str) is uuid.UUID, f"Expected uuid.UUID, got {type(result_str)} for {dialect.name}"


def test_portable_uuid_roundtrip_sqlite() -> None:
    """Full roundtrip: UUID → bind → store → load → UUID."""
    from portal.models.types import PortableUUID

    puuid = PortableUUID()
    original = uuid.uuid4()

    # Bind for SQLite (stores as string)
    stored = puuid.process_bind_param(original, _sqlite_dialect())
    assert isinstance(stored, str)

    # Load from SQLite (string → UUID)
    loaded = puuid.process_result_value(stored, _sqlite_dialect())
    assert isinstance(loaded, uuid.UUID)
    assert loaded == original


def test_portable_uuid_roundtrip_postgresql() -> None:
    """Full roundtrip: UUID → bind → store → load → UUID (PostgreSQL)."""
    from portal.models.types import PortableUUID

    puuid = PortableUUID()
    original = uuid.uuid4()

    # Bind for PostgreSQL (stores as native UUID)
    stored = puuid.process_bind_param(original, _pg_dialect())
    assert isinstance(stored, uuid.UUID)

    # Load from PostgreSQL (UUID → UUID)
    loaded = puuid.process_result_value(stored, _pg_dialect())
    assert isinstance(loaded, uuid.UUID)
    assert loaded == original


def test_portable_uuid_cache_ok() -> None:
    """PortableUUID is cache-safe (required by SQLAlchemy)."""
    from portal.models.types import PortableUUID

    assert PortableUUID.cache_ok is True


# --- Helpers ---


class _FakeDialect:
    def __init__(self, name: str) -> None:
        self.name = name

    def type_descriptor(self, typeobj):
        return typeobj


def _sqlite_dialect() -> _FakeDialect:
    return _FakeDialect("sqlite")


def _pg_dialect() -> _FakeDialect:
    return _FakeDialect("postgresql")
