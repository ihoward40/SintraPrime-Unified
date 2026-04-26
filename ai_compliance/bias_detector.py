"""
bias_detector.py — Statistical Bias Detector for SintraPrime-Unified
Detects demographic bias in legal and financial AI outputs using statistical methods.
No external ML libraries required.
"""

from __future__ import annotations
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enumerations and Constants
# ---------------------------------------------------------------------------

class ProtectedCategory(str, Enum):
    RACE = "race"
    GENDER = "gender"
    AGE = "age"
    RELIGION = "religion"
    NATIONAL_ORIGIN = "national_origin"
    DISABILITY = "disability"
    SEXUAL_ORIENTATION = "sexual_orientation"
    PREGNANCY = "pregnancy"
    VETERAN_STATUS = "veteran_status"


class BiasType(str, Enum):
    EXPLICIT = "explicit"                 # Direct discriminatory language
    PROXY = "proxy"                       # Neutral variable correlated to protected class
    STATISTICAL_PARITY = "statistical_parity"  # Unequal positive outcome rates
    ADVERSE_IMPACT = "adverse_impact"     # 4/5ths rule violation
    REPRESENTATIONAL = "representational"  # Underrepresentation in output
    ASSOCIATIONAL = "associational"       # Negative associations with protected class


class BiasSeverity(str, Enum):
    CRITICAL = "critical"    # Must block output
    HIGH = "high"            # Must remediate before delivery
    MEDIUM = "medium"        # Flag for review
    LOW = "low"              # Document and monitor
    NONE = "none"            # No bias detected


ADVERSE_IMPACT_THRESHOLD = 0.80    # 4/5ths rule
STATISTICAL_PARITY_THRESHOLD = 0.10  # Max acceptable gap


# ---------------------------------------------------------------------------
# Bias Pattern Dictionaries
# ---------------------------------------------------------------------------

EXPLICIT_BIAS_PATTERNS: Dict[ProtectedCategory, List[str]] = {
    ProtectedCategory.RACE: [
        r"\b(blacks?|whites?|asians?|hispanics?|latinos?|caucasians?)\s+(are|tend|usually|typically|always|never)\b",
        r"\btypical\s+(black|white|asian|hispanic|latino)\b",
        r"\b(racial|ethnic)\s+(inferiority|superiority)\b",
        r"\bright\s+neighborhood\b",
        r"\bthose\s+people\b",
    ],
    ProtectedCategory.GENDER: [
        r"\b(women|men|females?|males?)\s+(can't|cannot|shouldn't|don't)\b",
        r"\b(too\s+emotional|not\s+logical|hysterical)\b",
        r"\bmanly|womanly\s+(profession|job|role)\b",
        r"\bnot\s+suitable\s+for\s+(women|men)\b",
    ],
    ProtectedCategory.AGE: [
        r"\b(too\s+old|past\s+their\s+prime|over\s+the\s+hill)\b",
        r"\b(old|older)\s+(people|workers|employees)\s+(can't|cannot|shouldn't|typically|usually|always|never)\b",
        r"\b(millennials?|boomers?|gen\s*z)\s+(are|always|never|typically)\b",
        r"\bolder\s+workers\s+\w+\s+(cannot|can't|won't|are\s+unable)\b",
    ],
    ProtectedCategory.RELIGION: [
        r"\b(christians?|muslims?|jews?|hindus?|buddhists?)\s+(are|tend|usually|always|never)\b",
        r"\breligious\s+extremist\b",
        r"\b(sharia|jihad)\s+(law|court|tribunal)\s+advocate\b",
    ],
    ProtectedCategory.NATIONAL_ORIGIN: [
        r"\b(immigrants?|foreigners?|aliens?)\s+(steal|take|don't|can't)\b",
        r"\bsend\s+them\s+back\b",
        r"\bnot\s+real\s+(american|citizen)\b",
    ],
    ProtectedCategory.DISABILITY: [
        r"\b(handicapped|crippled|retarded|crazy|insane)\s+(person|people|individual)\b",
        r"\bnormal\s+(people|persons|individuals)\s+vs\b",
        r"\bmentally\s+ill\s+(and\s+therefore|so\s+they)\b",
    ],
}

