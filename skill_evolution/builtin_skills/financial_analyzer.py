"""
Financial Analyzer Skill

Performs budget analysis, credit scoring simulation, and financial ratio calculations.
Useful for legal cases involving financial disputes, bankruptcy, and business litigation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..skill_types import SkillCategory, SkillTemplate


class FinancialAnalyzerSkill(SkillTemplate):
    """Budget analysis, credit scoring, and financial ratio calculations."""

    @property
    def skill_id(self) -> str:
        return "builtin_financial_calc"

    @property
    def name(self) -> str:
        return "financial_calc"

    @property
    def description(self) -> str:
        return "Budget analysis, credit scoring, and financial ratio calculations."

    @property
    def category(self) -> SkillCategory:
        return SkillCategory.FINANCIAL

    @property
    def parameter_schema(self) -> Dict[str, Any]:
        return {
            "data": {
                "type": "dict",
                "required": True,
                "description": "Financial data dictionary",
            },
            "analysis_type": {
                "type": "str",
                "required": True,
                "description": "Type of analysis: budget|credit_score|ratios|liquidity|solvency",
            },
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Run financial analysis based on analysis_type."""
        data = kwargs.get("data", {})
        analysis_type = kwargs.get("analysis_type", "budget").lower()

        dispatch = {
            "budget": self.budget_analysis,
            "credit_score": self.credit_score,
            "ratios": self.financial_ratios,
            "liquidity": self.liquidity_analysis,
            "solvency": self.solvency_analysis,
        }

        if analysis_type not in dispatch:
            return {
                "error": f"Unknown analysis_type '{analysis_type}'. Use: {list(dispatch.keys())}",
                "success": False,
            }

        try:
            result = dispatch[analysis_type](data)
            result["success"] = True
            result["analysis_type"] = analysis_type
            result["analyzed_at"] = datetime.utcnow().isoformat()
            return result
        except (KeyError, TypeError, ValueError) as e:
            return {"error": f"Analysis failed: {e}", "success": False}

    def budget_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze income vs. expenses and compute surplus/deficit."""
        income = float(data.get("income", 0))
        expenses = data.get("expenses", {})

        if isinstance(expenses, dict):
            total_expenses = sum(float(v) for v in expenses.values())
            expense_breakdown = {k: float(v) for k, v in expenses.items()}
        elif isinstance(expenses, (int, float)):
            total_expenses = float(expenses)
            expense_breakdown = {"total": total_expenses}
        else:
            total_expenses = 0
            expense_breakdown = {}

        net = income - total_expenses
        savings_rate = (net / income * 100) if income > 0 else 0

        # Identify top expense categories
        sorted_expenses = sorted(expense_breakdown.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_income": round(income, 2),
            "total_expenses": round(total_expenses, 2),
            "net_surplus_deficit": round(net, 2),
            "savings_rate_pct": round(savings_rate, 2),
            "status": "surplus" if net >= 0 else "deficit",
            "top_expenses": sorted_expenses[:5],
            "expense_to_income_ratio": round(total_expenses / income, 4) if income > 0 else None,
        }

    def credit_score(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estimate a credit score (300–850 FICO-like) from financial attributes.

        Inputs: payment_history (0-1), utilization_ratio (0-1),
                account_age_years (int), derogatory_marks (int),
                credit_mix_count (int)
        """
        payment_history = float(data.get("payment_history", 1.0))  # 0-1, 1 = perfect
        utilization = float(data.get("utilization_ratio", 0.3))     # 0-1, lower is better
        account_age = float(data.get("account_age_years", 5))
        derogatory = int(data.get("derogatory_marks", 0))
        credit_mix = int(data.get("credit_mix_count", 2))

        # FICO weight approximation
        score = 300
        score += payment_history * 294        # 35% of 850-300
        score += max(0, (1 - utilization)) * 181  # 30%
        score += min(account_age / 15, 1) * 91    # 15%
        score += max(0, 1 - derogatory * 0.3) * 55  # 10%
        score += min(credit_mix / 5, 1) * 27     # 10%

        score = max(300, min(850, round(score)))

        rating = (
            "Exceptional (800-850)" if score >= 800 else
            "Very Good (740-799)" if score >= 740 else
            "Good (670-739)" if score >= 670 else
            "Fair (580-669)" if score >= 580 else
            "Poor (300-579)"
        )

        return {
            "estimated_score": score,
            "rating": rating,
            "factors": {
                "payment_history": f"{payment_history * 100:.0f}%",
                "utilization_ratio": f"{utilization * 100:.0f}%",
                "account_age_years": account_age,
                "derogatory_marks": derogatory,
                "credit_mix_accounts": credit_mix,
            },
            "note": "Estimate only. Actual FICO score requires credit bureau data.",
        }

    def financial_ratios(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate standard financial ratios from balance sheet data."""
        current_assets = float(data.get("current_assets", 0))
        current_liabilities = float(data.get("current_liabilities", 1))
        total_assets = float(data.get("total_assets", 0))
        total_liabilities = float(data.get("total_liabilities", 0))
        net_income = float(data.get("net_income", 0))
        revenue = float(data.get("revenue", 1))
        equity = total_assets - total_liabilities

        ratios: Dict[str, Any] = {}
        ratios["current_ratio"] = round(current_assets / current_liabilities, 3) if current_liabilities else None
        ratios["debt_to_equity"] = round(total_liabilities / equity, 3) if equity else None
        ratios["net_profit_margin"] = round(net_income / revenue * 100, 2) if revenue else None
        ratios["return_on_assets"] = round(net_income / total_assets * 100, 2) if total_assets else None
        ratios["return_on_equity"] = round(net_income / equity * 100, 2) if equity else None
        ratios["debt_ratio"] = round(total_liabilities / total_assets, 3) if total_assets else None

        return {"ratios": ratios}

    def liquidity_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess short-term liquidity position."""
        cash = float(data.get("cash", 0))
        receivables = float(data.get("receivables", 0))
        inventory = float(data.get("inventory", 0))
        current_liabilities = float(data.get("current_liabilities", 1))

        quick_ratio = (cash + receivables) / current_liabilities if current_liabilities else None
        cash_ratio = cash / current_liabilities if current_liabilities else None
        current_ratio = (cash + receivables + inventory) / current_liabilities if current_liabilities else None

        assessment = (
            "Strong" if (quick_ratio or 0) >= 1.5 else
            "Adequate" if (quick_ratio or 0) >= 1.0 else
            "At Risk" if (quick_ratio or 0) >= 0.5 else
            "Critical"
        )

        return {
            "current_ratio": round(current_ratio, 3) if current_ratio else None,
            "quick_ratio": round(quick_ratio, 3) if quick_ratio else None,
            "cash_ratio": round(cash_ratio, 3) if cash_ratio else None,
            "liquidity_assessment": assessment,
        }

    def solvency_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess long-term solvency (ability to meet long-term obligations)."""
        total_assets = float(data.get("total_assets", 0))
        total_liabilities = float(data.get("total_liabilities", 0))
        ebit = float(data.get("ebit", 0))          # Earnings before interest and taxes
        interest_expense = float(data.get("interest_expense", 1))
        long_term_debt = float(data.get("long_term_debt", 0))

        equity = total_assets - total_liabilities
        debt_to_equity = total_liabilities / equity if equity else None
        interest_coverage = ebit / interest_expense if interest_expense else None
        equity_ratio = equity / total_assets if total_assets else None

        assessment = (
            "Solvent" if (debt_to_equity or 999) < 1.5 and (interest_coverage or 0) > 3
            else "Moderately Leveraged" if (debt_to_equity or 999) < 3
            else "Highly Leveraged / At Risk"
        )

        return {
            "debt_to_equity_ratio": round(debt_to_equity, 3) if debt_to_equity else None,
            "interest_coverage_ratio": round(interest_coverage, 3) if interest_coverage else None,
            "equity_ratio": round(equity_ratio, 3) if equity_ratio else None,
            "long_term_debt": long_term_debt,
            "solvency_assessment": assessment,
        }
