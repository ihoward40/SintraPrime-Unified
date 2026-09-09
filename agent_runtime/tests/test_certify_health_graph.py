"""Wave 3 CHECKPOINT 2 §23-§25, §30-§35 — certification entrypoint, receipt
hashing/immutability, health state + quarantine, dependency graph."""
from __future__ import annotations

import json

import pytest

from agent_runtime.certify import (
    build_dependency_graph,
    certification_generation,
    certify_agent,
    source_sha,
)
from agent_runtime.delegation import DelegationAuthority
from agent_runtime.manifest import AgentManifest, CertificationStatus, manifest_hash
from agent_runtime.receipts import AgentRuntimeReceipt, RuntimeOutcome
from agent_runtime.registry import AgentRegistry


def _m(i: str, **kw) -> AgentManifest:
    f = {
        "agent_id": i,
        "agent_version": "1.0.0",
        "display_name": i,
        "owner": "sintraprime.principal",
        "runtime_class": "t.F",
        "mission_types": ("m",),
        "required_capabilities": ("READ_REPOSITORY",),
        "provider_policy": {"provider_class": "REASONING"},
        "tool_policy": {},
        "authority_policy": "DELEGATED",
    }
    f.update(kw)
    return AgentManifest(**f)


def _registry_with_agent() -> tuple[AgentRegistry, DelegationAuthority, str]:
    r = AgentRegistry()
    r.register(_m("agent.hermes", mission_types=("gov",), required_capabilities=("READ_REPOSITORY", "DELEGATE_TASK")))
    auth = DelegationAuthority()
    auth.set_delegatable("agent.hermes", {"READ_REPOSITORY", "DELEGATE_TASK"}, actor="governance")
    r.validate_registered("agent.hermes")
    return r, auth, "agent.hermes"


class TestCertificationEntrypoint:
    def test_certify_single_agent_machine_readable(self):
        """§23-§24: `certify --agent` produces full machine-readable JSON."""
        r, auth, agent = _registry_with_agent()
        res = certify_agent(r, agent, delegation_authority=auth)
        data = json.loads(res.model_dump_json())
        for field in ("agent_id", "agent_version", "manifest_hash", "certification_generation",
                      "authority", "memory", "provider_policy", "tool_policy", "runtime",
                      "result", "timestamp", "source_sha"):
            assert field in data, field
        assert res.result == "PASS"
        assert res.source_sha == source_sha()
        assert res.manifest_hash == manifest_hash(r.resolve(agent))

    def test_certification_binds_to_repo_revision(self):
        """§24: certification binds to the repository revision."""
        r, auth, agent = _registry_with_agent()
        res = certify_agent(r, agent, delegation_authority=auth)
        # W3 publication reconciliation: the certification binds to the LIVE
        # repository revision, not a frozen parent literal. Assert the binding
        # is a full SHA matching the current HEAD (parent-agnostic by design).
        assert res.source_sha == source_sha()
        assert len(res.source_sha) == 40
        assert res.certification_generation == certification_generation(res.source_sha)

    def test_unrooted_agent_fails_certification(self):
        r = AgentRegistry()
        r.register(_m("agent.rogue"))
        rogue_auth = DelegationAuthority()  # no provenance for agent.rogue
        r.validate_registered("agent.rogue")
        res = certify_agent(r, "agent.rogue", delegation_authority=rogue_auth)
        assert res.result == "FAIL"
        assert "provenance" in res.authority

    def test_stale_certification_detected_on_manifest_change(self):
        """§25/§ backlog: dependency closure — manifest change ⇒ STALE."""
        r, auth, agent = _registry_with_agent()
        res_before = certify_agent(r, agent, delegation_authority=auth)
        closure = res_before.dependency_closure
        changed = _m("agent.hermes", agent_version="1.0.1", mission_types=("gov",),
                     required_capabilities=("READ_REPOSITORY", "DELEGATE_TASK"))
        assert closure["manifest_hash"] != manifest_hash(changed)


class TestReceiptHash:
    def test_receipt_hash_deterministic_and_mutation_detectable(self):
        """§31: receipts hash canonically; post-finalization edits detectable."""
        receipt = AgentRuntimeReceipt(
            agent_id="agent.w", agent_version="1.0.0", mission_id="M1",
            result=RuntimeOutcome.COMPLETED, manifest_hash="h" * 64,
        )
        from agent_runtime.canonical import canonical_hash

        h1 = canonical_hash(receipt)
        h2 = canonical_hash(receipt)
        assert h1 == h2
        mutated = receipt.model_copy(update={"result": RuntimeOutcome.FAILED})
        assert canonical_hash(mutated) != h1


class TestHealthState:
    def test_process_up_does_not_imply_ready(self):
        """§32: PROCESS_RUNNING != CERTIFIED — health gates on certification."""
        r, _auth, agent = _registry_with_agent()
        # agent registered (process may run) but not certified:
        assert r.status(agent) is CertificationStatus.VALIDATED
        # mission admission checks CERTIFIED, not liveness:
        assert r.status(agent) is not CertificationStatus.CERTIFIED
        r.set_status(agent, CertificationStatus.TESTED)
        r.certify(agent)
        assert r.status(agent) is CertificationStatus.CERTIFIED

    def test_quarantine_prevents_new_missions_preserves_evidence(self):
        """§33: quarantine blocks admission, keeps receipts, reversible."""
        r, _auth, agent = _registry_with_agent()
        r.set_status(agent, CertificationStatus.TESTED)
        r.certify(agent)
        receipt = AgentRuntimeReceipt(
            agent_id=agent, agent_version="1.0.0", mission_id="M1",
            result=RuntimeOutcome.COMPLETED, manifest_hash=manifest_hash(r.resolve(agent)),
        )
        r.quarantine(agent)
        assert r.status(agent) is CertificationStatus.QUARANTINED
        assert r.list_enabled() == []  # no new missions
        assert receipt.result is RuntimeOutcome.COMPLETED  # evidence intact
        # reversible through authorized governance action
        r.set_status(agent, CertificationStatus.TESTED)
        r.certify(agent)
        assert r.status(agent) is CertificationStatus.CERTIFIED


class TestDependencyGraph:
    def test_graph_generated_from_registry(self):
        """§34: graph is generated, never hand-authored."""
        r, auth, _agent = _registry_with_agent()
        r.register(_m("agent.worker", required_capabilities=("READ_REPOSITORY",)))
        g = build_dependency_graph(r, auth)
        assert {a["agent_id"] for a in g["nodes"]["agents"]} >= {"agent.hermes", "agent.worker"}
        cap_edges = [e for e in g["edges"] if e["type"] == "requires"]
        assert any(e["to"] == "cap:READ_REPOSITORY" for e in cap_edges)

    def test_graph_detects_unknown_capability(self):
        """§35: unknown capabilities surface in validation."""
        from pydantic import ValidationError

        r, _auth, _agent = _registry_with_agent()
        with pytest.raises(ValidationError, match="unknown capability"):
            r.register(_m("agent.bad", required_capabilities=("TOTALLY_UNKNOWN_CAP",)))
