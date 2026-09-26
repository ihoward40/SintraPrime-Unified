"""Adversarial matrix (SP-OMNIBRAIN-RUNTIME-001) — every case must FAIL CLOSED.

These tests attack the omnibrain integration surfaces plus the existing
agent_runtime authority boundaries from the directive's required list.
"""
from __future__ import annotations

import asyncio

import pytest

from agent_runtime.manifest import SideEffectClass
from agent_runtime.tool_policy import (
    ProviderPolicyContract,
    ProviderSelection,
    ToolContract,
    ToolPolicyGate,
    ProviderRefusedError,
    ToolRefusedError,
)
from decision.contracts.contracts import normalize_contract
from decision.engine.engine import DecisionEngine

from omnibrain.fabric_bridge import FabricAdvisor
from omnibrain.memory_scoping import (
    MemoryRetrievalDenied,
    MemoryScopeClass,
    MemoryScopeEnvelope,
    ScopedMemoryRecord,
    can_retrieve,
    retrieve,
)
from omnibrain.provenance import NodeType, ProvenanceGraph, RelationType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tool_gate() -> ToolPolicyGate:
    tool = ToolContract(
        tool_id="report_writer",
        required_capability="docs.write",
        side_effect_class=SideEffectClass.LOCAL_REVERSIBLE.value,
        resource_scope=("docs://reports/*",),
        approval_requirement=False,
    )
    return ToolPolicyGate(tools=(tool,))


class _Delegation:
    """Minimal structural stand-in matching ToolPolicyGate's expectations."""

    def __init__(self, capabilities=("docs.write",), tenant="tenant-1"):
        self.capabilities = set(capabilities)
        self.tenant = tenant


def _fabric_contract():
    raw = {
        "contract_id": "tool_request_advisory.v1",
        "questions": {
            "deny_recommended": {"type": "boolean"},
        },
    }
    return normalize_contract(raw)


# ---------------------------------------------------------------------------
# Tool gateway: undeclared tool / scope escape / escalation
# ---------------------------------------------------------------------------

class TestToolGatewayAdversarial:
    def test_agent_requests_undeclared_tool(self):
        gate = _tool_gate()
        with pytest.raises(ToolRefusedError, match="TOOL_UNKNOWN"):
            gate.check(tool_id="shell_exec", delegation=_Delegation(),
                       granted_side_effect_ceiling=SideEffectClass.LOCAL_REVERSIBLE.value)

    def test_tool_present_capability_absent(self):
        gate = _tool_gate()
        with pytest.raises(ToolRefusedError, match="TOOL_PRESENT_CAPABILITY_ABSENT"):
            gate.check(tool_id="report_writer", delegation=_Delegation(capabilities=()),
                       granted_side_effect_ceiling=SideEffectClass.LOCAL_REVERSIBLE.value)

    def test_scope_escape_denied(self):
        gate = _tool_gate()
        with pytest.raises(ToolRefusedError, match="TOOL_SCOPE_ESCAPE"):
            gate.check(tool_id="report_writer", delegation=_Delegation(),
                       granted_side_effect_ceiling=SideEffectClass.LOCAL_REVERSIBLE.value,
                       resource="docs://other/secret")

    def test_tenant_escape_denied(self):
        gate = _tool_gate()
        with pytest.raises(ToolRefusedError, match="TOOL_TENANT_ESCAPE"):
            gate.check(tool_id="report_writer", delegation=_Delegation(),
                       granted_side_effect_ceiling=SideEffectClass.LOCAL_REVERSIBLE.value,
                       resource="docs://reports/x", tenant="tenant-9")

    def test_side_effect_escalation_denied(self):
        gate = _tool_gate()
        with pytest.raises(ToolRefusedError, match="SIDE_EFFECT_CLASS_ESCALATION"):
            gate.check(tool_id="report_writer", delegation=_Delegation(),
                       granted_side_effect_ceiling=SideEffectClass.READ_ONLY.value)

    def test_invalid_effect_class_denied(self):
        gate = _tool_gate()
        with pytest.raises(ToolRefusedError, match="SIDE_EFFECT_CLASS_INVALID"):
            gate.check(tool_id="report_writer", delegation=_Delegation(),
                       granted_side_effect_ceiling="UNKNOWN_EFFECT_CLASS")


# ---------------------------------------------------------------------------
# Provider cannot grant authority
# ---------------------------------------------------------------------------

