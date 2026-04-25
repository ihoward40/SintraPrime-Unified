"""
Judge Analyzer - Comprehensive Judicial Intelligence

Provides detailed analysis of judge tendencies, preferences, and decision patterns
to inform litigation strategy and predict judicial outcomes.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum


class OralArgumentStyle(Enum):
    """Judge's approach to oral arguments."""
    SOCRATIC = "socratic"  # Asks probing questions
    PASSIVE = "passive"  # Limited interaction
    HOSTILE = "hostile"  # Challenges counsel aggressively
    MIXED = "mixed"


@dataclass
class JudgeProfile:
    """Comprehensive profile of a judicial officer."""
    judge_id: str
    judge_name: str
    court: str
    jurisdiction: str
    
    # Background
    education: List[str] = field(default_factory=list)
    prior_positions: List[str] = field(default_factory=list)
    appointing_president: Optional[str] = None
    party_affiliation: Optional[str] = None  # "Democrat", "Republican", "Independent"
    years_on_bench: int = 0
    total_cases_decided: int = 0
    
    # Decision patterns by case type
    civil_rights_plaintiff_win_rate: float = 0.5
    contract_plaintiff_win_rate: float = 0.5
    tort_plaintiff_win_rate: float = 0.5
    criminal_conviction_rate: float = 0.5
    employment_plaintiff_win_rate: float = 0.5
    ip_plaintiff_win_rate: float = 0.5
    family_plaintiff_win_rate: float = 0.5
    
    # Average decision times
    avg_days_to_decision_civil: int = 365
    avg_days_to_decision_criminal: int = 180
    avg_days_to_decision_family: int = 240
    
    # Motion grant rates
    summary_judgment_grant_rate: float = 0.45
    class_certification_grant_rate: float = 0.35
    injunction_grant_rate: float = 0.40
    mtd_grant_rate: float = 0.40
    
    # Reversal and appeal rates
    reversal_rate: float = 0.10
    reversal_rate_by_circuit: Dict[str, float] = field(default_factory=dict)
    precedent_adherence_score: float = 0.9  # How often follows precedent (0-1)
    
    # Criminal sentencing patterns (for judges who do criminal)
    avg_sentence_length_felony_months: Optional[int] = None
    sentence_leniency_vs_guidelines: float = 0.0  # -1 to +1, negative = lenient
    drug_sentencing_pattern: str = "moderate"  # "harsh", "moderate", "lenient"
    
    # Preferences and style
    written_opinion_detail: str = "moderate"  # "sparse", "moderate", "detailed"
    oral_argument_style: OralArgumentStyle = OralArgumentStyle.MIXED
    brief_length_tolerance: str = "standard"  # "strict", "standard", "generous"
    discovery_dispute_approach: str = "balanced"  # "pro-plaintiff", "balanced", "pro-defendant"
    
    # Published opinions and ideology (if applicable)
    total_published_opinions: int = 0
    political_lean: Optional[str] = None  # "progressive", "moderate", "conservative"
    
    # Specific case preferences
    prefers_bench_trial: bool = False
    motion_practice_style: str = "standard"  # "permissive", "standard", "restrictive"
    amicus_influence_receptiveness: float = 0.5  # 0-1
    
    # Recent statistics (last 2 years)
    recent_disposition_rate: float = 0.7  # Fraction of cases disposed
    recent_settlement_approval_rate: float = 0.85
    
    profile_date: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TendencyReport:
    """Analysis of a judge's tendencies in a specific case type."""
    judge_id: str
    case_type: str
    plaintiff_win_rate: float
    defendant_win_rate: float
    average_judgment_amount: float
    average_days_to_decision: int
    motion_grant_rates: Dict[str, float]
    reversal_rate: float
    key_patterns: List[str]
    recommendations: List[str]
    analysis_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class StrategyRecommendations:
    """Recommended litigation strategy based on judge profile."""
    judge_id: str
    case_type: str
    
    # Motion strategy
    motion_strategy: str
    mtd_viability: float  # 0-1 probability of success
    msj_viability: float
    summary_judgment_defensive_strategy: str
    
    # Discovery strategy
    discovery_pace: str  # "aggressive", "standard", "deliberate"
    discovery_scope_focus: List[str]  # What to prioritize
    deposition_target_order: List[str]
    e_discovery_volume_assessment: str
    
    # Trial strategy
    trial_type_recommendation: str  # "bench", "jury", "either"
    jury_preference_notes: Optional[str] = None
    bench_trial_preparation: List[str] = field(default_factory=list)
    
    # Brief and argument
    brief_length_recommendation: str
    legal_theory_emphasis: List[str]  # Strongest theories for this judge
    precedent_strategy: List[str]  # Which precedents to emphasize
    oral_argument_length: str  # "minimal", "standard", "extended"
    
    # Timeline
    recommended_filing_timeline: str
    optimal_decision_point: str  # When to push for decision
    
    # Risk factors
    judge_specific_risks: List[str]
    mitigation_strategies: List[str]


