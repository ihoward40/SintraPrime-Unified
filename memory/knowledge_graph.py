"""Minimal durable knowledge/provenance graph for OmniBrain."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .context_packages import ContextPackage


@dataclass(frozen=True)
class GraphEdge:
    source_id: str
    relation: str
    target_id: str
    metadata: Dict[str, Any]


class KnowledgeGraphStore:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            root = Path.home() / ".sintra" / "memory"
            root.mkdir(parents=True, exist_ok=True)
            db_path = str(root / "knowledge_graph.db")
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS graph_nodes (
                    node_id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    label TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS graph_edges (
                    source_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (source_id, relation, target_id)
                )"""
            )
            conn.commit()

    def upsert_node(self, node_id: str, node_type: str, label: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO graph_nodes(node_id, node_type, label, metadata, created_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(node_id) DO UPDATE SET
                     node_type=excluded.node_type,
                     label=excluded.label,
                     metadata=excluded.metadata""",
                (node_id, node_type, label, json.dumps(metadata or {}), now),
            )
            conn.commit()

    def add_edge(self, source_id: str, relation: str, target_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO graph_edges(source_id, relation, target_id, metadata, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (source_id, relation, target_id, json.dumps(metadata or {}), now),
            )
            conn.commit()

    def record_context_package(self, package: ContextPackage) -> None:
        agent_node = f"agent:{package.scope.agent_id}"
        self.upsert_node(agent_node, "agent", package.scope.agent_id)
        for item in package.items:
            memory_node = f"memory:{item.memory_id}"
            self.upsert_node(
                memory_node,
                "memory",
                item.content[:120],
                {"tags": item.tags, "scope": item.scope, "provenance": item.provenance},
            )
            self.add_edge(agent_node, "RECALLED", memory_node, {"query": package.query})
            source_id = item.provenance.get("source_id")
            if source_id:
                source_node = f"source:{source_id}"
                self.upsert_node(source_node, "source", str(source_id), item.provenance)
                self.add_edge(memory_node, "DERIVED_FROM", source_node)
            for key, relation in (
                ("project_id", "SCOPED_TO_PROJECT"),
                ("matter_id", "SCOPED_TO_MATTER"),
                ("tenant_id", "SCOPED_TO_TENANT"),
            ):
                value = item.scope.get(key)
                if value:
                    scope_node = f"{key}:{value}"
                    self.upsert_node(scope_node, key.removesuffix("_id"), str(value))
                    self.add_edge(memory_node, relation, scope_node)

    def stats(self) -> Dict[str, int]:
        with self._connect() as conn:
            nodes = conn.execute("SELECT COUNT(*) FROM graph_nodes").fetchone()[0]
            edges = conn.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0]
        return {"nodes": int(nodes), "edges": int(edges)}