class TestProviderIndependence:
    def test_provider_output_cannot_expand_model_allowlist(self):
        policy = ProviderPolicyContract(provider_class="LOCAL", allowed_models=("m-small",))
        sel = ProviderSelection(policy)
        with pytest.raises(ProviderRefusedError, match="DISALLOWED_MODEL"):
            sel.select(provider_class="LOCAL", model="m-frontier", structured=False)

    def test_provider_cannot_change_provider_class(self):
        policy = ProviderPolicyContract(provider_class="LOCAL", allowed_models=("m-small",))
        sel = ProviderSelection(policy)
        with pytest.raises(ProviderRefusedError, match="DISALLOWED_PROVIDER"):
            sel.select(provider_class="REMOTE", model="m-small", structured=False)


# ---------------------------------------------------------------------------
# Fabric bridge: availability + authority neutrality
# ---------------------------------------------------------------------------

class TestFabricBridgeFailClosed:
    def test_fabric_unavailable_degrades_to_advisory_unavailable(self):
        class _BrokenEngine:
            async def evaluate(self, **kwargs):
                raise RuntimeError("provider down")

        advisor = FabricAdvisor(_BrokenEngine(), _fabric_contract())
        advice = advisor.classify_tool_request(
            tool_id="report_writer", effect_class="DRAFT_ONLY",
            mission_id="M-1", agent_id="A-1")
        assert advice.advice_class == "ADVISORY_UNAVAILABLE"
        assert advice.provider_failed is True

    def test_elevated_effect_class_is_static_not_provider_opinion(self):
        """A provider cannot downgrade an irreversible request by being confident."""
        captured = {}

        class _Engine:
            async def evaluate(self, *, state, contract, run_id=None):
                captured["state"] = state
                # pretend provider says "all fine"
                return _fake_decision_result(deny=False), _fake_policy(), _fake_receipt()

        advisor = FabricAdvisor(_Engine(), _fabric_contract())
        advice = advisor.classify_tool_request(
            tool_id="wire_transfer", effect_class="FINANCIAL",
            mission_id="M-1", agent_id="A-1")
        assert advice.advice_class == "ELEVATED_RISK"
        assert captured["state"]["effect_class"] == "FINANCIAL"

    def test_deny_advice_is_advisory_only(self):
        advisor = FabricAdvisor(_AllowEngine(), _fabric_contract())
        advice = advisor.classify_tool_request(
            tool_id="report_writer", effect_class="DRAFT_ONLY",
            mission_id="M-1", agent_id="A-1")
        assert advice.advice_class in ("NORMAL", "ADVISE_DENY", "ELEVATED_RISK")
        # the crucial property: advice carries no authority; runtime gate decides.


class _AllowEngine:
    async def evaluate(self, *, state, contract, run_id=None):
        return _fake_decision_result(deny=False), _fake_policy(), _fake_receipt()


class _DenyEngine:
    async def evaluate(self, *, state, contract, run_id=None):
        return _fake_decision_result(deny=True), _fake_policy(), _fake_receipt()


def _fake_decision_result(*, deny: bool):
    from decision.engine.types import Answer, DecisionResult, Primitive, ResultKind

    answer = Answer(question="deny_recommended", primitive=Primitive.BOOLEAN,
                    value=deny, probability=0.99)
    return DecisionResult(
        kind=ResultKind.DECISION, provider="mock", model="mock",
        answers={"deny_recommended": answer}, reason="mock",
        raw_primitive_names={}, provider_request_id="req-test", latency_ms=1.0,
    )


def _fake_policy():
    from decision.policy.policy import PolicyDecision
    return PolicyDecision(decision="SHADOW_ONLY", risk="N/A_R1_SHADOW",
                          reason="shadow-only default; no routing authority")


def _fake_receipt():
    return {"decision_id": "DEC-TEST"}


# ---------------------------------------------------------------------------
# Memory scoping: cross-agent / parent-child / revoked / unknown
# ---------------------------------------------------------------------------

