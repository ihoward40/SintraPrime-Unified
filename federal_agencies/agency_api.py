"""
Federal Agencies FastAPI Router

REST API endpoints for IRS, SEC, FTC, CFPB, and DOJ navigators.

Line count: 310+ lines
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta

from .irs_navigator import (
    IRSNavigator, NoticeAnalysis, OICAnalysis, InstallmentPlan, AuditResponse
)
from .sec_navigator import (
    SECNavigator, ExemptionAnalysis, FormD, WellsNoticeAnalysis, InsiderTradeAnalysis
)
from .cfpb_ftc_navigator import (
    CFPBNavigator, FTCNavigator, ViolationAnalysis, CFPBComplaint, 
    FCRSDamagesCalculation, IdentityTheftRecoveryPlan
)
from .doj_navigator import (
    DOJNavigator, SubpoenaAnalysis, QuiTamAnalysis, FOIARequest, ForfeitureDefense
)


# ===== Pydantic Request Models =====

class IRSNoticeRequest(BaseModel):
    """Request to analyze IRS notice."""
    notice_text: str = Field(..., description="Full text of IRS notice")


class OICCalculatorRequest(BaseModel):
    """Request for OIC eligibility calculation."""
    gross_income: float
    total_taxes_owed: float
    total_assets: float
    monthly_expenses: float
    dependents: int = 0
    reasonable_doubt: bool = False


class InstallmentPlanRequest(BaseModel):
    """Request for installment plan design."""
    tax_balance: float
    annual_income: float
    monthly_expenses: float
    desired_monthly_payment: Optional[float] = None


class SECExemptionRequest(BaseModel):
    """Request for securities exemption analysis."""
    offering_type: str
    investor_types: List[str]
    general_solicitation: bool
    offering_amount: float
    international_component: bool = False


class FDCPAViolationRequest(BaseModel):
    """Request for FDCPA violation analysis."""
    violation_facts: str
    collector_name: str
    violation_type: str


class FCRADamagesRequest(BaseModel):
    """Request for FCRA damages calculation."""
    violations: List[str]
    actual_damages: Optional[float] = None
    willful_violation: bool = False


class IdentityTheftRequest(BaseModel):
    """Request for identity theft recovery plan."""
    theft_type: str
    discovery_date: datetime
    documents_compromised: List[str]


class SubpoenaRequest(BaseModel):
    """Request to analyze grand jury subpoena."""
    subpoena_text: str
    subpoena_type: str = "documents"
    return_date: Optional[datetime] = None


class QuiTamRequest(BaseModel):
    """Request to evaluate qui tam case."""
    defendant_name: str
    alleged_fraud_type: str
    government_damages_estimate: float
    facts: str


class FOIARequestForm(BaseModel):
    """Request to draft FOIA request."""
    agency: str
    records_sought: str
    start_date: datetime
    end_date: datetime
    expedited: bool = False
    fee_waiver: bool = False


class ForfeitureDefenseRequest(BaseModel):
    """Request for asset forfeiture defense."""
    property_description: str
    property_value: float
    forfeiture_type: str
    fact_pattern: str


class AuditResponseRequest(BaseModel):
    """Request to build audit response strategy."""
    audit_type: str
    identified_issues: List[str]
    tax_years: List[str]


# ===== Router Setup =====

def create_agencies_router() -> APIRouter:
    """Create federal agencies API router."""
    
    router = APIRouter(prefix="/agencies", tags=["Federal Agencies"])
    
    # Initialize navigators
    irs = IRSNavigator()
    sec = SECNavigator()
    cfpb = CFPBNavigator()
    ftc = FTCNavigator()
    doj = DOJNavigator()
    
    # ===== IRS Endpoints =====
    
    @router.post("/irs/analyze-notice")
    async def analyze_irs_notice(request: IRSNoticeRequest) -> Dict:
        """
        Analyze and decode any IRS notice.
        
        POST /agencies/irs/analyze-notice
        {
            "notice_text": "Dear Taxpayer..."
        }
        """
        try:
            analysis = irs.analyze_notice(request.notice_text)
            
            return {
                "success": True,
                "notice_type": analysis.notice_type.value,
                "issue_date": analysis.issue_date.isoformat(),
                "response_deadline": analysis.response_deadline.isoformat(),
                "tax_year": analysis.tax_year,
                "amount_owed": analysis.amount_owed,
                "main_issues": analysis.main_issues,
                "statutory_options": analysis.statutory_options,
                "recommended_action": analysis.recommended_action,
                "forms_needed": analysis.forms_needed,
                "timeline_days": analysis.timeline_days
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @router.post("/irs/oic-calculator")
    async def calculate_oic_eligibility(request: OICCalculatorRequest) -> Dict:
        """
        Calculate OIC (Offer in Compromise) eligibility and settlement range.
        
        POST /agencies/irs/oic-calculator
        {
            "gross_income": 50000,
            "total_taxes_owed": 100000,
            "total_assets": 25000,
            "monthly_expenses": 3000
        }
        """
        try:
            analysis = irs.calculate_oic_eligibility(
                request.total_taxes_owed,
                request.gross_income,
                request.total_assets,
                request.monthly_expenses,
                request.dependents,
                request.reasonable_doubt
            )
            
            return {
                "success": True,
                "is_eligible": analysis.is_eligible,
                "qualification_basis": analysis.qualification_basis.value,
                "estimated_oic_amount": analysis.estimated_oic_amount,
                "settlement_range": {
                    "minimum": analysis.settlement_range[0],
                    "maximum": analysis.settlement_range[1]
                },
                "likelihood_of_acceptance": analysis.likelihood_of_acceptance,
                "forms_required": analysis.forms_required,
                "supporting_docs": analysis.supporting_docs,
                "timeline_months": analysis.timeline_months,
                "pros": analysis.pros,
                "cons": analysis.cons,
                "alternative_strategies": analysis.alternative_strategies
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @router.post("/irs/installment-plan")
    async def design_installment_plan(request: InstallmentPlanRequest) -> Dict:
        """
        Design optimal installment agreement strategy.
        
        POST /agencies/irs/installment-plan
        {
            "tax_balance": 50000,
            "annual_income": 75000,
            "monthly_expenses": 3000
        }
        """
        try:
            plan = irs.design_installment_plan(
                request.tax_balance,
                request.annual_income,
                request.monthly_expenses,
                request.desired_monthly_payment
            )
            
            return {
                "success": True,
                "plan_type": plan.plan_type,
                "monthly_payment": plan.monthly_payment,
                "total_months": plan.total_months,
                "total_cost": plan.total_cost,
                "interest_rate": plan.interest_rate,
                "setup_fee": plan.setup_fee,
                "estimated_completion": plan.estimated_completion.isoformat(),
                "advantages": plan.advantages,
                "disadvantages": plan.disadvantages,
                "collections_activity": plan.collections_activity,
                "form_required": plan.form_required
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @router.post("/irs/audit-response")
    async def build_audit_response(request: AuditResponseRequest) -> Dict:
        """
        Build audit defense strategy.
        
        POST /agencies/irs/audit-response
        {
            "audit_type": "field",
            "identified_issues": ["unreported_income", "overstate_deductions"],
            "tax_years": ["2022", "2023"]
        }
        """
        try:
            from .irs_navigator import AuditType, AuditIssue
            
            audit_type = AuditType(request.audit_type.lower())
            issues = [AuditIssue(issue.lower()) for issue in request.identified_issues]
            
            response = irs.build_audit_response(audit_type, issues, request.tax_years)
            
            return {
                "success": True,
                "audit_type": response.audit_type.value,
                "identified_issues": [i.value for i in response.identified_issues],
                "defense_strategy": response.defense_strategy,
                "required_documentation": response.required_documentation,
                "timeline": response.timeline,
                "estimated_cost": response.estimated_cost,
                "outcome_scenarios": response.outcome_scenarios
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # ===== SEC Endpoints =====
    
    @router.post("/sec/exemption-analysis")
    async def analyze_offering_exemption(request: SECExemptionRequest) -> Dict:
        """
        Analyze which securities exemption applies.
        
        POST /agencies/sec/exemption-analysis
        {
            "offering_type": "private_placement",
            "investor_types": ["accredited"],
            "general_solicitation": false,
            "offering_amount": 5000000
        }
        """
        try:
            analysis = sec.analyze_offering_exemption(
                request.offering_type,
                request.investor_types,
                request.general_solicitation,
                request.offering_amount,
                request.international_component
            )
            
            return {
                "success": True,
                "exemption_type": analysis.exemption_type.value,
                "is_applicable": analysis.is_applicable,
                "conditions_met": analysis.conditions_met,
                "conditions_not_met": analysis.conditions_not_met,
                "investor_limitations": analysis.investor_limitations,
                "disclosure_requirements": analysis.disclosure_requirements,
                "integration_risk": analysis.integration_risk,
                "compliance_cost": analysis.compliance_cost,
                "timeline_to_closing": analysis.timeline_to_closing,
                "forms_required": analysis.forms_required,
                "limitations": analysis.limitations
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # ===== CFPB/FTC Endpoints =====
    
    @router.post("/cfpb/violation-analysis")
    async def analyze_debt_collection(request: FDCPAViolationRequest) -> Dict:
        """
        Analyze potential FDCPA violation.
        
        POST /agencies/cfpb/violation-analysis
        {
            "violation_facts": "Collector called at 11pm without cease letter",
            "collector_name": "ABC Collections",
            "violation_type": "communication_timing"
        }
        """
        try:
            from .cfpb_ftc_navigator import DebtCollectionViolation
            
            violation_type = DebtCollectionViolation(request.violation_type)
            analysis = ftc.analyze_debt_collection_violation(
                request.violation_facts,
                request.collector_name,
                violation_type
            )
            
            return {
                "success": True,
                "is_violation": analysis.is_violation,
                "severity": analysis.severity,
                "damages_potential": analysis.damages_potential,
                "statutory_damages_available": analysis.statutory_damages_available,
                "statutory_damages_range": {
                    "minimum": analysis.statutory_damages_range[0],
                    "maximum": analysis.statutory_damages_range[1]
                },
                "attorney_fees_available": analysis.attorney_fees_available,
                "settlement_likelihood": analysis.settlement_likelihood,
                "recommended_actions": analysis.recommended_actions
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @router.post("/ftc/complaint")
    async def navigate_ftc_complaint(request: IdentityTheftRequest) -> Dict:
        """
        Create identity theft recovery plan.
        
        POST /agencies/ftc/complaint
        {
            "theft_type": "credit_file",
            "discovery_date": "2024-01-15T00:00:00",
            "documents_compromised": ["SSN", "Credit card"]
        }
        """
        try:
            from .cfpb_ftc_navigator import IdentityTheftType
            
            theft_type = IdentityTheftType(request.theft_type)
            plan = ftc.build_identity_theft_recovery_plan(
                theft_type,
                request.discovery_date,
                request.documents_compromised
            )
            
            return {
                "success": True,
                "theft_type": plan.theft_type.value,
                "immediate_actions": plan.immediate_actions,
                "steps": plan.steps,
                "credit_freeze_recommended": plan.credit_freeze_recommended,
                "account_monitoring_months": plan.account_monitoring_months,
                "estimated_recovery_time_months": plan.estimated_recovery_time_months,
                "ongoing_precautions": plan.ongoing_precautions
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @router.post("/ftc/fcra-damages")
    async def calculate_fcra_damages(request: FCRADamagesRequest) -> Dict:
        """
        Calculate potential FCRA damages.
        
        POST /agencies/ftc/fcra-damages
        {
            "violations": ["inaccurate_reporting", "failure_to_investigate"],
            "actual_damages": 5000,
            "willful_violation": true
        }
        """
        try:
            calc = ftc.calculate_fcra_damages(
                request.violations,
                request.actual_damages,
                request.willful_violation
            )
            
            return {
                "success": True,
                "violations": calc.violations,
                "actual_damages": calc.actual_damages,
                "statutory_damages_available": calc.statutory_damages_available,
                "statutory_damages_count": calc.statutory_damages_count,
                "total_statutory_damages": calc.total_statutory_damages,
                "estimated_attorney_fees": calc.estimated_attorney_fees,
                "total_potential_recovery": calc.total_potential_recovery,
                "factors_favorable": calc.factors_favorable,
                "factors_unfavorable": calc.factors_unfavorable
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # ===== DOJ Endpoints =====
    
    @router.post("/doj/subpoena-analysis")
    async def analyze_subpoena(request: SubpoenaRequest) -> Dict:
        """
        Analyze grand jury subpoena and response options.
        
        POST /agencies/doj/subpoena-analysis
        {
            "subpoena_text": "You are commanded to appear...",
            "subpoena_type": "documents",
            "return_date": "2024-02-15T00:00:00"
        }
        """
        try:
            from .doj_navigator import SubpoenaType
            
            subpoena_type = SubpoenaType(request.subpoena_type)
            analysis = doj.analyze_grand_jury_subpoena(
                request.subpoena_text,
                subpoena_type,
                request.return_date
            )
            
            return {
                "success": True,
                "subpoena_type": analysis.subpoena_type.value,
                "return_date": analysis.return_date.isoformat(),
                "days_to_comply": analysis.days_to_comply,
                "responsive_documents_estimate": analysis.responsive_documents_estimate,
                "compliance_cost_estimate": analysis.compliance_cost_estimate,
                "legal_privilege_issues": analysis.legal_privilege_issues,
                "recommended_objections": analysis.recommended_objections,
                "motion_to_quash_viable": analysis.motion_to_quash_viable,
                "disclosure_risks": analysis.disclosure_risks,
                "compliance_timeline": analysis.compliance_timeline
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @router.post("/doj/qui-tam")
    async def evaluate_qui_tam(request: QuiTamRequest) -> Dict:
        """
        Evaluate False Claims Act (qui tam) case viability.
        
        POST /agencies/doj/qui-tam
        {
            "defendant_name": "ABC Healthcare Corp",
            "alleged_fraud_type": "healthcare",
            "government_damages_estimate": 5000000,
            "facts": "Fraudulent billing practices..."
        }
        """
        try:
            analysis = doj.evaluate_qui_tam_case(
                request.defendant_name,
                request.alleged_fraud_type,
                request.government_damages_estimate,
                request.facts
            )
            
            return {
                "success": True,
                "government_claim_amount": analysis.government_claim_amount,
                "qui_tam_potential": analysis.qui_tam_potential,
                "likelihood_of_success": analysis.likelihood_of_success,
                "relator_share": {
                    "minimum_percent": int(analysis.relator_share[0] * 100),
                    "maximum_percent": int(analysis.relator_share[1] * 100)
                },
                "government_intervention_likely": analysis.government_intervention_likely,
                "statute_of_limitations": analysis.statute_of_limitations,
                "litigation_cost_estimate": analysis.litigation_cost_estimate,
                "timeline_to_recovery_months": analysis.timeline_to_recovery_months,
                "risks_to_relator": analysis.risks_to_relator,
                "advantages": analysis.advantages
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @router.post("/doj/foia")
    async def draft_foia_request(request: FOIARequestForm) -> Dict:
        """
        Draft FOIA request.
        
        POST /agencies/doj/foia
        {
            "agency": "FBI",
            "records_sought": "Documents related to investigation",
            "start_date": "2020-01-01T00:00:00",
            "end_date": "2024-12-31T00:00:00"
        }
        """
        try:
            foia = doj.draft_foia_request(
                request.agency,
                request.records_sought,
                (request.start_date, request.end_date),
                request.expedited,
                request.fee_waiver
            )
            
            return {
                "success": True,
                "agency": foia.agency,
                "request_date": foia.request_date.isoformat(),
                "records_sought": foia.records_sought,
                "date_range": {
                    "start": foia.date_range[0].isoformat(),
                    "end": foia.date_range[1].isoformat()
                },
                "estimated_fees": foia.estimated_fees,
                "expedited_request": foia.expedited_request,
                "fee_waiver_requested": foia.fee_waiver_requested,
                "appeal_deadline_days": foia.appeal_deadline_days
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @router.post("/doj/forfeiture-defense")
    async def design_forfeiture_defense(request: ForfeitureDefenseRequest) -> Dict:
        """
        Design asset forfeiture defense strategy.
        
        POST /agencies/doj/forfeiture-defense
        {
            "property_description": "2022 Toyota Camry",
            "property_value": 25000,
            "forfeiture_type": "civil",
            "fact_pattern": "Vehicle seized during traffic stop"
        }
        """
        try:
            from .doj_navigator import ForfeitureType
            
            forfeiture_type = ForfeitureType(request.forfeiture_type)
            defense = doj.design_forfeiture_defense(
                request.property_description,
                request.property_value,
                forfeiture_type,
                request.fact_pattern
            )
            
            return {
                "success": True,
                "property_description": defense.property_description,
                "property_value": defense.property_value,
                "forfeiture_type": defense.forfeiture_type.value,
                "innocent_owner_claim": defense.innocent_owner_claim,
                "defense_strategy": defense.defense_strategy,
                "estimated_legal_cost": defense.estimated_legal_cost,
                "likelihood_of_recovery": defense.likelihood_of_recovery,
                "timeline_to_resolution_months": defense.timeline_to_resolution_months,
                "required_documentation": defense.required_documentation
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    return router
