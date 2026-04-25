"""Case management router."""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.rbac import CurrentUser, Permission, require_permissions
from ..database import get_db
from ..models.case import Case, CaseDeadline, CaseEvent, CaseNote, CaseTask
from ..schemas.case import (
    CaseCreate, CaseDeadlineCreate, CaseDeadlineResponse, CaseEventCreate,
    CaseEventResponse, CaseListResponse, CaseNoteCreate, CaseNoteResponse,
    CaseResponse, CaseTaskCreate, CaseTaskResponse, CaseUpdate,
    ConflictCheckRequest, ConflictCheckResponse,
)
from ..services.audit_service import audit
from ..services.notification_service import notify_users

router = APIRouter()


def _generate_case_number(tenant_id: str, count: int) -> str:
    from datetime import datetime
    year = datetime.utcnow().year
    return f"CASE-{year}-{count:05d}"


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    body: CaseCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.CASE_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    count_q = await db.execute(
        select(func.count(Case.id)).where(Case.tenant_id == current_user.tenant_id)
    )
    count = (count_q.scalar() or 0) + 1
    case_number = _generate_case_number(current_user.tenant_id, count)

    body_dict = body.model_dump()
    case = Case(
        tenant_id=current_user.tenant_id,
        case_number=case_number,
        stage="intake",
        **body_dict,
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)

    await audit(db, action="case_create", user_id=current_user.user_id,
                tenant_id=current_user.tenant_id,
                resource_type="case", resource_id=str(case.id), resource_name=case.title)
    return CaseResponse.model_validate(case)


