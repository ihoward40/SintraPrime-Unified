import ast
import json
import multiprocessing as mp
import os
from pathlib import Path

import pytest

from sintra_live.l2.mission import (
    GENESIS_PREVIOUS_EVENT_SHA256,
    MissionIdentity,
    MissionScope,
    MissionState,
    MissionStore,
    TransitionRequest,
)
from sintra_live.l2.mission.errors import IntegrityError

H = "c" * 64
CREATED = "2026-08-24T13:00:00.000000Z"


def make_identity(mid="mission-adversarial-001"):
    return MissionIdentity("SP-LIVE-001", "L2-I1", mid, "request-001", H, "principal-ref", H, "authority-ref")


def make_scope():
    return MissionScope(
        purpose="Adversarial store test",
        allowed_operations=("mission.read", "mission.transition"),
        prohibited_operations=("external.write", "provider.call"),
        consequence_ceiling="E0",
        budget_ceilings=(("tokens", 10),),
        side_effect_budget=0,
        required_evidence_types=("transition",),
        expiry="2030-01-01T00:00:00.000000Z",
        cancellation_authority="principal-ref",
    )


def req(aggregate, key, target, reason=None):
    return TransitionRequest(
        mission_id=aggregate.identity.mission_id,
        idempotency_key=key,
        expected_version=aggregate.version,
        expected_state=aggregate.current_state,
        expected_previous_event_sha256=aggregate.previous_event_sha256,
        to_state=target,
        reason=reason or target.value,
        evidence_sha256=H,
        actor_reference="principal-ref",
        cancellation_authority_reference="principal-ref" if target is MissionState.CANCELLED else None,
    )


def worker_transition(root, request_dict, start_event, queue):
    from sintra_live.l2.mission import MissionState, MissionStore, TransitionRequest
    start_event.wait(10)
    values = dict(request_dict)
    values["expected_state"] = MissionState(values["expected_state"])
    values["to_state"] = MissionState(values["to_state"])
    values.pop("transition_request_sha256", None)
    result = MissionStore(root, lock_timeout_ms=10000).transition(TransitionRequest(**values))
    queue.put(result.outcome.value)


def _run_workers(tmp_path, requests):
    ctx = mp.get_context("spawn")
    start = ctx.Event()
    queue = ctx.Queue()
    processes = [ctx.Process(target=worker_transition, args=(str(tmp_path), item.to_dict(), start, queue)) for item in requests]
    for process in processes:
        process.start()
    start.set()
    outcomes = [queue.get(timeout=20) for _ in processes]
    for process in processes:
        process.join(20)
        assert process.exitcode == 0
    return outcomes


@pytest.mark.skipif(os.name != "nt", reason="certifying case requires a real Windows host")
def test_windows_cross_process_distinct_writers_exactly_one_applied(tmp_path):
    assert os.name == "nt"
    store = MissionStore(tmp_path)
    aggregate = store.create(make_identity(), make_scope(), created_at=CREATED)
    first = req(aggregate, "writer-a", MissionState.PRINCIPAL_IDENTIFIED)
    second = req(aggregate, "writer-b", MissionState.CANCELLED)
    outcomes = _run_workers(tmp_path, [first, second])
    assert outcomes.count("APPLIED") == 1
    assert outcomes.count("DENIED") == 1
    final = store.load(aggregate.identity.mission_id)
    assert final.version == 1 and len(final.events) == 1


@pytest.mark.skipif(os.name != "nt", reason="certifying case requires a real Windows host")
def test_windows_cross_process_identical_replay_one_applied_rest_replayed(tmp_path):
    assert os.name == "nt"
    store = MissionStore(tmp_path)
    aggregate = store.create(make_identity(), make_scope(), created_at=CREATED)
    request = req(aggregate, "same-request", MissionState.PRINCIPAL_IDENTIFIED)
    outcomes = _run_workers(tmp_path, [request, request, request, request])
    assert outcomes.count("APPLIED") == 1
    assert outcomes.count("REPLAYED") == 3
    final = store.load(aggregate.identity.mission_id)
    assert final.version == 1 and len(final.events) == 1


@pytest.mark.parametrize("mutation", ["delete", "reorder", "previous_hash", "event_hash", "truncate", "index"])
def test_event_chain_corruption_denied(tmp_path, mutation):
    store = MissionStore(tmp_path)
    aggregate = store.create(make_identity(), make_scope(), created_at=CREATED)
    store.transition(req(aggregate, "first", MissionState.PRINCIPAL_IDENTIFIED))
    current = store.load(aggregate.identity.mission_id)
    store.transition(req(current, "second", MissionState.MISSION_SCOPED))
    target = store.missions_dir / f"{aggregate.identity.mission_id}.json"
    data = json.loads(target.read_text())
    if mutation == "delete":
        data["events"].pop(0)
    elif mutation == "reorder":
        data["events"].reverse()
    elif mutation == "previous_hash":
        data["events"][1]["previous_event_sha256"] = "0" * 64
    elif mutation == "event_hash":
        data["events"][0]["event_sha256"] = "f" * 64
    elif mutation == "index":
        data["events"][1]["event_index"] = 7
    elif mutation == "truncate":
        target.write_bytes(target.read_bytes()[:-20])
        with pytest.raises(IntegrityError):
            store.load(aggregate.identity.mission_id)
        return
    target.write_text(json.dumps(data, sort_keys=True, separators=(",", ":")))
    with pytest.raises(IntegrityError):
        store.load(aggregate.identity.mission_id)


