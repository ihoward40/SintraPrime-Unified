"""Builds redacted, hash-addressed persistent matter export packets."""

from __future__ import annotations

import hashlib
import json
import textwrap
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.client import Matter
from ..models.deadline_evidence import (
    MatterDeadline,
    MatterDeadlineVersion,
    MatterEvidenceFinding,
    MatterEvidenceLink,
    MatterEvidenceNode,
)
from ..models.matter_intelligence import (
    MatterAccount,
    MatterAssessment,
    MatterAssessmentVersion,
    MatterAttachment,
    MatterAuditEvent,
    MatterCommunication,
    MatterDispute,
    MatterFiling,
    MatterParty,
)
from .matter_intelligence_service import MatterIntelligenceService, redact_sensitive


class MatterExportError(ValueError):
    """Raised when a matter packet cannot be safely assembled."""


class MatterExportResult:
    def __init__(
        self,
        *,
        export_id: str,
        matter_id: str,
        export_format: str,
        packet_hash: str,
        redacted_manifest_hash: str,
        audit_event_id: str,
        content: bytes,
    ) -> None:
        self.export_id = export_id
        self.matter_id = matter_id
        self.format = export_format
        self.packet_hash = packet_hash
        self.redacted_manifest_hash = redacted_manifest_hash
        self.audit_event_id = audit_event_id
        self.content = content


def _model_payload(model: Any) -> dict[str, Any]:
    return {
        column.name: getattr(model, column.name)
        for column in model.__table__.columns
        if column.name not in {"deleted_at"}
    }


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