PROXY_VARIABLE_INDICATORS: Dict[str, ProtectedCategory] = {
    "zip code": ProtectedCategory.RACE,
    "neighborhood": ProtectedCategory.RACE,
    "school district": ProtectedCategory.RACE,
    "alma mater": ProtectedCategory.RACE,
    "years of experience": ProtectedCategory.AGE,
    "graduation year": ProtectedCategory.AGE,
    "native language": ProtectedCategory.NATIONAL_ORIGIN,
    "accent": ProtectedCategory.NATIONAL_ORIGIN,
    "availability on sundays": ProtectedCategory.RELIGION,
    "availability on saturdays": ProtectedCategory.RELIGION,
    "credit score": ProtectedCategory.RACE,
    "criminal history": ProtectedCategory.RACE,
}

POSITIVE_OUTCOME_WORDS = [
    "approve", "approved", "grant", "granted", "accept", "accepted",
    "recommend", "recommended", "eligible", "qualified", "suitable",
    "hire", "hired", "promote", "promoted", "award", "awarded",
    "favorable", "positive", "successful", "merit", "qualified",
]

NEGATIVE_OUTCOME_WORDS = [
    "deny", "denied", "reject", "rejected", "decline", "declined",
    "ineligible", "unqualified", "unsuitable", "terminate", "terminated",
    "demote", "unfavorable", "negative", "unsuccessful",
]


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class BiasIndicator:
    """A single detected bias indicator."""
    bias_type: BiasType
    category: ProtectedCategory
    severity: BiasSeverity
    description: str
    evidence: str                    # Snippet from output showing bias
    matched_pattern: Optional[str] = None


@dataclass
class GroupOutcome:
    """Outcome statistics for a demographic group."""
    group_label: str
    category: ProtectedCategory
    total_mentions: int
    positive_outcomes: int
    negative_outcomes: int

    @property
    def positive_rate(self) -> float:
        if self.total_mentions == 0:
            return 0.0
        return self.positive_outcomes / self.total_mentions

    @property
    def negative_rate(self) -> float:
        if self.total_mentions == 0:
            return 0.0
        return self.negative_outcomes / self.total_mentions


@dataclass
class StatisticalParityResult:
    """Result of statistical parity analysis across groups."""
    category: ProtectedCategory
    groups: List[GroupOutcome]
    max_gap: float
    passes_parity: bool
    adverse_impact_ratio: Optional[float]      # Lowest/Highest positive rate
    passes_adverse_impact: bool
    details: str


@dataclass
class BiasReport:
    """Complete bias analysis report for an AI output."""
    output_id: str
    output_text: str
    indicators: List[BiasIndicator]
    statistical_results: List[StatisticalParityResult]
    overall_severity: BiasSeverity
    bias_score: float                          # 0.0 (no bias) to 1.0 (severe bias)
    remediation_suggestions: List[str]
    proxy_variables_detected: List[str]
    analyzed_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_biased(self) -> bool:
        return self.overall_severity != BiasSeverity.NONE

    @property
    def requires_blocking(self) -> bool:
        return self.overall_severity == BiasSeverity.CRITICAL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "output_id": self.output_id,
            "is_biased": self.is_biased,
            "overall_severity": self.overall_severity.value,
            "bias_score": round(self.bias_score, 3),
            "requires_blocking": self.requires_blocking,
            "indicator_count": len(self.indicators),
            "indicators": [
                {
                    "type": i.bias_type.value,
                    "category": i.category.value,
                    "severity": i.severity.value,
                    "description": i.description,
                    "evidence": i.evidence[:100],
                }
                for i in self.indicators
            ],
            "proxy_variables": self.proxy_variables_detected,
            "remediation": self.remediation_suggestions,
            "analyzed_at": self.analyzed_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# Statistical Analysis Functions
# ---------------------------------------------------------------------------

def compute_adverse_impact_ratio(
    favorable_rate_protected: float,
    favorable_rate_majority: float,
) -> Optional[float]:
    """
    Compute 4/5ths adverse impact ratio.
    Returns None if majority rate is 0.
    EEOC guidelines: ratio < 0.80 indicates adverse impact.
    """
    if favorable_rate_majority == 0:
        return None
    return favorable_rate_protected / favorable_rate_majority


