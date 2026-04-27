"""
Unit tests for lead router and routing algorithm.
"""

import pytest
from datetime import datetime
from models.lead import IntakeData, AgentType, Lead, LeadStatus
from utils.matching import (
    calculate_legal_score,
    calculate_financial_score,
    calculate_urgency_score,
    calculate_qualification_score,
    route_lead,
)


class TestLegalScoring:
    """Tests for legal score calculation."""
    
    def test_legal_focused_lead(self):
        """Test lead with strong legal focus gets high legal score."""
        intake = IntakeData(
            name="John Smith",
            email="john@example.com",
            phone="+1-555-1234",
            legal_situation="I need help setting up a trust and estate plan for my family business",
            financial_snapshot="I have significant assets to protect",
            goals="I want to establish proper legal structures for wealth succession",
            company_name="Smith Industries",
        )
        
        score = calculate_legal_score(intake)
        assert score > 60, "Legal-focused intake should score >60"
        print(f"Legal score: {score}")
    
    def test_non_legal_lead(self):
        """Test lead with no legal focus gets low legal score."""
        intake = IntakeData(
            name="Jane Doe",
            email="jane@example.com",
            phone="+1-555-5678",
            legal_situation="Just general questions",
            financial_snapshot="I want to invest in stocks",
            goals="Grow my retirement savings",
        )
        
        score = calculate_legal_score(intake)
        assert score < 40, "Non-legal lead should score <40"
        print(f"Legal score: {score}")


class TestFinancialScoring:
    """Tests for financial score calculation."""
    
    def test_financial_focused_lead(self):
        """Test lead with strong financial focus gets high financial score."""
        intake = IntakeData(
            name="Bob Johnson",
            email="bob@example.com",
            phone="+1-555-2345",
            legal_situation="I have some general questions",
            financial_snapshot="I have significant credit card debt and want to consolidate loans. "
                             "I'm concerned about my tax situation and want asset allocation advice.",
            goals="Improve my credit score and restructure my debt",
        )
        
        score = calculate_financial_score(intake)
        assert score > 60, "Financial-focused intake should score >60"
        print(f"Financial score: {score}")
    
    def test_non_financial_lead(self):
        """Test lead with no financial focus gets low financial score."""
        intake = IntakeData(
            name="Alice Brown",
            email="alice@example.com",
            phone="+1-555-6789",
            legal_situation="I need legal advice on business formation",
            financial_snapshot="General questions",
            goals="Get proper legal documents in place",
        )
        
        score = calculate_financial_score(intake)
        assert score < 40, "Non-financial lead should score <40"
        print(f"Financial score: {score}")


class TestUrgencyScoring:
    """Tests for urgency score calculation."""
    
    def test_urgent_lead(self):
        """Test lead with urgent signals gets high urgency score."""
        intake = IntakeData(
            name="Charlie Davis",
            email="charlie@example.com",
            phone="+1-555-3456",
            legal_situation="I am facing imminent foreclosure on my home",
            financial_snapshot="I am defaulting on multiple credit cards",
            goals="Prevent foreclosure and handle creditor collection",
            timeline="immediate",
        )
        
        score = calculate_urgency_score(intake)
        assert score > 50, "Urgent lead should score >50"
        print(f"Urgency score: {score}")
    
    def test_non_urgent_lead(self):
        """Test lead with no urgency signals gets low urgency score."""
        intake = IntakeData(
            name="Eve Wilson",
            email="eve@example.com",
            phone="+1-555-7890",
            legal_situation="I want to plan for the future",
            financial_snapshot="I'm doing well financially",
            goals="Plan for long-term growth",
            timeline="long-term",
        )
        
        score = calculate_urgency_score(intake)
        assert score < 40, "Non-urgent lead should score <40"
        print(f"Urgency score: {score}")


class TestQualificationScore:
    """Tests for overall qualification scoring."""
    
    def test_qualified_lead(self):
        """Test well-qualified lead gets reasonable qualification score."""
        legal = 75.0
        financial = 65.0
        urgency = 50.0
        
        score = calculate_qualification_score(legal, financial, urgency)
        assert 50 < score < 100, "Well-qualified lead should have mid-to-high qualification score"
        print(f"Qualification score: {score}")
    
    def test_low_quality_lead(self):
        """Test low-quality lead gets low qualification score."""
        legal = 20.0
        financial = 15.0
        urgency = 10.0
        
        score = calculate_qualification_score(legal, financial, urgency)
        assert score < 30, "Low-quality lead should have low qualification score"
        print(f"Qualification score: {score}")


