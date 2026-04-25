"""Pydantic v2 schemas for Cases, Events, Deadlines, Notes, Tasks."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    client_id: uuid.UUID
    matter_id: Optional[uuid.UUID] = None
    title: str = Field(..., min_length=2, max_length=500)
    description: Optional[str] = None
    practice_area: Optional[str] = None
    case_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    court_name: Optional[str] = None
    docket_number: Optional[str] = None
    lead_attorney_id: Optional[uuid.UUID] = None
    opposing_party: Optional[str] = None
    opposing_counsel: Optional[str] = None
    statute_of_limitations: Optional[date] = None
    next_court_date: Optional[date] = None
    is_urgent: bool = False
    is_confidential: bool = False
    intake_data: Optional[dict] = None
    tags: Optional[List[str]] = None


class CaseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2)
    description: Optional[str] = None
    stage: Optional[str] = None
    practice_area: Optional[str] = None
    case_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    court_name: Optional[str] = None
    docket_number: Optional[str] = None
    lead_attorney_id: Optional[uuid.UUID] = None
    assigned_staff: Optional[List[uuid.UUID]] = None
    opposing_party: Optional[str] = None
    opposing_counsel: Optional[str] = None
    statute_of_limitations: Optional[date] = None
    next_court_date: Optional[date] = None
    is_urgent: Optional[bool] = None
    conflict_checked: Optional[bool] = None
    conflict_cleared: Optional[bool] = None
    outcome: Optional[str] = None
    outcome_notes: Optional[str] = None
    settlement_amount: Optional[float] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[dict] = None


class CaseResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: uuid.UUID
    matter_id: Optional[uuid.UUID] = None
    case_number: str
    title: str
    description: Optional[str] = None
    practice_area: Optional[str] = None
    stage: str
    lead_attorney_id: Optional[uuid.UUID] = None
    is_urgent: bool
    is_confidential: bool
    conflict_checked: bool
    conflict_cleared: bool
    statute_of_limitations: Optional[date] = None
    next_court_date: Optional[date] = None
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    tags: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaseListResponse(BaseModel):
    items: List[CaseResponse]
    total: int
    page: int
    page_size: int


class CaseEventCreate(BaseModel):
    event_type: str
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    event_date: datetime
    location: Optional[str] = None
    is_client_visible: bool = False
    metadata: Optional[dict] = None


class CaseEventResponse(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    event_type: str
    title: str
    description: Optional[str] = None
    event_date: datetime
    location: Optional[str] = None
    is_client_visible: bool
    created_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class CaseDeadlineCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    deadline_type: str
    due_date: datetime
    reminder_days: List[int] = [7, 1]
    assigned_to: Optional[uuid.UUID] = None
    is_critical: bool = False


class CaseDeadlineResponse(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    title: str
    deadline_type: str
    due_date: datetime
    is_completed: bool
    is_critical: bool
    assigned_to: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CaseNoteCreate(BaseModel):
    title: Optional[str] = None
    content: str = Field(..., min_length=1)
    note_type: str = Field("private", pattern=r"^(private|client_visible)$")
    pinned: bool = False


class CaseNoteResponse(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    title: Optional[str] = None
    content: str
    note_type: str
    pinned: bool
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaseTaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    priority: str = Field("medium", pattern=r"^(low|medium|high|critical)$")
    assigned_to: Optional[uuid.UUID] = None
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = Field(None, ge=0)


class CaseTaskResponse(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    title: str
    description: Optional[str] = None
    priority: str
    status: str
    assigned_to: Optional[uuid.UUID] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ConflictCheckRequest(BaseModel):
    search_term: str = Field(..., min_length=2)


class ConflictCheckResponse(BaseModel):
    matches_found: bool
    matches: List[dict]  # list of matching cases/clients
    search_term: str
