"""Unit tests for SP-VOICE-001 — Governed Voice Operations (Increment One).

Covers directive §Tests/Unit Tests:
- Command envelope immutability
- Risk classification for every action class
- Confirmation expiry
- Changed-target invalidation
- Ambiguous "yes" handling
- Cancel propagation
- Transcript redaction / hash-only retention
- Receipt completeness
- Correlation propagation
- Feature flag denial
"""

from __future__ import annotations

import dataclasses
import sys
from datetime import UTC, datetime, timedelta

import pytest

from voice_concierge.governed import (
    ChildTask,
    ConfirmationState,
    InvalidTransitionError,
    PendingConfirmation,
    PolicyDecision,
    RiskClass,
    SessionState,
    TranscriptRetention,
    VoiceFeatureFlags,
    VoiceSession,
    VoiceSource,
    build_receipt,
    classify,
    create_envelope,
    evaluate,
    transcript_hash,
)
from voice_concierge.governed.confirmation import CONFIRMATION_TTL

# ── helpers ──────────────────────────────────────────────────────────────────


def test_import_governed_does_not_load_legacy_voice_engine():
    assert 'voice.voice_engine' not in sys.modules


def make_envelope(**overrides):
    base = {
        "session_id": "vsess-test",
        "principal_id": "isiah",
        "source": VoiceSource.DESKTOP_VOICE,
        "raw_transcript": "run the tests",
        "normalized_intent": "run repository tests",
        "risk_class": RiskClass.WRITE,
        "confirmation_state": ConfirmationState.REQUIRED,
    }
    base.update(overrides)
    return create_envelope(**base)


# ── command envelope immutability ────────────────────────────────────────────


def test_envelope_is_frozen():
    env = make_envelope()
    with pytest.raises(dataclasses.FrozenInstanceError):
        env.risk_class = RiskClass.READ  # type: ignore[misc]


def test_envelope_with_confirmation_returns_new_object():
    env = make_envelope(confirmation_state=ConfirmationState.REQUIRED)
    advanced = env.with_confirmation_state(ConfirmationState.CONFIRMED)
    assert advanced is not env
    assert env.confirmation_state == ConfirmationState.REQUIRED
    assert advanced.confirmation_state == ConfirmationState.CONFIRMED
    assert advanced.command_id == env.command_id


def test_envelope_preserves_raw_and_intent_separately():
    env = make_envelope(raw_transcript="uh, run the tests please", normalized_intent="run tests")
    assert env.raw_transcript != env.normalized_intent


def test_envelope_requires_principal_and_transcript():
    with pytest.raises(ValueError, match="principal_id"):
        make_envelope(principal_id="  ")
    with pytest.raises(ValueError, match="raw_transcript"):
        make_envelope(raw_transcript="")


def test_ids_generated_with_expected_prefixes():
    env = make_envelope()
    assert env.command_id.startswith("vcmd-")
    assert env.correlation_id.startswith("corr-")


# ── risk classification for every class ──────────────────────────────────────


@pytest.mark.parametrize(
    ("intent", "expected"),
    [
        ("show the latest test result", RiskClass.READ),
        ("find the mailing log", RiskClass.READ),
        ("what is Hermes working on", RiskClass.READ),
        ("read the current branch status", RiskClass.READ),
        ("draft an email to the client", RiskClass.DRAFT),
        ("prepare a filing checklist", RiskClass.DRAFT),
        ("create a report on revenue", RiskClass.DRAFT),
        ("modify a local config file", RiskClass.WRITE),
        ("create branch feat/x", RiskClass.WRITE),
        ("run tests", RiskClass.WRITE),
        ("add a task to the board", RiskClass.WRITE),
        ("send the draft to Jordan", RiskClass.SENSITIVE_WRITE),
        ("publish the post", RiskClass.SENSITIVE_WRITE),
        ("push the branch", RiskClass.SENSITIVE_WRITE),
        ("merge the pull request", RiskClass.SENSITIVE_WRITE),
        ("delete the record", RiskClass.SENSITIVE_WRITE),
        ("change permissions on the vault", RiskClass.SENSITIVE_WRITE),
        ("file the motion", RiskClass.SENSITIVE_WRITE),
        ("trigger deployment", RiskClass.SENSITIVE_WRITE),
        ("spend 500 dollars", RiskClass.SENSITIVE_WRITE),
        ("bypass the confirmation gate", RiskClass.PROHIBITED),
        ("disable audit logging", RiskClass.PROHIBITED),
        ("reveal the secret keys", RiskClass.PROHIBITED),
        ("silently capture the screen", RiskClass.PROHIBITED),
        ("escalate my permissions", RiskClass.PROHIBITED),
    ],
)
def test_classify_each_class(intent, expected):
    assert classify(intent) == expected