class TestLeadRouting:
    """Tests for lead routing algorithm."""
    
    def test_legal_specialist_routing(self):
        """Test that legal-focused leads route to legal specialist."""
        intake = IntakeData(
            name="John Attorney",
            email="john.attorney@example.com",
            phone="+1-555-1111",
            legal_situation="I need to create a comprehensive estate plan with trusts and "
                          "power of attorney. I also have business succession concerns.",
            financial_snapshot="I have some investments",
            goals="Establish proper legal structures and protect my family",
            company_name="Johnson LLC",
        )
        
        result = route_lead(intake)
        assert result.assigned_agent == AgentType.LEGAL_SPECIALIST
        assert result.confidence >= 50
        print(f"✓ Legal specialist routing: confidence {result.confidence}")
    
    def test_financial_specialist_routing(self):
        """Test that financial-focused leads route to financial specialist."""
        intake = IntakeData(
            name="Frank Finance",
            email="frank.finance@example.com",
            phone="+1-555-2222",
            legal_situation="General questions",
            financial_snapshot="I have high credit card debt ($150k), need tax planning help, "
                             "and want to restructure my business income. Also concerned about "
                             "capital gains and investment portfolio allocation.",
            goals="Improve financial situation and reduce tax burden",
        )
        
        result = route_lead(intake)
        assert result.assigned_agent == AgentType.FINANCIAL_SPECIALIST
        assert result.confidence >= 50
        print(f"✓ Financial specialist routing: confidence {result.confidence}")
    
    def test_combined_specialist_routing(self):
        """Test that balanced leads route to combined specialist."""
        intake = IntakeData(
            name="Nova Combined",
            email="nova.combined@example.com",
            phone="+1-555-3333",
            legal_situation="I need to set up an LLC for my business and handle contract issues. "
                          "I also need asset protection strategies.",
            financial_snapshot="I want to optimize my business income and plan for retirement. "
                             "I have some tax deductions to maximize.",
            goals="Set up proper business structure with financial optimization",
            company_name="Nova Enterprises",
            industry="Technology",
        )
        
        result = route_lead(intake)
        assert result.assigned_agent == AgentType.COMBINED_SPECIALIST
        assert result.confidence >= 50
        print(f"✓ Combined specialist routing: confidence {result.confidence}")
    
    def test_general_inquiry_routing(self):
        """Test that unclear leads route to general inquiry."""
        intake = IntakeData(
            name="Generic Inquiry",
            email="generic@example.com",
            phone="+1-555-4444",
            legal_situation="I have some general questions",
            financial_snapshot="Just exploring options",
            goals="See what services are available",
        )
        
        result = route_lead(intake)
        assert result.assigned_agent == AgentType.GENERAL_INQUIRY
        print(f"✓ General inquiry routing: confidence {result.confidence}")
    
    def test_confidence_score_range(self):
        """Test that confidence scores are within valid range."""
        intake = IntakeData(
            name="Test Lead",
            email="test@example.com",
            phone="+1-555-5555",
            legal_situation="This is a test legal situation",
            financial_snapshot="This is a test financial snapshot",
            goals="Test goals",
        )
        
        result = route_lead(intake)
        assert 0 <= result.confidence <= 100, "Confidence should be 0-100"
        assert 0 <= result.legal_score <= 100, "Legal score should be 0-100"
        assert 0 <= result.financial_score <= 100, "Financial score should be 0-100"
        assert 0 <= result.urgency_score <= 100, "Urgency score should be 0-100"
        print(f"✓ Score ranges valid: legal {result.legal_score}, "
              f"financial {result.financial_score}, urgency {result.urgency_score}")


