"""
Comprehensive pytest tests for Federal Agencies Navigator modules.

Tests IRS, SEC, CFPB/FTC, and DOJ navigators with 50+ test functions.

Line count: 450+ lines
"""

import pytest
from datetime import datetime, timedelta
from ..irs_navigator import (
    IRSNavigator, NoticeType, AuditType, AuditIssue, 
    OICQualification, PenaltyType
)
from ..sec_navigator import SECNavigator, ExemptionType, OfferingType
from ..cfpb_ftc_navigator import (
    CFPBNavigator, FTCNavigator, ViolationType, 
    DebtCollectionViolation, IdentityTheftType
)
from ..doj_navigator import (
    DOJNavigator, SubpoenaType, GrandJuryStatus, 
    ForfeitureType, WhistleblowerProgram
)


# ===== IRS Navigator Tests =====

class TestIRSNavigator:
    """Test cases for IRS Navigator."""
    
    def setup_method(self):
        """Setup for each test."""
        self.irs = IRSNavigator()
    
    def test_notice_analyzer_detects_cp2000(self):
        """Test detection of CP2000 notice."""
        notice_text = "This is a CP2000 notice proposing adjustments to your tax return"
        analysis = self.irs.analyze_notice(notice_text)
        assert analysis.notice_type == NoticeType.CP2000
    
    def test_notice_analyzer_detects_cp90(self):
        """Test detection of CP90 (Notice of Deficiency)."""
        notice_text = "Notice of Deficiency CP90 Tax Year 2022"
        analysis = self.irs.analyze_notice(notice_text)
        assert analysis.notice_type == NoticeType.CP90
    
    def test_notice_analyzer_extracts_deadline(self):
        """Test extraction of response deadline."""
        notice_text = "CP2000 notice dated 01/15/2024"
        analysis = self.irs.analyze_notice(notice_text)
        assert analysis.timeline_days > 0
    
    def test_notice_analyzer_identifies_issues(self):
        """Test identification of audit issues from notice."""
        notice_text = "Proposed adjustments to business income and vehicle deductions"
        analysis = self.irs.analyze_notice(notice_text)
        assert len(analysis.main_issues) > 0
    
    def test_oic_eligible_low_asset_high_income_gap(self):
        """Test OIC eligibility with low assets and income gap."""
        analysis = self.irs.calculate_oic_eligibility(
            tax_owed=100_000,
            gross_income=40_000,
            total_assets=5_000,
            monthly_expenses=3_000
        )
        assert analysis.is_eligible
        assert analysis.estimated_oic_amount > 0
    
    def test_oic_settlement_range_reasonable(self):
        """Test OIC settlement range is reasonable."""
        analysis = self.irs.calculate_oic_eligibility(
            tax_owed=50_000,
            gross_income=50_000,
            total_assets=10_000,
            monthly_expenses=2_500
        )
        min_settle, max_settle = analysis.settlement_range
        assert min_settle < max_settle
        assert min_settle < analysis.estimated_oic_amount
    
    def test_oic_reasonable_doubt_sets_qualification(self):
        """Test reasonable doubt sets correct qualification basis."""
        analysis = self.irs.calculate_oic_eligibility(
            tax_owed=100_000,
            gross_income=100_000,
            total_assets=100_000,
            monthly_expenses=5_000,
            reasonable_doubt=True
        )
        assert analysis.qualification_basis == OICQualification.REASONABLE_DOUBT
    
    def test_oic_forms_required_included(self):
        """Test required forms are included."""
        analysis = self.irs.calculate_oic_eligibility(
            tax_owed=50_000,
            gross_income=60_000,
            total_assets=10_000,
            monthly_expenses=3_000
        )
        assert "Form 656" in analysis.forms_required
        assert "Form 433-A/B" in analysis.forms_required
    
    def test_installment_plan_streamlined_eligible(self):
        """Test streamlined installment plan eligibility."""
        plan = self.irs.design_installment_plan(
            tax_balance=20_000,
            annual_income=60_000,
            monthly_expenses=3_000
        )
        assert plan.plan_type == "streamlined"
        assert plan.setup_fee == 31
    
    def test_installment_plan_standard_large_balance(self):
        """Test standard plan for large balance."""
        plan = self.irs.design_installment_plan(
            tax_balance=300_000,
            annual_income=100_000,
            monthly_expenses=5_000
        )
        assert plan.plan_type == "standard"
        assert plan.setup_fee == 225
    
    def test_installment_plan_monthly_payment_calculation(self):
        """Test monthly payment calculation."""
        plan = self.irs.design_installment_plan(
            tax_balance=50_000,
            annual_income=75_000,
            monthly_expenses=3_000
        )
        assert plan.monthly_payment > 0
        assert plan.total_cost >= plan.monthly_payment * plan.total_months
    
    def test_audit_response_unreported_income(self):
        """Test audit response for unreported income issue."""
        response = self.irs.build_audit_response(
            AuditType.FIELD,
            [AuditIssue.UNREPORTED_INCOME],
            ["2023"]
        )
        assert len(response.required_documentation) > 0
        assert "1099" in str(response.required_documentation).lower()
    
    def test_audit_response_home_office_deduction(self):
        """Test audit response for home office deduction."""
        response = self.irs.build_audit_response(
            AuditType.OFFICE,
            [AuditIssue.HOME_OFFICE],
            ["2022", "2023"]
        )
        assert len(response.defense_strategy) > 0
    
    def test_audit_response_multiple_issues(self):
        """Test audit response with multiple issues."""
        response = self.irs.build_audit_response(
            AuditType.FIELD,
            [AuditIssue.SCHEDULE_C, AuditIssue.VEHICLE_EXPENSES],
            ["2023"]
        )
        assert len(response.identified_issues) == 2
        assert len(response.outcome_scenarios) > 0
    
    def test_penalty_abatement_first_offense_reasonable_cause(self):
        """Test penalty abatement eligibility - first offense with reasonable cause."""
        strategy = self.irs.check_penalty_abatement(
            PenaltyType.FAILURE_TO_FILE,
            first_offense=True,
            reasonable_cause=True,
            facts="Hurricane delayed filing"
        )
        assert strategy["likelihood"] == "high"
    
    def test_penalty_abatement_accuracy_related_weak_case(self):
        """Test weak case for accuracy related penalty."""
        strategy = self.irs.check_penalty_abatement(
            PenaltyType.ACCURACY_RELATED,
            first_offense=False,
            reasonable_cause=False,
            facts="Calculation error"
        )
        assert strategy["likelihood"] == "low"


