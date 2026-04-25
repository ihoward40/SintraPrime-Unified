"""
Tax Summary Report — Annual tax summary with deductions, savings opportunities, and strategies.
"""

import logging
from datetime import datetime
from typing import Optional

from ..tax_optimizer import TaxOptimizationReport

logger = logging.getLogger(__name__)


class TaxSummaryReport:
    """
    Generates formatted tax summary reports for clients and CPAs.
    """

    def to_html(
        self,
        report: TaxOptimizationReport,
        entity_name: str = "Client",
    ) -> str:
        deduction_rows = "\n".join(
            f"<tr><td>{d.deduction_name}</td><td>${d.estimated_amount:,.2f}</td><td style='color:green'>${d.tax_savings_estimate:,.2f}</td><td>{d.action_required[:80]}</td></tr>"
            for d in report.deduction_opportunities if d.estimated_amount > 0
        )

        tlh_rows = "\n".join(
            f"<tr><td>{t.ticker or t.security_name}</td><td style='color:red'>(${abs(t.unrealized_loss):,.2f})</td><td style='color:green'>${t.tax_savings_estimate:,.2f}</td></tr>"
            for t in report.tax_loss_opportunities
        )

        acct_recs = "\n".join(f"<li>{r}</li>" for r in report.account_recommendations)

        return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><title>Tax Summary {report.tax_year} — {entity_name}</title>
<style>
  body {{ font-family: Arial, sans-serif; font-size: 13px; color: #222; margin: 40px; }}
  .kpi {{ display: inline-block; background: #f0fff4; border-radius: 8px; padding: 16px 24px; margin: 8px; text-align: center; }}
  .kpi-value {{ font-size: 22px; font-weight: bold; color: #27ae60; }}
  table {{ width: 100%; border-collapse: collapse; max-width: 900px; margin-top: 16px; }}
  th {{ background: #1a1a2e; color: white; padding: 8px; text-align: left; }}
  td {{ padding: 6px 8px; border-bottom: 1px solid #eee; }}
</style>
</head>
<body>
<h2>{entity_name} — Tax Optimization Report {report.tax_year}</h2>
<p>Filing Status: <strong>{report.filing_status.value.replace('_',' ').title()}</strong> &nbsp;|&nbsp;
   Marginal Rate: <strong>{report.marginal_rate*100:.0f}%</strong> &nbsp;|&nbsp;
   Estimated AGI: <strong>${report.estimated_agi:,.0f}</strong></p>

<div>
  <div class="kpi">
    <div class="kpi-value">${report.total_tax_savings_identified:,.0f}</div>
    <div>Total Savings Identified</div>
  </div>
  <div class="kpi">
    <div class="kpi-value">${report.total_deductible_expenses:,.0f}</div>
    <div>Deductible Expenses Found</div>
  </div>
</div>

<h3>Deduction Opportunities</h3>
<table>
  <thead><tr><th>Deduction</th><th>Estimated Amount</th><th>Tax Savings</th><th>Action Required</th></tr></thead>
  <tbody>{deduction_rows}</tbody>
</table>

{f'''<h3>Tax-Loss Harvesting Opportunities</h3>
<table>
  <thead><tr><th>Security</th><th>Unrealized Loss</th><th>Tax Savings</th></tr></thead>
  <tbody>{tlh_rows}</tbody>
</table>''' if tlh_rows else ''}

<h3>Account & Strategy Recommendations</h3>
<ul>{acct_recs}</ul>

<p style="margin-top:30px;font-size:11px;color:#888">
  {report.summary}<br/>
  This report is for informational purposes. Consult a CPA for personalized tax advice.
</p>
</body>
</html>"""

    def to_cpa_summary(self, report: TaxOptimizationReport, entity_name: str = "Client") -> str:
        """Generate a CPA-ready Markdown summary."""
        lines = [
            f"# Tax Summary {report.tax_year} — {entity_name}",
            f"**Filing Status:** {report.filing_status.value}  ",
            f"**Estimated AGI:** ${report.estimated_agi:,.2f}  ",
            f"**Marginal Rate:** {report.marginal_rate*100:.0f}%  ",
            f"**Potential Savings Identified:** ${report.total_tax_savings_identified:,.2f}",
            "",
            "## Key Deductions to Review",
        ]
        for d in report.deduction_opportunities:
            if d.estimated_amount > 0:
                lines.append(f"- **{d.deduction_name}**: ${d.estimated_amount:,.2f} → Est. savings ${d.tax_savings_estimate:,.2f}")
                lines.append(f"  - Action: {d.action_required}")

        if report.tax_loss_opportunities:
            lines += ["", "## Tax-Loss Harvesting"]
            for t in report.tax_loss_opportunities:
                lines.append(f"- {t.ticker or t.security_name}: Unrealized loss ${abs(t.unrealized_loss):,.2f} → Est. savings ${t.tax_savings_estimate:,.2f}")

        lines += ["", "## Strategic Recommendations"]
        for r in report.account_recommendations:
            lines.append(f"- {r}")

        lines += ["", "*Data sourced from bank and investment accounts via Plaid. Consult CPA for filing.*"]
        return "\n".join(lines)
