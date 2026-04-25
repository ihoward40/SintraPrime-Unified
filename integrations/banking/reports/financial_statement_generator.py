"""
Financial Statement Generator — GAAP-compliant P&L, Balance Sheet, Cash Flow Statements.
Produces HTML, PDF-ready, and Excel-compatible outputs.
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class StatementPeriod(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    YTD = "ytd"
    CUSTOM = "custom"


class StatementFormat(str, Enum):
    HTML = "html"
    JSON = "json"
    MARKDOWN = "markdown"
    CSV = "csv"


class LineItem(BaseModel):
    label: str
    amount: float
    is_subtotal: bool = False
    is_total: bool = False
    is_negative: bool = False
    indent_level: int = 0
    note: Optional[str] = None


class FinancialStatement(BaseModel):
    title: str
    entity_name: str
    period: str
    prepared_date: date = Field(default_factory=date.today)
    currency: str = "USD"
    line_items: List[LineItem] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    disclaimer: str = "Prepared from bank and investment data via Plaid. For management use only."


class ProfitLossStatement(FinancialStatement):
    total_revenue: float = 0.0
    total_cogs: float = 0.0
    gross_profit: float = 0.0
    gross_margin_pct: float = 0.0
    total_operating_expenses: float = 0.0
    ebitda: float = 0.0
    net_income: float = 0.0
    net_margin_pct: float = 0.0


class BalanceSheet(FinancialStatement):
    total_assets: float = 0.0
    total_liabilities: float = 0.0
    total_equity: float = 0.0
    is_balanced: bool = True


class CashFlowStatement(FinancialStatement):
    operating_activities: float = 0.0
    investing_activities: float = 0.0
    financing_activities: float = 0.0
    net_change_in_cash: float = 0.0
    beginning_cash: float = 0.0
    ending_cash: float = 0.0


class FinancialStatementGenerator:
    """
    Generates GAAP-structured financial statements from transaction and balance data.
    """

    def generate_pnl(
        self,
        entity_name: str,
        period_label: str,
        revenue_by_stream: Dict[str, float],
        cogs_by_category: Dict[str, float],
        opex_by_category: Dict[str, float],
        other_income: Optional[Dict[str, float]] = None,
        depreciation: float = 0.0,
        taxes: float = 0.0,
    ) -> ProfitLossStatement:
        """Generate a Profit & Loss statement."""
        total_revenue = sum(revenue_by_stream.values())
        total_cogs = sum(cogs_by_category.values())
        gross_profit = total_revenue - total_cogs
        gross_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0.0

        total_opex = sum(opex_by_category.values())
        total_other = sum((other_income or {}).values())
        ebitda = gross_profit - total_opex + total_other
        net_income = ebitda - depreciation - taxes

        lines: List[LineItem] = []

        # Revenue section
        lines.append(LineItem(label="REVENUE", amount=0, is_subtotal=True))
        for name, amount in revenue_by_stream.items():
            lines.append(LineItem(label=name, amount=amount, indent_level=1))
        if other_income:
            for name, amount in other_income.items():
                lines.append(LineItem(label=name, amount=amount, indent_level=1))
        lines.append(LineItem(label="Total Revenue", amount=round(total_revenue + total_other, 2), is_subtotal=True))

        # COGS section
        lines.append(LineItem(label="COST OF GOODS SOLD", amount=0, is_subtotal=True))
        for name, amount in cogs_by_category.items():
            lines.append(LineItem(label=name, amount=amount, indent_level=1, is_negative=True))
        lines.append(LineItem(label="Total COGS", amount=round(total_cogs, 2), is_subtotal=True, is_negative=True))

        # Gross Profit
        lines.append(LineItem(
            label=f"GROSS PROFIT ({gross_margin:.1f}% margin)",
            amount=round(gross_profit, 2),
            is_subtotal=True,
        ))

        # Operating Expenses
        lines.append(LineItem(label="OPERATING EXPENSES", amount=0, is_subtotal=True))
        for name, amount in opex_by_category.items():
            lines.append(LineItem(label=name, amount=amount, indent_level=1, is_negative=True))
        if depreciation > 0:
            lines.append(LineItem(label="Depreciation & Amortization", amount=depreciation, indent_level=1, is_negative=True))
        lines.append(LineItem(label="Total Operating Expenses", amount=round(total_opex + depreciation, 2), is_subtotal=True, is_negative=True))

        # EBITDA
        lines.append(LineItem(label="EBITDA", amount=round(ebitda, 2), is_subtotal=True))

        # Taxes
        if taxes > 0:
            lines.append(LineItem(label="Income Tax Provision", amount=taxes, is_negative=True))

        # Net Income
        lines.append(LineItem(label="NET INCOME", amount=round(net_income, 2), is_total=True))

        stmt = ProfitLossStatement(
            title="Profit & Loss Statement",
            entity_name=entity_name,
            period=period_label,
            line_items=lines,
            total_revenue=round(total_revenue, 2),
            total_cogs=round(total_cogs, 2),
            gross_profit=round(gross_profit, 2),
            gross_margin_pct=round(gross_margin, 2),
            total_operating_expenses=round(total_opex, 2),
            ebitda=round(ebitda, 2),
            net_income=round(net_income, 2),
            net_margin_pct=round((net_income / (total_revenue + total_other) * 100) if total_revenue > 0 else 0, 2),
        )
        return stmt

    def generate_balance_sheet(
        self,
        entity_name: str,
        as_of_date: date,
        assets: Dict[str, Dict[str, float]],  # {"Current Assets": {"Cash": 50000, ...}, ...}
        liabilities: Dict[str, Dict[str, float]],
        equity: Dict[str, float],
    ) -> BalanceSheet:
        """Generate a GAAP Balance Sheet."""
        lines: List[LineItem] = []
        total_assets = 0.0

        # Assets
        lines.append(LineItem(label="ASSETS", amount=0, is_subtotal=True))
        for section, items in assets.items():
            lines.append(LineItem(label=section, amount=0, is_subtotal=True, indent_level=1))
            section_total = 0.0
            for name, amount in items.items():
                lines.append(LineItem(label=name, amount=amount, indent_level=2))
                section_total += amount
            lines.append(LineItem(label=f"Total {section}", amount=round(section_total, 2), is_subtotal=True, indent_level=1))
            total_assets += section_total

        lines.append(LineItem(label="TOTAL ASSETS", amount=round(total_assets, 2), is_total=True))

        # Liabilities
        lines.append(LineItem(label="LIABILITIES", amount=0, is_subtotal=True))
        total_liabilities = 0.0
        for section, items in liabilities.items():
            lines.append(LineItem(label=section, amount=0, is_subtotal=True, indent_level=1))
            section_total = 0.0
            for name, amount in items.items():
                lines.append(LineItem(label=name, amount=amount, indent_level=2))
                section_total += amount
            lines.append(LineItem(label=f"Total {section}", amount=round(section_total, 2), is_subtotal=True, indent_level=1))
            total_liabilities += section_total

        lines.append(LineItem(label="TOTAL LIABILITIES", amount=round(total_liabilities, 2), is_subtotal=True))

        # Equity
        lines.append(LineItem(label="EQUITY", amount=0, is_subtotal=True))
        total_equity = 0.0
        for name, amount in equity.items():
            lines.append(LineItem(label=name, amount=amount, indent_level=1))
            total_equity += amount
        lines.append(LineItem(label="TOTAL EQUITY", amount=round(total_equity, 2), is_subtotal=True))

        total_liabilities_equity = total_liabilities + total_equity
        lines.append(LineItem(label="TOTAL LIABILITIES + EQUITY", amount=round(total_liabilities_equity, 2), is_total=True))

        is_balanced = abs(total_assets - total_liabilities_equity) < 1.0

        return BalanceSheet(
            title="Balance Sheet",
            entity_name=entity_name,
            period=f"As of {as_of_date.strftime('%B %d, %Y')}",
            line_items=lines,
            total_assets=round(total_assets, 2),
            total_liabilities=round(total_liabilities, 2),
            total_equity=round(total_equity, 2),
            is_balanced=is_balanced,
        )

    def generate_cash_flow(
        self,
        entity_name: str,
        period_label: str,
        operating_items: Dict[str, float],
        investing_items: Dict[str, float],
        financing_items: Dict[str, float],
        beginning_cash: float,
    ) -> CashFlowStatement:
        """Generate an indirect method Cash Flow Statement."""
        lines: List[LineItem] = []

        def add_section(section_title: str, items: Dict[str, float]) -> float:
            lines.append(LineItem(label=section_title, amount=0, is_subtotal=True))
            total = 0.0
            for name, amount in items.items():
                lines.append(LineItem(label=name, amount=amount, indent_level=1, is_negative=amount < 0))
                total += amount
            lines.append(LineItem(label=f"Net Cash from {section_title}", amount=round(total, 2), is_subtotal=True))
            return total

        op_total = add_section("Operating Activities", operating_items)
        inv_total = add_section("Investing Activities", investing_items)
        fin_total = add_section("Financing Activities", financing_items)

        net_change = op_total + inv_total + fin_total
        ending_cash = beginning_cash + net_change

        lines.append(LineItem(label="Net Increase (Decrease) in Cash", amount=round(net_change, 2), is_subtotal=True))
        lines.append(LineItem(label="Beginning Cash Balance", amount=round(beginning_cash, 2)))
        lines.append(LineItem(label="ENDING CASH BALANCE", amount=round(ending_cash, 2), is_total=True))

        return CashFlowStatement(
            title="Statement of Cash Flows",
            entity_name=entity_name,
            period=period_label,
            line_items=lines,
            operating_activities=round(op_total, 2),
            investing_activities=round(inv_total, 2),
            financing_activities=round(fin_total, 2),
            net_change_in_cash=round(net_change, 2),
            beginning_cash=round(beginning_cash, 2),
            ending_cash=round(ending_cash, 2),
        )

    def to_html(
        self,
        statement: FinancialStatement,
        brand_color: str = "#1a1a2e",
        logo_url: Optional[str] = None,
    ) -> str:
        """Render a financial statement as beautifully formatted HTML."""
        rows = []
        for item in statement.line_items:
            indent = "&nbsp;" * (item.indent_level * 4)
            style = ""
            if item.is_total:
                style = "font-weight:bold;border-top:2px solid #333;border-bottom:3px double #333;"
            elif item.is_subtotal:
                style = "font-weight:bold;border-top:1px solid #ccc;"
            amount_str = f"${abs(item.amount):,.2f}" if item.amount != 0 else ""
            if item.is_negative and item.amount > 0:
                amount_str = f"(${item.amount:,.2f})"
            color = "red" if item.is_negative else "inherit"
            rows.append(
                f"<tr style='{style}'>"
                f"<td style='padding:4px 8px;'>{indent}{item.label}</td>"
                f"<td style='text-align:right;padding:4px 8px;color:{color};'>{amount_str}</td>"
                f"</tr>"
            )

        rows_html = "\n".join(rows)
        logo_tag = f'<img src="{logo_url}" height="40" style="margin-bottom:10px;"/><br/>' if logo_url else ""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>{statement.title} — {statement.entity_name}</title>
  <style>
    body {{ font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 13px; color: #222; margin: 40px; }}
    .header {{ background: {brand_color}; color: white; padding: 20px 30px; border-radius: 6px; margin-bottom: 24px; }}
    table {{ width: 100%; border-collapse: collapse; max-width: 800px; }}
    tr:nth-child(even) {{ background: #f8f9fa; }}
    .footer {{ margin-top: 30px; font-size: 11px; color: #888; }}
  </style>
</head>
<body>
  <div class="header">
    {logo_tag}
    <h2 style="margin:0">{statement.entity_name}</h2>
    <h3 style="margin:4px 0 0">{statement.title}</h3>
    <p style="margin:4px 0 0;opacity:0.8">{statement.period} &nbsp;|&nbsp; Prepared {statement.prepared_date.strftime('%B %d, %Y')}</p>
  </div>
  <table>
    {rows_html}
  </table>
  <div class="footer">
    <p>{statement.disclaimer}</p>
    {''.join(f'<p><small>Note: {n}</small></p>' for n in statement.notes)}
  </div>
</body>
</html>"""

    def to_markdown(self, statement: FinancialStatement) -> str:
        """Render statement as Markdown table."""
        lines = [
            f"# {statement.entity_name}",
            f"## {statement.title}",
            f"**Period:** {statement.period}  ",
            f"**Prepared:** {statement.prepared_date.strftime('%B %d, %Y')}",
            "",
            "| Line Item | Amount |",
            "|-----------|--------|",
        ]
        for item in statement.line_items:
            indent = "  " * item.indent_level
            label = f"**{item.label}**" if item.is_total or item.is_subtotal else item.label
            amount = f"${item.amount:,.2f}" if item.amount != 0 else ""
            lines.append(f"| {indent}{label} | {amount} |")
        lines.append(f"\n*{statement.disclaimer}*")
        return "\n".join(lines)
