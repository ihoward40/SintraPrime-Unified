"""
compliance_reporter.py — AI Compliance Report Generator for SintraPrime-Unified
Generates PDF-ready markdown compliance reports with executive summaries and trend analysis.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ai_compliance.compliance_checker import (
    CheckStatus,
    ComplianceSummary,
    Severity,
)
from ai_compliance.bias_detector import BiasReport, BiasSeverity
from ai_compliance.ethics_framework import EthicsReview, EthicsDecision


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class TrendDirection(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    INSUFFICIENT_DATA = "insufficient_data"


class RiskRating(str, Enum):
    CRITICAL = "Critical"        # 80–100
    HIGH = "High"                # 60–79
    MEDIUM = "Medium"            # 40–59
    LOW = "Low"                  # 20–39
    MINIMAL = "Minimal"          # 0–19


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ComplianceSnapshot:
    """Point-in-time compliance metrics for trend analysis."""
    snapshot_date: date
    overall_risk_score: int
    compliant_count: int
    non_compliant_count: int
    needs_review_count: int
    bias_score: float
    ethics_approval_rate: float
    active_violations: int
    label: Optional[str] = None


@dataclass
class ComplianceTrend:
    """Trend analysis comparing snapshots over time."""
    direction: TrendDirection
    risk_score_delta: float          # Change in risk score (negative = improving)
    compliance_rate_delta: float     # Change in compliance rate (positive = improving)
    period_days: int
    summary: str
    key_changes: List[str]


@dataclass
class ComplianceReportData:
    """All data needed to generate a compliance report."""
    report_id: str
    report_title: str
    organization: str
    generated_at: datetime
    period_start: date
    period_end: date
    compliance_summaries: List[ComplianceSummary]
    bias_reports: List[BiasReport]
    ethics_reviews: List[EthicsReview]
    historical_snapshots: List[ComplianceSnapshot] = field(default_factory=list)
    auditor_name: Optional[str] = None
    version: str = "1.0"


# ---------------------------------------------------------------------------
# Report Computations
# ---------------------------------------------------------------------------

def compute_risk_rating(score: int) -> RiskRating:
    if score >= 80:
        return RiskRating.CRITICAL
    elif score >= 60:
        return RiskRating.HIGH
    elif score >= 40:
        return RiskRating.MEDIUM
    elif score >= 20:
        return RiskRating.LOW
    else:
        return RiskRating.MINIMAL


def compute_trend(snapshots: List[ComplianceSnapshot]) -> ComplianceTrend:
    """Compute trend from historical snapshots."""
    if len(snapshots) < 2:
        return ComplianceTrend(
            direction=TrendDirection.INSUFFICIENT_DATA,
            risk_score_delta=0.0,
            compliance_rate_delta=0.0,
            period_days=0,
            summary="Insufficient historical data for trend analysis.",
            key_changes=[],
        )

    sorted_snaps = sorted(snapshots, key=lambda s: s.snapshot_date)
    earliest = sorted_snaps[0]
    latest = sorted_snaps[-1]

    risk_delta = latest.overall_risk_score - earliest.overall_risk_score

    def compliance_rate(s: ComplianceSnapshot) -> float:
        total = s.compliant_count + s.non_compliant_count + s.needs_review_count
        return s.compliant_count / total if total > 0 else 0.0

    rate_delta = compliance_rate(latest) - compliance_rate(earliest)

    period_days = (latest.snapshot_date - earliest.snapshot_date).days

    if risk_delta <= -5 and rate_delta >= 0.05:
        direction = TrendDirection.IMPROVING
    elif risk_delta >= 5 and rate_delta <= -0.05:
        direction = TrendDirection.DEGRADING
    else:
        direction = TrendDirection.STABLE

    key_changes: List[str] = []
    if abs(risk_delta) > 0:
        direction_word = "decreased" if risk_delta < 0 else "increased"
        key_changes.append(f"Risk score {direction_word} by {abs(risk_delta)} points.")
    if abs(rate_delta) > 0.01:
        direction_word = "improved" if rate_delta > 0 else "declined"
        key_changes.append(f"Compliance rate {direction_word} by {abs(rate_delta):.1%}.")
    if latest.active_violations != earliest.active_violations:
        diff = latest.active_violations - earliest.active_violations
        direction_word = "increased" if diff > 0 else "decreased"
        key_changes.append(f"Active violations {direction_word} by {abs(diff)}.")

    summary_parts = [
        f"Over the past {period_days} days, compliance is {direction.value}.",
        f"Risk score: {earliest.overall_risk_score} → {latest.overall_risk_score} ({risk_delta:+d}).",
    ]

    return ComplianceTrend(
        direction=direction,
        risk_score_delta=float(risk_delta),
        compliance_rate_delta=rate_delta,
        period_days=period_days,
        summary=" ".join(summary_parts),
        key_changes=key_changes,
    )


def aggregate_compliance_stats(summaries: List[ComplianceSummary]) -> Dict[str, Any]:
    """Aggregate statistics across multiple compliance summaries."""
    if not summaries:
        return {"total_checks": 0, "compliance_rate": 0.0}

    total_checks = sum(len(s.checks) for s in summaries)
    total_compliant = sum(s.compliant_count for s in summaries)
    total_non_compliant = sum(s.non_compliant_count for s in summaries)
    total_needs_review = sum(s.needs_review_count for s in summaries)
    avg_risk_score = sum(s.risk_score for s in summaries) / len(summaries)

    # Compliance rate
    compliance_rate = total_compliant / total_checks if total_checks > 0 else 0.0

    # Top non-compliant laws
    law_violations: Dict[str, int] = {}
    for summary in summaries:
        for check in summary.checks:
            if check.status == CheckStatus.NON_COMPLIANT:
                law_name = check.law.short_name
                law_violations[law_name] = law_violations.get(law_name, 0) + 1

    top_violations = sorted(law_violations.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total_operations": len(summaries),
        "total_checks": total_checks,
        "total_compliant": total_compliant,
        "total_non_compliant": total_non_compliant,
        "total_needs_review": total_needs_review,
        "compliance_rate": compliance_rate,
        "average_risk_score": avg_risk_score,
        "top_violations": top_violations,
    }


# ---------------------------------------------------------------------------
# Report Generator
# ---------------------------------------------------------------------------

class ComplianceReporter:
    """
    Generates comprehensive, PDF-ready markdown compliance reports
    for SintraPrime-Unified AI operations.
    """

    def generate_report(self, data: ComplianceReportData) -> str:
        """Generate a full compliance report as a markdown string."""
        sections = [
            self._header(data),
            self._executive_summary(data),
            self._risk_dashboard(data),
            self._compliance_findings(data),
            self._bias_analysis(data),
            self._ethics_review_section(data),
            self._trend_analysis(data),
            self._remediation_roadmap(data),
            self._applicable_laws_section(data),
            self._footer(data),
        ]
        return "\n\n---\n\n".join(s for s in sections if s)

    def _header(self, data: ComplianceReportData) -> str:
        return f"""# {data.report_title}

