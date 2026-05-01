"""Pydantic v2 schemas for Cases, Events, Deadlines, Notes, Tasks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    import uuid
    from datetime import date, datetime


class CaseCreate(BaseModel):
    client_id: uuid.UUID
    matter_id: uuid.UUID | None = None
    title: str = Field(..., min_length=2, max_length=500)
    description: str | None = None
    practice_area: str | None = None
    case_type: str | None = None
    jurisdiction: str | None = None
    court_name: str | None = None
    docket_number: str | None = None
    lead_attorney_id: uuid.UUID | None = None
    opposing_party: str | None = None
    opposing_counsel: str | None = None
    statute_of_limitations: date | None = None
    next_court_date: date | None = None
    is_urgent: bool = False
    is_confidential: bool = False
    intake_data: dict | None = None
    tags: list[str] | None = None


class CaseUpdate(BaseModel):
    title: str | None = Field(None, min_length=2)
    description: str | None = None
    stage: str | None = None
    practice_area: str | None = None
    case_type: str | None = None
    jurisdiction: str | None = None
    court_name: str | None = None
    docket_number: str | None = None
    lead_attorney_id: uuid.UUID | None = None
    assigned_staff: list[uuid.UUID] | None = None
    opposing_party: str | None = None
    opposing_counsel: str | None = None
    statute_of_limitations: date | None = None
    next_court_date: date | None = None
    is_urgent: bool | None = None
    conflict_checked: bool | None = None
    conflict_cleared: bool | None = None
    outcome: str | None = None
    outcome_notes: str | None = None
    settlement_amount: float | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None


class CaseResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: uuid.UUID
    matter_id: uuid.UUID | None = None
    case_number: str
    title: str
    description: str | None = None
    practice_area: str | None = None
    stage: str
    lead_attorney_id: uuid.UUID | None = None
    is_urgent: bool
    is_confidential: bool
    conflict_checked: bool
    conflict_cleared: bool
    statute_of_limitations: date | None = None
    next_court_date: date | None = None
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    tags: list[str] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaseListResponse(BaseModel):
    items: list[CaseResponse]
    total: int
    page: int
    page_size: int


class CaseEventCreate(BaseModel):
    event_type: str
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    event_date: datetime
    location: str | None = None
    is_client_visible: bool = False
    metadata: dict | None = None


class CaseEventResponse(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    event_type: str
    title: str
    description: str | None = None
    event_date: datetime
    location: str | None = None
    is_client_visible: bool
    created_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class CaseDeadlineCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    deadline_type: str
    due_date: datetime
    reminder_days: list[int] = [7, 1]
    assigned_to: uuid.UUID | None = None
    is_critical: bool = False


class CaseDeadlineResponse(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    title: str
    deadline_type: str
    due_date: datetime
    is_completed: bool
    is_critical: bool
    assigned_to: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CaseNoteCreate(BaseModel):
    title: str | None = None
    content: str = Field(..., min_length=1)
    note_type: str = Field("private", pattern=r"^(private|client_visible)$")
    pinned: bool = False


class CaseNoteResponse(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    title: str | None = None
    content: str
    note_type: str
    pinned: bool
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaseTaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    priority: str = Field("medium", pattern=r"^(low|medium|high|critical)$")
    assigned_to: uuid.UUID | None = None
    due_date: datetime | None = None
    estimated_hours: float | None = Field(None, ge=0)


class CaseTaskResponse(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    title: str
    description: str | None = None
    priority: str
    status: str
    assigned_to: uuid.UUID | None = None
    due_date: datetime | None = None
    completed_at: datetime | None = None
    created_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ConflictCheckRequest(BaseModel):
    search_term: str = Field(..., min_length=2)


class ConflictCheckResponse(BaseModel):
    matches_found: bool
    matches: list[dict]  # list of matching cases/clients
    search_term: str
