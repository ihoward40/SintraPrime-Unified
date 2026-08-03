"""Deadline calculation and evidence-graph service for persistent matters."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.deadline_evidence import (
    MatterDeadline,
    MatterDeadlineVersion,
    MatterEvidenceFinding,
    MatterEvidenceLink,
    MatterEvidenceNode,
)
from .matter_intelligence_service import (
    MatterIntelligenceError,
    MatterIntelligenceService,
    _model_payload,
    redact_sensitive,
)


class DeadlineEvidenceService(MatterIntelligenceService):
    """Persists versioned deadlines and append-only evidence graph facts."""

    @staticmethod
    def _zone(name: str) -> ZoneInfo:
        try:
            return ZoneInfo(name)
        except ZoneInfoNotFoundError as exc:
            raise MatterIntelligenceError("unknown timezone") from exc

    @staticmethod
    def _advance_business_days(value: datetime, days: int, holidays: set[str]) -> datetime:
        current = value
        remaining = days
        while remaining:
            current += timedelta(days=1)
            if current.weekday() < 5 and current.date().isoformat() not in holidays:
                remaining -= 1
        return current

    @classmethod
    def calculate_due_at(
        cls,
        trigger_at: datetime,
        *,
        timezone_name: str,
        calendar_type: str,
        days_count: int,
        mailing_days: int = 0,
        holidays: list[str] | None = None,
    ) -> datetime:
        if trigger_at.tzinfo is None or trigger_at.utcoffset() is None:
            raise MatterIntelligenceError("trigger_at must include a timezone")
        if days_count < 0 or mailing_days < 0:
            raise MatterIntelligenceError("deadline day counts cannot be negative")
        zone = cls._zone(timezone_name)
        current = trigger_at.astimezone(zone)
        holiday_set = set(holidays or [])
        if calendar_type == "BUSINESS_DAYS":
            current = cls._advance_business_days(current, days_count + mailing_days, holiday_set)
        elif calendar_type == "CALENDAR_DAYS":
            current += timedelta(days=days_count + mailing_days)
        else:
            raise MatterIntelligenceError("unsupported calendar type")
        return current

    async def _node(
        self, db: AsyncSession, node_id: str, matter_id: str, tenant_id: str
    ) -> MatterEvidenceNode:
        result = await db.execute(
            select(MatterEvidenceNode).where(
                MatterEvidenceNode.id == node_id,
                MatterEvidenceNode.matter_id == matter_id,
                MatterEvidenceNode.tenant_id == tenant_id,
                MatterEvidenceNode.deleted_at.is_(None),
            )
        )
        node = result.scalar_one_or_none()
        if node is None:
            raise MatterIntelligenceError("evidence node not found")
        return node

    async def create_deadline(
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
        item = MatterDeadline(
            tenant_id=tenant_id,
            matter_id=matter_id,
            created_by=actor_id,
            title=payload["title"],
            deadline_type=payload["deadline_type"],
            source_kind=payload["source_kind"],
            trigger_at=payload.get("trigger_at"),
            due_at=payload.get("due_at"),
            timezone_name=payload["timezone_name"],
            calendar_type=payload["calendar_type"],
            calculation_status=payload["calculation_status"],
            calculation_rule_id=payload.get("calculation_rule_id"),
            authority_ids=payload.get("authority_ids", []),
            trigger_basis_redacted=payload.get("trigger_basis", {}),
            assumptions=payload.get("assumptions", []),
            limitations=payload.get("limitations", []),
        )
        db.add(item)
        await db.flush()
        version = MatterDeadlineVersion(
            tenant_id=tenant_id,
            matter_id=matter_id,
            deadline_id=item.id,
            version_number=1,
            trigger_at=item.trigger_at,
            due_at=item.due_at,
            calculation_status=item.calculation_status,
            calculation_inputs_redacted={
                "days_count": payload.get("days_count"),
                "mailing_days": payload.get("mailing_days", 0),
                "holidays": payload.get("holidays", []),
            },
            assumptions=item.assumptions,
            limitations=item.limitations,
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
            action="deadline_created",
            object_type="matter_deadline",
            object_id=item.id,
        )
        return {"deadline": _model_payload(item), "version": _model_payload(version)}

    async def calculate_and_create_deadline(
        self,
        db: AsyncSession,
        matter_id: str,
        tenant_id: str,
        actor_id: str,
        actor_role: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        payload = dict(data)
        due_at = self.calculate_due_at(
            payload["trigger_at"],
            timezone_name=payload["timezone_name"],
            calendar_type=payload["calendar_type"],
            days_count=payload["days_count"],
            mailing_days=payload.get("mailing_days", 0),
            holidays=payload.get("holidays", []),
        )
        payload["due_at"] = due_at
        payload["calculation_status"] = "CALCULATED"
        return await self.create_deadline(db, matter_id, tenant_id, actor_id, actor_role, payload)

    async def list_deadlines(
        self, db: AsyncSession, matter_id: str, tenant_id: str
    ) -> list[dict[str, Any]]:
        return await self._list(db, MatterDeadline, matter_id, tenant_id)

    async def add_deadline_version(
        self,
        db: AsyncSession,
        deadline_id: str,
        matter_id: str,
        tenant_id: str,
        actor_id: str,
        actor_role: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        await self._matter(db, matter_id, tenant_id)
        result = await db.execute(
            select(MatterDeadline).where(
                MatterDeadline.id == deadline_id,
                MatterDeadline.matter_id == matter_id,
                MatterDeadline.tenant_id == tenant_id,
                MatterDeadline.deleted_at.is_(None),
            )
        )
        deadline = result.scalar_one_or_none()
        if deadline is None:
            raise MatterIntelligenceError("deadline not found")
        latest = (
            await db.scalar(
                select(MatterDeadlineVersion.version_number)
                .where(MatterDeadlineVersion.deadline_id == deadline_id)
                .order_by(MatterDeadlineVersion.version_number.desc())
                .limit(1)
            )
            or 0
        )
        payload = redact_sensitive(data)
        version = MatterDeadlineVersion(
            tenant_id=tenant_id,
            matter_id=matter_id,
            deadline_id=deadline_id,
            version_number=latest + 1,
            trigger_at=payload.get("trigger_at"),
            due_at=payload.get("due_at"),
            calculation_status=payload["calculation_status"],
            calculation_inputs_redacted=payload.get("calculation_inputs", {}),
            assumptions=payload.get("assumptions", []),
            limitations=payload.get("limitations", []),
            created_by=actor_id,
        )
        deadline.trigger_at = version.trigger_at
        deadline.due_at = version.due_at
        deadline.calculation_status = version.calculation_status
        deadline.assumptions = version.assumptions
        deadline.limitations = version.limitations
        deadline.current_version = version.version_number
        db.add(version)
        await db.flush()
        await self._write_audit(
            db,
            matter_id=matter_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action="deadline_version_created",
            object_type="matter_deadline_version",
            object_id=version.id,
            details={"deadline_id": deadline_id, "version": version.version_number},
        )
        return _model_payload(version)

    async def list_deadline_versions(
        self, db: AsyncSession, deadline_id: str, matter_id: str, tenant_id: str
    ) -> list[dict[str, Any]]:
        await self._matter(db, matter_id, tenant_id)
        result = await db.execute(
            select(MatterDeadlineVersion)
            .where(
                MatterDeadlineVersion.deadline_id == deadline_id,
                MatterDeadlineVersion.matter_id == matter_id,
                MatterDeadlineVersion.tenant_id == tenant_id,
            )
            .order_by(MatterDeadlineVersion.version_number.desc())
        )
        return [_model_payload(item) for item in result.scalars().all()]

    async def create_evidence_node(
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
        node = MatterEvidenceNode(
            tenant_id=tenant_id,
            matter_id=matter_id,
            created_by=actor_id,
            node_type=payload["node_type"],
            title=payload["title"],
            statement_redacted=payload.get("statement"),
            evidence_status=payload["evidence_status"],
            source_document_id=payload.get("source_document_id"),
            source_authority_id=payload.get("source_authority_id"),
            source_rule_id=payload.get("source_rule_id"),
            provenance_redacted=payload.get("provenance", {}),
        )
        db.add(node)
        await db.flush()
        if node.evidence_status == "MISSING":
            await self._finding(
                db,
                matter_id,
                tenant_id,
                actor_id,
                "MISSING_EVIDENCE",
                node.id,
                None,
                "Required evidence is missing",
            )
        await self._write_audit(
            db,
            matter_id=matter_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action="evidence_node_created",
            object_type="matter_evidence_node",
            object_id=node.id,
        )
        return _model_payload(node)

    async def list_evidence_nodes(
        self, db: AsyncSession, matter_id: str, tenant_id: str
    ) -> list[dict[str, Any]]:
        return await self._list(db, MatterEvidenceNode, matter_id, tenant_id)

    async def _finding(
        self,
        db: AsyncSession,
        matter_id: str,
        tenant_id: str,
        actor_id: str,
        finding_type: str,
        node_id: str | None,
        related_node_id: str | None,
        summary: str,
    ) -> None:
        db.add(
            MatterEvidenceFinding(
                tenant_id=tenant_id,
                matter_id=matter_id,
                created_by=actor_id,
                finding_type=finding_type,
                node_id=node_id,
                related_node_id=related_node_id,
                summary_redacted=redact_sensitive(summary),
            )
        )
        await db.flush()

    async def create_evidence_link(
        self,
        db: AsyncSession,
        matter_id: str,
        tenant_id: str,
        actor_id: str,
        actor_role: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        await self._matter(db, matter_id, tenant_id)
        if data["source_node_id"] == data["target_node_id"]:
            raise MatterIntelligenceError("evidence link cannot self-reference")
        await self._node(db, data["source_node_id"], matter_id, tenant_id)
        await self._node(db, data["target_node_id"], matter_id, tenant_id)
        payload = redact_sensitive(data)
        link = MatterEvidenceLink(
            tenant_id=tenant_id,
            matter_id=matter_id,
            source_node_id=payload["source_node_id"],
            target_node_id=payload["target_node_id"],
            relationship_type=payload["relationship_type"],
            confidence=payload["confidence"],
            notes_redacted=payload.get("notes"),
            created_by=actor_id,
        )
        db.add(link)
        await db.flush()
        if link.relationship_type == "CONTRADICTS":
            await self._finding(
                db,
                matter_id,
                tenant_id,
                actor_id,
                "CONTRADICTORY_EVIDENCE",
                link.source_node_id,
                link.target_node_id,
                "Evidence nodes contradict one another",
            )
        if link.relationship_type == "REQUIRES":
            target = await self._node(db, link.target_node_id, matter_id, tenant_id)
            if target.evidence_status == "MISSING":
                await self._finding(
                    db,
                    matter_id,
                    tenant_id,
                    actor_id,
                    "MISSING_EVIDENCE",
                    link.target_node_id,
                    link.source_node_id,
                    "Required evidence is missing",
                )
        await self._write_audit(
            db,
            matter_id=matter_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action="evidence_link_created",
            object_type="matter_evidence_link",
            object_id=link.id,
        )
        return _model_payload(link)

    async def list_evidence_links(
        self, db: AsyncSession, matter_id: str, tenant_id: str
    ) -> list[dict[str, Any]]:
        await self._matter(db, matter_id, tenant_id)
        result = await db.execute(
            select(MatterEvidenceLink)
            .where(
                MatterEvidenceLink.matter_id == matter_id, MatterEvidenceLink.tenant_id == tenant_id
            )
            .order_by(MatterEvidenceLink.created_at.desc())
        )
        return [_model_payload(item) for item in result.scalars().all()]

    async def list_evidence_findings(
        self, db: AsyncSession, matter_id: str, tenant_id: str
    ) -> list[dict[str, Any]]:
        await self._matter(db, matter_id, tenant_id)
        result = await db.execute(
            select(MatterEvidenceFinding)
            .where(
                MatterEvidenceFinding.matter_id == matter_id,
                MatterEvidenceFinding.tenant_id == tenant_id,
            )
            .order_by(MatterEvidenceFinding.created_at.desc())
        )
        return [_model_payload(item) for item in result.scalars().all()]

    async def review_evidence_node(
        self,
        db: AsyncSession,
        node_id: str,
        matter_id: str,
        tenant_id: str,
        actor_id: str,
        actor_role: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        node = await self._node(db, node_id, matter_id, tenant_id)
        if data["review_status"] == "APPROVED" and actor_role != "ATTORNEY":
            raise MatterIntelligenceError("evidence approval requires attorney review")
        node.review_status = data["review_status"]
        await db.flush()
        await self._write_audit(
            db,
            matter_id=matter_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action="evidence_node_reviewed",
            object_type="matter_evidence_node",
            object_id=node.id,
            details={"review_status": node.review_status},
        )
        return _model_payload(node)