**Organization:** {data.organization}  
**Report ID:** {data.report_id}  
**Generated:** {data.generated_at.strftime("%B %d, %Y at %H:%M UTC")}  
**Period:** {data.period_start.strftime("%B %d, %Y")} – {data.period_end.strftime("%B %d, %Y")}  
**Version:** {data.version}  
{"**Auditor:** " + data.auditor_name if data.auditor_name else ""}

> This report is generated automatically by SintraPrime-Unified's AI Compliance Module.
> It covers applicable AI regulations as of 2026 and should be reviewed by qualified counsel.
"""

    def _executive_summary(self, data: ComplianceReportData) -> str:
        stats = aggregate_compliance_stats(data.compliance_summaries)
        avg_risk = stats.get("average_risk_score", 0)
        risk_rating = compute_risk_rating(int(avg_risk))
        compliance_rate = stats.get("compliance_rate", 0.0)

        total_biased = sum(1 for r in data.bias_reports if r.is_biased)
        total_ethics_approved = sum(
            1 for r in data.ethics_reviews if r.decision == EthicsDecision.APPROVED
        )
        ethics_total = len(data.ethics_reviews)
        ethics_rate = (total_ethics_approved / ethics_total * 100) if ethics_total > 0 else 0

        status_icon = {
            RiskRating.CRITICAL: "🔴",
            RiskRating.HIGH: "🟠",
            RiskRating.MEDIUM: "🟡",
            RiskRating.LOW: "🟢",
            RiskRating.MINIMAL: "✅",
        }[risk_rating]

        return f"""## Executive Summary

{status_icon} **Overall Compliance Risk Rating: {risk_rating.value}** (Score: {avg_risk:.0f}/100)

