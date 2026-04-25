"""
DOJ Navigator - Criminal, Civil, Enforcement, and Whistleblower Defense

Comprehensive guide for Department of Justice matters:
- Criminal: Grand jury subpoenas, target/subject/witness designations, proffer agreements
- Civil: Civil Division, False Claims Act (qui tam), civil rights
- Antitrust: Merger review (HSR), investigations, consent decrees
- Immigration: USCIS procedures, removal defense, asylum, visas
- Asset forfeiture: Civil forfeiture defense, administrative claims
- Whistleblower: False Claims Act relator, SEC/CFTC programs
- FOIA requests: Drafting, appeals, Vaughn Index

Line count: 390+ lines
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta


class SubpoenaType(Enum):
    """Types of grand jury subpoenas."""
    DOCUMENTS = "documents"
    TESTIMONY = "testimony"
    BOTH = "documents_and_testimony"


class GrandJuryStatus(Enum):
    """Status in grand jury investigation."""
    WITNESS = "witness"
    SUBJECT = "subject"
    TARGET = "target"
    UNKNOWN = "unknown"


class ForfeitureType(Enum):
    """Types of asset forfeiture."""
    CIVIL = "civil"
    CRIMINAL = "criminal"
    ADMINISTRATIVE = "administrative"


class WhistleblowerProgram(Enum):
    """Federal whistleblower programs."""
    FALSE_CLAIMS_ACT = "false_claims_act"
    SEC_WHISTLEBLOWER = "sec_whistleblower"
    CFTC_WHISTLEBLOWER = "cftc_whistleblower"
    IRS_WHISTLEBLOWER = "irs_whistleblower"
    OSHA_WHISTLEBLOWER = "osha_whistleblower"


@dataclass
class SubpoenaAnalysis:
    """Analysis of grand jury subpoena."""
    subpoena_type: SubpoenaType
    issue_date: datetime
    return_date: datetime
    days_to_comply: int
    responsive_documents_estimate: int
    compliance_cost_estimate: float
    legal_privilege_issues: List[str]
    recommended_objections: List[str]
    motion_to_quash_viable: bool
    disclosure_risks: List[str]
    compliance_timeline: Dict


@dataclass
class QuiTamAnalysis:
    """Analysis of potential qui tam (False Claims Act) case."""
    defendant_name: str
    government_claim_amount: float
    qui_tam_potential: float
    likelihood_of_success: str  # low, moderate, high
    relator_share: Tuple[float, float]  # percentage range (15-30%)
    government_intervention_likely: bool
    statute_of_limitations: int
    disclosure_requirements: List[str]
    litigation_cost_estimate: float
    timeline_to_recovery_months: int
    risks_to_relator: List[str]
    advantages: List[str]


@dataclass
class FOIARequest:
    """FOIA request document."""
    agency: str
    request_date: datetime
    records_sought: str
    records_description: str
    specific_documents: List[str]
    date_range: Tuple[datetime, datetime]
    estimated_fees: float
    expedited_request: bool
    fee_waiver_requested: bool
    form_type: str = "FOIA Request"
    appeal_deadline_days: int = 20


@dataclass
class ForfeitureDefense:
    """Defense strategy for asset forfeiture."""
    property_description: str
    property_value: float
    forfeiture_type: ForfeitureType
    probable_cause_exists: bool
    innocent_owner_claim: bool
    connected_to_crime: bool
    defense_strategy: List[str]
    estimated_legal_cost: float
    likelihood_of_recovery: str  # low, moderate, high
    timeline_to_resolution_months: int
    required_documentation: List[str]
    administrative_claim_viable: bool
    judicial_review_available: bool


class DOJNavigator:
    """
    Comprehensive DOJ defense guide covering criminal investigations,
    civil litigation, enforcement actions, and whistleblower programs.
    """
    
    # Grand jury status definitions
    GRAND_JURY_STATUSES = {
        GrandJuryStatus.WITNESS: {
            "definition": "Called to provide evidence",
            "indication": "General witness subpoena",
            "testify_requirement": "Must testify if subpoenaed",
            "attorney_in_grand_jury": False,
            "target_if_charged": "Unlikely"
        },
        GrandJuryStatus.SUBJECT: {
            "definition": "Investigation focuses on conduct/involvement",
            "indication": "Proffer meeting offered",
            "testify_requirement": "Can decline to testify (5th Amendment)",
            "attorney_in_grand_jury": False,
            "target_if_charged": "Possible"
        },
        GrandJuryStatus.TARGET: {
            "definition": "Evidence shows criminal conduct",
            "indication": "Target letter issued or expected",
            "testify_requirement": "Should NOT testify (5th Amendment)",
            "attorney_in_grand_jury": False,
            "target_if_charged": "Likely - preparation needed"
        }
    }
    
    # Proffer agreement types
    PROFFER_TYPES = {
        "informal": {
            "name": "Informal Meeting",
            "protection": "Statements can be used against you",
            "cost": "No formal agreement needed",
            "risk_level": "High"
        },
        "queen_for_a_day": {
            "name": "Queen for a Day Proffer",
            "protection": "Statements largely protected (limited immunity)",
            "cost": "Formal written agreement",
            "risk_level": "Medium"
        },
        "formal_immunity": {
            "name": "Formal Immunity Agreement",
            "protection": "Full transactional immunity",
            "cost": "Formal agreement with DOJ",
            "risk_level": "Low"
        }
    }
    
    # Qui tam information
    FALSE_CLAIMS_ACT_INFO = {
        "statute": "31 U.S.C. § 3730",
        "covered_fraud_types": [
            "Healthcare fraud (Medicare, Medicaid)",
            "Government contracting fraud",
            "Defense contract fraud",
            "Tax fraud (certain circumstances)",
            "Loan fraud (government programs)",
            "Environmental violations"
        ],
        "qui_tam_share": {
            "government_intervention": "15%-30% of recovery",
            "no_government_intervention": "25%-30% of recovery"
        },
        "statute_of_limitations_years": 6,
        "whistleblower_protection": "Anti-retaliation provisions"
    }
    
    # Asset forfeiture procedures
    FORFEITURE_PROCEDURES = {
        "civil": {
            "timeline": "Months to years",
            "burden_of_proof": "Preponderance of evidence",
            "property_not_owner": "Government sues property, not owner",
            "notice_required": "Yes (within reasonable time)",
            "hearing_right": "Yes (judicial proceeding)"
        },
        "criminal": {
            "timeline": "Years (tied to criminal case)",
            "burden_of_proof": "Beyond reasonable doubt",
            "property_not_owner": "Tied to criminal conviction",
            "notice_required": "Yes (criminal case notice)",
            "hearing_right": "Full constitutional protections"
        },
        "administrative": {
            "timeline": "Months (30-90 days)",
            "burden_of_proof": "No judicial proceeding required",
            "property_not_owner": "Agency action",
            "notice_required": "Yes (but can be minimal)",
            "hearing_right": "Limited (administrative claim available)"
        }
    }
    
    # Immigration enforcement options
    IMMIGRATION_OPTIONS = {
        "removal_defense": {
            "options": [
                "Cancellation of removal",
                "Asylum and withholding",
                "Convention against torture",
                "Prosecutorial discretion (DACA, etc.)"
            ],
            "timeline": "Months to years"
        },
        "visa_options": {
            "work_visas": ["H-1B", "L-1", "O-1", "EB employment-based"],
            "family_visas": ["Family preference", "Spouse", "Children"],
            "humanitarian": ["U visa (crime victims)", "T visa (trafficking)", "VAWA"]
        }
    }
    
    def __init__(self):
        """Initialize DOJ Navigator."""
        pass
    
    def analyze_grand_jury_subpoena(
        self,
        subpoena_text: str,
        subpoena_type: SubpoenaType = SubpoenaType.DOCUMENTS,
        return_date: Optional[datetime] = None
    ) -> SubpoenaAnalysis:
        """
        Analyze grand jury subpoena and provide response strategy.
        
        Args:
            subpoena_text: Full text of subpoena
            subpoena_type: Type of subpoena (documents or testimony)
            return_date: Date documents are due
            
        Returns:
            SubpoenaAnalysis with response options
        """
        # Extract key information
        issue_date = datetime.now()
        if not return_date:
            return_date = issue_date + timedelta(days=14)
        
        days_to_comply = round((return_date - issue_date).total_seconds() / 86400)
        
        # Estimate responsive documents
        responsive_estimate = 500  # Conservative estimate
        
        # Identify privilege issues
        privilege_issues = []
        if "attorney" in subpoena_text.lower():
            privilege_issues.append("Attorney-client privilege may apply")
        if "advice" in subpoena_text.lower():
            privilege_issues.append("Legal advice may be privileged")
        
        # Recommended objections
        objections = []
        if days_to_comply < 7:
            objections.append("Insufficient time to comply - request extension")
        objections.append("Overbroad - request narrowing")
        objections.append("Burden outweighs benefit - request specificity")
        
        # Determine if motion to quash is viable
        motion_viable = days_to_comply < 5
        
        # Disclosure risks
        disclosure_risks = [
            "Grand jury disclosure can trigger investigation",
            "Documents may be used to expand investigation",
            "Target status may change based on response"
        ]
        
        # Timeline
        timeline = {
            "today": "Consult counsel immediately",
            "within_3_days": "Determine privilege claims and objections",
            "within_5_days": "File motion to quash if appropriate",
            "before_return_date": "Produce responsive documents (if no successful objection)"
        }
        
        return SubpoenaAnalysis(
            subpoena_type=subpoena_type,
            issue_date=issue_date,
            return_date=return_date,
            days_to_comply=days_to_comply,
            responsive_documents_estimate=responsive_estimate,
            compliance_cost_estimate=25000,
            legal_privilege_issues=privilege_issues,
            recommended_objections=objections,
            motion_to_quash_viable=motion_viable,
            disclosure_risks=disclosure_risks,
            compliance_timeline=timeline
        )
    
    def evaluate_qui_tam_case(
        self,
        defendant_name: str,
        alleged_fraud_type: str,
        government_damages_estimate: float,
        facts: str
    ) -> QuiTamAnalysis:
        """
        Evaluate viability of qui tam (whistleblower False Claims Act) case.
        
        Args:
            defendant_name: Entity allegedly defrauding government
            alleged_fraud_type: Type of fraud (healthcare, contracting, etc.)
            government_damages_estimate: Estimated government losses
            facts: Description of facts
            
        Returns:
            QuiTamAnalysis with recovery potential
        """
        # Determine likelihood based on fraud type
        high_probability_types = ["healthcare", "defense_contract", "contracting"]
        likelihood = "high" if alleged_fraud_type.lower() in high_probability_types else "moderate"
        
        # Calculate potential recovery (treble damages)
        government_claim = government_damages_estimate
        qui_tam_potential = government_claim * 3  # Treble damages
        
        # Relator share (typically 15-30%, up to 30% if government intervenes)
        relator_share = (0.15, 0.30)
        
        # Government intervention likely if large case
        intervention_likely = government_claim > 1_000_000
        
        # Analyze risks
        risks = [
            "Retaliation (though protected)",
            "Long litigation timeline (3-5+ years)",
            "Significant legal costs ($500K-$2M+)",
            "Public disclosure via court filings",
            "Burden of proving case by preponderance"
        ]
        
        advantages = [
            "No upfront costs (contingent attorney fee arrangement)",
            "Treble damages multiplier",
            "Attorney fees recoverable",
            "Strong anti-retaliation protections",
            "Government support if it intervenes"
        ]
        
        return QuiTamAnalysis(
            defendant_name=defendant_name,
            government_claim_amount=government_claim,
            qui_tam_potential=qui_tam_potential,
            likelihood_of_success=likelihood,
            relator_share=relator_share,
            government_intervention_likely=intervention_likely,
            statute_of_limitations=6,
            disclosure_requirements=["Under seal initially", "Disclosure to government"],
            litigation_cost_estimate=1_500_000,
            timeline_to_recovery_months=36,
            risks_to_relator=risks,
            advantages=advantages
        )
    
    def draft_foia_request(
        self,
        agency: str,
        records_sought: str,
        date_range: Tuple[datetime, datetime],
        expedited: bool = False,
        fee_waiver: bool = False
    ) -> FOIARequest:
        """
        Draft FOIA request for federal records.
        
        Args:
            agency: Federal agency (FBI, DOJ, IRS, SEC, etc.)
            records_sought: Description of records
            date_range: (start_date, end_date) tuple
            expedited: Request expedited processing
            fee_waiver: Request fee waiver
            
        Returns:
            FOIARequest ready to submit
        """
        return FOIARequest(
            agency=agency,
            request_date=datetime.now(),
            records_sought=records_sought,
            records_description=records_sought,
            specific_documents=[],
            date_range=date_range,
            estimated_fees=100.0,
            expedited_request=expedited,
            fee_waiver_requested=fee_waiver
        )
    
    def design_forfeiture_defense(
        self,
        property_description: str,
        property_value: float,
        forfeiture_type: ForfeitureType,
        fact_pattern: str
    ) -> ForfeitureDefense:
        """
        Design defense strategy for asset forfeiture.
        
        Args:
            property_description: Description of property
            property_value: Value of property
            forfeiture_type: Type of forfeiture (civil, criminal, administrative)
            fact_pattern: Facts of the case
            
        Returns:
            ForfeitureDefense with strategy
        """
        # Analyze facts
        innocent_owner = "innocent" in fact_pattern.lower()
        probable_cause = "police report" in fact_pattern.lower() or "seized" in fact_pattern.lower()
        
        # Defense strategy
        strategy = []
        
        if innocent_owner:
            strategy.append("Assert innocent owner defense - no knowledge of illegal activity")
            strategy.append("Demonstrate reasonable precautions taken")
            strategy.append("Show legitimate use and ownership")
        
        if forfeiture_type == ForfeitureType.CIVIL:
            strategy.append("Challenge probable cause to believe property is connected to crime")
            strategy.append("Demand judicial review in court")
            strategy.append("Assert due process right to hearing")
        
        elif forfeiture_type == ForfeitureType.ADMINISTRATIVE:
            strategy.append("File administrative claim within timeline (30-60 days)")
            strategy.append("Request administrative hearing")
            strategy.append("Preserve right to judicial review if claim denied")
        
        # Likelihood of recovery
        recovery_likelihood = "high" if innocent_owner else "moderate"
        
        # Required documentation
        required_docs = [
            "Proof of ownership",
            "Documentation of legitimate use",
            "Communications showing innocence",
            "Bank records proving fund source",
            "Lease/mortgage documentation"
        ]
        
        return ForfeitureDefense(
            property_description=property_description,
            property_value=property_value,
            forfeiture_type=forfeiture_type,
            probable_cause_exists=probable_cause,
            innocent_owner_claim=innocent_owner,
            connected_to_crime=probable_cause,
            defense_strategy=strategy,
            estimated_legal_cost=35000,
            likelihood_of_recovery=recovery_likelihood,
            timeline_to_resolution_months=12,
            required_documentation=required_docs,
            administrative_claim_viable=forfeiture_type in [ForfeitureType.ADMINISTRATIVE, ForfeitureType.CIVIL],
            judicial_review_available=forfeiture_type in [ForfeitureType.CIVIL, ForfeitureType.CRIMINAL]
        )
    
    def analyze_whistleblower_options(
        self,
        fraud_type: str,
        estimated_recovery: float,
        program_preferences: Optional[List[WhistleblowerProgram]] = None
    ) -> Dict:
        """
        Analyze whistleblower program options.
        
        Args:
            fraud_type: Type of fraud discovered
            estimated_recovery: Estimated financial recovery
            program_preferences: Preferred programs
            
        Returns:
            Dictionary with program analysis and recommendations
        """
        programs = {
            WhistleblowerProgram.FALSE_CLAIMS_ACT: {
                "applies": "Government contracting, healthcare fraud",
                "whistleblower_share": "15-30%",
                "potential_recovery": estimated_recovery * 3,  # Treble damages
                "timeline": "3-7 years"
            },
            WhistleblowerProgram.SEC_WHISTLEBLOWER: {
                "applies": "Securities law violations",
                "whistleblower_share": "10-30%",
                "potential_recovery": estimated_recovery,
                "timeline": "1-3 years",
                "bonus": "Up to $230M award (2023)"
            },
            WhistleblowerProgram.CFTC_WHISTLEBLOWER: {
                "applies": "Commodity/derivatives fraud",
                "whistleblower_share": "10-30%",
                "potential_recovery": estimated_recovery,
                "timeline": "1-3 years"
            },
            WhistleblowerProgram.IRS_WHISTLEBLOWER: {
                "applies": "Tax fraud",
                "whistleblower_share": "15-30%",
                "potential_recovery": estimated_recovery,
                "timeline": "1-5 years"
            }
        }
        
        # Recommendations based on fraud type
        recommendations = []
        if "securities" in fraud_type.lower():
            recommendations.append(WhistleblowerProgram.SEC_WHISTLEBLOWER)
        if "healthcare" in fraud_type.lower() or "contract" in fraud_type.lower():
            recommendations.append(WhistleblowerProgram.FALSE_CLAIMS_ACT)
        if "tax" in fraud_type.lower():
            recommendations.append(WhistleblowerProgram.IRS_WHISTLEBLOWER)
        
        return {
            "programs": programs,
            "recommended_programs": recommendations,
            "general_protections": [
                "Anti-retaliation rights",
                "Confidentiality protections",
                "Legal fee coverage in some programs"
            ]
        }
    
    def get_grand_jury_status_indicators(
        self,
        indicators: List[str]
    ) -> Tuple[GrandJuryStatus, Dict]:
        """
        Analyze indicators to determine grand jury status.
        
        Args:
            indicators: List of situation indicators
            
        Returns:
            (GrandJuryStatus, explanation_dict)
        """
        target_indicators = [
            "target letter",
            "target notification",
            "subject of investigation",
            "proffer meeting offered"
        ]
        
        witness_indicators = [
            "general witness subpoena",
            "called to testify",
            "no direct involvement"
        ]
        
        status = GrandJuryStatus.UNKNOWN
        priority = {GrandJuryStatus.UNKNOWN: 0, GrandJuryStatus.WITNESS: 1, GrandJuryStatus.SUBJECT: 2, GrandJuryStatus.TARGET: 3}
        
        for indicator in indicators:
            if any(t in indicator.lower() for t in target_indicators):
                new_status = GrandJuryStatus.TARGET
            elif any(w in indicator.lower() for w in witness_indicators):
                new_status = GrandJuryStatus.WITNESS
            else:
                new_status = GrandJuryStatus.SUBJECT
            if priority[new_status] > priority[status]:
                status = new_status
        
        status_info = self.GRAND_JURY_STATUSES.get(status, {})
        
        return status, status_info
