"""
Persistence service for the Blackstone Evidence Ledger and evaluations.

Provides async CRUD helpers that integrate with the portal's async SQLAlchemy
session. Designed to be called from routers and background tasks.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portal.models.blackstone import BlackstoneEvaluation, EvidenceLedger


class EvidenceLedgerService:


    @staticmethod
    async def record(
        db: AsyncSession,
        object_type: str,
        object_id: str,
        action: str,
        actor: str,
        payload: dict[str, Any],
        parent_id: str | None = None,
        provenance_hash: str | None = None,
        tenant_id: str | None = None,
    ) -> EvidenceLedger:
        entry = EvidenceLedger(
            tenant_id=tenant_id,
            object_type=object_type,
            object_id=object_id,
            action=action,
            actor=actor,
            payload=payload,
            parent_id=parent_id,
            provenance_hash=provenance_hash,
        )
        db.add(entry)
        await db.flush()
        return entry

    @staticmethod
    async def get_chain(
        db: AsyncSession,
        object_type: str,
        object_id: str,
        tenant_id: str | None = None,
    ) -> list[EvidenceLedger]:
        stmt = select(EvidenceLedger).where(
            EvidenceLedger.object_type == object_type,
            EvidenceLedger.object_id == object_id,
        )
        if tenant_id:
            stmt = stmt.where(EvidenceLedger.tenant_id == tenant_id)
        stmt = stmt.order_by(EvidenceLedger.recorded_at.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())


class BlackstoneEvaluationService:
    """Persist and retrieve Blackstone evaluation snapshots."""

    @staticmethod
    async def save(
        db: AsyncSession,
        claim_id: str,
        evaluation: dict[str, Any],
        case_id: str | None = None,
        tenant_id: str | None = None,
        evaluated_by: str = "AGENT-BLACKSTONE-2-0",
    ) -> BlackstoneEvaluation:
        rec = evaluation["recommendation"]
        auth = evaluation["authority"]
        snapshot = BlackstoneEvaluation(
            tenant_id=tenant_id,
            case_id=case_id,
            claim_id=claim_id,
            question=rec.get("question"),
            status=evaluation["claim"]["status"],
            confidence=evaluation["claim"]["confidence"],
            recommendation=rec["recommendation"],
            rationale=rec["rationale"],
            controlling_authority=auth.get("controlling_authority"),
            conflicts=auth.get("conflicts", []),
            risks=evaluation.get("risks", []),
            agents=rec.get("agents", []),
            evaluated_by=evaluated_by,
        )
        db.add(snapshot)
        await db.flush()
        return snapshot

    @staticmethod
    async def get_latest(
        db: AsyncSession,
        claim_id: str,
        tenant_id: str | None = None,
    ) -> BlackstoneEvaluation | None:
        stmt = select(BlackstoneEvaluation).where(
            BlackstoneEvaluation.claim_id == claim_id,
        )
        if tenant_id:
            stmt = stmt.where(BlackstoneEvaluation.tenant_id == tenant_id)
        stmt = stmt.order_by(BlackstoneEvaluation.evaluated_at.desc()).limit(1)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_case(
        db: AsyncSession,
        case_id: str,
        tenant_id: str | None = None,
    ) -> list[BlackstoneEvaluation]:
        stmt = select(BlackstoneEvaluation).where(
            BlackstoneEvaluation.case_id == case_id,
        )
        if tenant_id:
            stmt = stmt.where(BlackstoneEvaluation.tenant_id == tenant_id)
        stmt = stmt.order_by(BlackstoneEvaluation.evaluated_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())
