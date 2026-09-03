"""JARVIS-001-A1 principal mission request boundary.

This unit records an intent separately from Mission execution state.  It is
read-only by design: creating a request is the only permitted persistence
operation and no workflow execution or external side effect is exposed.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

EXTERNAL_SIDE_EFFECTS = 0
JARVIS_WORKFLOW_TYPE = "jarvis.principal_mission"
JARVIS_AUTHORITY = "JARVIS_READ_ONLY"


class DecisionContext(BaseModel):
    """Typed, bounded context captured with a principal request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    objective: str = Field(min_length=1, max_length=4000)
    constraints: tuple[str, ...] = Field(default=())
    priorities: tuple[str, ...] = Field(default=())


class PrincipalMissionRequestInput(BaseModel):
    """Client-owned input; execution and authority fields are not accepted."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    objective: str = Field(min_length=1, max_length=4000)
    decision_context: DecisionContext


@dataclass(frozen=True, slots=True)
class PrincipalMissionRequest:
    """Persisted principal intent, deliberately independent from ``Mission``."""

    request_id: UUID
    tenant_id: str
    requested_by: str
    objective: str
    decision_context: DecisionContext
    workflow_type: str
    authority: str
    request_hash: str
    created_at: datetime


class PrincipalMissionRequestStore(Protocol):
    """Persistence seam; production storage can be added without coupling to Mission."""

    async def save(self, request: PrincipalMissionRequest) -> None: ...

    async def get(self, request_id: UUID) -> PrincipalMissionRequest | None: ...


class InMemoryPrincipalMissionRequestStore:
    """Durable-service test double for the separate request persistence seam."""

    def __init__(self) -> None:
        self._requests: dict[UUID, PrincipalMissionRequest] = {}

    async def save(self, request: PrincipalMissionRequest) -> None:
        self._requests[request.request_id] = request

    async def get(self, request_id: UUID) -> PrincipalMissionRequest | None:
        return self._requests.get(request_id)


class JarvisReadOnlyCapability:
    """Server-owned capability with no mutation or execution surface."""

    name = "jarvis.read_only"
    workflow_type = JARVIS_WORKFLOW_TYPE
    authority = JARVIS_AUTHORITY
    external_side_effects = EXTERNAL_SIDE_EFFECTS

    async def read(self, store: PrincipalMissionRequestStore, request_id: UUID) -> PrincipalMissionRequest | None:
        return await store.get(request_id)

    def mutate(self, *_args: object, **_kwargs: object) -> None:
        raise PermissionError("JARVIS_READ_ONLY_MUTATION_DENIED")

    def execute(self, *_args: object, **_kwargs: object) -> None:
        raise PermissionError("JARVIS_READ_ONLY_EXECUTION_DENIED")


def _canonical_request_payload(
    *, tenant_id: str, requested_by: str, input_data: PrincipalMissionRequestInput
) -> bytes:
    payload: Mapping[str, object] = {
        "tenant_id": tenant_id,
        "requested_by": requested_by,
        "objective": input_data.objective,
        "decision_context": input_data.decision_context.model_dump(mode="json"),
        "workflow_type": JARVIS_WORKFLOW_TYPE,
        "authority": JARVIS_AUTHORITY,
        "external_side_effects": EXTERNAL_SIDE_EFFECTS,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def deterministic_request_hash(
    *, tenant_id: str, requested_by: str, input_data: PrincipalMissionRequestInput
) -> str:
    """Hash the canonical server-bound request representation."""
    return hashlib.sha256(
        _canonical_request_payload(
            tenant_id=tenant_id, requested_by=requested_by, input_data=input_data
        )
    ).hexdigest()


async def persist_principal_mission_request(
    store: PrincipalMissionRequestStore,
    *,
    tenant_id: str,
    requested_by: str,
    input_data: PrincipalMissionRequestInput,
) -> PrincipalMissionRequest:
    """Persist intent only; no Mission row is created or modified."""
    request = PrincipalMissionRequest(
        request_id=uuid4(),
        tenant_id=tenant_id,
        requested_by=requested_by,
        objective=input_data.objective,
        decision_context=input_data.decision_context,
        workflow_type=JARVIS_WORKFLOW_TYPE,
        authority=JARVIS_AUTHORITY,
        request_hash=deterministic_request_hash(
            tenant_id=tenant_id, requested_by=requested_by, input_data=input_data
        ),
        created_at=datetime.now(UTC),
    )
    await store.save(request)
    return request
