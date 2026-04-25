"""
Case Strategy Optimizer - AI-Driven Litigation Strategy

Optimizes motion strategy, discovery planning, trial strategy, and appeals
based on case characteristics and judge analysis.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime


class TrialType(Enum):
    """Trial type recommendation."""
    BENCH = "bench"
    JURY = "jury"
    EITHER = "either"


@dataclass
class MotionStrategy:
    """Recommended motion filing strategy."""
    case_id: str
    
    # Dismissal motions
    mtd_recommendation: str  # "file", "defer", "avoid"
    mtd_success_probability: float  # 0-1
    mtd_timing: str  # "early", "standard", "late"
    mtd_legal_theories: List[str]
    
    # Summary judgment
    msj_recommendation: str
    msj_success_probability: float
    msj_timing: str
    msj_focus_areas: List[str]
    
    # Other motions
    motion_in_limine_topics: List[str]
    pretrial_conference_strategy: str
    
    # Risk assessment
    adverse_motion_risk: List[str]  # Motions opponent likely to file
    counter_strategies: List[str]  # How to defeat adverse motions
    
    # Procedural
    estimated_motion_costs: float
    expected_timeline_impact_days: int


@dataclass
class DiscoveryPlan:
    """Comprehensive discovery strategy."""
    case_id: str
    
    # Scope and depth
    scope_breadth: str  # "narrow", "standard", "broad", "aggressive"
    priority_topics: List[str]  # Top discovery targets
    
    # Document discovery
    document_request_strategy: str
    expected_document_volume: str  # "small", "moderate", "large", "voluminous"
    e_discovery_complexity: str  # "simple", "moderate", "complex"
    e_discovery_cost_estimate: float
    
    # Interrogatories
    interrogatory_count: int
    interrogatory_focus: List[str]
    
    # Depositions
    deposition_strategy: str
    priority_deposition_targets: List[str]
    estimated_deposition_count: int
    estimated_deposition_duration_days: int
    deposition_cost_estimate: float
    
    # Expert discovery
    expert_witnesses_needed: int
    expert_disciplines: List[str]
    expert_discovery_timeline: str
    
    # Requests for Admission
    admission_count: int
    admission_strategy: str
    
    # Timeline
    discovery_phase_duration_months: int
    critical_discovery_deadlines: List[Tuple[str, int]]  # (Milestone, Days from start)
    
    # Costs and metrics
    total_discovery_cost_estimate: float
    expected_cost_per_document_page: float


@dataclass
class TrialStrategy:
    """Recommended trial strategy."""
    case_id: str
    
    # Trial type
    trial_type_recommendation: TrialType
    trial_type_rationale: str
    jury_vs_bench_factors: Dict[str, float]  # Factor -> impact score
    
    # Legal theory selection
    primary_legal_theory: str
    secondary_theories: List[str]
    theories_to_avoid: List[str]
    theory_win_probability_map: Dict[str, float]
    
    # Factual presentation
    key_facts_to_emphasize: List[str]
    facts_to_minimize: List[str]
    narrative_arc: str  # Overall story to tell
    
    # Witness strategy
    key_witness_testimony_order: List[str]
    witness_preparation_priorities: List[str]
    expert_witness_recommendations: List[str]
    
    # Evidence strategy
    demonstrative_evidence_recommendations: List[str]
    visual_strategy: str
    technology_use_recommendations: List[str]
    
    # Argument strategy
    opening_statement_focus: str
    closing_argument_themes: List[str]
    anticipated_defense_arguments: List[str]
    counter_argument_preparation: List[str]
    
    # Verdict considerations
    verdict_form_strategy: str
    damages_presentation_strategy: str
    
    # Timeline
    trial_duration_estimate_days: int
    critical_trial_dates: List[Tuple[str, str]]  # (Event, Estimated Date)
    
    # Optional fields with defaults
    special_verdict_questions: Optional[List[str]] = None


@dataclass
class AppealAnalysis:
    """Analysis of appeal viability and strategy."""
    case_id: str
    trial_outcome: Dict[str, any]  # Trial result data
    
    # Appeal viability
    appeal_viability_score: float  # 0-1
    appeal_viability_assessment: str  # "strong", "moderate", "weak", "not viable"
    
    # Grounds for appeal
    potential_appeal_grounds: List[str]
    strongest_grounds: str
    weakest_potential_grounds: List[str]
    
    # Appellate judge analysis
    appellate_court: str
    recent_precedent_favorable: bool
    recent_precedent_summary: str
    
    # Strategy
    optimal_appeal_arguments: List[str]
    arguments_to_avoid: List[str]
    briefing_strategy: str
    
    # Likelihood of success
    estimated_win_probability_appeal: float
    estimated_reversal_probability: float
    
    # Cost and timeline
    estimated_appeal_cost: float
    estimated_appeal_timeline_months: int
    expected_decision_timeline: str
    
    # Risk mitigation
    rehearing_en_banc_probability: float
    supreme_court_cert_probability: float
    
    # Optional fields with defaults
    oral_argument_strategy: Optional[str] = None


@dataclass
class StrategyReport:
    """Comprehensive litigation strategy report."""
    case_id: str
    case_name: str
    case_type: str
    
    # Overall strategy
    overall_strategy_summary: str
    key_strategic_milestones: List[Tuple[str, int]]  # (Milestone, Estimated days)
    
    # Risks and contingencies
    identified_risks: List[str]
    contingency_plans: Dict[str, str]  # Risk -> Response
    
    # Resource requirements
    estimated_attorney_hours: int
    estimated_total_cost: float
    staffing_requirements: List[str]
    
    # Success metrics
    success_metrics: List[str]
    decision_points: List[Tuple[str, str]]  # (Decision, Action if result X)
    
    # Optional fields with defaults
    motion_strategy: Optional[MotionStrategy] = None
    discovery_plan: Optional[DiscoveryPlan] = None
    trial_strategy: Optional[TrialStrategy] = None
    appeal_analysis: Optional[AppealAnalysis] = None
    report_date: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


class CaseStrategyOptimizer:
    """
    Optimizes litigation strategy across all phases based on case
    characteristics, judge profiles, and predictive models.
    """
    
    def __init__(self):
        """Initialize the optimizer."""
        self.case_strategies: Dict[str, StrategyReport] = {}
    
    def optimize_motion_strategy(
        self,
        case_features: Dict[str, any],
        judge_profile: Optional[Dict[str, any]] = None
    ) -> MotionStrategy:
        """
        Optimize motion filing strategy.
        
        Args:
            case_features: Case characteristics
            judge_profile: Judge profile data if available
            
        Returns:
            MotionStrategy with recommendations
        """
        case_strength = case_features.get('case_strength', 0.5)
        case_type = case_features.get('case_type', 'general')
        
        # MTD analysis
        if case_type in ['employment', 'civil_rights']:
            mtd_success = 0.25  # Hard to get MTD on these
            mtd_rec = "defer"
        else:
            mtd_success = 0.35 + (case_strength * 0.2)
            mtd_rec = "file" if case_strength > 0.6 else "standard"
        
        # MSJ analysis
        msj_success = 0.35 + (case_strength * 0.3)
        msj_rec = "file" if case_strength > 0.7 else "prepare"
        
        # Adjust for judge preferences
        if judge_profile:
            if judge_profile.get('summary_judgment_grant_rate', 0.45) > 0.55:
                msj_success += 0.1
            if judge_profile.get('mtd_grant_rate', 0.4) > 0.5:
                mtd_success += 0.1
        
        # Motion timing
        mtd_timing = "early" if mtd_success > 0.4 else "late"
        msj_timing = "standard" if msj_success > 0.35 else "aggressive"
        
        # Adverse motion assessment
        adverse_motions = []
        if case_strength < 0.4:
            adverse_motions = ["MTD", "MSJ", "Motion in Limine"]
        elif case_strength < 0.6:
            adverse_motions = ["MSJ", "Motion in Limine"]
        
        return MotionStrategy(
            case_id=case_features.get('case_id', 'unknown'),
            mtd_recommendation=mtd_rec,
            mtd_success_probability=min(mtd_success, 1.0),
            mtd_timing=mtd_timing,
            mtd_legal_theories=[
                "Failure to state a claim",
                "Lack of subject matter jurisdiction",
                "Statute of limitations",
            ],
            msj_recommendation="file" if msj_success > 0.3 else "prepare_defensively",
            msj_success_probability=min(msj_success, 1.0),
            msj_timing=msj_timing,
            msj_focus_areas=[
                "Undisputed material facts",
                "Liability elements",
                "Damages calculations",
            ],
            motion_in_limine_topics=[
                "Prejudicial evidence",
                "Character evidence",
                "Hearsay",
                "Expert opinion scope",
            ],
            pretrial_conference_strategy="Aggressive settlement posture",
            adverse_motion_risk=adverse_motions,
            counter_strategies=[
                "Develop strong factual record",
                "Cite favorable case law",
                "Prepare detailed opposition",
            ],
            estimated_motion_costs=50000,
            expected_timeline_impact_days=90,
        )
    
    def optimize_discovery_plan(
        self,
        case_features: Dict[str, any]
    ) -> DiscoveryPlan:
        """
        Optimize discovery strategy.
        
        Args:
            case_features: Case characteristics
            
        Returns:
            DiscoveryPlan with comprehensive strategy
        """
        case_complexity = case_features.get('complexity', 'moderate')
        num_parties = case_features.get('num_parties', 2)
        damages_amount = case_features.get('damages_amount', 500000)
        
        # Determine scope
        if case_complexity == 'simple' and num_parties == 2:
            scope = "narrow"
            duration_months = 8
        elif case_complexity == 'moderate':
            scope = "standard"
            duration_months = 12
        else:
            scope = "aggressive"
            duration_months = 18
        
        # Document volume estimation
        if damages_amount > 5000000:
            doc_volume = "voluminous"
            doc_cost = 250000
        elif damages_amount > 1000000:
            doc_volume = "large"
            doc_cost = 150000
        else:
            doc_volume = "moderate"
            doc_cost = 75000
        
        # Priority topics
        priority_topics = [
            "Contract/agreement",
            "Communications",
            "Decision-making process",
            "Damages/harm",
            "Industry standards",
            "Similar transactions",
        ]
        
        # Deposition strategy
        deposition_targets = [
            "Plaintiff/Defendant",
            "Key decision makers",
            "Fact witnesses",
            "Industry experts",
        ]
        deposition_count = 5 + (num_parties * 2)
        
        # Expert discovery
        expert_count = 2 if case_complexity == 'simple' else 3 if case_complexity == 'moderate' else 4
        
        return DiscoveryPlan(
            case_id=case_features.get('case_id', 'unknown'),
            scope_breadth=scope,
            priority_topics=priority_topics,
            document_request_strategy="Targeted and proportional",
            expected_document_volume=doc_volume,
            e_discovery_complexity="moderate" if doc_volume != "voluminous" else "complex",
            e_discovery_cost_estimate=doc_cost,
            interrogatory_count=25 if scope == "narrow" else 35 if scope == "standard" else 50,
            interrogatory_focus=["Liability", "Damages", "Witnesses", "Documents"],
            deposition_strategy="Sequential targeting of key witnesses",
            priority_deposition_targets=deposition_targets,
            estimated_deposition_count=deposition_count,
            estimated_deposition_duration_days=deposition_count,
            deposition_cost_estimate=deposition_count * 15000,
            expert_witnesses_needed=expert_count,
            expert_disciplines=["Economics", "Industry standard", "Damages"],
            expert_discovery_timeline="6 months into discovery",
            admission_count=20,
            admission_strategy="Pin down undisputed facts",
            discovery_phase_duration_months=duration_months,
            critical_discovery_deadlines=[
                ("Initial disclosures", 30),
                ("Expert disclosures", 120),
                ("Discovery cutoff", 240),
            ],
            total_discovery_cost_estimate=300000 + doc_cost,
            expected_cost_per_document_page=0.50,
        )
    
    def recommend_trial_strategy(
        self,
        case_features: Dict[str, any],
        judge_profile: Optional[Dict[str, any]] = None
    ) -> TrialStrategy:
        """
        Recommend optimal trial strategy.
        
        Args:
            case_features: Case characteristics
            judge_profile: Judge preferences if available
            
        Returns:
            TrialStrategy with detailed recommendations
        """
        case_strength = case_features.get('case_strength', 0.5)
        case_type = case_features.get('case_type', 'general')
        case_complexity = case_features.get('complexity', 'moderate')
        
        # Trial type recommendation
        if judge_profile and judge_profile.get('prefers_bench_trial'):
            trial_type = TrialType.BENCH
        elif case_strength > 0.7:
            trial_type = TrialType.JURY
        else:
            trial_type = TrialType.BENCH
        
        # Primary theory selection
        theory_map = {
            'employment': 'Discrimination under Title VII',
            'contract': 'Breach of contract',
            'tort': 'Negligence',
            'civil_rights': 'Constitutional violation',
            'general': 'Primary claim'
        }
        
        primary_theory = theory_map.get(case_type, 'Primary legal theory')
        
        return TrialStrategy(
            case_id=case_features.get('case_id', 'unknown'),
            trial_type_recommendation=trial_type,
            trial_type_rationale="Based on case strength and judge preferences",
            jury_vs_bench_factors={
                'case_complexity': 0.5 if case_strength > 0.5 else -0.3,
                'sympathetic_plaintiff': 0.4 if case_strength > 0.6 else 0,
                'technical_issues': -0.3 if case_complexity == 'high' else 0,
            },
            primary_legal_theory=primary_theory,
            secondary_theories=[
                "Alternative legal basis",
                "Fallback position",
            ],
            theories_to_avoid=[
                "Weak theories",
                "Inconsistent positions",
            ],
            theory_win_probability_map={
                primary_theory: case_strength,
                'Alternative theory': case_strength * 0.7,
            },
            key_facts_to_emphasize=[
                "Undisputed liability factors",
                "Damages evidence",
                "Party credibility",
            ],
            facts_to_minimize=[
                "Weaknesses in claim",
                "Favorable defense evidence",
            ],
            narrative_arc="Clear, compelling story aligned with legal theory",
            key_witness_testimony_order=[
                "Credible fact witnesses",
                "Expert witnesses",
                "Adverse party",
            ],
            witness_preparation_priorities=["Key fact witnesses", "Experts"],
            expert_witness_recommendations=[
                "Industry expert",
                "Damages expert",
                "Technical expert if needed",
            ],
            demonstrative_evidence_recommendations=[
                "Timeline exhibits",
                "Document compilations",
                "Damages calculations",
                "Visual depictions",
            ],
            visual_strategy="Clear, professional presentations",
            technology_use_recommendations=[
                "Trial presentation software",
                "Real-time transcript",
                "Video depositions",
            ],
            opening_statement_focus="Tell compelling story; frame issues",
            closing_argument_themes=[
                "Liability clear from evidence",
                "Damages reasonable and warranted",
                "Justice requires verdict for plaintiff",
            ],
            anticipated_defense_arguments=[
                "Alternative causation",
                "Damages overstated",
                "Comparative fault",
            ],
            counter_argument_preparation=[
                "Pre-emptive arguments",
                "Evidentiary support",
                "Legal refutation",
            ],
            verdict_form_strategy="Use favorable verdict form questions",
            damages_presentation_strategy="Credible, documented damages evidence",
            trial_duration_estimate_days=10,
            critical_trial_dates=[
                ("Trial start", "TBD"),
                ("Key witness testimony", "Day 3-4"),
                ("Closing arguments", "Final day"),
            ],
        )
    
    def analyze_appeal_viability(
        self,
        trial_outcome: Dict[str, any],
        case_features: Dict[str, any]
    ) -> AppealAnalysis:
        """
        Analyze viability of appeal.
        
        Args:
            trial_outcome: Trial result details
            case_features: Original case features
            
        Returns:
            AppealAnalysis with appeal strategy
        """
        verdict = trial_outcome.get('verdict', 'loss')
        judge_name = case_features.get('judge_name')
        case_type = case_features.get('case_type', 'general')
        
        # Appeal viability score
        if verdict == 'loss':
            # Loss might be appealable
            viability = 0.4
            assessment = "moderate"
        else:
            # Win less likely to be appealed, but opponent might
            viability = 0.3
            assessment = "weak"
        
        potential_grounds = [
            "Evidentiary errors",
            "Instructional errors",
            "Procedural errors",
            "Legal interpretation",
            "Abuse of discretion",
        ]
        
        return AppealAnalysis(
            case_id=case_features.get('case_id', 'unknown'),
            trial_outcome=trial_outcome,
            appeal_viability_score=viability,
            appeal_viability_assessment=assessment,
            potential_appeal_grounds=potential_grounds,
            strongest_grounds="Clear legal error",
            weakest_potential_grounds=["Discretionary rulings"],
            appellate_court="Circuit Court of Appeals",
            recent_precedent_favorable=(viability > 0.5),
            recent_precedent_summary="Recent circuit precedent analysis needed",
            optimal_appeal_arguments=[
                "Primary legal theory",
                "Evidentiary issues",
            ],
            arguments_to_avoid=["Weak arguments"],
            briefing_strategy="Thorough factual and legal development",
            estimated_win_probability_appeal=viability,
            estimated_reversal_probability=viability * 0.8,
            estimated_appeal_cost=100000,
            estimated_appeal_timeline_months=18,
            expected_decision_timeline="12-24 months",
            rehearing_en_banc_probability=0.15,
            supreme_court_cert_probability=0.05,
        )
    
    def optimize_overall_strategy(
        self,
        case_features: Dict[str, any],
        judge_profile: Optional[Dict[str, any]] = None
    ) -> StrategyReport:
        """
        Optimize comprehensive litigation strategy.
        
        Args:
            case_features: Case characteristics
            judge_profile: Judge profile if available
            
        Returns:
            StrategyReport with comprehensive strategy
        """
        case_id = case_features.get('case_id', 'unknown')
        
        # Generate component strategies
        motion_strategy = self.optimize_motion_strategy(case_features, judge_profile)
        discovery_plan = self.optimize_discovery_plan(case_features)
        trial_strategy = self.recommend_trial_strategy(case_features, judge_profile)
        
        # Strategic milestones
        milestones = [
            ("Initial pleadings", 30),
            ("Motion practice", 90),
            ("Discovery initiation", 120),
            ("Expert disclosures", 180),
            ("Discovery completion", 240),
            ("Pretrial conference", 300),
            ("Trial", 365),
        ]
        
        # Risks
        risks = [
            "Adverse motion grants",
            "Unfavorable discovery",
            "Jury unpredictability",
            "Appellate reversal",
        ]
        
        # Cost and resource estimation
        total_cost = (
            motion_strategy.estimated_motion_costs +
            discovery_plan.total_discovery_cost_estimate +
            100000  # Trial preparation
        )
        
        attorney_hours = int(total_cost / 300)  # Assume $300/hour effective rate
        
        report = StrategyReport(
            case_id=case_id,
            case_name=case_features.get('case_name', 'Unknown'),
            case_type=case_features.get('case_type', 'general'),
            motion_strategy=motion_strategy,
            discovery_plan=discovery_plan,
            trial_strategy=trial_strategy,
            overall_strategy_summary="Comprehensive litigation strategy optimized for case strength and judge preferences",
            key_strategic_milestones=milestones,
            identified_risks=risks,
            contingency_plans={
                "Adverse motion grants": "Prepare strong opposition briefs",
                "Unfavorable discovery": "Work through discovery disputes",
            },
            estimated_attorney_hours=attorney_hours,
            estimated_total_cost=total_cost,
            staffing_requirements=["Lead counsel", "Associate counsel", "Paralegal"],
            success_metrics=[
                "Motion success rate > 50%",
                "Settlement above trial value",
                "Favorable verdict if tried",
            ],
            decision_points=[
                ("MTD ruling", "Adjust strategy if granted"),
                ("Discovery completion", "Evaluate settlement"),
                ("Pretrial conference", "Final settlement push"),
            ],
        )
        
        self.case_strategies[case_id] = report
        return report
