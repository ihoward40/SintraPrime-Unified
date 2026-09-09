"""Wave 3 REGISTRY layer — registration, resolution, duplicates, startup validation (§12-§14)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_runtime.manifest import AgentManifest, CertificationStatus
from agent_runtime.registry import (
    AgentRegistry,
    DuplicateAgentIdError,
    ManifestValidationError,
)


def _manifest(agent_id="agent.a", **overrides):
    fields = {
        "agent_id": agent_id,
        "agent_version": "1.0.0",
        "display_name": agent_id,
        "owner": "sintraprime.principal",
        "runtime_class": "tests.Fake",
        "mission_types": ("generic",),
        "required_capabilities": ("READ_REPOSITORY",),
        "forbidden_capabilities": ("EXECUTE_PAYMENT",),
        "provider_policy": {"provider_class": "REASONING"},
        "tool_policy": {},
        "authority_policy": "DELEGATED",
    }
    fields.update(overrides)
    return AgentManifest(**fields)


class TestRegistration:
    def test_register_resolve_list(self):
        r = AgentRegistry()
        r.register(_manifest())
        assert r.resolve("agent.a").agent_id == "agent.a"
        assert len(r.list()) == 1

    def test_duplicate_agent_id_rejected(self):
        r = AgentRegistry()
        r.register(_manifest())
        with pytest.raises(DuplicateAgentIdError):
            r.register(_manifest())

    def test_unknown_agent_rejected(self):
        r = AgentRegistry()
        with pytest.raises(Exception, match="unknown agent"):
            r.resolve("agent.ghost")

    def test_registration_fails_on_unknown_capability(self):
        # Manifest construction itself fails closed (§13); a raw dict-driven
        # path would hit the registry validator. Assert the pydantic layer.
        with pytest.raises(ValidationError, match="unknown capability"):
            AgentManifest(
                agent_id="agent.bad",
                agent_version="1.0.0",
                display_name="bad",
                owner="p",
                runtime_class="c",
                mission_types=("m",),
                required_capabilities=("MADE_UP_CAPABILITY",),
                provider_policy={"provider_class": "REASONING"},
                tool_policy={},
                authority_policy="DELEGATED",
            )

    def test_registration_rejects_contradiction(self):
        with pytest.raises(ValidationError):
            _manifest(
                required_capabilities=("READ_REPOSITORY",),
                forbidden_capabilities=("READ_REPOSITORY",),
            )


class TestCertificationLadder:
    def test_importable_is_not_certified(self):
        r = AgentRegistry()
        r.register(_manifest())
        assert r.status("agent.a") is CertificationStatus.REGISTERED
        assert r.status("agent.a") is not CertificationStatus.CERTIFIED
        assert r.status("agent.a") is not CertificationStatus.CERTIFIED

    def test_ladder_register_validate_certify(self):
        r = AgentRegistry()
        r.register(_manifest())
        assert r.validate_registered("agent.a") == []
        r.certify("agent.a")
        assert r.status("agent.a") is CertificationStatus.CERTIFIED

    def test_certify_from_registered_refused(self):
        r = AgentRegistry()
        r.register(_manifest())
        from agent_runtime.registry import RegistryError

        with pytest.raises(RegistryError):
            r.certify("agent.a")

    def test_disable_and_quarantine(self):
        r = AgentRegistry()
        r.register(_manifest())
        r.validate_registered("agent.a")
        r.quarantine("agent.a")
        assert r.status("agent.a") is CertificationStatus.QUARANTINED
        assert r.list_enabled() == []
        r.set_status("agent.a", CertificationStatus.TESTED)
        r.certify("agent.a")
        assert len(r.list_enabled()) == 1

    def test_unknown_agent_set_status_refused(self):
        r = AgentRegistry()
        with pytest.raises(Exception, match="unknown agent"):
            r.disable("agent.ghost")

    def test_validate_registered_records_validated(self):
        r = AgentRegistry()
        r.register(_manifest())
        assert r.validate_registered("agent.a") == []
        assert r.status("agent.a") is CertificationStatus.VALIDATED


class TestStartupValidation:
    def test_startup_passes_clean_registry(self):
        r = AgentRegistry()
        r.register(_manifest())
        r.startup_validation()  # no raise

    def test_startup_collects_problems(self):
        r = AgentRegistry()
        m = _manifest()
        r._manifests[m.agent_id] = m
        # inject drift bypassing pydantic (simulating a corrupted manifest)
        object.__setattr__(m, "timeout_seconds", 0)
        assert m.timeout_seconds == 0
        with pytest.raises(ManifestValidationError):
            r.startup_validation()
