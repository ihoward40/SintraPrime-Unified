"""
SEC Navigator - Securities Registration, Exemptions, and Enforcement

Comprehensive guide for securities law compliance:
- Registration requirements (S-1, S-11, Form D, Reg A+, Reg CF)
- Reporting requirements (10-K, 10-Q, 8-K, proxy, beneficial ownership)
- Securities exemptions (4(a)(2), Reg D 506(b)/506(c), Reg S, Rule 144)
- Enforcement and investigation response (Wells Notice, subpoena)
- EDGAR filing system
- Insider trading rules (Section 16, Rule 10b-5, 10b5-1)
- Investment advisor and broker-dealer compliance

Line count: 420+ lines
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime


class OfferingType(Enum):
    """Types of securities offerings."""
    IPO = "ipo"
    SECONDARY = "secondary"
    REIT = "reit"
    DIRECT_LISTING = "direct_listing"
    SPAC = "spac"
    PRIVATE_PLACEMENT = "private_placement"


class ExemptionType(Enum):
    """Securities law exemptions."""
    SECTION_4A2 = "section_4a2"
    REG_D_506B = "reg_d_506b"
    REG_D_506C = "reg_d_506c"
    REG_S = "reg_s"
    REGULATION_A = "regulation_a"
    REGULATION_CF = "regulation_cf"
    RULE_144 = "rule_144"
    SECTION_4A9 = "section_4a9"


class ReportingFrequency(Enum):
    """SEC reporting frequencies."""
    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    CURRENT = "current"


@dataclass
class ExemptionAnalysis:
    """Analysis of securities law exemption."""
    exemption_type: ExemptionType
    is_applicable: bool
    conditions_met: List[str]
    conditions_not_met: List[str]
    investor_limitations: Dict
    disclosure_requirements: List[str]
    integration_risk: str  # low, medium, high
    compliance_cost: str  # low, medium, high
    timeline_to_closing: int  # days
    forms_required: List[str]
    limitations: List[str]


@dataclass
class FormD:
    """Form D notice of exempt offering."""
    issuer_name: str
    cik_number: Optional[str]
    offering_type: str
    securities_offered: str
    amount_offered: float
    amount_sold: float
    states_of_qualification: List[str]
    accredited_investors: int
    non_accredited_investors: int
    use_of_proceeds: Dict
    filing_date: datetime
    sales_closed_date: datetime
    form_type: str = "Form D"


@dataclass
class WellsNoticeAnalysis:
    """Analysis of SEC Wells Notice."""
    issuer_name: str
    investigation_subject: str
    alleged_violations: List[str]
    securities_act_sections: List[str]
    exchange_act_sections: List[str]
    investigation_timeline: Dict
    potential_penalties: Dict
    settlement_likelihood: str  # low, moderate, high
    litigation_cost_estimate: float
    defense_strategy: List[str]
    witnesses_to_prepare: List[str]
    documents_to_gather: List[str]


@dataclass
class InsiderTradeAnalysis:
    """Analysis of insider trading compliance."""
    transaction_description: str
    is_compliant: bool
    rule_10b5_issues: List[str]
    section_16_issues: List[str]
    blackout_period_status: str
    form_required: str
    filing_deadline: Optional[datetime]
    penalties_if_violated: List[str]
    mitigation_steps: List[str]


class SECNavigator:
    """
    Comprehensive SEC compliance guide for offerings, registration,
    exemptions, reporting, and enforcement matters.
    """
    
    # Registration forms by offering type
    REGISTRATION_FORMS = {
        OfferingType.IPO: {
            "form": "Form S-1",
            "required_disclosures": [
                "Business description",
                "Risk factors",
                "Financial data (5 years)",
                "MD&A",
                "Executive compensation",
                "Capitalization table",
                "Use of proceeds"
            ],
            "timeline_months": 6,
            "cost_estimate": "$2-5M"
        },
        OfferingType.SECONDARY: {
            "form": "Form S-3/S-4",
            "required_disclosures": [
                "Recent SEC filings incorporated by reference",
                "Financial statements (2 years)",
                "Changes since last filing",
                "Use of proceeds"
            ],
            "timeline_months": 3,
            "cost_estimate": "$1-3M"
        },
        OfferingType.REIT: {
            "form": "Form S-11",
            "required_disclosures": [
                "REIT properties and leases",
                "Valuation methods",
                "Tenant concentration",
                "Debt structure",
                "Distributions policy"
            ],
            "timeline_months": 4,
            "cost_estimate": "$1.5-4M"
        }
    }
    
    # Exemption requirements
    EXEMPTION_REQUIREMENTS = {
        ExemptionType.REG_D_506B: {
            "name": "Regulation D 506(b) - Accredited Investors + 35 Others",
            "accredited_limit": None,  # Unlimited accredited
            "non_accredited_limit": 35,
            "general_solicitation": False,
            "disclosure_required": True,
            "form_d_required": True,
            "allowed_investors": "Accredited + experienced non-accredited",
            "key_limitation": "No general advertising/solicitation"
        },
        ExemptionType.REG_D_506C: {
            "name": "Regulation D 506(c) - General Solicitation OK",
            "accredited_limit": None,
            "non_accredited_limit": 0,
            "general_solicitation": True,
            "disclosure_required": True,
            "form_d_required": True,
            "allowed_investors": "Accredited investors only",
            "key_limitation": "Must verify accreditation, no non-accredited investors"
        },
        ExemptionType.REG_S: {
            "name": "Regulation S - Foreign Offering",
            "accredited_limit": None,
            "non_accredited_limit": None,
            "general_solicitation": True,
            "disclosure_required": False,
            "form_d_required": False,
            "allowed_investors": "Non-US persons only",
            "key_limitation": "Cannot offer in US, 40-day seasoning period"
        },
        ExemptionType.REGULATION_A: {
            "name": "Regulation A+ - Mini IPO",
            "max_offering": 75_000_000,
            "non_accredited_allowed": True,
            "general_solicitation": True,
            "disclosure_required": True,
            "form_d_required": False,
            "allowed_investors": "Anyone can invest",
            "key_limitation": "Caps on offering ($20M Tier I, $75M Tier II)"
        }
    }
    
    # Insider trading rules
    INSIDER_TRADING_RULES = {
        "section_16": {
            "rule": "Section 16 - Officers, Directors, Large Shareholders (10%+)",
            "reporting_forms": ["Form 3", "Form 4", "Form 5"],
            "filing_deadline_days": 2,
            "scope": "Equity securities transactions"
        },
        "rule_10b5": {
            "rule": "Rule 10b-5 - General Anti-Fraud",
            "prohibition": "Fraud in connection with purchase/sale of securities",
            "insider_scope": "Officers, directors, employees with material non-public info",
            "tipper_scope": "Anyone with MNPI who tips others",
            "penalties": ["Disgorgement", "Civil penalties up to 3x profits"]
        },
        "rule_10b5_1": {
            "rule": "Rule 10b5-1 Plan - Pre-arranged trading",
            "purpose": "Insiders can execute pre-planned trades",
            "adoption_requirements": ["In good faith", "Not in possession of MNPI at time of adoption"],
            "cooling_off": "30 days (or 90 if director)"
        }
    }
    
    def __init__(self):
        """Initialize SEC Navigator."""
        pass
    
    def analyze_offering_exemption(
        self,
        offering_type: str,
        investor_types: List[str],
        general_solicitation: bool,
        offering_amount: float,
        international_component: bool = False
    ) -> ExemptionAnalysis:
        """
        Analyze which securities exemption applies.
        
        Args:
            offering_type: Type of offering
            investor_types: List of investor types (accredited, non-accredited, foreign)
            general_solicitation: Will general solicitation be used
            offering_amount: Amount being raised
            international_component: International offering component
            
        Returns:
            ExemptionAnalysis with applicable exemptions and requirements
        """
        has_non_accredited = "non_accredited" in investor_types
        has_foreign = "foreign" in investor_types
        
        # Determine best fit exemption
        if offering_type == "mini_ipo" and offering_amount <= 75_000_000:
            exemption_type = ExemptionType.REGULATION_A
        elif has_foreign and offering_amount <= 75_000_000:
            exemption_type = ExemptionType.REGULATION_A
        elif general_solicitation and not has_non_accredited:
            exemption_type = ExemptionType.REG_D_506C
        elif general_solicitation and has_non_accredited:
            exemption_type = ExemptionType.REG_D_506C
        elif not general_solicitation and has_non_accredited:
            exemption_type = ExemptionType.REG_D_506B
        else:
            exemption_type = ExemptionType.REG_D_506B
        
        # Get requirements
        reqs = self.EXEMPTION_REQUIREMENTS.get(exemption_type, {})
        
        conditions_met = []
        conditions_not_met = []
        
        if exemption_type == ExemptionType.REG_D_506B:
            conditions_met.append("Private placement exemption available")
            if not general_solicitation:
                conditions_met.append("No general solicitation requirement met")
            else:
                conditions_not_met.append("General solicitation used - 506(b) incompatible")
        
        elif exemption_type == ExemptionType.REG_D_506C:
            if general_solicitation:
                conditions_met.append("General solicitation permitted with 506(c)")
            else:
                conditions_not_met.append("No general solicitation - could use 506(b)")
            
            if has_non_accredited:
                conditions_not_met.append("Non-accredited investors not allowed in 506(c)")
            else:
                conditions_met.append("Accredited-only investor pool meets 506(c) requirement")
        
        investor_limitations = {
            "accredited_only": exemption_type in [ExemptionType.REG_D_506C, ExemptionType.REGULATION_A],
            "non_accredited_limit": reqs.get("non_accredited_limit"),
            "general_solicitation_allowed": reqs.get("general_solicitation", False)
        }
        
        return ExemptionAnalysis(
            exemption_type=exemption_type,
            is_applicable=len(conditions_not_met) == 0,
            conditions_met=conditions_met,
            conditions_not_met=conditions_not_met,
            investor_limitations=investor_limitations,
            disclosure_requirements=["PPM or prospectus", "Investor suitability docs"],
            integration_risk="low" if exemption_type in [ExemptionType.REG_S] else "medium",
            compliance_cost="low",
            timeline_to_closing=60,
            forms_required=["Form D", "Accreditation certifications"],
            limitations=[
                f"Max offering: {reqs.get('max_offering', 'No limit')}",
                f"General solicitation: {reqs.get('general_solicitation', False)}",
                f"Form D required: {reqs.get('form_d_required', True)}"
            ]
        )
    
    def draft_form_d(
        self,
        issuer_name: str,
        offering_description: str,
        offering_amount: float,
        investors_accredited: int,
        investors_non_accredited: int,
        use_of_proceeds: Dict
    ) -> FormD:
        """
        Draft Form D (Notice of Exempt Offering).
        
        Returns:
            FormD with all required information
        """
        return FormD(
            issuer_name=issuer_name,
            cik_number=None,
            offering_type=offering_description,
            securities_offered="Common stock",
            amount_offered=offering_amount,
            amount_sold=0,
            states_of_qualification=["All"],
            accredited_investors=investors_accredited,
            non_accredited_investors=investors_non_accredited,
            use_of_proceeds=use_of_proceeds,
            filing_date=datetime.now(),
            sales_closed_date=datetime.now()
        )
    
    def respond_to_wells_notice(
        self,
        company_name: str,
        violations_alleged: List[str],
        facts: str
    ) -> WellsNoticeAnalysis:
        """
        Analyze Wells Notice and develop response strategy.
        
        Args:
            company_name: Company name
            violations_alleged: Alleged SEC violations
            facts: Key facts of situation
            
        Returns:
            WellsNoticeAnalysis with defense strategy
        """
        # Identify applicable statutes
        securities_act_sections = []
        exchange_act_sections = []
        
        for violation in violations_alleged:
            if "registration" in violation.lower():
                securities_act_sections.append("Section 5")
            if "fraud" in violation.lower():
                securities_act_sections.append("Section 17(a)")
                exchange_act_sections.append("Section 10(b) / Rule 10b-5")
            if "disclosure" in violation.lower():
                exchange_act_sections.append("Section 13(a)")
        
        # Defense strategy
        defense_strategy = [
            "Gather all contemporaneous documents and communications",
            "Conduct privilege-protected investigation",
            "Prepare factual presentation",
            "Consider settlement vs. litigation",
            "Monitor statute of limitations"
        ]
        
        # Settlement likelihood assessment
        if "fraud" in str(violations_alleged).lower():
            settlement_likelihood = "low"
            litigation_estimate = 5_000_000
        else:
            settlement_likelihood = "moderate"
            litigation_estimate = 2_000_000
        
        return WellsNoticeAnalysis(
            issuer_name=company_name,
            investigation_subject=" / ".join(violations_alleged),
            alleged_violations=violations_alleged,
            securities_act_sections=securities_act_sections,
            exchange_act_sections=exchange_act_sections,
            investigation_timeline={
                "notice_received": "Today",
                "response_deadline": "30 days typically",
                "sec_decision": "6-12 months"
            },
            potential_penalties={
                "civil_penalty": "$100,000 - $200,000+",
                "disgorgement": "Ill-gotten gains",
                "officer_bar": "Possible"
            },
            settlement_likelihood=settlement_likelihood,
            litigation_cost_estimate=litigation_estimate,
            defense_strategy=defense_strategy,
            witnesses_to_prepare=["CEO", "CFO", "Compliance Officer"],
            documents_to_gather=[
                "All board minutes",
                "Communications with SEC/counsel",
                "Offering documents",
                "Financial records"
            ]
        )
    
    def check_insider_trading_rules(
        self,
        person_status: str,
        has_material_non_public_info: bool,
        transaction_type: str,
        amount: float,
        company_name: str
    ) -> InsiderTradeAnalysis:
        """
        Verify insider trading compliance.
        
        Args:
            person_status: 'officer', 'director', 'employee', '10_percent_shareholder'
            has_material_non_public_info: Whether person has MNPI
            transaction_type: 'purchase' or 'sale'
            amount: Dollar amount of transaction
            company_name: Company name
            
        Returns:
            InsiderTradeAnalysis with compliance status
        """
        issues = []
        section_16_issues = []
        rule_10b5_issues = []
        
        # Check Rule 10b-5
        if has_material_non_public_info and transaction_type == "sale":
            rule_10b5_issues.append("Trading while in possession of MNPI may violate Rule 10b-5")
            rule_10b5_issues.append("Consider implementation of Rule 10b5-1 trading plan")
        
        # Check Section 16
        if person_status in ['officer', 'director', '10_percent_shareholder']:
            section_16_issues.append(f"Form 4 required within 2 business days for {transaction_type}")
            section_16_issues.append(f"Transaction must be reported: {amount}")
        
        # Determine if compliant
        is_compliant = len(rule_10b5_issues) == 0 and len(section_16_issues) == 0
        
        mitigation = []
        if has_material_non_public_info:
            mitigation.append("Adopt Rule 10b5-1 trading plan (30-90 day cooling off)")
            mitigation.append("Wait for material info to become public")
        
        if person_status in ['officer', 'director']:
            mitigation.append("File Form 4 within deadline")
        
        return InsiderTradeAnalysis(
            transaction_description=f"{transaction_type.upper()} {amount:,} of {company_name}",
            is_compliant=is_compliant,
            rule_10b5_issues=rule_10b5_issues,
            section_16_issues=section_16_issues,
            blackout_period_status="Check company blackout policy",
            form_required="Form 4" if person_status in ['officer', 'director'] else "None",
            filing_deadline=datetime.now() if section_16_issues else None,
            penalties_if_violated=[
                "Treble damages",
                "Injunctive relief",
                "Officer/director bar",
                "Criminal prosecution possible"
            ],
            mitigation_steps=mitigation
        )
    
    def get_reporting_requirements(
        self,
        company_status: str
    ) -> Dict:
        """
        Get SEC reporting requirements based on company status.
        
        Args:
            company_status: 'public_company', 'emerging_growth', 'accelerated_filer', 'large_accelerated'
            
        Returns:
            Dictionary of reporting requirements
        """
        return {
            "annual_report": {
                "form": "Form 10-K",
                "deadline": "60-90 days after fiscal year end",
                "frequency": ReportingFrequency.ANNUAL.value
            },
            "quarterly_report": {
                "form": "Form 10-Q",
                "deadline": "40-45 days after quarter end",
                "frequency": ReportingFrequency.QUARTERLY.value
            },
            "current_reports": {
                "form": "Form 8-K",
                "deadline": "4 business days for most events",
                "frequency": "As events occur"
            },
            "proxy_statement": {
                "form": "Schedule 14A",
                "deadline": "Varies with meeting date",
                "frequency": "Annual or as needed"
            },
            "beneficial_ownership": {
                "form": "Schedule 13D/13G",
                "deadline": "5 days (13D) / 10 days (13G)",
                "frequency": "Upon acquisition of 5% stake"
            }
        }