class TestLeadModel:
    """Tests for Lead data model."""
    
    def test_lead_creation(self):
        """Test creating a lead record."""
        lead = Lead(
            lead_id="test-uuid-123",
            name="Test User",
            email="test@example.com",
            phone="+1-555-1234",
            legal_situation="Test legal situation",
            financial_snapshot="Test financial situation",
            goals="Test goals",
            assigned_agent=AgentType.LEGAL_SPECIALIST,
            legal_score=75.0,
            financial_score=40.0,
            urgency_score=30.0,
            qualification_score=50.0,
        )
        
        assert lead.lead_id == "test-uuid-123"
        assert lead.status == LeadStatus.NEW
        assert lead.name == "Test User"
        print(f"✓ Lead created: {lead.lead_id}")
    
    def test_lead_with_optional_fields(self):
        """Test lead creation with optional fields."""
        lead = Lead(
            lead_id="test-uuid-456",
            name="Business User",
            email="business@example.com",
            phone="+1-555-5678",
            legal_situation="Business legal needs",
            financial_snapshot="Business financial needs",
            goals="Business growth",
            company_name="ABC Corporation",
            industry="Technology",
            assigned_agent=AgentType.COMBINED_SPECIALIST,
            legal_score=60.0,
            financial_score=70.0,
            urgency_score=40.0,
            qualification_score=65.0,
        )
        
        assert lead.company_name == "ABC Corporation"
        assert lead.industry == "Technology"
        print(f"✓ Lead with optional fields created: {lead.company_name}")


class TestIntakeDataValidation:
    """Tests for intake data validation."""
    
    def test_valid_intake(self):
        """Test valid intake data passes validation."""
        intake = IntakeData(
            name="John Doe",
            email="john@example.com",
            phone="+1-555-1234",
            legal_situation="I need legal help with my business",
            financial_snapshot="I want to plan my finances",
            goals="Achieve my financial and legal goals",
        )
        
        assert intake.name == "John Doe"
        assert intake.email == "john@example.com"
        print(f"✓ Valid intake accepted: {intake.name}")
    
    def test_invalid_email(self):
        """Test that invalid email is rejected."""
        with pytest.raises(ValueError):
            IntakeData(
                name="John Doe",
                email="not-an-email",
                phone="+1-555-1234",
                legal_situation="Test",
                financial_snapshot="Test",
                goals="Test",
            )
        print("✓ Invalid email rejected")
    
    def test_invalid_phone(self):
        """Test that invalid phone is rejected."""
        with pytest.raises(ValueError):
            IntakeData(
                name="John Doe",
                email="john@example.com",
                phone="123",  # Too short
                legal_situation="Test",
                financial_snapshot="Test",
                goals="Test",
            )
        print("✓ Invalid phone rejected")
    
    def test_missing_required_field(self):
        """Test that missing required field raises error."""
        with pytest.raises(ValueError):
            IntakeData(
                name="John Doe",
                email="john@example.com",
                phone="+1-555-1234",
                legal_situation="Test legal situation to be long enough",
                goals="Test goals to be long enough",
                # Missing financial_snapshot
            )
        print("✓ Missing required field rejected")


def run_tests():
    """Run all tests and report results."""
    test_count = 0
    passed_count = 0
    failed_count = 0
    
    # Define all test classes
    test_classes = [
        TestLegalScoring,
        TestFinancialScoring,
        TestUrgencyScoring,
        TestQualificationScore,
        TestLeadRouting,
        TestLeadModel,
        TestIntakeDataValidation,
    ]
    
    print("\n" + "="*70)
    print("RUNNING LEAD ROUTER TESTS")
    print("="*70 + "\n")
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        print("-" * 70)
        
        test_instance = test_class()
        test_methods = [m for m in dir(test_instance) if m.startswith("test_")]
        
        for method_name in test_methods:
            test_count += 1
            try:
                method = getattr(test_instance, method_name)
                method()
                passed_count += 1
                print(f"  ✓ {method_name}")
            except AssertionError as e:
                failed_count += 1
                print(f"  ✗ {method_name}: {str(e)}")
            except Exception as e:
                failed_count += 1
                print(f"  ✗ {method_name}: {str(e)}")
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Total: {test_count}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {failed_count}")
    print(f"Success Rate: {(passed_count/test_count)*100:.1f}%")
    print("="*70 + "\n")
    
    return passed_count, failed_count, test_count


if __name__ == "__main__":
    passed, failed, total = run_tests()
    exit(0 if failed == 0 else 1)
