"""
Legal Risk Scorer - Multi-Dimensional Risk Assessment

Provides comprehensive risk assessment across litigation, regulatory,
criminal, contractual, and other legal dimensions.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime


class RiskLevel(Enum):
    """Risk severity levels."""
    MINIMAL = "minimal"  # 0-15
    LOW = "low"  # 15-30
    MODERATE = "moderate"  # 30-50
    HIGH = "high"  # 50-70
    CRITICAL = "critical"  # 70-100


@dataclass
class RiskScore:
    """Individual risk dimension score."""
    dimension: str
    score: float  # 0-100
    risk_level: RiskLevel
    confidence: float  # 0-1, confidence in score
    probability: float  # 0-1, probability of risk occurring
    potential_damages: float  # Dollar exposure
    key_drivers: List[str]  # What factors drive this risk
    mitigation_opportunities: List[str]  # How to reduce risk
    score_date: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RiskDimension:
    """Named risk dimension for organizing scores."""
    name: str
    description: str
    score: RiskScore


@dataclass
class RiskProfile:
    """Comprehensive risk profile across all dimensions."""
    entity_name: str
    entity_type: str  # "individual", "corporation", "nonprofit", etc.
    
    # Risk dimensions
    litigation_risk: RiskScore = field(default_factory=
        lambda: RiskScore("litigation", 50, RiskLevel.MODERATE, 0.7, 0.5, 500000, [], []))
    regulatory_risk: RiskScore = field(default_factory=
        lambda: RiskScore("regulatory", 35, RiskLevel.MODERATE, 0.6, 0.3, 250000, [], []))
    criminal_risk: RiskScore = field(default_factory=
        lambda: RiskScore("criminal", 10, RiskLevel.LOW, 0.8, 0.05, 100000, [], []))
    contractual_risk: RiskScore = field(default_factory=
        lambda: RiskScore("contractual", 40, RiskLevel.MODERATE, 0.65, 0.4, 300000, [], []))
    ip_risk: RiskScore = field(default_factory=
        lambda: RiskScore("ip", 30, RiskLevel.LOW, 0.7, 0.25, 200000, [], []))
    employment_risk: RiskScore = field(default_factory=
        lambda: RiskScore("employment", 45, RiskLevel.MODERATE, 0.7, 0.45, 400000, [], []))
    environmental_risk: RiskScore = field(default_factory=
        lambda: RiskScore("environmental", 20, RiskLevel.LOW, 0.6, 0.15, 150000, [], []))
    
    # Aggregate scores
    overall_risk_score: float = 0.0
    overall_risk_level: RiskLevel = RiskLevel.MODERATE
    total_potential_exposure: float = 0.0
    
    # Analysis metadata
    industry: str = ""
    company_size: str = "medium"  # "small", "medium", "large", "enterprise"
    geographic_reach: str = "regional"  # "local", "regional", "national", "international"
    risk_appetite: str = "moderate"  # "conservative", "moderate", "aggressive"
    
    profile_date: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MitigationPlan:
    """Risk mitigation plan with recommended actions."""
    entity_name: str
    risk_profile: RiskProfile
    
    high_priority_actions: List[str]
    medium_priority_actions: List[str]
    low_priority_actions: List[str]
    
    estimated_mitigation_cost: float
    estimated_risk_reduction: float  # 0-1, fraction of risk that can be mitigated
    timeline_months: int
    
    responsible_parties: Dict[str, str]  # Role -> Department/Person
    implementation_milestones: List[Tuple[str, int]]  # (Milestone, Days)
    
    quarterly_review_schedule: List[str]
    success_metrics: List[str]
    
    plan_date: str = field(default_factory=lambda: datetime.now().isoformat())


class LegalRiskScorer:
    """
    Comprehensive multi-dimensional legal risk assessment system.
    """
    
    def __init__(self):
        """Initialize the risk scorer."""
        self.risk_factors_db = self._initialize_risk_factors()
    
    def _initialize_risk_factors(self) -> Dict[str, Dict[str, any]]:
        """Initialize risk factor database."""
        return {
            'litigation': {
                'recent_lawsuits': {'weight': 0.3, 'max_score': 30},
                'past_litigation_history': {'weight': 0.25, 'max_score': 25},
                'industry_litigation_rate': {'weight': 0.2, 'max_score': 20},
                'current_claims': {'weight': 0.15, 'max_score': 15},
                'regulatory_scrutiny': {'weight': 0.1, 'max_score': 10},
            },
            'regulatory': {
                'industry_regulation_level': {'weight': 0.3, 'max_score': 30},
                'compliance_violations': {'weight': 0.25, 'max_score': 25},
                'regulatory_inspection_findings': {'weight': 0.2, 'max_score': 20},
                'agency_relationships': {'weight': 0.15, 'max_score': 15},
                'pending_rulemakings': {'weight': 0.1, 'max_score': 10},
            },
            'employment': {
                'employee_count': {'weight': 0.2, 'max_score': 20},
                'past_employment_claims': {'weight': 0.3, 'max_score': 30},
                'hr_policy_quality': {'weight': 0.2, 'max_score': 20},
                'wage_hour_compliance': {'weight': 0.15, 'max_score': 15},
                'discrimination_complaint_history': {'weight': 0.15, 'max_score': 15},
            },
            'contractual': {
                'contract_complexity': {'weight': 0.25, 'max_score': 25},
                'performance_issues': {'weight': 0.3, 'max_score': 30},
                'counterparty_creditworthiness': {'weight': 0.2, 'max_score': 20},
                'dispute_history': {'weight': 0.15, 'max_score': 15},
                'termination_triggers': {'weight': 0.1, 'max_score': 10},
            },
            'ip': {
                'ip_portfolio_value': {'weight': 0.2, 'max_score': 20},
                'third_party_ip_dependence': {'weight': 0.25, 'max_score': 25},
                'patent_enforcement_activity': {'weight': 0.2, 'max_score': 20},
                'trade_secret_protection': {'weight': 0.2, 'max_score': 20},
                'licensing_disputes': {'weight': 0.15, 'max_score': 15},
            },
        }
    
    def assess_litigation_risk(
        self,
        business_facts: Dict[str, any]
    ) -> RiskScore:
        """
        Assess probability and exposure of litigation risk.
        
        Args:
            business_facts: Dictionary with litigation risk factors
            
        Returns:
            RiskScore for litigation dimension
        """
        # Extract factors with defaults
        recent_lawsuits = business_facts.get('recent_lawsuits', 0)
        past_litigation_count = business_facts.get('past_litigation_count', 0)
        industry_litigation_rate = business_facts.get('industry_litigation_rate', 0.5)
        current_claims = business_facts.get('current_claims', 0)
        damages_exposure = business_facts.get('damages_exposure', 500000)
        
        # Calculate component scores
        score = 0.0
        
        # Recent lawsuits (heavily weighted)
        if recent_lawsuits > 2:
            score += 25
        elif recent_lawsuits > 0:
            score += 15 + (recent_lawsuits * 5)
        
        # Past litigation history
        score += min(past_litigation_count * 3, 25)
        
        # Industry rate baseline
        score += industry_litigation_rate * 20
        
        # Current claims/allegations
        score += current_claims * 10
        
        # Probability assessment
        probability = min(0.2 + recent_lawsuits * 0.15 + industry_litigation_rate * 0.3, 1.0)
        
        # Identify key drivers
        drivers = []
        if recent_lawsuits > 0:
            drivers.append(f"{recent_lawsuits} recent lawsuits")
        if past_litigation_count > 5:
            drivers.append("Significant litigation history")
        if industry_litigation_rate > 0.7:
            drivers.append("High-risk industry")
        
        # Mitigation opportunities
        mitigations = [
            "Implement robust compliance program",
            "Enhance documentation practices",
            "Review insurance coverage",
            "Improve risk management protocols",
            "Conduct audit of past practices",
        ]
        
        return RiskScore(
            dimension='litigation',
            score=min(score, 100),
            risk_level=self._score_to_level(min(score, 100)),
            confidence=0.7,
            probability=probability,
            potential_damages=damages_exposure,
            key_drivers=drivers,
            mitigation_opportunities=mitigations,
        )
    
    def assess_regulatory_risk(
        self,
        industry: str,
        practices: Dict[str, any]
    ) -> RiskScore:
        """
        Assess regulatory and compliance risk.
        
        Args:
            industry: Industry sector
            practices: Dictionary with regulatory compliance factors
            
        Returns:
            RiskScore for regulatory dimension
        """
        # Industry base score
        high_reg_industries = ['finance', 'healthcare', 'environmental', 'energy', 'utilities']
        industry_score = 50 if industry.lower() in high_reg_industries else 20
        
        # Compliance factors
        violations = practices.get('compliance_violations', 0)
        last_inspection = practices.get('months_since_inspection', 24)
        compliance_score = practices.get('compliance_program_score', 5)  # 1-10
        
        score = industry_score
        
        # Violations heavily weighted
        score += violations * 15
        
        # Inspection recency
        if last_inspection > 24:
            score += 10
        
        # Compliance program weakness
        if compliance_score < 5:
            score += 20 - (compliance_score * 4)
        
        probability = 0.1 + (violations * 0.2) + (1 - compliance_score/10) * 0.3
        
        drivers = []
        if violations > 0:
            drivers.append(f"{violations} compliance violations")
        if compliance_score < 5:
            drivers.append("Weak compliance program")
        if industry.lower() in high_reg_industries:
            drivers.append("Highly regulated industry")
        
        mitigations = [
            "Establish or enhance compliance officer role",
            "Conduct regulatory audit",
            "Implement training program",
            "Strengthen record-keeping",
            "Establish monitoring procedures",
        ]
        
        return RiskScore(
            dimension='regulatory',
            score=min(score, 100),
            risk_level=self._score_to_level(min(score, 100)),
            confidence=0.75,
            probability=min(probability, 1.0),
            potential_damages=practices.get('regulatory_penalty_exposure', 250000),
            key_drivers=drivers,
            mitigation_opportunities=mitigations,
        )
    
    def assess_criminal_risk(
        self,
        entity_facts: Dict[str, any]
    ) -> RiskScore:
        """
        Assess exposure to criminal liability.
        
        Args:
            entity_facts: Facts about the entity
            
        Returns:
            RiskScore for criminal dimension
        """
        # Criminal risk is generally low but critical
        industry = entity_facts.get('industry', 'general')
        prior_criminal = entity_facts.get('prior_criminal_exposure', 0)
        bad_actors = entity_facts.get('key_person_criminal_history', 0)
        
        score = 10  # Baseline
        
        # Prior exposure
        score += prior_criminal * 20
        
        # Key person risk
        score += bad_actors * 15
        
        # Industry factors (some industries have higher criminal exposure)
        if industry.lower() in ['financial_services', 'pharmaceuticals', 'environmental']:
            score += 10
        
        probability = 0.01 + prior_criminal * 0.1 + bad_actors * 0.05
        
        drivers = []
        if prior_criminal > 0:
            drivers.append("Prior criminal exposure")
        if bad_actors > 0:
            drivers.append("Key personnel with criminal history")
        
        mitigations = [
            "Implement anti-corruption compliance",
            "Background screening for key roles",
            "Document good faith compliance efforts",
            "Establish ethics hotline",
            "Regular compliance training",
        ]
        
        return RiskScore(
            dimension='criminal',
            score=min(score, 100),
            risk_level=self._score_to_level(min(score, 100)),
            confidence=0.8,
            probability=min(probability, 1.0),
            potential_damages=entity_facts.get('criminal_exposure', 500000),
            key_drivers=drivers,
            mitigation_opportunities=mitigations,
        )
    
    def assess_employment_risk(
        self,
        employee_count: int,
        past_claims: int = 0,
        industry: str = "general"
    ) -> RiskScore:
        """
        Assess employment-related legal risks.
        
        Args:
            employee_count: Number of employees
            past_claims: Number of prior employment claims
            industry: Industry sector
            
        Returns:
            RiskScore for employment dimension
        """
        score = 20  # Baseline
        
        # Company size (larger companies have more exposure)
        if employee_count > 1000:
            score += 20
        elif employee_count > 500:
            score += 15
        elif employee_count > 100:
            score += 10
        else:
            score += 5
        
        # Past claims
        score += min(past_claims * 8, 30)
        
        # Industry (some industries have higher employment risk)
        if industry.lower() in ['hospitality', 'retail', 'construction', 'manufacturing']:
            score += 15
        
        probability = 0.1 + (employee_count / 5000) * 0.3 + past_claims * 0.05
        
        drivers = []
        drivers.append(f"Company size: {employee_count} employees")
        if past_claims > 0:
            drivers.append(f"{past_claims} prior employment claims")
        
        mitigations = [
            "Implement HR compliance system",
            "Provide management training",
            "Document performance issues properly",
            "Review employment policies",
            "Establish fair discipline procedures",
        ]
        
        damages = employee_count * 5000 * 0.1  # Expected exposure
        
        return RiskScore(
            dimension='employment',
            score=min(score, 100),
            risk_level=self._score_to_level(min(score, 100)),
            confidence=0.7,
            probability=min(probability, 1.0),
            potential_damages=damages,
            key_drivers=drivers,
            mitigation_opportunities=mitigations,
        )
    
    def assess_ip_risk(
        self,
        ip_facts: Dict[str, any]
    ) -> RiskScore:
        """
        Assess intellectual property risk.
        
        Args:
            ip_facts: IP-related facts
            
        Returns:
            RiskScore for IP dimension
        """
        score = 15  # Baseline
        
        # Third-party dependence increases risk
        third_party_dep = ip_facts.get('third_party_ip_dependence', 0)
        score += third_party_dep * 20
        
        # Patent enforcement activity indicates risk
        patent_disputes = ip_facts.get('patent_disputes', 0)
        score += patent_disputes * 15
        
        # Trade secret protection weakness
        trade_secret_score = ip_facts.get('trade_secret_protection_score', 5)
        if trade_secret_score < 5:
            score += (5 - trade_secret_score) * 8
        
        # IP portfolio value (larger portfolio = more risk)
        ip_value = ip_facts.get('ip_portfolio_value', 0)
        if ip_value > 10000000:
            score += 20
        elif ip_value > 1000000:
            score += 10
        
        probability = 0.1 + third_party_dep * 0.2 + patent_disputes * 0.1
        
        drivers = []
        if third_party_dep > 0:
            drivers.append("Dependence on third-party IP")
        if patent_disputes > 0:
            drivers.append("Active patent disputes")
        
        mitigations = [
            "Conduct IP audit",
            "Implement trade secret protection",
            "Review third-party licenses",
            "Consider patent insurance",
            "Establish IP management procedures",
        ]
        
        return RiskScore(
            dimension='ip',
            score=min(score, 100),
            risk_level=self._score_to_level(min(score, 100)),
            confidence=0.65,
            probability=min(probability, 1.0),
            potential_damages=ip_value * 0.3,
            key_drivers=drivers,
            mitigation_opportunities=mitigations,
        )
    
    def generate_risk_profile(
        self,
        entity_data: Dict[str, any]
    ) -> RiskProfile:
        """
        Generate comprehensive risk profile across all dimensions.
        
        Args:
            entity_data: Entity information and risk factors
            
        Returns:
            RiskProfile with all dimension scores
        """
        # Assess each dimension
        litigation_risk = self.assess_litigation_risk(
            entity_data.get('litigation_facts', {})
        )
        regulatory_risk = self.assess_regulatory_risk(
            entity_data.get('industry', 'general'),
            entity_data.get('regulatory_facts', {})
        )
        criminal_risk = self.assess_criminal_risk(
            entity_data.get('criminal_facts', {})
        )
        employment_risk = self.assess_employment_risk(
            entity_data.get('employee_count', 50),
            entity_data.get('past_employment_claims', 0),
            entity_data.get('industry', 'general')
        )
        ip_risk = self.assess_ip_risk(
            entity_data.get('ip_facts', {})
        )
        
        # Create profile
        profile = RiskProfile(
            entity_name=entity_data.get('entity_name', 'Unknown'),
            entity_type=entity_data.get('entity_type', 'corporation'),
            litigation_risk=litigation_risk,
            regulatory_risk=regulatory_risk,
            criminal_risk=criminal_risk,
            employment_risk=employment_risk,
            ip_risk=ip_risk,
            industry=entity_data.get('industry', ''),
            company_size=entity_data.get('company_size', 'medium'),
            geographic_reach=entity_data.get('geographic_reach', 'regional'),
        )
        
        # Calculate overall score
        all_scores = [
            litigation_risk.score,
            regulatory_risk.score,
            criminal_risk.score,
            employment_risk.score,
            ip_risk.score,
        ]
        profile.overall_risk_score = sum(all_scores) / len(all_scores)
        profile.overall_risk_level = self._score_to_level(profile.overall_risk_score)
        
        # Total exposure
        profile.total_potential_exposure = sum([
            litigation_risk.potential_damages,
            regulatory_risk.potential_damages,
            criminal_risk.potential_damages,
            employment_risk.potential_damages,
            ip_risk.potential_damages,
        ])
        
        return profile
    
    def recommend_risk_mitigation(
        self,
        risk_profile: RiskProfile
    ) -> MitigationPlan:
        """
        Generate risk mitigation plan based on risk profile.
        
        Args:
            risk_profile: RiskProfile to mitigate
            
        Returns:
            MitigationPlan with prioritized actions
        """
        # Collect all mitigation opportunities
        all_mitigations = []
        risk_scores = [
            risk_profile.litigation_risk,
            risk_profile.regulatory_risk,
            risk_profile.criminal_risk,
            risk_profile.employment_risk,
            risk_profile.ip_risk,
        ]
        
        for risk_score in risk_scores:
            for mitigation in risk_score.mitigation_opportunities:
                all_mitigations.append((mitigation, risk_score.score))
        
        # Sort by impact (highest risk dimensions first)
        all_mitigations.sort(key=lambda x: x[1], reverse=True)
        
        # Categorize by priority
        high_priority = [m[0] for m in all_mitigations[:5]]
        medium_priority = [m[0] for m in all_mitigations[5:10]]
        low_priority = [m[0] for m in all_mitigations[10:]]
        
        # Estimate mitigation cost and benefit
        mitigation_cost = 50000 + risk_profile.overall_risk_score * 1000
        risk_reduction = min(0.3 + (risk_profile.overall_risk_score / 100) * 0.4, 0.8)
        
        # Milestones
        milestones = [
            ("Initial assessment and planning", 7),
            ("Policy and procedure updates", 30),
            ("Training program rollout", 60),
            ("Compliance monitoring implementation", 90),
            ("Quarterly review and adjustment", 180),
        ]
        
        return MitigationPlan(
            entity_name=risk_profile.entity_name,
            risk_profile=risk_profile,
            high_priority_actions=high_priority,
            medium_priority_actions=medium_priority,
            low_priority_actions=low_priority,
            estimated_mitigation_cost=mitigation_cost,
            estimated_risk_reduction=risk_reduction,
            timeline_months=6,
            responsible_parties={
                'Chief Compliance Officer': 'Legal Department',
                'HR Manager': 'Human Resources',
                'Controller': 'Finance',
                'General Counsel': 'Legal Department',
            },
            implementation_milestones=milestones,
            quarterly_review_schedule=['Q2', 'Q3', 'Q4'],
            success_metrics=[
                f"Reduce overall risk score from {risk_profile.overall_risk_score:.0f} to below 40",
                "100% employee compliance training completion",
                "Zero compliance violations for 6 months",
                "Documented improvement in risk assessments",
            ],
        )
    
    def _score_to_level(self, score: float) -> RiskLevel:
        """Convert numeric score to risk level."""
        if score < 15:
            return RiskLevel.MINIMAL
        elif score < 30:
            return RiskLevel.LOW
        elif score < 50:
            return RiskLevel.MODERATE
        elif score < 70:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
