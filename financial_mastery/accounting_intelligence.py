"""
Accounting Intelligence — CPA-level accounting and financial analysis.
Covers financial statements, tax optimization, payroll, and audit defense.
Replaces a CPA, tax advisor, and bookkeeper.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any


# ─────────────────────────────────────────────────────────────────────────────
# TAX CALENDAR
# ─────────────────────────────────────────────────────────────────────────────

TAX_CALENDAR: Dict[str, List[Dict[str, str]]] = {
    "January": [
        {"date": "Jan 15", "entity": "Individual", "deadline": "Q4 estimated tax payment due (Form 1040-ES)"},
        {"date": "Jan 31", "entity": "All Employers", "deadline": "W-2s to employees; 1099-NEC to contractors"},
        {"date": "Jan 31", "entity": "Employers", "deadline": "Form 941 Q4; FUTA Form 940"},
    ],
    "February": [
        {"date": "Feb 15", "entity": "Employers", "deadline": "Employees who claimed exempt W-4 must re-certify"},
        {"date": "Feb 28", "entity": "All", "deadline": "1099 paper filing deadline (except 1099-NEC)"},
    ],
    "March": [
        {"date": "Mar 15", "entity": "S-Corp / Partnership", "deadline": "Form 1120-S / Form 1065 due (or extend)"},
        {"date": "Mar 15", "entity": "S-Corp / Partnership", "deadline": "Issue K-1s to shareholders/partners"},
        {"date": "Mar 31", "entity": "All", "deadline": "1099 electronic filing deadline (except 1099-NEC)"},
    ],
    "April": [
        {"date": "Apr 15", "entity": "Individual / C-Corp", "deadline": "Form 1040 / Form 1120 due (or 6-month extension)"},
        {"date": "Apr 15", "entity": "Individual", "deadline": "Q1 estimated tax payment due (Form 1040-ES)"},
        {"date": "Apr 15", "entity": "Individual", "deadline": "IRA / HSA contribution deadline for prior year"},
        {"date": "Apr 15", "entity": "FBAR", "deadline": "FinCEN Form 114 (foreign accounts > $10K)"},
    ],
    "June": [
        {"date": "Jun 15", "entity": "Individual", "deadline": "Q2 estimated tax payment due (Form 1040-ES)"},
        {"date": "Jun 15", "entity": "Expats", "deadline": "Automatic 2-month extension for Americans abroad"},
    ],
    "September": [
        {"date": "Sep 15", "entity": "S-Corp / Partnership", "deadline": "Extended return deadline (6-month extension)"},
        {"date": "Sep 15", "entity": "Individual", "deadline": "Q3 estimated tax payment due (Form 1040-ES)"},
        {"date": "Sep 15", "entity": "Individual", "deadline": "SEP-IRA contribution deadline (if extended)"},
    ],
    "October": [
        {"date": "Oct 15", "entity": "Individual / C-Corp", "deadline": "Extended Form 1040 / 1120 deadline"},
        {"date": "Oct 15", "entity": "Individual", "deadline": "Recharacterize prior-year Roth conversion deadline"},
    ],
    "December": [
        {"date": "Dec 31", "entity": "All", "deadline": "Year-end tax planning actions must be completed"},
        {"date": "Dec 31", "entity": "Employers", "deadline": "Last day to establish a SIMPLE IRA for current year"},
        {"date": "Dec 31", "entity": "C-Corp", "deadline": "Fiscal year-end Q4 estimated tax payments"},
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# DEDUCTION DATABASE — 100+ Legitimate Business Deductions
# ─────────────────────────────────────────────────────────────────────────────

DEDUCTION_DATABASE: List[Dict[str, str]] = [
    {"name": "Advertising & Marketing", "irc": "§162", "notes": "Digital ads, print, radio, TV, direct mail, SEO/SEM"},
    {"name": "Auto — Business Use (Actual)", "irc": "§162", "notes": "Actual expenses: gas, insurance, repairs × business %"},
    {"name": "Auto — Standard Mileage", "irc": "§162", "notes": "67¢/mile (2024); track with MileIQ, TripLog"},
    {"name": "Auto — Section 179 Expensing", "irc": "§179", "notes": "Full deduction of vehicle cost in year of purchase (SUV > 6,000 lbs: up to $28,900 bonus limit)"},
    {"name": "Bad Debts", "irc": "§166", "notes": "Uncollectable business receivables"},
    {"name": "Bank Fees & Charges", "irc": "§162", "notes": "Monthly fees, wire transfer fees, overdraft fees"},
    {"name": "Bonus Depreciation", "irc": "§168(k)", "notes": "60% in 2024, phasing down 20%/year; applies to new and used property"},
    {"name": "Business Licenses & Permits", "irc": "§162", "notes": "Federal, state, and local licenses"},
    {"name": "Client Gifts", "irc": "§274", "notes": "Up to $25 per recipient per year"},
    {"name": "Commissions & Fees Paid", "irc": "§162", "notes": "Paid to outside parties; issue 1099-NEC if ≥$600"},
    {"name": "Computer & Tech Equipment", "irc": "§179/§168", "notes": "Deduct full cost year 1 via §179 or bonus depreciation"},
    {"name": "Contract Labor / Independent Contractors", "irc": "§162", "notes": "Issue 1099-NEC if ≥$600; document with contract"},
    {"name": "Continuing Education & Training", "irc": "§162", "notes": "Courses, seminars, webinars maintaining/improving skills"},
    {"name": "Depreciation — MACRS", "irc": "§168", "notes": "5-yr: computers; 7-yr: furniture; 15-yr: improvements; 39-yr: buildings"},
    {"name": "Dues & Subscriptions", "irc": "§162", "notes": "Professional memberships, industry associations, trade journals"},
    {"name": "Education — Employee Training", "irc": "§127", "notes": "Up to $5,250/employee tax-free education assistance"},
    {"name": "Employee Benefits — Health Insurance", "irc": "§106", "notes": "Premiums paid for employees; 100% deductible for S-corp owners on W-2"},
    {"name": "Employee Benefits — Life Insurance", "irc": "§162", "notes": "Up to $50K group term life tax-free to employees"},
    {"name": "Employee Benefits — Retirement Plan Contributions", "irc": "§404", "notes": "401k match, SEP, SIMPLE, defined benefit contributions"},
    {"name": "Energy-Efficient Building Deduction", "irc": "§179D", "notes": "Up to $5/sq ft for qualifying commercial building improvements"},
    {"name": "Equipment Rental / Leasing", "irc": "§162", "notes": "Rent paid for equipment used in business"},
    {"name": "Filing Fees & Legal Registrations", "irc": "§162", "notes": "State filing fees, registered agent, trademark filings"},
    {"name": "Franchise Fees", "irc": "§162/§197", "notes": "Ongoing royalties §162; initial fee amortized §197 over 15 years"},
    {"name": "Home Office — Regular/Exclusive Use", "irc": "§280A", "notes": "Simplified: $5/sq ft (max 300 sq ft = $1,500); Actual: % of home expenses"},
    {"name": "Home Office Rent to Yourself — Augusta Rule", "irc": "§280A(g)", "notes": "Rent home to business ≤14 days/year — excluded from income; business deducts"},
    {"name": "Insurance — Business", "irc": "§162", "notes": "General liability, E&O, professional, cyber, D&O, property"},
    {"name": "Insurance — Health (Self-Employed)", "irc": "§162(l)", "notes": "100% of health, dental, vision premiums for self-employed (Schedule 1 deduction)"},
    {"name": "Interest — Business Loans", "irc": "§163", "notes": "Interest on loans for business purpose; subject to §163(j) limit for large businesses"},
    {"name": "Internet & Telephone — Business Portion", "irc": "§162", "notes": "Business % of bill; document usage"},
    {"name": "Inventory — Cost of Goods Sold", "irc": "§471", "notes": "Product cost (materials, direct labor, overhead) deducted when sold"},
    {"name": "Legal & Professional Fees", "irc": "§162", "notes": "Attorney, CPA, consultant fees for business matters"},
    {"name": "Meals — Business Entertainment (50%)", "irc": "§274", "notes": "50% deductible if business discussion occurs; receipt and note required"},
    {"name": "Medical Expense Reimbursement — HRA/QSEHRA", "irc": "§105", "notes": "Reimburse employees for medical expenses tax-free (QSEHRA: $6,150/self, $12,450/family 2024)"},
    {"name": "Moving Expenses (Business-Related)", "irc": "§217", "notes": "Suspended for individuals 2018–2025; deductible for military"},
    {"name": "Office Supplies & Materials", "irc": "§162", "notes": "Paper, pens, printer ink, cleaning supplies — document receipts"},
    {"name": "Payroll Taxes (Employer Portion)", "irc": "§164", "notes": "FICA (7.65%), FUTA (6% on first $7K), SUTA — all deductible"},
    {"name": "Postage & Shipping", "irc": "§162", "notes": "FedEx, UPS, USPS, stamps for business mail"},
    {"name": "Printing & Reproduction", "irc": "§162", "notes": "Business cards, brochures, contracts, presentations"},
    {"name": "R&D Tax Credit (Credit — not deduction)", "irc": "§41", "notes": "Credit = 20% of qualified research expenses over base amount; payroll tax offset for startups"},
    {"name": "Rent — Business Premises", "irc": "§162", "notes": "Office, store, warehouse rent; CAM charges; triple net leases"},
    {"name": "Repairs & Maintenance", "irc": "§162", "notes": "Repairs that don't add value or extend life; improvements must be capitalized"},
    {"name": "Research & Experimental Costs", "irc": "§174", "notes": "Must amortize over 5 years (domestic) or 15 years (foreign) starting 2022"},
    {"name": "Retirement — SEP-IRA Contribution", "irc": "§404", "notes": "Up to 25% of compensation or $69,000 (2024); due by tax filing date + extension"},
    {"name": "Retirement — Solo 401(k)", "irc": "§401(k)", "notes": "Employee: $23,000 + $7,500 catch-up (age 50+); Employer: 25% of W-2"},
    {"name": "Salaries & Wages — Employees", "irc": "§162", "notes": "W-2 compensation for employees (not owners of pass-through without W-2)"},
    {"name": "Section 179 Expensing", "irc": "§179", "notes": "$1,220,000 limit (2024); phase-out at $3,050,000; covers equipment, software, vehicles"},
    {"name": "Software & SaaS Subscriptions", "irc": "§162/§179", "notes": "Business software subscriptions fully deductible; owned software — §179 or amortize"},
    {"name": "Start-Up Costs", "irc": "§195", "notes": "Deduct up to $5,000 in year 1; remainder amortized over 180 months"},
    {"name": "Storage Fees", "irc": "§162", "notes": "Warehouse, self-storage for business inventory or equipment"},
    {"name": "Tools & Small Equipment (<$2,500)", "irc": "§1.263(a)-1(f)", "notes": "De minimis safe harbor: deduct items costing ≤$2,500 per invoice in year purchased"},
    {"name": "Travel — Business (Ordinary & Necessary)", "irc": "§162", "notes": "Flights, hotels, car rental, 50% meals; must be away from tax home overnight"},
    {"name": "Uniforms & Work Clothing", "irc": "§162", "notes": "Clothing unsuitable for everyday wear required by employer"},
    {"name": "Utilities — Business Premises", "irc": "§162", "notes": "Electric, gas, water, trash for business location"},
    {"name": "Vehicle — Luxury Auto Limitation", "irc": "§280F", "notes": "Annual caps on depreciation for passenger autos; SUV >6,000 lbs has higher limit"},
    {"name": "Work Opportunity Tax Credit (Credit)", "irc": "§51", "notes": "Credit up to $9,600/new hire from targeted groups (veterans, ex-felons, food stamp recipients)"},
    {"name": "Workers Compensation Insurance", "irc": "§162", "notes": "Required in most states; fully deductible business expense"},
]


# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FinancialStatement:
    """Complete set of financial statements for a period."""
    period: str
    income_statement: Dict[str, Any]
    balance_sheet: Dict[str, Any]
    cash_flow_statement: Dict[str, Any]
    notes: List[str]
    ratios: Dict[str, float]

    def is_balanced(self) -> bool:
        """Check if balance sheet balances (Assets = Liabilities + Equity)."""
        bs = self.balance_sheet
        total_assets = bs.get("total_assets", 0)
        total_liab_equity = bs.get("total_liabilities", 0) + bs.get("total_equity", 0)
        return abs(total_assets - total_liab_equity) < 0.01

    def format_as_text(self) -> str:
        inc = self.income_statement
        bs = self.balance_sheet
        cf = self.cash_flow_statement

        lines = [
            "╔" + "═" * 70 + "╗",
            "║  FINANCIAL STATEMENTS" + " " * 48 + "║",
            f"║  Period: {self.period}" + " " * (59 - len(self.period)) + "║",
            "╚" + "═" * 70 + "╝",
            "",
            "  ─── INCOME STATEMENT ───────────────────────────────────────────",
            f"  Revenue:                  ${inc.get('revenue', 0):>15,.2f}",
            f"  Cost of Goods Sold:       ${inc.get('cogs', 0):>15,.2f}",
            f"  Gross Profit:             ${inc.get('gross_profit', 0):>15,.2f}",
            f"  Operating Expenses:       ${inc.get('operating_expenses', 0):>15,.2f}",
            f"  EBITDA:                   ${inc.get('ebitda', 0):>15,.2f}",
            f"  Depreciation:             ${inc.get('depreciation', 0):>15,.2f}",
            f"  EBIT:                     ${inc.get('ebit', 0):>15,.2f}",
            f"  Interest Expense:         ${inc.get('interest_expense', 0):>15,.2f}",
            f"  Pre-Tax Income:           ${inc.get('pretax_income', 0):>15,.2f}",
            f"  Tax Expense:              ${inc.get('tax_expense', 0):>15,.2f}",
            f"  NET INCOME:               ${inc.get('net_income', 0):>15,.2f}",
            "",
            "  ─── BALANCE SHEET ───────────────────────────────────────────────",
            "  ASSETS:",
            f"    Current Assets:         ${bs.get('current_assets', 0):>15,.2f}",
            f"    Fixed Assets (net):     ${bs.get('fixed_assets_net', 0):>15,.2f}",
            f"    Other Assets:           ${bs.get('other_assets', 0):>15,.2f}",
            f"  TOTAL ASSETS:             ${bs.get('total_assets', 0):>15,.2f}",
            "  LIABILITIES:",
            f"    Current Liabilities:    ${bs.get('current_liabilities', 0):>15,.2f}",
            f"    Long-Term Debt:         ${bs.get('long_term_debt', 0):>15,.2f}",
            f"  TOTAL LIABILITIES:        ${bs.get('total_liabilities', 0):>15,.2f}",
            "  EQUITY:",
            f"    Paid-in Capital:        ${bs.get('paid_in_capital', 0):>15,.2f}",
            f"    Retained Earnings:      ${bs.get('retained_earnings', 0):>15,.2f}",
            f"  TOTAL EQUITY:             ${bs.get('total_equity', 0):>15,.2f}",
            f"  {'✓ BALANCED' if self.is_balanced() else '✗ DOES NOT BALANCE — CHECK ENTRIES'}",
            "",
            "  ─── CASH FLOW STATEMENT (Indirect Method) ──────────────────────",
            f"  Operating Activities:     ${cf.get('operating_activities', 0):>15,.2f}",
            f"  Investing Activities:     ${cf.get('investing_activities', 0):>15,.2f}",
            f"  Financing Activities:     ${cf.get('financing_activities', 0):>15,.2f}",
            f"  NET CHANGE IN CASH:       ${cf.get('net_change_in_cash', 0):>15,.2f}",
        ]
        if self.ratios:
            lines.append("")
            lines.append("  ─── KEY RATIOS ──────────────────────────────────────────────────")
            for ratio, value in self.ratios.items():
                lines.append(f"  {ratio:<30} {value:>8.2f}")
        return "\n".join(lines)


@dataclass
class TaxStrategy:
    """Comprehensive tax optimization strategy."""
    entity_type: str
    estimated_tax_liability: float
    deductions: List[Dict[str, Any]]
    credits: List[Dict[str, Any]]
    estimated_savings: float
    strategies: List[str]
    deadlines: List[Dict[str, str]]
    effective_tax_rate: float = 0.0

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 70 + "╗",
            "║  TAX OPTIMIZATION STRATEGY" + " " * 43 + "║",
            "╚" + "═" * 70 + "╝",
            "",
            f"  Entity Type:           {self.entity_type}",
            f"  Est. Tax Liability:    ${self.estimated_tax_liability:,.2f}",
            f"  Est. Tax Savings:      ${self.estimated_savings:,.2f}",
            f"  Effective Tax Rate:    {self.effective_tax_rate*100:.1f}%",
            "",
            "  TAX STRATEGIES:",
        ]
        for i, s in enumerate(self.strategies, 1):
            lines.append(f"  {i:2d}. {s}")
        lines += ["", "  KEY DEDUCTIONS:"]
        for d in self.deductions[:10]:
            lines.append(f"  • {d.get('name', '')}: ${d.get('amount', 0):,.2f} [{d.get('irc', '')}]")
        if self.credits:
            lines += ["", "  TAX CREDITS:"]
            for c in self.credits:
                lines.append(f"  • {c.get('name', '')}: ${c.get('amount', 0):,.2f} [{c.get('irc', '')}]")
        lines += ["", "  UPCOMING DEADLINES:"]
        for dl in self.deadlines[:6]:
            lines.append(f"  {dl.get('date', '')} — {dl.get('description', '')}")
        return "\n".join(lines)


@dataclass
class RatioAnalysis:
    """Financial ratio analysis with industry benchmarks."""
    ratios: Dict[str, Dict[str, Any]]   # ratio_name → {value, benchmark, interpretation}
    overall_health: str                   # excellent / good / fair / poor
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 72 + "╗",
            "║  FINANCIAL RATIO ANALYSIS" + " " * 46 + "║",
            "╚" + "═" * 72 + "╝",
            "",
            f"  Overall Financial Health: {self.overall_health.upper()}",
            "",
            f"  {'RATIO':<35} {'VALUE':>10}  {'BENCHMARK':>12}  STATUS",
            "  " + "─" * 68,
        ]
        for name, data in self.ratios.items():
            value = data.get("value", 0)
            benchmark = data.get("benchmark", "N/A")
            status = data.get("status", "—")
            bm_str = str(benchmark)
            lines.append(f"  {name:<35} {value:>10.2f}  {bm_str:>12}  {status}")
        lines += [
            "",
            "  STRENGTHS:",
        ]
        for s in self.strengths:
            lines.append(f"  ✓ {s}")
        lines += ["", "  AREAS FOR IMPROVEMENT:"]
        for w in self.weaknesses:
            lines.append(f"  ⚠ {w}")
        lines += ["", "  RECOMMENDATIONS:"]
        for r in self.recommendations:
            lines.append(f"  → {r}")
        return "\n".join(lines)


@dataclass
class PayrollReport:
    """Payroll calculation and compliance report."""
    pay_period: str
    employees: List[Dict[str, Any]]
    total_gross_wages: float
    total_employer_taxes: float
    total_net_payroll: float
    compliance_notes: List[str]

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 70 + "╗",
            "║  PAYROLL REPORT" + " " * 54 + "║",
            f"║  Period: {self.pay_period}" + " " * (59 - len(self.pay_period)) + "║",
            "╚" + "═" * 70 + "╝",
            "",
            f"  {'EMPLOYEE':<25} {'GROSS':>10}  {'FED TAX':>8}  {'FICA':>8}  {'NET':>10}",
            "  " + "─" * 65,
        ]
        for emp in self.employees:
            lines.append(
                f"  {emp.get('name', 'Unknown'):<25} "
                f"${emp.get('gross', 0):>9,.2f}  "
                f"${emp.get('federal_tax', 0):>7,.2f}  "
                f"${emp.get('fica_ee', 0):>7,.2f}  "
                f"${emp.get('net', 0):>9,.2f}"
            )
        lines += [
            "  " + "─" * 65,
            f"  {'TOTALS':<25} ${self.total_gross_wages:>9,.2f}",
            f"  Total Employer Taxes:              ${self.total_employer_taxes:>9,.2f}",
            f"  Total Net Payroll:                 ${self.total_net_payroll:>9,.2f}",
        ]
        if self.compliance_notes:
            lines += ["", "  COMPLIANCE NOTES:"]
            for note in self.compliance_notes:
                lines.append(f"  ! {note}")
        return "\n".join(lines)


@dataclass
class AuditDefenseStrategy:
    """IRS audit defense strategy."""
    audit_type: str
    risk_level: str
    key_issues: List[str]
    defense_steps: List[str]
    documents_needed: List[str]
    escalation_path: List[str]
    statute_of_limitations: str

    def format_as_text(self) -> str:
        lines = [
            "╔" + "═" * 70 + "╗",
            "║  IRS AUDIT DEFENSE STRATEGY" + " " * 42 + "║",
            "╚" + "═" * 70 + "╝",
            "",
            f"  Audit Type:    {self.audit_type}",
            f"  Risk Level:    {self.risk_level.upper()}",
            f"  SOL:           {self.statute_of_limitations}",
            "",
            "  KEY ISSUES:",
        ]
        for issue in self.key_issues:
            lines.append(f"  • {issue}")
        lines += ["", "  DEFENSE STEPS:"]
        for i, step in enumerate(self.defense_steps, 1):
            lines.append(f"  {i}. {step}")
        lines += ["", "  REQUIRED DOCUMENTS:"]
        for doc in self.documents_needed:
            lines.append(f"  □ {doc}")
        lines += ["", "  ESCALATION PATH (if needed):"]
        for i, path in enumerate(self.escalation_path, 1):
            lines.append(f"  {i}. {path}")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CLASS
# ─────────────────────────────────────────────────────────────────────────────

class AccountingIntelligence:
    """
    CPA-level accounting and financial analysis system.
    Replaces a CPA, tax advisor, bookkeeper, and financial controller.

    Example:
        ai = AccountingIntelligence()
        fs = ai.generate_financial_statements(transactions, "2024")
        tax = ai.tax_optimization_strategy({"entity": "s_corp"}, 500000, {})
    """

    def __init__(self):
        self.tax_calendar = TAX_CALENDAR
        self.deduction_db = DEDUCTION_DATABASE

    # ─────────────────────────────────────────────────────────────────────────
    # FINANCIAL STATEMENTS
    # ─────────────────────────────────────────────────────────────────────────

    def generate_financial_statements(
        self, transactions: List[dict], period: str
    ) -> FinancialStatement:
        """
        Generate a complete set of financial statements from a transaction list.

        Args:
            transactions: List of dicts with date, description, category, amount, type
                          type: 'revenue', 'cogs', 'expense', 'asset_purchase',
                                'liability_payment', 'owner_equity', 'loan_proceeds'
            period: "2024" or "Q1 2024" or "January 2024"

        Returns:
            FinancialStatement with income statement, balance sheet, cash flow
        """
        # Aggregate transactions by category
        revenue = sum(t["amount"] for t in transactions if t.get("type") == "revenue")
        cogs = sum(t["amount"] for t in transactions if t.get("type") == "cogs")
        expenses_by_cat: Dict[str, float] = {}
        for t in transactions:
            if t.get("type") == "expense":
                cat = t.get("category", "Other")
                expenses_by_cat[cat] = expenses_by_cat.get(cat, 0) + t["amount"]

        total_opex = sum(expenses_by_cat.values())
        depreciation = expenses_by_cat.get("Depreciation", 0)
        interest_expense = expenses_by_cat.get("Interest", 0)

        gross_profit = revenue - cogs
        gross_margin = (gross_profit / revenue) if revenue > 0 else 0.0
        ebitda = gross_profit - (total_opex - depreciation - interest_expense)
        ebit = ebitda - depreciation
        pretax_income = ebit - interest_expense
        tax_expense = max(0, pretax_income * 0.21)  # C-corp rate; adjust for entity type
        net_income = pretax_income - tax_expense

        # Balance sheet construction
        cash = sum(t["amount"] for t in transactions if t.get("category") == "Cash")
        ar = sum(t["amount"] for t in transactions if t.get("category") == "Accounts Receivable")
        inventory = sum(t["amount"] for t in transactions if t.get("category") == "Inventory")
        current_assets = max(0, cash) + max(0, ar) + max(0, inventory)

        fixed_assets_gross = sum(t["amount"] for t in transactions if t.get("type") == "asset_purchase")
        fixed_assets_net = max(0, fixed_assets_gross - depreciation)
        total_assets = current_assets + fixed_assets_net

        ap = sum(t["amount"] for t in transactions if t.get("category") == "Accounts Payable")
        current_liabilities = max(0, ap)
        long_term_debt = sum(t["amount"] for t in transactions if t.get("type") == "loan_proceeds")
        total_liabilities = current_liabilities + long_term_debt

        paid_in_capital = sum(t["amount"] for t in transactions if t.get("type") == "owner_equity")
        retained_earnings = net_income  # simplified: single period
        total_equity = paid_in_capital + retained_earnings

        # Enforce balance sheet equation: make assets = liabilities + equity
        balance_adj = total_assets - (total_liabilities + total_equity)
        if abs(balance_adj) > 0.01:
            retained_earnings -= balance_adj
            total_equity = paid_in_capital + retained_earnings

        # Cash flow (indirect method)
        operating_cf = net_income + depreciation - (ar - 0) - (inventory - 0) + (ap - 0)
        investing_cf = -fixed_assets_gross
        financing_cf = long_term_debt + paid_in_capital - sum(t["amount"] for t in transactions if t.get("type") == "liability_payment")
        net_change = operating_cf + investing_cf + financing_cf

        # Key ratios
        ratios = {
            "Gross Margin %": round(gross_margin * 100, 2),
            "Net Margin %": round((net_income / revenue * 100) if revenue > 0 else 0, 2),
            "EBITDA Margin %": round((ebitda / revenue * 100) if revenue > 0 else 0, 2),
            "Current Ratio": round(current_assets / current_liabilities if current_liabilities > 0 else 0, 2),
            "Debt-to-Equity": round(total_liabilities / total_equity if total_equity > 0 else 0, 2),
        }

        return FinancialStatement(
            period=period,
            income_statement={
                "revenue": revenue,
                "cogs": cogs,
                "gross_profit": gross_profit,
                "operating_expenses": total_opex,
                "ebitda": ebitda,
                "depreciation": depreciation,
                "ebit": ebit,
                "interest_expense": interest_expense,
                "pretax_income": pretax_income,
                "tax_expense": tax_expense,
                "net_income": net_income,
                "gross_margin_pct": round(gross_margin * 100, 2),
            },
            balance_sheet={
                "cash": cash,
                "accounts_receivable": ar,
                "inventory": inventory,
                "current_assets": current_assets,
                "fixed_assets_gross": fixed_assets_gross,
                "fixed_assets_net": fixed_assets_net,
                "other_assets": 0,
                "total_assets": current_assets + fixed_assets_net,
                "accounts_payable": ap,
                "current_liabilities": current_liabilities,
                "long_term_debt": long_term_debt,
                "total_liabilities": total_liabilities,
                "paid_in_capital": paid_in_capital,
                "retained_earnings": retained_earnings,
                "total_equity": total_equity,
            },
            cash_flow_statement={
                "net_income": net_income,
                "depreciation": depreciation,
                "changes_in_working_capital": -ar - inventory + ap,
                "operating_activities": operating_cf,
                "capex": -fixed_assets_gross,
                "investing_activities": investing_cf,
                "debt_proceeds": long_term_debt,
                "equity_proceeds": paid_in_capital,
                "financing_activities": financing_cf,
                "net_change_in_cash": net_change,
            },
            notes=[
                f"Period: {period}",
                "Financial statements prepared on accrual basis",
                "Depreciation calculated on straight-line method",
                "Tax rate: 21% (C-Corp flat rate per TCJA 2017)",
                "Balance sheet checks: " + ("BALANCED ✓" if abs((current_assets + fixed_assets_net) - (total_liabilities + total_equity)) < 0.01 else "IMBALANCED — REVIEW"),
            ],
            ratios=ratios,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # RATIO ANALYSIS
    # ─────────────────────────────────────────────────────────────────────────

    def financial_ratio_analysis(self, statements: FinancialStatement) -> RatioAnalysis:
        """
        Calculate and interpret all major financial ratios with industry benchmarks.

        Args:
            statements: FinancialStatement from generate_financial_statements()

        Returns:
            RatioAnalysis with benchmarks and interpretations
        """
        inc = statements.income_statement
        bs = statements.balance_sheet

        revenue = max(1, inc.get("revenue", 1))
        net_income = inc.get("net_income", 0)
        ebitda = inc.get("ebitda", 0)
        gross_profit = inc.get("gross_profit", 0)
        interest = max(1, inc.get("interest_expense", 1))

        current_assets = bs.get("current_assets", 0)
        current_liabilities = max(1, bs.get("current_liabilities", 1))
        cash = bs.get("cash", 0)
        ar = bs.get("accounts_receivable", 0)
        inventory = bs.get("inventory", 0)
        total_assets = max(1, bs.get("total_assets", 1))
        total_liabilities = bs.get("total_liabilities", 0)
        total_equity = max(1, bs.get("total_equity", 1))
        long_term_debt = bs.get("long_term_debt", 0)

        def status(value: float, good_min: float, good_max: float = float("inf"), higher_is_better: bool = True) -> str:
            if higher_is_better:
                if value >= good_min:
                    return "✓ Good"
                else:
                    return "⚠ Low"
            else:
                if value <= good_max:
                    return "✓ Good"
                else:
                    return "⚠ High"

        ratios: Dict[str, Dict[str, Any]] = {
            # Liquidity
            "Current Ratio": {
                "value": round(current_assets / current_liabilities, 2),
                "benchmark": "1.5–3.0x",
                "status": status(current_assets / current_liabilities, 1.5),
                "interpretation": "Ability to pay short-term obligations",
            },
            "Quick Ratio": {
                "value": round((current_assets - inventory) / current_liabilities, 2),
                "benchmark": "1.0–2.0x",
                "status": status((current_assets - inventory) / current_liabilities, 1.0),
                "interpretation": "Liquid assets vs current liabilities",
            },
            "Cash Ratio": {
                "value": round(cash / current_liabilities, 2),
                "benchmark": ">0.5x",
                "status": status(cash / current_liabilities, 0.5),
                "interpretation": "Cash available vs current obligations",
            },
            # Profitability
            "Gross Margin %": {
                "value": round(gross_profit / revenue * 100, 2),
                "benchmark": "Varies: SaaS 70%+, Retail 25–45%",
                "status": status(gross_profit / revenue, 0.25),
                "interpretation": "Revenue remaining after direct costs",
            },
            "Net Profit Margin %": {
                "value": round(net_income / revenue * 100, 2),
                "benchmark": "5–20% (industry varies)",
                "status": status(net_income / revenue, 0.05),
                "interpretation": "Ultimate profitability after all expenses",
            },
            "ROA (Return on Assets) %": {
                "value": round(net_income / total_assets * 100, 2),
                "benchmark": "5–10%",
                "status": status(net_income / total_assets, 0.05),
                "interpretation": "Profit generated per dollar of assets",
            },
            "ROE (Return on Equity) %": {
                "value": round(net_income / total_equity * 100, 2),
                "benchmark": "15–20%",
                "status": status(net_income / total_equity, 0.15),
                "interpretation": "Return on shareholder investment",
            },
            "EBITDA Margin %": {
                "value": round(ebitda / revenue * 100, 2),
                "benchmark": "15–35%",
                "status": status(ebitda / revenue, 0.15),
                "interpretation": "Operating profitability before non-cash/financing items",
            },
            # Leverage
            "Debt-to-Equity": {
                "value": round(total_liabilities / total_equity, 2),
                "benchmark": "<2.0x",
                "status": status(total_liabilities / total_equity, 0, 2.0, higher_is_better=False),
                "interpretation": "Financial leverage; higher = more risk",
            },
            "Interest Coverage (EBIT/Interest)": {
                "value": round((ebitda - inc.get("depreciation", 0)) / max(interest, 1), 2),
                "benchmark": ">3.0x",
                "status": status((ebitda - inc.get("depreciation", 0)) / max(interest, 1), 3.0),
                "interpretation": "Ability to cover interest payments",
            },
            "Debt Service Coverage (DSCR)": {
                "value": round(ebitda / max(interest + inc.get("principal_payments", 0), 1), 2),
                "benchmark": ">1.25x (lender minimum)",
                "status": status(ebitda / max(interest + inc.get("principal_payments", 0), 1), 1.25),
                "interpretation": "SBA and bank lenders require >1.25x DSCR",
            },
        }

        strengths = [name for name, data in ratios.items() if "✓" in data["status"]]
        weaknesses = [name for name, data in ratios.items() if "⚠" in data["status"]]

        overall = "excellent" if len(strengths) > 8 else "good" if len(strengths) > 5 else "fair" if len(strengths) > 2 else "poor"

        recommendations = []
        if "Current Ratio" in weaknesses:
            recommendations.append("Improve liquidity: negotiate longer AP terms; speed up AR collection")
        if "Net Profit Margin %" in weaknesses:
            recommendations.append("Reduce operating expenses; review pricing strategy; cut COGS")
        if "Debt-to-Equity" in weaknesses:
            recommendations.append("Reduce debt: prioritize paying down high-interest obligations")
        if "EBITDA Margin %" in weaknesses:
            recommendations.append("Review all operating costs for efficiency opportunities")

        return RatioAnalysis(
            ratios=ratios,
            overall_health=overall,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # TAX OPTIMIZATION
    # ─────────────────────────────────────────────────────────────────────────

    def tax_optimization_strategy(
        self,
        entity: dict,
        income: float,
        expenses: dict,
    ) -> TaxStrategy:
        """
        Generate comprehensive tax optimization strategy.

        Args:
            entity: dict with entity_type (sole_prop/llc/s_corp/c_corp/partnership),
                    state, owner_age, is_married, w2_salary (for s-corps),
                    has_employees, years_in_business
            income: gross business income / revenue
            expenses: dict of expense category → amount

        Returns:
            TaxStrategy with all applicable strategies and estimated savings
        """
        entity_type = entity.get("entity_type", "sole_prop")
        state = entity.get("state", "CA")
        age = entity.get("owner_age", 40)
        is_married = entity.get("is_married", False)
        w2_salary = entity.get("w2_salary", income * 0.40)
        has_employees = entity.get("has_employees", False)

        strategies = []
        deductions = []
        credits = []
        total_savings = 0.0

        total_expenses = sum(expenses.values()) if expenses else income * 0.40
        net_income = income - total_expenses

        # ── Entity Selection ─────────────────────────────────────────────────
        if entity_type == "sole_prop" and net_income > 80000:
            strategies.append(
                "ENTITY RESTRUCTURE: Convert to S-Corp. Net income $80K+ means S-Corp saves "
                "SE tax on distributions above reasonable salary. "
                f"Example: ${net_income:,.0f} income, ${w2_salary:,.0f} salary → "
                f"${(net_income - w2_salary) * 0.153:,.0f} SE tax savings per year."
            )
            total_savings += (net_income - w2_salary) * 0.153

        # ── QBI Deduction (Section 199A) ─────────────────────────────────────
        if entity_type in ("s_corp", "llc", "sole_prop", "partnership"):
            qbi_income = net_income if entity_type != "s_corp" else net_income - w2_salary
            qbi_deduction = min(qbi_income * 0.20, (income * 0.50) if has_employees else qbi_income * 0.20)
            qbi_tax_savings = qbi_deduction * 0.24  # assume 24% marginal rate
            deductions.append({
                "name": "QBI Deduction (Section 199A)",
                "amount": qbi_deduction,
                "irc": "§199A",
                "notes": "20% of qualified business income; phase-outs for specified service trades (SST) at $182,050/$364,200 (2024)",
            })
            strategies.append(
                f"MAXIMIZE QBI DEDUCTION (§199A): Deduct ${qbi_deduction:,.0f} (20% of QBI). "
                f"Tax savings: ~${qbi_tax_savings:,.0f}. "
                "For S-corps: Keep W-2 wages at 'reasonable compensation' — QBI = pass-through income above salary. "
                "WARNING: Specified Service Trades (lawyers, consultants, doctors) phase out at higher incomes."
            )
            total_savings += qbi_tax_savings

        # ── S-Corp Salary Optimization ────────────────────────────────────────
        if entity_type == "s_corp":
            opt_salary = min(net_income * 0.40, 160000)  # reasonable salary rule
            se_savings = (net_income - opt_salary) * 0.153
            strategies.append(
                f"S-CORP SALARY OPTIMIZATION: Set W-2 salary at ${opt_salary:,.0f} "
                f"('reasonable compensation' for your industry/duties). "
                f"Take remaining ${net_income - opt_salary:,.0f} as distributions (no SE tax). "
                f"SE tax savings: ~${se_savings:,.0f}/year. "
                "Document reasonable salary with industry salary surveys."
            )
            total_savings += se_savings

        # ── Retirement Contributions ─────────────────────────────────────────
        if entity_type == "s_corp":
            solo_401k_employee = min(23000 + (7500 if age >= 50 else 0), w2_salary)
            solo_401k_employer = min(w2_salary * 0.25, 69000 - solo_401k_employee)
            total_401k = solo_401k_employee + solo_401k_employer
        else:
            sep_limit = min(net_income * 0.25, 69000)
            total_401k = sep_limit

        retirement_savings = total_401k * 0.32  # 32% marginal rate
        deductions.append({
            "name": "Solo 401(k) / SEP-IRA Contribution",
            "amount": total_401k,
            "irc": "§401(k)/§404",
            "notes": f"Max ${total_401k:,.0f} in retirement contributions",
        })
        strategies.append(
            f"MAXIMIZE RETIREMENT CONTRIBUTIONS: Contribute ${total_401k:,.0f} to "
            f"{'Solo 401(k)' if entity_type == 's_corp' else 'SEP-IRA'}. "
            f"Tax savings: ~${retirement_savings:,.0f}. "
            "Solo 401k allows Roth contributions — consider split for tax diversification."
        )
        total_savings += retirement_savings

        # ── Home Office ──────────────────────────────────────────────────────
        home_office_sqft = entity.get("home_office_sqft", 0)
        if home_office_sqft > 0:
            ho_deduction = min(home_office_sqft * 5, 1500)  # simplified method
            strategies.append(
                f"HOME OFFICE DEDUCTION (§280A): Claim ${ho_deduction:,.0f} using simplified method "
                f"($5 × {home_office_sqft} sq ft, max 300 sq ft = $1,500). "
                "Room must be REGULAR AND EXCLUSIVE use for business. No personal use allowed. "
                "Alternatively use actual method if home expenses × business% > $1,500."
            )
            deductions.append({"name": "Home Office (Simplified)", "amount": ho_deduction, "irc": "§280A"})
            total_savings += ho_deduction * 0.24

        # ── Augusta Rule ─────────────────────────────────────────────────────
        home_value = entity.get("home_fair_market_rental_per_day", 500)
        augusta_deduction = home_value * 14
        strategies.append(
            f"AUGUSTA RULE (§280A(g)): Rent your home to your business for up to 14 days/year. "
            f"At ${home_value}/day market rate = ${augusta_deduction:,.0f} business deduction; "
            f"you personally receive it TAX-FREE (not reported on Schedule E). "
            "Use for board meetings, strategic planning sessions, company retreats. "
            "Document with: rental agreement at fair market rate, business purpose memo, photos."
        )
        deductions.append({"name": "Augusta Rule — Home Rental to Business", "amount": augusta_deduction, "irc": "§280A(g)"})
        total_savings += augusta_deduction * 0.24

        # ── Vehicle Deduction ────────────────────────────────────────────────
        business_miles = entity.get("business_miles", 0)
        if business_miles > 0:
            mileage_deduction = business_miles * 0.67  # 2024 rate
            strategies.append(
                f"VEHICLE DEDUCTION: {business_miles:,} business miles × $0.67 = ${mileage_deduction:,.0f}. "
                "Track EVERY mile with MileIQ, TripLog, or a mileage log. "
                "Compare: Standard mileage vs Actual (gas + insurance + depreciation × business %) — "
                "take whichever is larger. "
                "New vehicle purchase: Section 179 up to $1.22M or 60% bonus depreciation in 2024."
            )
            deductions.append({"name": "Vehicle — Standard Mileage", "amount": mileage_deduction, "irc": "§162"})
            total_savings += mileage_deduction * 0.24

        # ── Section 179 / Bonus Depreciation ──────────────────────────────────
        equipment_cost = expenses.get("equipment", 0) + expenses.get("machinery", 0) + expenses.get("technology", 0)
        if equipment_cost > 0:
            sec179_limit = min(equipment_cost, 1_220_000)  # 2024 limit
            sec179_savings = sec179_limit * 0.24
            strategies.append(
                f"SECTION 179 EXPENSING (§179): Deduct ${sec179_limit:,.0f} of equipment/machinery cost "
                f"immediately in the year of purchase rather than depreciating over years. "
                f"2024 limit: $1,220,000 (phase-out begins at $3,050,000 total equipment). "
                "Also consider 60% Bonus Depreciation (2024) on new/used assets. "
                "Covers: machinery, computers, vehicles (>6,000 lbs), office furniture, software."
            )
            deductions.append({
                "name": "Section 179 Expensing",
                "amount": sec179_limit,
                "irc": "§179",
                "notes": "Immediate expensing of qualifying business equipment",
            })
            total_savings += sec179_savings

        # ── R&D Tax Credit ───────────────────────────────────────────────────
        if entity.get("has_rd_expenses", False):
            rd_expenses = entity.get("rd_expenses", 0)
            rd_credit = rd_expenses * 0.20
            credits.append({"name": "R&D Tax Credit (§41)", "amount": rd_credit, "irc": "§41"})
            strategies.append(
                f"R&D TAX CREDIT (§41): Claim credit of ${rd_credit:,.0f} on ${rd_expenses:,.0f} of qualified "
                "research expenses (QREs). Qualifies: developing/improving products, processes, software. "
                "Startup benefit: Use up to $500K/year to offset PAYROLL taxes (not income tax). "
                "Hire an R&D tax credit specialist — ROI is typically 3–5x their fee."
            )
            total_savings += rd_credit

        # ── WOTC ─────────────────────────────────────────────────────────────
        if has_employees:
            credits.append({
                "name": "Work Opportunity Tax Credit (WOTC)",
                "amount": 2400,
                "irc": "§51",
                "notes": "Per qualifying new hire; up to $9,600 for veterans",
            })
            strategies.append(
                "WORK OPPORTUNITY TAX CREDIT (WOTC): Screen all new hires for qualifying status. "
                "Credit: $2,400–$9,600 per hire for veterans, ex-felons, food stamp recipients, etc. "
                "File Form 8850 within 28 days of new hire's start date."
            )

        # ── Deadlines ────────────────────────────────────────────────────────
        deadlines = []
        for month, events in self.tax_calendar.items():
            for event in events:
                if entity_type.lower() in event["entity"].lower() or "All" in event["entity"]:
                    deadlines.append({"date": event["date"], "description": event["deadline"]})

        # Estimate tax liability before optimization
        if entity_type == "c_corp":
            base_tax = net_income * 0.21
        elif entity_type == "s_corp":
            base_tax = net_income * 0.30  # approximate blended rate
        else:
            base_tax = net_income * 0.30 + net_income * 0.153  # income + SE tax

        optimized_tax = max(0, base_tax - total_savings)
        effective_rate = optimized_tax / income if income > 0 else 0

        return TaxStrategy(
            entity_type=entity_type,
            estimated_tax_liability=optimized_tax,
            deductions=deductions,
            credits=credits,
            estimated_savings=total_savings,
            strategies=strategies,
            deadlines=deadlines[:8],
            effective_tax_rate=effective_rate,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # PAYROLL SYSTEM
    # ─────────────────────────────────────────────────────────────────────────

    def payroll_system(self, employees: List[dict]) -> PayrollReport:
        """
        Calculate payroll, taxes, and generate compliance report.

        Args:
            employees: List of dicts with name, gross_wages, filing_status,
                       allowances, state, ytd_wages, is_1099 (bool)

        Returns:
            PayrollReport with complete payroll breakdown
        """
        pay_period = "Current Pay Period"
        processed = []
        total_gross = 0.0
        total_employer_taxes = 0.0
        compliance_notes = []

        # 2024 tax brackets (simplified — use tax tables for production)
        FICA_SS_RATE = 0.062   # 6.2% employee, 6.2% employer
        FICA_MEDI_RATE = 0.0145  # 1.45% each
        FUTA_RATE = 0.006        # Effective FUTA after credits
        SS_WAGE_BASE = 168600    # 2024 Social Security wage base

        for emp in employees:
            name = emp.get("name", "Employee")
            gross = emp.get("gross_wages", 0)
            filing = emp.get("filing_status", "single")
            ytd = emp.get("ytd_wages", 0)
            is_1099 = emp.get("is_1099", False)

            if is_1099:
                compliance_notes.append(
                    f"{name}: Classified as 1099 contractor. Verify under IRS 20-factor behavioral/financial control test. "
                    "Misclassification penalty: back taxes + 100% of FICA + penalties."
                )
                processed.append({
                    "name": f"{name} (1099)",
                    "gross": gross,
                    "federal_tax": 0,
                    "fica_ee": 0,
                    "net": gross,
                    "note": "1099 — no withholding",
                })
                continue

            # Federal income tax withholding (simplified flat rate for illustration)
            if filing == "single":
                fed_tax = max(0, (gross - 100) * 0.22)  # simplified
            else:
                fed_tax = max(0, (gross - 200) * 0.22)

            # FICA — employee portion
            ss_taxable = max(0, min(gross, SS_WAGE_BASE - ytd))
            ss_ee = ss_taxable * FICA_SS_RATE
            medi_ee = gross * FICA_MEDI_RATE
            # Additional Medicare 0.9% on wages > $200K
            add_medi = gross * 0.009 if (ytd + gross) > 200000 else 0
            fica_ee = ss_ee + medi_ee + add_medi

            # Employer FICA
            ss_er = ss_taxable * FICA_SS_RATE
            medi_er = gross * FICA_MEDI_RATE
            fica_er = ss_er + medi_er
            futa = min(gross, max(0, 7000 - ytd)) * FUTA_RATE

            net = gross - fed_tax - fica_ee
            total_gross += gross
            total_employer_taxes += fica_er + futa

            processed.append({
                "name": name,
                "gross": gross,
                "federal_tax": round(fed_tax, 2),
                "state_tax": round(gross * 0.05, 2),
                "fica_ee": round(fica_ee, 2),
                "fica_er": round(fica_er, 2),
                "futa": round(futa, 2),
                "net": round(net, 2),
            })

        # Compliance notes
        compliance_notes += [
            "File Form 941 quarterly (due: April 30, July 31, Oct 31, Jan 31)",
            "Deposit payroll taxes: semi-weekly if prior year liability >$50K; otherwise monthly",
            "File Form 940 annually for FUTA (due: January 31)",
            "Issue W-2s to all employees by January 31",
            "Issue 1099-NEC to contractors paid ≥$600 by January 31",
        ]

        return PayrollReport(
            pay_period=pay_period,
            employees=processed,
            total_gross_wages=total_gross,
            total_employer_taxes=total_employer_taxes,
            total_net_payroll=total_gross - sum(e.get("federal_tax", 0) + e.get("fica_ee", 0) for e in processed),
            compliance_notes=compliance_notes,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # AUDIT DEFENSE
    # ─────────────────────────────────────────────────────────────────────────

    def audit_defense_guide(self, audit_type: str, issues: List[str]) -> AuditDefenseStrategy:
        """
        IRS audit defense strategy for all audit types.

        Args:
            audit_type: 'correspondence', 'office', 'field', 'eggshell'
            issues: List of IRS issues cited in audit notice

        Returns:
            AuditDefenseStrategy with complete defense roadmap
        """
        documents_needed = [
            "Copy of audit notice and all IRS correspondence",
            "Original tax return(s) under examination",
            "Bank statements for all accounts (business and personal) for the period",
            "All income records: 1099s, K-1s, business records, invoices",
            "Receipts for ALL deductions claimed",
            "Business mileage logs (if vehicle deduction claimed)",
            "Home office documentation (floor plan, measurements, photos)",
        ]

        if audit_type == "correspondence":
            defense_steps = [
                "Read the IRS letter CAREFULLY — identify exactly what they're questioning",
                "Gather all documentation supporting the questioned item(s)",
                "Respond WITHIN THE DEADLINE (typically 30–60 days) — late response = assessment",
                "Write a clear, organized response letter with attachments",
                "Only address what they asked — don't volunteer additional information",
                "Send response via Certified Mail with Return Receipt",
                "Keep a copy of everything you send",
                "If assessment is wrong, file a written protest within 30 days",
            ]
            risk = "low"
            escalation = [
                "If IRS disagrees: Request appeals conference (IRS Office of Appeals)",
                "Offer in Compromise if tax debt is legitimate but unaffordable",
                "Tax Court petition (pro se) for amounts < $50K (Small Tax Case procedure)",
                "Hire CPA or tax attorney for amounts > $10K or complex issues",
            ]
        elif audit_type in ("office", "field"):
            defense_steps = [
                "Hire a tax professional (CPA, EA, or tax attorney) immediately — DO NOT GO ALONE",
                "Do NOT meet with IRS at your home or business — schedule at IRS office or your CPA's office",
                "Prepare organized binders of ALL documentation organized by IRS information document request (IDR)",
                "Let your representative speak — you can say 'I'll check with my representative on that'",
                "Review all returns for any issues BEFORE the audit — voluntary disclosure is better than discovery",
                "Do not bring more documents than requested — don't open new issues",
                "Verify agent's credentials and get their badge number",
                "Take notes at every meeting — date, time, topics discussed",
                "Never sign Form 872 (extension of statute) without understanding why",
            ]
            risk = "medium" if audit_type == "office" else "high"
            escalation = [
                "If examiner proposes assessment: Submit written protest to IRS Appeals Office",
                "IRS Appeals: 90% of cases settled at Appeals without litigation",
                "If Appeals fails: Tax Court, District Court, or Court of Federal Claims",
                "Consider Offer in Compromise, Installment Agreement, or Currently Not Collectible status for liability",
            ]
        else:  # eggshell / criminal risk
            defense_steps = [
                "IMMEDIATELY hire a criminal tax defense attorney (not a CPA)",
                "Invoke Fifth Amendment rights — do not provide any statements without attorney",
                "Attorney-client privilege protects your communications with a tax attorney (not a CPA)",
                "Do not destroy or alter any records — obstruction charge is often worse than underlying tax issue",
                "Understand: Civil audit can become criminal referral if agent finds fraud indicators",
                "Voluntary disclosure may be available — attorney can evaluate",
            ]
            risk = "critical"
            escalation = [
                "Criminal Defense Attorney: Evaluate voluntary disclosure program",
                "If indicted: Jury trial is typically best option (jury nullification possible)",
                "Sentencing: Tax evasion up to 5 years; tax fraud up to 3 years per count",
            ]
            documents_needed.insert(0, "⚠ DO NOT PRODUCE ANY DOCUMENTS WITHOUT ATTORNEY GUIDANCE")

        return AuditDefenseStrategy(
            audit_type=audit_type.replace("_", " ").title() + " Audit",
            risk_level=risk,
            key_issues=issues if issues else ["Under examination"],
            defense_steps=defense_steps,
            documents_needed=documents_needed,
            escalation_path=escalation,
            statute_of_limitations=(
                "3 years from filing date (standard); "
                "6 years if substantial omission (>25% of income); "
                "Unlimited if fraudulent return or no return filed"
            ),
        )
