"""Wave 3D CHECKPOINT — Hermes delegation certification (§9-§10).

Required: CHILD_CAPABILITY ⊆ HERMES_DELEGATABLE_CAPABILITY with negatives:
undeclared child capability, Hermes-forbidden capability, expired
delegation, wrong mission, wrong tenant, wrong resource, mutated
delegation payload, missing approval, replayed approval — all REFUSED.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from agent_runtime.delegation import DelegationAuthority, DelegationRefusedError
from agent_runtime.manifest import AgentManifest


def _manifest(agent_id: str, **kw) -> AgentManifest:
    fields = {
        "agent_id": agent_id,
        "agent_version": "1.0.0",
        "display_name": agent_id,
        "owner": "sintraprime.principal",
        "runtime_class": "tests.Fake",
        "mission_types": ("generic",),
        "provider_policy": {"provider_class": "REASONING"},
        "tool_policy": {},
        "authority_policy": "DELEGATED",
    }
    fields.update(kw)
    return AgentManifest(**fields)


HERMES_DELEGATABLE = frozenset({"READ_REPOSITORY", "RUN_TESTS", "SEARCH_WEB", "REQUEST_MEMORY_WRITE", "DELEGATE_TASK"})


@pytest.fixture
def auth() -> DelegationAuthority:
    a = DelegationAuthority()
    a.set_delegatable("agent.hermes", HERMES_DELEGATABLE, actor="governance")
    return a


def _issue(auth, child=None, **kw):
    return auth.issue(
        parent_agent="agent.hermes",
        child_manifest=child or _manifest("agent.worker"),
        delegation_id=kw.pop("delegation_id", "dh"),
        mission_id=kw.pop("mission_id", "M1"),
        capabilities=kw.pop("capabilities", ["READ_REPOSITORY"]),
        tenant=kw.pop("tenant", "t1"),
        **kw,
    )


class TestHermesSubsetInvariant:
    def test_child_subset_of_hermes_delegatable(self, auth):
        d = _issue(auth, capabilities=["READ_REPOSITORY", "RUN_TESTS"])
        assert d.capabilities <= HERMES_DELEGATABLE

    def test_undeclared_child_capability_refused(self, auth):
        with pytest.raises(DelegationRefusedError, match="not delegable"):
            _issue(auth, capabilities=["SEND_EMAIL"])

    def test_hermes_forbidden_capability_refused(self, auth):
        hermes = _manifest("agent.hermes", forbidden_capabilities=("EXECUTE_PAYMENT",))
        with pytest.raises(DelegationRefusedError):
            auth.issue(
                parent_agent="agent.hermes",
                child_manifest=hermes,
                delegation_id="df",
                mission_id="M1",
                capabilities=["EXECUTE_PAYMENT"],
            )


class TestHermesBindingNegatives:
    def _d(self, auth, **kw):
        return _issue(auth, **kw)

    def test_expired_refused(self, auth):
        d = self._d(auth, issued_at=datetime.now(UTC) - timedelta(hours=3), ttl_seconds=3600)
        with pytest.raises(DelegationRefusedError, match="expired"):
            auth.check_use(d, capability="READ_REPOSITORY", mission_id="M1", tenant="t1")

    def test_wrong_mission_refused(self, auth):
        d = self._d(auth)
        with pytest.raises(DelegationRefusedError, match="mission mismatch"):
            auth.check_use(d, capability="READ_REPOSITORY", mission_id="OTHER", tenant="t1")

    def test_wrong_tenant_refused(self, auth):
        d = self._d(auth)
        with pytest.raises(DelegationRefusedError, match="tenant mismatch"):
            auth.check_use(d, capability="READ_REPOSITORY", mission_id="M1", tenant="t2")

    def test_wrong_resource_refused(self, auth):
        d = self._d(auth, resource_scope=("src/*",))
        with pytest.raises(DelegationRefusedError, match="outside delegation scope"):
            auth.check_use(d, capability="READ_REPOSITORY", mission_id="M1", tenant="t1", resource="portal/secrets.env")

    def test_mutated_delegation_payload_detected(self, auth):
        """§10: a copied delegation object re-bound to another mission
        cannot pass — its payload hash differs from the issued one."""
        d = self._d(auth)
        issued_hash = auth.delegation_payload_hash(d)
        # attacker "mutates" the payload: same object re-bound to mission M2
        mutated = d.model_copy(update={"mission_id": "M2"})
        assert auth.delegation_payload_hash(mutated) != issued_hash
        # and the runtime check refuses the mutated object BEFORE any use:
        with pytest.raises(DelegationRefusedError, match="DELEGATION_PAYLOAD_MUTATED"):
            auth.check_use(mutated, capability="READ_REPOSITORY", mission_id="M2", tenant="t1")

    def test_missing_approval_refused_for_consequential_delegation(self, auth):
        with pytest.raises(DelegationRefusedError, match="MISSING_APPROVAL"):
            self._d(auth, capabilities=["DELEGATE_TASK"], require_approval=True)

    def test_present_approval_issued(self, auth):
        d = self._d(
            auth,
            capabilities=["DELEGATE_TASK"],
            require_approval=True,
            approval_reference="apr-77",
        )
        assert d.approval_reference == "apr-77"


class TestApprovalReplay:
    def test_replayed_approval_one_delegation_only(self, auth):
        """§9: an approval reference is single-use at the delegation layer —
        a second delegation with the SAME approval reference is REFUSED."""
        issued = auth.issue(
            parent_agent="agent.hermes",
            child_manifest=_manifest("agent.w1"),
            delegation_id="dr1",
            mission_id="M1",
            capabilities=["DELEGATE_TASK"],
            tenant="t1",
            require_approval=True,
            approval_reference="apr-replay-1",
        )
        assert issued.approval_reference == "apr-replay-1"
        auth.consume_approval("apr-replay-1")
        with pytest.raises(DelegationRefusedError, match=r"replayed|consumed"):
            auth.issue(
                parent_agent="agent.hermes",
                child_manifest=_manifest("agent.w2"),
                delegation_id="dr2",
                mission_id="M1",
                capabilities=["DELEGATE_TASK"],
                tenant="t1",
                require_approval=True,
                approval_reference="apr-replay-1",
            )

    def test_fresh_approval_succeeds_after_replay_attempt(self, auth):
        auth.consume_approval("apr-x")  # mark used
        auth._consumed_approvals.clear()
        d = auth.issue(
            parent_agent="agent.hermes",
            child_manifest=_manifest("agent.w1"),
            delegation_id="dr3",
            mission_id="M1",
            capabilities=["DELEGATE_TASK"],
            tenant="t1",
            require_approval=True,
            approval_reference="apr-y",
        )
        assert d.approval_reference == "apr-y"