### Key Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Operations Reviewed | {stats.get("total_operations", 0)} | — |
| Compliance Rate | {compliance_rate:.1%} | {"✅" if compliance_rate >= 0.80 else "⚠️" if compliance_rate >= 0.60 else "❌"} |
| Non-Compliant Checks | {stats.get("total_non_compliant", 0)} | {"✅" if stats.get("total_non_compliant", 0) == 0 else "❌"} |
| Bias Incidents | {total_biased}/{len(data.bias_reports)} outputs | {"✅" if total_biased == 0 else "⚠️"} |
| Ethics Approval Rate | {ethics_rate:.1f}% | {"✅" if ethics_rate >= 90 else "⚠️" if ethics_rate >= 70 else "❌"} |
| Average Risk Score | {avg_risk:.1f}/100 | {status_icon} |

### Summary Assessment

{"✅ SintraPrime operations are substantially compliant with applicable AI regulations." if compliance_rate >= 0.80 else "⚠️ SintraPrime operations require attention to achieve full regulatory compliance." if compliance_rate >= 0.60 else "❌ CRITICAL: Significant compliance deficiencies detected requiring immediate remediation."}

**Top Compliance Concerns:**
{chr(10).join(f"- {law}: {count} violation(s)" for law, count in stats.get("top_violations", [])[:3]) or "- No significant compliance concerns identified."}
"""

    def _risk_dashboard(self, data: ComplianceReportData) -> str:
        stats = aggregate_compliance_stats(data.compliance_summaries)
        avg_risk = int(stats.get("average_risk_score", 0))

        bars = {
            RiskRating.MINIMAL: "░░░░░░░░░░",
            RiskRating.LOW: "██░░░░░░░░",
            RiskRating.MEDIUM: "████░░░░░░",
            RiskRating.HIGH: "██████░░░░",
            RiskRating.CRITICAL: "██████████",
        }
        rating = compute_risk_rating(avg_risk)

        return f"""## Risk Dashboard

### Overall Risk Score: {avg_risk}/100 — {rating.value}

```
Risk Level:  {bars[rating]} {avg_risk}%
Min Risk:    ░░░░░░░░░░ 0
Max Risk:    ██████████ 100
```

### Checks by Status

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ Compliant | {stats.get("total_compliant", 0)} | {stats.get("compliance_rate", 0):.1%} |
| ❌ Non-Compliant | {stats.get("total_non_compliant", 0)} | {(stats.get("total_non_compliant", 0) / max(stats.get("total_checks", 1), 1)):.1%} |
| ⚠️ Needs Review | {stats.get("total_needs_review", 0)} | {(stats.get("total_needs_review", 0) / max(stats.get("total_checks", 1), 1)):.1%} |
| **Total** | **{stats.get("total_checks", 0)}** | 100% |
"""

    def _compliance_findings(self, data: ComplianceReportData) -> str:
        if not data.compliance_summaries:
            return "## Compliance Findings\n\nNo compliance checks available for this period."

        lines = ["## Compliance Findings\n"]

        for i, summary in enumerate(data.compliance_summaries[:10], 1):
            status_icon = {"COMPLIANT": "✅", "NON_COMPLIANT": "❌", "NEEDS_REVIEW": "⚠️"}.get(
                summary.overall_status.value, "❓"
            )
            lines.append(f"### Operation {i}: {summary.operation_context.operation_type}")
            lines.append(f"**Status:** {status_icon} {summary.overall_status.value}  ")
            lines.append(f"**Risk Score:** {summary.risk_score}/100  ")
            lines.append(f"**Jurisdiction:** {', '.join(j.value for j in summary.operation_context.jurisdictions)}\n")

            non_compliant = [c for c in summary.checks if c.status == CheckStatus.NON_COMPLIANT]
            if non_compliant:
                lines.append("**Non-Compliant Areas:**")
                for check in non_compliant[:3]:
                    lines.append(f"- **{check.law.short_name}** ({check.area.value}): {check.findings[0] if check.findings else 'No details'}")
                lines.append("")

        if len(data.compliance_summaries) > 10:
            lines.append(f"*...and {len(data.compliance_summaries) - 10} additional operations (see full data)*")

        return "\n".join(lines)

    def _bias_analysis(self, data: ComplianceReportData) -> str:
        if not data.bias_reports:
            return "## Bias Analysis\n\nNo bias reports available for this period."

        biased = [r for r in data.bias_reports if r.is_biased]
        blocking = [r for r in data.bias_reports if r.requires_blocking]
        avg_bias_score = sum(r.bias_score for r in data.bias_reports) / len(data.bias_reports)

        lines = [
            "## Bias Analysis",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Outputs Analyzed | {len(data.bias_reports)} |",
            f"| Outputs with Bias Detected | {len(biased)} ({len(biased)/len(data.bias_reports):.1%}) |",
            f"| Outputs Requiring Blocking | {len(blocking)} |",
            f"| Average Bias Score | {avg_bias_score:.3f}/1.000 |",
            "",
        ]

        if biased:
            lines.append("### Bias Incidents")
            for report in biased[:5]:
                lines.append(f"- **Output {report.output_id}**: {report.overall_severity.value.upper()} severity, "
                           f"score {report.bias_score:.3f}. "
                           f"Indicators: {len(report.indicators)}")
            lines.append("")

        # Category breakdown
        from collections import Counter
        category_counts: Counter = Counter()
        for report in data.bias_reports:
            for indicator in report.indicators:
                category_counts[indicator.category.value] += 1

        if category_counts:
            lines.append("### Bias by Category")
            lines.append("| Category | Occurrences |")
            lines.append("|----------|------------|")
            for cat, count in category_counts.most_common():
                lines.append(f"| {cat} | {count} |")
            lines.append("")

        return "\n".join(lines)

    def _ethics_review_section(self, data: ComplianceReportData) -> str:
        if not data.ethics_reviews:
            return "## Ethics Reviews\n\nNo ethics reviews available for this period."

        approved = sum(1 for r in data.ethics_reviews if r.decision == EthicsDecision.APPROVED)
        conditional = sum(1 for r in data.ethics_reviews if r.decision == EthicsDecision.CONDITIONAL)
        refused = sum(1 for r in data.ethics_reviews if r.decision == EthicsDecision.REFUSED)
        avg_score = sum(r.overall_score for r in data.ethics_reviews) / len(data.ethics_reviews)

        return f"""## Ethics Reviews

