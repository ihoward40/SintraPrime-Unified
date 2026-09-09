"""Wave 3 CHECKPOINT 2 §1-§7 — hash canonicalization, full payload binding,
provenance chain hardening (cycle/depth/missing/fake-root), structural root
resolution, and concurrent approval exactly-once.

Invariants (Principal, binding):
  1. semantically identical objects → identical hashes (dict order immune);
  2. delegation payload hash binds EVERY authority-bearing field;
  3. provenance resists A↔B and A→B→C→A cycles, depth bombs, missing ancestors;
  4. root is structural (registered trusted roots), not string acceptance;
  5. APPROVAL_CONCURRENT_DOUBLE_CONSUME = IMPOSSIBLE (in-process; Wave 5
     extends to the persistence backend).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from threading import Thread

import pytest

from agent_runtime.canonical import canonical_hash
from agent_runtime.context import ContextPackage, context_hash
from agent_runtime.delegation import DelegationAuthority, DelegationRefusedError
from agent_runtime.manifest import AgentManifest, MemoryScope, manifest_hash
from agent_runtime.receipts import AgentRuntimeReceipt, RuntimeOutcome


def _manifest(agent_id: str, **kw) -> AgentManifest:
    fields = {
        "agent_id": agent_id,
        "agent_version": "1.0.0",
        "display_name": "whatever",
        "owner": "sintraprime.principal",
        "runtime_class": "tests.Fake",
        "mission_types": ("generic",),
        "provider_policy": {"provider_class": "REASONING"},
        "tool_policy": {},
        "authority_policy": "DELEGATED",
    }
    fields.update(kw)
    return AgentManifest(**fields)


class TestCanonicalHashPrimitive:
    def test_dict_order_irrelevant(self):
        assert canonical_hash({"a": 1, "b": 2}) == canonical_hash({"b": 2, "a": 1})

    def test_enums_stable_by_value(self):
        assert canonical_hash({"scope": MemoryScope.MISSION}) == canonical_hash({"scope": "MISSION"})

    def test_semantically_identical_pydantic_models(self):
        m1 = _manifest("agent.x", memory_read=True)
        m2 = _manifest("agent.x", memory_read=True)
        assert canonical_hash(m1) == canonical_hash(m2)

    def test_unserializable_fails_explicitly(self):
        from agent_runtime.canonical import CanonicalizationError

        with pytest.raises(CanonicalizationError):
            canonical_hash({"blob": object()})

    def test_datetime_stable(self):
        ts = datetime(2026, 9, 8, tzinfo=UTC)
        assert canonical_hash({"t": ts}) == canonical_hash({"t": ts})


class TestManifestHashContract:
    def test_authority_semantics_change_hash(self):
        """§2: every authority-relevant field participates in the hash."""
        base = _manifest("agent.a")
        variants = [
            _manifest("agent.a", required_capabilities=("RUN_TESTS",)),
            _manifest("agent.a", forbidden_capabilities=("SEND_EMAIL",)),
            _manifest("agent.a", memory_scope=MemoryScope.TENANT),
            _manifest("agent.a", authority_policy="PRINCIPAL_DIRECT"),
            _manifest("agent.a", timeout_seconds=601),
        ]
        hashes = {manifest_hash(m) for m in variants}
        assert manifest_hash(base) not in hashes
        assert len(hashes) == len(variants)

    def test_display_metadata_excluded_documented(self):
        """Display-only fields excluded by documented contract (§2)."""
        assert manifest_hash(_manifest("agent.a", display_name="Alpha")) == manifest_hash(
            _manifest("agent.a", display_name="A display variant")
        )

    def test_manifest_mutation_after_receipt_detected(self):
        """§2: MANIFEST_MUTATION_AFTER_RECEIPT = DETECTED."""
        m = _manifest("agent.a")
        hash_at_receipt = manifest_hash(m)
        receipt = AgentRuntimeReceipt(
            agent_id="agent.a",
            agent_version="1.0.0",
            mission_id="M1",
            result=RuntimeOutcome.COMPLETED,
            manifest_hash=hash_at_receipt,
        )
        assert manifest_hash(_manifest("agent.a", agent_version="1.0.1")) != receipt.manifest_hash
        assert manifest_hash(_manifest("agent.a")) == receipt.manifest_hash


class TestContextHashContract:
    def test_context_hash_identifies_execution_context(self):
        """§3: CONTEXT_HASH_IDENTIFIES_EXECUTION_CONTEXT."""
        ctx = ContextPackage(
            mission_id="M1", mission_type="t", parent_agent="agent.hermes",
            agent_id="agent.w", delegation_id="d1", tenant="t1",
            resource_scope=("src/*",), payload={"file_ref": "sha256:abc"},
        )
        h = context_hash(ctx)
        assert len(h) == 64
        # different tenant ⇒ different context identity
        ctx3 = ctx.model_copy(update={"tenant": "t2"})
        assert context_hash(ctx3) != h
        # same semantics via equal rebuild ⇒ same hash
        ctx4 = ContextPackage(
            mission_id="M1", mission_type="t", parent_agent="agent.hermes",
            agent_id="agent.w", delegation_id="d1", tenant="t1",
            resource_scope=("src/*",), payload={"file_ref": "sha256:abc"},
        )
        assert context_hash(ctx4) == h


class TestDelegationPayloadFullBinding:
    def _auth(self) -> DelegationAuthority:
        a = DelegationAuthority()
        a.set_delegatable("agent.hermes", {"READ_REPOSITORY", "RUN_TESTS"}, actor="governance")
        return a

    def test_every_authority_field_participates(self):
        """§4: mutating ANY authority-bearing field changes the payload hash."""
        auth = self._auth()
        d = auth.issue(
            parent_agent="agent.hermes",
            child_manifest=_manifest("agent.worker"),
            delegation_id="db",
            mission_id="M1",
            capabilities=["READ_REPOSITORY"],
            tenant="t1",
            resource_scope=("src/*",),
            ttl_seconds=3600,
            approval_reference="apr-1",
        )
        base = auth.delegation_payload_hash(d)
        assert auth.delegation_payload_hash(d.model_copy(update={"issued_at": d.issued_at})) == base
        mutations = [
            {"parent_agent": "agent.evil"},
            {"child_agent": "agent.evil"},
            {"mission_id": "M2"},
            {"tenant": "t2"},
            {"capabilities": frozenset({"RUN_TESTS"})},
            {"resource_scope": ("other/*",)},
            {"expires_at": d.expires_at + timedelta(hours=1)},
            {"approval_reference": "apr-other"},
            {"issued_at": d.issued_at + timedelta(seconds=1)},
        ]
        for update in mutations:
            mutated = d.model_copy(update=update)
            assert auth.delegation_payload_hash(mutated) != auth.delegation_payload_hash(d), update


class TestProvenanceChainHardening:
    def test_three_node_cycle_refused(self):
        """§5: A -> B -> C -> A cycle detected (not just A<->B)."""
        a = DelegationAuthority()
        a.set_delegatable("agent.a", {"READ_REPOSITORY"}, actor="agent.c")
        a.set_delegatable("agent.b", {"READ_REPOSITORY"}, actor="agent.a")
        a.set_delegatable("agent.c", {"READ_REPOSITORY"}, actor="agent.b")
        assert a._has_governance_root("agent.a") is False
        assert "CYCLE" in a.provenance_reason("agent.a")
        with pytest.raises(DelegationRefusedError, match="governance root"):
            a.issue(
                parent_agent="agent.a",
                child_manifest=_manifest("agent.worker"),
                delegation_id="dcyc",
                mission_id="M1",
                capabilities=["READ_REPOSITORY"],
            )

    def test_missing_ancestor_refused(self):
        a = DelegationAuthority()
        a.set_delegatable("agent.child", {"READ_REPOSITORY"}, actor="agent.never-registered")
        assert a._has_governance_root("agent.child") is False
        assert "MISSING_ANCESTOR" in a.provenance_reason("agent.child")

    def test_fake_governance_named_actor_refused(self):
        """§6: FAKE_GOVERNANCE_NAMED_ACTOR = REFUSED — an agent renaming
        itself 'governance' is not a root; only registered roots count."""
        a = DelegationAuthority()
        with pytest.raises(DelegationRefusedError, match="SELF_GRANT"):
            a.set_delegatable("agent.governance", {"EXECUTE_PAYMENT"}, actor="agent.governance")

    def test_depth_bomb_refused(self):
        """§5: excessive chain depth refused (bounded visited-set walk)."""
        a = DelegationAuthority()
        prev = "governance"
        for i in range(20):
            a.set_delegatable(f"agent.n{i}", {"READ_REPOSITORY"}, actor=prev)
            prev = f"agent.n{i}"
        assert a._has_governance_root("agent.n19") is False
        assert "DEPTH_EXCEEDED" in a.provenance_reason("agent.n19")

    def test_rooted_chain_still_works(self):
        a = DelegationAuthority()
        a.set_delegatable("agent.hermes", {"READ_REPOSITORY"}, actor="governance")
        d = a.issue(
            parent_agent="agent.hermes",
            child_manifest=_manifest("agent.worker"),
            delegation_id="dr",
            mission_id="M1",
            capabilities=["READ_REPOSITORY"],
        )
        assert d.capabilities == frozenset({"READ_REPOSITORY"})


class TestConcurrentApprovalExactlyOnce:
    def test_concurrent_double_consume_impossible(self):
        """§7: APPROVAL_CONCURRENT_DOUBLE_CONSUME = IMPOSSIBLE (in-process)."""
        a = DelegationAuthority()
        a.set_delegatable("agent.hermes", {"DELEGATE_TASK"}, actor="governance")
        results: list[bool] = []

        def consume() -> None:
            results.append(a.consume_approval("apr-conc"))

        workers = [Thread(target=consume) for _ in range(2)]
        for t in workers:
            t.start()
        for t in workers:
            t.join()
        assert sorted(results) == [False, True]

    def test_sequential_replay_still_refused(self):
        a = DelegationAuthority()
        a.set_delegatable("agent.hermes", {"DELEGATE_TASK"}, actor="governance")
        assert a.consume_approval("apr-z") is True
        assert a.consume_approval("apr-z") is False
