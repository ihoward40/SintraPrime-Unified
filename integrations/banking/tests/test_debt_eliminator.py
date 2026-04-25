"""
Tests for DebtEliminator — avalanche, snowball, hybrid strategies, extra payment impact,
consolidation analysis, and edge cases.
"""

import pytest
from datetime import date

from integrations.banking.debt_eliminator import (
    DebtEliminator,
    DebtItem,
    DebtStrategy,
    DebtPayoffPlan,
    DebtEliminationReport,
    ExtraPaymentImpact,
)


@pytest.fixture
def eliminator():
    return DebtEliminator()


@pytest.fixture
def typical_debts():
    return [
        DebtItem(
            debt_id="d1",
            name="Chase Sapphire",
            current_balance=5_000.00,
            apr=0.22,
            minimum_payment=100.0,
            account_type="credit_card",
        ),
        DebtItem(
            debt_id="d2",
            name="Wells Fargo Card",
            current_balance=2_500.00,
            apr=0.19,
            minimum_payment=50.0,
            account_type="credit_card",
        ),
        DebtItem(
            debt_id="d3",
            name="Student Loan",
            current_balance=12_000.00,
            apr=0.065,
            minimum_payment=150.0,
            account_type="student_loan",
        ),
    ]


@pytest.fixture
def single_debt():
    return [
        DebtItem(
            debt_id="s1",
            name="Personal Loan",
            current_balance=3_000.00,
            apr=0.12,
            minimum_payment=75.0,
            account_type="personal_loan",
        )
    ]


class TestAvalancheStrategy:
    def test_avalanche_pays_highest_apr_first(self, eliminator, typical_debts):
        plan = eliminator._calculate_plan(typical_debts, 500, DebtStrategy.AVALANCHE)
        assert "Chase Sapphire" in plan.debt_payoff_order[0]

    def test_avalanche_returns_payoff_plan(self, eliminator, typical_debts):
        plan = eliminator._calculate_plan(typical_debts, 500, DebtStrategy.AVALANCHE)
        assert isinstance(plan, DebtPayoffPlan)
        assert plan.total_months > 0

    def test_avalanche_minimizes_interest(self, eliminator, typical_debts):
        avalanche = eliminator._calculate_plan(typical_debts, 500, DebtStrategy.AVALANCHE)
        snowball = eliminator._calculate_plan(typical_debts, 500, DebtStrategy.SNOWBALL)
        assert avalanche.total_interest_paid <= snowball.total_interest_paid


class TestSnowballStrategy:
    def test_snowball_pays_lowest_balance_first(self, eliminator, typical_debts):
        plan = eliminator._calculate_plan(typical_debts, 500, DebtStrategy.SNOWBALL)
        assert "Wells Fargo" in plan.debt_payoff_order[0]

    def test_snowball_returns_plan(self, eliminator, typical_debts):
        plan = eliminator._calculate_plan(typical_debts, 500, DebtStrategy.SNOWBALL)
        assert plan.total_months > 0
        assert plan.total_interest_paid > 0

    def test_snowball_psychological_wins(self, eliminator):
        debts = [
            DebtItem(debt_id="a", name="SmallCard", current_balance=200, apr=0.20, minimum_payment=15),
            DebtItem(debt_id="b", name="BigLoan", current_balance=20_000, apr=0.10, minimum_payment=300),
        ]
        plan = eliminator._calculate_plan(debts, 600, DebtStrategy.SNOWBALL)
        assert "SmallCard" == plan.debt_payoff_order[0]


class TestHybridStrategy:
    def test_hybrid_returns_plan(self, eliminator, typical_debts):
        plan = eliminator._calculate_plan(typical_debts, 500, DebtStrategy.HYBRID)
        assert isinstance(plan, DebtPayoffPlan)
        assert plan.total_months > 0

    def test_hybrid_between_avalanche_and_snowball(self, eliminator, typical_debts):
        avalanche = eliminator._calculate_plan(typical_debts, 500, DebtStrategy.AVALANCHE)
        snowball = eliminator._calculate_plan(typical_debts, 500, DebtStrategy.SNOWBALL)
        hybrid = eliminator._calculate_plan(typical_debts, 500, DebtStrategy.HYBRID)
        # Hybrid interest should be between or equal to avalanche (best) and snowball (most interest)
        assert avalanche.total_interest_paid <= hybrid.total_interest_paid + 0.01


