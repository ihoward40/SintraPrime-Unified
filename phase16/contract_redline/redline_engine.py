"""Phase 16D — AI Contract Redlining Engine."""
from __future__ import annotations
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from phase16.contract_redline.models import (
    ClauseType, ContractAnalysis, ContractClause, Redline,
    RedlineAction, RiskFlag, RiskLevel,
)

# ── Risk patterns: (pattern, risk_level, issue, recommendation) ──────────────
RISK_PATTERNS: Dict[ClauseType, List[Tuple[str, RiskLevel, str, str]]] = {
    ClauseType.INDEMNIFICATION: [
        (r"indemnif[yi]", RiskLevel.HIGH,
         "Broad indemnification clause detected",
         "Limit indemnification to direct damages caused by your own negligence"),
        (r"unlimited\s+liabilit", RiskLevel.CRITICAL,
         "Unlimited liability exposure",
         "Cap liability to contract value or insurance coverage"),
    ],
    ClauseType.LIMITATION_OF_LIABILITY: [
        (r"no\s+limit\s+on\s+liabilit|unlimited", RiskLevel.CRITICAL,
         "No limitation of liability",
         "Add mutual cap on liability equal to 12 months of fees"),
        (r"consequential.*damages.*excluded", RiskLevel.LOW,
         "Consequential damages excluded — standard",
         "Review if exclusion is mutual"),
    ],
    ClauseType.TERMINATION: [
        (r"terminat.{0,30}without\s+cause", RiskLevel.MEDIUM,
         "Termination for convenience without notice period",
         "Require minimum 30-day written notice"),
        (r"terminat.{0,30}immediately", RiskLevel.HIGH,
         "Immediate termination clause",
         "Negotiate cure period of at least 15 days"),
    ],
    ClauseType.NON_COMPETE: [
        (r"not.{0,20}compet|non.{0,5}compet", RiskLevel.HIGH,
         "Non-compete clause detected",
         "Limit scope to 12 months and specific geographic area"),
        (r"perpetual.{0,20}non.{0,5}compet", RiskLevel.CRITICAL,
         "Perpetual non-compete — likely unenforceable",
         "Remove or limit to reasonable duration"),
    ],
    ClauseType.INTELLECTUAL_PROPERTY: [
        (r"all\s+intellectual\s+property.{0,30}assign", RiskLevel.HIGH,
         "Broad IP assignment clause",
         "Carve out pre-existing IP and background technology"),
        (r"work\s+for\s+hire", RiskLevel.MEDIUM,
         "Work-for-hire designation",
         "Clarify scope — only applies to specifically commissioned works"),
    ],
    ClauseType.CONFIDENTIALITY: [
        (r"perpetual.{0,20}confidential", RiskLevel.MEDIUM,
         "Perpetual confidentiality obligation",
         "Limit to 3-5 years post-termination"),
        (r"confidential.{0,30}without\s+limit", RiskLevel.HIGH,
         "Unlimited confidentiality scope",
         "Define categories of confidential information explicitly"),
    ],
    ClauseType.PAYMENT: [
        (r"net\s+90|net-90", RiskLevel.MEDIUM,
         "Net-90 payment terms — unfavorable",
         "Negotiate to Net-30 or Net-45"),
        (r"automatic.{0,20}renew", RiskLevel.MEDIUM,
         "Auto-renewal clause",
         "Add 60-day cancellation notice window before renewal"),
    ],
}

# ── Clause detection keywords ─────────────────────────────────────────────────
CLAUSE_KEYWORDS: Dict[ClauseType, List[str]] = {
    ClauseType.INDEMNIFICATION: ["indemnif", "hold harmless", "defend"],
    ClauseType.LIMITATION_OF_LIABILITY: ["limitation of liability", "limit.*liabilit", "cap on liabilit"],
    ClauseType.TERMINATION: ["terminat", "cancell", "expir"],
    ClauseType.PAYMENT: ["payment", "invoice", "fee", "compensation", "net "],
    ClauseType.CONFIDENTIALITY: ["confidential", "non-disclosure", "nda", "proprietary"],
    ClauseType.INTELLECTUAL_PROPERTY: ["intellectual property", "ip ", "copyright", "patent", "work for hire"],
    ClauseType.GOVERNING_LAW: ["governing law", "choice of law", "governed by the laws"],
    ClauseType.DISPUTE_RESOLUTION: ["arbitration", "mediation", "dispute resolution", "adr"],
    ClauseType.FORCE_MAJEURE: ["force majeure", "act of god", "unforeseeable"],
    ClauseType.NON_COMPETE: ["non-compete", "non compete", "noncompete", "covenant not to compete", "not to compete", "agree.*not.*compete"],
    ClauseType.ASSIGNMENT: ["may not be assigned", "assignment", "transfer.*rights", "assign.*agreement", "without.*consent.*assign"],
    ClauseType.AMENDMENT: ["amendment", "modification", "change.*agreement"],
}