# ===== SEC Navigator Tests =====

class TestSECNavigator:
    """Test cases for SEC Navigator."""
    
    def setup_method(self):
        """Setup for each test."""
        self.sec = SECNavigator()
    
    def test_reg_d_506b_no_general_solicitation(self):
        """Test 506(b) exemption without general solicitation."""
        analysis = self.sec.analyze_offering_exemption(
            "private_placement",
            ["accredited", "non_accredited"],
            general_solicitation=False,
            offering_amount=5_000_000
        )
        assert analysis.is_applicable
        assert analysis.exemption_type == ExemptionType.REG_D_506B
    
    def test_reg_d_506c_general_solicitation_ok(self):
        """Test 506(c) allows general solicitation."""
        analysis = self.sec.analyze_offering_exemption(
            "private_placement",
            ["accredited"],
            general_solicitation=True,
            offering_amount=5_000_000
        )
        assert analysis.is_applicable
        assert analysis.exemption_type == ExemptionType.REG_D_506C
    
    def test_reg_d_506c_non_accredited_not_allowed(self):
        """Test 506(c) doesn't allow non-accredited investors."""
        analysis = self.sec.analyze_offering_exemption(
            "private_placement",
            ["accredited", "non_accredited"],
            general_solicitation=True,
            offering_amount=5_000_000
        )
        assert len(analysis.conditions_not_met) > 0
    
    def test_regulation_a_large_offering(self):
        """Test Regulation A+ for large offering."""
        analysis = self.sec.analyze_offering_exemption(
            "mini_ipo",
            ["accredited", "non_accredited"],
            general_solicitation=True,
            offering_amount=50_000_000
        )
        assert analysis.is_applicable
    
    def test_form_d_creation(self):
        """Test Form D creation."""
        form_d = self.sec.draft_form_d(
            issuer_name="TechCorp Inc",
            offering_description="Series A Preferred Stock",
            offering_amount=2_000_000,
            investors_accredited=10,
            investors_non_accredited=5,
            use_of_proceeds={"operations": 1_000_000, "marketing": 500_000, "r_and_d": 500_000}
        )
        assert form_d.issuer_name == "TechCorp Inc"
        assert form_d.amount_offered == 2_000_000
        assert form_d.accredited_investors == 10
    
    def test_wells_notice_fraud_allegations(self):
        """Test Wells Notice analysis with fraud allegations."""
        analysis = self.sec.respond_to_wells_notice(
            "SecuritiesCo Inc",
            ["Securities fraud", "Misrepresentation of risks"],
            "Company failed to disclose material risks"
        )
        assert "Section 17(a)" in analysis.securities_act_sections
        assert len(analysis.defense_strategy) > 0
    
    def test_insider_trading_rule_10b5_violation(self):
        """Test insider trading Rule 10b-5 violation detection."""
        analysis = self.sec.check_insider_trading_rules(
            "officer",
            has_material_non_public_info=True,
            transaction_type="sale",
            amount=100_000,
            company_name="PublicCorp Inc"
        )
        assert not analysis.is_compliant
        assert len(analysis.rule_10b5_issues) > 0
    
    def test_insider_trading_section_16_requires_form4(self):
        """Test Section 16 requires Form 4 filing."""
        analysis = self.sec.check_insider_trading_rules(
            "director",
            has_material_non_public_info=False,
            transaction_type="purchase",
            amount=50_000,
            company_name="PublicCorp Inc"
        )
        assert analysis.form_required == "Form 4"
        assert analysis.filing_deadline is not None
    
    def test_reporting_requirements_public_company(self):
        """Test reporting requirements for public company."""
        reqs = self.sec.get_reporting_requirements("public_company")
        assert "annual_report" in reqs
        assert reqs["annual_report"]["form"] == "Form 10-K"
        assert reqs["quarterly_report"]["form"] == "Form 10-Q"


# ===== CFPB/FTC Navigator Tests =====

class TestCFPBNavigator:
    """Test cases for CFPB Navigator."""
    
    def setup_method(self):
        """Setup for each test."""
        self.cfpb = CFPBNavigator()
    
    def test_complaint_draft(self):
        """Test drafting CFPB complaint."""
        complaint = self.cfpb.draft_cfpb_complaint(
            "John Doe",
            "john@example.com",
            "MortageBank Inc",
            "mortgage",
            "Improper loan modification denial",
            "Applied for modification, bank refused without reason"
        )
        assert complaint.consumer_name == "John Doe"
        assert complaint.company_name == "MortageBank Inc"
        assert complaint.complaint_status == "draft"
    
    def test_tila_violation_analysis(self):
        """Test TILA violation analysis."""
        analysis = self.cfpb.analyze_tila_violation(
            loan_amount=200_000,
            apr=5.5,
            finance_charge=55_000,
            payment_terms="360 months"
        )
        assert "Finance charge amount" in analysis["required_disclosures"]
        assert analysis["rescission_available"]
    
    def test_respa_kickback_violation(self):
        """Test RESPA kickback violation detection."""
        analysis = self.cfpb.analyze_respa_violation(
            "mortgage",
            kickback_or_unearned_fee=True,
            affiliated_business_disclosure=True
        )
        assert len(analysis["violations_found"]) > 0


