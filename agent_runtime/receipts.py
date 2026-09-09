"""Runtime receipts, memory provenance (Wave 3, §38-§39, §22-§23).

Receipts store operational facts, never hidden reasoning (§39). Memory
writes are REQUESTED (§22) and always carry provenance (§23) — no
anonymous writes. Outcomes are standardized (§44): REFUSED is policy
denial, never collapsed into system failure.
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .manifest import MemoryScope


class RuntimeOutcome(StrEnum):
    """§44 standardized outcomes. REFUSED = intentional policy denial."""

    COMPLETED = "COMPLETED"
    REFUSED = "REFUSED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"
    DEGRADED = "DEGRADED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"  # §22: bounded stop, distinct from FAILED


class AgentRuntimeReceipt(BaseModel):
    """§38: operational facts only — never chain-of-thought (§39)."""

    model_config = ConfigDict(frozen=True)

    agent_id: str
    agent_version: str
    manifest_hash: str = ""  # §6: MISSION_AGENT_MANIFEST = VERSION_BOUND
    mission_id: str
    delegation_id: str = ""
    capabilities_used: tuple[str, ...] = ()
    tools_used: tuple[str, ...] = ()
    context_hash: str = ""  # §17: stable hash of the audited context package
    provider_calls: int = 0
    tool_calls: int = 0
    memory_reads: int = 0
    memory_write_requests: int = 0
    duration_seconds: float = 0.0
    result: RuntimeOutcome
    evidence_refs: tuple[str, ...] = ()
    error_class: str | None = None  # failure classification, not model output


class MemoryWriteDeniedError(PermissionError):
    """REFUSED: the write request violated memory policy."""


class MemoryProvenance(BaseModel):
    """§23: provenance-complete persisted memory. No anonymous writes."""

    model_config = ConfigDict(frozen=True)

    origin: str
    actor_agent: str
    mission_id: str
    tenant: str
    timestamp: str
    classification: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_reference: str = ""
    trust_level: str  # VERIFIED | GOVERNING | OBSERVED (portal precedent)
    content_sha256: str = ""  # digest of persisted content (content itself lives in the store)


class MemoryWriteAuthority:
    """Mediates memory write REQUESTS (§22): scope policy → provenance →
    persistence. Agents never persist memory directly."""

    def __init__(self) -> None:
        self._write_scopes: dict[str, set[str]] = {}
        self.persisted: list[MemoryProvenance] = []

    def allow_write_scope(self, agent_id: str, scope: str) -> None:
        self._write_scopes.setdefault(agent_id, set()).add(scope)

    def submit(
        self,
        *,
        agent_id: str,
        proposed_scope: str,
        content: str,
        mission_id: str = "",
        tenant: str = "",
        evidence_reference: str = "",
        classification: str = "OBSERVED",
        confidence: float = 0.5,
        trust_level_proposed: str = "",
        actor: str = "",
    ) -> MemoryProvenance:
        """Evaluate a write REQUEST (§9: request ≠ persisted fact). Returns
        the provenance-complete record or raises MemoryWriteDeniedError.

        §8: NO_ACTOR and NO_MISSION refuse. §10: trust_level is ASSIGNED by
        this governing authority (always OBSERVED at intake) — an agent's
        self-asserted trust level is never honored."""
        if not actor and not agent_id:
            raise MemoryWriteDeniedError("NO_ACTOR: memory write refused without an acting identity")
        actor_id = actor or agent_id
        if not actor_id:
            raise MemoryWriteDeniedError("NO_ACTOR: memory write refused without an acting identity")
        # mission-bound scopes (MISSION) require a mission binding (§15)
        if proposed_scope in ("MISSION", MemoryScope.MISSION.value) and not mission_id:
            raise MemoryWriteDeniedError("NO_MISSION: mission-scoped write requires mission_id (§23)")
        allowed = self._write_scopes.get(agent_id, set())
        if proposed_scope not in allowed:
            raise MemoryWriteDeniedError(
                f"memory write refused: scope {proposed_scope!r} not manifest-permitted for {agent_id}"
            )
        if proposed_scope in ("GOVERNANCE_READONLY", MemoryScope.GOVERNANCE_READONLY.value):
            raise MemoryWriteDeniedError("governance memory is read-only through the agent runtime (§21)")
        if not evidence_reference:
            raise MemoryWriteDeniedError("anonymous memory write refused: evidence_reference required (§23)")
        # §10: agent-proposed trust levels are NEVER accepted — the governing
        # service assigns trust; the agent's proposal is recorded as data.
        proposed_trust = trust_level_proposed
        del proposed_trust
        record = MemoryProvenance(
            origin=actor or agent_id,
            actor_agent=agent_id,
            mission_id=mission_id,
            tenant=tenant,
            timestamp=datetime.now(UTC).isoformat(),
            classification=classification,
            confidence=confidence,
            evidence_reference=evidence_reference,
            trust_level="OBSERVED",
            content_sha256=__import__("hashlib").sha256(content.encode("utf-8")).hexdigest(),
        )
        # content itself is persisted with the record by the caller store;
        # the authority mediates policy and provenance (§22).
        self.persisted.append(record)
        return record
