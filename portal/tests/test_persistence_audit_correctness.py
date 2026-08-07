from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.database import Base
from portal.models.audit_record import AuditRecord
from portal.models.case import Case
from portal.models.client import Client
from portal.models.document import Document
from portal.models.evidence_snapshot import EvidenceSnapshot, SnapshotStatus
from portal.models.user import Role, Tenant, User
from portal.services.audit_service import audit
from portal.services.document_export_service import export_documents_to_packet


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    Tenant.__table__,
                    Role.__table__,
                    User.__table__,
                    Client.__table__,
                    Case.__table__,
                    Document.__table__,
                    EvidenceSnapshot.__table__,
                    AuditRecord.__table__,
                ],
            )
        )
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session
    await engine.dispose()


def _document(*, doc_id: str, tenant_id: str, case_id: str, user_id: str) -> Document:
    return Document(
        id=doc_id,
        tenant_id=tenant_id,
        case_id=case_id,
        uploaded_by=user_id,
        name="Packet Exhibit.pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        size_bytes=2048,
        checksum_sha256="a" * 64,
        storage_key=f"documents/{doc_id}.pdf",
        storage_bucket="sintra-documents",
        current_version=1,
        description="Durable provenance certification fixture",
    )


@pytest.mark.asyncio
async def test_document_packet_export_persists_snapshot_and_audit_record(db: AsyncSession):
    tenant_id = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    doc = _document(doc_id=str(uuid.uuid4()), tenant_id=tenant_id, case_id=case_id, user_id=user_id)

    result = await export_documents_to_packet(
        session=db,
        case_id=case_id,
        tenant_id=tenant_id,
        user_id=user_id,
        documents=[doc],
    )

    snapshot_count = await db.scalar(select(func.count()).select_from(EvidenceSnapshot))
    audit_count = await db.scalar(select(func.count()).select_from(AuditRecord))
    persisted_snapshot = await db.get(EvidenceSnapshot, uuid.UUID(result.snapshot_id))
    persisted_audit = await db.get(AuditRecord, uuid.UUID(result.audit_id))

    assert snapshot_count == 1
    assert audit_count == 1
    assert persisted_snapshot is not None
    assert persisted_snapshot.evidence_hash == result.evidence_hash
    assert persisted_audit is not None
    assert persisted_audit.packet_hash == result.packet_hash
    assert persisted_audit.snapshot_id == uuid.UUID(result.snapshot_id)


@pytest.mark.asyncio
async def test_document_packet_export_supersedes_prior_active_snapshot(db: AsyncSession):
    tenant_id = str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    await export_documents_to_packet(
        session=db,
        case_id=case_id,
        tenant_id=tenant_id,
        user_id=user_id,
        documents=[_document(doc_id=str(uuid.uuid4()), tenant_id=tenant_id, case_id=case_id, user_id=user_id)],
    )
    second = await export_documents_to_packet(
        session=db,
        case_id=case_id,
        tenant_id=tenant_id,
        user_id=user_id,
        documents=[_document(doc_id=str(uuid.uuid4()), tenant_id=tenant_id, case_id=case_id, user_id=user_id)],
    )

    rows = (await db.execute(select(EvidenceSnapshot).where(EvidenceSnapshot.case_id == case_id))).scalars().all()
    statuses = sorted(row.status for row in rows)

    assert len(rows) == 2
    assert statuses == sorted([SnapshotStatus.ACTIVE, SnapshotStatus.SUPERSEDED])
    assert {row.snapshot_version for row in rows} == {1, 2}
    assert second.snapshot_id != rows[0].snapshot_id


@pytest.mark.asyncio
async def test_audit_service_does_not_rollback_caller_transaction_on_flush_failure():
    class FailingSession:
        def __init__(self) -> None:
            self.rollback_called = False
            self.added = []

        async def execute(self, _stmt):
            class Result:
                def scalar_one_or_none(self):
                    return None

            return Result()

        def add(self, entry):
            self.added.append(entry)

        async def flush(self):
            raise RuntimeError("flush failed")

        async def rollback(self):
            self.rollback_called = True

    session = FailingSession()

    with pytest.raises(RuntimeError, match="flush failed"):
        await audit(session, action="certify", tenant_id=str(uuid.uuid4()))  # type: ignore[arg-type]

    assert session.added
    assert session.rollback_called is False
