"""Pydantic v2 schemas for Client and Matter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, EmailStr, Field

if TYPE_CHECKING:
    import uuid
    from datetime import datetime


class ClientBase(BaseModel):
    client_type: str = Field("individual", pattern=r"^(individual|organization)$")
    first_name: str | None = None
    last_name: str | None = None
    company_name: str | None = None
    contact_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    alt_phone: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str = "US"
    notes: str | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None


class ClientCreate(ClientBase):
    primary_attorney_id: uuid.UUID | None = None
    intake_date: datetime | None = None


class ClientUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    company_name: str | None = None
    contact_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    alt_phone: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    notes: str | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None
    status: str | None = None
    primary_attorney_id: uuid.UUID | None = None
    portal_access: bool | None = None


class ClientResponse(ClientBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    status: str
    portal_access: bool
    primary_attorney_id: uuid.UUID | None = None
    intake_date: datetime | None = None
    created_at: datetime
    updated_at: datetime
    display_name: str

    model_config = {"from_attributes": True}


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    total: int
    page: int
    page_size: int


# ── Matter ────────────────────────────────────────────────────────────────────

class MatterBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    practice_area: str | None = None
    billing_type: str = Field("hourly", pattern=r"^(hourly|flat_fee|contingency|retainer)$")
    hourly_rate: float | None = Field(None, ge=0)
    flat_fee: float | None = Field(None, ge=0)
    retainer_amount: float | None = Field(None, ge=0)
    contingency_pct: float | None = Field(None, ge=0, le=100)
    responsible_attorney_id: uuid.UUID | None = None
    billing_attorney_id: uuid.UUID | None = None


class MatterCreate(MatterBase):
    client_id: uuid.UUID
    matter_number: str | None = None


class MatterUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    practice_area: str | None = None
    billing_type: str | None = None
    hourly_rate: float | None = None
    flat_fee: float | None = None
    retainer_amount: float | None = None
    status: str | None = None
    responsible_attorney_id: uuid.UUID | None = None
    billing_attorney_id: uuid.UUID | None = None
    closed_at: datetime | None = None


class MatterResponse(MatterBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: uuid.UUID
    matter_number: str
    status: str
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