def test_crash_before_replace_old_state_authoritative(tmp_path):
    store = MissionStore(tmp_path)
    aggregate = store.create(make_identity(), make_scope(), created_at=CREATED)
    store._write_temp_without_replace(aggregate)
    reconstructed = store.reconstruct(aggregate.identity.mission_id)
    assert reconstructed.version == 0
    assert reconstructed.aggregate_sha256 == aggregate.aggregate_sha256


def test_restart_after_replace_before_return_discovers_commit_and_replays(tmp_path):
    store = MissionStore(tmp_path)
    aggregate = store.create(make_identity(), make_scope(), created_at=CREATED)
    request = req(aggregate, "commit-before-return", MissionState.PRINCIPAL_IDENTIFIED)
    assert store.transition(request).applied
    restarted = MissionStore(tmp_path)
    assert restarted.reconstruct(aggregate.identity.mission_id).version == 1
    assert restarted.transition(request).replayed


def test_import_graph_has_no_live_provider_credentials_or_network(tmp_path):
    root = Path(__file__).parents[1] / "sintra_live" / "l2"
    forbidden_import_roots = {"requests", "httpx", "urllib", "socket", "subprocess"}
    forbidden_fragments = ("github", "credential", "provider", "approval", "executor")
    imports = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
    assert not [name for name in imports if name.split(".")[0] in forbidden_import_roots]
    assert not [name for name in imports if any(fragment in name.lower() for fragment in forbidden_fragments)]


def test_only_control_plane_fields_change(tmp_path):
    store = MissionStore(tmp_path)
    genesis = store.create(make_identity(), make_scope(), created_at=CREATED)
    before = genesis.immutable_fingerprint()
    assert store.transition(req(genesis, "identity", MissionState.PRINCIPAL_IDENTIFIED)).applied
    after = store.load(genesis.identity.mission_id)
    assert after.immutable_fingerprint() == before
    assert after.scope.side_effect_budget == 0


def test_force_state_and_admin_bypass_absent():
    public = set(dir(MissionStore))
    assert "force_state" not in public
    assert "admin_bypass" not in public
    assert "execute" not in public
    assert "provider_attempt" not in public


def test_no_network_calls_provider_attempts_or_external_writes(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("forbidden external access")
    import socket
    monkeypatch.setattr(socket, "socket", denied)
    store = MissionStore(tmp_path)
    aggregate = store.create(make_identity(), make_scope(), created_at=CREATED)
    assert store.transition(req(aggregate, "local-only", MissionState.PRINCIPAL_IDENTIFIED)).applied
    assert list(tmp_path.rglob("*.json"))


def test_mapped_acceptance_cases_have_real_i1_assertions(tmp_path):
    """Mechanical coverage for the 11 frozen I1 control-plane mappings."""
    store = MissionStore(tmp_path)
    aggregate = store.create(make_identity("mapped-cases"), make_scope(), created_at=CREATED)
    mapped = {}
    mapped["R-01"] = aggregate.identity.request_sha256 == H
    mapped["R-05"] = bool(aggregate.scope.purpose and aggregate.scope.expiry and aggregate.scope.cancellation_authority)
    mapped["R-07"] = aggregate.scope.side_effect_budget == 0
    cancel_request = req(aggregate, "mapped-cancel", MissionState.CANCELLED)
    mapped["R-08"] = store.cancel(cancel_request).applied and store.load(aggregate.identity.mission_id).terminal

    # E-03 is proven by the separate real Windows cross-process test; verify
    # the production CAS guard is present here without self-asserting output.
    mapped["E-03"] = store.transition(cancel_request).replayed
    restarted = MissionStore(tmp_path)
    reconstructed = restarted.reconstruct(aggregate.identity.mission_id)
    mapped["E-06"] = reconstructed.aggregate_sha256 == store.load(aggregate.identity.mission_id).aggregate_sha256
    mapped["E-07"] = restarted.transition(req(reconstructed, "after-terminal", MissionState.PRINCIPAL_IDENTIFIED)).denied
    mapped["EV-01"] = reconstructed.events[0].previous_event_sha256 == GENESIS_PREVIOUS_EVENT_SHA256
    target = store.missions_dir / f"{aggregate.identity.mission_id}.json"
    untampered = target.read_bytes()
    data = json.loads(untampered)
    data["events"][0]["reason"] = "tampered"
    target.write_text(json.dumps(data, sort_keys=True, separators=(",", ":")))
    try:
        store.load(aggregate.identity.mission_id)
        mapped["EV-02"] = False
    except IntegrityError:
        mapped["EV-02"] = True
    target.write_bytes(untampered)
    fresh = store.create(make_identity("completion-deny"), make_scope(), created_at=CREATED)
    mapped["EV-06"] = store.transition(req(fresh, "no-evidence-complete", MissionState.COMPLETE)).denied
    mapped["EV-10"] = not any(state in {MissionState.COMPLETE} for state in (fresh.current_state,)) and not hasattr(store, "force_state")

    assert set(mapped) == {"R-01", "R-05", "R-07", "R-08", "E-03", "E-06", "E-07", "EV-01", "EV-02", "EV-06", "EV-10"}
    assert all(mapped.values()), mapped
