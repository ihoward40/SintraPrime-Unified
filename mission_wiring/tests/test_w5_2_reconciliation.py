"""W5-2 — reconciliation queue state machine + exactly-once tests."""
from __future__ import annotations

import pytest

from mission_wiring.durable_mission import DurableMissionError
from mission_wiring.reconciliation import (
    ReconciliationQueue,
    ReconciliationState,
)


def _queue() -> ReconciliationQueue:
    return ReconciliationQueue(clock=lambda: "T0")


def _enqueue_kwargs(**over) -> dict:
    base = {
        "mission_id": "mission.w5-002", "attempt_id": "attempt-1", "effect_id": "effect-1",
        "tenant_id": "tenant.default", "actor_id": "agent.browser.worker",
        "canonical_capability": "computer.browser.navigate",
        "canonical_resource": "https://example.com",
        "intent_hash": "ih-123", "intent_timestamp": "T0",
        "contact_started_at": "T0", "contact_evidence_hash": "evh-1",
        "last_known_mission_state": "EXECUTING",
        "certification_generation": "certgen-24fbaf3c8fa1a07d65cf310960e421bf",
        "executor_binding_generation": "ebg-44efb071ec7e",
        "reason_code": "PROCESS_CRASH_DURING_EXTERNAL_CONTACT",
    }
    base.update(over)
    return base


def test_enqueue_and_get():
    q = _queue()
    rec = q.enqueue(**_enqueue_kwargs())
    assert rec.state is ReconciliationState.QUEUED
    assert q.get(rec.reconciliation_id) is rec
    assert q.get_by_effect("mission.w5-002", "effect-1") is rec


def test_duplicate_unknown_effect_yields_exactly_one_active_item():
    """Same unknown effect encountered twice on restart → exactly one active
    reconciliation record (case 8)."""
    q = _queue()
    r1 = q.enqueue(**_enqueue_kwargs())
    r2 = q.enqueue(**_enqueue_kwargs())
    assert r1.reconciliation_id == r2.reconciliation_id
    assert len(q.list_pending()) == 1


def test_list_pending_excludes_resolved():
    q = _queue()
    rec = q.enqueue(**_enqueue_kwargs())
    q.begin_review(rec.reconciliation_id, reviewer="governance")
    q.resolve_no_effect(rec.reconciliation_id, resolver="governance",
                        evidence_hash="evh-1")
    assert q.list_pending() == []
    resolved = q.get(rec.reconciliation_id)
    assert resolved.state is ReconciliationState.RESOLVED_NO_EFFECT
    assert resolved.resolution.value == "NO_EFFECT"


def test_typed_resolution_commands_only():
    """No generic resolve(status, payload) surface — only typed commands."""
    q = _queue()
    assert not hasattr(q, "resolve"), "generic resolve() would blur authority semantics"
    for required in ("begin_review", "resolve_effect_confirmed", "resolve_no_effect",
                     "resolve_compensated", "mark_unresolved"):
        assert hasattr(q, required), required


def test_resolve_requires_evidence_hash():
    q = _queue()
    rec = q.enqueue(**_enqueue_kwargs())
    with pytest.raises(DurableMissionError) as ei:
        q.resolve_no_effect(rec.reconciliation_id, resolver="governance",
                            evidence_hash="")
    assert ei.value.code == "INVALID_RECONCILIATION_FIELD"


def test_double_resolution_refused():
    q = _queue()
    rec = q.enqueue(**_enqueue_kwargs())
    q.begin_review(rec.reconciliation_id, reviewer="governance")
    q.resolve_no_effect(rec.reconciliation_id, resolver="governance",
                        evidence_hash="evh-1")
    with pytest.raises(DurableMissionError) as ei:
        q.resolve_effect_confirmed(rec.reconciliation_id, resolver="governance",
                                   evidence_hash="evh-2")
    assert ei.value.code == "RECONCILIATION_ALREADY_RESOLVED"


def test_begin_review_from_resolved_refused():
    q = _queue()
    rec = q.enqueue(**_enqueue_kwargs())
    q.begin_review(rec.reconciliation_id, reviewer="governance")
    q.resolve_effect_confirmed(rec.reconciliation_id, resolver="governance",
                               evidence_hash="evh-1")
    with pytest.raises(DurableMissionError) as ei:
        q.begin_review(rec.reconciliation_id, reviewer="governance")
    assert ei.value.code == "RECONCILIATION_ALREADY_RESOLVED"


def test_invalid_reason_code_refused():
    q = _queue()
    with pytest.raises(DurableMissionError) as ei:
        q.enqueue(**_enqueue_kwargs(reason_code="BECAUSE_I_SAID_SO"))
    assert ei.value.code == "INVALID_REASON_CODE"


def test_unknown_reconciliation_refused():
    q = _queue()
    with pytest.raises(DurableMissionError) as ei:
        q.get("recon-nonexistent")
    assert ei.value.code == "RECONCILIATION_NOT_FOUND"
