"""
Trust Reasoning Engine
======================
Multi-step chain-of-thought reasoning for trust law analysis.
Provides genuine legal reasoning through scoring algorithms,
weighted factors, and conditional logic.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re


@dataclass
class TrustAnalysis:
    """Complete analysis result for a trust law scenario."""
    recommended_trust_type: str
    jurisdiction_recommendation: str
    asset_protection_score: float       # 0-100
    tax_efficiency_score: float          # 0-100
    complexity_score: float              # 0-100 (higher = more complex)
    risks: List[str]
    opportunities: List[str]
    reasoning_chain: List[str]
    confidence: float                    # 0.0 - 1.0
    alternative_strategies: List[str]
    estimated_cost_range: str
    implementation_timeline: str
    critical_deadlines: List[str]


@dataclass
class TrustAudit:
    """Audit result for an existing trust document."""
    trust_type_detected: str
    validity_score: float                # 0-100
    vulnerabilities: List[str]
    strengths: List[str]
    recommendations: List[str]
    jurisdiction_compliance: Dict[str, Any]
    missing_provisions: List[str]
    potential_tax_issues: List[str]
    estimated_exposure: str


@dataclass
class Opinion:
    """An individual agent's opinion in a strategy comparison."""
    agent_role: str
    position: str
    reasoning: str
    score: float
    key_concerns: List[str]


@dataclass
class StrategyComparison:
    """Result of comparing multiple trust strategies."""
    strategies: List[str]
    winner: str
    winner_score: float
    scores: Dict[str, float]
    opinions: List[Opinion]
    recommendation: str
    caveats: List[str]