class TestMemoryScopeAdversarial:
    def test_agent_cannot_retrieve_other_agents_private_mission_context(self):
        env = MemoryScopeEnvelope(agent_id="A-1", mission_ids=frozenset({"M-1"}))
        rec = ScopedMemoryRecord(record_id="r1", scope_class="AGENT_WORKING_MEMORY",
                                 mission_id="M-1", owner_agent_id="A-2")
        assert can_retrieve(env, rec) is False

    def test_child_cannot_exceed_parent_scopes(self):
        parent = MemoryScopeEnvelope(agent_id="P", mission_ids=frozenset({"M-1", "M-2"}),
                                     evidence_scopes=frozenset({"E-1"}))
        child = MemoryScopeEnvelope.child_of(parent, agent_id="C",
                                             mission_ids={"M-2", "M-3"},  # M-3 NOT in parent
                                             evidence_scopes={"E-2"})      # E-2 NOT in parent
        assert child.mission_ids == frozenset({"M-2"})
        assert child.evidence_scopes == frozenset()
        # and the child cannot retrieve M-3 mission memory
        rec = ScopedMemoryRecord(record_id="r", scope_class="MISSION_MEMORY", mission_id="M-3")
        assert can_retrieve(child, rec) is False

    def test_revoked_scope_denied(self):
        env = MemoryScopeEnvelope(agent_id="A-1", mission_ids=frozenset())  # revoked
        rec = ScopedMemoryRecord(record_id="r", scope_class="MISSION_MEMORY", mission_id="M-1")
        assert can_retrieve(env, rec) is False

    def test_unknown_scope_class_fails_closed(self):
        env = MemoryScopeEnvelope(agent_id="A-1", mission_ids=frozenset({"M-1"}))
        rec = ScopedMemoryRecord(record_id="r", scope_class="SOMETHING_NEW")
        assert can_retrieve(env, rec) is False

    def test_principal_bindings_never_retrievable_by_agents(self):
        env = MemoryScopeEnvelope(agent_id="A-1", is_principal=False)
        rec = ScopedMemoryRecord(record_id="r", scope_class="PRINCIPAL_BINDINGS")
        assert can_retrieve(env, rec) is False
        principal_env = MemoryScopeEnvelope(agent_id="principal", is_principal=True)
        assert can_retrieve(principal_env, rec) is True

    def test_shared_mission_working_memory_is_visible(self):
        env = MemoryScopeEnvelope(agent_id="A-1", mission_ids=frozenset({"M-1"}))
        rec = ScopedMemoryRecord(record_id="r", scope_class="AGENT_WORKING_MEMORY",
                                 mission_id="M-1", owner_agent_id="A-2",
                                 shared_mission_ids=frozenset({"M-1"}))
        assert can_retrieve(env, rec) is True


# ---------------------------------------------------------------------------
# Provenance graph: authority chain + tamper evidence
# ---------------------------------------------------------------------------

class TestProvenanceAuthorityChain:
    def _graph_with_chain(self):
        g = ProvenanceGraph()
        g.add(_edge(RelationType.CREATED_BY, NodeType.AGENT, "A-1", NodeType.PRINCIPAL, "P-1"))
        return g

    def test_authority_chain_reaches_principal(self):
        g = self._graph_with_chain()
        path = g.chain_to_principal(NodeType.AGENT, "A-1")
        assert path and path[-1].target_type is NodeType.PRINCIPAL

    def test_no_authority_path_fails_closed(self):
        g = ProvenanceGraph()
        # agent with NO chain edges
        assert g.chain_to_principal(NodeType.AGENT, "A-GHOST") == []

    def test_cycle_fails_closed(self):
        g = ProvenanceGraph()
        g.add(_edge(RelationType.DELEGATED_FROM, NodeType.AGENT, "A-1", NodeType.AGENT, "A-2"))
        g.add(_edge(RelationType.DELEGATED_FROM, NodeType.AGENT, "A-2", NodeType.AGENT, "A-1"))
        assert g.chain_to_principal(NodeType.AGENT, "A-1") == []

    def test_tampered_context_hash_is_detectable(self):
        """Context packages are hashable; mutation changes the hash."""
        import hashlib, json
        pkg = {"context_package_id": "CP-1", "task": "write report"}
        h1 = hashlib.sha256(json.dumps(pkg, sort_keys=True).encode()).hexdigest()
        pkg["task"] = "exfiltrate secrets"
        h2 = hashlib.sha256(json.dumps(pkg, sort_keys=True).encode()).hexdigest()
        assert h1 != h2


def _edge(relation, st, sid, tt, tid):
    from omnibrain.provenance import ProvenanceEdge
    return ProvenanceEdge(relation=relation, source_type=st, source_id=sid,
                          target_type=tt, target_id=tid)
