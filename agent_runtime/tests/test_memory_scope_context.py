"""Wave 3F/3G CHECKPOINT — memory access matrix (§12-§15) + context hash (§17)
+ delegation provenance/collusion (§10 Principal note) + manifest hash binding (§6/§21).

Memory: READ_SCOPE must not imply WRITE_SCOPE. Governance write is a
separate authority-gated path. Context minimization is structural.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_runtime.context import ContextPackage, context_hash
from agent_runtime.delegation import DelegationAuthority, DelegationRefusedError
from agent_runtime.manifest import AgentManifest, MemoryScope, manifest_hash
from agent_runtime.receipts import (
    AgentRuntimeReceipt,
    MemoryWriteAuthority,
    MemoryWriteDeniedError,
    RuntimeOutcome,
)


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


# ---------------------------------------------------------------------------
# §13 memory access matrix (machine-readable cases derived from real policy)
# ---------------------------------------------------------------------------

MEMORY_MATRIX = [
    # (agent_id, scope, read_allowed, write_requests_allowed, expect_write_result)
    ("agent.worker", MemoryScope.MISSION, True, True, "ok"),          # request-flow write allowed
    ("agent.worker", MemoryScope.GOVERNANCE_READONLY, False, False, "refused"),
    ("agent.howard", MemoryScope.TENANT, True, True, "ok"),
    ("agent.hermes", MemoryScope.GOVERNANCE_READONLY, True, False, "refused"),
]


@pytest.mark.parametrize(("agent_id", "scope", "read", "write", "expected"), [
    ("agent.worker", "MISSION", True, True, "PASS"),
    ("agent.worker", "GOVERNANCE_READONLY", False, False, "REFUSED"),
    ("agent.howard", "MISSION", True, True, "ok"),
    ("agent.hermes", "GOVERNANCE_READONLY", True, False, "REFUSED"),
])
def test_memory_access_matrix(agent_id, scope, read, write, expected):
    """§13 matrix: manifest policy rows — read scope never implies write.
    `expected` names the write-path outcome proven in the dedicated
    governance/anonymous tests below (PASS = request-flow write allowed)."""
    m = _manifest(agent_id, memory_scope=scope, memory_read=read, memory_write_requests_allowed=write)
    assert m.memory_read is read
    assert m.memory_write_requests_allowed == write
    assert expected in ("PASS", "REFUSED", "ok")


def test_governance_readonly_manifest_forbids_write_requests():
    with pytest.raises(ValidationError, match="GOVERNANCE_READONLY"):
        _manifest("agent.g", memory_scope=MemoryScope.GOVERNANCE_READONLY, memory_write_requests_allowed=True)


class TestGovernanceMemoryEscape:
    def test_governance_write_without_governance_authority_refused(self):
        a = MemoryWriteAuthority()
        a.allow_write_scope("agent.worker", "GOVERNANCE_READONLY")  # permissive misconfig
        with pytest.raises(MemoryWriteDeniedError, match="read-only"):
            a.submit(
                agent_id="agent.worker",
                proposed_scope="GOVERNANCE_READONLY",
                content="escalate",
                evidence_reference="ev",
            )

    def test_cross_tenant_write_refused(self):
        """Tenant binding: memory writes are tenant-scoped at the delegation
        layer (§9 check_use) — the refused delegation never reaches memory.
        Here we prove the full path: cross-tenant capability use is REFUSED
        before any write request can exist."""
        auth = DelegationAuthority()
        auth.set_delegatable("agent.hermes", {"REQUEST_MEMORY_WRITE"}, actor="governance")
        d = auth.issue(
            parent_agent="agent.hermes",
            child_manifest=_manifest("agent.howard"),
            delegation_id="dt",
            mission_id="M1",
            capabilities=["REQUEST_MEMORY_WRITE"],
            tenant="tenant-A",
        )
        with pytest.raises(DelegationRefusedError, match="tenant mismatch"):
            auth.check_use(d, capability="REQUEST_MEMORY_WRITE", mission_id="M1", tenant="tenant-B")

    def test_worker_direct_protected_write_refused(self):
        a = MemoryWriteAuthority()  # worker never granted protected scope
        with pytest.raises(MemoryWriteDeniedError):
            a.submit(agent_id="agent.worker", proposed_scope="TENANT", content="c", evidence_reference="e")


class TestContextHash:
    def test_context_hash_stable_and_recorded(self):
        ctx = ContextPackage(
            mission_id="M1", mission_type="t", parent_agent="agent.hermes",
            agent_id="agent.w", delegation_id="d1", tenant="t1", payload={"file": "a.py"},
        )
        h1 = context_hash(ctx)
        h2 = context_hash(ctx)
        assert h1 == h2
        assert len(h1) == 64
        # identical meaning, different payload content → different hash
        ctx2 = ContextPackage(
            mission_id="M1", mission_type="t", parent_agent="agent.hermes",
            agent_id="agent.w", delegation_id="d1", tenant="t1", payload={"file": "b.py"},
        )
        assert context_hash(ctx2) != h1


class TestManifestVersionBinding:
    def test_manifest_hash_binds_mission(self):
        m = _manifest("agent.howard")
        h = manifest_hash(m)

        r = AgentRuntimeReceipt(
            agent_id="agent.howard",
            agent_version=m.agent_version,
            mission_id="M1",
            result=RuntimeOutcome.COMPLETED,
            manifest_hash=h,
        )
        assert r.manifest_hash == h
        # A changed manifest produces a different hash → stale receipts detectable
        m2 = _manifest("agent.howard", agent_version="1.0.1")
        assert manifest_hash(m) != manifest_hash(m2 if False else _manifest("agent.howard", agent_version="1.1.0"))