@router.get("", response_model=CaseListResponse)
async def list_cases(
    client_id: Optional[uuid.UUID] = Query(None),
    stage: Optional[str] = Query(None),
    attorney_id: Optional[uuid.UUID] = Query(None),
    practice_area: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    is_urgent: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_permissions(Permission.CASE_READ)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Case).where(
        Case.tenant_id == current_user.tenant_id,
        Case.deleted_at.is_(None),
    )
    if client_id:
        stmt = stmt.where(Case.client_id == client_id)
    if stage:
        stmt = stmt.where(Case.stage == stage)
    if attorney_id:
        stmt = stmt.where(Case.lead_attorney_id == attorney_id)
    if practice_area:
        stmt = stmt.where(Case.practice_area == practice_area)
    if is_urgent is not None:
        stmt = stmt.where(Case.is_urgent == is_urgent)
    if search:
        stmt = stmt.where(or_(
            Case.title.ilike(f"%{search}%"),
            Case.case_number.ilike(f"%{search}%"),
            Case.docket_number.ilike(f"%{search}%"),
            Case.opposing_party.ilike(f"%{search}%"),
        ))

    # CLIENT: only their cases
    if current_user.is_client():
        from ..models.client import Client
        client_result = await db.execute(
            select(Client.id).where(Client.portal_user_id == current_user.user_id)
        )
        client_ids = client_result.scalars().all()
        stmt = stmt.where(Case.client_id.in_(client_ids))

    total_q = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_q.scalar() or 0

    stmt = stmt.offset((page - 1) * page_size).limit(page_size).order_by(Case.created_at.desc())
    result = await db.execute(stmt)
    cases = result.scalars().all()

    return CaseListResponse(
        items=[CaseResponse.model_validate(c) for c in cases],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permissions(Permission.CASE_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Case).where(
            Case.id == case_id,
            Case.tenant_id == current_user.tenant_id,
            Case.deleted_at.is_(None),
        )
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Confidential case: only assigned attorneys can see
    if case.is_confidential and not current_user.is_staff():
        if current_user.user_id not in (case.assigned_staff or []) and \
           str(case.lead_attorney_id) != current_user.user_id:
            raise HTTPException(status_code=403, detail="Access denied: confidential case")

    return CaseResponse.model_validate(case)


@router.put("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: uuid.UUID,
    body: CaseUpdate,
    current_user: CurrentUser = Depends(require_permissions(Permission.CASE_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Case).where(
            Case.id == case_id,
            Case.tenant_id == current_user.tenant_id,
            Case.deleted_at.is_(None),
        )
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404)

    old_stage = case.stage
    for field, value in body.model_dump(exclude_none=True).items():
        if field == "assigned_staff":
            setattr(case, field, [str(v) for v in value])
        else:
            setattr(case, field, value)

    await db.commit()
    await db.refresh(case)

    # Notify on stage change
    if body.stage and body.stage != old_stage:
        await notify_users(
            db=db,
            tenant_id=current_user.tenant_id,
            event_type="case_stage_changed",
            resource_id=str(case.id),
            resource_name=case.title,
            actor_id=current_user.user_id,
            details={"old_stage": old_stage, "new_stage": body.stage},
        )

    await audit(db, action="case_update", user_id=current_user.user_id,
                tenant_id=current_user.tenant_id,
                resource_type="case", resource_id=str(case.id))
    return CaseResponse.model_validate(case)


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permissions(Permission.CASE_DELETE)),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone
    result = await db.execute(
        select(Case).where(Case.id == case_id, Case.tenant_id == current_user.tenant_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404)
    case.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    await audit(db, action="case_delete", user_id=current_user.user_id,
                tenant_id=current_user.tenant_id, resource_type="case", resource_id=str(case_id))


# ── Events ────────────────────────────────────────────────────────────────────

@router.post("/{case_id}/events", response_model=CaseEventResponse, status_code=201)
async def add_case_event(
    case_id: uuid.UUID,
    body: CaseEventCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.CASE_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    event = CaseEvent(
        case_id=case_id,
        tenant_id=current_user.tenant_id,
        created_by=current_user.user_id,
        **body.model_dump(),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return CaseEventResponse.model_validate(event)


@router.get("/{case_id}/events", response_model=List[CaseEventResponse])
async def list_case_events(
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permissions(Permission.CASE_READ)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CaseEvent).where(CaseEvent.case_id == case_id)
    if current_user.is_client():
        stmt = stmt.where(CaseEvent.is_client_visible == True)
    result = await db.execute(stmt.order_by(CaseEvent.event_date.desc()))
    return [CaseEventResponse.model_validate(e) for e in result.scalars().all()]


# ── Deadlines ─────────────────────────────────────────────────────────────────

@router.post("/{case_id}/deadlines", response_model=CaseDeadlineResponse, status_code=201)
async def add_deadline(
    case_id: uuid.UUID,
    body: CaseDeadlineCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.CASE_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    deadline = CaseDeadline(
        case_id=case_id,
        tenant_id=current_user.tenant_id,
        created_by=current_user.user_id,
        **body.model_dump(),
    )
    db.add(deadline)
    await db.commit()
    await db.refresh(deadline)
    return CaseDeadlineResponse.model_validate(deadline)


@router.get("/{case_id}/deadlines", response_model=List[CaseDeadlineResponse])
async def list_deadlines(
    case_id: uuid.UUID,
    include_completed: bool = Query(False),
    current_user: CurrentUser = Depends(require_permissions(Permission.CASE_READ)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CaseDeadline).where(CaseDeadline.case_id == case_id)
    if not include_completed:
        stmt = stmt.where(CaseDeadline.is_completed == False)
    result = await db.execute(stmt.order_by(CaseDeadline.due_date.asc()))
    return [CaseDeadlineResponse.model_validate(d) for d in result.scalars().all()]


# ── Notes ─────────────────────────────────────────────────────────────────────

@router.post("/{case_id}/notes", response_model=CaseNoteResponse, status_code=201)
async def add_note(
    case_id: uuid.UUID,
    body: CaseNoteCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.CASE_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    note = CaseNote(
        case_id=case_id,
        tenant_id=current_user.tenant_id,
        created_by=current_user.user_id,
        **body.model_dump(),
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return CaseNoteResponse.model_validate(note)


@router.get("/{case_id}/notes", response_model=List[CaseNoteResponse])
async def list_notes(
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permissions(Permission.CASE_READ)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CaseNote).where(
        CaseNote.case_id == case_id,
        CaseNote.deleted_at.is_(None),
    )
    if current_user.is_client() or not current_user.has_permission(Permission.CASE_READ_PRIVATE_NOTES):
        stmt = stmt.where(CaseNote.note_type == "client_visible")
    result = await db.execute(stmt.order_by(CaseNote.pinned.desc(), CaseNote.created_at.desc()))
    return [CaseNoteResponse.model_validate(n) for n in result.scalars().all()]


# ── Tasks ─────────────────────────────────────────────────────────────────────

@router.post("/{case_id}/tasks", response_model=CaseTaskResponse, status_code=201)
async def create_task(
    case_id: uuid.UUID,
    body: CaseTaskCreate,
    current_user: CurrentUser = Depends(require_permissions(Permission.CASE_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    task = CaseTask(
        case_id=case_id,
        tenant_id=current_user.tenant_id,
        created_by=current_user.user_id,
        **body.model_dump(),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return CaseTaskResponse.model_validate(task)


@router.get("/{case_id}/tasks", response_model=List[CaseTaskResponse])
async def list_tasks(
    case_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permissions(Permission.CASE_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CaseTask).where(
            CaseTask.case_id == case_id,
            CaseTask.deleted_at.is_(None),
        ).order_by(CaseTask.due_date.asc())
    )
    return [CaseTaskResponse.model_validate(t) for t in result.scalars().all()]


# ── Conflict check ────────────────────────────────────────────────────────────

@router.post("/conflict-check", response_model=ConflictCheckResponse)
async def conflict_check(
    body: ConflictCheckRequest,
    current_user: CurrentUser = Depends(require_permissions(Permission.CASE_CONFLICT_CHECK)),
    db: AsyncSession = Depends(get_db),
):
    """Search all cases and clients for potential conflicts of interest."""
    from ..models.client import Client
    term = f"%{body.search_term}%"

    # Search cases
    case_result = await db.execute(
        select(Case).where(
            Case.tenant_id == current_user.tenant_id,
            or_(
                Case.title.ilike(term),
                Case.opposing_party.ilike(term),
                Case.opposing_counsel.ilike(term),
            ),
            Case.deleted_at.is_(None),
        ).limit(20)
    )
    cases = case_result.scalars().all()

    # Search clients
    client_result = await db.execute(
        select(Client).where(
            Client.tenant_id == current_user.tenant_id,
            or_(
                Client.first_name.ilike(term),
                Client.last_name.ilike(term),
                Client.company_name.ilike(term),
            ),
            Client.deleted_at.is_(None),
        ).limit(20)
    )
    clients = client_result.scalars().all()

    matches = []
    for c in cases:
        matches.append({
            "type": "case",
            "id": str(c.id),
            "title": c.title,
            "case_number": c.case_number,
            "opposing_party": c.opposing_party,
            "stage": c.stage,
        })
    for cl in clients:
        matches.append({
            "type": "client",
            "id": str(cl.id),
            "name": cl.display_name,
            "email": cl.email,
            "status": cl.status,
        })

    return ConflictCheckResponse(
        matches_found=len(matches) > 0,
        matches=matches,
        search_term=body.search_term,
    )
