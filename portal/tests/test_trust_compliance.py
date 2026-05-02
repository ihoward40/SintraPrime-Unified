
import pytest
from portal.services.trust_compliance_service import TrustComplianceService

@pytest.fixture
def trust_compliance_service():
    # Initialize with empty policies for testing purposes
    service = TrustComplianceService()
    service.risk_tags = []
    service.safety_gates = []
    service.forbidden_phrases = []
    return service

def test_analyze_document_no_risks(trust_compliance_service):
    document_text = "This is a clean document with no risks."
    document_type = "report"
    result = trust_compliance_service.analyze_document(document_text, document_type)
    assert result["compliance_score"] == 1.0
    assert len(result["risk_tags"]) == 0
    assert len(result["safety_gates"]) == 0
    assert len(result["recommendations"]) == 0

def test_analyze_document_with_risk_tags(trust_compliance_service):
    trust_compliance_service.risk_tags = ["risk-tag-1", "risk-tag-2"]
    document_text = "This document contains risk-tag-1 and risk-tag-2."
    document_type = "report"
    result = trust_compliance_service.analyze_document(document_text, document_type)
    assert result["compliance_score"] == 1.0 - (2 * 0.1) # 0.8
    assert "risk-tag-1" in result["risk_tags"]
    assert "risk-tag-2" in result["risk_tags"]
    assert "Review document for compliance issues." not in result["recommendations"]
    assert "Address triggered risk tags: risk-tag-1, risk-tag-2." in result["recommendations"]

def test_analyze_document_with_forbidden_phrases(trust_compliance_service):
    trust_compliance_service.forbidden_phrases = ["forbidden phrase 1", "forbidden phrase 2"]
    document_text = "This document has forbidden phrase 1 and forbidden phrase 2."
    document_type = "report"
    result = trust_compliance_service.analyze_document(document_text, document_type)
    assert result["compliance_score"] == 1.0 - (2 * 0.15) # 0.7
    assert "Remove or rephrase forbidden phrases: forbidden phrase 1, forbidden phrase 2." in result["recommendations"]

def test_analyze_document_with_safety_gates(trust_compliance_service):
    trust_compliance_service.safety_gates = ["safety-gate-1", "safety-gate-2"]
    document_text = "This document triggers safety-gate-1 and safety-gate-2."
    document_type = "report"
    result = trust_compliance_service.analyze_document(document_text, document_type)
    assert "safety-gate-1" in result["safety_gates"]
    assert "safety-gate-2" in result["safety_gates"]

def test_get_policies(trust_compliance_service):
    trust_compliance_service.risk_tags = ["risk-tag-A"]
    trust_compliance_service.safety_gates = ["safety-gate-B"]
    trust_compliance_service.forbidden_phrases = ["forbidden phrase C"]
    policies = trust_compliance_service.get_policies()
    assert policies["risk_tags"] == ["risk-tag-A"]
    assert policies["safety_gates"] == ["safety-gate-B"]
    assert policies["forbidden_phrases"] == ["forbidden phrase C"]

def test_rewrite_document_no_changes(trust_compliance_service):
    document_text = "Original text."
    risk_tags = []
    result = trust_compliance_service.rewrite_document(document_text, risk_tags)
    assert result["rewritten_text"] == "Original text."
    assert len(result["changes_made"]) == 0

def test_rewrite_document_with_changes(trust_compliance_service):
    document_text = "Original text with risk-tag-1."
    risk_tags = ["risk-tag-1"]
    result = trust_compliance_service.rewrite_document(document_text, risk_tags)
    assert result["rewritten_text"] == "Original text with [REDACTED]."
    assert "Replaced 'risk-tag-1' with '[REDACTED]'" in result["changes_made"]

def test_compliance_score_clamping(trust_compliance_service):
    document_text = "risk-tag-1 risk-tag-2 risk-tag-3 risk-tag-4 risk-tag-5 risk-tag-6 risk-tag-7 risk-tag-8 risk-tag-9 risk-tag-10 forbidden-phrase-1 forbidden-phrase-2 forbidden-phrase-3 forbidden-phrase-4 forbidden-phrase-5 forbidden-phrase-6 forbidden-phrase-7 forbidden-phrase-8 forbidden-phrase-9 forbidden-phrase-10"
    document_type = "report"
    trust_compliance_service.risk_tags = [f"risk-tag-{i}" for i in range(1, 11)]
    trust_compliance_service.forbidden_phrases = [f"forbidden-phrase-{i}" for i in range(1, 11)]
    result = trust_compliance_service.analyze_document(document_text, document_type)
    assert result["compliance_score"] == 0.0 # Should be clamped to 0.0
