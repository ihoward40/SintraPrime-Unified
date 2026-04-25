"""
Net Worth Report Generator — Formatted net worth snapshots with trend visualization data.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..net_worth_calculator import NetWorthReport

logger = logging.getLogger(__name__)


class NetWorthReportGenerator:
    """
    Generates formatted net worth reports in HTML and Markdown.
    """

    def to_html(self, report: NetWorthReport, entity_name: str = "Client") -> str:
        peer = report.peer_benchmark or {}
        fire = report.fire_analysis or {}

        if report.net_worth_growth_12m is not None:
            trend = f"+${report.net_worth_growth_12m:,.0f} (+{report.net_worth_growth_pct:.1f}%) vs 12 months ago"
        else:
            trend = "Insufficient history for trend"

        asset_rows = "\n".join(
            "<tr>"
            f"<td>{a.name}</td>"
            f"<td>{a.asset_type.value.replace('_', ' ').title()}</td>"
            f"<td style='text-align:right'>${a.current_value:,.2f}</td>"
            "</tr>"
            for a in report.assets
        )
        liability_rows = "\n".join(
            "<tr>"
            f"<td>{lb.name}</td>"
            f"<td>{lb.liability_type.value.replace('_', ' ').title()}</td>"
            f"<td style='text-align:right;color:red'>(${lb.current_balance:,.2f})</td>"
            "</tr>"
            for lb in report.liabilities
        )

        peer_section = ""
        if peer:
            summary = peer.get("summary", "")
            peer_section = f"<p><strong>Peer Benchmark:</strong> {summary}</p>"

        fire_section = ""
        if fire:
            fire_number = fire.get("fire_number", 0)
            investable = fire.get("current_investable_assets", 0)
            pct = fire.get("pct_of_fire_goal", 0)
            fire_age = fire.get("projected_fire_age", "N/A")
            fire_section = (
                "<h3>FIRE Analysis</h3>"
                "<table>"
                "<tr><td>FIRE Number (25x annual expenses)</td>"
                f"<td style='text-align:right'>${fire_number:,.0f}</td></tr>"
                "<tr><td>Current Investable Assets</td>"
                f"<td style='text-align:right'>${investable:,.0f}</td></tr>"
                "<tr><td>Progress to FIRE</td>"
                f"<td style='text-align:right'>{pct:.1f}%</td></tr>"
                "<tr><td>Projected FIRE Age</td>"
                f"<td style='text-align:right'>{fire_age}</td></tr>"
                "</table>"
            )

        prepared = report.calculated_at.strftime("%B %d, %Y")
        nw = report.net_worth
        ta = report.total_assets
        tl = report.total_liabilities
        la = report.liquid_assets

        return (
            "<!DOCTYPE html>\n"
            "<html lang='en'>\n"
            "<head><meta charset='UTF-8'/>"
            f"<title>Net Worth Report - {entity_name}</title>\n"
            "<style>\n"
            "  body { font-family: Arial, sans-serif; font-size: 13px; color: #222; margin: 40px; }\n"
            "  .kpi { display: inline-block; background: #f0f4ff; border-radius: 8px; padding: 16px 24px; margin: 8px; text-align: center; }\n"
            "  .kpi-value { font-size: 24px; font-weight: bold; color: #1a1a2e; }\n"
            "  table { width: 100%; border-collapse: collapse; max-width: 800px; margin-top: 16px; }\n"
            "  th { background: #1a1a2e; color: white; padding: 8px; text-align: left; }\n"
            "  td { padding: 6px 8px; border-bottom: 1px solid #eee; }\n"
            "  .total-row { font-weight: bold; background: #f0f4ff; }\n"
            "</style>\n"
            "</head>\n"
            "<body>\n"
            f"<h2>{entity_name} - Net Worth Report</h2>\n"
            f"<p>As of {prepared}</p>\n"
            "<div>\n"
            f"  <div class='kpi'><div class='kpi-value'>${nw:,.0f}</div><div>Net Worth</div></div>\n"
            f"  <div class='kpi'><div class='kpi-value'>${ta:,.0f}</div><div>Total Assets</div></div>\n"
            f"  <div class='kpi'><div class='kpi-value' style='color:red'>(${tl:,.0f})</div><div>Total Liabilities</div></div>\n"
            f"  <div class='kpi'><div class='kpi-value'>${la:,.0f}</div><div>Liquid Assets</div></div>\n"
            "</div>\n"
            f"<p><strong>12-Month Trend:</strong> {trend}</p>\n"
            f"{peer_section}\n"
            "<h3>Assets</h3>\n"
            "<table>\n"
            "  <thead><tr><th>Asset</th><th>Type</th><th>Value</th></tr></thead>\n"
            "  <tbody>\n"
            f"    {asset_rows}\n"
            f"    <tr class='total-row'><td colspan='2'>Total Assets</td><td style='text-align:right'>${ta:,.2f}</td></tr>\n"
            "  </tbody>\n"
            "</table>\n"
            "<h3>Liabilities</h3>\n"
            "<table>\n"
            "  <thead><tr><th>Liability</th><th>Type</th><th>Balance</th></tr></thead>\n"
            "  <tbody>\n"
            f"    {liability_rows}\n"
            f"    <tr class='total-row'><td colspan='2'>Total Liabilities</td><td style='text-align:right;color:red'>(${tl:,.2f})</td></tr>\n"
            "  </tbody>\n"
            "</table>\n"
            f"{fire_section}\n"
            "<p style='margin-top:30px;font-size:11px;color:#888'>\n"
            "  Prepared by SintraPrime Financial Intelligence. Data sourced from Plaid. For informational purposes only.\n"
            "</p>\n"
            "</body>\n"
            "</html>"
        )

    def to_markdown(self, report: NetWorthReport, entity_name: str = "Client") -> str:
        prepared = report.calculated_at.strftime("%B %d, %Y")
        lines = [
            f"# {entity_name} - Net Worth Report",
            f"*As of {prepared}*",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| **Net Worth** | **${report.net_worth:,.2f}** |",
            f"| Total Assets | ${report.total_assets:,.2f} |",
            f"| Total Liabilities | (${report.total_liabilities:,.2f}) |",
            f"| Liquid Assets | ${report.liquid_assets:,.2f} |",
            "",
            "## Assets",
            "| Asset | Type | Value |",
            "|-------|------|-------|",
        ]
        for a in report.assets:
            lines.append(f"| {a.name} | {a.asset_type.value} | ${a.current_value:,.2f} |")
        lines.append(f"| **Total** | | **${report.total_assets:,.2f}** |")

        lines += [
            "",
            "## Liabilities",
            "| Liability | Type | Balance |",
            "|-----------|------|---------|",
        ]
        for lb in report.liabilities:
            lines.append(f"| {lb.name} | {lb.liability_type.value} | (${lb.current_balance:,.2f}) |")
        lines.append(f"| **Total** | | **(${report.total_liabilities:,.2f})** |")

        return "\n".join(lines)
