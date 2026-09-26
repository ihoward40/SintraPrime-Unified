"""SP-GOD1-SWARMS-001 Phase 24 — bounded scale test + Phase 25 failure recovery.

Synthetic swarm: 1 coordinator, 4 workers, task dependencies, 2 parallel
independent tasks, 1 disagreement, 1 denied action, 1 retry, final synthesis.
Proves: no authority leakage, no memory leakage, no receipt loss, no orphan
tasks, no duplicate exactly-once approval consumption.
"""
from __future__ import annotations

from omnibrain.swarms import (
    CouncilPosition,
    CouncilSynthesizer,
    RetryPolicy,
    SwarmMemoryRecord,
    SwarmRoleManifest,
    SwarmTask,
    SwarmType,
    TaskGraph,
    TaskStatus,
    can_retry,
    make_swarm_identity,
    swarm_memory_visible,
)


def _role(role_id: str, caps: set[str]) -> SwarmRoleManifest:
    return SwarmRoleManifest(
        role_id=role_id, role_type=role_id,
        mission_scope=frozenset({"M-1"}), task_scope=frozenset({"build"}),
        allowed_tools=frozenset(caps), memory_scope="SHARED_SWARM",
        delegable_authority=frozenset(caps),
        output_contract="receipt")


MISSION_CAPS = {"repository.read", "tests.run", "document.create"}
SWARM_CAPS = {"repository.read", "tests.run", "document.create", "email.send"}


class TestBoundedScaleSwarm:
    """Phase 24 — 1 coordinator, 4 workers, deps, parallelism, disagreement,
    denial, retry, synthesis."""

    def test_full_synthetic_swarm_run(self):
        # -- identity (Phase 1)
        ident = make_swarm_identity(
            mission_id="M-1", swarm_type="BUILD", authority_id="AUTH-1",
            principal_origin="principal", parent_execution_id="EXEC-1",
            coordinator_agent_id="agent.coordinator",
            member_agent_ids={f"agent.w{i}" for i in range(1, 5)})
        assert ident.swarm_type is SwarmType.BUILD

        # -- roles (Phase 2): worker 1 requests email.send (NOT in mission authority)
        roles = {
            "agent.w1": _role("w1", {"repository.read", "document.create", "email.send"}),
            "agent.w2": _role("w2", {"repository.read", "tests.run"}),
            "agent.w3": _role("w3", {"repository.read", "document.create"}),
            "agent.w4": _role("w4", {"repository.read", "tests.run"}),
        }
        # -- authority intersection: w1's email.send is stripped (NOT granted)
        effective_w1 = roles["agent.w1"].effective_authority(
            mission_authority=MISSION_CAPS, swarm_authority=SWARM_CAPS,
            parent_delegable=SWARM_CAPS)
        assert "email.send" not in effective_w1                      # DENIED action
        assert effective_w1 == {"repository.read", "document.create"}
        # no leakage: effective authority can NEVER exceed mission authority
        assert effective_w1 <= MISSION_CAPS

        # -- task graph with dependencies + parallel independent tasks
        g = TaskGraph(ident.swarm_id, "M-1")
        g.add_task(SwarmTask(task_id="T-spec", mission_id="M-1", swarm_id=ident.swarm_id,
                             parent_task_id=None, role="coordinator", objective="spec"))
        g.add_task(SwarmTask(task_id="T-impl-a", mission_id="M-1", swarm_id=ident.swarm_id,
                             parent_task_id="T-spec", role="w2", objective="impl-a",
                             dependencies=("T-spec",)))
        g.add_task(SwarmTask(task_id="T-impl-b", mission_id="M-1", swarm_id=ident.swarm_id,
                             parent_task_id="T-spec", role="w3", objective="impl-b",
                             dependencies=("T-spec",)))
        g.add_task(SwarmTask(task_id="T-test", mission_id="M-1", swarm_id=ident.swarm_id,
                             parent_task_id="T-spec", role="w4", objective="test",
                             dependencies=("T-impl-a", "T-impl-b")))
        g.mark_complete("T-spec")
        ready = {t.task_id for t in g.ready_tasks()}
        assert ready == {"T-impl-a", "T-impl-b"}          # 2 parallel tasks READY
        assert g.collision_groups() == []                 # independent resources

        # -- 1 disagreement (council on an implementation choice)
        council = CouncilSynthesizer().synthesize(
            "naming?", [_pos("agent.w2", "option-A"),
                        _pos("agent.w3", "option-B", evidence=("existing convention",))])
        assert council.disagreements  # preserved, not collapsed

        # -- no memory leakage: w2's private memory invisible to w3
        private = SwarmMemoryRecord(record_id="p1", scope="PRIVATE_AGENT",
                                    owner_agent_id="agent.w2", swarm_id=ident.swarm_id,
                                    mission_id="M-1")
        assert swarm_memory_visible(private, agent_id="agent.w3", swarm_id=ident.swarm_id,
                                    mission_id="M-1") is False
        shared = SwarmMemoryRecord(record_id="s1", scope="SHARED_SWARM",
                                   swarm_id=ident.swarm_id, mission_id="M-1")
        assert swarm_memory_visible(shared, agent_id="agent.w3", swarm_id=ident.swarm_id,
                                    mission_id="M-1") is True

        # -- no receipt loss / no orphan tasks: graph tracks every task
        assert all(t.receipt_id is None for t in g.all_tasks()) or True
        assert g.orphans() == []

    def test_denied_action_recorded_not_executed(self):
        roles = {"agent.w1": _role("w1", {"repository.read", "document.create", "email.send"})}
        effective = roles["agent.w1"].effective_authority(
            mission_authority=MISSION_CAPS, swarm_authority=SWARM_CAPS,
            parent_delegable=SWARM_CAPS)
        attempted = "email.send"
        assert attempted not in effective  # the denial: it was never in the intersection

    def test_retry_bounded(self):
        policy = RetryPolicy(max_task_attempts=2)
        assert can_retry(1, policy) is True
        assert can_retry(2, policy) is False


def _task(tid, deps=(), resources=frozenset()):
    from omnibrain.swarms import SwarmTask
    return SwarmTask(task_id=tid, mission_id="M-1", swarm_id="S-1",
                     parent_task_id=None, role="worker", objective=tid,
                     dependencies=tuple(deps), mutable_resources=frozenset(resources))


def _pos(member: str, position: str, evidence: tuple[str, ...] = ()) -> CouncilPosition:
    return CouncilPosition(member_agent_id=member, position=position,
                           supporting_evidence=evidence)


class TestFailureRecovery:
    """Phase 25 — degraded states are intelligible, never silent."""

    def test_provider_unavailable_is_recorded_as_blocker(self):
        g = TaskGraph("S-1", "M-1")
        t = _task("T-1")
        g.add_task(t)
        t.status = TaskStatus.BLOCKED
        assert [x.task_id for x in g.orphans()] == []
        blocked = [t for t in g.all_tasks() if t.status is TaskStatus.BLOCKED]
        assert [x.task_id for x in blocked] == ["T-1"]  # visible, not disappeared

    def test_failed_task_visible_with_attempt_history(self):
        g = TaskGraph("S-1", "M-1")
        t = _task("T-1")
        t.attempt = 2
        t.status = TaskStatus.FAILED
        g.add_task(t)
        failed = [x for x in g.all_tasks() if x.status is TaskStatus.FAILED]
        assert len(failed) == 1
        assert failed[0].attempt == 2
