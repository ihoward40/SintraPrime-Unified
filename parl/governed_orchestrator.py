"""Governed PARL facade for SintraPrime-wide agent orchestration."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from memory.context_packages import ContextPackageBuilder, ContextScope
from memory.knowledge_graph import KnowledgeGraphStore
from memory.memory_engine import MemoryEngine
from parl.god_mode import PrincipalCommandPolicy, PrincipalSession
from parl.orchestrator import PARLOrchestrator, Task


class GovernedPARLOrchestrator(PARLOrchestrator):
    """PARL orchestrator with Principal Command and scoped OmniBrain context.

    Existing PARL registration/execution stays intact.  Before workers spawn,
    each subtask receives a scope-filtered context package from the existing
    memory subsystem.  The package is recorded into the provenance graph and
    then evaluated by Principal Command admission control.
    """

    def __init__(
        self,
        *args: Any,
        command_policy: Optional[PrincipalCommandPolicy] = None,
        memory_engine: Optional[MemoryEngine] = None,
        context_builder: Optional[ContextPackageBuilder] = None,
        graph_store: Optional[KnowledgeGraphStore] = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.command_policy = command_policy or PrincipalCommandPolicy()
        self.memory_engine = memory_engine or MemoryEngine()
        self.context_builder = context_builder or ContextPackageBuilder(self.memory_engine)
        self.graph_store = graph_store or KnowledgeGraphStore()

    def _attach_context(self, specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        decorated: List[Dict[str, Any]] = []
        for original in specs:
            spec = dict(original)
            payload = dict(spec.get("payload", {}) or {})
            agent_type = spec.get("agent_type")
            agent_id = getattr(agent_type, "value", None) or str(agent_type or "generic")
            scope_data = dict(payload.get("context_scope", {}) or {})
            scope = ContextScope(
                agent_id=str(scope_data.get("agent_id") or agent_id),
                user_id=scope_data.get("user_id", payload.get("user_id")),
                project_id=scope_data.get("project_id", payload.get("project_id")),
                matter_id=scope_data.get("matter_id", payload.get("matter_id")),
                tenant_id=scope_data.get("tenant_id", payload.get("tenant_id")),
                max_items=int(scope_data.get("max_items", 8)),
                allow_legacy_user_scoped=bool(scope_data.get("allow_legacy_user_scoped", True)),
            )
            query = str(payload.get("context_query") or spec.get("description") or "current task")
            package = self.context_builder.build(query=query, scope=scope)
            self.graph_store.record_context_package(package)
            payload["omnibrain_context"] = package.to_dict()
            spec["payload"] = payload
            decorated.append(spec)
        return decorated

    def decompose_and_run(
        self,
        description: str,
        subtask_specs: List[Dict[str, Any]],
        training_step: Optional[int] = None,
        timeout: Optional[float] = None,
        principal_session: Optional[PrincipalSession] = None,
    ) -> Task:
        governed_specs = self._attach_context(subtask_specs)
        self.command_policy.authorize_specs(governed_specs, session=principal_session)
        return super().decompose_and_run(
            description=description,
            subtask_specs=governed_specs,
            training_step=training_step,
            timeout=timeout,
        )
