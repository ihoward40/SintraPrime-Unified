"""Pydantic v2 schemas for Client and Matter."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class ClientBase(BaseModel):
    client_type: str = Field("individual", pattern=r"^(individual|organization)$")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    alt_phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "US"
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[dict] = None


class ClientCreate(ClientBase):
    primary_attorney_id: Optional[uuid.UUID] = None
    intake_date: Optional[datetime] = None


class ClientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    alt_phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[dict] = None
    status: Optional[str] = None
    primary_attorney_id: Optional[uuid.UUID] = None
    portal_access: Optional[bool] = None


class ClientResponse(ClientBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    status: str
    portal_access: bool
    primary_attorney_id: Optional[uuid.UUID] = None
    intake_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    display_name: str

    model_config = {"from_attributes": True}


class ClientListResponse(BaseModel):
    items: List[ClientResponse]
    total: int
    page: int
    page_size: int


# ── Matter ────────────────────────────────────────────────────────────────────

class MatterBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    practice_area: Optional[str] = None
    billing_type: str = Field("hourly", pattern=r"^(hourly|flat_fee|contingency|retainer)$")
    hourly_rate: Optional[float] = Field(None, ge=0)
    flat_fee: Optional[float] = Field(None, ge=0)
    retainer_amount: Optional[float] = Field(None, ge=0)
    contingency_pct: Optional[float] = Field(None, ge=0, le=100)
    responsible_attorney_id: Optional[uuid.UUID] = None
    billing_attorney_id: Optional[uuid.UUID] = None


class MatterCreate(MatterBase):
    client_id: uuid.UUID
    matter_number: Optional[str] = None


class MatterUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    practice_area: Optional[str] = None
    billing_type: Optional[str] = None
    hourly_rate: Optional[float] = None
    flat_fee: Optional[float] = None
    retainer_amount: Optional[float] = None
    status: Optional[str] = None
    responsible_attorney_id: Optional[uuid.UUID] = None
    billing_attorney_id: Optional[uuid.UUID] = None
    closed_at: Optional[datetime] = None


class MatterResponse(MatterBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: uuid.UUID
    matter_number: str
    status: str
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