class TestFTCNavigator:
    """Test cases for FTC Navigator."""
    
    def setup_method(self):
        """Setup for each test."""
        self.ftc = FTCNavigator()
    
    def test_fdcpa_communication_timing_violation(self):
        """Test FDCPA communication timing violation."""
        analysis = self.ftc.analyze_debt_collection_violation(
            "Called at 11:30 PM without prior authorization",
            "FastCollect LLC",
            DebtCollectionViolation.COMMUNICATION_TIMING
        )
        assert analysis.is_violation
        assert analysis.severity == "high"
        assert analysis.statutory_damages_available
    
    def test_fdcpa_third_party_contact_critical(self):
        """Test FDCPA third party disclosure is critical."""
        analysis = self.ftc.analyze_debt_collection_violation(
            "Called employer to discuss debt",
            "BadCollectors Inc",
            DebtCollectionViolation.THIRD_PARTY_CONTACT
        )
        assert analysis.severity == "critical"
        assert analysis.damages_potential > 10_000
    
    def test_fdcpa_harassment_settlement_likelihood(self):
        """Test harassment violations have high settlement likelihood."""
        analysis = self.ftc.analyze_debt_collection_violation(
            "Called 20 times in one day",
            "CollectionCo",
            DebtCollectionViolation.PHONE_HARASSMENT
        )
        assert analysis.settlement_likelihood == "high"
    
    def test_fdcpa_attorney_fees_available(self):
        """Test attorney fees available in FDCPA violations."""
        analysis = self.ftc.analyze_debt_collection_violation(
            "Any violation",
            "AnyCollector",
            DebtCollectionViolation.COMMUNICATION_TIMING
        )
        assert analysis.attorney_fees_available
    
    def test_fcra_damages_calculation_statutory(self):
        """Test FCRA statutory damages calculation."""
        calc = self.ftc.calculate_fcra_damages(
            ["inaccurate_reporting", "failure_to_investigate"],
            actual_damages=2_000,
            willful_violation=False
        )
        assert calc.statutory_damages_available
        assert calc.total_statutory_damages > 0
        assert calc.total_potential_recovery > calc.actual_damages
    
    def test_fcra_damages_willful_multiplier(self):
        """Test FCRA willful violation treble damages."""
        calc = self.ftc.calculate_fcra_damages(
            ["inaccurate_reporting"],
            actual_damages=1_000,
            willful_violation=True
        )
        assert calc.willful_multiplier == 3.0
    
    def test_fcra_attorney_fees_always_available(self):
        """Test FCRA attorney fees are always available."""
        calc = self.ftc.calculate_fcra_damages(
            ["any_violation"],
            willful_violation=False
        )
        assert calc.estimated_attorney_fees > 0
    
    def test_identity_theft_recovery_plan_credit_file(self):
        """Test identity theft recovery plan for credit file theft."""
        plan = self.ftc.build_identity_theft_recovery_plan(
            IdentityTheftType.CREDIT_FILE,
            datetime.now(),
            ["SSN", "Name", "Address"]
        )
        assert plan.theft_type == IdentityTheftType.CREDIT_FILE
        assert len(plan.immediate_actions) > 0
        assert plan.credit_freeze_recommended
        assert len(plan.steps) > 0
    
    def test_identity_theft_recovery_plan_account_monitoring(self):
        """Test identity theft plan includes account monitoring."""
        plan = self.ftc.build_identity_theft_recovery_plan(
            IdentityTheftType.CREDIT_CARD,
            datetime.now(),
            ["Card number"]
        )
        assert plan.account_monitoring_months > 0
        assert plan.estimated_recovery_time_months > 0


# ===== DOJ Navigator Tests =====

