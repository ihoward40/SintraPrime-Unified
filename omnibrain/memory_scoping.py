"""Scoped memory retrieval (SP-OMNIBRAIN-RUNTIME-001 Phase 4/5).

An agent does NOT automatically receive all SintraPrime memory. This module
is a FAIL-CLOSED retrieval filter layered over any memory backend that can
list entries: it never writes, never deletes, never ranks by authority.

Scope model (directive Phase 4): memory is classified as
    MISSION_MEMORY | AGENT_WORKING_MEMORY | LONG_TERM_SYSTEM_MEMORY |
    EVIDENCE_MEMORY | PRINCIPAL_BINDINGS | EXTERNAL_REFERENCE_MEMORY

Access rules (fail closed):
    - an agent retrieves MISSION_MEMORY only for missions in its envelope
    - an agent retrieves AGENT_WORKING_MEMORY only if agent_id matches,
      or the entry was explicitly shared to its mission
    - LONG_TERM_SYSTEM_MEMORY is readable by any admitted agent
    - EVIDENCE_MEMORY requires the evidence scope in the envelope
    - PRINCIPAL_BINDINGS are NEVER retrievable by agents (Principal-only)
    - EXTERNAL_REFERENCE_MEMORY follows the data scope of the envelope
    - UNKNOWN scope class -> DENY (fail closed)
    - a CHILD's visible scope set is the intersection of the parent's
      visible scope set and its own envelope (subset invariant)
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum


class MemoryScopeClass(str, Enum):
    MISSION_MEMORY = "MISSION_MEMORY"
    AGENT_WORKING_MEMORY = "AGENT_WORKING_MEMORY"
    LONG_TERM_SYSTEM_MEMORY = "LONG_TERM_SYSTEM_MEMORY"
    EVIDENCE_MEMORY = "EVIDENCE_MEMORY"
    PRINCIPAL_BINDINGS = "PRINCIPAL_BINDINGS"
    EXTERNAL_REFERENCE_MEMORY = "EXTERNAL_REFERENCE_MEMORY"


class MemoryRetrievalDenied(PermissionError):
    """Fail-closed denial. NOT a system failure — an authorization outcome."""


@dataclass(frozen=True)
class MemoryScopeEnvelope:
    """The memory-relevant slice of an agent's authority envelope."""

    agent_id: str
    mission_ids: frozenset[str] = frozenset()
    data_scopes: frozenset[str] = frozenset()
    evidence_scopes: frozenset[str] = frozenset()
    is_principal: bool = False

    @classmethod
    def child_of(cls, parent: "MemoryScopeEnvelope", *, agent_id: str,
                 mission_ids: Iterable[str] = (),
                 data_scopes: Iterable[str] = (),
                 evidence_scopes: Iterable[str] = ()) -> "MemoryScopeEnvelope":
        """Subset invariant: a child's scopes can only shrink, never grow."""
        return cls(
            agent_id=agent_id,
            mission_ids=frozenset(mission_ids) & parent.mission_ids,
            data_scopes=frozenset(data_scopes) & parent.data_scopes,
            evidence_scopes=frozenset(evidence_scopes) & parent.evidence_scopes,
            is_principal=False,  # principal status never propagates to children
        )


@dataclass(frozen=True)
class ScopedMemoryRecord:
    """A memory record classified for governed retrieval."""

    record_id: str
    scope_class: str                    # MemoryScopeClass value or UNKNOWN
    mission_id: str | None = None
    owner_agent_id: str | None = None
    shared_mission_ids: frozenset[str] = field(default_factory=frozenset)
    data_scope: str | None = None
    content: str = ""
    metadata: Mapping[str, object] = field(default_factory=dict)


def can_retrieve(envelope: MemoryScopeEnvelope, record: ScopedMemoryRecord) -> bool:
    """Deterministic, side-effect-free access decision. Fail closed."""
    try:
        scope = MemoryScopeClass(record.scope_class)
    except ValueError:
        return False  # UNKNOWN scope class -> DENY

    if scope is MemoryScopeClass.PRINCIPAL_BINDINGS:
        return envelope.is_principal

    if scope is MemoryScopeClass.LONG_TERM_SYSTEM_MEMORY:
        return True

    if scope is MemoryScopeClass.MISSION_MEMORY:
        return record.mission_id in envelope.mission_ids

    if scope is MemoryScopeClass.AGENT_WORKING_MEMORY:
        if record.owner_agent_id == envelope.agent_id:
            return True
        return record.mission_id in envelope.mission_ids and record.mission_id in record.shared_mission_ids

    if scope is MemoryScopeClass.EVIDENCE_MEMORY:
        return record.data_scope in envelope.evidence_scopes

    if scope is MemoryScopeClass.EXTERNAL_REFERENCE_MEMORY:
        return record.data_scope in envelope.data_scopes

    return False  # unreachable; kept for explicit fail-closed completeness


def retrieve(envelope: MemoryScopeEnvelope,
             records: Iterable[ScopedMemoryRecord]) -> list[ScopedMemoryRecord]:
    """Filter an iterable of records down to what the envelope may see."""
    return [r for r in records if can_retrieve(envelope, r)]