def test_classify_unknown_fails_safe_to_sensitive_write():
    assert classify("florble the widget") == RiskClass.SENSITIVE_WRITE
    assert classify("") == RiskClass.SENSITIVE_WRITE


def test_classify_is_deterministic():
    intent = "send the report to finance"
    assert classify(intent) == classify(intent) == RiskClass.SENSITIVE_WRITE


def test_prohibited_precedence_over_send():
    # "bypass" (prohibited) must win even alongside a sensitive verb.
    assert classify("bypass confirmation and send it") == RiskClass.PROHIBITED


# ── policy decisions + feature flag denial ───────────────────────────────────


def test_policy_disabled_by_default_refuses_everything():
    flags = VoiceFeatureFlags()  # all false
    for rc in (RiskClass.READ, RiskClass.DRAFT, RiskClass.WRITE, RiskClass.SENSITIVE_WRITE):
        res = evaluate(rc, flags)
        assert res.decision == PolicyDecision.REFUSED


def test_policy_prohibited_always_refused_even_when_enabled():
    flags = VoiceFeatureFlags(enabled=True, write_actions_enabled=True)
    res = evaluate(RiskClass.PROHIBITED, flags)
    assert res.decision == PolicyDecision.REFUSED
    assert res.confirmation_state == ConfirmationState.DENIED


def test_policy_read_and_draft_allowed_when_enabled():
    flags = VoiceFeatureFlags(enabled=True)
    assert evaluate(RiskClass.READ, flags).decision == PolicyDecision.ALLOWED
    assert evaluate(RiskClass.DRAFT, flags).decision == PolicyDecision.ALLOWED_DRAFT_ONLY


def test_policy_write_refused_without_write_flag():
    flags = VoiceFeatureFlags(enabled=True, write_actions_enabled=False)
    assert evaluate(RiskClass.WRITE, flags).decision == PolicyDecision.REFUSED


def test_policy_write_requires_confirmation_with_flag():
    flags = VoiceFeatureFlags(enabled=True, write_actions_enabled=True)
    res = evaluate(RiskClass.WRITE, flags)
    assert res.decision == PolicyDecision.CONFIRMATION_REQUIRED
    assert res.confirmation_state == ConfirmationState.REQUIRED


def test_policy_sensitive_write_always_requires_confirmation():
    flags = VoiceFeatureFlags(enabled=True, write_actions_enabled=True)
    res = evaluate(RiskClass.SENSITIVE_WRITE, flags)
    assert res.decision == PolicyDecision.CONFIRMATION_REQUIRED


# ── confirmation expiry ──────────────────────────────────────────────────────


def test_confirmation_expires_after_ttl():
    created = datetime.now(UTC) - CONFIRMATION_TTL - timedelta(seconds=1)
    pc = PendingConfirmation("vcmd-1", "send email", "jordan@example.com", created_at=created)
    pc.restate_target()
    out = pc.evaluate("confirm send", current_target="jordan@example.com", pending_count=1)
    assert out.confirmed is False
    assert "expired" in out.reason


