"""Durable document packet provenance services."""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from portal.models.audit_record import AuditRecord
from portal.models.evidence_snapshot import EvidenceSnapshot, SnapshotStatus

from .evidence_audit_service import AuditRecordValue, AuditVerificationError
from .evidence_snapshot_service import SnapshotRecord


async def create_evidence_snapshot(
    session: AsyncSession,
    *,
    case_id: str,
    evidence_hash: str,
    manifest_hash: str,
    created_by: str,
    evidence_count: int = 0,
) -> SnapshotRecord:
    """Persist a new evidence snapshot and supersede the prior active one in the caller transaction."""
    active_result = await session.execute(
        select(EvidenceSnapshot).where(
            EvidenceSnapshot.case_id == case_id,
            EvidenceSnapshot.status == SnapshotStatus.ACTIVE,
        )
    )
    for active in active_result.scalars().all():
        active.status = SnapshotStatus.SUPERSEDED

    version_result = await session.execute(
        select(func.max(EvidenceSnapshot.snapshot_version)).where(EvidenceSnapshot.case_id == case_id)
    )
    next_version = (version_result.scalar_one_or_none() or 0) + 1
    snapshot_id = uuid.uuid4()
    created_at = datetime.now(UTC)
    row = EvidenceSnapshot(
        snapshot_id=snapshot_id,
        case_id=case_id,
        evidence_hash=evidence_hash,
        manifest_hash=manifest_hash,
        snapshot_version=next_version,
        created_at=created_at,
        created_by=created_by,
        evidence_count=evidence_count,
        status=SnapshotStatus.ACTIVE,
    )
    await _add(session, row)
    await session.flush()
    return SnapshotRecord(
        snapshot_id=str(snapshot_id),
        case_id=case_id,
        evidence_hash=evidence_hash,
        manifest_hash=manifest_hash,
        snapshot_version=next_version,
        created_at=created_at,
        created_by=created_by,
        evidence_count=evidence_count,
        status=SnapshotStatus.ACTIVE,
    )


async def create_packet_audit_record(
    session: AsyncSession,
    *,
    snapshot_id: str,
    evidence_hash: str,
    packet_id: str,
    packet_hash: str,
    packet_version: int,
    serialization_version: int,
    created_by: str,
    verify_packet: bool = True,
) -> AuditRecordValue:
    """Persist an immutable packet audit record in the caller transaction."""
    verification_status = "verified"
    verification_details = None
    if verify_packet and packet_hash != evidence_hash:
        verification_status = "failed"
        verification_details = f"Packet hash mismatch: packet_hash={packet_hash}, evidence_hash={evidence_hash}"
        raise AuditVerificationError(verification_details)

    audit_id = uuid.uuid4()
    created_at = datetime.now(UTC)
    row = AuditRecord(
        audit_id=audit_id,
        snapshot_id=uuid.UUID(str(snapshot_id)),
        evidence_hash=evidence_hash,
        packet_id=_coerce_packet_uuid(packet_id),
        packet_hash=packet_hash,
        packet_version=packet_version,
        serialization_version=serialization_version,
        created_at=created_at,
        created_by=created_by,
        verification_status=verification_status,
        verification_details=verification_details,
    )
    await _add(session, row)
    await session.flush()
    return AuditRecordValue(
        audit_id=str(audit_id),
        snapshot_id=str(snapshot_id),
        evidence_hash=evidence_hash,
        packet_id=str(row.packet_id),
        packet_hash=packet_hash,
        packet_version=packet_version,
        serialization_version=serialization_version,
        created_at=created_at,
        created_by=created_by,
        verification_status=verification_status,  # type: ignore[arg-type]
        verification_details=verification_details,
    )


def _coerce_packet_uuid(packet_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(packet_id))
    except ValueError:
        return uuid.uuid5(uuid.NAMESPACE_URL, f"sintraprime-packet:{packet_id}")


async def _add(session: AsyncSession, row: object) -> None:
    result = session.add(row)
    if inspect.isawaitable(result):
        await result
