from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

HOWARD_POLICY_PACK: Dict[str, Any] = {
    "policy_pack": "HOWARD_RECOVERY_POLICY_PACK_v1",
    "mode": "evidence_intake_only",
    "external_action": "locked",
    "approval_required_before": [
        "send",
        "file",
        "contact",
        "submit",
        "delete",
        "modify",
        "email",
        "call",
        "mail",
        "serve",
        "post"
    ],
    "evidence_rule": "Every claim must be tied to email, screenshot, PDF, credit report, statement, contract, notice, court record, or payment receipt.",
    "active_cases": [
        "PayPal Negative Balance / Account Block",
        "Halsted / LVNV / Bank of Missouri / Milestone",
        "UACC / Vroom",
        "AFF / FinWise",
        "Self Financial / Lead Bank",
        "Verizon",
        "Chase / Wells Fargo / EWS",
        "Unknown Collections",
        "SAP / FMCSA",
        "Expungement",
        "Funding / Grants",
        "TikTok Shop"
    ],
    "approved_public_theories": [
        "FCRA inaccurate reporting",
        "FCRA failure to investigate",
        "FDCPA validation failure",
        "FDCPA misleading collection",
        "chain-of-title defects",
        "assignment proof defects",
        "itemized ledger defects",
        "failure to mark disputed",
        "incorrect balance",
        "improper account restriction",
        "defective adverse-action notice",
        "breach of contract",
        "unfair or deceptive acts or practices",
        "consumer reporting dispute preservation",
        "evidence preservation",
        "administrative notice and cure"
    ],
    "prohibited_outputs": [
        "unsupported legal conclusions",
        "automatic lien claims",
        "self-executing default claims",
        "accepted-for-value payment claims",
        "birth certificate or CUSIP monetization claims",
        "claims that private or indigenous status exempts public law",
        "company contact without approval",
        "guaranteed lawsuit outcomes",
        "threats not supported by evidence"
    ]
}

class AnalyzeRequest(BaseModel):
    document_text: str
    document_type: str

class AnalyzeResponse(BaseModel):
    risk_tags: List[str]
    safety_gates: List[str]
    compliance_score: float
    recommendations: List[str]

class RewriteRequest(BaseModel):
    document_text: str
    risk_tags: List[str]

class RewriteResponse(BaseModel):
    rewritten_text: str
    changes_made: List[str]

def detect_risks(text: str) -> List[str]:
    lowered = text.lower()
    risks: List[str] = []

    prohibited_terms = {
        "accepted for value": "A4V / accepted-for-value language detected",
        "birth certificate": "birth certificate monetization risk",
        "cusip": "CUSIP monetization risk",
        "self-executing": "self-executing default/lien risk",
        "commercial lien": "commercial lien escalation risk",
        "silence equals agreement": "tacit consent risk",
        "automatic default": "automatic default risk",
        "exempt from": "public-law exemption claim risk",
        "not subject to": "public-law exemption claim risk",
        "guaranteed": "guarantee language risk",
        "steal": "unsupported accusation risk",
        "fraud": "fraud allegation requires evidence support"
    }

    for term, tag in prohibited_terms.items():
        if term in lowered and tag not in risks:
            risks.append(tag)

    external_actions = ["send", "file", "submit", "contact", "serve", "mail", "email", "call"]
    if any(action in lowered for action in external_actions):
        risks.append("external-action approval gate required")

    if "lawsuit" in lowered or "sue" in lowered:
        risks.append("litigation-prep gate required")

    if "credit report" in lowered or "furnisher" in lowered or "consumer report" in lowered:
        risks.append("FCRA evidence-support gate required")

    if "collector" in lowered or "collection" in lowered or "debt collector" in lowered:
        risks.append("FDCPA validation-support gate required")

    if "expungement" in lowered or "criminal" in lowered or "charges" in lowered:
        risks.append("court-record verification gate required")

    if not risks:
        risks.append("low-risk evidence-intake document")

    return risks

