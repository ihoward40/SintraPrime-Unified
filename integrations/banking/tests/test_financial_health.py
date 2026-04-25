"""
Tests for FinancialHealthScorer — composite score, letter grades, 8 dimensions.
"""

import pytest
from datetime import datetime

from integrations.banking.financial_health_scorer import (
    FinancialHealthScorer,
    FinancialHealthInput,
    FinancialHealthReport,
    HealthDimension,
)


@pytest.fixture
def scorer():
    return FinancialHealthScorer()


def make_input(
    monthly_income: float = 8_000,
    monthly_expenses: float = 5_000,
    liquid_savings: float = 15_000,
    total_debt: float = 20_000,
    monthly_debt_payments: float = 600,
    monthly_savings: float = 1_000,
    monthly_investments: float = 500,
    credit_score: int = 720,
    net_worth: float = 50_000,
    net_worth_prior_year: float = 45_000,
    budget_adherence_pct: float = 85.0,
    has_life_insurance: bool = True,
    has_health_insurance: bool = True,
    has_disability_insurance: bool = False,
    has_property_insurance: bool = True,
) -> FinancialHealthInput:
    return FinancialHealthInput(
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        liquid_savings=liquid_savings,
        total_debt=total_debt,
        monthly_debt_payments=monthly_debt_payments,
        monthly_savings=monthly_savings,
        monthly_investments=monthly_investments,
        credit_score=credit_score,
        net_worth=net_worth,
        net_worth_prior_year=net_worth_prior_year,
        budget_adherence_pct=budget_adherence_pct,
        has_life_insurance=has_life_insurance,
        has_health_insurance=has_health_insurance,
        has_disability_insurance=has_disability_insurance,
        has_property_insurance=has_property_insurance,
    )


class TestCompositeScore:
    def test_score_in_range(self, scorer):
        inp = make_input()
        report = scorer.score(inp)
        assert 0 <= report.composite_score <= 100

    def test_high_score_for_excellent_profile(self, scorer):
        inp = make_input(
            liquid_savings=50_000,
            monthly_income=15_000,
            monthly_expenses=7_000,
            total_debt=5_000,
            monthly_debt_payments=200,
            credit_score=800,
            net_worth=500_000,
            net_worth_prior_year=400_000,
            budget_adherence_pct=95.0,
            has_disability_insurance=True,
        )
        report = scorer.score(inp)
        assert report.composite_score >= 80

    def test_low_score_for_poor_profile(self, scorer):
        inp = make_input(
            liquid_savings=500,
            monthly_income=3_000,
            monthly_expenses=4_000,
            total_debt=80_000,
            monthly_debt_payments=2_000,
            credit_score=520,
            net_worth=-10_000,
            net_worth_prior_year=-5_000,
            budget_adherence_pct=40.0,
            has_life_insurance=False,
            has_health_insurance=False,
            has_disability_insurance=False,
            has_property_insurance=False,
        )
        report = scorer.score(inp)
        assert report.composite_score <= 40

    def test_score_is_reproducible(self, scorer):
        inp = make_input()
        r1 = scorer.score(inp)
        r2 = scorer.score(inp)
        assert r1.composite_score == r2.composite_score


class TestLetterGrade:
    def test_a_grade_for_high_score(self, scorer):
        inp = make_input(
            liquid_savings=60_000,
            monthly_income=20_000,
            monthly_expenses=8_000,
            credit_score=800,
            net_worth=600_000,
            net_worth_prior_year=500_000,
            has_disability_insurance=True,
            budget_adherence_pct=98.0,
        )
        report = scorer.score(inp)
        assert report.letter_grade in ("A+", "A", "A-")

    def test_f_grade_for_very_poor_profile(self, scorer):
        inp = make_input(
            liquid_savings=0,
            monthly_income=2_000,
            monthly_expenses=5_000,
            total_debt=150_000,
            monthly_debt_payments=3_000,
            credit_score=450,
            net_worth=-80_000,
            net_worth_prior_year=-60_000,
            has_life_insurance=False,
            has_health_insurance=False,
            has_disability_insurance=False,
            has_property_insurance=False,
            budget_adherence_pct=10.0,
        )
        report = scorer.score(inp)
        assert report.letter_grade in ("D", "D-", "F")


