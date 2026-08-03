"""Schemas for redacted persistent matter packet exports."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class MatterExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["JSON", "PDF"] = "JSON"


class MatterExportResponse(BaseModel):
    export_id: str
    matter_id: str
    format: Literal["JSON", "PDF"]
    packet_hash: str
    redacted_manifest_hash: str
    audit_event_id: str
    byte_count: int
    content: str | None = None
