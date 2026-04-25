"""
Debt Elimination Engine — Master debt strategy, negotiation, bankruptcy analysis,
and student loan optimization. Path to financial freedom from any debt situation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import math


@dataclass
class DebtAnalysis:
    """Complete analysis of a debt situation."""
    total_debt: float
    weighted_average_rate: float
    minimum_monthly_payment: float
    payoff_months_minimum_only: int
    total_interest_minimum_only: float
    debts_sorted_avalanche: List[Dict[str, Any]]
    debts_sorted_snowball: List[Dict[str, Any]]
    summary: str

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 70 + "╗",
            "║  DEBT ANALYSIS REPORT" + " " * 48 + "║",
            "╚" + "═" * 70 + "╝",
            "",
            f"  Total Debt:               ${self.total_debt:,.0f}",
            f"  Weighted Avg Interest:    {self.weighted_average_rate*100:.2f}%",
            f"  Minimum Monthly Payment:  ${self.minimum_monthly_payment:,.0f}",
            f"  Payoff (minimums only):   {self.payoff_months_minimum_only} months ({self.payoff_months_minimum_only/12:.1f} years)",
            f"  Total Interest (minimums): ${self.total_interest_minimum_only:,.0f}",
            "",
            "  DEBT INVENTORY (Avalanche Order — Highest Interest First):",
            f"  {'CREDITOR':<25} {'BALANCE':>10} {'RATE':>7} {'MIN PMT':>9}",
            "  " + "─" * 55,
        ]
        for d in self.debts_sorted_avalanche:
            lines.append(
                f"  {d.get('name', ''):<25} ${d.get('balance', 0):>9,.0f} "
                f"{d.get('rate', 0)*100:>6.1f}% ${d.get('min_payment', 0):>8,.0f}"
            )
        lines += ["", f"  ► {self.summary}"]
        return "\n".join(lines)


@dataclass
class DebtEliminationPlan:
    """Complete debt elimination plan with method comparison."""
    method: str
    payoff_schedule: List[Dict[str, Any]]
    total_months: int
    total_interest_paid: float
    interest_saved_vs_minimum: float
    extra_payment: float
    avalanche_vs_snowball: Dict[str, Any]
    motivation_milestones: List[str]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 70 + "╗",
            "║  DEBT ELIMINATION PLAN" + " " * 47 + "║",
            "╚" + "═" * 70 + "╝",
            "",
            f"  Method:                   {self.method}",
            f"  Extra Monthly Payment:    ${self.extra_payment:,.0f}",
            f"  Payoff Timeline:          {self.total_months} months ({self.total_months/12:.1f} years)",
            f"  Total Interest to Pay:    ${self.total_interest_paid:,.0f}",
            f"  Interest Saved:           ${self.interest_saved_vs_minimum:,.0f}",
            "",
            "  PAYOFF SCHEDULE:",
            f"  {'DEBT':<25} {'BALANCE':>10} {'PAYOFF MONTH':>13} {'TOTAL INTEREST':>15}",
            "  " + "─" * 67,
        ]
        for item in self.payoff_schedule:
            lines.append(
                f"  {item.get('name', ''):<25} ${item.get('balance', 0):>9,.0f} "
                f"Month {item.get('payoff_month', 0):>6}       ${item.get('interest_paid', 0):>13,.0f}"
            )
        lines += [
            "",
            "  AVALANCHE vs SNOWBALL COMPARISON:",
            f"  Avalanche (highest rate first): Saves ${self.avalanche_vs_snowball.get('avalanche_interest_savings', 0):,.0f} in interest",
            f"  Snowball (smallest balance first): Provides early wins — better for motivation",
            f"  Recommended: {self.avalanche_vs_snowball.get('recommendation', '')}",
            "",
            "  MILESTONES:",
        ]
        for milestone in self.motivation_milestones:
            lines.append(f"  🎯 {milestone}")
        return "\n".join(lines)


@dataclass
class NegotiationStrategy:
    """Debt negotiation strategy for each debt type."""
    scripts: List[Dict[str, str]]
    settlement_approach: List[str]
    medical_debt_strategy: List[str]
    legal_rights: List[str]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 70 + "╗",
            "║  DEBT NEGOTIATION STRATEGY" + " " * 43 + "║",
            "╚" + "═" * 70 + "╝",
            "",
            "  NEGOTIATION SCRIPTS:",
        ]
        for script in self.scripts:
            lines.append(f"\n  ═══ {script.get('type', '')} ═══")
            lines.append(f'  "{script.get("script", "")}"')
        lines += ["", "  SETTLEMENT PROCESS:"]
        for step in self.settlement_approach:
            lines.append(f"  {step}")
        lines += ["", "  MEDICAL DEBT NEGOTIATION:"]
        for item in self.medical_debt_strategy:
            lines.append(f"  • {item}")
        lines += ["", "  YOUR LEGAL RIGHTS:"]
        for right in self.legal_rights:
            lines.append(f"  ⚖ {right}")
        return "\n".join(lines)


@dataclass
class BankruptcyAnalysis:
    """Bankruptcy analysis and alternatives."""
    recommended_chapter: str
    means_test_result: str
    discharge_timeline: str
    dischargeable_debts: List[str]
    non_dischargeable_debts: List[str]
    exemptions: List[str]
    alternatives: List[str]
    life_after_bankruptcy: List[str]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 70 + "╗",
            "║  BANKRUPTCY ANALYSIS" + " " * 49 + "║",
            "╚" + "═" * 70 + "╝",
            "",
            f"  Recommended Chapter:      {self.recommended_chapter}",
            f"  Means Test Result:        {self.means_test_result}",
            f"  Discharge Timeline:       {self.discharge_timeline}",
            "",
            "  DISCHARGEABLE DEBTS (Can Be Eliminated):",
        ]
        for d in self.dischargeable_debts:
            lines.append(f"  ✓ {d}")
        lines += ["", "  NON-DISCHARGEABLE DEBTS (SURVIVE Bankruptcy):"]
        for d in self.non_dischargeable_debts:
            lines.append(f"  ✗ {d}")
        lines += ["", "  EXEMPTIONS (Property You Keep):"]
        for e in self.exemptions:
            lines.append(f"  → {e}")
        lines += ["", "  ALTERNATIVES TO BANKRUPTCY:"]
        for alt in self.alternatives:
            lines.append(f"  • {alt}")
        lines += ["", "  LIFE AFTER BANKRUPTCY (Credit Rebuilding):"]
        for step in self.life_after_bankruptcy:
            lines.append(f"  {step}")
        return "\n".join(lines)


@dataclass
class StudentLoanStrategy:
    """Comprehensive student loan repayment strategy."""
    total_loan_balance: float
    recommended_plan: str
    monthly_payment: float
    forgiveness_timeline_years: Optional[int]
    total_paid_estimate: float
    refinancing_recommendation: str
    strategies: List[str]
    idr_comparison: List[Dict[str, Any]]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 70 + "╗",
            "║  STUDENT LOAN STRATEGY" + " " * 47 + "║",
            "╚" + "═" * 70 + "╝",
            "",
            f"  Total Balance:            ${self.total_loan_balance:,.0f}",
            f"  Recommended Plan:         {self.recommended_plan}",
            f"  Monthly Payment:          ${self.monthly_payment:,.0f}",
            f"  Forgiveness Timeline:     {f'{self.forgiveness_timeline_years} years' if self.forgiveness_timeline_years else 'N/A'}",
            f"  Total Paid Estimate:      ${self.total_paid_estimate:,.0f}",
            "",
            f"  Refinancing: {self.refinancing_recommendation}",
            "",
            "  IDR PLAN COMPARISON:",
            f"  {'PLAN':<12} {'PAYMENT %':>12} {'TERM':>10} {'FORGIVENESS':>15}",
            "  " + "─" * 52,
        ]
        for plan in self.idr_comparison:
            lines.append(
                f"  {plan.get('plan', ''):<12} {plan.get('payment_pct', ''):>12} "
                f"{plan.get('term', ''):>10} {plan.get('forgiveness', ''):>15}"
            )
        lines += ["", "  STRATEGIES:"]
        for s in self.strategies:
            lines.append(f"  → {s}")
        return "\n".join(lines)


class DebtEliminationEngine:
    """
    Master debt strategy, negotiation, bankruptcy analysis, and student loan optimization.

    Covers all debt types: credit cards, medical, student loans, mortgages, auto loans,
    and personal loans. Provides mathematical optimization plus psychological strategies.

    Example:
        engine = DebtEliminationEngine()
        debts = [{"name": "Chase Visa", "balance": 8000, "rate": 0.24, "min_payment": 200}]
        analysis = engine.analyze_debt_situation(debts)
        plan = engine.elimination_strategy(debts, income=5000)
    """

    def analyze_debt_situation(self, debts: List[dict]) -> DebtAnalysis:
        """
        Comprehensive analysis of all debts with payoff projections.

        Args:
            debts: List of dicts with name, balance, rate (decimal), min_payment, type

        Returns:
            DebtAnalysis with complete picture
        """
        if not debts:
            return DebtAnalysis(
                total_debt=0, weighted_average_rate=0, minimum_monthly_payment=0,
                payoff_months_minimum_only=0, total_interest_minimum_only=0,
                debts_sorted_avalanche=[], debts_sorted_snowball=[],
                summary="No debts — congratulations! Focus on building wealth.",
            )

        total_debt = sum(d.get("balance", 0) for d in debts)
        total_min = sum(d.get("min_payment", 0) for d in debts)

        # Weighted average rate
        weighted_rate = (
            sum(d.get("balance", 0) * d.get("rate", 0) for d in debts) / total_debt
            if total_debt > 0 else 0
        )

        # Avalanche (highest rate first)
        avalanche = sorted(debts, key=lambda x: x.get("rate", 0), reverse=True)
        # Snowball (lowest balance first)
        snowball = sorted(debts, key=lambda x: x.get("balance", 0))

        # Estimate payoff months with minimum payments only
        payoff_months, total_interest = self._estimate_payoff(debts, 0)

        if total_debt < 10000:
            summary = "Manageable debt level — aggressive payoff achievable within 24 months with focused effort"
        elif total_debt < 50000:
            summary = "Moderate debt load — avalanche method with extra $200–$500/month can eliminate in 3–5 years"
        else:
            summary = "High debt load — consider debt negotiation, balance transfers, or income increase alongside payoff strategy"

        return DebtAnalysis(
            total_debt=total_debt,
            weighted_average_rate=weighted_rate,
            minimum_monthly_payment=total_min,
            payoff_months_minimum_only=payoff_months,
            total_interest_minimum_only=total_interest,
            debts_sorted_avalanche=avalanche,
            debts_sorted_snowball=snowball,
            summary=summary,
        )

    def _estimate_payoff(self, debts: List[dict], extra_payment: float) -> tuple:
        """Simulate debt payoff and return (months, total_interest)."""
        balances = {i: d.get("balance", 0) for i, d in enumerate(debts)}
        rates = {i: d.get("rate", 0) / 12 for i, d in enumerate(debts)}
        min_pmts = {i: d.get("min_payment", 0) for i, d in enumerate(debts)}

        total_interest = 0.0
        months = 0
        max_months = 600  # 50 years cap

        while any(b > 0 for b in balances.values()) and months < max_months:
            months += 1
            available_extra = extra_payment

            for i in balances:
                if balances[i] <= 0:
                    continue
                interest = balances[i] * rates[i]
                total_interest += interest
                payment = min(min_pmts[i], balances[i] + interest)
                balances[i] = balances[i] + interest - payment

            # Apply extra to highest rate remaining
            for i in sorted(balances, key=lambda x: rates[x], reverse=True):
                if balances[i] > 0 and available_extra > 0:
                    applied = min(available_extra, balances[i])
                    balances[i] -= applied
                    available_extra -= applied

        return months, round(total_interest, 2)

    def elimination_strategy(self, debts: List[dict], income: float) -> DebtEliminationPlan:
        """
        Create optimal debt elimination plan with method comparison.

        Args:
            debts: List of debt dicts
            income: Monthly take-home income

        Returns:
            DebtEliminationPlan with schedule and method comparison
        """
        total_min = sum(d.get("min_payment", 0) for d in debts)
        total_debt = sum(d.get("balance", 0) for d in debts)

        # Recommend extra payment (target 20–25% of income to debt)
        debt_budget = income * 0.25
        extra_payment = max(0, debt_budget - total_min)

        # Avalanche method
        avalanche_debts = sorted(debts, key=lambda x: x.get("rate", 0), reverse=True)
        avalanche_months, avalanche_interest = self._estimate_payoff(avalanche_debts, extra_payment)

        # Snowball method
        snowball_debts = sorted(debts, key=lambda x: x.get("balance", 0))
        snowball_months, snowball_interest = self._estimate_payoff(snowball_debts, extra_payment)

        # Minimum only
        min_months, min_interest = self._estimate_payoff(debts, 0)

        interest_saved = min_interest - avalanche_interest

        # Choose method
        if avalanche_interest < snowball_interest * 0.85:
            method = "Debt Avalanche (Mathematically Optimal)"
            schedule = self._build_payoff_schedule(avalanche_debts, extra_payment)
            total_months = avalanche_months
            total_interest = avalanche_interest
        else:
            method = "Hybrid (Avalanche with Snowball wins for motivation)"
            schedule = self._build_payoff_schedule(snowball_debts, extra_payment)
            total_months = snowball_months
            total_interest = snowball_interest

        milestones = []
        running = total_debt
        for item in schedule:
            running -= item.get("balance", 0)
            pct = (1 - running / total_debt) * 100 if total_debt > 0 else 0
            if item == schedule[0]:
                milestones.append(f"Month {item.get('payoff_month', 0)}: First debt GONE — {item.get('name', '')}! Roll payment to next debt.")
        milestones.append(f"Month {total_months}: DEBT FREE! Redirect ${total_min + extra_payment:,.0f}/month to investments")

        return DebtEliminationPlan(
            method=method,
            payoff_schedule=schedule,
            total_months=total_months,
            total_interest_paid=total_interest,
            interest_saved_vs_minimum=interest_saved,
            extra_payment=extra_payment,
            avalanche_vs_snowball={
                "avalanche_interest_savings": snowball_interest - avalanche_interest,
                "avalanche_months": avalanche_months,
                "snowball_months": snowball_months,
                "recommendation": (
                    "Avalanche saves more money; Snowball is better if you need motivation wins. "
                    "Either beats minimum payments dramatically."
                ),
            },
            motivation_milestones=milestones,
        )

    def _build_payoff_schedule(self, debts: List[dict], extra_payment: float) -> List[Dict[str, Any]]:
        """Build month-by-month payoff schedule for ordered debts."""
        balances = [d.get("balance", 0) for d in debts]
        rates = [d.get("rate", 0) / 12 for d in debts]
        min_pmts = [d.get("min_payment", 0) for d in debts]
        names = [d.get("name", f"Debt {i}") for i, d in enumerate(debts)]

        paid_off_month = [None] * len(debts)
        interest_paid = [0.0] * len(debts)

        month = 0
        max_months = 600

        while any(b > 0 for b in balances) and month < max_months:
            month += 1
            available_extra = extra_payment

            for i in range(len(balances)):
                if balances[i] <= 0:
                    continue
                interest = balances[i] * rates[i]
                interest_paid[i] += interest
                pmt = min(min_pmts[i], balances[i] + interest)
                balances[i] = balances[i] + interest - pmt

            # Apply extra to first non-zero balance
            for i in range(len(balances)):
                if balances[i] > 0 and available_extra > 0:
                    applied = min(available_extra, balances[i])
                    balances[i] -= applied
                    available_extra -= applied
                    break

            for i in range(len(balances)):
                if balances[i] <= 0 and paid_off_month[i] is None:
                    paid_off_month[i] = month
                    balances[i] = 0
                    # Add freed minimum payment to extra
                    extra_payment += min_pmts[i]

        schedule = []
        for i, d in enumerate(debts):
            schedule.append({
                "name": names[i],
                "balance": d.get("balance", 0),
                "payoff_month": paid_off_month[i] or month,
                "interest_paid": round(interest_paid[i], 2),
            })
        return schedule

    def debt_negotiation_guide(self, debts: List[dict]) -> NegotiationStrategy:
        """
        Negotiation strategy for each type of debt.

        Args:
            debts: List of debt dicts with type ('credit_card'/'medical'/'collection'/'student')

        Returns:
            NegotiationStrategy with scripts and settlement process
        """
        scripts = [
            {
                "type": "Credit Card Hardship Program",
                "script": (
                    "Hello, I'm calling because I'm experiencing financial hardship and I want to find "
                    "a solution before missing any payments. Can you connect me with your hardship or "
                    "customer assistance department? I'd like to discuss a temporary interest rate reduction "
                    "or modified payment plan."
                ),
            },
            {
                "type": "Settlement Offer (40–60 cents on dollar)",
                "script": (
                    "I'm calling about account ending in [XXXX]. I've been unable to pay this balance "
                    "due to [hardship reason]. I'd like to discuss a settlement. I can offer a lump sum "
                    "of $[AMOUNT] to resolve this account in full. Can you authorize that settlement today? "
                    "I would need written confirmation before making payment."
                ),
            },
            {
                "type": "Collection Agency Validation",
                "script": (
                    "I am writing to demand validation of this debt per my rights under 15 U.S.C. §1692g "
                    "(FDCPA). Please cease all collection activity until you provide: (1) amount owed, "
                    "(2) name and address of original creditor, (3) copy of original signed agreement, "
                    "(4) proof you are licensed to collect in my state."
                ),
            },
        ]

        settlement_approach = [
            "Step 1: Wait until account is 90–180 days delinquent (creditors more flexible then)",
            "Step 2: Save lump sum — creditors rarely accept payment plans for settlements",
            "Step 3: Start at 25 cents on the dollar; expect to settle at 40–60%",
            "Step 4: ALWAYS get settlement offer in writing BEFORE making payment",
            "Step 5: Specify 'Paid in Full' (not 'Settled') if possible — better for credit report",
            "Step 6: Beware of tax consequences — forgiven debt >$600 = IRS Form 1099-C (taxable income unless insolvent)",
            "Step 7: Check insolvency exception (Form 982) — if liabilities exceed assets, forgiven debt may not be taxable",
        ]

        medical_debt = [
            "Hospital charity care: Most nonprofit hospitals required to offer — ask BEFORE paying anything",
            "Offer 10–30 cents on the dollar — hospitals routinely accept",
            "Medical debt <$500 no longer on credit reports (CFPB rule 2022)",
            "Medical debt removed from credit reports after 1 year (changed 2023)",
            "Sample opening offer: 'I'd like to pay $[20% of bill]. Is there a financial counselor I can speak with?'",
            "Get itemized bill: 80% of medical bills contain errors — dispute anything incorrect",
            "SURPRISE BILLING ACT: Protects from out-of-network surprise bills for emergency services",
            "Contact your state insurance commissioner if insurer wrongly denies a claim",
        ]

        legal_rights = [
            "FDCPA: Collectors cannot call before 8am or after 9pm, cannot threaten violence, cannot use profanity",
            "Cease communication: Send written request and collector MUST stop (except to confirm no further contact)",
            "Statute of limitations: After SOL expires, debt is 'time-barred' — collector cannot sue (but can still try to collect)",
            "NEVER make payment on time-barred debt without understanding it may restart SOL",
            "Zombie debt: Old debt collectors buy and try to collect — verify SOL before any acknowledgment",
            "File complaint with FTC and CFPB for FDCPA violations — statutory damages up to $1,000 + attorney fees",
        ]

        return NegotiationStrategy(
            scripts=scripts,
            settlement_approach=settlement_approach,
            medical_debt_strategy=medical_debt,
            legal_rights=legal_rights,
        )

    def bankruptcy_analysis(self, facts: dict) -> BankruptcyAnalysis:
        """
        Analyze bankruptcy options and alternatives.

        Args:
            facts: dict with monthly_income, state, total_debt, debt_types,
                   assets (dict), dependents, has_steady_income

        Returns:
            BankruptcyAnalysis with chapter recommendation and exemptions
        """
        income = facts.get("monthly_income", 0)
        annual_income = income * 12
        state = facts.get("state", "CA")
        total_debt = facts.get("total_debt", 0)
        debt_types = facts.get("debt_types", ["credit_card"])
        has_income = facts.get("has_steady_income", True)

        # Chapter 7 means test: compare to state median income
        # Simplified median income thresholds (2024 approximate)
        state_median = {
            "CA": 75000, "TX": 60000, "FL": 58000, "NY": 68000, "IL": 65000,
            "PA": 62000, "OH": 58000, "GA": 58000, "NC": 57000, "MI": 60000,
        }.get(state, 62000)

        if annual_income <= state_median:
            recommended = "Chapter 7 (Liquidation)"
            means_test = f"QUALIFIES — Income ${annual_income:,.0f} below state median ${state_median:,.0f}"
            timeline = "3–6 months from filing to discharge"
        elif not has_income:
            recommended = "Chapter 7 (No means test issue with no income)"
            means_test = "Qualifies — no regular income, means test passed"
            timeline = "3–6 months from filing to discharge"
        else:
            recommended = "Chapter 13 (Reorganization)"
            means_test = f"Chapter 7 FAILS — Income ${annual_income:,.0f} above state median. Chapter 13 allows repayment plan."
            timeline = "3–5 year repayment plan then discharge"

        dischargeable = [
            "Credit card debt",
            "Medical bills",
            "Personal loans",
            "Utility bills",
            "Most lease obligations",
            "Civil court judgments (some)",
            "Business debts",
        ]

        non_dischargeable = [
            "Student loans (extremely rare exception — 'undue hardship' standard, very difficult)",
            "Child support and alimony (NEVER dischargeable)",
            "Most tax debts (taxes <3 years old; exceptions for older taxes)",
            "Debts from fraud or false pretenses",
            "DUI death/injury judgments",
            "Criminal fines and restitution",
            "Homeowner association fees (post-petition)",
        ]

        # Exemptions (federal exemptions — states vary)
        exemptions = [
            f"Homestead: Varies dramatically by state — TX and FL: UNLIMITED; CA: $600K–$678K; federal: $27,900",
            "Vehicle: Up to $4,450 (federal) or state equivalent",
            "Retirement accounts: 401(k), IRA — FULLY protected in federal and most states (ERISA + Bankruptcy Code §522)",
            "Household goods: Up to $14,875 total (federal)",
            "Tools of trade: Up to $2,800 (federal)",
            "Life insurance cash value: Varies by state",
            "Wildcard exemption (federal): $1,475 + $14,050 of unused homestead exemption",
        ]

        alternatives = [
            "Debt management plan (DMP) via NFCC-member nonprofit credit counselor — lower rates, 3–5 year payoff",
            "Debt settlement — settle for 40–60 cents on dollar (damages credit but avoids bankruptcy)",
            "Negotiate with creditors directly — hardship programs, lower rates",
            "Sell assets to pay down debt",
            "Increase income: side income, overtime, second job",
            "Balance transfer (0% APR for 12–21 months on credit card debt)",
            "Personal loan consolidation at lower rate",
        ]

        life_after = [
            "Year 1: Chapter 7 stays on credit report 10 years; Chapter 13 stays 7 years",
            "Month 1: Get secured credit card immediately (Capital One Secured, Discover Secured)",
            "Month 6: Credit score often rebounds to 600–640 within 12–24 months",
            "Year 1–2: Become authorized user on spouse/family member's good-standing account",
            "Year 2: Apply for credit builder loan at credit union",
            "Year 3+: Can qualify for FHA mortgage (2 years after Chapter 7; 1 year into Chapter 13 with court approval)",
            "Year 7–10: Bankruptcy falls off credit report — fresh start",
        ]

        return BankruptcyAnalysis(
            recommended_chapter=recommended,
            means_test_result=means_test,
            discharge_timeline=timeline,
            dischargeable_debts=dischargeable,
            non_dischargeable_debts=non_dischargeable,
            exemptions=exemptions,
            alternatives=alternatives,
            life_after_bankruptcy=life_after,
        )

    def student_loan_mastery(self, loans: List[dict]) -> StudentLoanStrategy:
        """
        Comprehensive student loan strategy with IDR comparison and forgiveness analysis.

        Args:
            loans: List of dicts with loan_type ('federal'/'private'), balance,
                   interest_rate, servicer, loan_type_specific ('subsidized'/'unsubsidized'/'PLUS')
            Include facts dict fields: income, family_size, filing_status, employer_type,
                                        state, career ('public_service'/'private')

        Returns:
            StudentLoanStrategy with optimal repayment plan
        """
        total_balance = sum(l.get("balance", 0) for l in loans)
        income = loans[0].get("income", 50000) if loans else 50000
        family_size = loans[0].get("family_size", 1) if loans else 1
        employer = loans[0].get("employer_type", "private") if loans else "private"
        career = loans[0].get("career", "private") if loans else "private"

        # Poverty guideline 2024 (continental US)
        poverty_line = 15060 + (4720 * (family_size - 1))

        # SAVE plan: 5% of discretionary income (income - 225% of poverty line) for undergrad
        discretionary_save = max(0, income - poverty_line * 2.25)
        save_payment = round(discretionary_save * 0.05 / 12, 2)

        # PAYE plan: 10% of discretionary income (income - 150% of poverty line)
        discretionary_paye = max(0, income - poverty_line * 1.50)
        paye_payment = round(discretionary_paye * 0.10 / 12, 2)

        # IBR plan: 10–15% of discretionary income
        ibr_payment = round(discretionary_paye * 0.10 / 12, 2)

        # ICR: 20% of discretionary income or 12-year fixed payment, whichever is less
        icr_payment = round(discretionary_paye * 0.20 / 12, 2)

        # Standard 10-year
        avg_rate = sum(l.get("interest_rate", 0.065) for l in loans) / len(loans) if loans else 0.065
        monthly_rate = avg_rate / 12
        if monthly_rate > 0:
            standard_payment = round(
                total_balance * monthly_rate * (1 + monthly_rate) ** 120 / ((1 + monthly_rate) ** 120 - 1), 2
            )
        else:
            standard_payment = round(total_balance / 120, 2)

        idr_comparison = [
            {"plan": "SAVE", "payment_pct": "5% discret.", "term": "20–25 yrs", "forgiveness": "Yes (tax-free)"},
            {"plan": "PAYE", "payment_pct": "10% discret.", "term": "20 yrs", "forgiveness": "Yes (taxable)"},
            {"plan": "IBR (new)", "payment_pct": "10% discret.", "term": "20 yrs", "forgiveness": "Yes (taxable)"},
            {"plan": "IBR (old)", "payment_pct": "15% discret.", "term": "25 yrs", "forgiveness": "Yes (taxable)"},
            {"plan": "ICR", "payment_pct": "20% discret.", "term": "25 yrs", "forgiveness": "Yes (taxable)"},
            {"plan": "Standard", "payment_pct": "Fixed payment", "term": "10 yrs", "forgiveness": "No"},
        ]

        # Choose recommended plan
        if employer == "government" or career == "public_service":
            recommended = "PSLF (Public Service Loan Forgiveness) + SAVE plan"
            forgiveness_years = 10
            monthly_pmt = save_payment
            total_paid = save_payment * 120
            refi_rec = "DO NOT refinance to private — lose PSLF eligibility. Federal loans only for PSLF."
        elif total_balance > income * 1.5:
            recommended = "SAVE plan — loan forgiveness after 20–25 years"
            forgiveness_years = 20 if any(l.get("loan_type_specific") == "undergrad" for l in loans) else 25
            monthly_pmt = save_payment
            total_paid = save_payment * forgiveness_years * 12
            refi_rec = "Do NOT refinance if pursuing IDR forgiveness — lose federal protections."
        else:
            recommended = "Standard 10-year repayment (or refinance if rate >6%)"
            forgiveness_years = None
            monthly_pmt = standard_payment
            total_paid = standard_payment * 120
            refi_rec = f"Refinance if credit score 720+ — could get 4.5–5.5% vs current {avg_rate*100:.1f}%"

        strategies = [
            "PSLF: 120 qualifying payments while working full-time for government/nonprofit → 100% forgiveness tax-free",
            "SAVE plan: Best IDR for most borrowers — 5% for undergrad, caps interest from growing",
            "Teacher Loan Forgiveness: Up to $17,500 after 5 years teaching in low-income school",
            "Borrower Defense to Repayment: Full discharge if school misled you about programs/employment",
            "Closed School Discharge: If school closed while enrolled or within 120 days of closure",
            "Disability Discharge: TPD discharge if permanently disabled — now automatic for SSA recipients",
            "Administrative Discharge: HERO Act waivers, bankruptcy discharge (rare but exists)",
            f"PSLF tip: Certify employment annually — don't wait 10 years to discover a problem",
            "Refinancing: ONLY consider for private loan holders or those not pursuing forgiveness",
            f"Income certification: Recertify IDR every year — use IRS Data Retrieval Tool for accuracy",
        ]

        return StudentLoanStrategy(
            total_loan_balance=total_balance,
            recommended_plan=recommended,
            monthly_payment=monthly_pmt,
            forgiveness_timeline_years=forgiveness_years,
            total_paid_estimate=total_paid,
            refinancing_recommendation=refi_rec,
            strategies=strategies,
            idr_comparison=idr_comparison,
        )
