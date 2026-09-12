from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_runtime.manifest import AgentManifest
from agent_runtime.registry import AgentRegistry, ManifestValidationError


def _manifest(agent_id: str = "agent.copilot.engineering.01", **overrides):
    fields = {
        "agent_id": agent_id,
        "agent_version": "1.0.0",
        "display_name": "Copilot Engineering Worker",
        "owner": "sintraprime.principal",
        "runtime_class": "tests.CopilotWorker",
        "mission_types": ("engineering",),
        "required_capabilities": ("READ_REPOSITORY", "RUN_TESTS"),
        "forbidden_capabilities": ("MERGE_PULL_REQUEST", "DEPLOY_SERVICE", "EXECUTE_PAYMENT"),
        "provider_policy": {"provider_class": "CODE"},
        "tool_policy": {},
        "authority_policy": "DELEGATED",
        "actor_id": "copilot.engineering.01",
        "worker_role": "ENGINEERING_WORKER",
        "parent_coordinator": "hermes.canonical",
        "authority_source": "NONE",
        "control_plane": False,
        "preferred_task_types": ("CODE_IMPLEMENTATION", "TEST_IMPLEMENTATION"),
        "max_parallel_tasks": 2,
        "write_capable": True,
        "review_capable": True,
    }
    fields.update(overrides)
    return AgentManifest(**fields)


def test_copilot_registration_happy_path():
    registry = AgentRegistry()
    registry.register(_manifest())
    resolved = registry.resolve("agent.copilot.engineering.01")
    assert resolved.actor_id == "copilot.engineering.01"
    assert resolved.parent_coordinator == "hermes.canonical"


def test_duplicate_actor_rejected():
    registry = AgentRegistry()
    registry.register(_manifest())
    with pytest.raises(ManifestValidationError, match="duplicate actor_id"):
        registry.register(_manifest(agent_id="agent.copilot.engineering.02"))


def test_forged_parent_rejected():
    with pytest.raises(ValidationError, match="parent"):
        _manifest(parent_coordinator="fake.parent")


def test_authority_source_override_rejected():
    with pytest.raises(ValidationError, match="authority_source"):
        _manifest(authority_source="PRINCIPAL")


def test_hermes_impersonation_rejected():
    registry = AgentRegistry()
    with pytest.raises(ManifestValidationError, match="impersonate"):
        registry.register(_manifest(actor_id="hermes.canonical"))