| Decision | Count | Percentage |
|----------|-------|------------|
| ✅ Approved | {approved} | {approved/len(data.ethics_reviews):.1%} |
| ⚠️ Conditional | {conditional} | {conditional/len(data.ethics_reviews):.1%} |
| ❌ Refused | {refused} | {refused/len(data.ethics_reviews):.1%} |
| **Average Ethics Score** | **{avg_score:.3f}** | — |

### Red Line Violations
{"No red line violations detected during this period. ✅" if not any(r.has_red_line_violations for r in data.ethics_reviews) else
"⚠️ Red line violations were detected. See individual ethics reviews for details."}
"""

    def _trend_analysis(self, data: ComplianceReportData) -> str:
        trend = compute_trend(data.historical_snapshots)
        icon = {
            TrendDirection.IMPROVING: "📈",
            TrendDirection.STABLE: "➡️",
            TrendDirection.DEGRADING: "📉",
            TrendDirection.INSUFFICIENT_DATA: "❓",
        }[trend.direction]

        lines = [
            "## Trend Analysis",
            "",
            f"**Direction:** {icon} {trend.direction.value.replace('_', ' ').title()}",
            f"**Period:** {trend.period_days} days",
            f"**Risk Score Change:** {trend.risk_score_delta:+.1f} points",
            f"**Compliance Rate Change:** {trend.compliance_rate_delta:+.1%}",
            "",
            f"**Summary:** {trend.summary}",
            "",
        ]

        if trend.key_changes:
            lines.append("**Key Changes:**")
            for change in trend.key_changes:
                lines.append(f"- {change}")

        if len(data.historical_snapshots) >= 2:
            lines.append("\n### Historical Risk Scores")
            lines.append("| Date | Risk Score | Rating |")
            lines.append("|------|-----------|--------|")
            for snap in sorted(data.historical_snapshots, key=lambda s: s.snapshot_date)[-6:]:
                rating = compute_risk_rating(snap.overall_risk_score)
                lines.append(f"| {snap.snapshot_date.isoformat()} | {snap.overall_risk_score} | {rating.value} |")

        return "\n".join(lines)

    def _remediation_roadmap(self, data: ComplianceReportData) -> str:
        from ai_compliance.compliance_checker import ComplianceChecker
        checker = ComplianceChecker()

        all_remediations: List[Dict[str, Any]] = []
        for summary in data.compliance_summaries:
            roadmap = checker.get_remediation_roadmap(summary)
            all_remediations.extend(roadmap)

        if not all_remediations:
            return "## Remediation Roadmap\n\n✅ No remediation actions required."

        priority_order = ["critical", "high", "medium", "low"]
        grouped: Dict[str, List[Dict]] = {p: [] for p in priority_order}
        for item in all_remediations:
            priority = item.get("priority", "low")
            if priority in grouped:
                grouped[priority].append(item)

        lines = ["## Remediation Roadmap", ""]
        for priority in priority_order:
            items = grouped[priority]
            if not items:
                continue
            icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}[priority]
            lines.append(f"### {icon} {priority.title()} Priority")
            lines.append("")
            seen = set()
            for item in items[:5]:
                action = item.get("action", "")
                if action not in seen:
                    seen.add(action)
                    law = item.get("law", "")
                    area = item.get("area", "")
                    deadline = item.get("deadline", "30 days")
                    lines.append(f"- **[{law} / {area}]** {action} *(Deadline: {deadline})*")
            lines.append("")

        return "\n".join(lines)

    def _applicable_laws_section(self, data: ComplianceReportData) -> str:
        seen_ids: set = set()
        all_laws = []
        for summary in data.compliance_summaries:
            for law in summary.applicable_laws:
                if law.law_id not in seen_ids:
                    seen_ids.add(law.law_id)
                    all_laws.append(law)

        if not all_laws:
            return ""

        lines = [
            "## Applicable Laws and Regulations",
            "",
            "| Law | Jurisdiction | Effective Date | Status |",
            "|-----|-------------|----------------|--------|",
        ]
        for law in sorted(all_laws, key=lambda l: l.jurisdiction.value):
            lines.append(
                f"| {law.short_name} | {law.jurisdiction.value} | "
                f"{law.effective_date.isoformat()} | {law.status} |"
            )

        return "\n".join(lines)

    def _footer(self, data: ComplianceReportData) -> str:
        return f"""## Disclaimer

