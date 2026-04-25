"""
Financial Report Generator — Beautiful, professional financial artifacts.
Generates net worth statements, cash flow analyses, business valuations,
and comprehensive financial plans in structured, printable format.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import math
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class NetWorthReport:
    """Professional net worth statement."""
    as_of_date: str
    total_assets: float
    total_liabilities: float
    net_worth: float
    asset_breakdown: Dict[str, Dict[str, float]]
    liability_breakdown: Dict[str, Dict[str, float]]
    prior_year_net_worth: Optional[float]
    notes: List[str]

    def format_as_text(self) -> str:
        change = ""
        if self.prior_year_net_worth is not None:
            delta = self.net_worth - self.prior_year_net_worth
            pct = delta / abs(self.prior_year_net_worth) * 100 if self.prior_year_net_worth != 0 else 0
            arrow = "▲" if delta >= 0 else "▼"
            change = f"  Year-over-Year Change:    {arrow} ${abs(delta):,.0f} ({pct:+.1f}%)"

        lines = [
            "╔" + "═" * 72 + "╗",
            "║" + "  PERSONAL NET WORTH STATEMENT".center(72) + "║",
            "║" + f"  As of {self.as_of_date}".center(72) + "║",
            "╚" + "═" * 72 + "╝",
            "",
        ]
        if change:
            lines.append(change)
            lines.append("")

        # Assets
        lines += [
            "  ┌─ ASSETS " + "─" * 62 + "┐",
        ]
        for category, items in self.asset_breakdown.items():
            cat_total = sum(items.values())
            lines.append(f"  │  {category}")
            for name, value in items.items():
                lines.append(f"  │    {'·' + name:<42} ${value:>12,.0f}  │")
            lines.append(f"  │    {'Subtotal:':<42} ${cat_total:>12,.0f}  │")
            lines.append(f"  │" + " " * 58 + "  │")
        lines += [
            f"  │  {'TOTAL ASSETS':<44} ${self.total_assets:>12,.0f}  │",
            "  └" + "─" * 64 + "┘",
            "",
        ]

        # Liabilities
        lines += [
            "  ┌─ LIABILITIES " + "─" * 57 + "┐",
        ]
        for category, items in self.liability_breakdown.items():
            cat_total = sum(items.values())
            lines.append(f"  │  {category}")
            for name, value in items.items():
                lines.append(f"  │    {'·' + name:<42} ${value:>12,.0f}  │")
            lines.append(f"  │    {'Subtotal:':<42} ${cat_total:>12,.0f}  │")
            lines.append(f"  │" + " " * 58 + "  │")
        lines += [
            f"  │  {'TOTAL LIABILITIES':<44} ${self.total_liabilities:>12,.0f}  │",
            "  └" + "─" * 64 + "┘",
            "",
            "  " + "═" * 66,
            f"  {'NET WORTH (TOTAL ASSETS – TOTAL LIABILITIES)':<44} ${self.net_worth:>12,.0f}",
            "  " + "═" * 66,
        ]

        if self.notes:
            lines += ["", "  NOTES:"]
            for note in self.notes:
                lines.append(f"  • {note}")

        return "\n".join(lines)


@dataclass
class CashFlowReport:
    """Comprehensive cash flow analysis."""
    period: str
    total_monthly_income: float
    total_monthly_expenses: float
    monthly_surplus: float
    savings_rate: float
    income_breakdown: Dict[str, float]
    expense_breakdown: Dict[str, float]
    budget_analysis: Dict[str, Any]
    recommendations: List[str]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 72 + "╗",
            "║" + "  CASH FLOW ANALYSIS".center(72) + "║",
            "║" + f"  Period: {self.period}".center(72) + "║",
            "╚" + "═" * 72 + "╝",
            "",
            "  ┌─ INCOME ─────────────────────────────────────────────────────────┐",
        ]
        for source, amount in self.income_breakdown.items():
            lines.append(f"  │  {source:<50} ${amount:>10,.0f}  │")
        lines += [
            f"  │  {'TOTAL MONTHLY INCOME':<50} ${self.total_monthly_income:>10,.0f}  │",
            "  └───────────────────────────────────────────────────────────────────┘",
            "",
            "  ┌─ EXPENSES ────────────────────────────────────────────────────────┐",
        ]
        for category, amount in self.expense_breakdown.items():
            pct = amount / self.total_monthly_income * 100 if self.total_monthly_income > 0 else 0
            lines.append(f"  │  {category:<44} {pct:>4.0f}%  ${amount:>10,.0f}  │")
        lines += [
            f"  │  {'TOTAL MONTHLY EXPENSES':<44}       ${self.total_monthly_expenses:>10,.0f}  │",
            "  └───────────────────────────────────────────────────────────────────┘",
            "",
            "  ╔─ SUMMARY ─────────────────────────────────────────────────────────╗",
            f"  ║  Monthly Surplus (Deficit):              ${self.monthly_surplus:>12,.0f}  ║",
            f"  ║  Annual Surplus:                         ${self.monthly_surplus * 12:>12,.0f}  ║",
            f"  ║  Savings Rate:                           {self.savings_rate*100:>11.1f}%  ║",
            "  ╚───────────────────────────────────────────────────────────────────╝",
            "",
            "  50/30/20 RULE ANALYSIS:",
            f"  Needs (50% target):    ${self.total_monthly_income * 0.50:>10,.0f} | Actual: ${self.budget_analysis.get('needs', 0):>10,.0f}  {self._flag(self.budget_analysis.get('needs', 0), self.total_monthly_income * 0.50)}",
            f"  Wants (30% target):    ${self.total_monthly_income * 0.30:>10,.0f} | Actual: ${self.budget_analysis.get('wants', 0):>10,.0f}  {self._flag(self.budget_analysis.get('wants', 0), self.total_monthly_income * 0.30)}",
            f"  Savings (20% target):  ${self.total_monthly_income * 0.20:>10,.0f} | Actual: ${self.budget_analysis.get('savings', 0):>10,.0f}  {self._flag(self.total_monthly_income * 0.20, self.budget_analysis.get('savings', 0))}",
            "",
            "  RECOMMENDATIONS:",
        ]
        for rec in self.recommendations:
            lines.append(f"  → {rec}")
        return "\n".join(lines)

    def _flag(self, actual: float, target: float) -> str:
        if actual <= target * 1.05:
            return "✓ On track"
        else:
            return f"⚠ Over by ${actual - target:,.0f}"


@dataclass
class ValuationReport:
    """Business valuation report."""
    business_name: str
    valuation_date: str
    revenue: float
    ebitda: float
    sde: float
    asset_value: float
    income_value: float
    market_value: float
    weighted_value: float
    methodology: Dict[str, Any]
    notes: List[str]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 72 + "╗",
            "║" + "  BUSINESS VALUATION REPORT".center(72) + "║",
            "║" + f"  {self.business_name}".center(72) + "║",
            "║" + f"  As of {self.valuation_date}".center(72) + "║",
            "╚" + "═" * 72 + "╝",
            "",
            "  ┌─ FINANCIAL SUMMARY ───────────────────────────────────────────────┐",
            f"  │  Annual Revenue:                          ${self.revenue:>14,.0f}  │",
            f"  │  EBITDA:                                  ${self.ebitda:>14,.0f}  │",
            f"  │  SDE (Seller's Discretionary Earnings):   ${self.sde:>14,.0f}  │",
            "  └───────────────────────────────────────────────────────────────────┘",
            "",
            "  ┌─ VALUATION METHODS ────────────────────────────────────────────────┐",
            f"  │  Asset-Based Approach:                    ${self.asset_value:>14,.0f}  │",
            f"  │  Income Approach (DCF/Multiple):          ${self.income_value:>14,.0f}  │",
            f"  │  Market Comparable Approach:              ${self.market_value:>14,.0f}  │",
            "  ├───────────────────────────────────────────────────────────────────┤",
            f"  │  WEIGHTED AVERAGE VALUATION:              ${self.weighted_value:>14,.0f}  │",
            "  └───────────────────────────────────────────────────────────────────┘",
            "",
            "  METHODOLOGY DETAILS:",
        ]
        for method, details in self.methodology.items():
            lines.append(f"  ► {method}:")
            if isinstance(details, dict):
                for k, v in details.items():
                    lines.append(f"      {k}: {v}")
            else:
                lines.append(f"      {details}")
        if self.notes:
            lines += ["", "  NOTES:"]
            for note in self.notes:
                lines.append(f"  • {note}")
        return "\n".join(lines)


@dataclass
class ComprehensiveFinancialPlan:
    """Complete personal financial plan."""
    client_name: str
    plan_date: str
    sections: Dict[str, List[str]]
    ten_year_roadmap: List[Dict[str, str]]
    net_worth_projection: List[Dict[str, Any]]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 72 + "╗",
            "║" + "  COMPREHENSIVE FINANCIAL PLAN".center(72) + "║",
            "║" + f"  Prepared for: {self.client_name}".center(72) + "║",
            "║" + f"  Date: {self.plan_date}".center(72) + "║",
            "╚" + "═" * 72 + "╝",
        ]
        for section, items in self.sections.items():
            lines += ["", f"  ╔═ {section.upper()} " + "═" * (60 - len(section)) + "╗"]
            for item in items:
                lines.append(f"  ║  {item}")
            lines.append("  ╚" + "═" * 68 + "╝")

        lines += ["", "  10-YEAR FINANCIAL ROADMAP:", "  " + "─" * 68]
        for milestone in self.ten_year_roadmap:
            lines.append(f"  {milestone.get('year', '')}: {milestone.get('goal', '')} | {milestone.get('action', '')}")

        if self.net_worth_projection:
            lines += ["", "  NET WORTH PROJECTION:"]
            lines.append(f"  {'YEAR':<6} {'NET WORTH':>15} {'CHANGE':>12}")
            lines.append("  " + "─" * 36)
            prev = None
            for proj in self.net_worth_projection:
                nw = proj.get("net_worth", 0)
                change = f"+${nw - prev:,.0f}" if prev is not None else "—"
                lines.append(f"  {proj.get('year', ''):<6} ${nw:>14,.0f} {change:>12}")
                prev = nw

        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CLASS
# ─────────────────────────────────────────────────────────────────────────────

class FinancialReportGenerator:
    """
    Professional financial report generator.
    Creates beautiful, structured financial artifacts suitable for professional use.

    All reports return dataclass objects with format_as_text() for pretty output.

    Example:
        gen = FinancialReportGenerator()
        assets = {"liquid": {"Checking": 5000, "Savings": 20000}}
        liabilities = {"consumer": {"Car Loan": 15000}}
        report = gen.generate_net_worth_statement(assets, liabilities)
        print(report.format_as_text())
    """

    def generate_net_worth_statement(
        self,
        assets: dict,
        liabilities: dict,
        prior_year_net_worth: Optional[float] = None,
        as_of_date: Optional[str] = None,
    ) -> NetWorthReport:
        """
        Generate a professional net worth statement.

        Args:
            assets: Dict of category -> {item_name: value}
                    Categories: liquid, investment, retirement, real_estate, business, personal_property
            liabilities: Dict of category -> {item_name: value}
                         Categories: mortgage, auto_loans, student_loans, credit_cards, other_debt
            prior_year_net_worth: For year-over-year comparison
            as_of_date: Date string (default: today)

        Returns:
            NetWorthReport with format_as_text() method
        """
        date = as_of_date or datetime.now().strftime("%B %d, %Y")

        total_assets = sum(
            value for cat in assets.values() for value in (cat.values() if isinstance(cat, dict) else [cat])
        )
        total_liabilities = sum(
            value for cat in liabilities.values() for value in (cat.values() if isinstance(cat, dict) else [cat])
        )
        net_worth = total_assets - total_liabilities

        # Build categorized breakdowns
        asset_breakdown = {}
        for cat, items in assets.items():
            display = {
                "liquid": "Liquid Assets",
                "investment": "Investment Accounts",
                "retirement": "Retirement Accounts",
                "real_estate": "Real Estate",
                "business": "Business Interests",
                "personal_property": "Personal Property",
            }.get(cat, cat.replace("_", " ").title())
            asset_breakdown[display] = items if isinstance(items, dict) else {"Value": items}

        liability_breakdown = {}
        for cat, items in liabilities.items():
            display = {
                "mortgage": "Mortgage & Real Estate Debt",
                "auto_loans": "Auto Loans",
                "student_loans": "Student Loans",
                "credit_cards": "Credit Card Balances",
                "other_debt": "Other Debt",
            }.get(cat, cat.replace("_", " ").title())
            liability_breakdown[display] = items if isinstance(items, dict) else {"Balance": items}

        notes = [
            f"Total Assets: ${total_assets:,.0f} | Total Liabilities: ${total_liabilities:,.0f}",
            f"Debt-to-Asset Ratio: {total_liabilities/total_assets*100:.1f}%" if total_assets > 0 else "No assets",
        ]
        if net_worth < 0:
            notes.append("⚠ Negative net worth — focus on debt elimination and asset building")
        elif net_worth < 10000:
            notes.append("Building phase — consistent savings and debt payoff will accelerate growth")
        elif net_worth >= 1_000_000:
            notes.append("Millionaire milestone achieved — focus on tax efficiency and wealth preservation")

        return NetWorthReport(
            as_of_date=date,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            net_worth=net_worth,
            asset_breakdown=asset_breakdown,
            liability_breakdown=liability_breakdown,
            prior_year_net_worth=prior_year_net_worth,
            notes=notes,
        )

    def generate_cash_flow_analysis(self, income: dict, expenses: dict) -> CashFlowReport:
        """
        Generate a comprehensive cash flow analysis with budget optimization.

        Args:
            income: Dict of source -> monthly_amount (e.g., {"Salary": 7000, "Side Business": 500})
            expenses: Dict of category -> monthly_amount (e.g., {"Housing": 1800, "Food": 600})
                      Mark category as 'need' or 'want' by prefixing: "need_Housing", "want_Entertainment"

        Returns:
            CashFlowReport with format_as_text() method
        """
        total_income = sum(income.values())
        total_expenses = sum(expenses.values())
        surplus = total_income - total_expenses
        savings_rate = surplus / total_income if total_income > 0 else 0

        # Categorize expenses (50/30/20 rule)
        needs_amount = 0
        wants_amount = 0
        savings_amount = surplus

        needs_categories = {"housing", "utilities", "groceries", "transportation", "insurance",
                           "minimum_debt_payments", "healthcare", "childcare"}
        wants_categories = {"dining", "entertainment", "shopping", "subscriptions", "travel",
                           "hobbies", "gym", "beauty"}

        for cat, amount in expenses.items():
            cat_lower = cat.lower().replace(" ", "_")
            if any(n in cat_lower for n in needs_categories) or cat_lower.startswith("need_"):
                needs_amount += amount
            elif any(w in cat_lower for w in wants_categories) or cat_lower.startswith("want_"):
                wants_amount += amount
            else:
                needs_amount += amount  # Default to needs if unclear

        budget_analysis = {
            "needs": needs_amount,
            "wants": wants_amount,
            "savings": savings_amount,
        }

        recommendations = []
        if savings_rate < 0.10:
            recommendations.append(f"Increase savings rate — currently {savings_rate*100:.1f}%, target 20%+. Find ${total_income * 0.20 - savings_amount:,.0f}/month to cut or earn.")
        if savings_rate >= 0.20:
            recommendations.append(f"Excellent savings rate of {savings_rate*100:.1f}%! Ensure invested efficiently (not just in savings account).")
        if needs_amount > total_income * 0.55:
            recommendations.append(f"Needs consuming {needs_amount/total_income*100:.0f}% of income — above 50% target. Review housing costs (largest lever).")
        if surplus > 0:
            recommendations.append(f"${surplus:,.0f}/month surplus — prioritize: 1) High-interest debt, 2) Emergency fund, 3) 401k match, 4) IRA, 5) Invest remainder")
        if surplus < 0:
            recommendations.append(f"⚠ Spending exceeds income by ${abs(surplus):,.0f}/month — immediate action required to avoid accumulating debt")

        recommendations += [
            "Automate savings on payday — transfer before you can spend it",
            "Review subscriptions quarterly — average household pays $200+/month in unused subscriptions",
            "Track spending daily for 30 days — awareness reduces spending by 10–20%",
        ]

        period = datetime.now().strftime("%B %Y")
        return CashFlowReport(
            period=period,
            total_monthly_income=total_income,
            total_monthly_expenses=total_expenses,
            monthly_surplus=surplus,
            savings_rate=savings_rate,
            income_breakdown=income,
            expense_breakdown=expenses,
            budget_analysis=budget_analysis,
            recommendations=recommendations,
        )

    def generate_business_valuation(self, business: dict, financials: dict) -> ValuationReport:
        """
        Generate a professional business valuation using multiple methods.

        Args:
            business: dict with name, industry, years_in_business, num_employees,
                      owner_salary, growth_rate, industry_ebitda_multiple
            financials: dict with revenue, gross_profit, operating_expenses,
                        ebitda, net_income, total_assets, total_liabilities,
                        owner_benefits (addbacks)

        Returns:
            ValuationReport with multiple valuation methods
        """
        name = business.get("name", "Business")
        industry = business.get("industry", "General")
        years = business.get("years_in_business", 5)
        owner_salary = business.get("owner_salary", 100000)
        growth_rate = business.get("growth_rate", 0.05)
        industry_multiple = business.get("industry_ebitda_multiple", 4.0)

        revenue = financials.get("revenue", 0)
        ebitda = financials.get("ebitda", 0)
        net_income = financials.get("net_income", 0)
        total_assets = financials.get("total_assets", 0)
        total_liabilities = financials.get("total_liabilities", 0)
        owner_benefits = financials.get("owner_benefits", 0)

        # SDE = Net income + owner salary + owner benefits + one-time expenses
        sde = net_income + owner_salary + owner_benefits

        # 1. Asset-Based Approach
        book_value = total_assets - total_liabilities
        # Adjust for goodwill (estimate 1x annual net income)
        asset_value = max(book_value, total_assets * 0.85)

        # 2. Income Approach — EBITDA Multiple
        # Adjust multiple for size (smaller = lower multiple)
        size_adjustment = 0.8 if revenue < 1_000_000 else (1.0 if revenue < 5_000_000 else 1.2)
        growth_adjustment = 1.0 + (growth_rate - 0.03) * 2  # Premium for above-average growth
        adjusted_multiple = industry_multiple * size_adjustment * growth_adjustment

        ebitda_value = ebitda * adjusted_multiple

        # SDE multiple for small business (typically 2–4x SDE)
        sde_multiple = 2.5 if revenue < 500000 else (3.0 if revenue < 2_000_000 else industry_multiple)
        sde_value = sde * sde_multiple

        income_value = (ebitda_value + sde_value) / 2

        # 3. DCF Approach (simplified)
        wacc = 0.15  # Typical for small business risk
        terminal_multiple = 3.0
        dcf_years = 5
        fcf = ebitda * 0.75  # Approximate FCF
        pv_flows = sum(fcf * (1 + growth_rate) ** i / (1 + wacc) ** i for i in range(1, dcf_years + 1))
        terminal_value = (fcf * (1 + growth_rate) ** dcf_years * terminal_multiple) / (1 + wacc) ** dcf_years
        dcf_value = pv_flows + terminal_value

        market_value = (ebitda_value + dcf_value) / 2

        # Weighted average
        weights = {"asset": 0.20, "income": 0.50, "market": 0.30}
        weighted_value = (
            asset_value * weights["asset"] +
            income_value * weights["income"] +
            market_value * weights["market"]
        )

        methodology = {
            "Asset-Based Approach (20% weight)": {
                "Book Value": f"${book_value:,.0f}",
                "Adjusted Asset Value": f"${asset_value:,.0f}",
                "Best for": "Asset-heavy businesses, liquidation scenarios",
            },
            f"Income Approach — EBITDA Multiple (50% weight)": {
                "EBITDA": f"${ebitda:,.0f}",
                f"Industry Multiple ({industry})": f"{adjusted_multiple:.1f}x",
                "EBITDA Value": f"${ebitda_value:,.0f}",
                "SDE": f"${sde:,.0f}",
                "SDE Multiple": f"{sde_multiple:.1f}x",
                "SDE Value": f"${sde_value:,.0f}",
            },
            "Market/DCF Approach (30% weight)": {
                "DCF Value (5-year)": f"${dcf_value:,.0f}",
                "WACC Used": f"{wacc*100:.0f}%",
                "Growth Rate": f"{growth_rate*100:.1f}%",
            },
        }

        notes = [
            f"Revenue multiple: {revenue/weighted_value:.2f}x revenue" if weighted_value > 0 else "",
            f"EBITDA margin: {ebitda/revenue*100:.1f}%" if revenue > 0 else "",
            f"Years in business ({years}) {'adds stability premium' if years >= 5 else 'may warrant discount for risk'}",
            "Valuation is for reference only — actual sale price negotiated based on market conditions",
            "Consider seller financing (10–30% of purchase price) to maximize valuation and close deals",
            "Key value drivers: recurring revenue, diverse customer base, documented systems, owner not essential",
        ]

        return ValuationReport(
            business_name=name,
            valuation_date=datetime.now().strftime("%B %d, %Y"),
            revenue=revenue,
            ebitda=ebitda,
            sde=sde,
            asset_value=asset_value,
            income_value=income_value,
            market_value=market_value,
            weighted_value=weighted_value,
            methodology=methodology,
            notes=[n for n in notes if n],
        )

    def generate_financial_plan(self, facts: dict) -> ComprehensiveFinancialPlan:
        """
        Generate a complete comprehensive financial plan.

        Args:
            facts: dict with name, age, income, net_worth, debts, monthly_savings,
                   goals (list), has_emergency_fund, emergency_fund_months,
                   has_life_insurance, has_will, has_disability_insurance,
                   retirement_age, expected_retirement_income

        Returns:
            ComprehensiveFinancialPlan with 10-year roadmap
        """
        name = facts.get("name", "Client")
        age = facts.get("age", 35)
        income = facts.get("income", 80000)
        net_worth = facts.get("net_worth", 0)
        monthly_savings = facts.get("monthly_savings", 500)
        retirement_age = facts.get("retirement_age", 65)
        ef_months = facts.get("emergency_fund_months", 0)
        has_will = facts.get("has_will", False)
        has_life_ins = facts.get("has_life_insurance", False)
        has_disability = facts.get("has_disability_insurance", False)
        total_debt = facts.get("total_debt", 0)

        # Monthly income and emergency fund target
        monthly_income = income / 12
        ef_target = monthly_income * 6
        ef_current = monthly_income * ef_months

        # Projections
        years_to_retirement = retirement_age - age
        projected_retirement = (net_worth + monthly_savings * 12 * years_to_retirement) * (1.07 ** years_to_retirement)

        sections = {
            "Current Financial Position": [
                f"Annual Income: ${income:,.0f} | Monthly: ${monthly_income:,.0f}",
                f"Net Worth: ${net_worth:,.0f}",
                f"Total Debt: ${total_debt:,.0f}",
                f"Monthly Savings: ${monthly_savings:,.0f} ({monthly_savings/monthly_income*100:.1f}% savings rate)",
                f"Emergency Fund: {ef_months} months (${ef_current:,.0f}) {'✓' if ef_months >= 6 else f'⚠ Target: 6 months (${ef_target:,.0f})'}",
            ],
            "Priority Action Items": [
                "① Build emergency fund to 6 months of expenses FIRST",
                "② Eliminate high-interest debt (>7% APR) aggressively",
                "③ Contribute enough to 401(k) to capture ALL employer match",
                "④ Max out HSA if eligible (triple tax advantage)",
                "⑤ Max IRA ($7,000/year; $8,000 if 50+)",
                "⑥ Max 401(k) ($23,000/year)",
                "⑦ Invest additional savings in taxable brokerage",
            ],
            "Insurance Needs Analysis": [
                f"Life Insurance: {'✓ Has coverage' if has_life_ins else '⚠ MISSING — Get 10–12x income in term life insurance'} | Target: ${income * 10:,.0f}–${income * 12:,.0f}",
                f"Disability Insurance: {'✓ Has coverage' if has_disability else '⚠ MISSING — 60% of income protected (most critical insurance)'}",
                "Health Insurance: Ensure adequate coverage with manageable deductible",
                "Umbrella Insurance: $1M policy for ~$200–$400/year (essential if any assets)",
                "Property/Auto: Review annually — avoid over-insuring depreciating assets",
            ],
            "Estate Planning Needs": [
                f"Will: {'✓ In place' if has_will else '⚠ MISSING — Create will immediately (LegalZoom or estate attorney, ~$500–$1,500)'}",
                "Healthcare Directive (Living Will): Required if incapacitated",
                "Financial Power of Attorney: Who manages finances if incapacitated?",
                "Beneficiary Designations: Review on ALL accounts and insurance policies (overrides will)",
                "Digital asset access: Document all accounts, passwords, crypto keys",
            ],
            "Tax Optimization": [
                "Maximize pre-tax retirement contributions to reduce taxable income",
                f"Marginal rate reduction: Every $1,000 to 401(k) saves ~${income * 0.001 * 0.25:,.0f} in taxes",
                "HSA contributions: $4,150 individual/$8,300 family — fully deductible",
                "Qualified Business Income (QBI): If self-employed, consider S-corp election",
                "Charitable giving: Donor-advised fund if itemizing; appreciated stock donations",
            ],
            "Retirement Projection": [
                f"Years to retirement ({retirement_age}): {years_to_retirement}",
                f"Projected retirement portfolio: ${projected_retirement:,.0f}",
                f"Monthly income at 4% SWR: ${projected_retirement * 0.04 / 12:,.0f}",
                "Maximize catch-up contributions starting at age 50 (+$7,500 to 401k, +$1,000 to IRA)",
                "Consider Roth conversion ladder in low-income years before retirement",
            ],
        }

        # 10-year roadmap
        roadmap = []
        current_year = datetime.now().year
        for yr in range(1, 11):
            year = current_year + yr
            nw_proj = net_worth + monthly_savings * 12 * yr * (1.07 ** yr)
            if yr == 1:
                goal = "Foundation"
                action = "Build emergency fund, get employer match, eliminate bad debt"
            elif yr <= 3:
                goal = "Debt Freedom"
                action = "Aggressive debt payoff, maximize tax-advantaged accounts"
            elif yr <= 5:
                goal = "Accumulation"
                action = f"Net worth ~${nw_proj:,.0f} | Max all retirement accounts + taxable investing"
            elif yr <= 7:
                goal = "Wealth Building"
                action = f"Net worth ~${nw_proj:,.0f} | Real estate or business investment, estate planning"
            else:
                goal = "Acceleration"
                action = f"Net worth ~${nw_proj:,.0f} | Optimize for FIRE or retirement target"
            roadmap.append({"year": str(year), "goal": goal, "action": action})

        nw_projections = [
            {"year": current_year + i, "net_worth": net_worth + monthly_savings * 12 * i * (1.07 ** i)}
            for i in range(0, 11, 2)
        ]

        return ComprehensiveFinancialPlan(
            client_name=name,
            plan_date=datetime.now().strftime("%B %d, %Y"),
            sections=sections,
            ten_year_roadmap=roadmap,
            net_worth_projection=nw_projections,
        )
