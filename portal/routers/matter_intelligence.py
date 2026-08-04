"""Controlled tenant-scoped persistent matter-intelligence API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.rbac import CurrentUser, Permission, require_permissions
from ..database import get_db
from ..schemas.matter_intelligence import (
    MatterAccountCreate,
    MatterAssessmentCreate,
    MatterAssessmentReviewCreate,
    MatterAssessmentVersionCreate,
    MatterAttachmentCreate,
    MatterCommunicationCreate,
    MatterDisputeCreate,
    MatterFilingCreate,
    MatterPartyCreate,
)
from ..services.matter_intelligence_service import (
    MatterIntelligenceError,
    MatterIntelligenceService,
)

router = APIRouter(prefix="/api/v1/matters", tags=["matter-intelligence"])
service = MatterIntelligenceService()


def _error(exc: MatterIntelligenceError) -> HTTPException:
    if str(exc) in {"matter not found", "account not found", "assessment not found"}:
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=422, detail=str(exc))


@router.post("/{matter_id}/intelligence/parties", status_code=status.HTTP_201_CREATED)
async def create_party(
    matter_id: str,
    body: MatterPartyCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.MATTER_INTELLIGENCE_WRITE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.create_party(
            db,
            matter_id,
            current_user.tenant_id,
            current_user.user_id,
            current_user.role.value,
            body.model_dump(),
        )
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.get("/{matter_id}/intelligence/parties")
async def list_parties(
    matter_id: str,
    current_user: CurrentUser = Depends(require_permissions(Permission.MATTER_INTELLIGENCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.list_parties(db, matter_id, current_user.tenant_id)
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.post("/{matter_id}/intelligence/accounts", status_code=status.HTTP_201_CREATED)
async def create_account(
    matter_id: str,
    body: MatterAccountCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.MATTER_INTELLIGENCE_WRITE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.create_account(
            db,
            matter_id,
            current_user.tenant_id,
            current_user.user_id,
            current_user.role.value,
            body.model_dump(),
        )
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.get("/{matter_id}/intelligence/accounts")
async def list_accounts(
    matter_id: str,
    current_user: CurrentUser = Depends(require_permissions(Permission.MATTER_INTELLIGENCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.list_accounts(db, matter_id, current_user.tenant_id)
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.post("/{matter_id}/intelligence/filings", status_code=status.HTTP_201_CREATED)
async def create_filing(
    matter_id: str,
    body: MatterFilingCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.MATTER_INTELLIGENCE_WRITE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.create_filing(
            db,
            matter_id,
            current_user.tenant_id,
            current_user.user_id,
            current_user.role.value,
            body.model_dump(),
        )
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.get("/{matter_id}/intelligence/filings")
async def list_filings(
    matter_id: str,
    current_user: CurrentUser = Depends(require_permissions(Permission.MATTER_INTELLIGENCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.list_filings(db, matter_id, current_user.tenant_id)
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.post("/{matter_id}/intelligence/communications", status_code=status.HTTP_201_CREATED)
async def create_communication(
    matter_id: str,
    body: MatterCommunicationCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.MATTER_INTELLIGENCE_WRITE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.create_communication(
            db,
            matter_id,
            current_user.tenant_id,
            current_user.user_id,
            current_user.role.value,
            body.model_dump(),
        )
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.get("/{matter_id}/intelligence/communications")
async def list_communications(
    matter_id: str,
    current_user: CurrentUser = Depends(require_permissions(Permission.MATTER_INTELLIGENCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.list_communications(db, matter_id, current_user.tenant_id)
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.post("/{matter_id}/intelligence/disputes", status_code=status.HTTP_201_CREATED)
async def create_dispute(
    matter_id: str,
    body: MatterDisputeCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.MATTER_INTELLIGENCE_WRITE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.create_dispute(
            db,
            matter_id,
            current_user.tenant_id,
            current_user.user_id,
            current_user.role.value,
            body.model_dump(),
        )
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.get("/{matter_id}/intelligence/disputes")
async def list_disputes(
    matter_id: str,
    current_user: CurrentUser = Depends(require_permissions(Permission.MATTER_INTELLIGENCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.list_disputes(db, matter_id, current_user.tenant_id)
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.post("/{matter_id}/intelligence/attachments", status_code=status.HTTP_201_CREATED)
async def register_attachment(
    matter_id: str,
    body: MatterAttachmentCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.MATTER_INTELLIGENCE_WRITE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.create_attachment(
            db,
            matter_id,
            current_user.tenant_id,
            current_user.user_id,
            current_user.role.value,
            body.model_dump(),
        )
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.get("/{matter_id}/intelligence/attachments")
async def list_attachments(
    matter_id: str,
    current_user: CurrentUser = Depends(require_permissions(Permission.MATTER_INTELLIGENCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.list_attachments(db, matter_id, current_user.tenant_id)
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.post("/{matter_id}/intelligence/assessments", status_code=status.HTTP_201_CREATED)
async def create_assessment(
    matter_id: str,
    body: MatterAssessmentCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.MATTER_INTELLIGENCE_WRITE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.create_assessment(
            db,
            matter_id,
            current_user.tenant_id,
            current_user.user_id,
            current_user.role.value,
            body.model_dump(),
        )
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.get("/{matter_id}/intelligence/assessments")
async def list_assessments(
    matter_id: str,
    current_user: CurrentUser = Depends(require_permissions(Permission.MATTER_INTELLIGENCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.list_assessments(db, matter_id, current_user.tenant_id)
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.post(
    "/{matter_id}/intelligence/assessments/{assessment_id}/versions",
    status_code=status.HTTP_201_CREATED,
)
async def add_assessment_version(
    matter_id: str,
    assessment_id: str,
    body: MatterAssessmentVersionCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.MATTER_INTELLIGENCE_WRITE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.add_assessment_version(
            db,
            assessment_id,
            matter_id,
            current_user.tenant_id,
            current_user.user_id,
            current_user.role.value,
            body.model_dump(),
        )
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.get("/{matter_id}/intelligence/assessments/{assessment_id}/versions")
async def list_assessment_versions(
    matter_id: str,
    assessment_id: str,
    current_user: CurrentUser = Depends(require_permissions(Permission.MATTER_INTELLIGENCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.list_assessment_versions(
            db, assessment_id, matter_id, current_user.tenant_id
        )
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.post("/{matter_id}/intelligence/assessments/{assessment_id}/review")
async def review_assessment(
    matter_id: str,
    assessment_id: str,
    body: MatterAssessmentReviewCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.MATTER_INTELLIGENCE_REVIEW)),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.review_assessment(
            db,
            assessment_id,
            matter_id,
            current_user.tenant_id,
            current_user.user_id,
            current_user.role.value,
            body.model_dump(),
        )
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc


@router.get("/{matter_id}/intelligence/audit-events")
async def list_audit_events(
    matter_id: str,
    current_user: CurrentUser = Depends(require_permissions(Permission.MATTER_INTELLIGENCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.audit_events(db, matter_id, current_user.tenant_id)
    except MatterIntelligenceError as exc:
        raise _error(exc) from exc