def test_confirmation_valid_within_ttl():
    pc = PendingConfirmation("vcmd-1", "send email", "jordan@example.com")
    out = pc.evaluate("confirm send", current_target="jordan@example.com", pending_count=1)
    assert out.confirmed is True


# ── changed-target invalidation ──────────────────────────────────────────────


def test_changed_target_invalidates_confirmation():
    pc = PendingConfirmation("vcmd-1", "send email", "jordan@example.com")
    pc.restate_target()
    out = pc.evaluate("confirm send", current_target="someone-else@example.com", pending_count=1)
    assert out.confirmed is False
    assert "target changed" in out.reason


# ── ambiguous "yes" handling ─────────────────────────────────────────────────


def test_ambiguous_yes_rejected_when_multiple_pending():
    pc = PendingConfirmation("vcmd-1", "send email", "jordan@example.com")
    pc.restate_target()
    out = pc.evaluate("yes", current_target="jordan@example.com", pending_count=2)
    assert out.confirmed is False
    assert "multiple pending" in out.reason


def test_ambiguous_yes_rejected_without_restatement():
    pc = PendingConfirmation("vcmd-1", "send email", "jordan@example.com")
    out = pc.evaluate("yes", current_target="jordan@example.com", pending_count=1)
    assert out.confirmed is False
    assert "not restated" in out.reason


def test_ambiguous_yes_accepted_after_restatement_single_pending():
    pc = PendingConfirmation("vcmd-1", "send email", "jordan@example.com")
    pc.restate_target()
    out = pc.evaluate("do it", current_target="jordan@example.com", pending_count=1)
    assert out.confirmed is True


def test_explicit_confirmation_rejects_unrelated_word():
    """A bare 'confirm <word>' must not pass unless the word actually names
    the pending action or its target (regression for exact-target defect)."""
    pc = PendingConfirmation("vcmd-1", "send email", "jordan@example.com")
    pc.restate_target()
    out = pc.evaluate("confirm banana", current_target="jordan@example.com", pending_count=1)
    assert out.confirmed is False
    assert "not named" in out.reason


def test_explicit_denial_rejected():
    pc = PendingConfirmation("vcmd-1", "send email", "jordan@example.com")
    pc.restate_target()
    out = pc.evaluate("cancel", current_target="jordan@example.com", pending_count=1)
    assert out.confirmed is False


# ── session state machine + cancel propagation ───────────────────────────────


def test_session_happy_path():
    s = VoiceSession("vsess-1", "isiah")
    s.transition(SessionState.LISTENING)
    s.transition(SessionState.TRANSCRIBING)
    s.transition(SessionState.CLASSIFYING)
    s.transition(SessionState.PLANNING)
    s.transition(SessionState.EXECUTING)
    s.transition(SessionState.COMPLETED)
    assert s.state == SessionState.COMPLETED
    assert s.is_terminal


def test_illegal_transition_raises():
    s = VoiceSession("vsess-1", "isiah")
    with pytest.raises(InvalidTransitionError):
        s.transition(SessionState.EXECUTING)  # can't jump from IDLE


def test_no_transition_from_terminal():
    s = VoiceSession("vsess-1", "isiah")
    s.transition(SessionState.LISTENING)
    s.refuse("prohibited")
    with pytest.raises(InvalidTransitionError):
        s.transition(SessionState.TRANSCRIBING)


def test_cancel_propagates_to_cancellable_children_and_marks_others():
    s = VoiceSession("vsess-1", "isiah")
    s.transition(SessionState.LISTENING)
    s.add_child(ChildTask("t1", cancellable=True))
    s.add_child(ChildTask("t2", cancellable=False))
    non_cancellable = s.cancel()
    assert s.state == SessionState.CANCELLED
    assert s.children[0].cancelled is True
    assert s.children[1].cancelled is False
    assert s.children[1].marked_noncancellable is True
    assert [c.task_id for c in non_cancellable] == ["t2"]


