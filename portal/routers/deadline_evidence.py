"""Authenticated deadline and evidence graph routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.rbac import CurrentUser, Permission, require_permissions
from ..database import get_db
from ..schemas.deadline_evidence import (
    MatterDeadlineCalculate,
    MatterDeadlineCreate,
    MatterEvidenceLinkCreate,
    MatterEvidenceNodeCreate,
    MatterEvidenceReview,
)
from ..services.deadline_evidence_service import DeadlineEvidenceService
from ..services.matter_intelligence_service import MatterIntelligenceError

router = APIRouter(prefix="/api/v1/matters", tags=["matter-deadlines-evidence"])
service = DeadlineEvidenceService()


def _read() -> CurrentUser:
    return Depends(require_permissions(Permission.MATTER_INTELLIGENCE_READ))


def _write() -> CurrentUser:
    return Depends(require_permissions(Permission.MATTER_INTELLIGENCE_WRITE))


def _review() -> CurrentUser:
    return Depends(require_permissions(Permission.MATTER_INTELLIGENCE_REVIEW))


def _error(exc: MatterIntelligenceError) -> HTTPException:
    status = 404 if "not found" in str(exc) else 422
    return HTTPException(status_code=status, detail=str(exc))


@router.post("/{matter_id}/intelligence/deadlines")
async def create_deadline(
    matter_id: str,
    data: MatterDeadlineCreate,
    current_user: CurrentUser = _write(),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.create_deadline(
            db,
            matter_id,
            current_user.tenant_id,
            current_user.user_id,
            current_user.role.value,
            data.model_dump(),
        )
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.post("/{matter_id}/intelligence/deadlines/calculate")
async def calculate_deadline(
    matter_id: str,
    data: MatterDeadlineCalculate,
    current_user: CurrentUser = _write(),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.calculate_and_create_deadline(
            db,
            matter_id,
            current_user.tenant_id,
            current_user.user_id,
            current_user.role.value,
            data.model_dump(),
        )
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.get("/{matter_id}/intelligence/deadlines")
async def list_deadlines(
    matter_id: str, current_user: CurrentUser = _read(), db: AsyncSession = Depends(get_db)
):
    try:
        return {"items": await service.list_deadlines(db, matter_id, current_user.tenant_id)}
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.post("/{matter_id}/intelligence/deadlines/{deadline_id}/versions")
async def add_deadline_version(
    matter_id: str,
    deadline_id: str,
    data: MatterDeadlineCreate,
    current_user: CurrentUser = _write(),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.add_deadline_version(
            db,
            deadline_id,
            matter_id,
            current_user.tenant_id,
            current_user.user_id,
            current_user.role.value,
            data.model_dump(),
        )
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.get("/{matter_id}/intelligence/deadlines/{deadline_id}/versions")
async def list_deadline_versions(
    matter_id: str,
    deadline_id: str,
    current_user: CurrentUser = _read(),
    db: AsyncSession = Depends(get_db),
):
    try:
        return {
            "items": await service.list_deadline_versions(
                db, deadline_id, matter_id, current_user.tenant_id
            )
        }
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.post("/{matter_id}/intelligence/evidence/nodes")
async def create_evidence_node(
    matter_id: str,
    data: MatterEvidenceNodeCreate,
    current_user: CurrentUser = _write(),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.create_evidence_node(
            db,
            matter_id,
            current_user.tenant_id,
            current_user.user_id,
            current_user.role.value,
            data.model_dump(),
        )
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.get("/{matter_id}/intelligence/evidence/nodes")
async def list_evidence_nodes(
    matter_id: str, current_user: CurrentUser = _read(), db: AsyncSession = Depends(get_db)
):
    try:
        return {"items": await service.list_evidence_nodes(db, matter_id, current_user.tenant_id)}
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.post("/{matter_id}/intelligence/evidence/links")
async def create_evidence_link(
    matter_id: str,
    data: MatterEvidenceLinkCreate,
    current_user: CurrentUser = _write(),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.create_evidence_link(
            db,
            matter_id,
            current_user.tenant_id,
            current_user.user_id,
            current_user.role.value,
            data.model_dump(),
        )
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.get("/{matter_id}/intelligence/evidence/links")
async def list_evidence_links(
    matter_id: str, current_user: CurrentUser = _read(), db: AsyncSession = Depends(get_db)
):
    try:
        return {"items": await service.list_evidence_links(db, matter_id, current_user.tenant_id)}
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.get("/{matter_id}/intelligence/evidence/findings")
async def list_evidence_findings(
    matter_id: str, current_user: CurrentUser = _read(), db: AsyncSession = Depends(get_db)
):
    try:
        return {
            "items": await service.list_evidence_findings(db, matter_id, current_user.tenant_id)
        }
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.post("/{matter_id}/intelligence/evidence/nodes/{node_id}/review")
async def review_evidence_node(
    matter_id: str,
    node_id: str,
    data: MatterEvidenceReview,
    current_user: CurrentUser = _review(),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.review_evidence_node(
            db,
            node_id,
            matter_id,
            current_user.tenant_id,
            current_user.user_id,
            current_user.role.value,
            data.model_dump(),
        )
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc
