"""
self_audit.py — Self-audit engine for SintraPrime.

SintraPrime catches and corrects its own mistakes before they reach users.
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

AUDIT_LOG_PATH = Path(os.environ.get("AUDIT_LOG_PATH", str(Path.home() / ".sintra" / "audit_log.jsonl")))


def _now_ts() -> float:
    return time.time()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# AuditRule
# ---------------------------------------------------------------------------

@dataclass
class AuditRule:
    rule_id: str
    name: str
    description: str
    severity: str  # critical / high / medium / low
    check_fn: Callable[[str, str], Tuple[bool, str]] = field(repr=False)

    def check(self, response: str, context: str = "") -> Tuple[bool, str]:
        """Run the rule. Returns (passed, issue_description)."""
        try:
            return self.check_fn(response, context)
        except Exception as e:
            return False, f"Rule check error: {e}"

    def __repr__(self) -> str:
        return f"AuditRule(id={self.rule_id}, name={self.name!r}, severity={self.severity})"


@dataclass
class AuditIssue:
    rule_id: str
    rule_name: str
    severity: str
    description: str
    fixed: bool = False
    fix_applied: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    def __repr__(self) -> str:
        return f"AuditIssue(rule={self.rule_name!r}, severity={self.severity}, fixed={self.fixed})"


@dataclass
class AuditResult:
    audit_id: str
    timestamp: float
    response_snippet: str
    issues: List[AuditIssue]
    passed: bool
    overall_score: float  # 0-1, higher is better
    fixed_response: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "audit_id": self.audit_id,
            "timestamp": self.timestamp,
            "response_snippet": self.response_snippet,
            "issues": [i.to_dict() for i in self.issues],
            "passed": self.passed,
            "overall_score": self.overall_score,
            "fixed_response": self.fixed_response,
        }

    def __repr__(self) -> str:
        return (f"AuditResult(id={self.audit_id[:8]}, passed={self.passed}, "
                f"issues={len(self.issues)}, score={self.overall_score:.2f})")


# ---------------------------------------------------------------------------
# Built-in Audit Rule Implementations
# ---------------------------------------------------------------------------

def _hallucination_check(response: str, context: str) -> Tuple[bool, str]:
    """Check if response claims things not present in context."""
    if not context:
        return True, ""
    # Extract capitalized proper nouns/numbers from response
    response_specifics = re.findall(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b|\b\d{4}\b|\b\d+\.\d+\b", response)
    context_lower = context.lower()
    unsupported = []
    for item in response_specifics:
        if len(item) > 3 and item.lower() not in context_lower:
            unsupported.append(item)
    if len(unsupported) > 5:
        return False, f"Potential hallucinations: {unsupported[:5]}"
    return True, ""


def _consistency_check(response: str, context: str) -> Tuple[bool, str]:
    """Check if response contradicts itself."""
    sentences = [s.strip() for s in re.split(r"[.!?]", response) if s.strip()]
    contradiction_patterns = [
        (r"\bis\b", r"\bis not\b"),
        (r"\bcan\b", r"\bcannot\b"),
        (r"\bwill\b", r"\bwill not\b"),
        (r"\balways\b", r"\bnever\b"),
    ]
    for pos_pat, neg_pat in contradiction_patterns:
        has_pos = any(re.search(pos_pat, s, re.I) for s in sentences)
        has_neg = any(re.search(neg_pat, s, re.I) for s in sentences)
        if has_pos and has_neg:
            return False, f"Possible contradiction: '{pos_pat}' vs '{neg_pat}' in response"
    return True, ""


def _confidence_calibration_check(response: str, context: str) -> Tuple[bool, str]:
    """Check if agent expresses appropriate uncertainty."""
    absolute_terms = re.findall(
        r"\b(definitely|certainly|absolutely|100%|always|never|guaranteed|impossible)\b",
        response, re.I
    )
    uncertain_terms = re.findall(
        r"\b(likely|probably|possibly|might|may|could|approximately|about|around|roughly)\b",
        response, re.I
    )
    # If many absolutes and no uncertainty markers on a complex topic, flag it
    if len(absolute_terms) > 3 and len(uncertain_terms) == 0:
        return False, f"Overuse of absolute terms: {absolute_terms[:3]} without hedging"
    return True, ""


def _toxicity_check(response: str, context: str) -> Tuple[bool, str]:
    """Check for harmful/offensive content."""
    toxic_patterns = [
        r"\b(hate|kill|murder|attack|harm|destroy|violence)\s+(all|every|those)\b",
        r"\b(stupid|idiot|moron|retard|dumb)\b",
        r"\b(racist|sexist|bigot)\b",
    ]
    for pattern in toxic_patterns:
        if re.search(pattern, response, re.I):
            return False, f"Potentially harmful content detected (pattern: {pattern})"
    return True, ""


def _factual_grounding_check(response: str, context: str) -> Tuple[bool, str]:
    """Check if factual claims have supporting evidence in context."""
    if not context:
        return True, ""
    factual_markers = re.findall(
        r"(?:according to|research shows|studies indicate|data shows|statistics show)[^.]+\.",
        response, re.I
    )
    ungrounded = []
    for claim in factual_markers:
        # Check if any key noun from the claim appears in context
        nouns = re.findall(r"\b[a-z]{5,}\b", claim.lower())
        if not any(n in context.lower() for n in nouns):
            ungrounded.append(claim[:60])
    if ungrounded:
        return False, f"Ungrounded factual claims: {ungrounded[:2]}"
    return True, ""


def _logic_consistency_check(response: str, context: str) -> Tuple[bool, str]:
    """Check for internal logical contradictions."""
    # Look for "X because Y" where X and Y are semantically opposite
    because_clauses = re.findall(r"([^.]+)\s+because\s+([^.]+)", response, re.I)
    for claim, reason in because_clauses:
        # Simple heuristic: if claim and reason have opposite sentiment
        neg_in_claim = bool(re.search(r"\b(not|no|never|cannot|can\'t|won\'t)\b", claim, re.I))
        neg_in_reason = bool(re.search(r"\b(not|no|never|cannot|can\'t|won\'t)\b", reason, re.I))
        # If both heavily negated, might be double-negative logic issue
        if neg_in_claim and neg_in_reason and len(claim.split()) > 8:
            return False, f"Potential logical inconsistency in: '{claim[:60]}'"
    return True, ""


def _completeness_check(response: str, context: str) -> Tuple[bool, str]:
    """Check if response actually answers the question asked."""
    # Context might contain the question
    question_words = re.findall(r"\b(what|why|how|when|where|who|which|explain|describe|list)\b",
                                 context, re.I)
    if not question_words:
        return True, ""
    # Response should have some substantive content
    word_count = len(response.split())
    if word_count < 10:
        return False, f"Response too short ({word_count} words) to answer: {question_words[:3]}"
    # Check if question type is addressed
    if "how" in [q.lower() for q in question_words]:
        has_steps = bool(re.search(r"\b(first|then|next|finally|step|by)\b", response, re.I))
        if not has_steps and word_count < 30:
            return False, "How-to question may lack step-by-step explanation"
    return True, ""


def _circular_reasoning_check(response: str, context: str) -> Tuple[bool, str]:
    """Detect circular logic ('A because A')."""
    because_clauses = re.findall(r"([^.!?]+)\s+because\s+([^.!?]+)", response, re.I)
    for claim, reason in because_clauses:
        # Strip filler words and compare
        def clean(s: str) -> str:
            return re.sub(r"\b(it|is|the|a|an|that|this|because|therefore)\b", "", s.lower()).strip()
        c_clean = clean(claim)
        r_clean = clean(reason)
        if c_clean and r_clean and (c_clean in r_clean or r_clean in c_clean):
            return False, f"Circular reasoning: '{claim[:60]}' because '{reason[:60]}'"
    return True, ""


def _overconfidence_check(response: str, context: str) -> Tuple[bool, str]:
    """Flag responses too certain about uncertain things."""
    certainty_phrases = re.findall(
        r"\b(I am certain|I am sure|I know for a fact|undoubtedly|unquestionably|"
        r"it is a fact that|proven fact|100% certain|without a doubt)\b",
        response, re.I
    )
    if certainty_phrases:
        return False, f"Overconfidence detected: {certainty_phrases[:2]}"
    return True, ""


def _bias_check(response: str, context: str) -> Tuple[bool, str]:
    """Detect common cognitive biases in reasoning."""
    bias_patterns = {
        "confirmation_bias": r"\b(confirms|confirms my|as expected|I knew|proves that)\b",
        "availability_heuristic": r"\b(everyone knows|obviously|clearly everyone|all people)\b",
        "appeal_to_authority": r"\b(experts say|scientists agree|authorities confirm)\b(?! (?:that|because|when))",
        "false_dichotomy": r"\b(either .{1,30} or .{1,30}(?:, nothing else|no other option|no alternative))\b",
    }
    detected = []
    for bias_name, pattern in bias_patterns.items():
        if re.search(pattern, response, re.I):
            detected.append(bias_name)
    if detected:
        return False, f"Possible cognitive bias(es): {detected}"
    return True, ""


# ---------------------------------------------------------------------------
# SelfAuditEngine
# ---------------------------------------------------------------------------

class SelfAuditEngine:
    """Runs audit rules against agent responses and auto-fixes issues."""

    # Severity weights for scoring
    SEVERITY_WEIGHTS = {"critical": 0.4, "high": 0.25, "medium": 0.15, "low": 0.05}

    def __init__(self):
        self._rules: List[AuditRule] = []
        self.fixer = AutoFixer()
        self.logger = AuditLogger()
        self._register_builtin_rules()
        self._session_responses: List[str] = []

    def _register_builtin_rules(self):
        builtin_rules = [
            AuditRule("R001", "HallucinationDetector",
                      "Checks if response contains claims that contradict context",
                      "high", _hallucination_check),
            AuditRule("R002", "ConsistencyChecker",
                      "Checks if response contradicts itself",
                      "high", _consistency_check),
            AuditRule("R003", "ConfidenceCalibrator",
                      "Checks if agent expresses appropriate uncertainty",
                      "medium", _confidence_calibration_check),
            AuditRule("R004", "ToxicityFilter",
                      "Checks for harmful/offensive content",
                      "critical", _toxicity_check),
            AuditRule("R005", "FactualGroundingChecker",
                      "Checks if factual claims have supporting evidence",
                      "high", _factual_grounding_check),
            AuditRule("R006", "LogicConsistencyChecker",
                      "Checks for internal logical contradictions",
                      "medium", _logic_consistency_check),
            AuditRule("R007", "CompletenessChecker",
                      "Checks if response actually answers the question",
                      "medium", _completeness_check),
            AuditRule("R008", "CircularReasoningDetector",
                      "Detects circular logic (A because A)",
                      "medium", _circular_reasoning_check),
            AuditRule("R009", "OverconfidenceDetector",
                      "Flags responses too certain about uncertain things",
                      "low", _overconfidence_check),
            AuditRule("R010", "BiasDetector",
                      "Detects common cognitive biases in reasoning",
                      "low", _bias_check),
        ]
        for rule in builtin_rules:
            self._rules.append(rule)

    def register_rule(self, rule: AuditRule):
        """Add a new audit rule."""
        self._rules.append(rule)

    def audit(self, response: str, context: str = "") -> AuditResult:
        """Run all audit rules against a response."""
        issues: List[AuditIssue] = []
        for rule in self._rules:
            passed, issue_desc = rule.check(response, context)
            if not passed:
                issues.append(AuditIssue(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    description=issue_desc,
                ))

        # Compute overall score
        penalty = sum(
            self.SEVERITY_WEIGHTS.get(issue.severity, 0.1)
            for issue in issues
        )
        overall_score = max(0.0, 1.0 - penalty)
        passed = overall_score >= 0.6 and not any(i.severity == "critical" for i in issues)

        result = AuditResult(
            audit_id=str(uuid.uuid4()),
            timestamp=_now_ts(),
            response_snippet=response[:200],
            issues=issues,
            passed=passed,
            overall_score=overall_score,
        )

        # Track session responses for consistency checks
        self._session_responses.append(response)

        # Log the audit
        self.logger.log(result)
        return result

    def fix(self, response: str, audit_result: AuditResult) -> str:
        """Attempt to auto-fix detected issues."""
        fixed = response
        for issue in audit_result.issues:
            if issue.rule_id == "R008":  # Circular reasoning
                fixed = self.fixer.fix_circular_reasoning(fixed)
                issue.fixed = True
                issue.fix_applied = "Added circular reasoning warning"
            elif issue.rule_id == "R009":  # Overconfidence
                fixed = self.fixer.fix_overconfidence(fixed)
                issue.fixed = True
                issue.fix_applied = "Added hedging language"
            elif issue.rule_id == "R001":  # Hallucination
                fixed = self.fixer.fix_hallucinations(fixed, "")
                issue.fixed = True
                issue.fix_applied = "Qualified unsupported claims"
            elif issue.rule_id == "R007":  # Completeness
                fixed = self.fixer.fix_incompleteness(fixed, "the question")
                issue.fixed = True
                issue.fix_applied = "Added completeness note"

        audit_result.fixed_response = fixed
        return fixed

    def report(self, audit_result: AuditResult) -> str:
        """Generate human-readable audit report."""
        lines = [
            f"=== AUDIT REPORT ===",
            f"Audit ID: {audit_result.audit_id}",
            f"Timestamp: {datetime.fromtimestamp(audit_result.timestamp, tz=timezone.utc).isoformat()}",
            f"Overall Score: {audit_result.overall_score:.2f}/1.0",
            f"Passed: {audit_result.passed}",
            f"Issues Found: {len(audit_result.issues)}",
            f"",
            f"--- Response (snippet) ---",
            f"{audit_result.response_snippet}",
            f"",
            f"--- Issues ---",
        ]
        if not audit_result.issues:
            lines.append("  None — response looks good!")
        else:
            for i, issue in enumerate(audit_result.issues, 1):
                fixed_str = " [FIXED]" if issue.fixed else ""
                lines.append(
                    f"  {i}. [{issue.severity.upper()}] {issue.rule_name}{fixed_str}"
                    f"\n     {issue.description}"
                )
                if issue.fix_applied:
                    lines.append(f"     Fix: {issue.fix_applied}")
        if audit_result.fixed_response and audit_result.fixed_response != audit_result.response_snippet:
            lines.append(f"\n--- Fixed Response (snippet) ---")
            lines.append(audit_result.fixed_response[:200])
        lines.append(f"\n{'=' * 20}")
        return "\n".join(lines)

    def rules(self) -> List[AuditRule]:
        return list(self._rules)

    def __repr__(self) -> str:
        return f"SelfAuditEngine(rules={len(self._rules)})"


# ---------------------------------------------------------------------------
# AutoFixer
# ---------------------------------------------------------------------------

class AutoFixer:
    """Attempts to auto-fix common issues in responses."""

    HEDGING_PHRASES = [
        "I believe", "it appears", "based on available information",
        "with some uncertainty", "to the best of my knowledge",
    ]

    OVERCONFIDENT_PATTERNS = [
        (r"\bI am certain\b", "I believe"),
        (r"\bI am sure\b", "I think"),
        (r"\bundoubtedly\b", "likely"),
        (r"\bunquestionably\b", "apparently"),
        (r"\b100% certain\b", "fairly confident"),
        (r"\bwithout a doubt\b", "in my assessment"),
        (r"\bI know for a fact\b", "I understand that"),
        (r"\bit is a fact that\b", "it appears that"),
    ]

    def fix_hallucinations(self, response: str, context: str) -> str:
        """Remove or qualify unsupported claims."""
        # Add a general qualification prefix
        qualifier = "[Note: Some claims in this response may require verification] "
        if not response.startswith("[Note:"):
            return qualifier + response
        return response

    def fix_overconfidence(self, response: str) -> str:
        """Add appropriate hedging language."""
        fixed = response
        for pattern, replacement in self.OVERCONFIDENT_PATTERNS:
            fixed = re.sub(pattern, replacement, fixed, flags=re.I)
        return fixed

    def fix_incompleteness(self, response: str, question: str) -> str:
        """Note what was not addressed."""
        note = f"\n\n[Note: This response may not fully address all aspects of the question. Additional detail may be needed.]"
        return response + note

    def fix_circular_reasoning(self, response: str) -> str:
        """Flag and explain the circular logic."""
        note = "\n\n[Warning: This response may contain circular reasoning. The conclusion should be supported by independent evidence.]"
        return response + note

    def __repr__(self) -> str:
        return "AutoFixer()"


# ---------------------------------------------------------------------------
# AuditLogger
# ---------------------------------------------------------------------------

class AuditLogger:
    """Logs all audits with persistence."""

    def __init__(self, path: Path = AUDIT_LOG_PATH):
        self.path = path
        self._log: List[Dict] = []
        self._load()

    def _load(self):
        if self.path.exists():
            with open(self.path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            self._log.append(json.loads(line))
                        except Exception:
                            pass

    def log(self, audit_result: AuditResult):
        """Persist an audit result."""
        entry = audit_result.to_dict()
        self._log.append(entry)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def stats(self) -> Dict[str, Any]:
        """Audit statistics."""
        if not self._log:
            return {"total": 0}
        total = len(self._log)
        passed = sum(1 for e in self._log if e.get("passed"))
        all_issues = [i for e in self._log for i in e.get("issues", [])]
        # Most common issues
        from collections import Counter
        rule_counts = Counter(i["rule_name"] for i in all_issues)
        fix_count = sum(1 for i in all_issues if i.get("fixed"))
        return {
            "total_audits": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total, 3) if total else 0,
            "total_issues": len(all_issues),
            "fix_rate": round(fix_count / max(len(all_issues), 1), 3),
            "most_common_issues": dict(rule_counts.most_common(5)),
            "avg_score": round(
                sum(e.get("overall_score", 0) for e in self._log) / total, 3
            ),
        }

    def recent(self, n: int = 10) -> List[Dict]:
        return self._log[-n:]

    def __repr__(self) -> str:
        return f"AuditLogger(records={len(self._log)}, path={self.path})"
