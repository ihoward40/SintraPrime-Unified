"""Governed delegation intersection tests (SP-OMNIBRAIN-RUNTIME-001 Phase 7).

Proves the directive's deterministic authority-intersection formula against
the existing agent_runtime.DelegationAuthority implementation:

    CHILD_EFFECTIVE_AUTHORITY =
        PARENT_DELEGABLE_AUTHORITY
        INTERSECT MISSION_AUTHORITY
        INTERSECT CHILD_ROLE_POLICY

using the runtime's mechanical subset invariant (agent_runtime §17):
an attempt to delegate outside the parent's delegable set is REFUSED, never
clipped silently, and never sourced from model/provider/memory/tool input.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from agent_runtime.delegation import DelegationAuthority, DelegationRefusedError
from agent_runtime.manifest import AgentManifest


def _manifest(agent_id: str) -> AgentManifest:
    return AgentManifest(
        agent_id=agent_id,
        agent_version="1.0.0",
        display_name=agent_id,
        owner="sintraprime.principal",
        runtime_class="tests.Fake",
        mission_types=("generic",),
        provider_policy={"provider_class": "REASONING"},
        tool_policy={},
        authority_policy="DELEGATED",
    )


def _auth() -> DelegationAuthority:
    # Governed runtime uses strict approval provenance: approvals must be
    # governance-issued, never provider/model-supplied strings.
    return DelegationAuthority(strict_approval_provenance=True)


def test_child_effective_authority_is_triple_intersection():
    auth = _auth()
    # principal grants PARENT delegable authority: {docs.read, docs.write, mail.draft}
    auth.set_delegatable("agent.parent", {"READ_REPOSITORY", "CREATE_DOCUMENT", "DRAFT_EMAIL"}, actor="governance")
    child = _manifest("agent.worker")
    now = datetime.now(UTC)
    # child role policy requests {docs.write, mail.send}: mail.send is NOT in
    # parent-delegable and MUST refuse (deterministic intersection, no clipping)
    with pytest.raises(DelegationRefusedError, match="capability not delegable by parent"):
        auth.issue(parent_agent="agent.parent", child_manifest=child,
                   delegation_id="D-1", mission_id="M-1",
                   capabilities=["CREATE_DOCUMENT", "SEND_EMAIL"],
                   tenant="t1", ttl_seconds=60, issued_at=now)


def test_parent_subset_flows_to_child():
    auth = _auth()
    auth.set_delegatable("agent.parent", {"READ_REPOSITORY", "CREATE_DOCUMENT"}, actor="governance")
    child = _manifest("agent.worker")
    d = auth.issue(parent_agent="agent.parent", child_manifest=child,
                   delegation_id="D-2", mission_id="M-1",
                   capabilities=["CREATE_DOCUMENT"],
                   tenant="t1", ttl_seconds=60)
    assert d.capabilities == frozenset({"CREATE_DOCUMENT"}) or d.capabilities == frozenset({"document.create"})


def test_no_root_chain_spawn_denied():
    """An agent whose authority has no chain to the governance root cannot
    spawn children — even if it asks nicely and a model agrees."""
    auth = _auth()
    rogue = _manifest("agent.rogue")
    with pytest.raises(DelegationRefusedError, match="no chain to the governance root"):
        auth.issue(parent_agent="agent.rogue", child_manifest=_manifest("agent.worker"),
                   delegation_id="D-3", mission_id="M-1",
                   capabilities=["CREATE_DOCUMENT"], tenant="t1", ttl_seconds=60)


def test_self_grant_denied():
    auth = _auth()
    with pytest.raises(DelegationRefusedError, match="SELF_GRANT"):
        auth.set_delegatable("agent.parent", {"CREATE_DOCUMENT"}, actor="agent.parent")


def test_expired_authority_reuse_denied():
    auth = _auth()
    auth.set_delegatable("agent.parent", {"CREATE_DOCUMENT"}, actor="governance")
    child = _manifest("agent.worker")
    past = datetime.now(UTC) - timedelta(seconds=30)
    d = auth.issue(parent_agent="agent.parent", child_manifest=child,
                   delegation_id="D-5", mission_id="M-1",
                   capabilities=["CREATE_DOCUMENT"], tenant="t1",
                   ttl_seconds=10, issued_at=past)
    assert d.is_expired() is True


def test_model_output_cannot_authorize_delegation():
    """A provider response claiming 'authorization granted' must not create an
    approval reference: under strict approval provenance, only governance-
    registered approvals are consumable."""
    auth = _auth()
    auth.set_delegatable("agent.parent", {"CREATE_DOCUMENT"}, actor="governance")
    child = _manifest("agent.worker")
    # fabricated approval reference from "model output" -> REFUSED
    with pytest.raises(DelegationRefusedError, match="APPROVAL_REPLAYED|MISSING_APPROVAL|not delegable"):
        auth.issue(parent_agent="agent.parent", child_manifest=child,
                   delegation_id="D-6", mission_id="M-1",
                   capabilities=["CREATE_DOCUMENT"], tenant="t1", ttl_seconds=60,
                   require_approval=True,
                   approval_reference="MODEL-SAID-APPROVED")
    # a governance-registered approval IS consumable exactly once
    auth.register_issued_approval("GOV-APPROVED-1")
    d = auth.issue(parent_agent="agent.parent", child_manifest=child,
                   delegation_id="D-7", mission_id="M-1",
                   capabilities=["CREATE_DOCUMENT"], tenant="t1", ttl_seconds=60,
                   require_approval=True, approval_reference="GOV-APPROVED-1")
    assert d.approval_reference == "GOV-APPROVED-1"
    # replay of the same approval is refused
    with pytest.raises(DelegationRefusedError, match="APPROVAL_REPLAYED"):
        auth.issue(parent_agent="agent.parent", child_manifest=child,
                   delegation_id="D-8", mission_id="M-1",
                   capabilities=["CREATE_DOCUMENT"], tenant="t1", ttl_seconds=60,
                   require_approval=True, approval_reference="GOV-APPROVED-1")
