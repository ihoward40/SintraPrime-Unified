"""Wave 2D — MESSAGE PERSISTENCE CERTIFICATION (SP-CONVERGE-001 §VIII).

DB-real coverage of the portal messages domain (no service-layer mocks):
create, user/agent/system senders, thread (conversation) / tenant / reply
relationships, ordering, timestamps, Unicode, large bodies, optional fields,
invalid FKs, rollback, concurrent inserts with the unique idempotency key,
and restart retrieval. Also asserts snake_case column alignment against the
portal lineage migrations (legacy runtime `messages` shape is a DIFFERENT
schema world — classified COMPATIBILITY_ONLY in Wave 2C and out of scope).

NOTE on sender typing: the portal message model has no sender-type
discriminator; senders are user identities (Users may be system/agent
identities via `users.is_system`). The tests certify exactly what the
production schema supports.
"""
from __future__ import annotations

import asyncio
import pathlib
import tempfile
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from portal.database import Base
from portal.models.message import Message, MessageAttachment, MessageThread
from portal.models.user import Permission, Role, RolePermission, Tenant, User

pytestmark = pytest.mark.portal


def _uuid(label: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, "sintraprime-w2d:" + label)


@pytest_asyncio.fixture
async def db(tmp_path: pathlib.Path):
    """File-backed shared SQLite so 'restart'/'concurrent' fixtures truly open
    NEW engines against the SAME committed data (in-memory SQLite is
    per-connection — a known 2D fixture trap)."""
    db_file = tmp_path / "w2d-messages.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync: Base.metadata.create_all(
                sync,
                tables=[
                    Tenant.__table__,
                    Role.__table__,
                    User.__table__,
                    MessageThread.__table__,
                    Message.__table__,
                    MessageAttachment.__table__,
                    RolePermission.__table__,
                    Permission.__table__,
                ],
            )
        )
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        # Seed tenant + role + three principals: user, agent, system.
        session.add_all([
            Tenant(id=_uuid("tenant"), name="W2D Tenant", slug="w2d"),
            Role(id=_uuid("role"), name="W2D_ROLE", display_name="W2D", is_system=True),
        ])
        await session.flush()
        session.add_all([
            User(id=_uuid("user"), tenant_id=_uuid("tenant"), role_id=_uuid("role"),
                 email="user@w2d.test", hashed_password="x", first_name="U", last_name="One"),
            User(id=_uuid("agent"), tenant_id=_uuid("tenant"), role_id=_uuid("role"),
                 email="agent@w2d.test", hashed_password="x", first_name="A", last_name="Gent"),
            User(id=_uuid("system"), tenant_id=_uuid("tenant"), role_id=_uuid("role"),
                 email="system@w2d.test", hashed_password="x", first_name="S", last_name="ystem"),
        ])
        await session.commit()
        yield session
    await engine.dispose()


async def _mk_thread(db: AsyncSession, **overrides) -> MessageThread:
    fields: dict = {
        "id": _uuid("thread"),
        "tenant_id": _uuid("tenant"),
        "subject": "W2D certification thread",
        "participants": [str(_uuid("user"))],
        "created_by": _uuid("user"),
    }
    fields.update(overrides)
    thread = MessageThread(**fields)
    db.add(thread)
    await db.flush()
    return thread


def _msg(thread_id, **overrides) -> Message:
    fields: dict = {
        "thread_id": thread_id,
        "tenant_id": _uuid("tenant"),
        "sender_id": _uuid("user"),
        "content": "hello",
    }
    fields.update(overrides)
    return Message(**fields)


# ---------------------------------------------------------------------------
# create / senders / relationships
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_message_round_trip(db: AsyncSession):
    thread = await _mk_thread(db)
    msg = _msg(thread.id, content="create round-trip")
    db.add(msg)
    await db.commit()

    loaded = (await db.execute(select(Message).where(Message.id == msg.id))).scalar_one()
    assert loaded.content == "create round-trip"
    assert loaded.thread_id == thread.id
    assert loaded.is_edited is False
    assert loaded.is_deleted is False
    assert loaded.created_at is not None


@pytest.mark.asyncio
async def test_user_agent_and_system_senders_persist(db: AsyncSession):
    """All three sender identities (user/agent/system user rows) persist and
    round-trip with their FK intact. The schema models senders as users; there
    is no separate sender-type column (documented 2D finding)."""
    thread = await _mk_thread(db)
    senders = [_uuid("user"), _uuid("agent"), _uuid("system")]
    db.add_all([_msg(thread.id, sender_id=s, content=f"from {i}") for i, s in enumerate(senders)])
    await db.commit()

    rows = (await db.execute(select(Message).order_by(Message.created_at))).scalars().all()
    assert len(rows) == 3
    assert {str(r.sender_id) for r in rows} == {str(s) for s in senders}
    # Every sender resolves to a real user row (FK integrity through ORM).
    for r in rows:
        assert (await db.get(User, r.sender_id)) is not None