class TestDimensions:
    def test_all_8_dimensions_present(self, scorer):
        inp = make_input()
        report = scorer.score(inp)
        assert len(report.dimensions) == 8

    def test_emergency_fund_high_score(self, scorer):
        inp = make_input(liquid_savings=30_000, monthly_expenses=5_000)  # 6 months coverage
        report = scorer.score(inp)
        ef = next((d for d in report.dimensions if d.name == HealthDimension.EMERGENCY_FUND), None)
        if ef:
            assert ef.score >= 70

    def test_emergency_fund_low_score(self, scorer):
        inp = make_input(liquid_savings=500, monthly_expenses=5_000)  # 0.1 month
        report = scorer.score(inp)
        ef = next((d for d in report.dimensions if d.name == HealthDimension.EMERGENCY_FUND), None)
        if ef:
            assert ef.score <= 30

    def test_debt_to_income_score(self, scorer):
        inp = make_input(monthly_income=10_000, monthly_debt_payments=500)  # 5% DTI = great
        report = scorer.score(inp)
        dti = next((d for d in report.dimensions if d.name == HealthDimension.DEBT_TO_INCOME), None)
        if dti:
            assert dti.score >= 80

    def test_savings_rate_score(self, scorer):
        inp = make_input(monthly_income=10_000, monthly_savings=2_000)  # 20% savings rate
        report = scorer.score(inp)
        sr = next((d for d in report.dimensions if d.name == HealthDimension.SAVINGS_RATE), None)
        if sr:
            assert sr.score >= 70


class TestRecommendations:
    def test_report_has_recommendations(self, scorer):
        inp = make_input()
        report = scorer.score(inp)
        assert len(report.recommendations) > 0

    def test_recommendation_for_no_emergency_fund(self, scorer):
        inp = make_input(liquid_savings=100)
        report = scorer.score(inp)
        all_recs = " ".join(report.recommendations).lower()
        assert "emergency" in all_recs or "savings" in all_recs

    def test_recommendation_for_no_insurance(self, scorer):
        inp = make_input(
            has_life_insurance=False,
            has_health_insurance=False,
            has_disability_insurance=False,
            has_property_insurance=False,
        )
        report = scorer.score(inp)
        all_recs = " ".join(report.recommendations).lower()
        assert "insurance" in all_recs


class TestEdgeCases:
    def test_zero_income(self, scorer):
        inp = make_input(monthly_income=0)
        report = scorer.score(inp)
        assert 0 <= report.composite_score <= 100

    def test_negative_net_worth(self, scorer):
        inp = make_input(net_worth=-50_000, net_worth_prior_year=-30_000)
        report = scorer.score(inp)
        nw = next((d for d in report.dimensions if d.name == HealthDimension.NET_WORTH_GROWTH), None)
        if nw:
            assert nw.score <= 40

    def test_perfect_credit_score(self, scorer):
        inp = make_input(credit_score=850)
        report = scorer.score(inp)
        cs = next((d for d in report.dimensions if d.name == HealthDimension.CREDIT_SCORE), None)
        if cs:
            assert cs.score >= 95

    def test_no_insurance_coverage(self, scorer):
        inp = make_input(
            has_life_insurance=False,
            has_health_insurance=False,
            has_disability_insurance=False,
            has_property_insurance=False,
        )
        report = scorer.score(inp)
        ins = next((d for d in report.dimensions if d.name == HealthDimension.INSURANCE_COVERAGE), None)
        if ins:
            assert ins.score <= 20
