"""
Credit Report Analyzer — Formatted credit intelligence reports with score visualizations.
"""

import logging
from datetime import datetime
from typing import Optional

from ..credit_intelligence import CreditReport, CreditImprovementPlan

logger = logging.getLogger(__name__)


class CreditReportAnalyzer:
    """
    Formats credit intelligence data into polished reports.
    """

    SCORE_COLOR_MAP = [
        (800, "#27ae60"),   # Exceptional — green
        (740, "#2ecc71"),   # Very Good
        (670, "#f39c12"),   # Good — orange
        (580, "#e67e22"),   # Fair
        (0,   "#e74c3c"),   # Poor — red
    ]

    def _score_color(self, score: Optional[int]) -> str:
        if not score:
            return "#95a5a6"
        for threshold, color in self.SCORE_COLOR_MAP:
            if score >= threshold:
                return color
        return "#e74c3c"

    def to_html(
        self,
        report: CreditReport,
        plan: Optional[CreditImprovementPlan] = None,
        entity_name: str = "Client",
    ) -> str:
        score = report.credit_score or 0
        color = self._score_color(score)
        tier = report.score_tier.value.replace("_", " ").title() if report.score_tier else "Unknown"

        component_rows = "\n".join(
            f"""<tr>
              <td>{c.name}</td>
              <td>{c.weight:.0f}%</td>
              <td>
                <div style="background:#eee;border-radius:4px;height:14px;width:100%">
                  <div style="background:{self._score_color(int(c.current_score * 8.5))};width:{c.current_score}%;height:14px;border-radius:4px;"></div>
                </div>
              </td>
              <td>{c.current_score:.0f}/100</td>
              <td>{c.status.title()}</td>
              <td style="font-size:11px;color:#555">{c.recommendation or '✓ On track'}</td>
            </tr>"""
            for c in report.components
        )

        action_rows = ""
        if plan:
            action_rows = "\n".join(
                f"<tr><td>{a.priority}</td><td>{a.action}</td><td>{a.expected_impact}</td><td>{a.timeline}</td><td>{a.effort}</td></tr>"
                for a in plan.actions
            )

        return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><title>Credit Report — {entity_name}</title>
<style>
  body {{ font-family: Arial, sans-serif; font-size: 13px; color: #222; margin: 40px; }}
  .score-circle {{
    width: 120px; height: 120px; border-radius: 50%;
    border: 8px solid {color};
    display: flex; align-items: center; justify-content: center;
    font-size: 32px; font-weight: bold; color: {color};
    margin: 0 auto 16px;
  }}
  table {{ width: 100%; border-collapse: collapse; max-width: 900px; margin-top: 16px; }}
  th {{ background: #1a1a2e; color: white; padding: 8px; }}
  td {{ padding: 6px 8px; border-bottom: 1px solid #eee; vertical-align: middle; }}
</style>
</head>
<body>
<h2>{entity_name} — Credit Intelligence Report</h2>
<p>Prepared {report.last_updated.strftime('%B %d, %Y')}</p>

<div style="text-align:center">
  <div class="score-circle">{score}</div>
  <p><strong>{tier}</strong> — {report.score_model}</p>
  <p>Utilization: {report.total_utilization*100:.0f}% &nbsp;|&nbsp;
     Missed Payments: {report.total_missed_payments} &nbsp;|&nbsp;
     Derogatory Marks: {report.derogatory_marks}</p>
</div>

<h3>Score Component Breakdown</h3>
<table>
  <thead><tr><th>Component</th><th>Weight</th><th>Score</th><th>Out of 100</th><th>Status</th><th>Recommendation</th></tr></thead>
  <tbody>{component_rows}</tbody>
</table>

{f'''<h3>Improvement Plan — Target Score: {plan.target_score}</h3>
<p>Estimated time to target: <strong>{plan.estimated_months} months</strong></p>
<table>
  <thead><tr><th>#</th><th>Action</th><th>Expected Impact</th><th>Timeline</th><th>Effort</th></tr></thead>
  <tbody>{action_rows}</tbody>
</table>''' if plan else ''}

<p style="margin-top:30px;font-size:11px;color:#888">
  Credit data sourced from Plaid credit report API. Scores are estimates and may differ from bureau scores.
</p>
</body>
</html>"""
