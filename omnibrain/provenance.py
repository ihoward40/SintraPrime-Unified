"""Provenance graph relationships (SP-OMNIBRAIN-RUNTIME-001 Phase 6).

A queryable relationship surface over governed identifiers. Deliberately
NOT a new graph database: an in-memory + JSON-serializable edge list that
any durable store can hold. Edge semantics (directive Phase 6):

    CREATED_BY AUTHORIZED_BY DERIVED_FROM DELEGATED_FROM
    USED_CONTEXT USED_MEMORY CALLED_TOOL PRODUCED SUPERSEDES RELATES_TO

Edges are append-only and hash-chain verifiable at the application layer
via receipt hashes; this module only maintains the relationship index.
"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum


class RelationType(str, Enum):
    CREATED_BY = "CREATED_BY"
    AUTHORIZED_BY = "AUTHORIZED_BY"
    DERIVED_FROM = "DERIVED_FROM"
    DELEGATED_FROM = "DELEGATED_FROM"
    USED_CONTEXT = "USED_CONTEXT"
    USED_MEMORY = "USED_MEMORY"
    CALLED_TOOL = "CALLED_TOOL"
    PRODUCED = "PRODUCED"
    SUPERSEDES = "SUPERSEDES"
    RELATES_TO = "RELATES_TO"


class NodeType(str, Enum):
    PRINCIPAL = "PRINCIPAL"
    MISSION = "MISSION"
    AUTHORITY_ENVELOPE = "AUTHORITY_ENVELOPE"
    AGENT = "AGENT"
    CONTEXT_PACKAGE = "CONTEXT_PACKAGE"
    MEMORY_EVENT = "MEMORY_EVENT"
    TOOL_CALL = "TOOL_CALL"
    MODEL_CALL = "MODEL_CALL"
    EXTERNAL_EFFECT = "EXTERNAL_EFFECT"
    EVIDENCE_ARTIFACT = "EVIDENCE_ARTIFACT"
    RECEIPT = "RECEIPT"


@dataclass(frozen=True)
class ProvenanceEdge:
    relation: RelationType
    source_type: NodeType
    source_id: str
    target_type: NodeType
    target_id: str
    meta: dict = field(default_factory=dict)


class ProvenanceGraph:
    """Append-only edge index with deterministic query helpers."""

    def __init__(self) -> None:
        self._edges: list[ProvenanceEdge] = []
        self._by_source: dict[tuple[NodeType, str], list[ProvenanceEdge]] = {}
        self._by_target: dict[tuple[NodeType, str], list[ProvenanceEdge]] = {}

    def add(self, edge: ProvenanceEdge) -> ProvenanceEdge:
        self._edges.append(edge)
        self._by_source.setdefault((edge.source_type, edge.source_id), []).append(edge)
        self._by_target.setdefault((edge.target_type, edge.target_id), []).append(edge)
        return edge

    def outgoing(self, node_type: NodeType, node_id: str) -> list[ProvenanceEdge]:
        return list(self._by_source.get((node_type, node_id), []))

    def incoming(self, node_type: NodeType, node_id: str) -> list[ProvenanceEdge]:
        return list(self._by_target.get((node_type, node_id), []))

    def has(self, *, relation: RelationType, source_id: str, target_id: str) -> bool:
        return any(
            e.relation is relation and e.source_id == source_id and e.target_id == target_id
            for e in self._edges
        )

    def chain_to_principal(self, node_type: NodeType, node_id: str) -> list[ProvenanceEdge]:
        """Walk AUTHORIZED_BY/DELEGATED_FROM/CREATED_BY edges upward toward a
        PRINCIPAL node. Returns the edge path; empty list = NO authority path
        exists (callers must treat that as fail-closed)."""
        path: list[ProvenanceEdge] = []
        visited: set[str] = {node_id}
        frontier: tuple[NodeType, str] = (node_type, node_id)
        while True:
            edges = [
                e for e in self._by_source.get(frontier, [])
                if e.relation in (RelationType.AUTHORIZED_BY, RelationType.DELEGATED_FROM,
                                  RelationType.CREATED_BY)
            ]
            if not edges:
                return []  # dead end without reaching a Principal -> no authority path
            edge = edges[0]
            path.append(edge)
            if edge.target_type is NodeType.PRINCIPAL:
                return path
            key = (edge.target_type, edge.target_id)
            if key[1] in visited:
                return []  # cycle -> fail closed
            visited.add(key[1])
            frontier = key

    def to_json(self) -> list[dict]:
        return [
            {
                "relation": e.relation.value,
                "source_type": e.source_type.value,
                "source_id": e.source_id,
                "target_type": e.target_type.value,
                "target_id": e.target_id,
                "meta": dict(e.meta),
            }
            for e in self._edges
        ]

    def __len__(self) -> int:
        return len(self._edges)

    def __iter__(self) -> Iterator[ProvenanceEdge]:
        return iter(self._edges)
