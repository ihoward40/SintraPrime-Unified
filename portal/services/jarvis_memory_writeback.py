"""JARVIS-001-A3: bounded, provenance-linked memory writeback and brief.

Bridges a certified ``JarvisMissionResult`` to the EXISTING OmniBrain memory
vault and the EXISTING Principal Brief service. No new memory engine and no
new brief engine is introduced here: persistence goes through
``memory_vault.store_memory`` and synthesis through ``brief_service``.

Bounded by construction: this module accepts ONLY a typed read-only
``JarvisMissionResult``, verifies its provenance against the authoritative
A1 request store (fail-closed), and writes exactly one memory record whose
content carries the mission/request/result/evidence linkage. Worker outputs
can never reach this seam directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.orchestration import MemoryEntry
from .jarvis_principal_mission import (
    EXTERNAL_SIDE_EFFECTS,
    JARVIS_AUTHORITY,
    JARVIS_WORKFLOW_TYPE,
    PrincipalMissionRequestStore,
)
from .jarvis_read_only_workflow import JarvisMissionResult
from .memory_vault import memory_vault
from .principal_brief import brief_service

MEMORY_TYPE_JARVIS_MISSION_RESULT = "JARVIS_MISSION_RESULT"
JARVIS_MEMORY_SOURCE = "jarvis.read_only"
_MEMORY_SCHEMA = "jarvis.mission_memory.v1"
_EVIDENCE_LIMIT = 16
_TEXT_LIMIT = 500


@dataclass(frozen=True, slots=True)
class JarvisMemoryRecord:
    """Typed receipt of one bounded provenance-linked memory write."""

    memory_id: str
    tenant_id: UUID
    request_id: UUID
    mission_id: UUID
    request_hash: str
    memory_type: str = MEMORY_TYPE_JARVIS_MISSION_RESULT
    external_side_effects: int = EXTERNAL_SIDE_EFFECTS


def _require_typed_read_only_result(result: Any) -> None:
    """Fail closed unless the input is a certified read-only mission result."""
    if not isinstance(result, JarvisMissionResult):
        raise PermissionError("JARVIS_MEMORY_TYPED_RESULT_REQUIRED")
    if result.external_side_effects != EXTERNAL_SIDE_EFFECTS:
        raise PermissionError("JARVIS_MEMORY_SIDE_EFFECTS_FORBIDDEN")
    if result.legacy_delegate_used:
        raise PermissionError("JARVIS_MEMORY_LEGACY_PATH_FORBIDDEN")
    if result.mission.authority != JARVIS_AUTHORITY:
        raise PermissionError("JARVIS_MEMORY_AUTHORITY_MISMATCH")
    if result.mission.workflow_type != JARVIS_WORKFLOW_TYPE:
        raise PermissionError("JARVIS_MEMORY_WORKFLOW_TYPE_MISMATCH")


def _bounded_text(value: Any) -> str:
    text = "" if value is None else str(value)
    return text[:_TEXT_LIMIT]


def _coerce_tenant_id(value: Any) -> UUID:
    """Tenant identity must be a canonical UUID; anything else fails closed."""
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except ValueError as exc:
        raise PermissionError("JARVIS_MEMORY_TENANT_ID_INVALID") from exc


def build_mission_memory_record(result: JarvisMissionResult) -> dict[str, Any]:
    """Derive the bounded, linkage-carrying memory payload from the result."""
    _require_typed_read_only_result(result)
    artifact_evidence: list[dict[str, Any]] = []
    for item in list(result.evidence)[:_EVIDENCE_LIMIT]:
        if not isinstance(item, dict):
            continue
        artifact = item.get("artifact") if isinstance(item.get("artifact"), dict) else {}
        findings = artifact.get("findings") if isinstance(artifact.get("findings"), dict) else {}
        artifact_evidence.append(
            {
                "worker_id": _bounded_text(item.get("worker_id")),
                "artifact_state": _bounded_text(artifact.get("state")),
                "provider": _bounded_text(findings.get("provider")),
            }
        )
    summary = result.summary if isinstance(result.summary, dict) else {}
    return {
        "schema": _MEMORY_SCHEMA,
        "source": JARVIS_MEMORY_SOURCE,
        "authority": JARVIS_AUTHORITY,
        "workflow_type": JARVIS_WORKFLOW_TYPE,
        "external_side_effects": EXTERNAL_SIDE_EFFECTS,
        "created_at": datetime.now(UTC).isoformat(),
        "linkage": {
            "mission_id": str(result.mission.mission_id),
            "request_id": str(result.request_id),
            "request_hash": result.request_hash,
            "tenant_id": str(result.mission.tenant_id),
            "swarm_id": _bounded_text(result.swarm_id),
            "task_id": _bounded_text(result.task_provenance.get("task_id")),
            "worker_class": _bounded_text(result.task_provenance.get("worker_class")),
            "status": _bounded_text(result.status),
        },
        "evidence_references": artifact_evidence,
        "findings": {
            "status": _bounded_text(result.status),
            "worker_class": _bounded_text(result.task_provenance.get("worker_class")),
            "evidence_count": len(artifact_evidence),
            "error": _bounded_text(result.error or ""),
        },
        "uncertainty": [_bounded_text(u) for u in summary.get("uncertainty", []) or []],
        "recommended_next_actions": [
            _bounded_text(a) for a in summary.get("recommended_next_actions", []) or []
        ],
        "actions_requiring_approval": [
            _bounded_text(a) for a in summary.get("actions_requiring_approval", []) or []
        ],
    }


async def store_mission_result_memory(
    session: AsyncSession,
    request_store: PrincipalMissionRequestStore,
    result: JarvisMissionResult,
) -> JarvisMemoryRecord:
    """Write exactly one bounded provenance-linked record via the existing vault.

    Provenance is verified against the authoritative A1 request store before
    any write: the request must exist, belong to the result's tenant, and hash
    to the request_hash carried by the result. Any mismatch fails closed.
    """
    _require_typed_read_only_result(result)
    tenant_id = _coerce_tenant_id(result.mission.tenant_id)
    request = await request_store.get(result.request_id)
    if request is None:
        raise PermissionError("JARVIS_MEMORY_PROVENANCE_UNVERIFIED")
    if str(request.tenant_id) != str(tenant_id):
        raise PermissionError("JARVIS_MEMORY_TENANT_MISMATCH")
    if request.request_hash != result.request_hash:
        raise PermissionError("JARVIS_MEMORY_HASH_MISMATCH")

    payload = build_mission_memory_record(result)
    metadata = {
        "schema": _MEMORY_SCHEMA,
        "source": JARVIS_MEMORY_SOURCE,
        "authority": JARVIS_AUTHORITY,
        "mission_id": str(result.mission.mission_id),
        "request_id": str(result.request_id),
        "request_hash": result.request_hash,
    }
    memory_id = await memory_vault.store_memory(
        session,
        str(tenant_id),
        payload,
        MEMORY_TYPE_JARVIS_MISSION_RESULT,
        metadata,
    )
    return JarvisMemoryRecord(
        memory_id=memory_id,
        tenant_id=tenant_id,
        request_id=result.request_id,
        mission_id=result.mission.mission_id,
        request_hash=result.request_hash,
    )


async def retrieve_mission_memory(
    session: AsyncSession,
    request_store: PrincipalMissionRequestStore,
    *,
    tenant_id: str | UUID,
    request_id: UUID,
) -> list[MemoryEntry]:
    """Retrieve mission memory strictly within the caller's tenant boundary.

    Returns an empty list (never another tenant's records) when the request is
    unknown or tenant-foreign, so substitution and cross-tenant reads fail
    closed without leaking existence.
    """
    tenant_uuid = _coerce_tenant_id(tenant_id)
    request = await request_store.get(request_id)
    if request is None or str(request.tenant_id) != str(tenant_uuid):
        return []
    entries = await memory_vault.retrieve_tenant_memory(
        session, str(tenant_uuid), MEMORY_TYPE_JARVIS_MISSION_RESULT
    )
    wanted = str(request_id)
    return [
        entry
        for entry in entries
        if isinstance(entry.content, dict)
        and entry.content.get("linkage", {}).get("request_id") == wanted
    ]


async def synthesize_mission_brief(
    session: AsyncSession,
    request_store: PrincipalMissionRequestStore,
    result: JarvisMissionResult,
    *,
    actor_id: str,
) -> dict[str, Any]:
    """Produce the Principal Brief via the EXISTING brief service, linked.

    Stores the bounded memory record, then asks the existing
    ``brief_service.create_brief`` to synthesize the brief and annotates the
    returned report with the memory-derived linkage so the brief carries the
    original request, mission, result, evidence, and memory record references.
    The actor must pass the existing principal-approval validation.
    """
    record = await store_mission_result_memory(session, request_store, result)
    entries = await retrieve_mission_memory(
        session, request_store, tenant_id=record.tenant_id, request_id=record.request_id
    )
    stored = next(
        (e for e in entries if str(e.id) == record.memory_id), None
    )
    if stored is None:
        raise PermissionError("JARVIS_MEMORY_RECORD_NOT_FOUND")
    content = stored.content if isinstance(stored.content, dict) else {}
    report = await brief_service.create_brief(
        session, str(record.tenant_id), actor_id
    )
    report["sections"]["jarvis_mission"] = {
        "memory_id": record.memory_id,
        "memory_type": MEMORY_TYPE_JARVIS_MISSION_RESULT,
        "authority": JARVIS_AUTHORITY,
        "external_side_effects": EXTERNAL_SIDE_EFFECTS,
        "linkage": content.get("linkage", {}),
        "evidence_references": content.get("evidence_references", []),
        "findings": content.get("findings", {}),
        "uncertainty": content.get("uncertainty", []),
        "recommended_next_actions": content.get("recommended_next_actions", []),
        "actions_requiring_approval": content.get("actions_requiring_approval", []),
    }
    return report
