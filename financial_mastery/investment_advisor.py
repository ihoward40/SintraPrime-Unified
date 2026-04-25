"""
Investment Advisor — Fiduciary-level investment intelligence.
Covers portfolio construction, retirement planning, real estate analysis,
tax-loss harvesting, and cryptocurrency strategy.
Replaces a CFP, RIA, and investment advisor.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
import math


# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RiskProfile:
    """Complete risk profile for an investor."""
    risk_tolerance: str           # conservative / moderate / aggressive / very_aggressive
    risk_capacity: str            # low / medium / high
    time_horizon_years: int
    questionnaire_score: int      # 0–100
    notes: List[str]
    recommended_allocation: Dict[str, float]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 68 + "╗",
            "║  INVESTOR RISK PROFILE" + " " * 45 + "║",
            "╚" + "═" * 68 + "╝",
            "",
            f"  Risk Tolerance:     {self.risk_tolerance.title()}",
            f"  Risk Capacity:      {self.risk_capacity.title()}",
            f"  Time Horizon:       {self.time_horizon_years} years",
            f"  Risk Score:         {self.questionnaire_score}/100",
            "",
            "  RECOMMENDED ALLOCATION:",
        ]
        for asset, pct in self.recommended_allocation.items():
            bar = "█" * int(pct / 2)
            lines.append(f"  {asset:<30} {pct:>5.1f}% {bar}")
        lines += ["", "  NOTES:"]
        for note in self.notes:
            lines.append(f"  • {note}")
        return "\n".join(lines)


@dataclass
class InvestmentPlan:
    """Complete investment plan for an investor."""
    risk_profile: str
    time_horizon_years: int
    portfolio_allocation: Dict[str, float]
    specific_recommendations: List[dict]
    expected_annual_return: float
    max_drawdown_estimate: float
    tax_efficiency_score: float
    rebalancing_schedule: str
    annual_investment_amount: float = 0.0

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 72 + "╗",
            "║  INVESTMENT PLAN" + " " * 55 + "║",
            "╚" + "═" * 72 + "╝",
            "",
            f"  Risk Profile:          {self.risk_profile.title()}",
            f"  Time Horizon:          {self.time_horizon_years} years",
            f"  Expected Annual Return: {self.expected_annual_return*100:.1f}%",
            f"  Max Drawdown Estimate: -{self.max_drawdown_estimate*100:.0f}%",
            f"  Tax Efficiency Score:  {self.tax_efficiency_score*100:.0f}/100",
            f"  Rebalancing:           {self.rebalancing_schedule}",
            "",
            "  PORTFOLIO ALLOCATION:",
            "  " + "─" * 60,
        ]
        for asset, pct in self.portfolio_allocation.items():
            bar = "▓" * int(pct / 2)
            lines.append(f"  {asset:<35} {pct:>5.1f}% {bar}")
        lines += ["", "  SPECIFIC FUND RECOMMENDATIONS:"]
        for rec in self.specific_recommendations:
            lines.append(f"  • {rec.get('fund', '')}: {rec.get('ticker', '')} — {rec.get('expense_ratio', '')} ER")
            lines.append(f"    {rec.get('description', '')}")
        return "\n".join(lines)


@dataclass
class RetirementPlan:
    """Comprehensive retirement plan."""
    current_age: int
    retirement_age: int
    current_savings: float
    monthly_contribution: float
    projected_balance_at_retirement: float
    monthly_income_at_retirement: float
    social_security_estimate: float
    probability_of_success: float
    strategies: List[str]
    account_recommendations: List[Dict[str, Any]]
    rmd_starting_age: int = 73

    def format_as_text(self) -> str:
        years_to_retirement = self.retirement_age - self.current_age
        lines = [
            "╔" + "═" * 70 + "╗",
            "║  RETIREMENT PLAN" + " " * 53 + "║",
            "╚" + "═" * 70 + "╝",
            "",
            f"  Current Age:               {self.current_age}",
            f"  Target Retirement Age:     {self.retirement_age}",
            f"  Years to Retirement:       {years_to_retirement}",
            f"  Current Savings:           ${self.current_savings:,.0f}",
            f"  Monthly Contribution:      ${self.monthly_contribution:,.0f}",
            "",
            f"  PROJECTED BALANCE AT {self.retirement_age}: ${self.projected_balance_at_retirement:,.0f}",
            f"  Monthly Income (4% Rule):  ${self.monthly_income_at_retirement:,.0f}",
            f"  Social Security Estimate:  ${self.social_security_estimate:,.0f}/month",
            f"  Probability of Success:    {self.probability_of_success*100:.0f}%",
            f"  RMD Starting Age:          {self.rmd_starting_age}",
            "",
            "  ACCOUNT RECOMMENDATIONS:",
        ]
        for acct in self.account_recommendations:
            lines.append(f"  • {acct.get('account', '')}: Contribute ${acct.get('annual_contribution', 0):,.0f}/yr")
            lines.append(f"    {acct.get('why', '')}")
        lines += ["", "  STRATEGIES:"]
        for s in self.strategies:
            lines.append(f"  → {s}")
        return "\n".join(lines)


@dataclass
class RealEstateAnalysis:
    """Real estate investment analysis."""
    property_address: str
    purchase_price: float
    monthly_rent: float
    cap_rate: float
    cash_on_cash_return: float
    gross_rent_multiplier: float
    irr_estimate: float
    annual_cash_flow: float
    recommendation: str
    notes: List[str]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 70 + "╗",
            "║  REAL ESTATE INVESTMENT ANALYSIS" + " " * 37 + "║",
            "╚" + "═" * 70 + "╝",
            "",
            f"  Property:           {self.property_address}",
            f"  Purchase Price:     ${self.purchase_price:,.0f}",
            f"  Monthly Rent:       ${self.monthly_rent:,.0f}",
            "",
            f"  ┌─ KEY METRICS ───────────────────────────────────────────┐",
            f"  │  Cap Rate:                    {self.cap_rate*100:.2f}%                │",
            f"  │  Cash-on-Cash Return:         {self.cash_on_cash_return*100:.2f}%                │",
            f"  │  Gross Rent Multiplier:       {self.gross_rent_multiplier:.1f}x                  │",
            f"  │  IRR Estimate:                {self.irr_estimate*100:.1f}%                   │",
            f"  │  Annual Cash Flow:            ${self.annual_cash_flow:,.0f}               │",
            f"  └──────────────────────────────────────────────────────────┘",
            "",
            f"  RECOMMENDATION: {self.recommendation}",
            "",
            "  NOTES:",
        ]
        for note in self.notes:
            lines.append(f"  • {note}")
        return "\n".join(lines)


@dataclass
class TaxLossStrategy:
    """Tax-loss harvesting strategy."""
    opportunities: List[Dict[str, Any]]
    estimated_tax_savings: float
    wash_sale_warnings: List[str]
    asset_location_recommendations: List[str]
    action_items: List[str]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 70 + "╗",
            "║  TAX-LOSS HARVESTING STRATEGY" + " " * 40 + "║",
            "╚" + "═" * 70 + "╝",
            "",
            f"  Estimated Tax Savings: ${self.estimated_tax_savings:,.0f}",
            "",
            "  HARVESTING OPPORTUNITIES:",
        ]
        for opp in self.opportunities:
            lines.append(f"  • Sell: {opp.get('sell', '')} | Loss: ${opp.get('loss', 0):,.0f}")
            lines.append(f"    Replace with: {opp.get('replacement', '')} (avoid wash sale)")
        if self.wash_sale_warnings:
            lines += ["", "  ⚠ WASH SALE WARNINGS:"]
            for w in self.wash_sale_warnings:
                lines.append(f"  ! {w}")
        lines += ["", "  ASSET LOCATION (Tax-Advantaged vs Taxable):"]
        for rec in self.asset_location_recommendations:
            lines.append(f"  • {rec}")
        lines += ["", "  ACTION ITEMS:"]
        for item in self.action_items:
            lines.append(f"  → {item}")
        return "\n".join(lines)


@dataclass
class CryptoStrategy:
    """Cryptocurrency investment and tax strategy."""
    allocation_pct: float
    recommended_assets: List[Dict[str, Any]]
    tax_treatment_notes: List[str]
    security_recommendations: List[str]
    risk_warnings: List[str]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 70 + "╗",
            "║  CRYPTOCURRENCY STRATEGY" + " " * 45 + "║",
            "╚" + "═" * 70 + "╝",
            "",
            f"  Portfolio Allocation:  {self.allocation_pct:.1f}% (of total portfolio)",
            "",
            "  RECOMMENDED ASSETS:",
        ]
        for asset in self.recommended_assets:
            lines.append(f"  • {asset.get('name', '')} ({asset.get('ticker', '')}): {asset.get('allocation', 0):.1f}% — {asset.get('rationale', '')}")
        lines += ["", "  TAX TREATMENT (IRS Notice 2014-21 + Rev. Rul. 2023-14):"]
        for note in self.tax_treatment_notes:
            lines.append(f"  • {note}")
        lines += ["", "  SECURITY — COLD STORAGE:"]
        for sec in self.security_recommendations:
            lines.append(f"  🔒 {sec}")
        lines += ["", "  ⚠ RISK WARNINGS:"]
        for w in self.risk_warnings:
            lines.append(f"  ! {w}")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CLASS
# ─────────────────────────────────────────────────────────────────────────────

class InvestmentAdvisor:
    """
    Fiduciary-level investment intelligence system.
    Replaces a CFP, RIA (Registered Investment Advisor), and financial planner.

    Operates on fiduciary standard — recommendations based on client's best interest,
    not commissions. Emphasizes low-cost index funds, tax efficiency, and evidence-based
    investing principles (Fama-French, CAPM, behavioral finance).

    Example:
        advisor = InvestmentAdvisor()
        profile = advisor.risk_assessment({"age": 35, "income": 120000, "risk_tolerance": "moderate"})
        plan = advisor.build_investment_plan(profile, [{"goal": "retirement", "years": 30}])
    """

    # ─────────────────────────────────────────────────────────────────────────
    # RISK ASSESSMENT
    # ─────────────────────────────────────────────────────────────────────────

    def risk_assessment(self, investor: dict) -> RiskProfile:
        """
        Complete risk assessment combining risk tolerance, capacity, and requirement.

        Args:
            investor: dict with age, income, net_worth, investment_amount,
                      time_horizon_years, risk_tolerance ('conservative'/'moderate'/'aggressive'),
                      has_emergency_fund, job_stability, dependents,
                      prior_investment_experience

        Returns:
            RiskProfile with recommended allocation
        """
        age = investor.get("age", 40)
        income = investor.get("income", 60000)
        net_worth = investor.get("net_worth", 0)
        time_horizon = investor.get("time_horizon_years", 20)
        stated_tolerance = investor.get("risk_tolerance", "moderate")
        has_emergency_fund = investor.get("has_emergency_fund", True)
        job_stability = investor.get("job_stability", "stable")  # stable/unstable/self-employed
        dependents = investor.get("dependents", 0)
        experience = investor.get("prior_investment_experience", "basic")

        # Questionnaire scoring (0–100, higher = more risk appropriate)
        score = 50  # baseline

        # Time horizon adjustment
        if time_horizon >= 30:
            score += 20
        elif time_horizon >= 20:
            score += 15
        elif time_horizon >= 10:
            score += 5
        elif time_horizon < 5:
            score -= 20

        # Age factor (100 minus age = equity allocation starting point)
        if age < 30:
            score += 15
        elif age < 40:
            score += 8
        elif age < 50:
            score += 0
        elif age < 60:
            score -= 10
        else:
            score -= 20

        # Risk capacity factors
        if has_emergency_fund:
            score += 5
        else:
            score -= 15
        if job_stability == "unstable":
            score -= 10
        if dependents > 2:
            score -= 5

        # Stated tolerance
        tolerance_map = {"conservative": -20, "moderate": 0, "aggressive": 20, "very_aggressive": 30}
        score += tolerance_map.get(stated_tolerance, 0)

        # Experience
        if experience in ("advanced", "professional"):
            score += 10
        elif experience == "none":
            score -= 5

        score = max(0, min(100, score))

        # Determine risk profile
        if score >= 75:
            risk_tol = "very_aggressive"
            risk_cap = "high"
            allocation = {
                "US Total Market Index": 45.0,
                "International Developed Markets": 20.0,
                "Emerging Markets": 10.0,
                "Small-Cap Value Factor": 10.0,
                "REITs": 5.0,
                "Bonds/Fixed Income": 5.0,
                "Cash/Short-Term": 5.0,
            }
            expected_return = 0.10
            max_drawdown = 0.55
        elif score >= 55:
            risk_tol = "aggressive"
            risk_cap = "high"
            allocation = {
                "US Total Market Index": 40.0,
                "International Developed Markets": 20.0,
                "Emerging Markets": 8.0,
                "Small-Cap Value Factor": 7.0,
                "REITs": 5.0,
                "Bonds/Fixed Income": 15.0,
                "Cash/Short-Term": 5.0,
            }
            expected_return = 0.085
            max_drawdown = 0.45
        elif score >= 35:
            risk_tol = "moderate"
            risk_cap = "medium"
            allocation = {
                "US Total Market Index": 30.0,
                "International Developed Markets": 15.0,
                "Emerging Markets": 5.0,
                "REITs": 5.0,
                "Total Bond Market Index": 30.0,
                "International Bonds": 5.0,
                "Cash/Money Market": 10.0,
            }
            expected_return = 0.065
            max_drawdown = 0.30
        else:
            risk_tol = "conservative"
            risk_cap = "low"
            allocation = {
                "US Total Market Index": 20.0,
                "International Developed Markets": 10.0,
                "Short-Term Bond Index": 25.0,
                "Total Bond Market Index": 25.0,
                "TIPS (Inflation-Protected)": 10.0,
                "High-Yield Savings/Money Market": 10.0,
            }
            expected_return = 0.045
            max_drawdown = 0.15

        notes = [
            f"Risk score: {score}/100",
            f"Time horizon: {time_horizon} years — {'long enough to ride out volatility' if time_horizon >= 10 else 'short — consider more conservative allocation'}",
            "Emergency fund: " + ("Present ✓ — can stay invested during market downturns" if has_emergency_fund else "MISSING ⚠ — build 3–6 months expenses BEFORE investing"),
            f"Age-based equity target: {max(20, 110 - age)}% equities (110 minus age rule)",
            "Review and rebalance annually or when allocation drifts >5% from target",
        ]

        return RiskProfile(
            risk_tolerance=risk_tol,
            risk_capacity=risk_cap,
            time_horizon_years=time_horizon,
            questionnaire_score=score,
            notes=notes,
            recommended_allocation=allocation,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # BUILD INVESTMENT PLAN
    # ─────────────────────────────────────────────────────────────────────────

    def build_investment_plan(self, profile: RiskProfile, goals: List[dict]) -> InvestmentPlan:
        """
        Build a complete investment plan with specific fund recommendations.

        Args:
            profile: RiskProfile from risk_assessment()
            goals: List of dicts with goal ('retirement'/'house'/'education'/'emergency'),
                   target_amount, years, monthly_contribution

        Returns:
            InvestmentPlan with specific low-cost index fund recommendations
        """
        risk = profile.risk_tolerance
        annual_investment = sum(g.get("monthly_contribution", 0) * 12 for g in goals)

        # Core index fund recommendations by risk profile
        if risk in ("aggressive", "very_aggressive"):
            recommendations = [
                {"fund": "Vanguard Total Stock Market ETF", "ticker": "VTI", "expense_ratio": "0.03%",
                 "description": "Core US equity — 3,600+ stocks, ultimate diversification"},
                {"fund": "Vanguard Total International Stock ETF", "ticker": "VXUS", "expense_ratio": "0.07%",
                 "description": "International equity — developed + emerging markets"},
                {"fund": "Vanguard Small-Cap Value ETF", "ticker": "VBR", "expense_ratio": "0.07%",
                 "description": "Small-cap value factor tilt — historically outperforms over long periods"},
                {"fund": "Vanguard Real Estate ETF", "ticker": "VNQ", "expense_ratio": "0.12%",
                 "description": "REITs — inflation hedge, income, diversification"},
                {"fund": "Vanguard Total Bond Market ETF", "ticker": "BND", "expense_ratio": "0.03%",
                 "description": "Stabilizer — reduces portfolio volatility"},
                {"fund": "Fidelity ZERO Total Market Index", "ticker": "FZROX", "expense_ratio": "0.00%",
                 "description": "Fidelity 0% ER alternative for tax-advantaged accounts"},
            ]
            expected_return = 0.092
            max_drawdown = 0.50
            tax_score = 0.85
        elif risk == "moderate":
            recommendations = [
                {"fund": "Vanguard Total Stock Market ETF", "ticker": "VTI", "expense_ratio": "0.03%",
                 "description": "US equity core — 30–40% of portfolio"},
                {"fund": "Vanguard Total International Stock ETF", "ticker": "VXUS", "expense_ratio": "0.07%",
                 "description": "International equity — 15–20% of portfolio"},
                {"fund": "Vanguard Total Bond Market ETF", "ticker": "BND", "expense_ratio": "0.03%",
                 "description": "Investment-grade bonds — 25–30% of portfolio"},
                {"fund": "Vanguard Short-Term Inflation-Protected Securities", "ticker": "VTIP", "expense_ratio": "0.04%",
                 "description": "Inflation protection — hold in tax-advantaged accounts"},
                {"fund": "Fidelity ZERO International Index", "ticker": "FZILX", "expense_ratio": "0.00%",
                 "description": "0% ER international — great for Fidelity accounts"},
            ]
            expected_return = 0.068
            max_drawdown = 0.30
            tax_score = 0.80
        else:  # conservative
            recommendations = [
                {"fund": "Vanguard LifeStrategy Conservative Growth", "ticker": "VSCGX", "expense_ratio": "0.12%",
                 "description": "All-in-one 40/60 fund — simple, rebalances automatically"},
                {"fund": "Vanguard Short-Term Bond ETF", "ticker": "BSV", "expense_ratio": "0.04%",
                 "description": "Low duration bonds — less interest rate risk"},
                {"fund": "Schwab U.S. Broad Market ETF", "ticker": "SCHB", "expense_ratio": "0.03%",
                 "description": "Core equity — lower volatility for conservative investors"},
                {"fund": "iShares TIPS Bond ETF", "ticker": "TIP", "expense_ratio": "0.19%",
                 "description": "Inflation-protected treasuries — preserve purchasing power"},
            ]
            expected_return = 0.048
            max_drawdown = 0.18
            tax_score = 0.75

        # Add factor tilt for long time horizons
        if profile.time_horizon_years >= 20 and risk in ("aggressive", "very_aggressive"):
            recommendations.append({
                "fund": "Avantis U.S. Small Cap Value ETF",
                "ticker": "AVUV",
                "expense_ratio": "0.25%",
                "description": "Fama-French small-cap value factor — expected excess return over market",
            })
            recommendations.append({
                "fund": "Avantis International Small Cap Value ETF",
                "ticker": "AVDV",
                "expense_ratio": "0.36%",
                "description": "International small-cap value factor tilt",
            })

        rebalancing = (
            "Annually (January) + drift-based: rebalance when any asset class drifts >5% from target. "
            "In tax-advantaged accounts: rebalance freely. In taxable: use new contributions first."
        )

        return InvestmentPlan(
            risk_profile=risk,
            time_horizon_years=profile.time_horizon_years,
            portfolio_allocation=profile.recommended_allocation,
            specific_recommendations=recommendations,
            expected_annual_return=expected_return,
            max_drawdown_estimate=max_drawdown,
            tax_efficiency_score=tax_score,
            rebalancing_schedule=rebalancing,
            annual_investment_amount=annual_investment,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # RETIREMENT PLANNING
    # ─────────────────────────────────────────────────────────────────────────

    def retirement_planning(self, facts: dict) -> RetirementPlan:
        """
        Comprehensive retirement planning with account optimization.

        Args:
            facts: dict with current_age, retirement_age, current_savings,
                   monthly_contribution, expected_return, income,
                   has_401k, has_ira, has_roth_ira, employer_match_pct,
                   employer_match_limit, social_security_estimate

        Returns:
            RetirementPlan with projections and strategies
        """
        age = facts.get("current_age", 40)
        ret_age = facts.get("retirement_age", 65)
        savings = facts.get("current_savings", 0)
        monthly_contrib = facts.get("monthly_contribution", 1000)
        expected_return = facts.get("expected_return", 0.07)
        income = facts.get("income", 80000)
        employer_match = facts.get("employer_match_pct", 0.03)
        match_limit = facts.get("employer_match_limit", 0.06)
        ss_estimate = facts.get("social_security_estimate", 2000)

        years = ret_age - age
        months = years * 12

        # Future value projection: FV = PV(1+r)^n + PMT * ((1+r)^n - 1) / r
        monthly_rate = expected_return / 12
        if monthly_rate > 0:
            fv_existing = savings * (1 + monthly_rate) ** months
            fv_contributions = monthly_contrib * (((1 + monthly_rate) ** months - 1) / monthly_rate)
        else:
            fv_existing = savings
            fv_contributions = monthly_contrib * months

        total_projected = fv_existing + fv_contributions

        # 4% safe withdrawal rate
        monthly_income = total_projected * 0.04 / 12

        # Monte Carlo simple success probability
        # Based on historical data: 60/40 portfolio succeeds ~95% of time with 4% SWR
        prob_success = self._monte_carlo_success(
            total_projected, monthly_income + ss_estimate, expected_return, years
        )

        strategies = [
            "ALWAYS capture employer match FIRST — it's an instant 50–100% return on investment",
            f"401(k) 2024 contribution limit: $23,000 (+$7,500 if age 50+). Maximize if possible.",
            "Backdoor Roth IRA: If income >$161K (single)/$240K (married), contribute to traditional IRA then convert to Roth (no income limit on conversion)",
            "Roth vs Traditional: Pay taxes now (Roth) if you expect higher tax bracket in retirement; defer (Traditional) if lower bracket expected",
            "Social Security optimization: Delay claiming to age 70 for maximum benefit (8%/year increase from 62–70)",
            f"Required Minimum Distributions start at age 73 — use Roth conversion ladder before RMDs start",
            "Asset location: Put tax-inefficient assets (bonds, REITs) in 401k/IRA; tax-efficient (index ETFs) in taxable",
            "Sequence of returns risk: First 10 years of retirement — keep 2–3 years of expenses in cash/short-term bonds",
        ]

        account_recommendations = [
            {
                "account": "401(k) up to employer match",
                "annual_contribution": income * match_limit,
                "why": "Instant 100% return from employer match — absolute priority",
            },
            {
                "account": "Health Savings Account (HSA) — triple tax advantage",
                "annual_contribution": 4150,  # 2024 individual limit
                "why": "Tax deductible, grows tax-free, withdrawals tax-free for medical. After 65, withdraw for anything (like IRA).",
            },
            {
                "account": "Max 401(k) contribution",
                "annual_contribution": 23000,
                "why": "Pre-tax contribution reduces current year taxes; compound growth tax-deferred",
            },
            {
                "account": "Roth IRA (or backdoor Roth)",
                "annual_contribution": 7000,  # 2024 limit
                "why": "Tax-free growth and withdrawals in retirement. No RMDs. Best for young investors.",
            },
            {
                "account": "Taxable Brokerage (after maxing tax-advantaged)",
                "annual_contribution": max(0, monthly_contrib * 12 - 23000 - 7000 - 4150),
                "why": "Unlimited contributions, long-term capital gains rates (0/15/20%), step-up in basis at death",
            },
        ]

        return RetirementPlan(
            current_age=age,
            retirement_age=ret_age,
            current_savings=savings,
            monthly_contribution=monthly_contrib,
            projected_balance_at_retirement=round(total_projected, 2),
            monthly_income_at_retirement=round(monthly_income, 2),
            social_security_estimate=ss_estimate,
            probability_of_success=prob_success,
            strategies=strategies,
            account_recommendations=account_recommendations,
            rmd_starting_age=73,
        )

    def _monte_carlo_success(
        self, portfolio: float, monthly_withdrawal: float, return_rate: float, years_remaining: int
    ) -> float:
        """Simple Monte Carlo success probability using historical volatility assumptions."""
        annual_withdrawal = monthly_withdrawal * 12
        withdrawal_rate = annual_withdrawal / portfolio if portfolio > 0 else 1.0
        # Historical success rates from Bengen/Trinity study
        if withdrawal_rate <= 0.03:
            return 0.99
        elif withdrawal_rate <= 0.04:
            return 0.95 - max(0, (years_remaining - 30) * 0.005)
        elif withdrawal_rate <= 0.05:
            return 0.82
        elif withdrawal_rate <= 0.06:
            return 0.68
        else:
            return 0.50

    # ─────────────────────────────────────────────────────────────────────────
    # REAL ESTATE INVESTMENT ANALYZER
    # ─────────────────────────────────────────────────────────────────────────

    def real_estate_investment_analyzer(self, property: dict) -> RealEstateAnalysis:
        """
        Analyze a real estate investment opportunity with all standard metrics.

        Args:
            property: dict with purchase_price, monthly_rent, address,
                      property_taxes_annual, insurance_annual, hoa_monthly,
                      maintenance_pct (of value, typically 1%), vacancy_rate,
                      management_fee_pct, mortgage_rate, down_payment_pct,
                      hold_years, appreciation_rate

        Returns:
            RealEstateAnalysis with cap rate, CoC return, IRR, and recommendation
        """
        price = property.get("purchase_price", 0)
        rent = property.get("monthly_rent", 0)
        address = property.get("address", "Unknown Property")
        prop_tax = property.get("property_taxes_annual", price * 0.012)
        insurance = property.get("insurance_annual", price * 0.005)
        hoa = property.get("hoa_monthly", 0) * 12
        maintenance = property.get("maintenance_pct", 0.01) * price
        vacancy_rate = property.get("vacancy_rate", 0.08)
        mgmt_fee = property.get("management_fee_pct", 0.10)
        mortgage_rate = property.get("mortgage_rate", 0.075)
        down_pct = property.get("down_payment_pct", 0.20)
        hold_years = property.get("hold_years", 5)
        appreciation = property.get("appreciation_rate", 0.03)

        # Gross annual rent
        gross_rent = rent * 12
        effective_rent = gross_rent * (1 - vacancy_rate)

        # Operating expenses
        mgmt_cost = effective_rent * mgmt_fee
        total_opex = prop_tax + insurance + hoa + maintenance + mgmt_cost

        # Net Operating Income
        noi = effective_rent - total_opex

        # Cap Rate
        cap_rate = noi / price if price > 0 else 0

        # Mortgage calculation
        down_payment = price * down_pct
        loan_amount = price - down_payment
        monthly_rate = mortgage_rate / 12
        n_payments = 30 * 12
        if monthly_rate > 0:
            monthly_mortgage = loan_amount * (monthly_rate * (1 + monthly_rate) ** n_payments) / ((1 + monthly_rate) ** n_payments - 1)
        else:
            monthly_mortgage = loan_amount / n_payments
        annual_debt_service = monthly_mortgage * 12

        # Cash-on-Cash Return
        annual_cash_flow = noi - annual_debt_service
        coc_return = annual_cash_flow / down_payment if down_payment > 0 else 0

        # Gross Rent Multiplier
        grm = price / gross_rent if gross_rent > 0 else 0

        # Simple IRR estimate (including appreciation)
        future_value = price * (1 + appreciation) ** hold_years
        total_cash_flows = [-down_payment] + [annual_cash_flow] * (hold_years - 1) + [annual_cash_flow + (future_value - loan_amount)]
        irr = self._simple_irr(total_cash_flows)

        # DSCR
        dscr = noi / annual_debt_service if annual_debt_service > 0 else 0

        # Recommendation
        if cap_rate >= 0.07 and coc_return >= 0.08:
            recommendation = "✓ STRONG BUY — Excellent cap rate and cash-on-cash return"
        elif cap_rate >= 0.05 and coc_return >= 0.05:
            recommendation = "✓ BUY — Solid investment with good fundamentals"
        elif cap_rate >= 0.04:
            recommendation = "○ HOLD/CONSIDER — Below average returns; check appreciation potential"
        else:
            recommendation = "✗ PASS — Cap rate too low; better opportunities likely available"

        notes = [
            f"NOI: ${noi:,.0f}/year | Annual Debt Service: ${annual_debt_service:,.0f}/year",
            f"DSCR: {dscr:.2f}x (banks want >1.25x for investment property loans)",
            f"1% Rule: Monthly rent should be ≥1% of purchase price. Current: {(rent/price*100):.2f}% {'✓' if rent/price >= 0.01 else '✗ Below 1% rule'}",
            "1031 Exchange: Defer capital gains by rolling profits into next property (hold 24 months before exchange)",
            "Depreciation: Deduct building value (not land) over 27.5 years — significant paper loss benefit",
            "Cost Segregation Study: Accelerate depreciation on components (electrical, plumbing, HVAC) to Years 5–15",
        ]

        return RealEstateAnalysis(
            property_address=address,
            purchase_price=price,
            monthly_rent=rent,
            cap_rate=cap_rate,
            cash_on_cash_return=coc_return,
            gross_rent_multiplier=grm,
            irr_estimate=irr,
            annual_cash_flow=annual_cash_flow,
            recommendation=recommendation,
            notes=notes,
        )

    def _simple_irr(self, cash_flows: List[float]) -> float:
        """Estimate IRR using Newton's method."""
        rate = 0.10
        for _ in range(50):
            npv = sum(cf / (1 + rate) ** t for t, cf in enumerate(cash_flows))
            dnpv = sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cash_flows))
            if abs(dnpv) < 1e-10:
                break
            rate -= npv / dnpv
            if rate <= -1:
                return -0.99
        return max(-0.99, min(rate, 5.0))

    # ─────────────────────────────────────────────────────────────────────────
    # TAX-LOSS HARVESTING
    # ─────────────────────────────────────────────────────────────────────────

    def tax_loss_harvesting(self, portfolio: dict) -> TaxLossStrategy:
        """
        Identify tax-loss harvesting opportunities and optimize asset location.

        Args:
            portfolio: dict with positions (list of {name, ticker, cost_basis, current_value,
                      account_type, acquisition_date}), marginal_tax_rate, state

        Returns:
            TaxLossStrategy with opportunities and asset location recommendations
        """
        positions = portfolio.get("positions", [])
        marginal_rate = portfolio.get("marginal_tax_rate", 0.32)
        state_rate = portfolio.get("state_tax_rate", 0.05)

        opportunities = []
        total_losses = 0.0
        wash_sale_warnings = []

        for pos in positions:
            cost = pos.get("cost_basis", 0)
            current = pos.get("current_value", 0)
            account = pos.get("account_type", "taxable")
            ticker = pos.get("ticker", "")
            name = pos.get("name", "Unknown")

            if account != "taxable":
                continue  # TLH only in taxable accounts

            loss = current - cost
            if loss < -500:  # Harvest losses > $500
                # Suggest replacement funds to avoid wash sale (30-day rule)
                replacement = self._suggest_replacement(ticker, name)
                opportunities.append({
                    "sell": f"{name} ({ticker})",
                    "loss": abs(loss),
                    "replacement": replacement,
                    "tax_savings": abs(loss) * (marginal_rate + state_rate),
                })
                total_losses += abs(loss)
                wash_sale_warnings.append(
                    f"Do NOT repurchase {ticker} within 30 days before or after sale (IRS wash sale rule §1091)"
                )

        estimated_savings = total_losses * (marginal_rate + state_rate)

        asset_location = [
            "Tax-Advantaged (401k/IRA/HSA): Bonds, REITs, high-dividend stocks, international funds (foreign tax credit lost in IRA)",
            "Taxable Brokerage: Total market index ETFs (VTI/VXUS) — buy-and-hold, low turnover, qualified dividends",
            "Roth IRA: Highest expected return assets (small-cap value, emerging markets) — grows tax-free forever",
            "Avoid in Taxable: High-yield bonds (taxed as ordinary income), REIT ETFs (non-qualified dividends), active funds with high turnover",
        ]

        action_items = [
            "Review portfolio in October/November for TLH opportunities before year-end",
            "Replace harvested positions immediately with similar-but-not-identical funds",
            "Track wash sale 31-day window carefully — automates in most brokerages",
            "Net capital losses offset gains; up to $3,000 of excess losses deduct against ordinary income",
            "Carry forward remaining losses to future years (no expiration)",
            "Consider donating appreciated assets to charity instead of selling (avoid capital gains + get deduction)",
        ]

        return TaxLossStrategy(
            opportunities=opportunities,
            estimated_tax_savings=estimated_savings,
            wash_sale_warnings=wash_sale_warnings,
            asset_location_recommendations=asset_location,
            action_items=action_items,
        )

    def _suggest_replacement(self, ticker: str, name: str) -> str:
        """Suggest a replacement fund that is similar but not substantially identical."""
        replacements = {
            "VTI": "SCHB (Schwab US Broad Market) or ITOT (iShares Core S&P Total US)",
            "VXUS": "IXUS (iShares Core MSCI Total Intl) or SPDW (SPDR Portfolio Dev World)",
            "BND": "AGG (iShares Core US Aggregate Bond) or SCHZ (Schwab US Aggregate Bond)",
            "QQQ": "QQQM or VGT (Vanguard IT Sector)",
            "SPY": "IVV (iShares Core S&P 500) or VOO (Vanguard S&P 500)",
            "VNQ": "IYR (iShares Real Estate) or SCHH (Schwab US REIT)",
        }
        for key, replacement in replacements.items():
            if key in ticker.upper():
                return replacement
        return f"Find a similar fund to {name} — avoid funds tracking the same index"

    # ─────────────────────────────────────────────────────────────────────────
    # CRYPTOCURRENCY STRATEGY
    # ─────────────────────────────────────────────────────────────────────────

    def cryptocurrency_strategy(self, facts: dict) -> CryptoStrategy:
        """
        Cryptocurrency portfolio strategy with tax and security guidance.

        Args:
            facts: dict with portfolio_value, risk_tolerance, time_horizon_years,
                   existing_crypto_pct, purpose ('speculation'/'store_of_value'/'defi')

        Returns:
            CryptoStrategy with allocation, tax treatment, and security guidance
        """
        portfolio_value = facts.get("portfolio_value", 100000)
        risk = facts.get("risk_tolerance", "moderate")
        purpose = facts.get("purpose", "store_of_value")

        # Allocation guidance
        if risk == "conservative":
            crypto_pct = 1.0
            btc_pct = 0.8
            eth_pct = 0.2
            alt_pct = 0.0
        elif risk == "moderate":
            crypto_pct = 3.0
            btc_pct = 0.6
            eth_pct = 0.3
            alt_pct = 0.1
        elif risk == "aggressive":
            crypto_pct = 7.0
            btc_pct = 0.5
            eth_pct = 0.3
            alt_pct = 0.2
        else:
            crypto_pct = 5.0
            btc_pct = 0.55
            eth_pct = 0.30
            alt_pct = 0.15

        recommended_assets = [
            {
                "name": "Bitcoin",
                "ticker": "BTC",
                "allocation": round(crypto_pct * btc_pct, 1),
                "rationale": "Digital gold — store of value, 21M supply cap, most liquid, institutional adoption",
            },
            {
                "name": "Ethereum",
                "ticker": "ETH",
                "allocation": round(crypto_pct * eth_pct, 1),
                "rationale": "Programmable blockchain — DeFi, NFT, smart contract backbone, proof-of-stake",
            },
        ]
        if alt_pct > 0:
            recommended_assets.append({
                "name": "Diversified Altcoins (Solana, Chainlink, Polygon)",
                "ticker": "Various",
                "allocation": round(crypto_pct * alt_pct, 1),
                "rationale": "Higher risk/reward — speculative allocation for aggressive investors only",
            })

        tax_treatment = [
            "IRS treats cryptocurrency as PROPERTY (IRS Notice 2014-21) — not currency",
            "Every crypto transaction is a taxable event: sale, trade, payment for goods/services",
            "Short-term capital gains (<12 months): taxed as ordinary income (up to 37%)",
            "Long-term capital gains (>12 months): taxed at 0%, 15%, or 20% depending on income",
            "Crypto-to-crypto trade: Taxable event — record FMV on date of exchange",
            "Staking rewards: Taxable as ordinary income at FMV on date received (Rev. Rul. 2023-14)",
            "DeFi: Each yield farming transaction may be taxable; complex — consult a crypto-specific CPA",
            "FBAR/FATCA: Foreign crypto exchanges may trigger reporting (still unclear — consult tax attorney)",
            "Use Koinly, TaxBit, or CoinTracker to automatically calculate gains/losses across all wallets",
        ]

        security = [
            "Hardware wallet (cold storage): Ledger Nano X or Trezor Model T — not connected to internet",
            "NEVER store crypto on exchange for long-term holdings — 'Not your keys, not your coins'",
            "Seed phrase: Write on metal (Cryptosteel), store in fireproof safe — NEVER digital/cloud",
            "Multi-signature wallet for large holdings (requires multiple keys to authorize transaction)",
            "Use separate email for crypto exchanges — not your primary email",
            "Enable 2FA with Authenticator app (not SMS) — SIM swap attacks are common",
            "Beware of phishing: MetaMask and Ledger will NEVER ask for your seed phrase",
        ]

        risk_warnings = [
            "Crypto is highly speculative — prices can drop 80–90% from peak (BTC dropped 84% in 2018, 77% in 2022)",
            "Only invest what you can afford to lose completely",
            f"${portfolio_value * crypto_pct / 100:,.0f} ({crypto_pct}%) maximum recommended crypto allocation for your risk profile",
            "Regulatory risk: SEC enforcement, potential bans, reporting requirements evolving",
            "DeFi smart contract risk: Code bugs, hacks, rug pulls — DYOR before any DeFi protocol",
            "Tax complexity: Most crypto investors underreport — ensure full compliance to avoid penalties",
        ]

        return CryptoStrategy(
            allocation_pct=crypto_pct,
            recommended_assets=recommended_assets,
            tax_treatment_notes=tax_treatment,
            security_recommendations=security,
            risk_warnings=risk_warnings,
        )