This report was automatically generated by SintraPrime-Unified AI Compliance Module v{data.version}.

- Compliance determinations are based on publicly available regulatory texts as of the report date.
- This report does not constitute legal advice.
- Consult qualified legal counsel to confirm compliance status and implement remediation measures.
- Regulatory landscape changes frequently; review should be conducted at least quarterly.

**Report generated:** {data.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")}  
**Next scheduled review:** {data.period_end.isoformat()}

*SintraPrime-Unified — AI Governance & Compliance Layer*
"""

    def generate_summary_dict(self, data: ComplianceReportData) -> Dict[str, Any]:
        """Generate a machine-readable compliance summary dict."""
        stats = aggregate_compliance_stats(data.compliance_summaries)
        trend = compute_trend(data.historical_snapshots)
        avg_risk = int(stats.get("average_risk_score", 0))

        return {
            "report_id": data.report_id,
            "organization": data.organization,
            "generated_at": data.generated_at.isoformat(),
            "period": {
                "start": data.period_start.isoformat(),
                "end": data.period_end.isoformat(),
            },
            "risk_score": avg_risk,
            "risk_rating": compute_risk_rating(avg_risk).value,
            "compliance_rate": stats.get("compliance_rate", 0.0),
            "trend": trend.direction.value,
            "total_checks": stats.get("total_checks", 0),
            "top_violations": stats.get("top_violations", []),
        }


if __name__ == "__main__":
    import uuid
    from datetime import timedelta

    reporter = ComplianceReporter()
    today = date.today()

    data = ComplianceReportData(
        report_id=str(uuid.uuid4())[:8],
        report_title="SintraPrime-Unified AI Compliance Report",
        organization="SintraPrime-Unified",
        generated_at=datetime.utcnow(),
        period_start=today - timedelta(days=30),
        period_end=today,
        compliance_summaries=[],
        bias_reports=[],
        ethics_reviews=[],
        historical_snapshots=[
            ComplianceSnapshot(
                snapshot_date=today - timedelta(days=30),
                overall_risk_score=45,
                compliant_count=80,
                non_compliant_count=15,
                needs_review_count=10,
                bias_score=0.12,
                ethics_approval_rate=0.88,
                active_violations=5,
            ),
            ComplianceSnapshot(
                snapshot_date=today,
                overall_risk_score=30,
                compliant_count=90,
                non_compliant_count=8,
                needs_review_count=7,
                bias_score=0.05,
                ethics_approval_rate=0.94,
                active_violations=2,
            ),
        ],
    )

    report_md = reporter.generate_report(data)
    print(report_md[:500])
    print("...")
    print(f"Report length: {len(report_md)} characters")
