from dataclasses import replace

from legal_intelligence.capital_dashboard import CapitalDashboardEngine
from legal_intelligence.capital_servicing import CapitalServicingEngine
from legal_intelligence.decision_journal import DecisionJournalHashChain


def test_servicing_escalates_delinquent_covenant_breach_to_workout_review():
    report = CapitalServicingEngine().review({
        "facility_id": "FAC-1",
        "days_past_due": 45,
        "missed_payments": 1,
        "principal_outstanding": 10000,
        "collateral_value": 8000,
        "covenant_tests": {"minimum_liquidity": False, "reporting": True},
        "collateral_revaluation_due": True,
    })
    assert report.status == "WORKOUT_REVIEW"
    assert "minimum_liquidity" in report.covenant_breaches
    assert report.workout_options
    assert report.collateral_actions
    assert report.beneficial_suggestions


def test_dashboard_surfaces_reserve_shortfall_delinquency_and_aged_exception():
    report = CapitalDashboardEngine().build({
        "as_of": "2026-09-30",
        "available_liquidity": 15000,
        "reserve_available": 5000,
        "reserve_required": 8000,
        "borrowing_base_available": 12000,
        "concentration_flags": ["AFFILIATE_GROUP_LIMIT"],
        "facilities": [
            {
                "facility_id": "FAC-1",
                "principal_outstanding": 10000,
                "collateral_value": 9000,
                "days_past_due": 35,
                "covenant_breaches": ["minimum_liquidity"],
                "exceptions": [{"code": "PAST_DUE_REPORTING", "age_days": 45}],
            },
            {
                "facility_id": "FAC-2",
                "principal_outstanding": 5000,
                "collateral_value": 7000,
                "days_past_due": 0,
            },
        ],
    })
    assert report.total_exposure == 15000
    assert report.reserve_shortfall == 3000
    assert report.delinquent_exposure == 10000
    assert report.weighted_collateral_coverage == 1.0667
    assert report.aged_exceptions
    assert report.beneficial_suggestions


def test_decision_journal_hash_chain_detects_tampering():
    journal = DecisionJournalHashChain()
    first = journal.append(
        actor="Principal",
        action="APPROVE",
        subject_id="FAC-1",
        decision="APPROVED_WITH_CONDITIONS",
        rationale="Cash flow and collateral within policy",
        evidence_refs=["UW-001", "VAL-001"],
        timestamp="2026-09-14T22:00:00+00:00",
    )
    second = journal.append(
        actor="Principal",
        action="COLLATERAL_REVALUATION",
        subject_id="FAC-1",
        decision="VALUE_UPDATED",
        rationale="Monthly valuation refresh",
        evidence_refs=["VAL-002"],
        prior_entry=first,
        timestamp="2026-09-30T22:00:00+00:00",
    )
    assert journal.verify([first, second])["valid"] is True

    tampered = replace(second, rationale="altered later")
    verification = journal.verify([first, tampered])
    assert verification["valid"] is False
    assert any("ENTRY_HASH_MISMATCH" in issue for issue in verification["issues"])
