"""Wave 3 AUTHORITY + NEGATIVE layers — delegation subset invariant, self-grant,
mission/tenant/capability/expiry negatives (§16-§17, §10, §43-§44)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from agent_runtime.delegation import DelegationAuthority, DelegationRefusedError
from agent_runtime.manifest import AgentManifest


def _manifest(agent_id: str, forbidden: tuple[str, ...] = ()) -> AgentManifest:
    return AgentManifest(
        agent_id=agent_id,
        agent_version="1.0.0",
        display_name=agent_id,
        owner="sintraprime.principal",
        runtime_class="tests.Fake",
        mission_types=("generic",),
        forbidden_capabilities=forbidden,
        provider_policy={"provider_class": "REASONING"},
        tool_policy={},
        authority_policy="DELEGATED",
    )


@pytest.fixture
def auth() -> DelegationAuthority:
    a = DelegationAuthority()
    a.set_delegatable("agent.hermes", {"READ_REPOSITORY", "RUN_TESTS", "SEARCH_WEB"}, actor="governance")
    return a


class TestSubsetInvariant:
    def test_subset_invariant_holds(self, auth):
        child = _manifest("agent.worker")
        d = auth.issue(
            parent_agent="agent.hermes",
            child_manifest=child,
            delegation_id="d1",
            mission_id="M1",
            capabilities=["READ_REPOSITORY", "RUN_TESTS"],
            tenant="t1",
        )
        assert d.capabilities <= auth.delegatable("agent.hermes")

    def test_child_undelegated_capability_refused(self, auth):
        child = _manifest("agent.worker")
        with pytest.raises(DelegationRefusedError, match="not delegable"):
            auth.issue(
                parent_agent="agent.hermes",
                child_manifest=child,
                delegation_id="d2",
                mission_id="M1",
                capabilities=["SEND_EMAIL"],  # parent cannot delegate this
            )

    def test_parent_forbidden_capability_never_delegated(self, auth):
        child = _manifest("agent.worker")
        with pytest.raises(DelegationRefusedError):
            auth.issue(
                parent_agent="agent.hermes",
                child_manifest=child,
                delegation_id="d3",
                mission_id="M1",
                capabilities=["MERGE_PULL_REQUEST"],
            )

    def test_child_forbidden_capability_refused(self, auth):
        child = _manifest("agent.worker", forbidden=("RUN_TESTS",))
        with pytest.raises(DelegationRefusedError, match="forbidden for child"):
            auth.issue(
                parent_agent="agent.hermes",
                child_manifest=child,
                delegation_id="d3b",
                mission_id="M1",
                capabilities=["RUN_TESTS"],
            )


class TestSelfGrant:
    def test_agent_cannot_extend_own_authority(self, auth):
        with pytest.raises(DelegationRefusedError, match="SELF_GRANT"):
            auth.set_delegatable("agent.hermes", {"SEND_EMAIL"}, actor="agent.hermes")

    def test_governance_actor_may_extend(self, auth):
        auth.set_delegatable("agent.hermes", {"SEND_EMAIL"}, actor="governance")
        assert "SEND_EMAIL" in auth.delegatable("agent.hermes")

    def test_self_delegation_refused(self, auth):
        hermes = _manifest("agent.hermes")
        with pytest.raises(DelegationRefusedError, match="itself"):
            auth.issue(
                parent_agent="agent.hermes",
                child_manifest=hermes,
                delegation_id="d4",
                mission_id="M1",
                capabilities=["READ_REPOSITORY"],
            )


class TestUseChecks:
    def _delegation(self, auth, **kw):
        child = _manifest("agent.worker")
        return auth.issue(
            parent_agent="agent.hermes",
            child_manifest=child,
            delegation_id="d9",
            mission_id="M1",
            capabilities=["READ_REPOSITORY"],
            tenant="t1",
            **kw,
        )

    def test_valid_use_passes(self, auth):
        d = self._delegation(auth)
        auth.check_use(d, capability="READ_REPOSITORY", mission_id="M1", tenant="t1")

    def test_expired_delegation_refused(self, auth):
        d = self._delegation(auth, issued_at=datetime.now(UTC) - timedelta(hours=2), ttl_seconds=3600)
        with pytest.raises(DelegationRefusedError, match="expired"):
            auth.check_use(d, capability="READ_REPOSITORY", mission_id="M1", tenant="t1")

    def test_wrong_mission_refused(self, auth):
        d = self._delegation(auth)
        with pytest.raises(DelegationRefusedError, match="mission mismatch"):
            auth.check_use(d, capability="READ_REPOSITORY", mission_id="OTHER", tenant="t1")

    def test_wrong_tenant_refused(self, auth):
        d = self._delegation(auth)
        with pytest.raises(DelegationRefusedError, match="tenant mismatch"):
            auth.check_use(d, capability="READ_REPOSITORY", mission_id="M1", tenant="other-tenant")

    def test_wrong_capability_refused(self, auth):
        d = self._delegation(auth)
        with pytest.raises(DelegationRefusedError, match="not delegated"):
            auth.check_use(d, capability="SEARCH_WEB", mission_id="M1", tenant="t1")

    def test_resource_outside_scope_refused(self, auth):
        d = self._delegation(auth, resource_scope=("src/app/*",))
        auth.check_use(d, capability="READ_REPOSITORY", mission_id="M1", tenant="t1", resource="src/app/main.py")
        with pytest.raises(DelegationRefusedError, match="outside delegation scope"):
            auth.check_use(d, capability="READ_REPOSITORY", mission_id="M1", tenant="t1", resource="portal/secrets.env")

    def test_zero_ttl_refused(self, auth):
        with pytest.raises(DelegationRefusedError, match="TTL"):
            self._delegation(auth, ttl_seconds=0)
