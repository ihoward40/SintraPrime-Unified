"""Tenant-scoped persistence service for creditor and UCC matter intelligence."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.client import Matter
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
from .audit_service import audit

ModelT = TypeVar("ModelT")

_SSN_RE = re.compile(r"\b\d{3}[- ]?\d{2}[- ]?\d{4}\b")
_LONG_NUMBER_RE = re.compile(r"\b\d{10,19}\b")


def redact_sensitive(value: Any) -> Any:
    """Redact SSNs and long account/card-like numbers recursively before persistence."""
    if isinstance(value, str):
        redacted = _SSN_RE.sub("[REDACTED-SSN]", value)
        return _LONG_NUMBER_RE.sub("[REDACTED-IDENTIFIER]", redacted)
    if isinstance(value, dict):
        return {str(key): redact_sensitive(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value


def _model_payload(model: Any) -> dict[str, Any]:
    return {
        column.name: getattr(model, column.name)
        for column in model.__table__.columns
        if column.name not in {"deleted_at"}
    }


def _present_ids(*values: Any) -> list[str]:
    return [value for value in values if isinstance(value, str) and value]


class MatterIntelligenceError(ValueError):
    """Expected matter-intelligence validation or access error."""


class MatterIntelligenceService:
    """Stores tenant-scoped matter records and append-only assessment history."""

    async def _matter(self, db: AsyncSession, matter_id: str, tenant_id: str) -> Matter:
        result = await db.execute(
            select(Matter).where(
                Matter.id == matter_id,
                Matter.tenant_id == tenant_id,
                Matter.deleted_at.is_(None),
            )
        )
        matter = result.scalar_one_or_none()
        if matter is None:
            raise MatterIntelligenceError("matter not found")
        return matter

    async def _party_ids(
        self, db: AsyncSession, matter_id: str, tenant_id: str, ids: list[str]
    ) -> None:
        values = {value for value in ids if value}
        if not values:
            return
        result = await db.execute(
            select(MatterParty.id).where(
                MatterParty.id.in_(values),
                MatterParty.matter_id == matter_id,
                MatterParty.tenant_id == tenant_id,
                MatterParty.deleted_at.is_(None),
            )
        )
        found = set(result.scalars().all())
        if found != values:
            raise MatterIntelligenceError("party reference is outside this matter")

    async def _account(
        self, db: AsyncSession, account_id: str, matter_id: str, tenant_id: str
    ) -> MatterAccount:
        result = await db.execute(
            select(MatterAccount).where(
                MatterAccount.id == account_id,
                MatterAccount.matter_id == matter_id,
                MatterAccount.tenant_id == tenant_id,
                MatterAccount.deleted_at.is_(None),
            )
        )
        account = result.scalar_one_or_none()
        if account is None:
            raise MatterIntelligenceError("account not found")
        return account

    async def _write_audit(
        self,
        db: AsyncSession,
        *,
        matter_id: str,
        tenant_id: str,
        actor_id: str,
        actor_role: str,
        action: str,
        object_type: str,
        object_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        previous = await db.scalar(
            select(MatterAuditEvent.entry_hash)
            .where(
                MatterAuditEvent.matter_id == matter_id,
                MatterAuditEvent.tenant_id == tenant_id,
            )
            .order_by(MatterAuditEvent.created_at.desc())
            .limit(1)
        )
        safe_details = redact_sensitive(details or {})
        content = {
            "matter_id": matter_id,
            "actor_id": actor_id,
            "action": action,
            "object_type": object_type,
            "object_id": object_id,
            "details": safe_details,
            "previous_hash": previous,
        }
        entry_hash = hashlib.sha256(
            json.dumps(content, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        db.add(
            MatterAuditEvent(
                tenant_id=tenant_id,
                matter_id=matter_id,
                actor_id=actor_id,
                action=action,
                object_type=object_type,
                object_id=object_id,
                details_redacted=safe_details,
                previous_hash=previous,
                entry_hash=entry_hash,
            )
        )
        await audit(
            db,
            action=f"matter_intelligence_{action}",
            user_id=actor_id,
            tenant_id=tenant_id,
            actor_role=actor_role,
            resource_type=object_type,
            resource_id=object_id,
            details=safe_details,
        )

    async def _list(
        self, db: AsyncSession, model: Any, matter_id: str, tenant_id: str
    ) -> list[dict[str, Any]]:
        await self._matter(db, matter_id, tenant_id)
        result = await db.execute(
            select(model)
            .where(
                model.matter_id == matter_id,
                model.tenant_id == tenant_id,
                model.deleted_at.is_(None),
            )
            .order_by(model.created_at.desc())
        )
        return [_model_payload(item) for item in result.scalars().all()]

    async def create_party(
        self,
        db: AsyncSession,
        matter_id: str,
        tenant_id: str,
        actor_id: str,
        actor_role: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        await self._matter(db, matter_id, tenant_id)
        item = MatterParty(
            tenant_id=tenant_id,
            matter_id=matter_id,
            created_by=actor_id,
            display_name=redact_sensitive(data["display_name"]),
            role=data["role"],
            contact_summary=redact_sensitive(data.get("contact_summary")),
            identifier_redacted=redact_sensitive(data.get("identifier")),
            metadata_json=redact_sensitive(data.get("metadata", {})),
        )
        db.add(item)
        await db.flush()
        await self._write_audit(
            db,
            matter_id=matter_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action="party_created",
            object_type="matter_party",
            object_id=item.id,
        )
        return _model_payload(item)

    async def list_parties(
        self, db: AsyncSession, matter_id: str, tenant_id: str
    ) -> list[dict[str, Any]]:
        return await self._list(db, MatterParty, matter_id, tenant_id)

    async def create_account(
        self,
        db: AsyncSession,
        matter_id: str,
        tenant_id: str,
        actor_id: str,
        actor_role: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        await self._matter(db, matter_id, tenant_id)
        party_ids = _present_ids(
            data.get("creditor_party_id"),
            data.get("collector_party_id"),
            data.get("furnisher_party_id"),
            data.get("servicer_party_id"),
            data.get("assignee_party_id"),
        )
        await self._party_ids(db, matter_id, tenant_id, party_ids)
        item = MatterAccount(
            tenant_id=tenant_id,
            matter_id=matter_id,
            created_by=actor_id,
            account_type=data["account_type"],
            account_reference_redacted=redact_sensitive(data.get("account_reference")),
            creditor_party_id=data.get("creditor_party_id"),
            collector_party_id=data.get("collector_party_id"),
            furnisher_party_id=data.get("furnisher_party_id"),
            servicer_party_id=data.get("servicer_party_id"),
            assignee_party_id=data.get("assignee_party_id"),
            status=data.get("status", "open"),
            details_redacted=redact_sensitive(data.get("details", {})),
        )
        db.add(item)
        await db.flush()
        await self._write_audit(
            db,
            matter_id=matter_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action="account_created",
            object_type="matter_account",
            object_id=item.id,
        )
        return _model_payload(item)

    async def list_accounts(
        self, db: AsyncSession, matter_id: str, tenant_id: str
    ) -> list[dict[str, Any]]:
        return await self._list(db, MatterAccount, matter_id, tenant_id)

    async def create_filing(
        self,
        db: AsyncSession,
        matter_id: str,
        tenant_id: str,
        actor_id: str,
        actor_role: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        await self._matter(db, matter_id, tenant_id)
        await self._party_ids(db, matter_id, tenant_id, _present_ids(data.get("secured_party_id")))
        payload = redact_sensitive(data)
        item = MatterFiling(
            tenant_id=tenant_id,
            matter_id=matter_id,
            created_by=actor_id,
            filing_kind=payload["filing_kind"],
            filing_number_redacted=payload.get("filing_number"),
            filing_office=payload.get("filing_office"),
            filing_jurisdiction=payload.get("filing_jurisdiction"),
            filed_on=payload.get("filed_on"),
            debtor_name_redacted=payload.get("debtor_name"),
            secured_party_id=payload.get("secured_party_id"),
            status=payload.get("status", "reported"),
            details_redacted=payload.get("details", {}),
        )
        db.add(item)
        await db.flush()
        await self._write_audit(
            db,
            matter_id=matter_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action="filing_created",
            object_type="matter_filing",
            object_id=item.id,
        )
        return _model_payload(item)

    async def list_filings(
        self, db: AsyncSession, matter_id: str, tenant_id: str
    ) -> list[dict[str, Any]]:
        return await self._list(db, MatterFiling, matter_id, tenant_id)

    async def create_communication(
        self,
        db: AsyncSession,
        matter_id: str,
        tenant_id: str,
        actor_id: str,
        actor_role: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        await self._matter(db, matter_id, tenant_id)
        await self._party_ids(
            db,
            matter_id,
            tenant_id,
            _present_ids(data.get("sender_party_id"), data.get("recipient_party_id")),
        )
        payload = redact_sensitive(data)
        item = MatterCommunication(
            tenant_id=tenant_id,
            matter_id=matter_id,
            created_by=actor_id,
            communication_type=payload["communication_type"],
            direction=payload["direction"],
            occurred_at=payload["occurred_at"],
            sender_party_id=payload.get("sender_party_id"),
            recipient_party_id=payload.get("recipient_party_id"),
            subject_redacted=payload.get("subject"),
            content_redacted=payload.get("content"),
            source_document_id=payload.get("source_document_id"),
        )
        db.add(item)
        await db.flush()
        await self._write_audit(
            db,
            matter_id=matter_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action="communication_created",
            object_type="matter_communication",
            object_id=item.id,
        )
        return _model_payload(item)

    async def list_communications(
        self, db: AsyncSession, matter_id: str, tenant_id: str
    ) -> list[dict[str, Any]]:
        return await self._list(db, MatterCommunication, matter_id, tenant_id)

    async def create_dispute(
        self,
        db: AsyncSession,
        matter_id: str,
        tenant_id: str,
        actor_id: str,
        actor_role: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        await self._matter(db, matter_id, tenant_id)
        if data.get("account_id"):
            await self._account(db, data["account_id"], matter_id, tenant_id)
        payload = redact_sensitive(data)
        item = MatterDispute(
            tenant_id=tenant_id,
            matter_id=matter_id,
            created_by=actor_id,
            account_id=payload.get("account_id"),
            dispute_type=payload["dispute_type"],
            status=payload.get("status", "open"),
            submitted_on=payload.get("submitted_on"),
            responded_on=payload.get("responded_on"),
            summary_redacted=payload["summary"],
            details_redacted=payload.get("details", {}),
        )
        db.add(item)
        await db.flush()
        await self._write_audit(
            db,
            matter_id=matter_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action="dispute_created",
            object_type="matter_dispute",
            object_id=item.id,
        )
        return _model_payload(item)

    async def list_disputes(
        self, db: AsyncSession, matter_id: str, tenant_id: str
    ) -> list[dict[str, Any]]:
        return await self._list(db, MatterDispute, matter_id, tenant_id)

    async def create_attachment(
        self,
        db: AsyncSession,
        matter_id: str,
        tenant_id: str,
        actor_id: str,
        actor_role: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        await self._matter(db, matter_id, tenant_id)
        payload = redact_sensitive(data)
        item = MatterAttachment(
            tenant_id=tenant_id,
            matter_id=matter_id,
            uploaded_by=actor_id,
            document_id=payload.get("document_id"),
            label_redacted=payload["label"],
            attachment_kind=payload["attachment_kind"],
            checksum_sha256=payload.get("checksum_sha256"),
            classification=payload.get("classification", "UNCLASSIFIED"),
            redaction_status=payload.get("redaction_status", "REDACTION_REQUIRED"),
            metadata_redacted=payload.get("metadata", {}),
        )
        db.add(item)
        await db.flush()
        await self._write_audit(
            db,
            matter_id=matter_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action="attachment_registered",
            object_type="matter_attachment",
            object_id=item.id,
        )
        return _model_payload(item)

    async def list_attachments(
        self, db: AsyncSession, matter_id: str, tenant_id: str
    ) -> list[dict[str, Any]]:
        return await self._list(db, MatterAttachment, matter_id, tenant_id)

    async def create_assessment(
        self,
        db: AsyncSession,
        matter_id: str,
        tenant_id: str,
        actor_id: str,
        actor_role: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        await self._matter(db, matter_id, tenant_id)
        payload = redact_sensitive(data)
        assessment = MatterAssessment(
            tenant_id=tenant_id,
            matter_id=matter_id,
            created_by=actor_id,
            assessment_type=payload["assessment_type"],
            title=payload["title"],
        )
        db.add(assessment)
        await db.flush()
        version = MatterAssessmentVersion(
            tenant_id=tenant_id,
            matter_id=matter_id,
            assessment_id=assessment.id,
            version_number=1,
            facts_redacted=payload.get("facts", {}),
            conclusions_redacted=payload.get("conclusions", {}),
            limitations=payload.get("limitations", []),
            created_by=actor_id,
        )
        db.add(version)
        await db.flush()
        await self._write_audit(
            db,
            matter_id=matter_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action="assessment_created",
            object_type="matter_assessment",
            object_id=assessment.id,
            details={"version": 1},
        )
        return {"assessment": _model_payload(assessment), "version": _model_payload(version)}

    async def list_assessments(
        self, db: AsyncSession, matter_id: str, tenant_id: str
    ) -> list[dict[str, Any]]:
        await self._matter(db, matter_id, tenant_id)
        result = await db.execute(
            select(MatterAssessment)
            .where(
                MatterAssessment.matter_id == matter_id,
                MatterAssessment.tenant_id == tenant_id,
                MatterAssessment.deleted_at.is_(None),
            )
            .order_by(MatterAssessment.created_at.desc())
        )
        return [_model_payload(item) for item in result.scalars().all()]

    async def add_assessment_version(
        self,
        db: AsyncSession,
        assessment_id: str,
        matter_id: str,
        tenant_id: str,
        actor_id: str,
        actor_role: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        await self._matter(db, matter_id, tenant_id)
        result = await db.execute(
            select(MatterAssessment).where(
                MatterAssessment.id == assessment_id,
                MatterAssessment.matter_id == matter_id,
                MatterAssessment.tenant_id == tenant_id,
                MatterAssessment.deleted_at.is_(None),
            )
        )
        assessment = result.scalar_one_or_none()
        if assessment is None:
            raise MatterIntelligenceError("assessment not found")
        version_number = (
            await db.scalar(
                select(func.max(MatterAssessmentVersion.version_number)).where(
                    MatterAssessmentVersion.assessment_id == assessment_id
                )
            )
        ) or 0
        payload = redact_sensitive(data)
        version = MatterAssessmentVersion(
            tenant_id=tenant_id,
            matter_id=matter_id,
            assessment_id=assessment_id,
            version_number=version_number + 1,
            facts_redacted=payload.get("facts", {}),
            conclusions_redacted=payload.get("conclusions", {}),
            limitations=payload.get("limitations", []),
            created_by=actor_id,
        )
        assessment.current_version = version.version_number
        assessment.review_status = "NOT_SUBMITTED"
        assessment.reviewer_role = None
        assessment.reviewer_identity = None
        assessment.review_notes = None
        assessment.reviewed_at = None
        db.add(version)
        await db.flush()
        await self._write_audit(
            db,
            matter_id=matter_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action="assessment_version_created",
            object_type="matter_assessment_version",
            object_id=version.id,
            details={"assessment_id": assessment_id, "version": version.version_number},
        )
        return _model_payload(version)

    async def list_assessment_versions(
        self, db: AsyncSession, assessment_id: str, matter_id: str, tenant_id: str
    ) -> list[dict[str, Any]]:
        await self._matter(db, matter_id, tenant_id)
        result = await db.execute(
            select(MatterAssessmentVersion)
            .where(
                MatterAssessmentVersion.assessment_id == assessment_id,
                MatterAssessmentVersion.matter_id == matter_id,
                MatterAssessmentVersion.tenant_id == tenant_id,
            )
            .order_by(MatterAssessmentVersion.version_number.desc())
        )
        return [_model_payload(item) for item in result.scalars().all()]

    async def review_assessment(
        self,
        db: AsyncSession,
        assessment_id: str,
        matter_id: str,
        tenant_id: str,
        actor_id: str,
        actor_role: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        await self._matter(db, matter_id, tenant_id)
        result = await db.execute(
            select(MatterAssessment).where(
                MatterAssessment.id == assessment_id,
                MatterAssessment.matter_id == matter_id,
                MatterAssessment.tenant_id == tenant_id,
                MatterAssessment.deleted_at.is_(None),
            )
        )
        assessment = result.scalar_one_or_none()
        if assessment is None:
            raise MatterIntelligenceError("assessment not found")
        if (
            data["review_status"] == "APPROVED"
            and assessment.assessment_type.lower() in {"tax", "accounting"}
            and actor_role != "ACCOUNTANT"
        ):
            raise MatterIntelligenceError(
                "tax and accounting assessments require accountant review"
            )
        if (
            data["review_status"] == "APPROVED"
            and assessment.assessment_type.lower() not in {"tax", "accounting"}
            and actor_role != "ATTORNEY"
        ):
            raise MatterIntelligenceError("legal assessments require attorney review")
        assessment.review_status = data["review_status"]
        assessment.reviewer_role = actor_role
        assessment.reviewer_identity = actor_id
        assessment.review_notes = redact_sensitive(data["notes"])
        assessment.reviewed_at = datetime.now(UTC)
        await db.flush()
        await self._write_audit(
            db,
            matter_id=matter_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action="assessment_reviewed",
            object_type="matter_assessment",
            object_id=assessment.id,
            details={"review_status": assessment.review_status},
        )
        return _model_payload(assessment)

    async def audit_events(
        self, db: AsyncSession, matter_id: str, tenant_id: str
    ) -> list[dict[str, Any]]:
        await self._matter(db, matter_id, tenant_id)
        result = await db.execute(
            select(MatterAuditEvent)
            .where(MatterAuditEvent.matter_id == matter_id, MatterAuditEvent.tenant_id == tenant_id)
            .order_by(MatterAuditEvent.created_at.desc())
        )
        return [_model_payload(item) for item in result.scalars().all()]