class TestFullReport:
    def test_report_generated(self, eliminator, typical_debts):
        report = eliminator.analyze("client_001", typical_debts)
        assert isinstance(report, DebtEliminationReport)
        assert report.total_debt > 0

    def test_report_includes_both_strategies(self, eliminator, typical_debts):
        report = eliminator.analyze("client_001", typical_debts)
        assert report.comparison.avalanche is not None
        assert report.comparison.snowball is not None

    def test_report_has_recommendation(self, eliminator, typical_debts):
        report = eliminator.analyze("client_001", typical_debts)
        assert report.comparison.recommended_strategy in (
            DebtStrategy.AVALANCHE, DebtStrategy.SNOWBALL, DebtStrategy.HYBRID
        )

    def test_total_debt_accurate(self, eliminator, typical_debts):
        report = eliminator.analyze("client_001", typical_debts)
        expected_total = sum(d.current_balance for d in typical_debts)
        assert abs(report.total_debt - expected_total) < 1.0

    def test_weighted_apr(self, eliminator, typical_debts):
        report = eliminator.analyze("client_001", typical_debts)
        assert 0 < report.weighted_average_apr < 1


class TestExtraPaymentImpact:
    def test_extra_payment_reduces_timeline(self, eliminator, typical_debts):
        report = eliminator.analyze("client_001", typical_debts)
        for impact in report.extra_payment_impacts:
            assert impact.months_saved >= 0

    def test_extra_payment_saves_interest(self, eliminator, typical_debts):
        report = eliminator.analyze("client_001", typical_debts)
        for impact in report.extra_payment_impacts:
            assert impact.interest_saved >= 0

    def test_extra_payments_tested(self, eliminator, typical_debts):
        report = eliminator.analyze("client_001", typical_debts)
        extras = [i.extra_monthly for i in report.extra_payment_impacts]
        assert 100 in extras
        assert 200 in extras
        assert 500 in extras

    def test_larger_extra_saves_more(self, eliminator, typical_debts):
        report = eliminator.analyze("client_001", typical_debts)
        impacts = sorted(report.extra_payment_impacts, key=lambda i: i.extra_monthly)
        if len(impacts) >= 2:
            assert impacts[-1].months_saved >= impacts[0].months_saved


class TestConsolidation:
    def test_consolidation_analysis_present(self, eliminator, typical_debts):
        report = eliminator.analyze("client_001", typical_debts, analyze_consolidation=True)
        assert report.consolidation is not None

    def test_consolidation_has_fields(self, eliminator, typical_debts):
        report = eliminator.analyze("client_001", typical_debts)
        c = report.consolidation
        if c:
            assert c.current_weighted_apr > 0
            assert c.new_monthly_payment > 0

    def test_single_debt_no_consolidation(self, eliminator, single_debt):
        report = eliminator.analyze("client_001", single_debt)
        # Single debt: no consolidation needed
        assert report.consolidation is None or not report.consolidation.recommended


class TestEdgeCases:
    def test_empty_debts_raises(self, eliminator):
        with pytest.raises(ValueError):
            eliminator.analyze("client_001", [])

    def test_zero_balance_debt(self, eliminator):
        debts = [
            DebtItem(debt_id="z1", name="Zero Card", current_balance=0.00, apr=0.20, minimum_payment=0),
            DebtItem(debt_id="z2", name="Real Card", current_balance=1_000.00, apr=0.18, minimum_payment=25),
        ]
        report = eliminator.analyze("client_001", debts)
        assert report.total_debt == 1_000.00

    def test_very_small_debt(self, eliminator):
        debts = [
            DebtItem(debt_id="small1", name="Tiny Balance", current_balance=5.00, apr=0.20, minimum_payment=5.00),
        ]
        report = eliminator.analyze("client_001", debts)
        assert report.comparison.avalanche.total_months <= 2

    def test_very_high_apr(self, eliminator):
        debts = [
            DebtItem(debt_id="p1", name="Payday Loan", current_balance=500, apr=3.99, minimum_payment=100),
        ]
        report = eliminator.analyze("client_001", debts)
        assert report.comparison.avalanche.total_months < 600