def test_pause_and_resume_preserve_audit_trail():
    s = VoiceSession("vsess-1", "isiah")
    s.transition(SessionState.LISTENING)
    s.transition(SessionState.TRANSCRIBING)
    s.pause()
    assert s.is_paused
    s.resume()
    assert not s.is_paused
    reasons = [h.reason for h in s.history]
    assert any("paused" in r for r in reasons)
    assert any("resumed" in r for r in reasons)


def test_history_records_every_transition():
    s = VoiceSession("vsess-1", "isiah")
    s.transition(SessionState.LISTENING, "wake word")
    s.transition(SessionState.TRANSCRIBING)
    assert len(s.history) == 2
    assert s.history[0].from_state == SessionState.IDLE


# ── transcript redaction / hash-only retention ───────────────────────────────


def test_transcript_hash_format():
    h = transcript_hash("secret words")
    assert h.startswith("sha256:")
    assert len(h) == len("sha256:") + 64


def test_receipt_hash_only_omits_raw_transcript():
    env = make_envelope(raw_transcript="my SSN is 123-45-6789")
    receipt = build_receipt(
        env,
        policy_decision="confirmation_required",
        result="completed",
        retention=TranscriptRetention.HASH_ONLY,
    )
    data = receipt.to_dict()
    assert "raw_transcript" not in data
    assert data["raw_transcript_hash"] == transcript_hash("my SSN is 123-45-6789")


def test_receipt_full_retention_includes_raw():
    env = make_envelope(raw_transcript="keep me")
    receipt = build_receipt(
        env, policy_decision="allowed", result="completed", retention=TranscriptRetention.FULL
    )
    assert receipt.to_dict()["raw_transcript"] == "keep me"


# ── receipt completeness + correlation propagation ───────────────────────────


def test_receipt_completeness():
    env = make_envelope()
    receipt = build_receipt(env, policy_decision="allowed", result="completed")
    data = receipt.to_dict()
    for key in (
        "command_id",
        "session_id",
        "source",
        "raw_transcript_hash",
        "normalized_intent",
        "risk_class",
        "policy_decision",
        "confirmation",
        "capability",
        "correlation_id",
        "result",
        "artifacts",
        "started_at",
        "completed_at",
    ):
        assert key in data


def test_correlation_propagates_from_envelope_to_receipt():
    env = make_envelope(correlation_id="corr-fixed-123")
    receipt = build_receipt(env, policy_decision="allowed", result="completed")
    assert receipt.correlation_id == "corr-fixed-123"


# ── feature flag env loading ─────────────────────────────────────────────────


def test_flags_default_all_false_except_retention(monkeypatch):
    for var in (
        "SP_VOICE_001_ENABLED",
        "SP_VOICE_001_REMOTE_ENABLED",
        "SP_VOICE_001_SCREEN_CONTEXT_ENABLED",
        "SP_VOICE_001_WRITE_ACTIONS_ENABLED",
        "SP_VOICE_001_TRANSCRIPT_RETENTION",
    ):
        monkeypatch.delenv(var, raising=False)
    flags = VoiceFeatureFlags.from_env()
    assert flags.enabled is False
    assert flags.remote_enabled is False
    assert flags.screen_context_enabled is False
    assert flags.write_actions_enabled is False
    assert flags.transcript_retention == TranscriptRetention.HASH_ONLY


def test_flags_env_enable(monkeypatch):
    monkeypatch.setenv("SP_VOICE_001_ENABLED", "true")
    monkeypatch.setenv("SP_VOICE_001_TRANSCRIPT_RETENTION", "full")
    flags = VoiceFeatureFlags.from_env()
    assert flags.enabled is True
    assert flags.transcript_retention == TranscriptRetention.FULL


def test_flags_unknown_retention_fails_safe(monkeypatch):
    monkeypatch.setenv("SP_VOICE_001_TRANSCRIPT_RETENTION", "everything")
    flags = VoiceFeatureFlags.from_env()
    assert flags.transcript_retention == TranscriptRetention.HASH_ONLY
