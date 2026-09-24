from datetime import date, timedelta

from legal_intelligence.capital_action_tracker import CapitalAction, CapitalActionTrackerEngine
from legal_intelligence.capital_committee_decisions import CapitalCommitteeDecisionsEngine, CommitteeDecision


def test_committee_decision_requires_traceable_disposition_fields():
    engine = CapitalCommitteeDecisionsEngine()
    decision = CommitteeDecision(
        decision_id="DEC-2026-09-01",
        meeting_period="2026-09",
        decision_type="RISK_REMEDIATION",
        responsible_owner="treasury_owner",
        approval_authority="capital_committee",
        effective_date=date(2026, 9, 14),
        required_actions=("Reduce borrower concentration",),
        action_deadline=date(2026, 9, 30),
        evidence_refs=("committee-pack:2026-09",),
        journal_entry_ref="journal:120",
        conditions=("No new discretionary advances until concentration returns to policy",),
        dissent=("member-b requested faster reduction",),
        policy_id="CAP-POLICY",
        policy_version="2.0",
    )
    report = engine.validate(decision)
    assert report.valid
    payloads = engine.open_action_payloads(decision)
    assert payloads[0]["action_id"] == "DEC-2026-09-01-A01"
    assert payloads[0]["evidence_required"] is True


def test_committee_decision_blocks_missing_journal_and_evidence():
    engine = CapitalCommitteeDecisionsEngine()
    decision = CommitteeDecision(
        decision_id="DEC-X",
        meeting_period="2026-09",
        decision_type="TEST",
        responsible_owner="owner",
        approval_authority="committee",
        effective_date=date(2026, 9, 14),
        required_actions=("Do thing",),
        action_deadline=date(2026, 9, 15),
        evidence_refs=(),
        journal_entry_ref="",
    )
    report = engine.validate(decision)
    assert not report.valid
    assert "EVIDENCE_REFERENCE_REQUIRED" in report.findings
    assert "JOURNAL_ENTRY_REQUIRED" in report.findings


def test_action_tracker_marks_overdue_and_requires_completion_evidence():
    engine = CapitalActionTrackerEngine()
    action = CapitalAction(
        action_id="A1",
        decision_id="D1",
        owner="owner-a",
        action="Obtain new valuation",
        due_date=date(2026, 9, 10),
    )
    overdue = engine.evaluate(action, date(2026, 9, 14))
    assert overdue.status == "OVERDUE"
    assert "ACTION_OVERDUE" in overdue.findings

    action.status = "COMPLETE"
    deficient = engine.evaluate(action, date(2026, 9, 14))
    assert deficient.status == "EVIDENCE_DEFICIENT"
    assert "COMPLETION_EVIDENCE_REQUIRED" in deficient.findings


def test_action_tracker_requires_independent_closure_certification():
    engine = CapitalActionTrackerEngine()
    action = CapitalAction(
        action_id="A2",
        decision_id="D2",
        owner="owner-a",
        action="Cure reserve shortfall",
        due_date=date(2026, 9, 20),
    )
    blocked = engine.certify_closure(
        action,
        certifier="owner-a",
        authority="risk-reviewer",
        certified_date=date(2026, 9, 18),
        evidence_refs=("bank-statement:sept",),
    )
    assert blocked.status == "BLOCK_CLOSURE"
    assert "INDEPENDENT_CLOSURE_CERTIFICATION_REQUIRED" in blocked.findings

    closed = engine.certify_closure(
        action,
        certifier="reviewer-b",
        authority="risk-reviewer",
        certified_date=date(2026, 9, 18),
        evidence_refs=("bank-statement:sept", "ledger-reconciliation:sept"),
    )
    assert closed.status == "CLOSED"


def test_reopen_trigger_reopens_closed_action():
    engine = CapitalActionTrackerEngine()
    action = CapitalAction(
        action_id="A3",
        decision_id="D3",
        owner="owner-a",
        action="Maintain insurance",
        due_date=date(2026, 9, 20),
        status="CLOSED",
        evidence_refs=["policy:abc"],
        closure_certifier="reviewer-b",
        closure_authority="risk-reviewer",
        closure_certified_date=date(2026, 9, 15),
        reopen_trigger="INSURANCE_LAPSE",
    )
    report = engine.evaluate(action, date(2026, 9, 18))
    assert report.status == "REOPENED"
    assert "REOPEN_TRIGGER:INSURANCE_LAPSE" in report.findings