def compute_statistical_parity_gap(rates: List[float]) -> float:
    """
    Compute maximum gap between group positive rates.
    Gap > STATISTICAL_PARITY_THRESHOLD suggests disparity.
    """
    if len(rates) < 2:
        return 0.0
    return max(rates) - min(rates)


def extract_group_outcomes(
    text: str,
    category: ProtectedCategory,
    group_terms: List[str],
) -> List[GroupOutcome]:
    """
    Extract positive/negative outcome mentions near each group term.
    Uses a sliding window of ±50 characters.
    """
    text_lower = text.lower()
    outcomes: List[GroupOutcome] = []

    for group in group_terms:
        group_lower = group.lower()
        positions = [m.start() for m in re.finditer(re.escape(group_lower), text_lower)]

        if not positions:
            continue

        positive_count = 0
        negative_count = 0

        for pos in positions:
            window_start = max(0, pos - 80)
            window_end = min(len(text_lower), pos + 80)
            window = text_lower[window_start:window_end]

            for word in POSITIVE_OUTCOME_WORDS:
                if word in window:
                    positive_count += 1

            for word in NEGATIVE_OUTCOME_WORDS:
                if word in window:
                    negative_count += 1

        outcomes.append(GroupOutcome(
            group_label=group,
            category=category,
            total_mentions=len(positions),
            positive_outcomes=positive_count,
            negative_outcomes=negative_count,
        ))

    return outcomes


# ---------------------------------------------------------------------------
# Main Bias Detector
# ---------------------------------------------------------------------------

DEMOGRAPHIC_GROUP_TERMS: Dict[ProtectedCategory, List[str]] = {
    ProtectedCategory.RACE: [
        "Black", "White", "Asian", "Hispanic", "Latino", "African American",
        "Caucasian", "Native American", "Pacific Islander",
    ],
    ProtectedCategory.GENDER: [
        "women", "men", "female", "male", "woman", "man", "nonbinary",
    ],
    ProtectedCategory.AGE: [
        "young", "older", "elderly", "senior", "millennial", "boomer", "Gen Z",
    ],
    ProtectedCategory.RELIGION: [
        "Christian", "Muslim", "Jewish", "Hindu", "Buddhist", "atheist", "secular",
    ],
    ProtectedCategory.NATIONAL_ORIGIN: [
        "American", "immigrant", "foreign-born", "Mexican", "Chinese", "Indian",
    ],
    ProtectedCategory.DISABILITY: [
        "disabled", "able-bodied", "wheelchair", "blind", "deaf", "neurodivergent",
    ],
}


