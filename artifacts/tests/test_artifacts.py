"""
Test Suite — SintraPrime-Unified Artifacts Engine
At least 40 tests covering all major components.
"""

import sys
import os

# Add the parent of the artifacts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest

from artifacts import (
    DocumentRenderer,
    DocumentStyle,
    RenderedDocument,
    DocumentPackage,
    LEGAL_TRADITIONAL,
    FINANCIAL_PROFESSIONAL,
    CORPORATE_MODERN,
    GOVERNMENT_OFFICIAL,
    SINTRAPRIME_SIGNATURE,
    LegalDocumentLibrary,
    FinancialReportTemplates,
    CreditReportAnalyzer,
    DisputePackage,
)


# ======================================================================
# FIXTURES
# ======================================================================

@pytest.fixture
def renderer():
    return DocumentRenderer()

@pytest.fixture
def library():
    return LegalDocumentLibrary()

@pytest.fixture
def financial():
    return FinancialReportTemplates()

@pytest.fixture
def credit_analyzer():
    return CreditReportAnalyzer()

@pytest.fixture
def sample_legal_doc():
    return {
        "title": "MOTION TO DISMISS",
        "court": "UNITED STATES DISTRICT COURT, DISTRICT OF [STATE]",
        "case_number": "2024-CV-00001",
        "plaintiff": "Jane Doe",
        "defendant": "Acme Corporation",
        "attorney": "John Smith",
        "bar_number": "123456",
        "firm": "Smith & Associates LLP",
        "sections": [
            {
                "title": "INTRODUCTION",
                "body": "Defendant Acme Corporation moves to dismiss this action.",
                "subsections": [],
            },
            {
                "title": "LEGAL STANDARD",
                "body": "Under Federal Rule of Civil Procedure 12(b)(6).",
                "subsections": [],
            },
        ],
    }

@pytest.fixture
def sample_letter():
    return {
        "sender_name": "Alice Johnson",
        "sender_firm": "Johnson Law Firm",
        "sender_address": "100 Main Street",
        "sender_city_state": "New York, NY 10001",
        "recipient_name": "Bob Williams",
        "recipient_address": "200 Park Ave",
        "recipient_city_state": "New York, NY 10002",
        "subject": "Demand for Payment",
        "body_paragraphs": [
            "This letter constitutes formal notice of demand.",
            "Please remit payment within ten days.",
        ],
        "cc": ["File"],
    }

@pytest.fixture
def sample_contract():
    return {
        "title": "SERVICE AGREEMENT",
        "effective_date": "January 1, 2025",
        "governing_law": "New York",
        "parties": [
            {"name": "Acme LLC", "type": "Client"},
            {"name": "Dev Corp", "type": "Contractor"},
        ],
        "recitals": [
            "Client desires to retain Contractor for software development services",
        ],
        "sections": [
            {
                "title": "SERVICES",
                "body": "Contractor shall provide software development services.",
                "subsections": [],
            },
        ],
    }

@pytest.fixture
def sample_financial_report():
    return {
        "title": "ANNUAL FINANCIAL REPORT",
        "prepared_by": "CFO",
        "key_metrics": {"Revenue": "$1,000,000", "EBITDA": "$250,000"},
        "sections": [
            {
                "title": "Revenue Analysis",
                "body": "Revenue grew 25% year-over-year.",
                "tables": [],
            }
        ],
    }

@pytest.fixture
def sample_credit_profile():
    return {
        "name": "Jane Doe",
        "score": 742,
        "payment_history_pct": 98,
        "utilization_pct": 18,
        "history_years": 8,
        "total_accounts": 6,
        "derogatory_marks": 0,
        "hard_inquiries": 1,
    }

@pytest.fixture
def sample_dispute_accounts():
    return [
        {
            "creditor": "ABC Bank",
            "account_number": "XXXX-1234",
            "amount": "500",
            "dispute_reason": "This is not my account — identity theft.",
            "bureaus": ["Equifax", "Experian", "TransUnion"],
            "supporting_docs": ["FTC Identity Theft Report", "Police Report"],
        },
        {
            "creditor": "XYZ Collections",
            "account_number": "XXXX-5678",
            "amount": "200",
            "dispute_reason": "Debt paid in full on 01/01/2024.",
            "bureaus": ["Equifax", "Experian"],
            "supporting_docs": ["Paid receipt", "Bank statement"],
        },
    ]


# ======================================================================
# DOCUMENT STYLE PRESET TESTS
# ======================================================================

class TestDocumentStylePresets:
    def test_legal_traditional_theme(self):
        assert LEGAL_TRADITIONAL.theme == "legal"

    def test_financial_professional_theme(self):
        assert FINANCIAL_PROFESSIONAL.theme == "financial"

    def test_corporate_modern_theme(self):
        assert CORPORATE_MODERN.theme == "corporate"

    def test_government_official_theme(self):
        assert GOVERNMENT_OFFICIAL.theme == "government"

    def test_sintraprime_signature_is_default(self):
        assert SINTRAPRIME_SIGNATURE.theme == "modern"

    def test_all_presets_have_footer(self):
        for style in [LEGAL_TRADITIONAL, FINANCIAL_PROFESSIONAL,
                      CORPORATE_MODERN, GOVERNMENT_OFFICIAL, SINTRAPRIME_SIGNATURE]:
            assert style.footer_text

    def test_all_presets_have_logo(self):
        for style in [LEGAL_TRADITIONAL, FINANCIAL_PROFESSIONAL,
                      CORPORATE_MODERN, GOVERNMENT_OFFICIAL, SINTRAPRIME_SIGNATURE]:
            assert style.logo_text

    def test_style_colors_are_hex(self):
        for style in [LEGAL_TRADITIONAL, FINANCIAL_PROFESSIONAL]:
            assert style.primary_color.startswith("#")
            assert len(style.primary_color) == 7


# ======================================================================
# DOCUMENT RENDERER TESTS
# ======================================================================

class TestDocumentRenderer:
    def test_renderer_creates_with_default_style(self, renderer):
        assert renderer.default_style is not None

    def test_render_legal_document_returns_rendered_document(self, renderer, sample_legal_doc):
        result = renderer.render_legal_document(sample_legal_doc)
        assert isinstance(result, RenderedDocument)

    def test_legal_document_contains_title(self, renderer, sample_legal_doc):
        result = renderer.render_legal_document(sample_legal_doc)
        assert "MOTION TO DISMISS" in result.content_text

    def test_legal_document_contains_plaintiff(self, renderer, sample_legal_doc):
        result = renderer.render_legal_document(sample_legal_doc)
        assert "JANE DOE" in result.content_text

    def test_legal_document_contains_defendant(self, renderer, sample_legal_doc):
        result = renderer.render_legal_document(sample_legal_doc)
        assert "ACME CORPORATION" in result.content_text

    def test_legal_document_contains_certificate_of_service(self, renderer, sample_legal_doc):
        result = renderer.render_legal_document(sample_legal_doc)
        assert "CERTIFICATE OF SERVICE" in result.content_text

    def test_legal_document_has_signature_block(self, renderer, sample_legal_doc):
        result = renderer.render_legal_document(sample_legal_doc)
        assert "Respectfully submitted" in result.content_text

    def test_legal_document_has_html_output(self, renderer, sample_legal_doc):
        result = renderer.render_legal_document(sample_legal_doc)
        assert "<html" in result.content_html
        assert "</html>" in result.content_html

    def test_legal_document_has_markdown_output(self, renderer, sample_legal_doc):
        result = renderer.render_legal_document(sample_legal_doc)
        assert "```" in result.content_markdown

    def test_legal_document_page_count_positive(self, renderer, sample_legal_doc):
        result = renderer.render_legal_document(sample_legal_doc)
        assert result.page_count >= 1

    def test_render_letter_full_block_format(self, renderer, sample_letter):
        result = renderer.render_letter(sample_letter)
        assert "Alice Johnson" in result.content_text
        assert "Bob Williams" in result.content_text
        assert "Demand for Payment" in result.content_text

    def test_render_letter_has_cc_line(self, renderer, sample_letter):
        result = renderer.render_letter(sample_letter)
        assert "cc:" in result.content_text

    def test_render_contract_contains_parties(self, renderer, sample_contract):
        result = renderer.render_contract(sample_contract)
        assert "Acme LLC" in result.content_text or "ACME LLC" in result.content_text

    def test_render_contract_has_signature_page(self, renderer, sample_contract):
        result = renderer.render_contract(sample_contract)
        assert "SIGNATURE PAGE" in result.content_text

    def test_render_contract_has_governing_law(self, renderer, sample_contract):
        result = renderer.render_contract(sample_contract)
        assert "New York" in result.content_text

    def test_render_financial_report_returns_rendered_doc(self, renderer, sample_financial_report):
        result = renderer.render_financial_report(sample_financial_report)
        assert isinstance(result, RenderedDocument)

    def test_render_financial_report_has_title(self, renderer, sample_financial_report):
        result = renderer.render_financial_report(sample_financial_report)
        assert "ANNUAL FINANCIAL REPORT" in result.content_text

    def test_render_financial_report_has_key_metrics(self, renderer, sample_financial_report):
        result = renderer.render_financial_report(sample_financial_report)
        assert "EXECUTIVE SUMMARY" in result.content_text

    def test_create_document_package_returns_package(self, renderer, sample_legal_doc, sample_letter):
        cover = {"title": "LEGAL PACKAGE", "date": "January 1, 2025"}
        result = renderer.create_document_package(
            [sample_legal_doc, sample_letter],
            cover,
        )
        assert isinstance(result, DocumentPackage)

    def test_document_package_has_toc(self, renderer, sample_legal_doc):
        cover = {"title": "DOCUMENT PACKAGE"}
        result = renderer.create_document_package([sample_legal_doc], cover)
        assert "TABLE OF CONTENTS" in result.table_of_contents

    def test_document_package_has_cover_page(self, renderer, sample_legal_doc):
        cover = {"title": "MY PACKAGE"}
        result = renderer.create_document_package([sample_legal_doc], cover)
        assert "MY PACKAGE" in result.cover_page

    def test_document_package_full_text_includes_all(self, renderer, sample_legal_doc):
        cover = {"title": "FULL PACKAGE"}
        result = renderer.create_document_package([sample_legal_doc], cover)
        full = result.full_text
        assert "FULL PACKAGE" in full


