"""GOD-1 -> governed runtime bridge tests (SP-GOD1X Phase 16).

Proves the GOD-1 task state reflects real backend execution, and that an empty
authority intersection denies execution (consensus/role != authority).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from omnibrain.swarm_execution_bridge import (
    build_envelope_from_intersection,
    dispatch_task_to_runtime,
    reflect_task_status,
)
from omnibrain.swarms import (
    SwarmRoleManifest,
    SwarmTask,
    TaskStatus,
)

REPO = Path(__file__).resolve().parents[2]
WORKBASE = REPO / "omnibrain" / ".gov_bridge_tmp"

WORKDIR: Path = REPO  # set per-test-run by the autouse fixture below


@pytest.fixture(autouse=True)
def _gov_workdir_fixture(tmp_path_factory: pytest.TempdirFactory) -> None:
    global WORKDIR
    d = WORKBASE / tmp_path_factory.mktemp("br").name
    d.mkdir(parents=True, exist_ok=True)
    WORKDIR = d
    yield
    shutil.rmtree(d, ignore_errors=True)


def _manifest(role_type: str, delegable: frozenset[str]) -> SwarmRoleManifest:
    return SwarmRoleManifest(
        role_id="builder", role_type=role_type, mission_scope=frozenset(),
        task_scope=frozenset(), allowed_tools=frozenset(),
        memory_scope="PRIVATE_AGENT", delegable_authority=delegable,
        output_contract="", evidence_requirements=(),
    )


def _task(task_id: str = "T1") -> SwarmTask:
    return SwarmTask(
        task_id=task_id, mission_id="M1", swarm_id="S1", parent_task_id=None,
        role="builder", objective="", mutable_resources=frozenset(),
    )


def test_bridge_admits_and_task_runs_only_when_admitted() -> None:
    task = _task()
    manifest = _manifest("BUILDER", frozenset({"local_exec"}))
    res, _env, ctrl = dispatch_task_to_runtime(
        task=task, manifest=manifest, mission_id="M1", swarm_id="S1",
        authority_id="AUTH1", context_package_id="CTX1",
        worker_class="CodeSearchWorker",
        task_params={"pattern": "class", "path": "swarm_runtime"},
        working_directory=str(WORKDIR), repo_path=str(REPO),
        run_dir=str(WORKDIR / "run"),
        mission_authority={"local_exec"}, swarm_authority={"local_exec"},
        parent_delegable={"local_exec"},
    )
    # TASK_RUNNING only because an admitted execution is actually running
    assert res is not None
    assert res.status == "RUNNING"
    assert task.status == TaskStatus.RUNNING
    ctrl.wait(timeout=120)
    reflect_task_status(task, res)
    assert res.status == "COMPLETED", res.to_dict()
    assert task.status == TaskStatus.COMPLETE


def test_bridge_empty_authority_intersection_denies_execution() -> None:
    task = _task()
    # Role's delegable authority is empty -> intersection empty -> no execution
    manifest = _manifest("BUILDER", frozenset())
    res, env, ctrl = dispatch_task_to_runtime(
        task=task, manifest=manifest, mission_id="M1", swarm_id="S1",
        authority_id="AUTH1", context_package_id="CTX1",
        worker_class="CodeSearchWorker",
        task_params={"pattern": "class", "path": "swarm_runtime"},
        working_directory=str(WORKDIR), repo_path=str(REPO),
        run_dir=str(WORKDIR / "run"),
        mission_authority={"local_exec"}, swarm_authority={"local_exec"},
        parent_delegable={"local_exec"},
    )
    # No subprocess spawned; task refused by authority, not by the backend.
    assert res is None
    assert env.role_allowed is False
    assert task.status == TaskStatus.BLOCKED
    assert ctrl.processes == {}


def test_bridge_envelope_intersection_matches_formula() -> None:
    task = _task()
    manifest = _manifest("BUILDER", frozenset({"a", "b"}))
    env = build_envelope_from_intersection(
        task=task, manifest=manifest, mission_id="M1", swarm_id="S1",
        authority_id="AUTH1", context_package_id="CTX1",
        mission_authority={"a"}, swarm_authority={"a", "b"}, parent_delegable={"a", "b"},
    )
    # effective = delegable ∩ mission ∩ swarm ∩ parent = {a,b} ∩ {a} ∩ {a,b} ∩ {a,b} = {a}
    assert env.role_allowed is True

    env2 = build_envelope_from_intersection(
        task=task, manifest=manifest, mission_id="M1", swarm_id="S1",
        authority_id="AUTH1", context_package_id="CTX1",
        mission_authority={"x"}, swarm_authority={"a", "b"}, parent_delegable={"a", "b"},
    )
    # {a,b} ∩ {x} = {} -> denied
    assert env2.role_allowed is False
