"""
Financial Report Templates — Professional financial document templates.
All output uses Unicode box-drawing characters and professional formatting.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


def _fmt_currency(value, width: int = 16) -> str:
    """Format a value as currency, right-aligned to width."""
    try:
        amount = float(value)
        formatted = f"${amount:,.2f}"
    except (TypeError, ValueError):
        formatted = str(value) if value else "[AMOUNT]"
    return formatted.rjust(width)


def _fmt_pct(value, width: int = 10) -> str:
    try:
        return f"{float(value):.1f}%".rjust(width)
    except (TypeError, ValueError):
        return "[%]".rjust(width)


def _center(text: str, width: int = 66) -> str:
    return text.center(width)


def _box_top(width: int = 66) -> str:
    return "╔" + "═" * (width - 2) + "╗"


def _box_bot(width: int = 66) -> str:
    return "╚" + "═" * (width - 2) + "╝"


def _box_mid(width: int = 66) -> str:
    return "╠" + "═" * (width - 2) + "╣"


def _box_row(text: str, width: int = 66) -> str:
    inner = width - 4
    text = str(text)[:inner]
    return "║  " + text.ljust(inner) + "  ║"


def _box_title(title: str, subtitle: str = "", width: int = 66) -> str:
    lines = [_box_top(width), _box_row(_center(title, width - 4), width)]
    if subtitle:
        lines.append(_box_row(_center(subtitle, width - 4), width))
    lines.append(_box_mid(width))
    return "\n".join(lines)


def _section_header(title: str, width: int = 66) -> str:
    return f"\n{'─' * width}\n  {title.upper()}\n{'─' * width}"


class FinancialReportTemplates:
    """
    Professional financial document templates with Unicode table formatting.
    All templates accept dictionaries with user data and return formatted strings.
    """

    WIDTH = 68

    # ------------------------------------------------------------------
    # Personal Financial Statement
    # ------------------------------------------------------------------

    def personal_financial_statement(self, data: Dict[str, Any]) -> str:
        """Generate a bank/SBA-ready personal financial statement."""
        W = self.WIDTH
        name = data.get("name", "[APPLICANT NAME]")
        date = data.get("date", datetime.now().strftime("%B %d, %Y"))
        ssn = data.get("ssn", "XXX-XX-[LAST 4]")
        address = data.get("address", "[ADDRESS]")
        phone = data.get("phone", "[PHONE]")
        employer = data.get("employer", "[EMPLOYER]")
        gross_income = data.get("gross_income", 0)
        net_income = data.get("net_income", 0)

        # Assets
        cash = data.get("cash", 0)
        savings = data.get("savings", 0)
        investments = data.get("investments", 0)
        real_estate = data.get("real_estate", 0)
        auto = data.get("auto", 0)
        retirement = data.get("retirement", 0)
        other_assets = data.get("other_assets", 0)
        total_assets = cash + savings + investments + real_estate + auto + retirement + other_assets

        # Liabilities
        mortgage = data.get("mortgage", 0)
        auto_loan = data.get("auto_loan", 0)
        student_loans = data.get("student_loans", 0)
        credit_cards = data.get("credit_cards", 0)
        other_liabilities = data.get("other_liabilities", 0)
        total_liabilities = mortgage + auto_loan + student_loans + credit_cards + other_liabilities

        net_worth = total_assets - total_liabilities

        lines = []
        lines.append(_box_title("PERSONAL FINANCIAL STATEMENT", f"As of {date}", W))
        lines.append(_box_row(f"Name: {name:<35}  SSN: {ssn}", W))
        lines.append(_box_row(f"Address: {address}", W))
        lines.append(_box_row(f"Phone: {phone:<30}  Employer: {employer}", W))
        lines.append(_box_mid(W))
        lines.append(_box_row("ASSETS", W))
        lines.append(_box_mid(W))

        def asset_row(label, val):
            return _box_row(f"  {label:<40}{_fmt_currency(val, 16)}", W)

        lines.append(asset_row("Cash and Checking Accounts", cash))
        lines.append(asset_row("Savings Accounts", savings))
        lines.append(asset_row("Investment Accounts (stocks/bonds/mutual funds)", investments))
        lines.append(asset_row("Real Estate (market value)", real_estate))
        lines.append(asset_row("Automobiles (market value)", auto))
        lines.append(asset_row("Retirement Accounts (IRA, 401k)", retirement))
        lines.append(asset_row("Other Assets", other_assets))
        lines.append(_box_mid(W))
        lines.append(_box_row(f"  {'TOTAL ASSETS':<40}{_fmt_currency(total_assets, 16)}", W))
        lines.append(_box_mid(W))
        lines.append(_box_row("LIABILITIES", W))
        lines.append(_box_mid(W))

        def liab_row(label, val):
            return _box_row(f"  {label:<40}{_fmt_currency(val, 16)}", W)

        lines.append(liab_row("Mortgage Balance(s)", mortgage))
        lines.append(liab_row("Auto Loan Balance(s)", auto_loan))
        lines.append(liab_row("Student Loan Balance(s)", student_loans))
        lines.append(liab_row("Credit Card Balances", credit_cards))
        lines.append(liab_row("Other Liabilities", other_liabilities))
        lines.append(_box_mid(W))
        lines.append(_box_row(f"  {'TOTAL LIABILITIES':<40}{_fmt_currency(total_liabilities, 16)}", W))
        lines.append(_box_mid(W))
        lines.append(_box_row(f"  {'NET WORTH (Total Assets - Total Liabilities)':<40}{_fmt_currency(net_worth, 16)}", W))
        lines.append(_box_mid(W))
        lines.append(_box_row("INCOME", W))
        lines.append(_box_mid(W))
        lines.append(_box_row(f"  {'Annual Gross Income':<40}{_fmt_currency(gross_income, 16)}", W))
        lines.append(_box_row(f"  {'Annual Net Income (after taxes)':<40}{_fmt_currency(net_income, 16)}", W))
        lines.append(_box_bot(W))

        lines.append("")
        lines.append("CERTIFICATION:")
        lines.append("The undersigned certifies that the information contained in this statement")
        lines.append("is true and accurate as of the date above.")
        lines.append("")
        lines.append("Signature: _______________________________   Date: _______________")
        lines.append(f"           {name}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Business Financial Summary
    # ------------------------------------------------------------------

    def business_financial_summary(self, data: Dict[str, Any]) -> str:
        """Generate an executive financial dashboard for a business."""
        W = self.WIDTH
        company = data.get("company", "[COMPANY NAME]")
        period = data.get("period", f"Year Ended {datetime.now().strftime('%B %d, %Y')}")
        currency = data.get("currency", "USD")

        revenue = data.get("revenue", 0)
        cogs = data.get("cogs", 0)
        gross_profit = revenue - cogs
        gross_margin = (gross_profit / revenue * 100) if revenue else 0

        operating_exp = data.get("operating_expenses", 0)
        ebitda = gross_profit - operating_exp
        depreciation = data.get("depreciation", 0)
        ebit = ebitda - depreciation
        interest = data.get("interest_expense", 0)
        ebt = ebit - interest
        tax = data.get("income_tax", 0)
        net_income = ebt - tax
        net_margin = (net_income / revenue * 100) if revenue else 0

        total_assets = data.get("total_assets", 0)
        total_liabilities = data.get("total_liabilities", 0)
        equity = total_assets - total_liabilities
        cash = data.get("cash", 0)
        current_ratio = data.get("current_ratio", 0)

        lines = []
        lines.append(_box_title(
            f"{company.upper()}",
            f"EXECUTIVE FINANCIAL SUMMARY — {period} ({currency})",
            W
        ))

        def row(label, val, is_margin=False):
            if is_margin:
                return _box_row(f"  {label:<38}{_fmt_pct(val, 16)}", W)
            return _box_row(f"  {label:<38}{_fmt_currency(val, 16)}", W)

        lines.append(_box_row(_center("INCOME STATEMENT", W - 4), W))
        lines.append(_box_mid(W))
        lines.append(row("Revenue", revenue))
        lines.append(row("Cost of Goods Sold (COGS)", cogs))
        lines.append(_box_row("  " + "─" * (W - 6), W))
        lines.append(row("GROSS PROFIT", gross_profit))
        lines.append(row("  Gross Margin", gross_margin, True))
        lines.append(row("Operating Expenses", operating_exp))
        lines.append(_box_row("  " + "─" * (W - 6), W))
        lines.append(row("EBITDA", ebitda))
        lines.append(row("Depreciation & Amortization", depreciation))
        lines.append(row("EBIT (Operating Income)", ebit))
        lines.append(row("Interest Expense", interest))
        lines.append(row("Earnings Before Tax (EBT)", ebt))
        lines.append(row("Income Tax", tax))
        lines.append(_box_row("  " + "═" * (W - 6), W))
        lines.append(row("NET INCOME", net_income))
        lines.append(row("  Net Profit Margin", net_margin, True))
        lines.append(_box_mid(W))
        lines.append(_box_row(_center("BALANCE SHEET SUMMARY", W - 4), W))
        lines.append(_box_mid(W))
        lines.append(row("Total Assets", total_assets))
        lines.append(row("Total Liabilities", total_liabilities))
        lines.append(row("Total Equity", equity))
        lines.append(row("Cash & Equivalents", cash))
        lines.append(row("Current Ratio", current_ratio))
        lines.append(_box_bot(W))
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Net Worth Statement
    # ------------------------------------------------------------------

    def net_worth_statement(self, data: Dict[str, Any]) -> str:
        """Generate a comprehensive personal balance sheet."""
        W = self.WIDTH
        name = data.get("name", "[YOUR NAME]")
        date = data.get("date", datetime.now().strftime("%B %d, %Y"))

        asset_groups = data.get("asset_groups", [
            {"label": "Liquid Assets", "items": [
                ("Checking Accounts", data.get("checking", 0)),
                ("Savings Accounts", data.get("savings", 0)),
                ("Money Market", data.get("money_market", 0)),
            ]},
            {"label": "Investment Assets", "items": [
                ("Brokerage Accounts", data.get("brokerage", 0)),
                ("Retirement Accounts", data.get("retirement", 0)),
                ("Crypto/Alternative", data.get("crypto", 0)),
            ]},
            {"label": "Real Property", "items": [
                ("Primary Residence", data.get("primary_home", 0)),
                ("Investment Properties", data.get("investment_property", 0)),
            ]},
            {"label": "Personal Property", "items": [
                ("Vehicles", data.get("vehicles", 0)),
                ("Jewelry/Art/Collectibles", data.get("valuables", 0)),
                ("Business Interests", data.get("business", 0)),
            ]},
        ])

        liability_groups = data.get("liability_groups", [
            {"label": "Secured Debt", "items": [
                ("Primary Mortgage", data.get("mortgage", 0)),
                ("Home Equity Loan/HELOC", data.get("heloc", 0)),
                ("Auto Loans", data.get("auto_loan", 0)),
            ]},
            {"label": "Unsecured Debt", "items": [
                ("Credit Card Balances", data.get("credit_cards", 0)),
                ("Student Loans", data.get("student_loans", 0)),
                ("Personal Loans", data.get("personal_loans", 0)),
                ("Other Liabilities", data.get("other_liabilities", 0)),
            ]},
        ])

        total_assets = sum(
            v for g in asset_groups for _, v in g["items"]
        )
        total_liabilities = sum(
            v for g in liability_groups for _, v in g["items"]
        )
        net_worth = total_assets - total_liabilities

        lines = []
        lines.append(_box_title(f"NET WORTH STATEMENT — {name}", f"As of {date}", W))
        lines.append(_box_row(_center("ASSETS", W - 4), W))
        lines.append(_box_mid(W))

        for group in asset_groups:
            lines.append(_box_row(f"  [{group['label'].upper()}]", W))
            group_total = 0
            for label, val in group["items"]:
                lines.append(_box_row(f"    {label:<36}{_fmt_currency(val, 16)}", W))
                group_total += float(val or 0)
            lines.append(_box_row(f"  {'Subtotal — ' + group['label']:<38}{_fmt_currency(group_total, 16)}", W))
            lines.append(_box_row("  " + "─" * (W - 6), W))

        lines.append(_box_row(f"  {'TOTAL ASSETS':<38}{_fmt_currency(total_assets, 16)}", W))
        lines.append(_box_mid(W))
        lines.append(_box_row(_center("LIABILITIES", W - 4), W))
        lines.append(_box_mid(W))

        for group in liability_groups:
            lines.append(_box_row(f"  [{group['label'].upper()}]", W))
            group_total = 0
            for label, val in group["items"]:
                lines.append(_box_row(f"    {label:<36}{_fmt_currency(val, 16)}", W))
                group_total += float(val or 0)
            lines.append(_box_row(f"  {'Subtotal — ' + group['label']:<38}{_fmt_currency(group_total, 16)}", W))
            lines.append(_box_row("  " + "─" * (W - 6), W))

        lines.append(_box_row(f"  {'TOTAL LIABILITIES':<38}{_fmt_currency(total_liabilities, 16)}", W))
        lines.append(_box_mid(W))
        lines.append(_box_row(f"  {'NET WORTH (Assets − Liabilities)':<38}{_fmt_currency(net_worth, 16)}", W))
        lines.append(_box_bot(W))
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Cash Flow Analysis
    # ------------------------------------------------------------------

    def cash_flow_analysis(self, data: Dict[str, Any]) -> str:
        """Generate monthly cash flow with variance analysis."""
        W = self.WIDTH
        name = data.get("name", "[NAME]")
        period = data.get("period", datetime.now().strftime("%B %Y"))
        income_items = data.get("income", [
            ("Primary Salary (net)", data.get("salary", 0), data.get("salary_budget", 0)),
            ("Side Income", data.get("side_income", 0), data.get("side_income_budget", 0)),
            ("Investment Income", data.get("investment_income", 0), 0),
            ("Other Income", data.get("other_income", 0), 0),
        ])
        expense_items = data.get("expenses", [
            ("Housing (rent/mortgage)", data.get("housing", 0), data.get("housing_budget", 0)),
            ("Utilities", data.get("utilities", 0), data.get("utilities_budget", 0)),
            ("Groceries", data.get("groceries", 0), data.get("groceries_budget", 0)),
            ("Transportation", data.get("transportation", 0), data.get("transportation_budget", 0)),
            ("Insurance", data.get("insurance", 0), data.get("insurance_budget", 0)),
            ("Healthcare", data.get("healthcare", 0), data.get("healthcare_budget", 0)),
            ("Subscriptions", data.get("subscriptions", 0), data.get("subscriptions_budget", 0)),
            ("Entertainment", data.get("entertainment", 0), data.get("entertainment_budget", 0)),
            ("Savings/Investments", data.get("savings_expense", 0), data.get("savings_budget", 0)),
            ("Debt Payments", data.get("debt_payments", 0), data.get("debt_budget", 0)),
            ("Other Expenses", data.get("other_expenses", 0), 0),
        ])

        def calc_totals(items):
            return (
                sum(float(a or 0) for _, a, _ in items),
                sum(float(b or 0) for _, _, b in items),
            )

        total_income_actual, total_income_budget = calc_totals(income_items)
        total_expense_actual, total_expense_budget = calc_totals(expense_items)
        net_actual = total_income_actual - total_expense_actual
        net_budget = total_income_budget - total_expense_budget

        col1, col2, col3, col4 = 30, 14, 14, 10

        def header_row():
            return "║  " + "CATEGORY".ljust(col1) + "ACTUAL".rjust(col2) + "BUDGET".rjust(col3) + "VARIANCE".rjust(col4) + "  ║"

        def data_row(label, actual, budget):
            var = float(actual or 0) - float(budget or 0)
            var_str = (("+" if var >= 0 else "") + f"${abs(var):,.0f}").rjust(col4)
            return "║  " + label[:col1].ljust(col1) + _fmt_currency(actual, col2) + _fmt_currency(budget, col3) + var_str + "  ║"

        def total_row(label, actual, budget):
            var = float(actual or 0) - float(budget or 0)
            var_str = (("+" if var >= 0 else "") + f"${abs(var):,.0f}").rjust(col4)
            return "╠══" + ("═" * col1) + ("═" * col2) + ("═" * col3) + ("═" * col4) + "══╣\n" + \
                   "║  " + label[:col1].ljust(col1) + _fmt_currency(actual, col2) + _fmt_currency(budget, col3) + var_str + "  ║"

        lines = []
        lines.append(_box_title(f"MONTHLY CASH FLOW ANALYSIS — {name}", f"Period: {period}", W))
        lines.append(header_row())
        lines.append("╠══" + "═" * col1 + "═" * col2 + "═" * col3 + "═" * col4 + "══╣")
        lines.append("║  " + "INCOME".ljust(W - 6) + "  ║")
        lines.append("╠══" + "═" * col1 + "═" * col2 + "═" * col3 + "═" * col4 + "══╣")

        for label, actual, budget in income_items:
            lines.append(data_row(label, actual, budget))

        lines.append(total_row("TOTAL INCOME", total_income_actual, total_income_budget))
        lines.append("║  " + "EXPENSES".ljust(W - 6) + "  ║")
        lines.append("╠══" + "═" * col1 + "═" * col2 + "═" * col3 + "═" * col4 + "══╣")

        for label, actual, budget in expense_items:
            lines.append(data_row(label, actual, budget))

        lines.append(total_row("TOTAL EXPENSES", total_expense_actual, total_expense_budget))
        lines.append(total_row("NET CASH FLOW", net_actual, net_budget))
        lines.append(_box_bot(W))

        savings_rate = (net_actual / total_income_actual * 100) if total_income_actual else 0
        lines.append(f"\n  Savings Rate: {savings_rate:.1f}%")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Loan Proposal
    # ------------------------------------------------------------------

    def loan_proposal(self, business: Dict[str, Any], loan_request: Dict[str, Any]) -> str:
        """Generate a compelling bank loan package."""
        W = self.WIDTH
        company = business.get("name", "[COMPANY NAME]")
        owner = business.get("owner", "[OWNER NAME]")
        business_type = business.get("type", "[BUSINESS TYPE]")
        years_in_business = business.get("years", "[NUMBER]")
        annual_revenue = business.get("annual_revenue", 0)
        annual_profit = business.get("annual_profit", 0)
        employees = business.get("employees", 0)
        address = business.get("address", "[ADDRESS]")
        ein = business.get("ein", "[EIN]")

        loan_amount = loan_request.get("amount", 0)
        loan_purpose = loan_request.get("purpose", "[LOAN PURPOSE]")
        term_years = loan_request.get("term_years", "[NUMBER]")
        requested_rate = loan_request.get("requested_rate", "[RATE]")
        collateral = loan_request.get("collateral", "[COLLATERAL DESCRIPTION]")
        dsrc = loan_request.get("dsrc", "[DSRC RATIO]")

        lines = []
        lines.append(_box_title(f"BUSINESS LOAN PROPOSAL", f"{company.upper()} — SBA/BANK FINANCING REQUEST", W))
        lines.append(_box_row(f"  Owner:                {owner}", W))
        lines.append(_box_row(f"  Business:             {company}", W))
        lines.append(_box_row(f"  Business Type:        {business_type}", W))
        lines.append(_box_row(f"  EIN:                  {ein}", W))
        lines.append(_box_row(f"  Years in Business:    {years_in_business}", W))
        lines.append(_box_row(f"  Employees:            {employees}", W))
        lines.append(_box_row(f"  Address:              {address}", W))
        lines.append(_box_mid(W))
        lines.append(_box_row(_center("LOAN REQUEST", W - 4), W))
        lines.append(_box_mid(W))
        lines.append(_box_row(f"  Loan Amount Requested:{_fmt_currency(loan_amount, 16)}", W))
        lines.append(_box_row(f"  Purpose:              {loan_purpose}", W))
        lines.append(_box_row(f"  Requested Term:       {term_years} years", W))
        lines.append(_box_row(f"  Requested Rate:       {requested_rate}%", W))
        lines.append(_box_row(f"  Proposed Collateral:  {collateral}", W))
        lines.append(_box_mid(W))
        lines.append(_box_row(_center("FINANCIAL SUMMARY", W - 4), W))
        lines.append(_box_mid(W))
        lines.append(_box_row(f"  Annual Revenue:       {_fmt_currency(annual_revenue, 16)}", W))
        lines.append(_box_row(f"  Annual Net Profit:    {_fmt_currency(annual_profit, 16)}", W))
        lines.append(_box_row(f"  Debt Service Coverage Ratio: {dsrc}", W))
        lines.append(_box_mid(W))
        lines.append(_box_row("USE OF FUNDS", W))
        lines.append(_box_mid(W))
        for use in loan_request.get("use_of_funds", [("[DESCRIBE USE]", loan_amount)]):
            label, amount = use if isinstance(use, (list, tuple)) else (use, "")
            lines.append(_box_row(f"  {label:<40}{_fmt_currency(amount, 16)}", W))
        lines.append(_box_bot(W))

        lines.append("\nEXECUTIVE SUMMARY:")
        lines.append(business.get("executive_summary",
            f"{company} is a {business_type} with {years_in_business} years of proven operations. "
            f"We are requesting ${loan_amount:,.0f} to {loan_purpose}. "
            "Management is committed to timely repayment as evidenced by our financial history."))
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Investor Pitch Financial Model
    # ------------------------------------------------------------------

    def investor_pitch_financial_model(self, startup: Dict[str, Any]) -> str:
        """Generate 3-year financial projections for investor pitch."""
        W = self.WIDTH
        company = startup.get("name", "[STARTUP NAME]")
        tagline = startup.get("tagline", "[COMPANY TAGLINE]")
        date = datetime.now().strftime("%B %Y")

        years = [
            startup.get("year1", "Year 1"),
            startup.get("year2", "Year 2"),
            startup.get("year3", "Year 3"),
        ]

        metrics = [
            ("Revenue", startup.get("revenue", [0, 0, 0])),
            ("Gross Profit", startup.get("gross_profit", [0, 0, 0])),
            ("Operating Expenses", startup.get("opex", [0, 0, 0])),
            ("EBITDA", startup.get("ebitda", [0, 0, 0])),
            ("Net Income / (Loss)", startup.get("net_income", [0, 0, 0])),
            ("Customers/Units", startup.get("customers", [0, 0, 0])),
            ("MRR (Monthly Recurring Revenue)", startup.get("mrr", [0, 0, 0])),
            ("Burn Rate / Month", startup.get("burn_rate", [0, 0, 0])),
            ("Runway (Months)", startup.get("runway", [0, 0, 0])),
        ]

        col0 = 32
        col1 = 12

        def header():
            h = "║  " + "METRIC".ljust(col0)
            for y in years:
                h += str(y).rjust(col1)
            h += "  ║"
            return h

        def metric_row(label, values):
            r = "║  " + label[:col0].ljust(col0)
            for v in values:
                try:
                    r += _fmt_currency(v, col1)
                except Exception:
                    r += str(v).rjust(col1)
            r += "  ║"
            return r

        sep = "╠══" + "═" * col0 + "═" * col1 * len(years) + "══╣"

        lines = []
        lines.append(_box_title(company.upper(), f"{tagline} — 3-YEAR FINANCIAL PROJECTIONS ({date})", W))
        lines.append(header())
        lines.append(sep)
        for label, values in metrics:
            lines.append(metric_row(label, values))
        lines.append(_box_bot(W))

        lines.append("\nKEY ASSUMPTIONS:")
        for assumption in startup.get("assumptions", ["[DESCRIBE KEY ASSUMPTIONS]"]):
            lines.append(f"  • {assumption}")

        lines.append("\nFUNDING SOUGHT:")
        lines.append(f"  Amount:    {_fmt_currency(startup.get('raise', 0))}")
        lines.append(f"  Use:       {startup.get('use_of_funds', '[DESCRIBE]')}")
        lines.append(f"  Valuation: {_fmt_currency(startup.get('valuation', 0))}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Tax Planning Summary
    # ------------------------------------------------------------------

    def tax_planning_summary(self, profile: Dict[str, Any]) -> str:
        """Generate an annual tax strategy document."""
        W = self.WIDTH
        name = data = profile
        taxpayer = profile.get("name", "[TAXPAYER NAME]")
        filing_status = profile.get("filing_status", "[FILING STATUS]")
        tax_year = profile.get("tax_year", str(datetime.now().year))
        advisor = profile.get("advisor", "[TAX ADVISOR NAME / CPA]")

        w2_income = profile.get("w2_income", 0)
        business_income = profile.get("business_income", 0)
        investment_income = profile.get("investment_income", 0)
        other_income = profile.get("other_income", 0)
        total_income = w2_income + business_income + investment_income + other_income

        # Deductions
        std_deduction = profile.get("std_deduction", 0)
        itemized = profile.get("itemized_deductions", 0)
        best_deduction = max(std_deduction, itemized)
        deduction_type = "Itemized" if itemized > std_deduction else "Standard"

        qbi_deduction = profile.get("qbi_deduction", 0)  # Section 199A
        taxable_income = total_income - best_deduction - qbi_deduction

        est_fed_tax = profile.get("estimated_federal_tax", 0)
        est_state_tax = profile.get("estimated_state_tax", 0)
        est_se_tax = profile.get("estimated_se_tax", 0)
        total_tax = est_fed_tax + est_state_tax + est_se_tax
        eff_rate = (total_tax / total_income * 100) if total_income else 0

        strategies = profile.get("strategies", [
            "Maximize 401(k)/IRA contributions ($[AMOUNT] remaining)",
            "Consider HSA contribution ($[AMOUNT] deductible)",
            "Harvest tax losses in brokerage account",
            "Review QBI deduction eligibility (Section 199A)",
            "Estimated quarterly payments due: [DATES]",
            "Consider Roth conversion if in lower bracket",
        ])

        lines = []
        lines.append(_box_title(f"TAX PLANNING SUMMARY — {tax_year}", taxpayer, W))
        lines.append(_box_row(f"  Filing Status: {filing_status:<30} Prepared by: {advisor}", W))
        lines.append(_box_mid(W))
        lines.append(_box_row(_center("INCOME ANALYSIS", W - 4), W))
        lines.append(_box_mid(W))

        def irow(label, val):
            return _box_row(f"  {label:<40}{_fmt_currency(val, 16)}", W)

        lines.append(irow("W-2 Wages and Salaries", w2_income))
        lines.append(irow("Business/Self-Employment Income", business_income))
        lines.append(irow("Investment Income (dividends/interest/gains)", investment_income))
        lines.append(irow("Other Income", other_income))
        lines.append(_box_row("  " + "─" * (W - 6), W))
        lines.append(irow("TOTAL GROSS INCOME", total_income))
        lines.append(_box_mid(W))
        lines.append(_box_row(_center("DEDUCTIONS", W - 4), W))
        lines.append(_box_mid(W))
        lines.append(_box_row(f"  Standard Deduction: {_fmt_currency(std_deduction, 16)}", W))
        lines.append(_box_row(f"  Itemized Deductions: {_fmt_currency(itemized, 16)}", W))
        lines.append(_box_row(f"  → Using: {deduction_type} Deduction: {_fmt_currency(best_deduction, 14)}", W))
        lines.append(irow("QBI Deduction (Sec. 199A)", qbi_deduction))
        lines.append(_box_row("  " + "─" * (W - 6), W))
        lines.append(irow("ESTIMATED TAXABLE INCOME", taxable_income))
        lines.append(_box_mid(W))
        lines.append(_box_row(_center("TAX ESTIMATES", W - 4), W))
        lines.append(_box_mid(W))
        lines.append(irow("Federal Income Tax (estimated)", est_fed_tax))
        lines.append(irow("State Income Tax (estimated)", est_state_tax))
        lines.append(irow("Self-Employment Tax (estimated)", est_se_tax))
        lines.append(_box_row("  " + "═" * (W - 6), W))
        lines.append(irow("TOTAL ESTIMATED TAX LIABILITY", total_tax))
        lines.append(_box_row(f"  Effective Tax Rate: {eff_rate:.1f}%", W))
        lines.append(_box_mid(W))
        lines.append(_box_row(_center("TAX REDUCTION STRATEGIES", W - 4), W))
        lines.append(_box_mid(W))
        for s in strategies:
            lines.append(_box_row(f"  ✓ {s}", W))
        lines.append(_box_bot(W))
        lines.append("\nDISCLAIMER: This summary is for informational and planning purposes only.")
        lines.append("Consult your CPA or tax attorney for personalized advice.")
        return "\n".join(lines)
