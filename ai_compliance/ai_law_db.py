"""
ai_law_db.py — Comprehensive AI Regulation Database for SintraPrime-Unified
Covers 2025-2026 AI laws and frameworks across EU, US federal, and US state levels.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import List, Optional, Dict


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Jurisdiction(str, Enum):
    EU = "European Union"
    US_FEDERAL = "United States Federal"
    US_CA = "California"
    US_TX = "Texas"
    US_CO = "Colorado"
    US_NY = "New York"
    US_IL = "Illinois"
    US_VA = "Virginia"
    US_WA = "Washington"
    US_FL = "Florida"
    INTERNATIONAL = "International"
    PROFESSIONAL = "Professional / Bar Association"


class RiskTier(str, Enum):
    UNACCEPTABLE = "unacceptable"       # Prohibited outright
    HIGH = "high"                       # Requires conformity assessment
    LIMITED = "limited"                 # Transparency obligations
    MINIMAL = "minimal"                 # No specific obligations


class ComplianceArea(str, Enum):
    TRANSPARENCY = "transparency"
    EXPLAINABILITY = "explainability"
    BIAS_FAIRNESS = "bias_and_fairness"
    DATA_MINIMIZATION = "data_minimization"
    HUMAN_OVERSIGHT = "human_oversight"
    SECURITY = "security"
    DOCUMENTATION = "documentation"
    ACCOUNTABILITY = "accountability"
    CONSENT = "consent"
    UPL = "unauthorized_practice_of_law"
    EMPLOYMENT = "employment"
    CONSUMER_PROTECTION = "consumer_protection"
    HEALTHCARE = "healthcare"
    FINANCIAL = "financial"


# ---------------------------------------------------------------------------
# Core Dataclass
# ---------------------------------------------------------------------------

@dataclass
class AILaw:
    """
    Represents a single AI regulation, framework, or guideline.
    """
    law_id: str
    jurisdiction: Jurisdiction
    law_name: str
    short_name: str
    effective_date: date
    last_updated: date
    status: str                            # active | proposed | repealed
    requirements: List[str]
    penalties: List[str]
    applies_to: List[str]                  # Categories of AI systems / actors
    compliance_areas: List[ComplianceArea]
    risk_tiers: List[RiskTier]
    official_url: str
    summary: str
    extraterritorial: bool = False         # Does it apply to non-local actors?
    legal_profession_specific: bool = False

    def matches_area(self, area: ComplianceArea) -> bool:
        return area in self.compliance_areas

    def is_active(self) -> bool:
        return self.status == "active"

    def covers_risk_tier(self, tier: RiskTier) -> bool:
        return tier in self.risk_tiers


# ---------------------------------------------------------------------------
# EU AI Act
# ---------------------------------------------------------------------------

EU_AI_ACT = AILaw(
    law_id="EU-AI-ACT-2024",
    jurisdiction=Jurisdiction.EU,
    law_name="Regulation (EU) 2024/1689 — Artificial Intelligence Act",
    short_name="EU AI Act",
    effective_date=date(2024, 8, 1),
    last_updated=date(2026, 2, 1),
    status="active",
    requirements=[
        "Classify AI systems into risk tiers: unacceptable, high, limited, minimal",
        "High-risk AI systems require conformity assessment before market placement",
        "Technical documentation and record-keeping for high-risk AI",
        "Transparency obligations: users must know they interact with AI",
        "Human oversight mechanisms for high-risk systems",
        "Accuracy, robustness, and cybersecurity requirements",
        "Fundamental rights impact assessment for high-risk AI",
        "Post-market monitoring and incident reporting",
        "AI literacy obligations for providers and deployers",
        "Registration in EU database for high-risk AI systems",
        "Prohibited AI practices: social scoring, real-time biometric surveillance, subliminal manipulation",
        "General-purpose AI (GPAI) model transparency and copyright compliance",
        "Systemic risk assessment for GPAI models above 10^25 FLOPs",
    ],
    penalties=[
        "Up to €35 million or 7% of global annual turnover for prohibited AI violations",
        "Up to €15 million or 3% of global annual turnover for non-compliance with obligations",
        "Up to €7.5 million or 1.5% for providing incorrect information",
        "SME/startup caps at lower absolute amounts",
    ],
    applies_to=[
        "AI system providers placing systems on EU market",
        "Deployers of AI systems established in EU",
        "Providers and deployers outside EU when output affects EU persons",
        "Importers and distributors of AI systems",
        "Product manufacturers incorporating AI",
    ],
    compliance_areas=[
        ComplianceArea.TRANSPARENCY,
        ComplianceArea.EXPLAINABILITY,
        ComplianceArea.HUMAN_OVERSIGHT,
        ComplianceArea.DOCUMENTATION,
        ComplianceArea.ACCOUNTABILITY,
        ComplianceArea.SECURITY,
        ComplianceArea.BIAS_FAIRNESS,
    ],
    risk_tiers=[RiskTier.UNACCEPTABLE, RiskTier.HIGH, RiskTier.LIMITED, RiskTier.MINIMAL],
    official_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689",
    summary="The EU AI Act is the world's first comprehensive legal framework on AI, establishing a risk-based regulatory approach.",
    extraterritorial=True,
)

# ---------------------------------------------------------------------------
# NIST AI RMF
# ---------------------------------------------------------------------------

NIST_AI_RMF = AILaw(
    law_id="NIST-AI-RMF-1.0",
    jurisdiction=Jurisdiction.US_FEDERAL,
    law_name="NIST AI Risk Management Framework 1.0",
    short_name="NIST AI RMF",
    effective_date=date(2023, 1, 26),
    last_updated=date(2025, 6, 1),
    status="active",
    requirements=[
        "GOVERN: Establish AI risk governance policies and culture",
        "MAP: Identify and categorize AI risks in context",
        "MEASURE: Analyze and assess AI risks quantitatively and qualitatively",
        "MANAGE: Prioritize and address AI risks with response plans",
        "Maintain trustworthy AI attributes: reliable, safe, secure, explainable, privacy-enhanced, fair",
        "Document AI system purpose, limitations, and trade-offs",
        "Engage diverse stakeholders in AI risk management",
        "Implement continuous monitoring and feedback loops",
        "Conduct impact assessments for high-risk deployments",
        "Maintain human oversight commensurate with risk",
    ],
    penalties=[
        "No direct legal penalties (voluntary framework)",
        "Non-compliance may affect federal procurement eligibility",
        "May be incorporated by reference in regulations",
    ],
    applies_to=[
        "Organizations developing AI systems",
        "Organizations deploying AI systems",
        "Federal agencies (increasingly required)",
        "Federal contractors",
    ],
    compliance_areas=[
        ComplianceArea.ACCOUNTABILITY,
        ComplianceArea.TRANSPARENCY,
        ComplianceArea.EXPLAINABILITY,
        ComplianceArea.HUMAN_OVERSIGHT,
        ComplianceArea.DOCUMENTATION,
        ComplianceArea.BIAS_FAIRNESS,
        ComplianceArea.SECURITY,
    ],
    risk_tiers=[RiskTier.HIGH, RiskTier.LIMITED, RiskTier.MINIMAL],
    official_url="https://www.nist.gov/system/files/documents/2023/01/26/NIST.AI.100-1.pdf",
    summary="Voluntary framework providing guidance for organizations to manage AI risks throughout the AI lifecycle.",
)

# ---------------------------------------------------------------------------
# FTC AI Guidelines
# ---------------------------------------------------------------------------

FTC_AI_GUIDELINES = AILaw(
    law_id="FTC-AI-2023",
    jurisdiction=Jurisdiction.US_FEDERAL,
    law_name="FTC Guidance on Artificial Intelligence and Consumer Protection",
    short_name="FTC AI Guidelines",
    effective_date=date(2023, 6, 29),
    last_updated=date(2026, 1, 15),
    status="active",
    requirements=[
        "Be truthful: do not make false or misleading claims about AI capabilities",
        "Ensure AI outputs are empirically substantiated before making claims",
        "Do not use AI to engage in deceptive or unfair practices",
        "Disclose AI use when material to consumer decision-making",
        "Avoid biased algorithms that cause disparate harm to protected groups",
        "Maintain data security for personal information used in AI",
        "Honor opt-out requests and privacy rights",
        "Do not use dark patterns to override consumer choices",
        "Test AI systems before deployment for accuracy and bias",
        "Maintain accountability for AI-generated consumer communications",
    ],
    penalties=[
        "Civil penalties up to $51,744 per violation per day under FTC Act Section 5",
        "Injunctive relief and disgorgement",
        "Consent orders requiring compliance programs",
        "Reputational harm from public enforcement actions",
    ],
    applies_to=[
        "Any business operating in US commerce using AI",
        "AI-driven advertising and marketing systems",
        "AI-powered consumer-facing applications",
        "AI in credit, employment, housing, and healthcare contexts",
    ],
    compliance_areas=[
        ComplianceArea.TRANSPARENCY,
        ComplianceArea.CONSUMER_PROTECTION,
        ComplianceArea.BIAS_FAIRNESS,
        ComplianceArea.DATA_MINIMIZATION,
        ComplianceArea.ACCOUNTABILITY,
    ],
    risk_tiers=[RiskTier.HIGH, RiskTier.LIMITED],
    official_url="https://www.ftc.gov/business-guidance/blog/2023/06/generative-ai-raises-competition-concerns",
    summary="FTC applies existing consumer protection authority to AI, requiring truthfulness, fairness, and accountability.",
)

# ---------------------------------------------------------------------------
# California SB 1047
# ---------------------------------------------------------------------------

CA_SB_1047 = AILaw(
    law_id="CA-SB-1047-2024",
    jurisdiction=Jurisdiction.US_CA,
    law_name="California Safe and Secure Innovation for Frontier Artificial Intelligence Models Act (SB 1047)",
    short_name="CA SB 1047",
    effective_date=date(2025, 1, 1),
    last_updated=date(2025, 9, 1),
    status="active",
    requirements=[
        "Developers of covered AI models (>$100M training cost or 10^26 FLOPs) must implement safety protocols",
        "Conduct safety testing before and after training of covered models",
        "Implement capability controls preventing mass casualties or critical infrastructure attacks",
        "Maintain a kill switch / ability to shut down model",
        "Preserve records of safety tests and evaluations",
        "Report safety incidents to California Attorney General",
        "Third-party safety audits for highest-risk models",
        "No fine-tune that restores hazardous capabilities removed from base model",
        "Publish transparency reports on safety measures",
        "Establish whistleblower protections for AI safety employees",
    ],
    penalties=[
        "Civil penalties up to 10% of cost to train covered model for first violation",
        "Up to 30% for subsequent violations",
        "Attorney General enforcement authority",
        "Private right of action for violations causing injury",
    ],
    applies_to=[
        "Developers of covered AI models with >$100M compute cost",
        "Fine-tuners making safety-capability trade-offs",
        "Cloud providers knowingly supporting covered model training",
    ],
    compliance_areas=[
        ComplianceArea.ACCOUNTABILITY,
        ComplianceArea.SECURITY,
        ComplianceArea.DOCUMENTATION,
        ComplianceArea.HUMAN_OVERSIGHT,
    ],
    risk_tiers=[RiskTier.HIGH, RiskTier.UNACCEPTABLE],
    official_url="https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240SB1047",
    summary="California law requiring safety protocols for frontier AI models with high compute thresholds.",
)

# ---------------------------------------------------------------------------
# California AB 2013 (AI Training Data Transparency)
# ---------------------------------------------------------------------------

CA_AB_2013 = AILaw(
    law_id="CA-AB-2013-2024",
    jurisdiction=Jurisdiction.US_CA,
    law_name="California Artificial Intelligence Transparency Act (AB 2013)",
    short_name="CA AI Transparency Act",
    effective_date=date(2026, 1, 1),
    last_updated=date(2026, 1, 1),
    status="active",
    requirements=[
        "Disclose training data sources for AI systems offered to California consumers",
        "Describe categories of data used in training",
        "Disclose whether copyrighted or personal data was used",
        "Publish disclosure on developer website",
        "Update disclosures when training data changes significantly",
        "Describe data collection methods and provenance",
    ],
    penalties=[
        "Civil penalties enforced by California AG",
        "Injunctive relief available",
    ],
    applies_to=[
        "AI system providers offering systems to California residents",
        "AI developers with >$100M annual revenue",
    ],
    compliance_areas=[
        ComplianceArea.TRANSPARENCY,
        ComplianceArea.DOCUMENTATION,
        ComplianceArea.DATA_MINIMIZATION,
    ],
    risk_tiers=[RiskTier.HIGH, RiskTier.LIMITED],
    official_url="https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240AB2013",
    summary="Requires AI providers to disclose training data sources to California consumers.",
)

# ---------------------------------------------------------------------------
# Texas HB 149
# ---------------------------------------------------------------------------

TX_HB_149 = AILaw(
    law_id="TX-HB-149-2025",
    jurisdiction=Jurisdiction.US_TX,
    law_name="Texas Responsible AI Governance Act (HB 149)",
    short_name="TX HB 149 / TRAIGA",
    effective_date=date(2025, 9, 1),
    last_updated=date(2025, 9, 1),
    status="active",
    requirements=[
        "Developers must provide documentation on high-risk AI capabilities and limitations",
        "Deployers must implement risk management policies for high-risk AI",
        "Conduct impact assessments before deploying high-risk AI systems",
        "Notify Texas consumers when high-risk AI makes consequential decisions",
        "Provide consumers right to opt out of high-risk AI decisions",
        "Implement bias testing and mitigation for high-risk AI",
        "Maintain audit logs of high-risk AI decisions for 3 years",
        "Annual compliance reports for covered deployers",
        "Designate an AI accountability officer for organizations >$50M revenue",
    ],
    penalties=[
        "Civil penalties up to $10,000 per violation",
        "Injunctive relief by Texas AG",
        "Cure period of 45 days before enforcement",
    ],
    applies_to=[
        "High-risk AI deployers operating in Texas",
        "Organizations with annual revenue >$25M using high-risk AI",
        "AI affecting Texas residents in consequential decisions",
    ],
    compliance_areas=[
        ComplianceArea.TRANSPARENCY,
        ComplianceArea.BIAS_FAIRNESS,
        ComplianceArea.HUMAN_OVERSIGHT,
        ComplianceArea.DOCUMENTATION,
        ComplianceArea.ACCOUNTABILITY,
        ComplianceArea.CONSENT,
    ],
    risk_tiers=[RiskTier.HIGH],
    official_url="https://capitol.texas.gov/BillLookup/History.aspx?LegSess=89R&Bill=HB149",
    summary="Texas law establishing risk-based AI governance with impact assessments and consumer rights for high-risk AI.",
)

# ---------------------------------------------------------------------------
# Colorado SB 205
# ---------------------------------------------------------------------------

CO_SB_205 = AILaw(
    law_id="CO-SB-205-2024",
    jurisdiction=Jurisdiction.US_CO,
    law_name="Colorado Artificial Intelligence Act (SB 205)",
    short_name="CO SB 205 / CAIA",
    effective_date=date(2026, 2, 1),
    last_updated=date(2026, 2, 1),
    status="active",
    requirements=[
        "Developers of high-risk AI must disclose known risks to deployers",
        "Deployers must use reasonable care to avoid algorithmic discrimination",
        "Conduct annual impact assessments for high-risk AI systems",
        "Publish summary of impact assessment or notify AG",
        "Post clear notice when high-risk AI is used in consequential decisions",
        "Provide consumers explanation of AI-generated decisions",
        "Allow consumers to appeal or correct decisions made by high-risk AI",
        "Implement bias testing against protected characteristics",
        "Maintain data governance policies",
        "Developer/deployer contracts must allocate compliance responsibilities",
    ],
    penalties=[
        "Exclusively enforced by Colorado AG",
        "Injunctive relief and disgorgement of profits",
        "Civil penalties as determined by court",
        "60-day cure period for first violations",
    ],
    applies_to=[
        "Developers of high-risk AI systems",
        "Deployers of high-risk AI in Colorado",
        "High-risk AI: consequential decisions in education, employment, financial, healthcare, housing, legal",
    ],
    compliance_areas=[
        ComplianceArea.BIAS_FAIRNESS,
        ComplianceArea.TRANSPARENCY,
        ComplianceArea.EXPLAINABILITY,
        ComplianceArea.HUMAN_OVERSIGHT,
        ComplianceArea.DOCUMENTATION,
        ComplianceArea.ACCOUNTABILITY,
    ],
    risk_tiers=[RiskTier.HIGH],
    official_url="https://leg.colorado.gov/bills/sb24-205",
    summary="Colorado's comprehensive AI act focusing on algorithmic discrimination prevention and consumer rights in high-risk AI decisions.",
)

# ---------------------------------------------------------------------------
# New York AI Bias Laws (Compilation)
# ---------------------------------------------------------------------------

NY_AI_BIAS = AILaw(
    law_id="NY-AI-BIAS-2023",
    jurisdiction=Jurisdiction.US_NY,
    law_name="New York City Automated Employment Decision Tool Law (Local Law 144) + NY AI Bias Laws",
    short_name="NY AI Bias Laws",
    effective_date=date(2023, 7, 5),
    last_updated=date(2026, 1, 1),
    status="active",
    requirements=[
        "NYC LL144: Annual independent bias audits of automated employment decision tools",
        "Publish bias audit summary on company website",
        "Notify NYC job candidates/employees before using AEDT",
        "Provide alternative assessment process upon request",
        "NY State: Prohibit AI discrimination in insurance underwriting",
        "NY DFS guidance: Insurers must test AI for proxy discrimination",
        "NY State Legislature: Proposed right to explanation for AI decisions",
        "Prohibit facial recognition in employment without consent",
        "AEDT bias audit must cover race/ethnicity and sex impact ratios",
    ],
    penalties=[
        "NYC LL144: $500-$1,500 per violation per day",
        "NY AG enforcement for broader AI discrimination",
        "Title VII federal liability for discriminatory employment AI",
        "EEOC guidance enforcement",
    ],
    applies_to=[
        "NYC employers using automated employment decision tools",
        "Employment agencies in NYC",
        "NY insurers using AI in underwriting",
        "Any organization using AI for hiring/promotion in NYC",
    ],
    compliance_areas=[
        ComplianceArea.BIAS_FAIRNESS,
        ComplianceArea.TRANSPARENCY,
        ComplianceArea.EMPLOYMENT,
        ComplianceArea.ACCOUNTABILITY,
        ComplianceArea.DOCUMENTATION,
    ],
    risk_tiers=[RiskTier.HIGH],
    official_url="https://www.nyc.gov/site/dca/about/automated-employment-decision-tools.page",
    summary="NYC requires bias audits for AI used in employment decisions; NY state extends protections to insurance and other sectors.",
)

# ---------------------------------------------------------------------------
# Illinois AI Laws
# ---------------------------------------------------------------------------

IL_AI_LAWS = AILaw(
    law_id="IL-AI-2020",
    jurisdiction=Jurisdiction.US_IL,
    law_name="Illinois Artificial Intelligence Video Interview Act + AI in Employment",
    short_name="IL AI Video Interview Act",
    effective_date=date(2020, 1, 1),
    last_updated=date(2025, 1, 1),
    status="active",
    requirements=[
        "Notify applicants before using AI to analyze video interviews",
        "Explain how AI evaluation works",
        "Obtain consent before AI video analysis",
        "Collect/share AI video data only for assessment purposes",
        "Destroy video and data within 30 days of request",
        "Cannot use facial recognition in employment without consent",
        "Illinois BIPA: Biometric data collection requires written consent and policy",
        "Disclose AI use in employment screening",
    ],
    penalties=[
        "BIPA: $1,000 per negligent violation, $5,000 per intentional violation",
        "Private right of action under BIPA",
        "State AG enforcement for video interview violations",
    ],
    applies_to=[
        "Illinois employers using AI video interviews",
        "Organizations collecting biometric data in Illinois",
        "HR technology vendors operating in Illinois",
    ],
    compliance_areas=[
        ComplianceArea.CONSENT,
        ComplianceArea.TRANSPARENCY,
        ComplianceArea.DATA_MINIMIZATION,
        ComplianceArea.EMPLOYMENT,
    ],
    risk_tiers=[RiskTier.HIGH, RiskTier.LIMITED],
    official_url="https://www.ilga.gov/legislation/ilcs/ilcs3.asp?ActID=4015",
    summary="Illinois requires consent and transparency for AI-driven video interview analysis and biometric data collection.",
)

# ---------------------------------------------------------------------------
# Virginia Consumer Data Protection Act (AI Provisions)
# ---------------------------------------------------------------------------

VA_CDPA_AI = AILaw(
    law_id="VA-CDPA-AI-2023",
    jurisdiction=Jurisdiction.US_VA,
    law_name="Virginia Consumer Data Protection Act — Automated Processing Provisions",
    short_name="VA CDPA AI",
    effective_date=date(2023, 1, 1),
    last_updated=date(2025, 7, 1),
    status="active",
    requirements=[
        "Conduct data protection assessment for processing involving solely automated decision-making",
        "Consumers have right to opt out of profiling for decisions with legal or significant effects",
        "Controller must provide meaningful information about automated decision logic",
        "Disclose use of personal data in automated decision-making",
        "Data minimization: collect only data adequate and relevant for processing purpose",
        "Purpose limitation: do not use data for incompatible secondary purposes",
    ],
    penalties=[
        "Civil penalties up to $7,500 per violation (AG enforcement)",
        "No private right of action",
        "30-day cure period",
    ],
    applies_to=[
        "Controllers processing personal data of 100,000+ Virginia consumers",
        "Controllers deriving 50%+ revenue from personal data of 25,000+ consumers",
    ],
    compliance_areas=[
        ComplianceArea.DATA_MINIMIZATION,
        ComplianceArea.TRANSPARENCY,
        ComplianceArea.HUMAN_OVERSIGHT,
        ComplianceArea.CONSENT,
    ],
    risk_tiers=[RiskTier.HIGH, RiskTier.LIMITED],
    official_url="https://law.lis.virginia.gov/vacodefull/title59.1/chapter53/",
    summary="Virginia privacy law includes provisions for automated decision-making and consumer opt-out rights.",
)

# ---------------------------------------------------------------------------
# Washington AI Laws
# ---------------------------------------------------------------------------

WA_AI_LAWS = AILaw(
    law_id="WA-AI-2024",
    jurisdiction=Jurisdiction.US_WA,
    law_name="Washington Artificial Intelligence Accountability Act (SB 5838)",
    short_name="WA AI Accountability Act",
    effective_date=date(2025, 7, 27),
    last_updated=date(2025, 7, 27),
    status="active",
    requirements=[
        "Developers must document high-risk AI capabilities and limitations",
        "Deployers must conduct impact assessments annually",
        "Consumers must be notified when high-risk AI affects consequential decisions",
        "Provide consumers with explanation of AI-generated decisions",
        "Right to human review of adverse high-risk AI decisions",
        "Implement bias testing for race, gender, national origin, disability",
        "Maintain records of AI system changes and updates",
        "Designate AI governance officer for large deployers",
        "Publish AI use policy on organizational website",
    ],
    penalties=[
        "Washington AG enforcement",
        "Civil penalties up to $7,500 per violation",
        "Pattern violations subject to enhanced penalties",
    ],
    applies_to=[
        "High-risk AI deployers in Washington state",
        "Organizations with annual revenue >$25M",
        "AI affecting Washington residents in consequential decisions",
    ],
    compliance_areas=[
        ComplianceArea.TRANSPARENCY,
        ComplianceArea.BIAS_FAIRNESS,
        ComplianceArea.HUMAN_OVERSIGHT,
        ComplianceArea.DOCUMENTATION,
        ComplianceArea.ACCOUNTABILITY,
        ComplianceArea.EXPLAINABILITY,
    ],
    risk_tiers=[RiskTier.HIGH],
    official_url="https://app.leg.wa.gov/billsummary?BillNumber=5838&Year=2025&Initiative=false",
    summary="Washington's comprehensive AI accountability law requiring impact assessments, bias testing, and consumer rights.",
)

# ---------------------------------------------------------------------------
# ABA Model Rules for AI (Legal Profession)
# ---------------------------------------------------------------------------

ABA_AI_RULES = AILaw(
    law_id="ABA-AI-RULES-2024",
    jurisdiction=Jurisdiction.PROFESSIONAL,
    law_name="ABA Formal Opinion 512: Generative Artificial Intelligence Tools",
    short_name="ABA Model Rules for AI",
    effective_date=date(2024, 7, 29),
    last_updated=date(2026, 1, 1),
    status="active",
    requirements=[
        "Competence (Rule 1.1): Lawyers must understand AI tools used in legal practice",
        "Confidentiality (Rule 1.6): Protect client data; evaluate AI vendor confidentiality",
        "Supervision (Rule 5.1/5.3): Supervise AI outputs as you would subordinate work",
        "Candor (Rule 3.3): Verify AI-generated legal citations before court submission",
        "Fees (Rule 1.5): AI efficiency gains must be reflected in reasonable fees",
        "Communication (Rule 1.4): Inform clients when AI materially affects their matter",
        "Diligence (Rule 1.3): Do not rely on AI without proper verification",
        "Unauthorized Practice: AI cannot practice law; must maintain human attorney oversight",
        "Disclosure: Disclose material AI use to clients when requested",
        "Data Security: Implement reasonable AI vendor security safeguards",
    ],
    penalties=[
        "Disciplinary action by state bar (suspension, disbarment)",
        "Malpractice liability for AI-related errors without proper oversight",
        "Fee disgorgement for unreasonable AI-inflated bills",
        "Sanctions for submitting AI-hallucinated citations to courts",
    ],
    applies_to=[
        "Licensed attorneys using AI tools",
        "Law firms deploying AI for legal work",
        "Legal technology companies serving law firms",
        "Paralegals using AI under attorney supervision",
    ],
    compliance_areas=[
        ComplianceArea.TRANSPARENCY,
        ComplianceArea.ACCOUNTABILITY,
        ComplianceArea.UPL,
        ComplianceArea.DATA_MINIMIZATION,
        ComplianceArea.EXPLAINABILITY,
    ],
    risk_tiers=[RiskTier.HIGH, RiskTier.LIMITED],
    official_url="https://www.americanbar.org/content/dam/aba/administrative/professional_responsibility/aba-formal-opinion-512.pdf",
    summary="ABA guidance on applying Model Rules of Professional Conduct to generative AI use in legal practice.",
    legal_profession_specific=True,
)

# ---------------------------------------------------------------------------
# Florida AI Laws
# ---------------------------------------------------------------------------

FL_AI_LAWS = AILaw(
    law_id="FL-AI-2025",
    jurisdiction=Jurisdiction.US_FL,
    law_name="Florida Digital Rights and Artificial Intelligence Act (SB 1804)",
    short_name="FL AI Rights Act",
    effective_date=date(2025, 7, 1),
    last_updated=date(2025, 7, 1),
    status="active",
    requirements=[
        "Disclose AI-generated content in political advertising",
        "Label synthetic media and deepfakes",
        "Right of publicity protection from AI voice/likeness cloning",
        "Prohibit non-consensual intimate AI-generated images",
        "Parental consent for AI interactions with minors",
        "K-12 AI literacy curriculum requirements",
        "State agency AI use inventory and disclosure",
        "Prohibit AI voice cloning for fraud",
    ],
    penalties=[
        "Civil penalties for synthetic media violations: $50,000+",
        "Criminal liability for deepfake fraud",
        "Private right of action for publicity violations",
    ],
    applies_to=[
        "Political advertisers in Florida",
        "AI content platforms",
        "Organizations using AI-generated voices or likenesses",
        "State agencies using AI",
    ],
    compliance_areas=[
        ComplianceArea.TRANSPARENCY,
        ComplianceArea.CONSENT,
        ComplianceArea.CONSUMER_PROTECTION,
    ],
    risk_tiers=[RiskTier.HIGH, RiskTier.LIMITED],
    official_url="https://www.flsenate.gov/Session/Bill/2025/1804",
    summary="Florida law targeting synthetic media, AI deepfakes, and right of publicity protections.",
)

# ---------------------------------------------------------------------------
# Master Law Registry
# ---------------------------------------------------------------------------

ALL_LAWS: List[AILaw] = [
    EU_AI_ACT,
    NIST_AI_RMF,
    FTC_AI_GUIDELINES,
    CA_SB_1047,
    CA_AB_2013,
    TX_HB_149,
    CO_SB_205,
    NY_AI_BIAS,
    IL_AI_LAWS,
    VA_CDPA_AI,
    WA_AI_LAWS,
    ABA_AI_RULES,
    FL_AI_LAWS,
]


def get_laws_by_jurisdiction(jurisdiction: Jurisdiction) -> List[AILaw]:
    """Return all laws for a given jurisdiction."""
    return [law for law in ALL_LAWS if law.jurisdiction == jurisdiction]


def get_laws_by_area(area: ComplianceArea) -> List[AILaw]:
    """Return all laws touching a specific compliance area."""
    return [law for law in ALL_LAWS if law.matches_area(area)]


def get_laws_by_risk_tier(tier: RiskTier) -> List[AILaw]:
    """Return all laws applicable to a given risk tier."""
    return [law for law in ALL_LAWS if law.covers_risk_tier(tier)]


def get_active_laws() -> List[AILaw]:
    """Return only currently active laws."""
    return [law for law in ALL_LAWS if law.is_active()]


def get_applicable_laws(
    jurisdictions: List[Jurisdiction],
    risk_tier: RiskTier,
    compliance_areas: Optional[List[ComplianceArea]] = None,
    legal_profession: bool = False,
) -> List[AILaw]:
    """
    Return laws applicable to a given deployment context.

    Args:
        jurisdictions: List of relevant jurisdictions (where you operate / serve users)
        risk_tier: Highest risk tier applicable to the AI system
        compliance_areas: Optional filter for specific compliance areas
        legal_profession: Include legal profession-specific rules
    """
    results = []
    for law in ALL_LAWS:
        if not law.is_active():
            continue
        # Jurisdiction match (including extraterritorial)
        jurisdiction_match = (
            law.jurisdiction in jurisdictions
            or law.extraterritorial
            or law.jurisdiction == Jurisdiction.US_FEDERAL
            or law.jurisdiction == Jurisdiction.INTERNATIONAL
            or (law.legal_profession_specific and legal_profession
                and law.jurisdiction == Jurisdiction.PROFESSIONAL)
        )
        if not jurisdiction_match:
            continue
        # Legal profession filter
        if law.legal_profession_specific and not legal_profession:
            continue
        # Risk tier match
        if not law.covers_risk_tier(risk_tier):
            continue
        # Compliance area filter
        if compliance_areas:
            if not any(law.matches_area(area) for area in compliance_areas):
                continue
        results.append(law)
    return results


def get_law_by_id(law_id: str) -> Optional[AILaw]:
    """Look up a law by its ID."""
    for law in ALL_LAWS:
        if law.law_id == law_id:
            return law
    return None


def get_laws_summary() -> Dict[str, Dict]:
    """Return a lightweight summary dict of all laws."""
    return {
        law.law_id: {
            "name": law.short_name,
            "jurisdiction": law.jurisdiction.value,
            "effective_date": law.effective_date.isoformat(),
            "status": law.status,
            "areas": [a.value for a in law.compliance_areas],
            "risk_tiers": [r.value for r in law.risk_tiers],
        }
        for law in ALL_LAWS
    }


if __name__ == "__main__":
    import json
    summary = get_laws_summary()
    print(f"Total laws in database: {len(ALL_LAWS)}")
    print(json.dumps(summary, indent=2, default=str))