class BiasDetector:
    """
    Comprehensive bias detector using statistical and pattern-matching methods.
    Checks legal/financial AI outputs for demographic bias across all protected categories.
    """

    def __init__(
        self,
        adverse_impact_threshold: float = ADVERSE_IMPACT_THRESHOLD,
        parity_threshold: float = STATISTICAL_PARITY_THRESHOLD,
    ):
        self.adverse_impact_threshold = adverse_impact_threshold
        self.parity_threshold = parity_threshold

    def analyze(self, output_text: str, output_id: Optional[str] = None) -> BiasReport:
        """
        Perform full bias analysis on an AI output text.
        """
        import uuid
        if not output_id:
            output_id = str(uuid.uuid4())[:8]

        indicators: List[BiasIndicator] = []
        statistical_results: List[StatisticalParityResult] = []

        # 1. Explicit bias pattern detection
        indicators.extend(self._detect_explicit_bias(output_text))

        # 2. Proxy variable detection
        proxy_vars = self._detect_proxy_variables(output_text)

        # 3. Statistical parity analysis
        for category, group_terms in DEMOGRAPHIC_GROUP_TERMS.items():
            result = self._analyze_statistical_parity(output_text, category, group_terms)
            if result:
                statistical_results.append(result)
                if not result.passes_parity:
                    indicators.append(BiasIndicator(
                        bias_type=BiasType.STATISTICAL_PARITY,
                        category=category,
                        severity=BiasSeverity.MEDIUM,
                        description=f"Statistical parity gap of {result.max_gap:.2%} detected for {category.value}.",
                        evidence=result.details,
                    ))
                if not result.passes_adverse_impact and result.adverse_impact_ratio is not None:
                    indicators.append(BiasIndicator(
                        bias_type=BiasType.ADVERSE_IMPACT,
                        category=category,
                        severity=BiasSeverity.HIGH,
                        description=(
                            f"Adverse impact ratio {result.adverse_impact_ratio:.2f} below 4/5ths "
                            f"threshold ({self.adverse_impact_threshold}) for {category.value}."
                        ),
                        evidence=result.details,
                    ))

        # 4. Proxy variable bias indicators
        for proxy in proxy_vars:
            associated_category = PROXY_VARIABLE_INDICATORS.get(proxy.lower(), ProtectedCategory.RACE)
            indicators.append(BiasIndicator(
                bias_type=BiasType.PROXY,
                category=associated_category,
                severity=BiasSeverity.LOW,
                description=f"Proxy variable '{proxy}' may correlate with protected category {associated_category.value}.",
                evidence=proxy,
            ))

        # 5. Compute overall severity and score
        overall_severity = self._compute_overall_severity(indicators)
        bias_score = self._compute_bias_score(indicators)

        # 6. Generate remediation
        remediation = self._generate_remediation(indicators, statistical_results)

        return BiasReport(
            output_id=output_id,
            output_text=output_text,
            indicators=indicators,
            statistical_results=statistical_results,
            overall_severity=overall_severity,
            bias_score=bias_score,
            remediation_suggestions=remediation,
            proxy_variables_detected=proxy_vars,
        )

    def _detect_explicit_bias(self, text: str) -> List[BiasIndicator]:
        """Detect explicit bias language using regex patterns."""
        indicators: List[BiasIndicator] = []

        for category, patterns in EXPLICIT_BIAS_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    full_match = re.search(pattern, text, re.IGNORECASE)
                    evidence = full_match.group(0) if full_match else str(matches[:2])
                    indicators.append(BiasIndicator(
                        bias_type=BiasType.EXPLICIT,
                        category=category,
                        severity=BiasSeverity.CRITICAL,
                        description=f"Explicit bias language detected for {category.value}.",
                        evidence=evidence,
                        matched_pattern=pattern,
                    ))

        return indicators

    def _detect_proxy_variables(self, text: str) -> List[str]:
        """Detect proxy variables that may encode protected characteristics."""
        detected: List[str] = []
        text_lower = text.lower()

        for proxy in PROXY_VARIABLE_INDICATORS:
            if proxy.lower() in text_lower:
                detected.append(proxy)

        return detected

    def _analyze_statistical_parity(
        self,
        text: str,
        category: ProtectedCategory,
        group_terms: List[str],
    ) -> Optional[StatisticalParityResult]:
        """Run statistical parity analysis for a demographic category."""
        groups = extract_group_outcomes(text, category, group_terms)

        # Only analyze if multiple groups mentioned with outcome words
        active_groups = [g for g in groups if g.total_mentions > 0 and
                         (g.positive_outcomes + g.negative_outcomes) > 0]

        if len(active_groups) < 2:
            return None

        positive_rates = [g.positive_rate for g in active_groups]
        max_gap = compute_statistical_parity_gap(positive_rates)
        passes_parity = max_gap <= self.parity_threshold

        # Adverse impact: lowest positive rate / highest positive rate
        if max(positive_rates) > 0:
            air = min(positive_rates) / max(positive_rates)
            passes_adverse_impact = air >= self.adverse_impact_threshold
        else:
            air = None
            passes_adverse_impact = True

        details = "; ".join(
            f"{g.group_label}: {g.positive_rate:.1%} positive rate"
            for g in active_groups
        )

        return StatisticalParityResult(
            category=category,
            groups=active_groups,
            max_gap=max_gap,
            passes_parity=passes_parity,
            adverse_impact_ratio=air,
            passes_adverse_impact=passes_adverse_impact,
            details=details,
        )

    @staticmethod
    def _compute_overall_severity(indicators: List[BiasIndicator]) -> BiasSeverity:
        if not indicators:
            return BiasSeverity.NONE
        severities = {i.severity for i in indicators}
        if BiasSeverity.CRITICAL in severities:
            return BiasSeverity.CRITICAL
        if BiasSeverity.HIGH in severities:
            return BiasSeverity.HIGH
        if BiasSeverity.MEDIUM in severities:
            return BiasSeverity.MEDIUM
        if BiasSeverity.LOW in severities:
            return BiasSeverity.LOW
        return BiasSeverity.NONE

    @staticmethod
    def _compute_bias_score(indicators: List[BiasIndicator]) -> float:
        """Score from 0.0 (no bias) to 1.0 (severe bias)."""
        if not indicators:
            return 0.0

        weights = {
            BiasSeverity.CRITICAL: 0.40,
            BiasSeverity.HIGH: 0.25,
            BiasSeverity.MEDIUM: 0.15,
            BiasSeverity.LOW: 0.05,
            BiasSeverity.NONE: 0.0,
        }
        raw_score = sum(weights.get(i.severity, 0.0) for i in indicators)
        return min(1.0, raw_score)

    @staticmethod
    def _generate_remediation(
        indicators: List[BiasIndicator],
        statistical_results: List[StatisticalParityResult],
    ) -> List[str]:
        suggestions: List[str] = []

        if any(i.bias_type == BiasType.EXPLICIT for i in indicators):
            suggestions.append(
                "CRITICAL: Remove all explicit demographic bias language from the output. "
                "Replace with neutral, fact-based descriptions."
            )

        if any(i.bias_type == BiasType.ADVERSE_IMPACT for i in indicators):
            suggestions.append(
                "Adverse impact detected: review decision criteria and remove or reweight "
                "factors that disproportionately disadvantage protected groups."
            )

        if any(i.bias_type == BiasType.STATISTICAL_PARITY for i in indicators):
            suggestions.append(
                "Statistical parity gap detected: calibrate model outputs to ensure "
                "equitable treatment across demographic groups."
            )

        if any(i.bias_type == BiasType.PROXY for i in indicators):
            suggestions.append(
                "Proxy variables detected: evaluate whether these variables are strictly necessary "
                "and whether they encode protected characteristics through disparate impact analysis."
            )

        suggestions.append(
            "Conduct annual bias audit by an independent third party as required by NYC Local Law 144 "
            "and CO SB 205 for high-risk AI systems."
        )
        suggestions.append(
            "Document bias testing methodology and results in AI system technical documentation."
        )

        return suggestions


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

