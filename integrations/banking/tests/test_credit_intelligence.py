"""
Tests for CreditIntelligence — score analysis, improvement plans, utilization optimizer.
"""

import pytest
from datetime import date, datetime
from typing import List

from integrations.banking.credit_intelligence import (
    CreditIntelligence,
    CreditReport,
    CreditAccount,
    CreditComponent,
    CreditScoreTier,
    CreditImprovementPlan,
)


def make_credit_account(
    account_id: str,
    name: str,
    account_type: str,
    balance: float,
    credit_limit: float = None,
    apr: float = None,
    payment_status: str = "current",
    age_months: int = 36,
    utilization: float = None,
) -> CreditAccount:
    util = utilization if utilization is not None else (balance / credit_limit if credit_limit else 0)
    return CreditAccount(
        account_id=account_id,
        name=name,
        account_type=account_type,
        current_balance=balance,
        credit_limit=credit_limit,
        apr=apr,
        payment_status=payment_status,
        account_age_months=age_months,
        utilization=util,
    )


def make_report(
    score: int = 720,
    accounts: List[CreditAccount] = None,
    missed_payments: int = 0,
    derogatory: int = 0,
    inquiries: int = 1,
) -> CreditReport:
    accts = accounts or [
        make_credit_account("cc1", "Visa Signature", "credit_card", 500, 5_000),
        make_credit_account("cc2", "Amex Gold", "credit_card", 200, 10_000),
        make_credit_account("sl1", "Navient Student Loan", "student_loan", 15_000),
    ]
    total_util = (
        sum(a.current_balance for a in accts if a.credit_limit)
        / sum(a.credit_limit for a in accts if a.credit_limit)
        if any(a.credit_limit for a in accts) else 0
    )
    avg_age = sum(a.account_age_months for a in accts) / max(len(accts), 1)
    return CreditReport(
        credit_score=score,
        score_model="FICO 8",
        score_tier=CreditScoreTier.GOOD if score >= 670 else CreditScoreTier.FAIR,
        accounts=accts,
        total_utilization=round(total_util, 4),
        total_missed_payments=missed_payments,
        derogatory_marks=derogatory,
        recent_inquiries=inquiries,
        average_account_age_months=avg_age,
        oldest_account_age_months=max(a.account_age_months for a in accts),
        last_updated=datetime.utcnow(),
    )


@pytest.fixture
def intel():
    return CreditIntelligence()


class TestScoreTierClassification:
    def test_exceptional(self, intel):
        report = make_report(score=820)
        assert report.score_tier in (CreditScoreTier.EXCEPTIONAL, CreditScoreTier.VERY_GOOD)

    def test_good(self, intel):
        report = make_report(score=700)
        assert report.score_tier == CreditScoreTier.GOOD

    def test_poor(self):
        from integrations.banking.credit_intelligence import CreditScoreTier
        assert CreditScoreTier.POOR.value == "poor"


class TestScoreComponents:
    def test_returns_all_five_components(self, intel):
        report = make_report(score=720)
        components = intel.compute_components(report)
        assert len(components) == 5

    def test_components_sum_to_100_weight(self, intel):
        report = make_report(score=720)
        components = intel.compute_components(report)
        total_weight = sum(c.weight for c in components)
        assert abs(total_weight - 100) < 1

    def test_payment_history_poor_when_missed(self, intel):
        report = make_report(score=620, missed_payments=3)
        components = intel.compute_components(report)
        payment = next(c for c in components if "payment" in c.name.lower())
        assert payment.current_score < 70

    def test_utilization_good_when_low(self, intel):
        accts = [
            make_credit_account("cc1", "Visa", "credit_card", 100, 10_000),
        ]
        report = make_report(score=760, accounts=accts)
        components = intel.compute_components(report)
        util = next((c for c in components if "utilization" in c.name.lower()), None)
        if util:
            assert util.current_score >= 80


class TestImprovementPlan:
    def test_plan_returned_for_fair_score(self, intel):
        report = make_report(score=640)
        plan = intel.build_improvement_plan(report, target_score=720)
        assert isinstance(plan, CreditImprovementPlan)
        assert len(plan.actions) > 0

    def test_plan_has_prioritized_actions(self, intel):
        report = make_report(score=640)
        plan = intel.build_improvement_plan(report, target_score=720)
        priorities = [a.priority for a in plan.actions]
        assert priorities == sorted(priorities)

    def test_plan_target_score_set(self, intel):
        report = make_report(score=650)
        plan = intel.build_improvement_plan(report, target_score=740)
        assert plan.target_score == 740

    def test_plan_for_high_utilization(self, intel):
        accts = [
            make_credit_account("cc1", "Visa", "credit_card", 4_500, 5_000, utilization=0.90),
        ]
        report = make_report(score=640, accounts=accts)
        plan = intel.build_improvement_plan(report, target_score=720)
        action_texts = [a.action.lower() for a in plan.actions]
        assert any("utilization" in t or "balance" in t or "pay" in t for t in action_texts)


class TestUtilizationOptimizer:
    def test_optimal_balances_below_30_pct(self, intel):
        accts = [
            make_credit_account("cc1", "Visa", "credit_card", 3_000, 5_000, utilization=0.60),
            make_credit_account("cc2", "Amex", "credit_card", 4_000, 10_000, utilization=0.40),
        ]
        report = make_report(score=660, accounts=accts)
        plan = intel.utilization_optimizer(report, target_utilization=0.10)
        assert len(plan) >= 1
        for item in plan:
            assert item.target_balance <= item.credit_limit * 0.11

    def test_no_recommendations_when_already_optimal(self, intel):
        accts = [
            make_credit_account("cc1", "Visa", "credit_card", 100, 10_000, utilization=0.01),
        ]
        report = make_report(score=780, accounts=accts)
        plan = intel.utilization_optimizer(report, target_utilization=0.10)
        assert len(plan) == 0


class TestCreditAlerts:
    def test_alert_for_high_utilization(self, intel):
        accts = [
            make_credit_account("cc1", "Visa", "credit_card", 4_500, 5_000, utilization=0.90),
        ]
        report = make_report(score=640, accounts=accts)
        alerts = intel.generate_alerts(report)
        assert any("utilization" in a.lower() for a in alerts)

    def test_alert_for_missed_payment(self, intel):
        report = make_report(score=580, missed_payments=2)
        alerts = intel.generate_alerts(report)
        assert any("payment" in a.lower() or "missed" in a.lower() for a in alerts)

    def test_no_alerts_for_excellent_profile(self, intel):
        accts = [make_credit_account("cc1", "Visa", "credit_card", 100, 10_000)]
        report = make_report(score=800, accounts=accts)
        alerts = intel.generate_alerts(report)
        assert len(alerts) == 0