class TrustReasoningEngine:
    """
    Multi-step reasoning engine for trust law analysis.
    Implements chain-of-thought legal reasoning across six dimensions:
    1. Trust type identification
    2. Asset protection requirements
    3. Tax implications
    4. Jurisdiction options
    5. Risk identification
    6. Strategy recommendation
    """

    # Scoring weights for different analysis dimensions
    DIMENSION_WEIGHTS = {
        "asset_protection": 0.30,
        "tax_efficiency": 0.25,
        "privacy": 0.15,
        "flexibility": 0.10,
        "cost": 0.10,
        "complexity": 0.10,
    }

    # Trust type keywords for scenario identification
    TRUST_TYPE_INDICATORS = {
        "revocable_living_trust": [
            "probate avoidance", "probate", "incapacity", "pour-over", "living trust",
            "revocable", "privacy from public", "ancillary", "multi-state property",
        ],
        "irrevocable_trust": [
            "estate tax", "irrevocable", "remove from estate", "life insurance",
            "ilit", "tax reduction", "gift", "medicaid",
        ],
        "asset_protection_trust": [
            "creditor", "lawsuit", "professional liability", "doctor", "lawyer",
            "malpractice", "liability", "protect assets", "judgment proof",
        ],
        "dynasty_trust": [
            "dynasty", "generation", "multi-generational", "grandchildren", "gst",
            "generation skipping", "perpetuities", "100 years", "long term",
        ],
        "special_needs_trust": [
            "special needs", "disabled", "disability", "medicaid", "ssi",
            "supplemental needs", "government benefits",
        ],
        "charitable_remainder_trust": [
            "charity", "charitable", "charitable remainder", "crt", "appreciated",
            "low basis", "income stream", "charitable deduction",
        ],
        "idgt": [
            "idgt", "intentionally defective", "installment sale", "estate freeze",
            "sell to trust", "business interest",
        ],
        "slat": [
            "slat", "spousal", "spouse", "lifetime access", "married", "marriage",
            "exemption", "sunset",
        ],
        "dapt": [
            "dapt", "self-settled", "domestic asset protection", "professional",
            "physician", "surgeon", "pilot",
        ],
        "offshore_trust": [
            "offshore", "foreign trust", "cook islands", "nevis", "liechtenstein",
            "cayman", "belize", "international",
        ],
        "qprt": [
            "qprt", "qualified personal residence", "residence", "home", "house",
            "real property",
        ],
        "medicaid_trust": [
            "medicaid", "nursing home", "long-term care", "ltc", "spend down",
            "elder law",
        ],
    }

    # Risk factors by scenario type
    RISK_FACTORS = {
        "fraudulent_transfer": [
            "creditors", "lawsuit", "pending litigation", "existing claims",
            "imminent", "asset transfer", "protect from creditor",
        ],
        "estate_tax_risk": [
            "estate", "high net worth", "millions", "billion", "inheritance",
        ],
        "regulatory_risk": [
            "offshore", "foreign", "fbar", "fatca", "reporting",
        ],
        "divorce_risk": [
            "marriage", "spouse", "divorce", "slat", "marital",
        ],
        "tax_compliance": [
            "grantor trust", "foreign trust", "form 3520", "reporting",
        ],
    }

    # Jurisdiction scoring matrix for different goals
    JURISDICTION_SCORES = {
        "south_dakota": {"asset_protection": 9, "tax": 10, "privacy": 10, "flexibility": 9, "cost": 6, "dynasty": 10},
        "nevada": {"asset_protection": 9, "tax": 10, "privacy": 8, "flexibility": 8, "cost": 7, "dynasty": 8},
        "alaska": {"asset_protection": 8, "tax": 10, "privacy": 7, "flexibility": 7, "cost": 7, "dynasty": 9},
        "delaware": {"asset_protection": 8, "tax": 9, "privacy": 8, "flexibility": 8, "cost": 6, "dynasty": 9},
        "wyoming": {"asset_protection": 8, "tax": 10, "privacy": 9, "flexibility": 7, "cost": 8, "dynasty": 8},
        "cook_islands": {"asset_protection": 10, "tax": 6, "privacy": 9, "flexibility": 7, "cost": 3, "dynasty": 9},
        "nevis": {"asset_protection": 9, "tax": 6, "privacy": 9, "flexibility": 7, "cost": 4, "dynasty": 9},
        "liechtenstein": {"asset_protection": 9, "tax": 5, "privacy": 8, "flexibility": 8, "cost": 2, "dynasty": 10},
    }

    def reason_about_trust(self, scenario: str, context: Dict[str, Any]) -> TrustAnalysis:
        """
        Main reasoning method. Applies 6-step chain-of-thought analysis.

        Args:
            scenario: Natural language description of the client's situation
            context: Dict with keys like: assets, liabilities, net_worth, goals,
                     threats, state, married, age, beneficiaries, existing_structures
        """
        reasoning_chain = []
        scenario_lower = scenario.lower()

        # ── STEP 1: Identify trust type needed ──────────────────────────────
        reasoning_chain.append("STEP 1: Identifying Trust Type Requirements")
        trust_type_scores: Dict[str, int] = {}
        for trust_type, keywords in self.TRUST_TYPE_INDICATORS.items():
            score = sum(1 for kw in keywords if kw in scenario_lower)
            if score > 0:
                trust_type_scores[trust_type] = score
                reasoning_chain.append(f"  → {trust_type}: matched {score} keyword(s)")

        # Context-based adjustments
        if context.get("net_worth", 0) > 5_000_000:
            trust_type_scores["dynasty_trust"] = trust_type_scores.get("dynasty_trust", 0) + 2
            trust_type_scores["idgt"] = trust_type_scores.get("idgt", 0) + 2
            reasoning_chain.append("  → High net worth: boosting dynasty trust and IDGT scores")
        if context.get("married"):
            trust_type_scores["slat"] = trust_type_scores.get("slat", 0) + 2
            reasoning_chain.append("  → Married status: boosting SLAT score")
        if context.get("threats") and "lawsuit" in str(context.get("threats", [])):
            trust_type_scores["asset_protection_trust"] = trust_type_scores.get("asset_protection_trust", 0) + 3
            reasoning_chain.append("  → Lawsuit threat: boosting asset protection trust score")

        if trust_type_scores:
            recommended_trust_type = max(trust_type_scores, key=lambda k: trust_type_scores[k])
        else:
            recommended_trust_type = "revocable_living_trust"  # default
            reasoning_chain.append("  → No strong indicators found; defaulting to revocable living trust")

        alternatives = sorted(
            [k for k in trust_type_scores if k != recommended_trust_type],
            key=lambda k: trust_type_scores[k], reverse=True
        )[:3]
        reasoning_chain.append(f"  ✓ Primary recommendation: {recommended_trust_type}")
        reasoning_chain.append(f"  ✓ Alternatives: {', '.join(alternatives)}")

        # ── STEP 2: Asset Protection Requirements ────────────────────────────
        reasoning_chain.append("\nSTEP 2: Analyzing Asset Protection Requirements")
        ap_score = 30.0  # base score
        threats = context.get("threats", [])
        if isinstance(threats, str):
            threats = [threats]

        threat_ap_boosts = {
            "lawsuit": 20, "creditor": 15, "divorce": 10, "bankruptcy": 25,
            "malpractice": 20, "professional liability": 20,
        }
        for threat in threats:
            for threat_key, boost in threat_ap_boosts.items():
                if threat_key in str(threat).lower():
                    ap_score = min(100, ap_score + boost)
                    reasoning_chain.append(f"  → Threat '{threat_key}' identified: +{boost} AP need")

        if "offshore" in scenario_lower:
            ap_score = min(100, ap_score + 20)
            reasoning_chain.append("  → Offshore indicator: +20 AP need")
        if context.get("existing_structures"):
            ap_score = max(20, ap_score - 10)
            reasoning_chain.append("  → Existing protection structures: -10 AP need (already partially protected)")

        reasoning_chain.append(f"  ✓ Asset protection requirement score: {ap_score:.1f}/100")

        # ── STEP 3: Tax Implications ─────────────────────────────────────────
        reasoning_chain.append("\nSTEP 3: Evaluating Tax Implications")
        tax_score = 50.0  # base
        net_worth = context.get("net_worth", 0)
        tax_keywords = ["estate tax", "gift tax", "capital gains", "income tax", "gst", "generation skipping"]

        if net_worth > 13_610_000:  # above 2024 federal exemption
            tax_score = min(100, tax_score + 30)
            reasoning_chain.append("  → Net worth exceeds federal estate tax exemption: high tax risk")
        if net_worth > 5_000_000:
            tax_score = min(100, tax_score + 10)
            reasoning_chain.append("  → Significant estate: estate planning tax optimization needed")

        for kw in tax_keywords:
            if kw in scenario_lower:
                tax_score = min(100, tax_score + 5)
                reasoning_chain.append(f"  → Tax keyword '{kw}' found: +5")

        if recommended_trust_type in ["idgt", "slat", "dynasty_trust", "charitable_remainder_trust"]:
            tax_score = min(100, tax_score + 15)
            reasoning_chain.append(f"  → {recommended_trust_type} is tax-optimization focused: +15")

        reasoning_chain.append(f"  ✓ Tax efficiency opportunity score: {tax_score:.1f}/100")

        # ── STEP 4: Jurisdiction Options ─────────────────────────────────────
        reasoning_chain.append("\nSTEP 4: Evaluating Jurisdiction Options")
        client_state = context.get("state", "").lower()
        offshore_needed = "offshore" in scenario_lower or ap_score > 85

        if offshore_needed:
            jurisdiction_recommendation = "Cook Islands (with domestic backup in South Dakota)"
            reasoning_chain.append("  → High AP need + offshore indicators: Cook Islands recommended")
        elif recommended_trust_type in ["asset_protection_trust", "dapt"]:
            if "nevada" in scenario_lower:
                jurisdiction_recommendation = "Nevada (client preference noted)"
            else:
                jurisdiction_recommendation = "South Dakota (2-year SOL, no state income tax, unlimited dynasty)"
            reasoning_chain.append(f"  → DAPT scenario: {jurisdiction_recommendation}")
        elif recommended_trust_type == "dynasty_trust":
            jurisdiction_recommendation = "South Dakota (unlimited duration, no state income tax)"
            reasoning_chain.append("  → Dynasty trust: South Dakota ideal (abolished Rule Against Perpetuities)")
        elif client_state and not offshore_needed:
            jurisdiction_recommendation = f"{client_state.title()} (client's home state — adequate for non-AP trust)"
            reasoning_chain.append(f"  → Standard trust in client's home state: {client_state}")
        else:
            jurisdiction_recommendation = "South Dakota (best overall domestic trust jurisdiction)"
            reasoning_chain.append("  → Default: South Dakota for best overall trust environment")

        reasoning_chain.append(f"  ✓ Jurisdiction recommendation: {jurisdiction_recommendation}")

        # ── STEP 5: Risk Identification ──────────────────────────────────────
        reasoning_chain.append("\nSTEP 5: Identifying Risks")
        risks = []
        opportunities = []

        # Fraudulent transfer risk
        if any(t in scenario_lower for t in ["pending", "lawsuit", "sued", "judgment"]):
            risks.append("⚠️ CRITICAL: Transfer may be challenged as fraudulent — existing creditor exposure detected")
            risks.append("Consult with litigator to assess exposure before any transfers")

        # Reciprocal trust doctrine
        if recommended_trust_type == "slat" and "married" in scenario_lower:
            risks.append("Reciprocal trust doctrine: if both spouses create SLATs, they must be materially different")

        # Offshore compliance risks
        if offshore_needed:
            risks.append("FBAR reporting required: FinCEN Form 114 annually if offshore account > $10,000")
            risks.append("Form 3520 and 3520-A required for foreign trust transactions")
            risks.append("FATCA compliance: Form 8938 if offshore assets exceed thresholds")
            risks.append("Civil contempt risk if US court orders repatriation and grantor refuses")

        # Dynasty trust risks
        if recommended_trust_type == "dynasty_trust":
            risks.append("GST tax applies to any generation-skipping distributions exceeding exemption")
            risks.append("Must allocate GST exemption properly at trust creation")

        # General risks
        if net_worth > 13_610_000:
            risks.append("Estate tax exemption sunset risk: exemption may halve in 2026 if TCJA not extended")
            opportunities.append("ACT NOW: Use current $13.61M exemption before potential 2026 sunset")

        if not risks:
            risks.append("Standard trust administration risks (fiduciary duty, accounting, beneficiary disputes)")

        # Opportunities
        if net_worth > 1_000_000:
            opportunities.append("Consider funding irrevocable trust with life insurance for leveraged transfer")
        if recommended_trust_type in ["crt", "charitable_lead_trust"]:
            opportunities.append("Charitable deduction available in year of contribution")
        if "appreciated" in scenario_lower or "low basis" in scenario_lower:
            opportunities.append("Charitable Remainder Trust can sell appreciated assets without immediate capital gains")

        reasoning_chain.append(f"  ✓ Identified {len(risks)} risk(s) and {len(opportunities)} opportunit(ies)")

        # ── STEP 6: Final Strategy ───────────────────────────────────────────
        reasoning_chain.append("\nSTEP 6: Formulating Recommended Strategy")

        # Complexity score
        complexity_map = {
            "revocable_living_trust": 25,
            "irrevocable_trust": 50,
            "asset_protection_trust": 70,
            "dapt": 70,
            "dynasty_trust": 80,
            "idgt": 85,
            "slat": 75,
            "offshore_trust": 95,
            "cook_islands_trust": 95,
            "charitable_remainder_trust": 75,
            "special_needs_trust": 65,
            "qprt": 70,
            "medicaid_trust": 65,
        }
        complexity_score = float(complexity_map.get(recommended_trust_type, 50))

        # Cost estimate
        cost_map = {
            "revocable_living_trust": "$1,500–$5,000",
            "irrevocable_trust": "$3,000–$10,000",
            "asset_protection_trust": "$5,000–$15,000 + annual admin",
            "dapt": "$5,000–$15,000",
            "dynasty_trust": "$10,000–$30,000 + ongoing admin",
            "idgt": "$8,000–$25,000",
            "slat": "$5,000–$15,000",
            "offshore_trust": "$20,000–$50,000 setup + $5,000–$15,000/year",
            "cook_islands_trust": "$25,000–$60,000 setup + $10,000–$30,000/year",
            "charitable_remainder_trust": "$5,000–$15,000 + actuarial",
            "special_needs_trust": "$3,000–$8,000",
        }
        cost_estimate = cost_map.get(recommended_trust_type, "$5,000–$25,000")

        timeline_map = {
            "revocable_living_trust": "2–4 weeks",
            "irrevocable_trust": "4–8 weeks",
            "asset_protection_trust": "4–8 weeks",
            "dynasty_trust": "6–12 weeks",
            "offshore_trust": "8–16 weeks",
            "cook_islands_trust": "8–16 weeks",
        }
        timeline = timeline_map.get(recommended_trust_type, "4–8 weeks")

        # Confidence scoring
        confidence = 0.5
        if len(trust_type_scores) >= 3:
            confidence += 0.2
        if context.get("net_worth") and context.get("state"):
            confidence += 0.1
        if context.get("threats"):
            confidence += 0.1
        if context.get("goals"):
            confidence += 0.1
        confidence = min(0.95, confidence)

        critical_deadlines = []
        if net_worth > 5_000_000:
            critical_deadlines.append("2025 year-end: Use gift tax annual exclusions ($18,000/donee for 2024)")
            critical_deadlines.append("2025: Act before potential TCJA exemption sunset January 1, 2026")

        reasoning_chain.append(f"  ✓ Complexity: {complexity_score}/100")
        reasoning_chain.append(f"  ✓ Cost estimate: {cost_estimate}")
        reasoning_chain.append(f"  ✓ Timeline: {timeline}")
        reasoning_chain.append(f"  ✓ Confidence: {confidence:.0%}")

        return TrustAnalysis(
            recommended_trust_type=recommended_trust_type,
            jurisdiction_recommendation=jurisdiction_recommendation,
            asset_protection_score=ap_score,
            tax_efficiency_score=tax_score,
            complexity_score=complexity_score,
            risks=risks,
            opportunities=opportunities,
            reasoning_chain=reasoning_chain,
            confidence=confidence,
            alternative_strategies=alternatives,
            estimated_cost_range=cost_estimate,
            implementation_timeline=timeline,
            critical_deadlines=critical_deadlines,
        )

    def analyze_existing_trust(self, trust_document_text: str) -> TrustAudit:
        """
        Audit an existing trust document for validity, vulnerabilities, and compliance.

        Args:
            trust_document_text: Full text of the trust document
        """
        text_lower = trust_document_text.lower()
        vulnerabilities = []
        strengths = []
        recommendations = []
        missing_provisions = []
        potential_tax_issues = []

        # ── Trust Type Detection ─────────────────────────────────────────────
        type_indicators = {
            "Revocable Living Trust": ["revocable", "grantor may revoke", "revoke at any time"],
            "Irrevocable Trust": ["irrevocable", "cannot be revoked", "irrevocably transferred"],
            "Asset Protection Trust": ["asset protection", "spendthrift", "self-settled"],
            "Dynasty Trust": ["dynasty", "generation-skipping", "perpetuities"],
            "Special Needs Trust": ["special needs", "supplemental needs", "governmental benefits"],
            "Charitable Remainder Trust": ["charitable remainder", "unitrust", "annuity trust"],
            "Business Trust": ["business trust", "certificate of beneficial interest", "business purposes"],
        }
        trust_type_detected = "Unknown Trust Type"
        for ttype, indicators in type_indicators.items():
            if any(ind in text_lower for ind in indicators):
                trust_type_detected = ttype
                break

        # ── Validity Checks ──────────────────────────────────────────────────
        validity_score = 100.0

        # Required elements check
        required_elements = {
            "settlor/grantor identification": ["grantor", "settlor", "trustor"],
            "trustee designation": ["trustee"],
            "beneficiary designation": ["beneficiary", "beneficiaries"],
            "trust property": ["trust property", "trust estate", "trust assets", "corpus"],
            "trust purpose": ["purpose", "for the benefit"],
            "governing law clause": ["governed by the laws", "laws of the state"],
            "signature block": ["in witness whereof", "signed", "executed"],
        }

        for element, keywords in required_elements.items():
            if any(kw in text_lower for kw in keywords):
                strengths.append(f"✓ Contains {element}")
            else:
                missing_provisions.append(f"Missing: {element}")
                validity_score -= 15
                vulnerabilities.append(f"⚠️ No clear {element} — may invalidate the trust")

        # Spendthrift clause check
        if "spendthrift" in text_lower:
            strengths.append("✓ Spendthrift clause present — creditor protection for beneficiaries")
        else:
            recommendations.append("Consider adding a spendthrift clause to protect beneficiary interests from creditors")

        # Successor trustee check
        if "successor trustee" in text_lower:
            strengths.append("✓ Successor trustee provisions present — continuity planning")
        else:
            missing_provisions.append("No successor trustee provision — critical gap")
            vulnerabilities.append("⚠️ No successor trustee named — court appointment may be required if primary trustee incapacitated")
            validity_score -= 10

        # Power of trustee check
        if "powers of the trustee" in text_lower or "trustee shall have" in text_lower:
            strengths.append("✓ Trustee powers enumerated")
        else:
            recommendations.append("Add explicit trustee powers section to avoid disputes")

        # Notarization check (looking for common notary language)
        if "notary public" in text_lower or "acknowledged before me" in text_lower or "subscribed and sworn" in text_lower:
            strengths.append("✓ Notarization language present")
        else:
            missing_provisions.append("No notarization language — may not be properly executed")
            validity_score -= 5

        # ── Tax Issue Detection ──────────────────────────────────────────────
        if "retained" in text_lower and trust_type_detected != "Revocable Living Trust":
            potential_tax_issues.append("Retained interests detected — analyze IRC §§2036-2038 estate inclusion risk")
        if "income" in text_lower and "grantor" in text_lower:
            potential_tax_issues.append("Potential grantor trust treatment under IRC §§671-679 — verify intent")
        if trust_type_detected == "Asset Protection Trust":
            potential_tax_issues.append("Self-settled trust: confirm grantor trust treatment for income tax")
        if "foreign" in text_lower or "offshore" in text_lower:
            potential_tax_issues.append("Foreign trust reporting: ensure Forms 3520, 3520-A, FBAR compliance")

        # ── Jurisdiction Compliance ──────────────────────────────────────────
        state_match = re.search(r"laws of the state of ([a-zA-Z\s]+)", trust_document_text, re.IGNORECASE)
        governing_state = state_match.group(1).strip() if state_match else "Undetected"

        jurisdiction_compliance = {
            "governing_state": governing_state,
            "utc_adopted": governing_state.lower() in [
                "alabama", "alaska", "arizona", "arkansas", "colorado",
                "connecticut", "florida", "georgia", "hawaii", "idaho",
                "illinois", "indiana", "iowa", "kansas", "kentucky",
                "maine", "maryland", "massachusetts", "michigan", "minnesota",
                "mississippi", "missouri", "montana", "nebraska", "nevada",
                "new hampshire", "new jersey", "new mexico", "north carolina",
                "north dakota", "ohio", "oregon", "pennsylvania", "south carolina",
                "south dakota", "tennessee", "texas", "utah", "vermont",
                "virginia", "west virginia", "wisconsin", "wyoming",
            ],
            "notes": f"Trust purports to be governed by {governing_state} law",
        }

        validity_score = max(0.0, min(100.0, validity_score))

        # Build recommendations
        if validity_score < 70:
            recommendations.insert(0, "🚨 Trust has significant structural deficiencies — consider redrafting")
        elif validity_score < 85:
            recommendations.insert(0, "⚠️ Trust has moderate deficiencies — amendment recommended")
        else:
            recommendations.insert(0, "✓ Trust is generally well-structured — address minor gaps noted")

        return TrustAudit(
            trust_type_detected=trust_type_detected,
            validity_score=validity_score,
            vulnerabilities=vulnerabilities,
            strengths=strengths,
            recommendations=recommendations,
            jurisdiction_compliance=jurisdiction_compliance,
            missing_provisions=missing_provisions,
            potential_tax_issues=potential_tax_issues,
            estimated_exposure="Review with qualified trust attorney; exposure depends on jurisdiction and specific facts",
        )

    def compare_strategies(self, strategies: List[str]) -> StrategyComparison:
        """
        Compare multiple trust strategies and recommend the best one.

        Args:
            strategies: List of strategy descriptions (e.g., ["DAPT in Nevada", "Offshore Trust in Cook Islands"])
        """
        scores: Dict[str, float] = {}
        opinions: List[Opinion] = []

        strategy_features = {
            "dapt": {"ap": 75, "tax": 70, "cost": 75, "complexity": 70, "privacy": 70},
            "offshore": {"ap": 95, "tax": 50, "cost": 30, "complexity": 30, "privacy": 80},
            "cook islands": {"ap": 98, "tax": 45, "cost": 25, "complexity": 25, "privacy": 80},
            "nevis": {"ap": 90, "tax": 45, "cost": 40, "complexity": 30, "privacy": 80},
            "nevada": {"ap": 80, "tax": 80, "cost": 65, "complexity": 60, "privacy": 75},
            "south dakota": {"ap": 85, "tax": 85, "cost": 60, "complexity": 60, "privacy": 85},
            "alaska": {"ap": 75, "tax": 80, "cost": 65, "complexity": 65, "privacy": 70},
            "revocable": {"ap": 10, "tax": 20, "cost": 90, "complexity": 90, "privacy": 60},
            "irrevocable": {"ap": 50, "tax": 70, "cost": 75, "complexity": 70, "privacy": 65},
            "dynasty": {"ap": 60, "tax": 85, "cost": 50, "complexity": 40, "privacy": 70},
            "slat": {"ap": 55, "tax": 85, "cost": 60, "complexity": 55, "privacy": 65},
            "idgt": {"ap": 55, "tax": 90, "cost": 55, "complexity": 40, "privacy": 65},
            "charitable remainder": {"ap": 20, "tax": 88, "cost": 55, "complexity": 45, "privacy": 60},
            "llc": {"ap": 65, "tax": 70, "cost": 80, "complexity": 75, "privacy": 70},
        }

        weights = {"ap": 0.30, "tax": 0.25, "cost": 0.15, "complexity": 0.15, "privacy": 0.15}

        for strategy in strategies:
            strategy_lower = strategy.lower()
            matched_features = {"ap": 50, "tax": 50, "cost": 50, "complexity": 50, "privacy": 50}
            for feature_key, feature_vals in strategy_features.items():
                if feature_key in strategy_lower:
                    matched_features = feature_vals
                    break

            weighted_score = sum(
                matched_features[dim] * weight
                for dim, weight in weights.items()
            )
            scores[strategy] = round(weighted_score, 2)

            # Generate opinion for each strategy
            ap_val = matched_features["ap"]
            tax_val = matched_features["tax"]
            opinions.append(Opinion(
                agent_role="Composite Analysis",
                position="Suitable" if weighted_score > 65 else "Caution",
                reasoning=(
                    f"Strategy scores: Asset Protection={ap_val}/100, "
                    f"Tax Efficiency={tax_val}/100, "
                    f"Cost Efficiency={matched_features['cost']}/100, "
                    f"Privacy={matched_features['privacy']}/100"
                ),
                score=weighted_score,
                key_concerns=[
                    "Cost-benefit analysis required" if matched_features["cost"] < 50 else "Cost is acceptable",
                    "High reporting burden" if "offshore" in strategy_lower else "Standard compliance requirements",
                ],
            ))

        winner = max(scores, key=lambda k: scores[k])
        caveats = [
            "Analysis based on general scoring; actual suitability depends on specific client facts",
            "Consult a qualified trust attorney and tax advisor before implementing any strategy",
            "Fraudulent transfer laws may affect strategy effectiveness if creditor threats exist",
        ]

        return StrategyComparison(
            strategies=strategies,
            winner=winner,
            winner_score=scores[winner],
            scores=scores,
            opinions=opinions,
            recommendation=f"Based on weighted scoring analysis, '{winner}' (score: {scores[winner]:.1f}/100) offers the best balance of protection, tax efficiency, and cost.",
            caveats=caveats,
        )