# ======================================================================
# LEGAL DOCUMENT LIBRARY TESTS
# ======================================================================

class TestLegalDocumentLibrary:
    def test_library_instantiates(self, library):
        assert library is not None

    def test_list_templates_returns_list(self, library):
        templates = library.list_templates()
        assert isinstance(templates, list)
        assert len(templates) >= 40

    def test_revocable_living_trust_not_empty(self, library):
        tmpl = library.get_template("revocable_living_trust")
        assert len(tmpl) > 100

    def test_revocable_trust_has_bracket_fields(self, library):
        tmpl = library.get_template("revocable_living_trust")
        assert "[" in tmpl and "]" in tmpl

    def test_revocable_trust_has_trustee_section(self, library):
        tmpl = library.get_template("revocable_living_trust")
        assert "TRUSTEE" in tmpl

    def test_revocable_trust_has_notarization(self, library):
        tmpl = library.get_template("revocable_living_trust")
        assert "Notary" in tmpl or "NOTARY" in tmpl or "notary" in tmpl.lower()

    def test_llc_single_member_has_articles(self, library):
        tmpl = library.get_template("llc_operating_agreement_single")
        assert "ARTICLE" in tmpl

    def test_llc_multi_member_has_voting(self, library):
        tmpl = library.get_template("llc_operating_agreement_multi")
        assert "VOTING" in tmpl or "voting" in tmpl.lower()

    def test_residential_lease_has_rent_section(self, library):
        tmpl = library.get_template("residential_lease")
        assert "RENT" in tmpl

    def test_residential_lease_has_security_deposit(self, library):
        tmpl = library.get_template("residential_lease")
        assert "SECURITY DEPOSIT" in tmpl

    def test_nda_has_confidential_info_definition(self, library):
        tmpl = library.get_template("nda")
        assert "Confidential Information" in tmpl

    def test_employment_agreement_has_compensation(self, library):
        tmpl = library.get_template("employment_agreement")
        assert "COMPENSATION" in tmpl

    def test_demand_letter_payment_has_amount(self, library):
        tmpl = library.get_template("demand_letter_payment")
        assert "[AMOUNT]" in tmpl

    def test_last_will_simple_has_witness_block(self, library):
        tmpl = library.get_template("last_will_simple")
        assert "WITNESSES" in tmpl or "witness" in tmpl.lower()

    def test_invoice_template_has_total_due(self, library):
        tmpl = library.get_template("invoice_template")
        assert "TOTAL" in tmpl

    def test_privacy_policy_has_data_rights(self, library):
        tmpl = library.get_template("privacy_policy")
        assert "RIGHT" in tmpl or "rights" in tmpl.lower()

    def test_invalid_template_key_raises_key_error(self, library):
        with pytest.raises(KeyError):
            library.get_template("nonexistent_document_type_xyz")

    def test_all_templates_have_bracket_fields(self, library):
        for key in library.list_templates():
            tmpl = library.get_template(key)
            assert "[" in tmpl, f"Template '{key}' has no [BRACKET] fields"

    def test_all_templates_are_nonempty(self, library):
        for key in library.list_templates():
            tmpl = library.get_template(key)
            assert len(tmpl.strip()) > 50, f"Template '{key}' appears too short"

    def test_cease_and_desist_ip_mentions_trademark(self, library):
        tmpl = library.get_template("cease_and_desist_ip")
        assert "Trademark" in tmpl or "trademark" in tmpl.lower()

    def test_fdcpa_letter_cites_statute(self, library):
        tmpl = library.get_template("fdcpa_debt_validation")
        assert "1692" in tmpl


