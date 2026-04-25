"""Pydantic v2 schemas for User and Tenant endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# ── Tenant ────────────────────────────────────────────────────────────────────

class TenantBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9\-]+$")
    domain: Optional[str] = None
    primary_color: str = "#1a56db"
    secondary_color: str = "#7e3af2"
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    domain: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    settings: Optional[dict] = None


class TenantResponse(TenantBase):
    id: uuid.UUID
    logo_url: Optional[str] = None
    plan: str
    storage_quota_gb: int
    user_quota: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── User ──────────────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = None
    title: Optional[str] = None
    bar_number: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=12, max_length=128)
    role: str = Field(..., description="Role name e.g. ATTORNEY, CLIENT")
    tenant_id: Optional[uuid.UUID] = None  # set by server for non-super-admin

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        from ..auth.password_handler import validate_password_strength, PasswordError
        try:
            validate_password_strength(v)
        except PasswordError as exc:
            raise ValueError(str(exc))
        return v


class UserInvite(BaseModel):
    email: EmailStr
    role: str
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    send_welcome_email: bool = True


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = None
    title: Optional[str] = None
    notify_email: Optional[bool] = None
    notify_sms: Optional[bool] = None
    notify_push: Optional[bool] = None


class UserPasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        from ..auth.password_handler import validate_password_strength, PasswordError
        try:
            validate_password_strength(v)
        except PasswordError as exc:
            raise ValueError(str(exc))
        return v


class UserResponse(UserBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    role: str
    avatar_url: Optional[str] = None
    email_verified: bool
    mfa_enabled: bool
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_role(cls, user) -> "UserResponse":
        data = {
            "id": user.id,
            "tenant_id": user.tenant_id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "title": user.title,
            "bar_number": user.bar_number,
            "avatar_url": user.avatar_url,
            "email_verified": user.email_verified,
            "mfa_enabled": user.mfa_enabled,
            "is_active": user.is_active,
            "last_login_at": user.last_login_at,
            "created_at": user.created_at,
            "role": user.role_ref.name if user.role_ref else "VIEWER",
        }
        return cls(**data)


class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ── Session ───────────────────────────────────────────────────────────────────

class SessionResponse(BaseModel):
    session_id: str
    device_info: str
    ip_address: str
    created_at: str
    last_active: str
    is_active: str
