"""Wave 3 MANIFEST layer — schema and validation tests (§46)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_runtime.manifest import (
    AgentManifest,
    CertificationStatus,
    MemoryScope,
)


def _manifest(**overrides):
    fields = {
        "agent_id": "agent.test",
        "agent_version": "1.0.0",
        "display_name": "Test Agent",
        "owner": "sintraprime.principal",
        "runtime_class": "tests.FakeAgent",
        "mission_types": ("generic",),
        "required_capabilities": ("READ_REPOSITORY",),
        "forbidden_capabilities": ("EXECUTE_PAYMENT", "MERGE_PULL_REQUEST"),
        "provider_policy": {"provider_class": "REASONING"},
        "tool_policy": {"filesystem_scope": "READ_ONLY"},
        "authority_policy": "DELEGATED",
    }
    fields.update(overrides)
    return AgentManifest(**fields)


class TestManifestSchema:
    def test_valid_manifest_defaults(self):
        m = _manifest()
        assert m.agent_id == "agent.test"
        assert m.manifest_schema == 1
        assert m.certification_status is CertificationStatus.UNREGISTERED

    def test_identity_must_be_namespaced(self):
        for bad in ("Nova", "nova_agent", "agent.", "agent.UPPER", "hermes"):
            with pytest.raises(ValidationError):
                _manifest(agent_id=bad)

    def test_agent_version_semver_distinct_from_schema(self):
        with pytest.raises(ValidationError):
            _manifest(agent_version="2.3")
        m = _manifest()
        assert m.manifest_schema == 1
        assert m.agent_version == "1.0.0"

    def test_required_forbidden_overlap_rejected(self):
        with pytest.raises(ValidationError, match="contradictory"):
            _manifest(required_capabilities=("READ_REPOSITORY",), forbidden_capabilities=("READ_REPOSITORY",))

    def test_unknown_capability_rejected(self):
        with pytest.raises(ValidationError, match="unknown capability"):
            _manifest(required_capabilities=("NOT_A_REAL_CAPABILITY",))

    def test_explicit_deny_list_allowed(self):
        m = _manifest(forbidden_capabilities=("EXECUTE_PAYMENT", "MERGE_PULL_REQUEST", "DEPLOY_SERVICE"))
        assert "EXECUTE_PAYMENT" in m.forbidden_capabilities

    def test_governance_readonly_scope_forbids_write(self):

        with pytest.raises(ValidationError, match="GOVERNANCE_READONLY"):
            _manifest(memory_scope=MemoryScope.GOVERNANCE_READONLY, memory_write_requests_allowed=True)

    def test_bounded_execution_defaults(self):
        m = _manifest()
        assert m.timeout_seconds >= 1
        assert m.max_iterations >= 1
        assert m.budget_policy.max_iterations >= 1

    def test_manifest_frozen(self):
        m = _manifest()
        with pytest.raises(ValidationError):
            m.agent_id = "agent.other"

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            _manifest(self_grant_enabled=True)

    def test_owner_required(self):
        with pytest.raises(ValidationError):
            AgentManifest(
                agent_id="agent.x",
                agent_version="1.0.0",
                display_name="x",
                owner="",
                runtime_class="c.C",
                mission_types=("m",),
                provider_policy={"provider_class": "REASONING"},
                tool_policy={},
                authority_policy="DELEGATED",
            )


def _manifest(**overrides):
    fields = {
        "agent_id": "agent.test",
        "agent_version": "1.0.0",
        "display_name": "Test Agent",
        "owner": "sintraprime.principal",
        "runtime_class": "tests.FakeAgent",
        "mission_types": ("generic",),
        "required_capabilities": ("READ_REPOSITORY",),
        "forbidden_capabilities": ("EXECUTE_PAYMENT", "MERGE_PULL_REQUEST"),
        "provider_policy": {"provider_class": "REASONING"},
        "tool_policy": {"filesystem_scope": "READ_ONLY"},
        "authority_policy": "DELEGATED",
    }
    fields.update(overrides)
    return AgentManifest(**fields)
