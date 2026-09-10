"""Collaboration API schemas — pydantic request/response models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ChannelCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    slug: str = Field(min_length=1)
    channel_type: str = "private"
    visibility: str = "tenant"
    description: str = ""
    created_by: str = ""


class MembershipJoin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    principal_id: str = Field(min_length=1)
    principal_type: str = "human"
    role: str = "contributor"


class BindingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1)
    allowed_event_types: list[str] = Field(default_factory=lambda: ["channel_message_created"])
    max_parallelism: int = Field(default=3, ge=1, le=16)
    memory_mode: str = "session"
    provider_profile: str = "balanced"
    model_profile: str = "balanced"
    actor_allowlist: list[str] = Field(default_factory=list)
    shadow_mode: bool = False


class EventEnvelopeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    channel_id: str = Field(min_length=1)
    actor_type: str = "human"
    actor_id: str = ""
    correlation_id: str = ""
    payload: dict = Field(default_factory=dict)
    hop_count: int = 0
    origin_type: str = "human"
    origin_id: str = ""


class HandoffCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    handoff_id: str = Field(min_length=1)
    source_agent: str = Field(min_length=1)
    target_agent: str = Field(min_length=1)
    task: str = ""
    input_artifacts: list[str] = Field(default_factory=list)
    expected_output_schema: str = ""
    correlation_id: str = ""


class StopAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1)


class KillSwitchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator: str = Field(min_length=1)
    reason: str = ""
    channel_ids: list[str] = Field(default_factory=list)