@pytest.mark.asyncio
async def test_conversation_thread_relationship_and_count(db: AsyncSession):
    thread = await _mk_thread(db)
    db.add_all([_msg(thread.id, content=f"m{i}") for i in range(3)])
    thread.message_count = 3
    await db.commit()

    loaded_thread = await db.get(MessageThread, thread.id)
    await db.refresh(loaded_thread, attribute_names=["messages"])
    assert len(loaded_thread.messages) == 3
    assert loaded_thread.message_count == 3
    assert all(m.thread_id == thread.id for m in loaded_thread.messages)


@pytest.mark.asyncio
async def test_tenant_scoping_on_thread_and_messages(db: AsyncSession):
    thread = await _mk_thread(db)
    db.add_all([_msg(thread.id) for _ in range(2)])
    await db.commit()

    tenant_rows = (await db.execute(
        select(Message).where(Message.tenant_id == _uuid("tenant"))
    )).scalars().all()
    assert len(tenant_rows) == 2
    other = (await db.execute(
        select(Message).where(Message.tenant_id == _uuid("other-tenant"))
    )).scalars().all()
    assert other == []


@pytest.mark.asyncio
async def test_reply_relationship_round_trip(db: AsyncSession):
    thread = await _mk_thread(db)
    parent = _msg(thread.id, content="parent")
    db.add(parent)
    await db.flush()
    child = _msg(thread.id, content="child", reply_to_id=parent.id)
    db.add(child)
    await db.commit()

    loaded = (await db.execute(select(Message).where(Message.reply_to_id == parent.id))).scalar_one()
    assert loaded.reply_to_id == parent.id


# ---------------------------------------------------------------------------
# ordering / timestamps / content edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ordering_by_created_at(db: AsyncSession):
    thread = await _mk_thread(db)
    for i in range(5):
        db.add(_msg(thread.id, content=f"seq {i}"))
        await db.flush()
    await db.commit()

    rows = (await db.execute(
        select(Message).order_by(Message.created_at.asc())
    )).scalars().all()
    stamps = [r.created_at for r in rows]
    assert stamps == sorted(stamps)
    assert len(rows) == 5


@pytest.mark.asyncio
async def test_timestamps_set_by_server_or_client(db: AsyncSession):
    thread = await _mk_thread(db)
    msg = _msg(thread.id)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    assert msg.created_at is not None
    assert msg.updated_at is not None


@pytest.mark.asyncio
async def test_unicode_content_round_trip(db: AsyncSession):
    thread = await _mk_thread(db)
    payload = "café — 中文 \U0001f9f5 résumé ✓"
    db.add(_msg(thread.id, content=payload))
    await db.commit()
    loaded = (await db.execute(select(Message).where(Message.thread_id == thread.id))).scalar_one()
    assert loaded.content == payload


@pytest.mark.asyncio
async def test_large_body_round_trip(db: AsyncSession):
    thread = await _mk_thread(db)
    payload = "x" * 50_000  # router cap is 50k; Text column has no hard limit
    db.add(_msg(thread.id, content=payload))
    await db.commit()
    loaded = (await db.execute(select(Message).where(Message.thread_id == thread.id))).scalar_one()
    assert len(loaded.content) == 50_000


@pytest.mark.asyncio
async def test_null_and_optional_fields(db: AsyncSession):
    thread = await _mk_thread(db)
    msg = _msg(thread.id, mentions=None, reply_to_id=None, idempotency_key=None,
               read_by=None, deleted_by=None)
    db.add(msg)
    await db.commit()
    loaded = await db.get(Message, msg.id)
    assert loaded.mentions is None
    assert loaded.reply_to_id is None
    assert loaded.idempotency_key is None
    # Defaults applied at ORM level
    assert loaded.is_edited is False
    assert loaded.is_deleted is False