# ======================================================================
# FINANCIAL REPORT TEMPLATES TESTS
# ======================================================================

class TestFinancialReportTemplates:
    def test_personal_financial_statement_not_empty(self, financial):
        result = financial.personal_financial_statement({"name": "Test User"})
        assert len(result) > 100

    def test_personal_financial_statement_has_net_worth(self, financial):
        result = financial.personal_financial_statement({"name": "Test"})
        assert "NET WORTH" in result

    def test_personal_financial_statement_has_assets(self, financial):
        result = financial.personal_financial_statement({})
        assert "ASSETS" in result

    def test_personal_financial_statement_has_liabilities(self, financial):
        result = financial.personal_financial_statement({})
        assert "LIABILITIES" in result

    def test_business_financial_summary_has_ebitda(self, financial):
        result = financial.business_financial_summary({"company": "Test Inc", "revenue": 1000000})
        assert "EBITDA" in result

    def test_net_worth_statement_has_liquid_assets(self, financial):
        result = financial.net_worth_statement({"name": "Test"})
        assert "LIQUID" in result or "liquid" in result.lower()

    def test_cash_flow_analysis_has_income_section(self, financial):
        result = financial.cash_flow_analysis({"name": "Test", "period": "Jan 2025"})
        assert "INCOME" in result

    def test_cash_flow_analysis_has_expenses(self, financial):
        result = financial.cash_flow_analysis({})
        assert "EXPENSES" in result

    def test_loan_proposal_has_loan_amount(self, financial):
        result = financial.loan_proposal(
            {"name": "Test Business"},
            {"amount": 100000, "purpose": "equipment"},
        )
        assert "100,000" in result or "LOAN" in result

    def test_investor_pitch_has_projections(self, financial):
        result = financial.investor_pitch_financial_model({
            "name": "StartupX",
            "revenue": [100000, 500000, 1000000],
        })
        assert "PROJECTIONS" in result or "Year" in result

    def test_tax_planning_has_taxable_income(self, financial):
        result = financial.tax_planning_summary({"name": "Test", "w2_income": 75000})
        assert "TAXABLE INCOME" in result or "taxable" in result.lower()

    def test_currency_formatting_with_real_values(self, financial):
        result = financial.personal_financial_statement({
            "cash": 10000,
            "savings": 25000,
        })
        assert "10,000" in result or "$10,000" in result

    def test_box_drawing_characters_present(self, financial):
        result = financial.personal_financial_statement({})
        assert "╔" in result or "║" in result or "╚" in result