def build_safety_gates(risks: List[str]) -> List[str]:
    gates = [
        "NO_EXTERNAL_ACTION_WITHOUT_APPROVAL",
        "EVIDENCE_REQUIRED_FOR_EVERY_CLAIM",
        "NO_UNSUPPORTED_CONCLUSIONS"
    ]

    if any("litigation" in risk.lower() for risk in risks):
        gates.append("ATTORNEY_REVIEW_RECOMMENDED_BEFORE_FILING")

    if any("FCRA" in risk for risk in risks):
        gates.append("CREDIT_REPORT_AND_DISPUTE_RESULTS_REQUIRED")

    if any("FDCPA" in risk for risk in risks):
        gates.append("VALIDATION_NOTICE_AND_COLLECTION_RECORD_REQUIRED")

    if any("court-record" in risk for risk in risks):
        gates.append("DOCKET_AND_DISPOSITION_REQUIRED")

    if any("exemption" in risk.lower() or "a4v" in risk.lower() or "cusip" in risk.lower() for risk in risks):
        gates.append("REMOVE_HIGH_RISK_THEORY_FROM_PUBLIC_DOCUMENT")

    return gates

def compliance_score(risks: List[str], text: str) -> float:
    score = 1.0
    lowered = text.lower()

    high_risk_markers = [
        "accepted for value",
        "birth certificate",
        "cusip",
        "self-executing",
        "silence equals agreement",
        "exempt from",
        "not subject to",
        "guaranteed"
    ]

    for marker in high_risk_markers:
        if marker in lowered:
            score -= 0.15

    if "evidence" in lowered or "screenshot" in lowered or "credit report" in lowered or "pdf" in lowered:
        score += 0.05

    if "approval required" in lowered or "external action locked" in lowered:
        score += 0.05

    return max(0.0, min(1.0, round(score, 2)))

def build_recommendations(risks: List[str], text: str) -> List[str]:
    recommendations = [
        "Maintain evidence-intake-only status until approval is given.",
        "Attach each factual claim to a source document before drafting demands.",
        "Use court-safe language: accuracy, completeness, accounting, reporting, collection authority, and procedural fairness.",
        "Separate private strategy notes from public-facing filings."
    ]

    if any("external-action" in risk.lower() for risk in risks):
        recommendations.append("Do not send, file, contact, submit, serve, mail, email, or call without explicit approval.")

    if any("FCRA" in risk for risk in risks):
        recommendations.append("Collect the credit report, bureau dispute, reinvestigation result, furnisher response, and disputed-status screenshot.")

    if any("FDCPA" in risk for risk in risks):
        recommendations.append("Collect the collection notice, validation request, collector response, payment history, and chain-of-title documents.")

    if any("court-record" in risk for risk in risks):
        recommendations.append("Collect docket number, charge, disposition, sentencing record, fines/restitution status, and eligibility notes.")

    if any("unsupported" in risk.lower() or "fraud" in risk.lower() for risk in risks):
        recommendations.append("Replace accusation language with documented discrepancy language unless proof is attached.")

    return recommendations

@router.post("/api/trust-compliance/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    risks = detect_risks(request.document_text)
    gates = build_safety_gates(risks)
    score = compliance_score(risks, request.document_text)
    recs = build_recommendations(risks, request.document_text)

    return AnalyzeResponse(
        risk_tags=risks,
        safety_gates=gates,
        compliance_score=score,
        recommendations=recs
    )

@router.get("/api/trust-compliance/policies")
async def get_policies():
    return HOWARD_POLICY_PACK

@router.post("/api/trust-compliance/rewrite", response_model=RewriteResponse)
async def rewrite(request: RewriteRequest):
    rewritten = request.document_text

    replacements = {
        "steal": "dispute the accounting and documentation supporting",
        "fraud": "potentially inaccurate, incomplete, or misleading conduct requiring investigation",
        "guaranteed": "requested",
        "self-executing": "subject to documented review and lawful approval",
        "accepted for value": "disputed and preserved for evidence review",
        "not subject to": "request clarification of the applicable authority and procedure for",
        "exempt from": "request clarification of the applicable authority and procedure for"
    }

    changes = []

    for old, new in replacements.items():
        if old in rewritten.lower():
            rewritten = rewritten.replace(old, new)
            rewritten = rewritten.replace(old.title(), new)
            rewritten = rewritten.replace(old.upper(), new.upper())
            changes.append(f"Replaced high-risk phrase: {old}")

    if not changes:
        changes.append("No high-risk phrase replacements required.")

    rewritten += "\n\nCourt-safe evidence statement: I dispute the accuracy, completeness, accounting, reporting, collection authority, and procedural fairness of this matter. Any further action must be supported by source documents and approved before external contact, filing, submission, or service."

    changes.append("Added court-safe evidence statement.")

    return RewriteResponse(
        rewritten_text=rewritten,
        changes_made=changes
    )

@router.get("/api/trust-compliance/health")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "policy_pack": "HOWARD_RECOVERY_POLICY_PACK_v1",
        "mode": "evidence_intake_only",
        "external_action": "locked"
    }