@dataclass
class JudgeComparison:
    """Comparison between multiple judges."""
    judge_ids: List[str]
    judge_names: List[str]
    case_type: str
    
    # Comparative metrics
    plaintiff_win_rates: Dict[str, float]  # judge_name -> win_rate
    defendant_win_rates: Dict[str, float]
    reversal_rates: Dict[str, float]
    decision_speed: Dict[str, int]  # judge_name -> avg days
    
    # Comparative analysis
    most_plaintiff_friendly: str
    most_defendant_friendly: str
    fastest_decider: str
    most_likely_to_reverse: str
    detailed_comparison: str


class JudgeAnalyzer:
    """
    Analyzes judicial officer tendencies and provides intelligence
    for litigation strategy optimization.
    """
    
    def __init__(self):
        """Initialize judge analyzer with sample data."""
        self.judge_database: Dict[str, JudgeProfile] = {}
        self._initialize_sample_judges()
    
    def _initialize_sample_judges(self):
        """Initialize with sample judge profiles for demonstration."""
        # Sample federal judge profiles
        self.judge_database['judge_001'] = JudgeProfile(
            judge_id='judge_001',
            judge_name='Judge Sarah Mitchell',
            court='U.S. District Court',
            jurisdiction='Northern District of California',
            education=['Stanford Law School', 'Berkeley College of Law'],
            prior_positions=['General Counsel, Tech Corp', 'Law Professor'],
            appointing_president='Obama',
            party_affiliation='Democrat',
            years_on_bench=12,
            total_cases_decided=1850,
            civil_rights_plaintiff_win_rate=0.68,
            contract_plaintiff_win_rate=0.52,
            tort_plaintiff_win_rate=0.58,
            employment_plaintiff_win_rate=0.62,
            ip_plaintiff_win_rate=0.48,
            summary_judgment_grant_rate=0.38,
            class_certification_grant_rate=0.52,
            injunction_grant_rate=0.58,
            reversal_rate=0.12,
            precedent_adherence_score=0.92,
            written_opinion_detail='detailed',
            oral_argument_style=OralArgumentStyle.SOCRATIC,
            brief_length_tolerance='generous',
            discovery_dispute_approach='pro-plaintiff',
            political_lean='progressive',
            prefers_bench_trial=False,
            motion_practice_style='permissive',
            recent_disposition_rate=0.75,
            recent_settlement_approval_rate=0.88,
        )
        
        self.judge_database['judge_002'] = JudgeProfile(
            judge_id='judge_002',
            judge_name='Judge Robert Chen',
            court='U.S. District Court',
            jurisdiction='Southern District of New York',
            education=['Yale Law School', 'Columbia University'],
            prior_positions=['Partner, Major Law Firm', 'Corporate Counsel'],
            appointing_president='Trump',
            party_affiliation='Republican',
            years_on_bench=8,
            total_cases_decided=1200,
            civil_rights_plaintiff_win_rate=0.42,
            contract_plaintiff_win_rate=0.48,
            tort_plaintiff_win_rate=0.44,
            employment_plaintiff_win_rate=0.38,
            ip_plaintiff_win_rate=0.56,
            summary_judgment_grant_rate=0.62,
            class_certification_grant_rate=0.22,
            injunction_grant_rate=0.35,
            reversal_rate=0.15,
            precedent_adherence_score=0.88,
            written_opinion_detail='sparse',
            oral_argument_style=OralArgumentStyle.HOSTILE,
            brief_length_tolerance='strict',
            discovery_dispute_approach='balanced',
            political_lean='conservative',
            prefers_bench_trial=True,
            motion_practice_style='restrictive',
            recent_disposition_rate=0.82,
            recent_settlement_approval_rate=0.92,
        )
        
        self.judge_database['judge_003'] = JudgeProfile(
            judge_id='judge_003',
            judge_name='Judge Maria Garcia',
            court='U.S. District Court',
            jurisdiction='Central District of California',
            education=['UCLA Law School', 'USC'],
            prior_positions=['Public Defender', 'Civil Rights Attorney'],
            appointing_president='Biden',
            party_affiliation='Democrat',
            years_on_bench=4,
            total_cases_decided=600,
            civil_rights_plaintiff_win_rate=0.71,
            contract_plaintiff_win_rate=0.55,
            tort_plaintiff_win_rate=0.62,
            employment_plaintiff_win_rate=0.68,
            ip_plaintiff_win_rate=0.51,
            summary_judgment_grant_rate=0.32,
            class_certification_grant_rate=0.58,
            injunction_grant_rate=0.62,
            reversal_rate=0.08,
            precedent_adherence_score=0.94,
            written_opinion_detail='detailed',
            oral_argument_style=OralArgumentStyle.SOCRATIC,
            brief_length_tolerance='generous',
            discovery_dispute_approach='pro-plaintiff',
            political_lean='progressive',
            prefers_bench_trial=False,
            motion_practice_style='permissive',
            amicus_influence_receptiveness=0.7,
            recent_disposition_rate=0.68,
            recent_settlement_approval_rate=0.85,
        )
    
    def get_judge_profile(self, judge_name: str, court: str) -> Optional[JudgeProfile]:
        """
        Retrieve judge profile by name and court.
        
        Args:
            judge_name: Name of the judge
            court: Court where judge serves
            
        Returns:
            JudgeProfile if found, None otherwise
        """
        for profile in self.judge_database.values():
            if profile.judge_name.lower() == judge_name.lower() and \
               profile.court.lower() == court.lower():
                return profile
        return None
    
    def analyze_judge_tendencies(
        self,
        judge_id: str,
        case_type: str
    ) -> Optional[TendencyReport]:
        """
        Analyze a judge's tendencies in a specific case type.
        
        Args:
            judge_id: Judge identifier
            case_type: Type of case ("civil_rights", "contract", etc.)
            
        Returns:
            TendencyReport with detailed analysis
        """
        profile = self.judge_database.get(judge_id)
        if not profile:
            return None
        
        # Get win rates by case type
        win_rate_map = {
            'civil_rights': profile.civil_rights_plaintiff_win_rate,
            'contract': profile.contract_plaintiff_win_rate,
            'tort': profile.tort_plaintiff_win_rate,
            'criminal': profile.criminal_conviction_rate,
            'employment': profile.employment_plaintiff_win_rate,
            'ip': profile.ip_plaintiff_win_rate,
            'family': profile.family_plaintiff_win_rate,
        }
        
        plaintiff_win_rate = win_rate_map.get(case_type.lower(), 0.5)
        defendant_win_rate = 1.0 - plaintiff_win_rate
        
        # Get average decision time
        time_map = {
            'civil': profile.avg_days_to_decision_civil,
            'criminal': profile.avg_days_to_decision_criminal,
            'family': profile.avg_days_to_decision_family,
        }
        avg_days = time_map.get('civil', 365)
        
        # Motion grant rates
        motion_grants = {
            'summary_judgment': profile.summary_judgment_grant_rate,
            'class_certification': profile.class_certification_grant_rate,
            'injunction': profile.injunction_grant_rate,
            'mtd': profile.mtd_grant_rate,
        }
        
        # Identify key patterns
        patterns = []
        if plaintiff_win_rate > 0.60:
            patterns.append(f"Plaintiff-friendly in {case_type} cases")
        elif plaintiff_win_rate < 0.45:
            patterns.append(f"Defendant-friendly in {case_type} cases")
        
        if profile.reversal_rate > 0.12:
            patterns.append("Higher than average reversal rate")
        
        if profile.summary_judgment_grant_rate > 0.55:
            patterns.append("Grants summary judgment frequently")
        
        if profile.class_certification_grant_rate > 0.50:
            patterns.append("Favorable to class certification")
        
        # Generate recommendations
        recommendations = self._generate_tendency_recommendations(
            profile, case_type, plaintiff_win_rate, patterns
        )
        
        return TendencyReport(
            judge_id=judge_id,
            case_type=case_type,
            plaintiff_win_rate=plaintiff_win_rate,
            defendant_win_rate=defendant_win_rate,
            average_judgment_amount=100000.0,  # Placeholder
            average_days_to_decision=avg_days,
            motion_grant_rates=motion_grants,
            reversal_rate=profile.reversal_rate,
            key_patterns=patterns,
            recommendations=recommendations,
        )
    
    def _generate_tendency_recommendations(
        self,
        profile: JudgeProfile,
        case_type: str,
        plaintiff_win_rate: float,
        patterns: List[str]
    ) -> List[str]:
        """Generate recommendations based on judge tendencies."""
        recommendations = []
        
        if plaintiff_win_rate > 0.60:
            recommendations.append(
                "This judge is plaintiff-friendly - emphasize client's damages and liability"
            )
        elif plaintiff_win_rate < 0.45:
            recommendations.append(
                "This judge favors defendants - focus on procedural defenses and burden of proof"
            )
        
        if profile.oral_argument_style == OralArgumentStyle.SOCRATIC:
            recommendations.append(
                "Prepare for probing questions during oral argument - have detailed answers ready"
            )
        elif profile.oral_argument_style == OralArgumentStyle.HOSTILE:
            recommendations.append(
                "Expect aggressive questioning - remain composed and well-prepared"
            )
        
        if profile.summary_judgment_grant_rate > 0.55:
            recommendations.append(
                "Be prepared to oppose summary judgment with strong factual development"
            )
        
        if profile.class_certification_grant_rate > 0.50 and case_type == 'employment':
            recommendations.append(
                "Class certification likely - prepare class-wide arguments early"
            )
        
        if profile.brief_length_tolerance == 'strict':
            recommendations.append(
                "This judge prefers concise briefs - cut unnecessary content"
            )
        elif profile.brief_length_tolerance == 'generous':
            recommendations.append(
                "This judge tolerates detailed briefs - provide thorough legal analysis"
            )
        
        return recommendations[:5]
    
    def get_win_rate(
        self,
        judge_id: str,
        case_type: str,
        party_side: str
    ) -> float:
        """
        Get win rate for a specific party in front of this judge.
        
        Args:
            judge_id: Judge identifier
            case_type: Type of case
            party_side: "plaintiff", "defendant", or "prosecutor"
            
        Returns:
            Estimated win probability (0-1)
        """
        profile = self.judge_database.get(judge_id)
        if not profile:
            return 0.5
        
        win_rate_map = {
            'civil_rights': profile.civil_rights_plaintiff_win_rate,
            'contract': profile.contract_plaintiff_win_rate,
            'tort': profile.tort_plaintiff_win_rate,
            'criminal': profile.criminal_conviction_rate,
            'employment': profile.employment_plaintiff_win_rate,
            'ip': profile.ip_plaintiff_win_rate,
        }
        
        plaintiff_rate = win_rate_map.get(case_type.lower(), 0.5)
        
        if party_side.lower() in ['plaintiff', 'prosecutor']:
            return plaintiff_rate
        else:  # defendant
            return 1.0 - plaintiff_rate
    
    def recommend_strategy(
        self,
        judge_id: str,
        case_type: str
    ) -> Optional[StrategyRecommendations]:
        """
        Generate litigation strategy recommendations for this judge.
        
        Args:
            judge_id: Judge identifier
            case_type: Type of case
            
        Returns:
            StrategyRecommendations object
        """
        profile = self.judge_database.get(judge_id)
        if not profile:
            return None
        
        # Determine motion viability
        mtd_viability = 1.0 - profile.mtd_grant_rate
        msj_viability = 1.0 - profile.summary_judgment_grant_rate
        
        # Motion strategy
        if profile.summary_judgment_grant_rate > 0.55:
            motion_strategy = "Aggressive SJ - focus on liability development"
        else:
            motion_strategy = "Standard motion practice"
        
        # Trial strategy
        if profile.prefers_bench_trial:
            trial_recommendation = "bench"
        else:
            trial_recommendation = "jury"
        
        # Discovery strategy
        if profile.discovery_dispute_approach == 'pro-plaintiff':
            discovery_pace = "aggressive"
        else:
            discovery_pace = "standard"
        
        # Brief recommendations
        if profile.brief_length_tolerance == 'strict':
            brief_length = "concise (20 pages or less)"
        elif profile.brief_length_tolerance == 'generous':
            brief_length = "detailed (30+ pages)"
        else:
            brief_length = "standard (25 pages)"
        
        return StrategyRecommendations(
            judge_id=judge_id,
            case_type=case_type,
            motion_strategy=motion_strategy,
            mtd_viability=mtd_viability,
            msj_viability=msj_viability,
            summary_judgment_defensive_strategy="Develop detailed factual record",
            discovery_pace=discovery_pace,
            discovery_scope_focus=["Admissions", "Documents", "Interrogatories"],
            deposition_target_order=["Key witnesses", "Experts", "Defendants"],
            trial_type_recommendation=trial_recommendation,
            jury_preference_notes=None if trial_recommendation == "bench" else
                "Jury may be more sympathetic to plaintiff's arguments",
            bench_trial_preparation=[
                "Prepare detailed factual record",
                "Cite precedent extensively",
                "Emphasize burden of proof",
            ],
            brief_length_recommendation=brief_length,
            legal_theory_emphasis=["Primary theory", "Alternative theory"],
            precedent_strategy=["Leading circuit precedent", "District precedent"],
            oral_argument_length="15 minutes prepared" if profile.oral_argument_style == OralArgumentStyle.PASSIVE
                else "Full 30 minutes available",
            recommended_filing_timeline="Standard",
            optimal_decision_point="After discovery complete",
            judge_specific_risks=[],
            mitigation_strategies=[],
        )
    
    def compare_judges(self, judge_ids: List[str]) -> Optional[JudgeComparison]:
        """
        Compare multiple judges across key metrics.
        
        Args:
            judge_ids: List of judge identifiers
            
        Returns:
            JudgeComparison object
        """
        profiles = [
            self.judge_database.get(jid) for jid in judge_ids
        ]
        if not all(profiles):
            return None
        
        case_type = 'employment'  # Default comparison case type
        
        plaintiff_rates = {
            p.judge_name: p.employment_plaintiff_win_rate
            for p in profiles
        }
        defendant_rates = {
            p.judge_name: 1.0 - p.employment_plaintiff_win_rate
            for p in profiles
        }
        reversal_rates = {
            p.judge_name: p.reversal_rate
            for p in profiles
        }
        decision_speeds = {
            p.judge_name: p.avg_days_to_decision_civil
            for p in profiles
        }
        
        most_plaintiff_friendly = max(plaintiff_rates.items(), key=lambda x: x[1])[0]
        most_defendant_friendly = max(defendant_rates.items(), key=lambda x: x[1])[0]
        fastest_decider = min(decision_speeds.items(), key=lambda x: x[1])[0]
        most_likely_to_reverse = max(reversal_rates.items(), key=lambda x: x[1])[0]
        
        return JudgeComparison(
            judge_ids=judge_ids,
            judge_names=[p.judge_name for p in profiles],
            case_type=case_type,
            plaintiff_win_rates=plaintiff_rates,
            defendant_win_rates=defendant_rates,
            reversal_rates=reversal_rates,
            decision_speed=decision_speeds,
            most_plaintiff_friendly=most_plaintiff_friendly,
            most_defendant_friendly=most_defendant_friendly,
            fastest_decider=fastest_decider,
            most_likely_to_reverse=most_likely_to_reverse,
            detailed_comparison="See individual judge profiles for detailed analysis",
        )
    
    def get_bench_memo_recommendations(
        self,
        judge_id: str,
        case_type: str
    ) -> List[str]:
        """
        Get bench memo recommendations based on judge preferences.
        
        Args:
            judge_id: Judge identifier
            case_type: Type of case
            
        Returns:
            List of memo recommendations
        """
        profile = self.judge_database.get(judge_id)
        if not profile:
            return []
        
        recommendations = [
            f"Judge {profile.judge_name} prefers "
            f"{profile.written_opinion_detail} opinions",
            f"Expect decision within {profile.avg_days_to_decision_civil} days",
            f"Judge's summary judgment grant rate: {profile.summary_judgment_grant_rate:.0%}",
            f"Judge's class certification grant rate: {profile.class_certification_grant_rate:.0%}",
            f"Oral argument style: {profile.oral_argument_style.value}",
        ]
        
        return recommendations