# ── Standard redline suggestions ─────────────────────────────────────────────
STANDARD_REDLINES: Dict[ClauseType, List[Tuple[str, str, str, RiskLevel]]] = {
    ClauseType.INDEMNIFICATION: [
        (r"shall indemnify.*from.*any.*all",
         "shall indemnify from direct damages arising solely from [Party]'s gross negligence or willful misconduct",
         "Limit indemnification scope to direct damages and own negligence",
         RiskLevel.HIGH),
    ],
    ClauseType.TERMINATION: [
        (r"terminat.{0,30}immediately\s+upon",
         "may terminate upon thirty (30) days' prior written notice",
         "Replace immediate termination with 30-day notice requirement",
         RiskLevel.HIGH),
    ],
    ClauseType.NON_COMPETE: [
        (r"for\s+a\s+period\s+of\s+(?:five|5|ten|10)\s+years",
         "for a period of twelve (12) months",
         "Reduce non-compete duration to 12 months",
         RiskLevel.HIGH),
    ],
    ClauseType.PAYMENT: [
        (r"net\s*[-\s]?90",
         "Net-30",
         "Improve payment terms from Net-90 to Net-30",
         RiskLevel.MEDIUM),
    ],
}


class ClauseExtractor:
    """Extracts and classifies clauses from contract text."""

    def extract(self, contract_text: str) -> List[ContractClause]:
        clauses: List[ContractClause] = []
        # Split on section markers (numbered sections, "ARTICLE", "SECTION")
        section_pattern = re.compile(
            r'(?:^|\n)(\d+\.?\d*\.?\s+[A-Z][^\n]{5,}|(?:ARTICLE|SECTION)\s+[IVX\d]+[^\n]*)',
            re.MULTILINE
        )
        sections = section_pattern.split(contract_text)

        # Process each section
        current_number = ""
        for i, chunk in enumerate(sections):
            if not chunk.strip():
                continue
            # Detect if this is a section header
            if section_pattern.match(chunk.strip()):
                current_number = chunk.strip()[:20]
                continue
            clause_type = self._classify_text(chunk)
            clause = ContractClause(
                clause_id=f"cl_{uuid.uuid4().hex[:8]}",
                clause_type=clause_type,
                original_text=chunk.strip(),
                section_number=current_number,
                page_number=max(1, i // 3),
            )
            clauses.append(clause)

        # If no sections found, treat whole text as one clause
        if not clauses:
            clauses.append(ContractClause(
                clause_id=f"cl_{uuid.uuid4().hex[:8]}",
                clause_type=self._classify_text(contract_text),
                original_text=contract_text.strip(),
                section_number="1",
                page_number=1,
            ))
        return clauses

    def _classify_text(self, text: str) -> ClauseType:
        text_lower = text.lower()
        best_match = ClauseType.GENERAL
        best_count = 0
        for clause_type, keywords in CLAUSE_KEYWORDS.items():
            count = sum(1 for kw in keywords if re.search(kw, text_lower))
            if count > best_count:
                best_count = count
                best_match = clause_type
        return best_match


class RiskAnalyzer:
    """Analyzes clauses for legal risk."""

    def analyze(self, clauses: List[ContractClause]) -> List[RiskFlag]:
        flags: List[RiskFlag] = []
        for clause in clauses:
            patterns = RISK_PATTERNS.get(clause.clause_type, [])
            for pattern, risk_level, issue, recommendation in patterns:
                if re.search(pattern, clause.original_text, re.IGNORECASE):
                    flag = RiskFlag(
                        flag_id=f"rf_{uuid.uuid4().hex[:8]}",
                        clause_id=clause.clause_id,
                        risk_level=risk_level,
                        issue=issue,
                        recommendation=recommendation,
                        confidence=0.85,
                    )
                    flags.append(flag)
        return flags

    def compute_overall_risk(self, flags: List[RiskFlag]) -> RiskLevel:
        if any(f.risk_level == RiskLevel.CRITICAL for f in flags):
            return RiskLevel.CRITICAL
        if any(f.risk_level == RiskLevel.HIGH for f in flags):
            return RiskLevel.HIGH
        if any(f.risk_level == RiskLevel.MEDIUM for f in flags):
            return RiskLevel.MEDIUM
        return RiskLevel.LOW


class RedlineSuggester:
    """Generates redline suggestions for risky clauses."""

    def suggest(self, clauses: List[ContractClause],
                flags: List[RiskFlag]) -> List[Redline]:
        redlines: List[Redline] = []
        flagged_clause_ids = {f.clause_id for f in flags}

        for clause in clauses:
            patterns = STANDARD_REDLINES.get(clause.clause_type, [])
            for pattern, replacement, rationale, risk_level in patterns:
                match = re.search(pattern, clause.original_text, re.IGNORECASE)
                if match:
                    redline = Redline(
                        redline_id=f"rl_{uuid.uuid4().hex[:8]}",
                        clause_id=clause.clause_id,
                        action=RedlineAction.MODIFY,
                        original_text=match.group(0),
                        suggested_text=replacement,
                        rationale=rationale,
                        risk_level=risk_level,
                    )
                    redlines.append(redline)

            # Flag clauses with no standard redline but with risk flags
            if clause.clause_id in flagged_clause_ids and not any(
                r.clause_id == clause.clause_id for r in redlines
            ):
                clause_flags = [f for f in flags if f.clause_id == clause.clause_id]
                if clause_flags:
                    top_flag = max(clause_flags, key=lambda f: list(RiskLevel).index(f.risk_level))
                    redline = Redline(
                        redline_id=f"rl_{uuid.uuid4().hex[:8]}",
                        clause_id=clause.clause_id,
                        action=RedlineAction.FLAG,
                        original_text=clause.original_text[:200],
                        suggested_text="[Requires attorney review]",
                        rationale=top_flag.recommendation,
                        risk_level=top_flag.risk_level,
                    )
                    redlines.append(redline)

        return redlines


class ContractRedlineEngine:
    """Main contract redlining engine."""

    def __init__(self):
        self._extractor = ClauseExtractor()
        self._analyzer = RiskAnalyzer()
        self._suggester = RedlineSuggester()
        self._analyses: Dict[str, ContractAnalysis] = {}

    def analyze(self, contract_id: str, contract_text: str) -> ContractAnalysis:
        """Full analysis pipeline: extract → analyze → suggest."""
        clauses = self._extractor.extract(contract_text)
        flags = self._analyzer.analyze(clauses)
        redlines = self._suggester.suggest(clauses, flags)
        overall_risk = self._analyzer.compute_overall_risk(flags)

        analysis = ContractAnalysis(
            analysis_id=f"ana_{uuid.uuid4().hex[:8]}",
            contract_id=contract_id,
            clauses=clauses,
            risk_flags=flags,
            redlines=redlines,
            overall_risk=overall_risk,
            summary=self._generate_summary(clauses, flags, redlines, overall_risk),
            created_at=time.time(),
        )
        self._analyses[analysis.analysis_id] = analysis
        return analysis

    def accept_redline(self, analysis_id: str, redline_id: str) -> Redline:
        analysis = self._get_analysis(analysis_id)
        redline = self._get_redline(analysis, redline_id)
        redline.accepted = True
        return redline

    def reject_redline(self, analysis_id: str, redline_id: str) -> Redline:
        analysis = self._get_analysis(analysis_id)
        redline = self._get_redline(analysis, redline_id)
        redline.accepted = False
        return redline

    def add_comment(self, analysis_id: str, redline_id: str, comment: str) -> Redline:
        analysis = self._get_analysis(analysis_id)
        redline = self._get_redline(analysis, redline_id)
        redline.comment = comment
        return redline

    def get_analysis(self, analysis_id: str) -> Optional[ContractAnalysis]:
        return self._analyses.get(analysis_id)

    def export_redlined_text(self, analysis_id: str) -> str:
        """Export contract text with accepted redlines applied."""
        analysis = self._get_analysis(analysis_id)
        result_parts = []
        for clause in analysis.clauses:
            text = clause.original_text
            for redline in analysis.accepted_redlines:
                if redline.clause_id == clause.clause_id and redline.original_text in text:
                    text = text.replace(redline.original_text, f"[REDLINED: {redline.suggested_text}]")
            result_parts.append(text)
        return "\n\n".join(result_parts)

    def _get_analysis(self, analysis_id: str) -> ContractAnalysis:
        analysis = self._analyses.get(analysis_id)
        if not analysis:
            raise KeyError(f"Analysis {analysis_id} not found")
        return analysis

    def _get_redline(self, analysis: ContractAnalysis, redline_id: str) -> Redline:
        for r in analysis.redlines:
            if r.redline_id == redline_id:
                return r
        raise KeyError(f"Redline {redline_id} not found in analysis {analysis.analysis_id}")

    def _generate_summary(self, clauses: List[ContractClause],
                           flags: List[RiskFlag],
                           redlines: List[Redline],
                           overall_risk: RiskLevel) -> str:
        critical = sum(1 for f in flags if f.risk_level == RiskLevel.CRITICAL)
        high = sum(1 for f in flags if f.risk_level == RiskLevel.HIGH)
        return (
            f"Contract analysis complete. Overall risk: {overall_risk.value.upper()}. "
            f"Found {len(clauses)} clauses, {len(flags)} risk flags "
            f"({critical} critical, {high} high), {len(redlines)} redline suggestions."
        )
