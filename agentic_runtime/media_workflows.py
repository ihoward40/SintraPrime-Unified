"""Governed contract for ComfyUI-style image/video/audio/3D workflows."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MediaKind(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    MODEL_3D = "3d"


@dataclass(frozen=True)
class MediaJob:
    kind: MediaKind
    workflow_id: str
    inputs: dict[str, Any]
    local_only: bool = True
    external_provider: str | None = None
    estimated_cost_usd: float = 0.0
    output_paths: list[str] = field(default_factory=list)


class MediaWorkflowPolicy:
    """Fail-closed admission checks before a media workflow reaches a runner."""

    def __init__(self, *, allow_external: bool = False, max_cost_usd: float = 0.0) -> None:
        self.allow_external = allow_external
        self.max_cost_usd = max_cost_usd

    def admit(self, job: MediaJob) -> tuple[bool, str]:
        if not job.workflow_id.strip():
            return False, "MISSING_WORKFLOW_ID"
        if job.local_only and job.external_provider:
            return False, "LOCAL_ONLY_CONFLICT"
        if job.external_provider and not self.allow_external:
            return False, "EXTERNAL_PROVIDER_REQUIRES_APPROVAL"
        if job.estimated_cost_usd < 0:
            return False, "INVALID_COST"
        if job.estimated_cost_usd > self.max_cost_usd:
            return False, "COST_LIMIT_EXCEEDED"
        return True, "ADMITTED"
