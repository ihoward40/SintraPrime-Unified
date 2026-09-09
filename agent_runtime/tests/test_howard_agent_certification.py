"""Wave 3E — Howard agent certification (§18-§20) + 3D Hermes delegation
non-exceedance (§15).

Certifies the canonical Howard topology (agents/howard_* sidecars driven by
the portal recovery domain) against the Wave 3 contracts: manifest,
delegation, memory scope, tool policy, budget bounds, external-action
approval gates. All effects are mocks/fakes — no real external action (§20).
"""
from __future__ import annotations

from agent_runtime.manifest import (
    AgentManifest,
    MemoryScope,
)


def _hermes_manifest() -> AgentManifest:
    return AgentManifest(
        agent_id="agent.hermes",
        agent_version="1.0.0",
        display_name="Hermes",
        owner="sintraprime.principal",
        runtime_class="portal.services.orchestration.orchestrator",
        mission_types=("governed_orchestration", "swarm_delegation"),
        required_capabilities=("READ_REPOSITORY", "SEARCH_WEB", "DELEGATE_TASK", "REQUEST_MEMORY_WRITE"),
        forbidden_capabilities=("EXECUTE_PAYMENT", "MERGE_PULL_REQUEST", "DEPLOY_SERVICE"),
        memory_scope=MemoryScope.TENANT,
        memory_read=True,
        memory_write_requests_allowed=True,
        provider_policy={"provider_class": "REASONING", "structured_output_required": True},
        tool_policy={"allowed_tool_categories": ("repository", "search"), "network_access": True},
        authority_policy="DELEGATED",
        approval_policy="TIERED",
        context_scope="MISSION",
    )


def _howard(**overrides) -> AgentManifest:
    fields = {
        "agent_id": "agent.howard",
        "agent_version": "1.0.0",
        "display_name": "Howard",
        "description": "Recovery-system intake worker (HOWARD_RECOVERY_SYSTEM_12_MONTH_MASTER domain)",
        "owner": "sintraprime.principal",
        "runtime_class": "agents.howard_intake_agent",
        "mission_types": ("recovery_intake", "recovery_monitoring"),
        "required_capabilities": ("READ_REPOSITORY", "READ_DATABASE"),
        "optional_capabilities": ("CREATE_DOCUMENT",),
        "forbidden_capabilities": (
            "EXECUTE_PAYMENT",
            "MERGE_PULL_REQUEST",
            "DEPLOY_SERVICE",
            "SEND_EMAIL",
        ),
        "memory_scope": MemoryScope.MISSION,
        "memory_read": True,
        "memory_write_requests_allowed": True,
        "provider_policy": {"provider_class": "LOCAL", "local_only": True},
        "tool_policy": {
            "allowed_tool_categories": ("filesystem", "http_client"),
            "network_access": True,
            "filesystem_scope": "SANDBOX",
            "shell_access": False,
        },
        "authority_policy": "DELEGATED",
        "approval_policy": "TIERED",
        "tenant_policy": "SINGLE_TENANT",
    }
    fields.update(overrides)
    return AgentManifest(**fields)
