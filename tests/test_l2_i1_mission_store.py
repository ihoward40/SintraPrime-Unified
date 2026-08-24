import json
from pathlib import Path

import pytest

from sintra_live.l2.mission import (
    GENESIS_PREVIOUS_EVENT_SHA256,
    MissionIdentity,
    MissionScope,
    MissionState,
    MissionStore,
    TransitionOutcome,
    TransitionRequest,
)
from sintra_live.l2.mission.errors import IntegrityError, MissionStoreError

H = "b" * 64
CREATED = "2026-08-24T13:00:00.000000Z"


def make_identity(mid="mission-store-001"):
    return MissionIdentity("SP-LIVE-001", "L2-I1", mid, "request-001", H, "principal-ref", H, "authority-ref")


def make_scope():
    return MissionScope(
        purpose="Mission store test",
        allowed_operations=("mission.read", "mission.transition"),
        prohibited_operations=("external.write", "provider.call"),
        consequence_ceiling="E0",
        budget_ceilings=(("tokens", 10),),
        side_effect_budget=0,
        required_evidence_types=("transition",),
        expiry="2030-01-01T00:00:00.000000Z",
        cancellation_authority="principal-ref",
    )


def request(aggregate, key, to_state, **changes):
    values = dict(
        mission_id=aggregate.identity.mission_id,
        idempotency_key=key,
        expected_version=aggregate.version,
        expected_state=aggregate.current_state,
        expected_previous_event_sha256=aggregate.previous_event_sha256,
        to_state=to_state,
        reason=f"to {to_state.value}",
        evidence_sha256=H,
        actor_reference="principal-ref",
        cancellation_authority_reference="principal-ref" if to_state is MissionState.CANCELLED else None,
    )
    values.update(changes)
    return TransitionRequest(**values)


def test_create_is_idempotent_and_collision_safe(tmp_path):
    store = MissionStore(tmp_path)
    first = store.create(make_identity(), make_scope(), created_at=CREATED)
    second = store.create(make_identity(), make_scope(), created_at=CREATED)
    assert first.aggregate_sha256 == second.aggregate_sha256
    changed = MissionScope(**{**make_scope().__dict__, "purpose": "different"})
    with pytest.raises(MissionStoreError):
        store.create(make_identity(), changed, created_at=CREATED)


def test_transition_applied_then_identical_replayed_without_append(tmp_path):
    store = MissionStore(tmp_path)
    aggregate = store.create(make_identity(), make_scope(), created_at=CREATED)
    req = request(aggregate, "identity-1", MissionState.PRINCIPAL_IDENTIFIED)
    applied = store.transition(req)
    replayed = store.transition(req)
    after = store.load(aggregate.identity.mission_id)
    assert applied.outcome is TransitionOutcome.APPLIED
    assert replayed.outcome is TransitionOutcome.REPLAYED
    assert after.version == 1
    assert len(after.events) == 1
    assert replayed.aggregate_sha256 == after.aggregate_sha256


def test_conflicting_replay_denied(tmp_path):
    store = MissionStore(tmp_path)
    aggregate = store.create(make_identity(), make_scope(), created_at=CREATED)
    assert store.transition(request(aggregate, "same-key", MissionState.PRINCIPAL_IDENTIFIED)).applied
    conflict = request(aggregate, "same-key", MissionState.CANCELLED)
    assert store.transition(conflict).denied


def test_stale_version_state_and_prior_hash_denied(tmp_path):
    store = MissionStore(tmp_path)
    aggregate = store.create(make_identity(), make_scope(), created_at=CREATED)
    assert store.transition(request(aggregate, "first", MissionState.PRINCIPAL_IDENTIFIED)).applied
    assert store.transition(request(aggregate, "stale-version", MissionState.CANCELLED)).denied
    current = store.load(aggregate.identity.mission_id)
    assert store.transition(request(current, "wrong-state", MissionState.CANCELLED, expected_state=MissionState.RECEIVED)).denied
    assert store.transition(request(current, "wrong-hash", MissionState.CANCELLED, expected_previous_event_sha256="0" * 64)).denied
    assert store.load(aggregate.identity.mission_id).version == 1