# ======================================================================
# CREDIT REPORT ANALYZER TESTS
# ======================================================================

class TestCreditReportAnalyzer:
    def test_dashboard_not_empty(self, credit_analyzer, sample_credit_profile):
        result = credit_analyzer.generate_credit_dashboard(sample_credit_profile)
        assert len(result) > 100

    def test_dashboard_shows_score(self, credit_analyzer, sample_credit_profile):
        result = credit_analyzer.generate_credit_dashboard(sample_credit_profile)
        assert "742" in result

    def test_dashboard_has_credit_intelligence_header(self, credit_analyzer):
        result = credit_analyzer.generate_credit_dashboard({"score": 700})
        assert "CREDIT" in result

    def test_dashboard_has_score_factors(self, credit_analyzer, sample_credit_profile):
        result = credit_analyzer.generate_credit_dashboard(sample_credit_profile)
        assert "Payment History" in result

    def test_dashboard_has_bar_characters(self, credit_analyzer, sample_credit_profile):
        result = credit_analyzer.generate_credit_dashboard(sample_credit_profile)
        assert "█" in result or "░" in result

    def test_dashboard_shows_utilization(self, credit_analyzer, sample_credit_profile):
        result = credit_analyzer.generate_credit_dashboard(sample_credit_profile)
        assert "Credit Usage" in result or "Utilization" in result

    def test_dashboard_has_recommended_actions(self, credit_analyzer):
        result = credit_analyzer.generate_credit_dashboard({"score": 600, "derogatory_marks": 2})
        assert "RECOMMENDED" in result or "recommended" in result.lower()

    def test_dispute_package_returns_dispute_package(self, credit_analyzer, sample_dispute_accounts):
        result = credit_analyzer.dispute_package_generator(sample_dispute_accounts)
        assert isinstance(result, DisputePackage)

    def test_dispute_package_has_cover_letter(self, credit_analyzer, sample_dispute_accounts):
        result = credit_analyzer.dispute_package_generator(sample_dispute_accounts)
        assert len(result.cover_letter) > 100

    def test_dispute_package_has_letters_for_all_bureaus(self, credit_analyzer, sample_dispute_accounts):
        result = credit_analyzer.dispute_package_generator(sample_dispute_accounts)
        assert len(result.dispute_letters) >= 2

    def test_dispute_package_mentions_fcra(self, credit_analyzer, sample_dispute_accounts):
        result = credit_analyzer.dispute_package_generator(sample_dispute_accounts)
        assert "FCRA" in result.cover_letter or "Fair Credit" in result.cover_letter

    def test_dispute_letter_mentions_certified_mail(self, credit_analyzer, sample_dispute_accounts):
        pkg = credit_analyzer.dispute_package_generator(sample_dispute_accounts)
        assert any("CERTIFIED MAIL" in letter for letter in pkg.dispute_letters)

    def test_tracking_instructions_lists_bureaus(self, credit_analyzer, sample_dispute_accounts):
        pkg = credit_analyzer.dispute_package_generator(sample_dispute_accounts)
        assert "Equifax" in pkg.tracking_instructions

    def test_follow_up_timeline_has_30_day_note(self, credit_analyzer, sample_dispute_accounts):
        pkg = credit_analyzer.dispute_package_generator(sample_dispute_accounts)
        assert "30" in pkg.follow_up_timeline

    def test_full_package_property_combines_all(self, credit_analyzer, sample_dispute_accounts):
        pkg = credit_analyzer.dispute_package_generator(sample_dispute_accounts)
        full = pkg.full_package
        assert len(full) > 500

    def test_make_bar_returns_correct_width(self, credit_analyzer):
        bar = credit_analyzer._make_bar(50, 12)
        assert len(bar) == 12

    def test_make_bar_full(self, credit_analyzer):
        bar = credit_analyzer._make_bar(100, 10)
        assert "░" not in bar

    def test_make_bar_empty(self, credit_analyzer):
        bar = credit_analyzer._make_bar(0, 10)
        assert "█" not in bar


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