class MatterExportService(MatterIntelligenceService):
    """Assembles a read-only packet from all tenant-scoped matter intelligence records."""

    async def _rows(
        self,
        db: AsyncSession,
        model: Any,
        matter_id: str,
        tenant_id: str,
        *,
        ascending: bool = True,
    ) -> list[dict[str, Any]]:
        conditions = [model.matter_id == matter_id, model.tenant_id == tenant_id]
        if hasattr(model, "deleted_at"):
            conditions.append(model.deleted_at.is_(None))
        statement = select(model).where(*conditions)
        if hasattr(model, "created_at"):
            statement = statement.order_by(
                model.created_at.asc() if ascending else model.created_at.desc()
            )
        result = await db.execute(statement)
        return [
            _json_safe(redact_sensitive(_model_payload(item))) for item in result.scalars().all()
        ]

    async def _matter_payload(
        self, db: AsyncSession, matter_id: str, tenant_id: str
    ) -> dict[str, Any]:
        result = await db.execute(
            select(Matter).where(
                Matter.id == matter_id,
                Matter.tenant_id == tenant_id,
                Matter.deleted_at.is_(None),
            )
        )
        matter = result.scalar_one_or_none()
        if matter is None:
            raise MatterExportError("matter not found")
        return _json_safe(
            {
                "id": str(matter.id),
                "tenant_id": str(matter.tenant_id),
                "matter_number": matter.matter_number,
                "title": matter.title,
                "description": matter.description,
                "practice_area": matter.practice_area,
                "status": matter.status,
                "opened_at": matter.opened_at,
                "closed_at": matter.closed_at,
                "created_at": matter.created_at,
                "updated_at": matter.updated_at,
            }
        )

    async def build_packet(
        self,
        db: AsyncSession,
        *,
        matter_id: str,
        tenant_id: str,
        actor_id: str,
        actor_role: str,
        export_format: str,
    ) -> MatterExportResult:
        if export_format not in {"JSON", "PDF"}:
            raise MatterExportError("unsupported export format")

        matter = await self._matter_payload(db, matter_id, tenant_id)
        export_id = str(uuid.uuid4())
        generated_at = datetime.now(UTC).isoformat()
        sections = {
            "parties": await self._rows(db, MatterParty, matter_id, tenant_id),
            "accounts": await self._rows(db, MatterAccount, matter_id, tenant_id),
            "filings": await self._rows(db, MatterFiling, matter_id, tenant_id),
            "communications": await self._rows(db, MatterCommunication, matter_id, tenant_id),
            "disputes": await self._rows(db, MatterDispute, matter_id, tenant_id),
            "attachments": await self._rows(db, MatterAttachment, matter_id, tenant_id),
            "assessments": await self._rows(db, MatterAssessment, matter_id, tenant_id),
            "assessment_versions": await self._rows(
                db, MatterAssessmentVersion, matter_id, tenant_id
            ),
            "deadlines": await self._rows(db, MatterDeadline, matter_id, tenant_id),
            "deadline_versions": await self._rows(db, MatterDeadlineVersion, matter_id, tenant_id),
            "evidence_nodes": await self._rows(db, MatterEvidenceNode, matter_id, tenant_id),
            "evidence_links": await self._rows(db, MatterEvidenceLink, matter_id, tenant_id),
            "evidence_findings": await self._rows(db, MatterEvidenceFinding, matter_id, tenant_id),
        }
        audit_events = await self._rows(db, MatterAuditEvent, matter_id, tenant_id)
        audit_valid = self.validate_audit_chain(
            [
                type("AuditRow", (), {**event, "details_redacted": event.get("details", {})})()
                for event in audit_events
            ]
        )
        redacted_manifest = [
            {
                "attachment_id": item.get("id"),
                "label_redacted": item.get("label_redacted"),
                "attachment_kind": item.get("attachment_kind"),
                "checksum_sha256": item.get("checksum_sha256"),
                "classification": item.get("classification"),
                "redaction_status": item.get("redaction_status"),
            }
            for item in sections["attachments"]
        ]
        manifest_hash = _sha256(redacted_manifest)
        audit_summary = {
            "chain_valid_before_export": audit_valid,
            "event_count_before_export": len(audit_events),
            "latest_entry_hash": audit_events[-1].get("entry_hash") if audit_events else None,
        }
        packet = {
            "schema": "sintraprime.matter-export.v1",
            "export_id": export_id,
            "generated_at": generated_at,
            "generated_by": actor_id,
            "matter": matter,
            "chronology": self._chronology(sections, audit_events),
            "sections": sections,
            "contradictions_and_missing_evidence": sections["evidence_findings"],
            "review_status": [
                *sections["assessments"],
                *sections["deadlines"],
                *sections["evidence_nodes"],
            ],
            "audit_chain": audit_summary,
            "redacted_evidence_manifest": redacted_manifest,
            "limitations": [
                "This packet contains redacted matter metadata and issue-spotting records only.",
                "It is not a legal opinion and does not establish the truth of any asserted fact.",
                "Source documents are not embedded; verify against the protected evidence vault.",
            ],
        }
        packet_hash = _sha256(packet)
        packet["integrity"] = {
            "packet_hash": packet_hash,
            "packet_hash_scope": "canonical packet excluding integrity object",
            "redacted_manifest_hash": manifest_hash,
        }
        packet_json = json.dumps(packet, sort_keys=True, indent=2, default=str)
        content = (
            packet_json.encode("utf-8")
            if export_format == "JSON"
            else render_pdf(packet_json, matter["title"])
        )

        await self._write_audit(
            db,
            matter_id=matter_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action="matter_export_created",
            object_type="matter_export",
            object_id=export_id,
            details={
                "format": export_format,
                "packet_hash": packet_hash,
                "redacted_manifest_hash": manifest_hash,
                "byte_count": len(content),
            },
        )
        await db.flush()
        event_result = await db.execute(
            select(MatterAuditEvent)
            .where(
                MatterAuditEvent.matter_id == matter_id,
                MatterAuditEvent.tenant_id == tenant_id,
                MatterAuditEvent.object_id == export_id,
            )
            .order_by(MatterAuditEvent.created_at.desc())
        )
        export_event = event_result.scalars().first()
        if export_event is None:
            raise MatterExportError("export audit event was not persisted")
        return MatterExportResult(
            export_id=export_id,
            matter_id=matter_id,
            export_format=export_format,
            packet_hash=packet_hash,
            redacted_manifest_hash=manifest_hash,
            audit_event_id=str(export_event.id),
            content=content,
        )

    @staticmethod
    def _chronology(
        sections: dict[str, list[dict[str, Any]]], audit_events: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for item in sections["communications"]:
            events.append(
                {
                    "occurred_at": item.get("occurred_at"),
                    "kind": "COMMUNICATION",
                    "id": item.get("id"),
                    "label": item.get("subject_redacted") or item.get("communication_type"),
                }
            )
        for item in sections["deadlines"]:
            events.append(
                {
                    "occurred_at": item.get("due_at"),
                    "kind": "DEADLINE",
                    "id": item.get("id"),
                    "label": item.get("title"),
                }
            )
        for item in audit_events:
            events.append(
                {
                    "occurred_at": item.get("created_at"),
                    "kind": "AUDIT",
                    "id": item.get("id"),
                    "label": item.get("action"),
                }
            )
        return sorted(events, key=lambda item: str(item.get("occurred_at") or ""))


def _pdf_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def render_pdf(packet_json: str, title: str) -> bytes:
    """Render a dependency-free text PDF containing the redacted packet manifest."""
    lines = [
        title,
        "SintraPrime Persistent Matter Export",
        "",
        *textwrap.wrap(packet_json, width=105),
    ]
    page_lines = [lines[index : index + 54] for index in range(0, len(lines), 54)] or [[]]
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    page_ids = [4 + index * 2 for index in range(len(page_lines))]
    objects.append(
        f"<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] /Count {len(page_ids)} >>".encode()
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for index, page in enumerate(page_lines):
        page_id = 4 + index * 2
        content_id = page_id + 1
        commands = ["BT", "/F1 8 Tf", "48 760 Td"]
        for line_number, line in enumerate(page):
            if line_number:
                commands.append("0 -13 Td")
            commands.append(f"({_pdf_escape(line[:180])}) Tj")
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1", errors="replace")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>".encode()
        )
        objects.append(
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        )
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode())
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode()
    )
    return bytes(output)