def test_cancellation_is_durable_terminal_and_replayable(tmp_path):
    store = MissionStore(tmp_path)
    aggregate = store.create(make_identity(), make_scope(), created_at=CREATED)
    req = request(aggregate, "cancel-1", MissionState.CANCELLED)
    assert store.cancel(req).applied
    assert store.cancel(req).replayed
    cancelled = store.load(aggregate.identity.mission_id)
    assert cancelled.cancelled and cancelled.terminal
    reopen = request(cancelled, "reopen", MissionState.PRINCIPAL_IDENTIFIED)
    assert store.transition(reopen).denied
    assert store.load(aggregate.identity.mission_id).version == 1


def test_later_operational_states_denied(tmp_path):
    store = MissionStore(tmp_path)
    aggregate = store.create(make_identity(), make_scope(), created_at=CREATED)
    for state in (MissionState.READY, MissionState.EXECUTING, MissionState.COMPLETE):
        assert store.transition(request(aggregate, f"deny-{state.value}", state)).denied
    assert store.load(aggregate.identity.mission_id).version == 0


def test_restart_reconstructs_identical_identity_and_hashes(tmp_path):
    first = MissionStore(tmp_path)
    aggregate = first.create(make_identity(), make_scope(), created_at=CREATED)
    first.transition(request(aggregate, "identity", MissionState.PRINCIPAL_IDENTIFIED))
    before = first.load(aggregate.identity.mission_id)
    restarted = MissionStore(tmp_path)
    after = restarted.reconstruct(aggregate.identity.mission_id)
    assert (after.current_state, after.version, after.previous_event_sha256, after.aggregate_sha256) == (
        before.current_state, before.version, before.previous_event_sha256, before.aggregate_sha256
    )
    original_req = request(aggregate, "identity", MissionState.PRINCIPAL_IDENTIFIED)
    assert restarted.transition(original_req).replayed


def test_stale_temp_blocks_mutation_but_valid_target_is_readable(tmp_path):
    store = MissionStore(tmp_path)
    aggregate = store.create(make_identity(), make_scope(), created_at=CREATED)
    temp = store._write_temp_without_replace(aggregate)
    assert store.load(aggregate.identity.mission_id).aggregate_sha256 == aggregate.aggregate_sha256
    assert store.transition(request(aggregate, "blocked", MissionState.CANCELLED)).denied
    temp.unlink()
    assert store.transition(request(aggregate, "allowed", MissionState.CANCELLED)).applied


def test_temp_without_target_is_not_committed(tmp_path):
    store = MissionStore(tmp_path)
    aggregate = store.create(make_identity(), make_scope(), created_at=CREATED)
    target = store.missions_dir / f"{aggregate.identity.mission_id}.json"
    raw = target.read_bytes()
    target.unlink()
    temp = store.missions_dir / f".{aggregate.identity.mission_id}.crash.tmp"
    temp.write_bytes(raw)
    with pytest.raises(IntegrityError):
        store.load(aggregate.identity.mission_id)


def test_hash_tamper_is_denied(tmp_path):
    store = MissionStore(tmp_path)
    aggregate = store.create(make_identity(), make_scope(), created_at=CREATED)
    target = store.missions_dir / f"{aggregate.identity.mission_id}.json"
    data = json.loads(target.read_text())
    data["scope"]["purpose"] = "tampered"
    target.write_text(json.dumps(data, sort_keys=True, separators=(",", ":")))
    with pytest.raises(IntegrityError):
        store.load(aggregate.identity.mission_id)


def test_no_force_or_admin_bypass_api(tmp_path):
    store = MissionStore(tmp_path)
    assert not hasattr(store, "force_state")
    assert not hasattr(store, "admin_bypass")
    assert not hasattr(store, "execute")
