"""
Settlement Calculator - Data-Driven Settlement Valuation

Calculates settlement ranges, NPV analysis, and negotiation strategies
based on comparable verdicts and case-specific factors.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import statistics


@dataclass
class ComparableVerdict:
    """Represents a comparable verdict from similar case."""
    verdict_id: str
    case_type: str
    jurisdiction: str
    verdict_year: int
    plaintiff_side: bool  # True if this was favorable to plaintiff-like party
    verdict_amount: float
    damages_awarded: float
    attorney_fees_awarded: float
    trial_duration_days: int
    jury_vs_bench: str  # "jury" or "bench"
    precedent_level: str  # "district", "circuit", "appellate"
    relevance_score: float  # 0-1, how similar to current case
    opinion_text: Optional[str] = None


@dataclass
class SettlementRange:
    """Settlement valuation range based on comparable verdicts."""
    low_estimate: float  # 10th percentile
    likely_estimate: float  # 50th percentile (median)
    high_estimate: float  # 90th percentile
    confidence: float  # 0-1, confidence in estimate
    comparable_cases: List[ComparableVerdict] = field(default_factory=list)
    case_type: str = ""
    jurisdiction: str = ""
    summary: str = ""
    calculation_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class NPVAnalysis:
    """Net Present Value analysis of trial vs. settlement."""
    trial_expected_value: float  # Probability of win * damages
    trial_cost: float  # Estimated attorney fees and costs
    trial_timeline_months: int
    settlement_amount: float
    settlement_net_after_fees: float
    npv_trial: float  # Expected value discounted
    npv_settlement: float  # Certain value discounted
    breakeven_settlement_amount: float  # Settlement equal to trial NPV
    recommendation: str  # "settle" or "try"
    risk_adjusted_recommendation: str


@dataclass
class NegotiationStrategy:
    """Recommended negotiation strategy."""
    initial_demand: float  # Opening position
    walkaway_floor: float  # Minimum acceptable
    likely_settlement_range: Tuple[float, float]
    negotiation_phases: List[str]
    batna_value: float  # Best Alternative to Negotiated Agreement
    batna_description: str
    risk_factors: List[str]
    negotiation_timeline_days: int
    mediator_recommendation: Optional[str] = None
    counterparty_likely_settlement: Optional[float] = None


class SettlementCalculator:
    """
    Calculates data-driven settlement valuations based on comparable verdicts
    and risk-adjusted trial analysis.
    """
    
    def __init__(self):
        """Initialize calculator with comparable verdict database."""
        self.verdict_database: List[ComparableVerdict] = []
        self._initialize_verdict_database()
    
    def _initialize_verdict_database(self):
        """Initialize with sample verdicts for different case types."""
        sample_verdicts = [
            # Employment cases
            ComparableVerdict(
                verdict_id='v001', case_type='employment', jurisdiction='federal',
                verdict_year=2023, plaintiff_side=True, verdict_amount=250000,
                damages_awarded=200000, attorney_fees_awarded=50000,
                trial_duration_days=15, jury_vs_bench='jury',
                precedent_level='district', relevance_score=0.85
            ),
            ComparableVerdict(
                verdict_id='v002', case_type='employment', jurisdiction='federal',
                verdict_year=2022, plaintiff_side=True, verdict_amount=180000,
                damages_awarded=140000, attorney_fees_awarded=40000,
                trial_duration_days=12, jury_vs_bench='jury',
                precedent_level='district', relevance_score=0.82
            ),
            ComparableVerdict(
                verdict_id='v003', case_type='employment', jurisdiction='state',
                verdict_year=2023, plaintiff_side=False, verdict_amount=50000,
                damages_awarded=50000, attorney_fees_awarded=0,
                trial_duration_days=8, jury_vs_bench='jury',
                precedent_level='district', relevance_score=0.75
            ),
            ComparableVerdict(
                verdict_id='v004', case_type='employment', jurisdiction='federal',
                verdict_year=2023, plaintiff_side=True, verdict_amount=350000,
                damages_awarded=280000, attorney_fees_awarded=70000,
                trial_duration_days=18, jury_vs_bench='jury',
                precedent_level='district', relevance_score=0.88
            ),
            # Contract cases
            ComparableVerdict(
                verdict_id='v005', case_type='contract', jurisdiction='federal',
                verdict_year=2023, plaintiff_side=True, verdict_amount=500000,
                damages_awarded=400000, attorney_fees_awarded=100000,
                trial_duration_days=20, jury_vs_bench='bench',
                precedent_level='district', relevance_score=0.80
            ),
            ComparableVerdict(
                verdict_id='v006', case_type='contract', jurisdiction='federal',
                verdict_year=2022, plaintiff_side=True, verdict_amount=300000,
                damages_awarded=240000, attorney_fees_awarded=60000,
                trial_duration_days=15, jury_vs_bench='bench',
                precedent_level='district', relevance_score=0.78
            ),
            # Tort cases
            ComparableVerdict(
                verdict_id='v007', case_type='tort', jurisdiction='state',
                verdict_year=2023, plaintiff_side=True, verdict_amount=750000,
                damages_awarded=600000, attorney_fees_awarded=150000,
                trial_duration_days=25, jury_vs_bench='jury',
                precedent_level='district', relevance_score=0.72
            ),
            ComparableVerdict(
                verdict_id='v008', case_type='tort', jurisdiction='state',
                verdict_year=2023, plaintiff_side=True, verdict_amount=1200000,
                damages_awarded=900000, attorney_fees_awarded=300000,
                trial_duration_days=30, jury_vs_bench='jury',
                precedent_level='circuit', relevance_score=0.70
            ),
        ]
        self.verdict_database.extend(sample_verdicts)
    
    def find_comparable_verdicts(
        self,
        case_type: str,
        jurisdiction: str,
        days_to_trial: int = 365,
        relevance_threshold: float = 0.6
    ) -> List[ComparableVerdict]:
        """
        Find comparable verdicts for valuation.
        
        Args:
            case_type: Type of case
            jurisdiction: Court jurisdiction
            days_to_trial: Days until potential trial
            relevance_threshold: Minimum relevance score
            
        Returns:
            List of comparable verdicts
        """
        comparables = [
            v for v in self.verdict_database
            if v.case_type.lower() == case_type.lower() and
               v.relevance_score >= relevance_threshold
        ]
        
        # Sort by relevance
        comparables.sort(key=lambda v: v.relevance_score, reverse=True)
        
        return comparables[:10]  # Return top 10 most relevant
    
    def calculate_settlement_value(
        self,
        case_type: str,
        jurisdiction: str,
        damages_requested: float,
        case_strength: float = 0.5,  # 0-1, plaintiff perspective
        defendant_assets: float = 1000000,
    ) -> SettlementRange:
        """
        Calculate data-driven settlement range.
        
        Args:
            case_type: Type of case
            jurisdiction: Court jurisdiction
            damages_requested: Amount of damages plaintiff is seeking
            case_strength: Estimated case strength (0-1, from plaintiff perspective)
            defendant_assets: Defendant's estimated assets (affects settlement ceiling)
            
        Returns:
            SettlementRange with low, likely, and high estimates
        """
        comparables = self.find_comparable_verdicts(case_type, jurisdiction)
        
        if not comparables:
            # Default fallback calculation
            return self._calculate_settlement_fallback(
                damages_requested, case_strength
            )
        
        # Extract verdicts favorable to plaintiff-like party
        favorable_verdicts = [
            v.verdict_amount for v in comparables if v.plaintiff_side
        ]
        unfavorable_verdicts = [
            v.verdict_amount for v in comparables if not v.plaintiff_side
        ]
        
        # Calculate percentiles from comparable verdicts
        if favorable_verdicts:
            favorable_sorted = sorted(favorable_verdicts)
            low_idx = max(0, len(favorable_sorted) // 10)
            mid_idx = len(favorable_sorted) // 2
            high_idx = len(favorable_sorted) - 1
            
            base_low = favorable_sorted[low_idx] if len(favorable_sorted) > 0 else 0
            base_mid = favorable_sorted[mid_idx] if len(favorable_sorted) > 0 else 0
            base_high = favorable_sorted[high_idx] if len(favorable_sorted) > 0 else 0
        else:
            base_low = damages_requested * 0.3
            base_mid = damages_requested * 0.6
            base_high = damages_requested * 0.9
        
        # Adjust based on case strength
        strength_factor = case_strength  # 0-1
        low_estimate = base_low * strength_factor * 0.8
        likely_estimate = base_mid * strength_factor
        high_estimate = min(base_high * strength_factor * 1.2, defendant_assets)
        
        # Ensure reasonable bounds
        high_estimate = max(high_estimate, likely_estimate * 1.3)
        
        confidence = min(0.9, 0.5 + len(comparables) * 0.05)
        
        return SettlementRange(
            low_estimate=max(0, low_estimate),
            likely_estimate=likely_estimate,
            high_estimate=min(defendant_assets, high_estimate),
            confidence=confidence,
            comparable_cases=comparables[:5],
            case_type=case_type,
            jurisdiction=jurisdiction,
            summary=f"Based on {len(comparables)} comparable verdicts in {case_type} cases",
        )
    
    def _calculate_settlement_fallback(
        self,
        damages_requested: float,
        case_strength: float
    ) -> SettlementRange:
        """Fallback calculation when no comparables found."""
        likely = damages_requested * case_strength
        return SettlementRange(
            low_estimate=likely * 0.6,
            likely_estimate=likely,
            high_estimate=likely * 1.5,
            confidence=0.4,
            case_type="unknown",
            jurisdiction="unknown",
            summary="Estimated range based on case strength and damages requested",
        )
    
    def calculate_trial_npv(
        self,
        win_probability: float,
        expected_damages: float,
        trial_costs: float = 150000,  # Attorney fees, expert costs, etc.
        trial_timeline_months: int = 36,
        discount_rate: float = 0.05  # 5% annual discount
    ) -> NPVAnalysis:
        """
        Calculate Net Present Value of trial vs. settlement.
        
        Args:
            win_probability: Probability of winning at trial (0-1)
            expected_damages: Expected damages if trial is won
            trial_costs: Total costs of going to trial
            trial_timeline_months: Months until trial outcome
            discount_rate: Annual discount rate for NPV
            
        Returns:
            NPVAnalysis with trial and settlement values
        """
        # Expected value of trial
        expected_trial_value = win_probability * expected_damages
        
        # Net after costs
        net_trial_value = expected_trial_value - trial_costs
        
        # Discount to present value
        discount_factor = (1 + discount_rate) ** (trial_timeline_months / 12.0)
        npv_trial = net_trial_value / discount_factor
        
        # Settlement recommendation (using expected trial value as baseline)
        likely_settlement = expected_trial_value * 0.85  # Usually some discount
        
        # NPV of settlement (immediate, no discount needed but some reduction)
        settlement_fee_rate = 0.33  # Typical 1/3 contingency fee
        settlement_net_after_fees = likely_settlement * (1 - settlement_fee_rate)
        npv_settlement = settlement_net_after_fees
        
        # Breakeven: settlement amount that equals trial NPV
        breakeven = npv_trial * (1 + discount_rate) ** (trial_timeline_months / 12.0)
        
        # Recommendation
        if npv_settlement > npv_trial:
            recommendation = "settle"
            risk_recommendation = "Strongly consider settlement - higher net value"
        elif npv_settlement > npv_trial * 0.95:
            recommendation = "neutral"
            risk_recommendation = "Settlement and trial have similar values - consider risk tolerance"
        else:
            recommendation = "try"
            risk_recommendation = "Trial has better expected value - proceed to trial if risk tolerant"
        
        return NPVAnalysis(
            trial_expected_value=expected_trial_value,
            trial_cost=trial_costs,
            trial_timeline_months=trial_timeline_months,
            settlement_amount=likely_settlement,
            settlement_net_after_fees=settlement_net_after_fees,
            npv_trial=npv_trial,
            npv_settlement=npv_settlement,
            breakeven_settlement_amount=breakeven,
            recommendation=recommendation,
            risk_adjusted_recommendation=risk_recommendation,
        )
    
    def recommend_negotiation_strategy(
        self,
        settlement_range: SettlementRange,
        npv_analysis: NPVAnalysis,
        client_goals: Dict[str, float],
        opposing_party_strength: float = 0.5
    ) -> NegotiationStrategy:
        """
        Recommend negotiation strategy based on settlement valuation.
        
        Args:
            settlement_range: Calculated settlement range
            npv_analysis: Trial NPV analysis
            client_goals: Client's goals {"maximize_recovery": 0-1, "minimize_risk": 0-1}
            opposing_party_strength: Estimated strength of opposing party (0-1)
            
        Returns:
            NegotiationStrategy with recommended approach
        """
        # BATNA (Best Alternative to Negotiated Agreement) = trial NPV
        batna_value = npv_analysis.npv_trial
        
        # Initial demand (anchoring)
        initial_demand = settlement_range.high_estimate * 1.1
        
        # Walkaway floor
        walkaway_floor = max(batna_value, settlement_range.low_estimate)
        
        # Likely settlement will be somewhere in range
        # Adjust based on case strength and opposing party strength
        likely_low = settlement_range.likely_estimate * 0.75
        likely_high = settlement_range.likely_estimate * 1.15
        
        # Opponent's likely position
        opposing_strength = opposing_party_strength
        if opposing_strength < 0.4:
            opponent_demand = settlement_range.likely_estimate * 0.5
        elif opposing_strength < 0.6:
            opponent_demand = settlement_range.likely_estimate * 0.65
        else:
            opponent_demand = settlement_range.likely_estimate * 0.75
        
        # Negotiation phases
        phases = [
            "Initial demand and response exchange",
            "First counter-offer round",
            "Mediation engagement (if stuck)",
            "Final negotiation push",
            "Go/no-go decision on trial",
        ]
        
        # Mediator recommendation
        if abs(initial_demand - opponent_demand) > settlement_range.likely_estimate * 0.4:
            mediator_rec = "Retired judge with mediation experience"
        else:
            mediator_rec = None
        
        return NegotiationStrategy(
            initial_demand=initial_demand,
            walkaway_floor=walkaway_floor,
            likely_settlement_range=(likely_low, likely_high),
            negotiation_phases=phases,
            batna_value=batna_value,
            batna_description=f"Trial expected value: ${batna_value:,.0f}",
            risk_factors=[
                "Appellate reversal risk",
                "Jury unpredictability",
                "Judge's known preferences",
                "Procedural delays",
            ],
            negotiation_timeline_days=90,
            mediator_recommendation=mediator_rec,
            counterparty_likely_settlement=opponent_demand,
        )
    
    def calculate_attorney_fee_impact(
        self,
        settlement_amount: float,
        fee_structure: str = "contingency_33"  # "contingency_25", "contingency_33", "hourly"
        ) -> Dict[str, float]:
        """
        Calculate net recovery after attorney fees.
        
        Args:
            settlement_amount: Gross settlement amount
            fee_structure: Fee arrangement type
            
        Returns:
            Dictionary with fee and net recovery information
        """
        if fee_structure == "contingency_33":
            attorney_fee = settlement_amount * 0.33
        elif fee_structure == "contingency_25":
            attorney_fee = settlement_amount * 0.25
        else:
            attorney_fee = 0  # Assume hourly already paid
        
        costs = settlement_amount * 0.05  # Estimated costs (expert, filing, etc.)
        net_recovery = settlement_amount - attorney_fee - costs
        
        return {
            "gross_settlement": settlement_amount,
            "attorney_fee": attorney_fee,
            "costs": costs,
            "net_recovery": net_recovery,
            "recovery_percentage": net_recovery / settlement_amount if settlement_amount > 0 else 0,
        }
    
    def calculate_time_value_impact(
        self,
        settlement_today: float,
        trial_value_future: float,
        months_until_trial: int = 36,
        discount_rate: float = 0.05
    ) -> Dict[str, float]:
        """
        Calculate time value of money impact on settlement decision.
        
        Args:
            settlement_today: Settlement available today
            trial_value_future: Expected value at trial
            months_until_trial: Months until trial decision
            discount_rate: Annual discount rate
            
        Returns:
            Comparison of settlement vs. discounted trial value
        """
        years = months_until_trial / 12.0
        discounted_trial_value = trial_value_future / ((1 + discount_rate) ** years)
        
        difference = settlement_today - discounted_trial_value
        
        return {
            "settlement_today": settlement_today,
            "trial_value_future": trial_value_future,
            "discounted_trial_value": discounted_trial_value,
            "difference": difference,
            "settlement_advantage": difference > 0,
            "advantage_magnitude_dollars": abs(difference),
            "advantage_magnitude_percent": (difference / discounted_trial_value * 100) if discounted_trial_value > 0 else 0,
        }