# ---------------------------------------------------------------------------
# constraints / failure semantics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_foreign_keys_rejected(db: AsyncSession, tmp_path: pathlib.Path):
    """SQLite enforces FKs only with PRAGMA foreign_keys=ON per connection
    (documented SQLite emulation behavior; PostgreSQL enforces natively).
    Uses a dedicated engine whose connections turn the pragma on, so FK
    violations raise real IntegrityErrors."""
    from sqlalchemy import event

    thread = await _mk_thread(db)
    await db.commit()  # release the fixture session's write lock on the file DB
    db_file = tmp_path / "w2d-messages.db"

    def _set_fk_pragma(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    fk_engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    event.listen(fk_engine.sync_engine, "connect", _set_fk_pragma)
    fk_maker = async_sessionmaker(fk_engine, expire_on_commit=False, class_=AsyncSession)

    async with fk_maker() as session:
        # thread FK that doesn't exist
        bad_thread = Message(
            thread_id=_uuid("no-such-thread"), tenant_id=_uuid("tenant"),
            sender_id=_uuid("user"), content="bad thread fk",
        )
        session.add(bad_thread)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

        # tenant FK that doesn't exist
        bad_tenant = Message(
            thread_id=thread.id, tenant_id=_uuid("no-such-tenant"),
            sender_id=_uuid("user"), content="bad tenant fk",
        )
        session.add(bad_tenant)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

        # sender FK that doesn't exist
        bad_sender = Message(
            thread_id=thread.id, tenant_id=_uuid("tenant"),
            sender_id=_uuid("no-such-user"), content="bad sender fk",
        )
        session.add(bad_sender)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

    await fk_engine.dispose()


@pytest.mark.asyncio
async def test_missing_required_fields_rejected(db: AsyncSession):
    thread = await _mk_thread(db)
    db.add(Message(thread_id=thread.id, tenant_id=_uuid("tenant"), sender_id=_uuid("user")))
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


@pytest.mark.asyncio
async def test_rollback_leaves_no_partial_message(db: AsyncSession):
    thread = await _mk_thread(db)
    db.add(_msg(thread.id, content="will roll back"))
    await db.flush()
    await db.rollback()
    rows = (await db.execute(select(Message))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_idempotency_key_unique_and_reuse_rejected(db: AsyncSession):
    thread = await _mk_thread(db)
    thread_id = thread.id  # capture BEFORE rollback (rollback expires loaded objects)
    first = _msg(thread.id, idempotency_key="w2d-key-001")
    db.add(first)
    await db.commit()

    db.add(_msg(thread_id, idempotency_key="w2d-key-001"))
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()

    # Distinct keys coexist
    db.add(_msg(thread_id, idempotency_key="w2d-key-002"))
    await db.commit()
    rows = (await db.execute(select(Message))).scalars().all()
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_concurrent_inserts_same_idempotency_key_only_one_wins(db: AsyncSession, tmp_path: pathlib.Path):
    """Two sessions race the same idempotency key: exactly one insert wins."""
    thread = await _mk_thread(db)
    await db.commit()

    db_file = tmp_path / "w2d-messages.db"
    maker = async_sessionmaker(
        create_async_engine(f"sqlite+aiosqlite:///{db_file}", connect_args={"check_same_thread": False}),
        expire_on_commit=False, class_=AsyncSession,
    )

    results: list[str] = []
    barrier = asyncio.Barrier(2) if hasattr(asyncio, "Barrier") else None

    async def insert_one(tag: str):
        async with maker() as session:
            session.add(_msg(thread.id, idempotency_key="w2d-race-001", content=tag))
            try:
                if barrier is not None:
                    await barrier.wait()
                await session.commit()
                results.append(f"{tag}:ok")
            except IntegrityError:
                results.append(f"{tag}:conflict")
            finally:
                await session.close()

    await asyncio.gather(insert_one("a"), insert_one("b"))
    ok = [r for r in results if r.endswith(":ok")]
    # SQLite serializes writers via file locking; with the unique constraint,
    # exactly one of the two racers commits (the other gets IntegrityError).
    assert len(ok) == 1, results
    rows = (await db.execute(select(Message).where(Message.idempotency_key == "w2d-race-001"))).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_restart_retrieval_new_engine(db: AsyncSession, tmp_path: pathlib.Path):
    """Restart semantics: a fresh engine/session reads committed messages."""
    thread = await _mk_thread(db)
    db.add_all([_msg(thread.id, content=f"survives {i}") for i in range(3)])
    await db.commit()

    db_file = tmp_path / "w2d-messages.db"
    fresh_engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", connect_args={"check_same_thread": False})
    fresh = async_sessionmaker(fresh_engine, expire_on_commit=False, class_=AsyncSession)
    async with fresh() as session:
        rows = (await session.execute(
            select(Message).order_by(Message.created_at.asc())
        )).scalars().all()
        assert len(rows) == 3
        assert all(m.content.startswith("survives") for m in rows)
    await fresh_engine.dispose()


# ---------------------------------------------------------------------------
# snake_case alignment (directive: verify column naming explicitly)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_snake_case_column_alignment(db: AsyncSession):
    """message_threads / messages expose snake_case columns exactly as the
    portal lineage migrations declare (Wave 2C classification)."""
    cols_messages = {c.name for c in Message.__table__.columns}
    cols_threads = {c.name for c in MessageThread.__table__.columns}
    for expected in ["thread_id", "tenant_id", "sender_id", "reply_to_id",
                     "idempotency_key", "is_edited", "is_deleted", "deleted_by",
                     "content_encrypted", "encryption_iv", "read_by", "created_at"]:
        assert expected in cols_messages, f"messages.{expected} missing"
    for expected in ["tenant_id", "client_id", "case_id", "last_message_at",
                     "message_count", "is_archived", "is_pinned", "is_encrypted",
                     "retention_days", "purge_after", "created_by", "created_at"]:
        assert expected in cols_threads, f"message_threads.{expected} missing"