_default_detector = BiasDetector()


def check_bias(text: str, output_id: Optional[str] = None) -> BiasReport:
    """Quick bias check on a text output."""
    return _default_detector.analyze(text, output_id)


def compute_group_adverse_impact(
    group_outcomes: Dict[str, int],
    group_totals: Dict[str, int],
) -> Dict[str, float]:
    """
    Compute adverse impact ratios for multiple groups.

    Args:
        group_outcomes: {group_name: favorable_outcomes_count}
        group_totals: {group_name: total_decisions_count}

    Returns:
        Dict mapping group name to adverse impact ratio vs best-performing group.
    """
    rates = {}
    for group, total in group_totals.items():
        if total > 0:
            rates[group] = group_outcomes.get(group, 0) / total

    if not rates:
        return {}

    max_rate = max(rates.values())
    if max_rate == 0:
        return {g: 1.0 for g in rates}

    return {group: rate / max_rate for group, rate in rates.items()}


if __name__ == "__main__":
    sample_text = (
        "Based on our analysis, applicants from the downtown area are typically "
        "more likely to be approved for the premium tier. Older applicants tend to "
        "have more experience. We recommend approving applicants with zip codes in "
        "the 9000x range for the best outcomes."
    )
    report = check_bias(sample_text)
    print(f"Bias Score: {report.bias_score:.3f}")
    print(f"Severity: {report.overall_severity.value}")
    print(f"Indicators: {len(report.indicators)}")
    print(f"Proxy Variables: {report.proxy_variables_detected}")
    for suggestion in report.remediation_suggestions:
        print(f"  → {suggestion}")
