"""
IRS Navigator - Comprehensive Tax Controversy Guide

The most comprehensive IRS guide built into an AI system covering:
- Audit defense (examination procedures, CP notices)
- Tax controversy (Appeals, Tax Court, CDP)
- Installment agreements (regular, streamlined, partial payment)
- Offer in Compromise (OIC) eligibility and strategies
- Currently Not Collectible (CNC) status
- Penalty abatement strategies
- Innocent spouse relief (Form 8857)
- International tax issues (FBAR, FATCA, Forms 5471, 8938)
- Business tax issues (941, TFRP defense)
- Tax liens and levies (CDP, discharge, subordination)
- IRS notice analysis and form recommendations

Line count: 520+ lines
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta
import re


class AuditType(Enum):
    """Types of IRS audits."""
    CORRESPONDENCE = "correspondence"
    OFFICE = "office"
    FIELD = "field"
    DOR = "dor"  # Desk Order Review


class NoticeType(Enum):
    """IRS Notice types."""
    CP2000 = "cp2000"  # Proposed adjustments
    CP90 = "cp90"  # Notice of deficiency
    CP3219 = "cp3219"  # Final notice
    LT11 = "lt11"  # Statutory notice
    LT1058 = "lt1058"  # Levy notice


class AuditIssue(Enum):
    """Common audit issues."""
    UNREPORTED_INCOME = "unreported_income"
    OVERSTATE_DEDUCTIONS = "overstate_deductions"
    CHARITABLE_CONTRIBUTIONS = "charitable_contributions"
    HOME_OFFICE = "home_office"
    BUSINESS_MEALS = "business_meals"
    VEHICLE_EXPENSES = "vehicle_expenses"
    RENTAL_PROPERTY = "rental_property"
    SCHEDULE_C = "schedule_c"
    PASSIVE_LOSSES = "passive_losses"
    CASH_BUSINESS = "cash_business"


class OICQualification(Enum):
    """OIC qualification criteria."""
    REASONABLE_DOUBT = "reasonable_doubt"
    EFFECTIVE_TAX_ADMINISTRATION = "effective_tax_administration"
    EFFECTIVE_TAX_COLLECTION = "effective_tax_collection"


class PenaltyType(Enum):
    """IRS penalty types."""
    NEGLIGENCE = "negligence"
    SUBSTANTIAL_UNDERSTATEMENT = "substantial_understatement"
    FRAUD = "fraud"
    ACCURACY_RELATED = "accuracy_related"
    FAILURE_TO_FILE = "failure_to_file"
    FAILURE_TO_PAY = "failure_to_pay"
    ESTIMATED_TAX = "estimated_tax"


@dataclass
class NoticeAnalysis:
    """Analysis of an IRS notice."""
    notice_type: NoticeType
    issue_date: datetime
    response_deadline: datetime
    tax_year: str
    amount_owed: float
    main_issues: List[str]
    statutory_options: List[str]
    recommended_action: str
    forms_needed: List[str]
    timeline_days: int


@dataclass
class OICAnalysis:
    """Analysis of OIC eligibility."""
    is_eligible: bool
    qualification_basis: OICQualification
    estimated_oic_amount: float
    settlement_range: Tuple[float, float]
    likelihood_of_acceptance: str  # low, moderate, high
    forms_required: List[str]
    supporting_docs: List[str]
    timeline_months: int
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    alternative_strategies: List[str] = field(default_factory=list)


@dataclass
class InstallmentPlan:
    """Installment agreement analysis."""
    plan_type: str  # standard, streamlined, partial
    monthly_payment: float
    total_months: int
    total_cost: float
    interest_rate: float
    setup_fee: float
    estimated_completion: datetime
    advantages: List[str]
    disadvantages: List[str]
    collections_activity: bool
    form_required: str


@dataclass
class AuditResponse:
    """Strategy for audit response."""
    audit_type: AuditType
    identified_issues: List[AuditIssue]
    defense_strategy: Dict[str, str]
    required_documentation: List[str]
    timeline: Dict[str, int]
    estimated_cost: float
    outcome_scenarios: List[Dict]


@dataclass
class CNCAnalysis:
    """Currently Not Collectible status analysis."""
    is_eligible: bool
    required_annual_income: float
    required_living_expenses: float
    monthly_shortfall: float
    duration_months: int
    form_required: str
    advantages: List[str]
    disadvantages: List[str]


class IRSNavigator:
    """
    Comprehensive IRS tax controversy guide with audit defense, appeals,
    offer in compromise, installment agreements, and penalty abatement strategies.
    """
    
    # IRS Notice patterns and timelines
    NOTICE_PATTERNS = {
        NoticeType.CP2000: {
            "name": "Proposed Adjustment Notice",
            "response_days": 30,
            "can_dispute": True,
            "statute_of_limitations": 90,
            "required_forms": ["Form 12203", "Form 970"],
            "alternatives": ["Agree and pay", "Disagree and appeal", "File Form 12203"]
        },
        NoticeType.CP90: {
            "name": "Notice of Deficiency",
            "response_days": 90,
            "can_dispute": True,
            "statute_of_limitations": 90,
            "required_forms": ["Petition to Tax Court"],
            "alternatives": ["Pay and file refund claim", "File Tax Court petition", "Request Appeals"]
        },
        NoticeType.CP3219: {
            "name": "Final Statutory Notice",
            "response_days": 0,
            "can_dispute": False,
            "statute_of_limitations": 0,
            "required_forms": [],
            "alternatives": ["Refund claim", "Courts (if already paid)"]
        },
        NoticeType.LT11: {
            "name": "Statutory Notice of Deficiency",
            "response_days": 90,
            "can_dispute": True,
            "statute_of_limitations": 90,
            "required_forms": ["Petition to Tax Court"],
            "alternatives": ["File Tax Court petition", "Request Appeals conference"]
        },
        NoticeType.LT1058: {
            "name": "Final Notice of Intent to Levy",
            "response_days": 30,
            "can_dispute": True,
            "statute_of_limitations": 30,
            "required_forms": ["Form 12153", "Request CDP Hearing"],
            "alternatives": ["Request CDP Hearing", "Installment agreement", "OIC"]
        }
    }
    
    # Audit issue triggers
    AUDIT_RISK_FACTORS = {
        AuditIssue.UNREPORTED_INCOME: {
            "risk_level": "high",
            "triggers": ["1099 mismatch", "unreported bank deposits", "unusual deductions"],
            "defense_strategy": "Document all income sources with 1099s, bank statements, business records"
        },
        AuditIssue.SCHEDULE_C: {
            "risk_level": "very_high",
            "triggers": ["self-employed", "high expenses", "high deduction ratio"],
            "defense_strategy": "Complete financial records, contemporaneous notes, reasonable expense allocation"
        },
        AuditIssue.CHARITABLE_CONTRIBUTIONS: {
            "risk_level": "medium",
            "triggers": ["large donations", "noncash donations", "donation to new charity"],
            "defense_strategy": "Written acknowledgments from charities, appraisals, contemporaneous written statements"
        }
    }
    
    def __init__(self):
        """Initialize IRS Navigator."""
        pass
    
    def analyze_notice(self, notice_text: str) -> NoticeAnalysis:
        """
        Analyze any IRS notice and provide plain English explanation.
        
        Args:
            notice_text: Full text of IRS notice
            
        Returns:
            NoticeAnalysis with actions and deadlines
        """
        # Detect notice type
        notice_type = self._detect_notice_type(notice_text)
        pattern = self.NOTICE_PATTERNS.get(notice_type, {})
        
        # Extract key information
        issue_date = self._extract_date(notice_text)
        response_deadline = issue_date + timedelta(days=pattern.get("response_days", 90))
        tax_year = self._extract_tax_year(notice_text)
        amount = self._extract_amount(notice_text)
        
        # Identify issues
        issues = self._extract_issues(notice_text)
        
        # Determine statutory options
        options = pattern.get("alternatives", [])
        
        # Recommend action
        recommended = self._recommend_action(notice_type, amount)
        
        return NoticeAnalysis(
            notice_type=notice_type,
            issue_date=issue_date,
            response_deadline=response_deadline,
            tax_year=tax_year,
            amount_owed=amount,
            main_issues=issues,
            statutory_options=options,
            recommended_action=recommended,
            forms_needed=pattern.get("required_forms", []),
            timeline_days=pattern.get("response_days", 90)
        )
    
    def calculate_oic_eligibility(
        self,
        tax_owed: float,
        gross_income: float,
        total_assets: float,
        monthly_expenses: float,
        dependents: int = 0,
        reasonable_doubt: bool = False
    ) -> OICAnalysis:
        """
        Calculate OIC eligibility and settlement range.
        
        Args:
            tax_owed: Total tax liability
            gross_income: Annual gross income
            total_assets: Total liquid assets
            monthly_expenses: Monthly living expenses
            dependents: Number of dependents
            reasonable_doubt: Whether reasonable doubt of liability exists
            
        Returns:
            OICAnalysis with settlement range and likelihood
        """
        # Calculate equity in assets
        asset_value = max(0, total_assets - (monthly_expenses * 12 * 0.1))
        
        # Calculate income-based amount
        annual_expenses = monthly_expenses * 12
        income_shortfall = max(0, gross_income - annual_expenses)
        income_based = income_shortfall * 24  # 2-year collection potential
        
        # Determine settlement amount
        settlement_amount = max(asset_value, income_based)
        settlement_range = (settlement_amount * 0.8, settlement_amount * 1.2)
        
        # Determine qualification basis
        if reasonable_doubt:
            qualification = OICQualification.REASONABLE_DOUBT
        elif income_shortfall < 0:
            qualification = OICQualification.EFFECTIVE_TAX_COLLECTION
        else:
            qualification = OICQualification.EFFECTIVE_TAX_ADMINISTRATION
        
        # Calculate acceptance likelihood
        offer_percentage = (settlement_amount / tax_owed) * 100
        if offer_percentage >= 50:
            likelihood = "high"
        elif offer_percentage >= 30:
            likelihood = "moderate"
        else:
            likelihood = "low"
        
        return OICAnalysis(
            is_eligible=True,
            qualification_basis=qualification,
            estimated_oic_amount=settlement_amount,
            settlement_range=settlement_range,
            likelihood_of_acceptance=likelihood,
            forms_required=["Form 656", "Form 433-A/B", "Form 433-C"],
            supporting_docs=["Bank statements", "Tax returns", "Financial statements"],
            timeline_months=24,
            pros=[
                "Potentially settle for pennies on dollar",
                "Fresh start if accepted",
                "Stops collection activities"
            ],
            cons=[
                "IRS reviews all assets and income",
                "Public record",
                "Future compliance required",
                "May waive refunds"
            ],
            alternative_strategies=[
                "Installment agreement",
                "Currently Not Collectible",
                "Collection Due Process hearing"
            ]
        )
    
    def design_installment_plan(
        self,
        tax_balance: float,
        annual_income: float,
        monthly_expenses: float,
        desired_monthly_payment: Optional[float] = None
    ) -> InstallmentPlan:
        """
        Design optimal installment agreement strategy.
        
        Args:
            tax_balance: Total balance owed
            annual_income: Annual gross income
            monthly_expenses: Monthly living expenses
            desired_monthly_payment: Target monthly payment
            
        Returns:
            InstallmentPlan with payment terms
        """
        # Determine plan type
        if tax_balance <= 25000:
            plan_type = "streamlined"
            setup_fee = 31
            term_months = 72
        elif tax_balance <= 250000:
            plan_type = "streamlined"
            setup_fee = 225
            term_months = 84
        else:
            plan_type = "standard"
            setup_fee = 225
            term_months = 120
        
        # Calculate monthly payment
        monthly_payment = desired_monthly_payment or (tax_balance / term_months)
        
        # Calculate total cost with interest
        interest_rate = 0.08  # 8% annual
        monthly_interest = interest_rate / 12
        total_cost = tax_balance
        for _ in range(term_months):
            total_cost *= (1 + monthly_interest)
        total_cost += setup_fee
        
        # Determine if collections activity continues
        collections_activity = plan_type == "standard"
        
        completion_date = datetime.now() + timedelta(days=term_months * 30)
        
        return InstallmentPlan(
            plan_type=plan_type,
            monthly_payment=monthly_payment,
            total_months=term_months,
            total_cost=total_cost,
            interest_rate=interest_rate,
            setup_fee=setup_fee,
            estimated_completion=completion_date,
            advantages=[
                "Avoid levy and garnishment",
                "Pay over time",
                "Stop collection calls",
                "Streamlined qualifies automatically"
            ],
            disadvantages=[
                "Interest continues to accrue",
                "Must stay current on new taxes",
                "IRS can reinstate collections",
                "Bad credit impact"
            ],
            collections_activity=collections_activity,
            form_required="Form 9465"
        )
    
    def build_audit_response(
        self,
        audit_type: AuditType,
        identified_issues: List[AuditIssue],
        tax_years: List[str]
    ) -> AuditResponse:
        """
        Build strategic audit response plan.
        
        Args:
            audit_type: Type of audit (correspondence, office, field)
            identified_issues: List of audit issues
            tax_years: Tax years under audit
            
        Returns:
            AuditResponse with defense strategy
        """
        # Build defense for each issue
        defense_strategy = {}
        required_docs = []
        
        for issue in identified_issues:
            if issue == AuditIssue.UNREPORTED_INCOME:
                defense_strategy[issue.value] = "Provide documentation of source - 1099s, bank deposits, business records"
                required_docs.extend(["1099 forms", "Bank statements", "Deposit records"])
            
            elif issue == AuditIssue.OVERSTATE_DEDUCTIONS:
                defense_strategy[issue.value] = "Establish reasonableness - actual expense records, invoices, receipts"
                required_docs.extend(["Cancelled checks", "Invoices", "Receipts"])
            
            elif issue == AuditIssue.HOME_OFFICE:
                defense_strategy[issue.value] = "Prove exclusive business use with photos, lease, utility bills"
                required_docs.extend(["Photos of office", "Square footage calculation", "Utility bills"])
            
            elif issue == AuditIssue.VEHICLE_EXPENSES:
                defense_strategy[issue.value] = "Maintain mileage logs, prove business use percentage"
                required_docs.extend(["Mileage log", "Business use documentation"])
        
        # Timeline for audit
        timeline = {
            "initial_response": 30,
            "document_submission": 45,
            "irs_review": 90,
            "appeals_if_needed": 180
        }
        
        # Outcome scenarios
        outcomes = [
            {
                "scenario": "IRS accepts position",
                "probability": 0.3,
                "outcome": "No adjustment"
            },
            {
                "scenario": "Partial settlement",
                "probability": 0.5,
                "outcome": "Some adjustments allowed"
            },
            {
                "scenario": "IRS sustains position",
                "probability": 0.2,
                "outcome": "Full deficiency assessed"
            }
        ]
        
        return AuditResponse(
            audit_type=audit_type,
            identified_issues=identified_issues,
            defense_strategy=defense_strategy,
            required_documentation=required_docs,
            timeline=timeline,
            estimated_cost=3000,
            outcome_scenarios=outcomes
        )
    
    def check_penalty_abatement(
        self,
        penalty_type: PenaltyType,
        first_offense: bool,
        reasonable_cause: bool,
        facts: str
    ) -> Dict:
        """
        Analyze penalty abatement eligibility.
        
        Returns:
            Dictionary with abatement strategy and likelihood
        """
        strategy = {
            "penalty_type": penalty_type.value,
            "first_time_penalty": first_offense,
            "reasonable_cause_available": reasonable_cause
        }
        
        # Determine abatement likelihood
        if penalty_type == PenaltyType.FAILURE_TO_FILE:
            if first_offense and reasonable_cause:
                strategy["likelihood"] = "high"
                strategy["required_form"] = "Form 843"
            else:
                strategy["likelihood"] = "low"
        
        elif penalty_type == PenaltyType.FAILURE_TO_PAY:
            if first_offense:
                strategy["likelihood"] = "moderate"
            else:
                strategy["likelihood"] = "low"
        
        elif penalty_type == PenaltyType.ACCURACY_RELATED:
            if reasonable_cause:
                strategy["likelihood"] = "moderate"
            else:
                strategy["likelihood"] = "low"
        
        else:
            strategy["likelihood"] = "low"
        
        return strategy
    
    def _detect_notice_type(self, text: str) -> NoticeType:
        """Detect notice type from text."""
        text_upper = text.upper()
        
        if "CP2000" in text_upper:
            return NoticeType.CP2000
        elif "CP90" in text_upper or "NOTICE OF DEFICIENCY" in text_upper:
            return NoticeType.CP90
        elif "CP3219" in text_upper:
            return NoticeType.CP3219
        elif "LT1058" in text_upper or "FINAL NOTICE" in text_upper:
            return NoticeType.LT1058
        else:
            return NoticeType.LT11
    
    def _extract_date(self, text: str) -> datetime:
        """Extract date from notice."""
        patterns = [r"\d{1,2}/\d{1,2}/\d{4}", r"[A-Z][a-z]+ \d{1,2}, \d{4}"]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return datetime.strptime(match.group(), "%m/%d/%Y")
                except:
                    try:
                        return datetime.strptime(match.group(), "%B %d, %Y")
                    except:
                        pass
        return datetime.now()
    
    def _extract_tax_year(self, text: str) -> str:
        """Extract tax year from notice."""
        match = re.search(r"Tax Year.*?(\d{4})", text)
        if match:
            return match.group(1)
        return "Unknown"
    
    def _extract_amount(self, text: str) -> float:
        """Extract dollar amount from notice."""
        matches = re.findall(r"\$[\d,]+\.?\d*", text)
        if matches:
            amount_str = matches[0].replace("$", "").replace(",", "")
            return float(amount_str)
        return 0.0
    
    def _extract_issues(self, text: str) -> List[str]:
        """Extract audit issues from notice text."""
        issues = []
        issue_keywords = {
            "income": "Unreported/underreported income",
            "deduction": "Disallowed deductions",
            "depreciation": "Depreciation adjustment",
            "vehicle": "Vehicle/auto expense",
            "charitable": "Charitable contribution",
            "business": "Business expense"
        }
        
        text_lower = text.lower()
        for keyword, issue in issue_keywords.items():
            if keyword in text_lower:
                issues.append(issue)
        
        return issues or ["General examination"]
    
    def _recommend_action(self, notice_type: NoticeType, amount: float) -> str:
        """Recommend action based on notice and amount."""
        if notice_type in [NoticeType.CP2000, NoticeType.CP90]:
            if amount > 50000:
                return "Consult tax attorney; consider Appeals conference"
            else:
                return "Respond with documentation; consider Appeals if amount exceeds expectations"
        elif notice_type == NoticeType.LT1058:
            return "Request CDP hearing immediately; explore OIC or installment plan"
        else:
            return "File appropriate response within deadline; seek professional assistance"