class TestDOJNavigator:
    """Test cases for DOJ Navigator."""
    
    def setup_method(self):
        """Setup for each test."""
        self.doj = DOJNavigator()
    
    def test_subpoena_analysis_documents_short_deadline(self):
        """Test subpoena analysis with short deadline."""
        return_date = datetime.now() + timedelta(days=3)
        analysis = self.doj.analyze_grand_jury_subpoena(
            "You are commanded to produce documents",
            SubpoenaType.DOCUMENTS,
            return_date
        )
        assert analysis.days_to_comply == 3
        assert analysis.motion_to_quash_viable
    
    def test_subpoena_analysis_compliance_cost(self):
        """Test subpoena compliance cost estimation."""
        return_date = datetime.now() + timedelta(days=14)
        analysis = self.doj.analyze_grand_jury_subpoena(
            "Subpoena for all communications",
            SubpoenaType.DOCUMENTS,
            return_date
        )
        assert analysis.compliance_cost_estimate > 0
    
    def test_qui_tam_healthcare_fraud_high_likelihood(self):
        """Test qui tam with healthcare fraud has high likelihood."""
        analysis = self.doj.evaluate_qui_tam_case(
            "Medicare Diagnostics Inc",
            "healthcare",
            5_000_000,
            "Fraudulent billing claims"
        )
        assert analysis.likelihood_of_success == "high"
    
    def test_qui_tam_recovery_treble_damages(self):
        """Test qui tam recovery includes treble damages."""
        analysis = self.doj.evaluate_qui_tam_case(
            "Corp",
            "healthcare",
            2_000_000,
            "Facts"
        )
        assert analysis.qui_tam_potential == 6_000_000
    
    def test_qui_tam_relator_share_range(self):
        """Test qui tam relator share is reasonable range."""
        analysis = self.doj.evaluate_qui_tam_case(
            "Corp",
            "fraud",
            1_000_000,
            "Facts"
        )
        assert analysis.relator_share[0] == 0.15
        assert analysis.relator_share[1] == 0.30
    
    def test_qui_tam_government_intervention_likely(self):
        """Test government intervention likely for large cases."""
        analysis = self.doj.evaluate_qui_tam_case(
            "Corp",
            "defense",
            5_000_000,
            "Facts"
        )
        assert analysis.government_intervention_likely
    
    def test_foia_request_draft(self):
        """Test FOIA request drafting."""
        start = datetime(2020, 1, 1)
        end = datetime(2024, 12, 31)
        foia = self.doj.draft_foia_request(
            "FBI",
            "Investigation records",
            (start, end),
            expedited=True,
            fee_waiver=True
        )
        assert foia.agency == "FBI"
        assert foia.expedited_request
        assert foia.fee_waiver_requested
    
    def test_forfeiture_defense_innocent_owner(self):
        """Test forfeiture defense for innocent owner."""
        defense = self.doj.design_forfeiture_defense(
            "2022 Honda Civic",
            25_000,
            ForfeitureType.CIVIL,
            "Vehicle owned by innocent person, spouse committed crime"
        )
        assert defense.innocent_owner_claim
        assert len(defense.defense_strategy) > 0
    
    def test_forfeiture_defense_administrative_claim(self):
        """Test forfeiture defense administrative claim available."""
        defense = self.doj.design_forfeiture_defense(
            "Cash in bank account",
            50_000,
            ForfeitureType.ADMINISTRATIVE,
            "Seized without warrant"
        )
        assert defense.administrative_claim_viable
    
    def test_grand_jury_status_target_indicators(self):
        """Test grand jury status detection - target."""
        status, info = self.doj.get_grand_jury_status_indicators(
            ["target letter received", "under investigation"]
        )
        assert status == GrandJuryStatus.TARGET
    
    def test_grand_jury_status_witness_indicators(self):
        """Test grand jury status detection - witness."""
        status, info = self.doj.get_grand_jury_status_indicators(
            ["general witness subpoena", "called to testify"]
        )
        assert status == GrandJuryStatus.WITNESS
    
    def test_whistleblower_programs_securities(self):
        """Test whistleblower program analysis for securities fraud."""
        programs = self.doj.analyze_whistleblower_options(
            "securities fraud",
            10_000_000
        )
        assert WhistleblowerProgram.SEC_WHISTLEBLOWER in programs["recommended_programs"]


# ===== Integration Tests =====

class TestIntegration:
    """Integration tests across modules."""
    
    def test_irs_and_collection_impact(self):
        """Test IRS options impact on collections."""
        irs = IRSNavigator()
        
        # Compare OIC vs installment plan
        oic = irs.calculate_oic_eligibility(100_000, 40_000, 5_000, 3_000)
        plan = irs.design_installment_plan(100_000, 40_000, 3_000)
        
        # OIC should result in lower total payment
        assert oic.estimated_oic_amount < plan.total_cost
    
    def test_sec_exemption_vs_registration_complexity(self):
        """Test exemption significantly simpler than registration."""
        sec = SECNavigator()
        
        # Exemption analysis
        exemption = sec.analyze_offering_exemption(
            "private_placement",
            ["accredited"],
            False,
            5_000_000
        )
        
        # Should be compliant with minimal forms
        assert exemption.is_applicable
        assert len(exemption.forms_required) <= 2
    
    def test_violations_compound_damages(self):
        """Test that multiple violations increase damages."""
        ftc = FTCNavigator()
        
        # Single violation
        single = ftc.calculate_fcra_damages(["inaccurate_reporting"], 1_000)
        
        # Multiple violations
        multiple = ftc.calculate_fcra_damages(
            ["inaccurate_reporting", "failure_to_investigate", "failure_to disclose"],
            1_000
        )
        
        assert multiple.total_potential_recovery > single.total_potential_recovery


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
