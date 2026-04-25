"""
Asset Protection Planner
========================
Comprehensive asset protection planning engine. Analyzes assets, threats,
and goals to build layered protection strategies using trusts, LLCs, and
other legal structures.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re


@dataclass
class Asset:
    """An asset to be protected."""
    asset_type: str       # real_estate, business_interests, investment_accounts, etc.
    description: str
    estimated_value: float
    current_owner: str
    state: str            # State where asset is located / owner resides
    current_protection: Optional[str] = None
    is_titled: bool = True   # Whether it's a titled asset


@dataclass
class ProtectionPlan:
    """Complete asset protection plan for a client."""
    recommended_structures: List[Dict[str, Any]]
    implementation_order: List[str]
    estimated_protection_level: float    # 0-100
    tax_impact: str
    cost_estimate: str
    timeline_months: int
    key_risks: List[str]
    synergies_with_existing: List[str]
    total_assets_analyzed: float
    priority_actions: List[str]
    long_term_maintenance: List[str]


@dataclass
class ProtectionAudit:
    """Audit of existing protection structures."""
    structures_analyzed: List[str]
    overall_protection_score: float    # 0-100
    gaps_identified: List[str]
    strengths: List[str]
    recommendations: List[str]
    immediate_actions: List[str]
    cost_to_remedy_gaps: str


class AssetProtectionPlanner:
    """
    Builds comprehensive, layered asset protection strategies.
    Analyzes assets by type, threats, and goals to recommend optimal structures.
    """

    # Asset protection scores by structure type
    STRUCTURE_PROTECTION_SCORES: Dict[str, float] = {
        "revocable_trust": 5.0,        # No protection (revocable)
        "irrevocable_trust": 55.0,     # Moderate (removes from estate but may not protect from creditors)
        "dapt_domestic": 72.0,         # Domestic APT
        "dapt_nevada": 78.0,           # Nevada DAPT (2-year SOL)
        "dapt_south_dakota": 80.0,     # SD DAPT
        "offshore_trust_nevis": 88.0,  # Nevis offshore
        "offshore_trust_cook": 95.0,   # Cook Islands
        "single_member_llc": 35.0,     # Low in many states
        "multi_member_llc": 60.0,      # Charging order protection
        "wyoming_llc": 75.0,           # Best charging order protection
        "fllc": 65.0,                  # Family Limited LLC
        "flp": 60.0,                   # Family Limited Partnership
        "land_trust": 40.0,            # Privacy but limited protection
        "ilit": 70.0,                  # Irrevocable Life Insurance Trust
        "dynasty_trust": 75.0,         # Dynasty trust
        "llc_plus_trust": 85.0,        # Combined LLC + Trust
        "offshore_llc_plus_trust": 95.0, # Offshore LLC + Trust
        "homestead_exemption": 80.0,   # State homestead (FL, TX unlimited)
        "retirement_accounts": 70.0,   # Federal/state protection for retirement
        "tenancy_by_entirety": 65.0,   # Available in some states for married couples
    }

    # Asset type → recommended primary structure
    ASSET_STRUCTURE_MAP: Dict[str, List[str]] = {
        "real_estate": [
            "land_trust",           # Privacy first
            "llc",                  # Liability shield
            "llc_plus_trust",       # Combined for protection
            "homestead_exemption",  # For primary residence
        ],
        "business_interests": [
            "wyoming_llc",          # Best charging order protection
            "fllc",                 # Family LLC for valuation discounts
            "flp",                  # Family LP for discounts
            "dapt_south_dakota",    # APT as overlay
        ],
        "investment_accounts": [
            "irrevocable_trust",    # Remove from estate
            "dapt_south_dakota",    # Creditor protection
            "dynasty_trust",        # Multi-generational
            "offshore_trust_cook",  # Maximum protection
        ],
        "retirement_accounts": [
            "retirement_accounts",  # Already protected federally
            "irrevocable_trust",    # Stretch IRA replacement
            "special_needs_trust",  # For disabled beneficiaries
        ],
        "intellectual_property": [
            "wyoming_llc",          # Hold IP in LLC
            "irrevocable_trust",    # Trust holds LLC
            "offshore_trust_cook",  # Maximum protection for high-value IP
        ],
        "cash": [
            "dapt_south_dakota",    # Best domestic
            "offshore_trust_cook",  # If extreme threat
            "irrevocable_trust",    # Remove from estate
        ],
        "cryptocurrency": [
            "wyoming_llc",          # Wyoming LLC (crypto-friendly)
            "dapt_south_dakota",    # Through trust
            "offshore_trust_cook",  # Maximum protection
        ],
        "precious_metals": [
            "offshore_trust_cook",  # Physical storage offshore
            "dapt_south_dakota",    # Domestic trust
            "wyoming_llc",          # LLC ownership
        ],
        "life_insurance": [
            "ilit",                 # Irrevocable Life Insurance Trust
            "dynasty_trust",        # Dynasty trust ILIT
        ],
    }

    # Threat type → recommended structures
    THREAT_STRUCTURE_MAP: Dict[str, List[str]] = {
        "lawsuits": [
            "wyoming_llc",
            "dapt_south_dakota",
            "offshore_trust_cook",
            "llc_plus_trust",
        ],
        "divorce": [
            "prenuptial_agreement",  # Note: not a trust but recommended
            "dapt_south_dakota",
            "irrevocable_trust",
            "dynasty_trust",
        ],
        "creditors": [
            "dapt_nevada",
            "dapt_south_dakota",
            "offshore_trust_nevis",
            "offshore_trust_cook",
        ],
        "bankruptcy": [
            "offshore_trust_cook",   # Best against bankruptcy
            "dapt_south_dakota",     # Domestic APT (limited vs bankruptcy)
            "retirement_accounts",   # Protected in bankruptcy
            "homestead_exemption",   # Protected in bankruptcy (state limits vary)
        ],
        "estate_taxes": [
            "dynasty_trust",
            "ilit",
            "idgt",
            "slat",
            "charitable_remainder_trust",
        ],
        "gift_taxes": [
            "annual_exclusion_gifting",
            "529_plan",
            "idgt",
            "grat",
        ],
        "medicaid_spenddown": [
            "medicaid_asset_protection_trust",
            "irrevocable_trust",
            "special_needs_trust",
        ],
        "professional_liability": [
            "dapt_nevada",
            "dapt_south_dakota",
            "wyoming_llc",
            "offshore_trust_cook",
        ],
    }

    # Layered defense strategies
    LAYERED_STRATEGIES: Dict[str, Dict[str, Any]] = {
        "moderate_protection": {
            "name": "Moderate Domestic Protection",
            "description": "LLC + Revocable Trust for probate avoidance and moderate protection",
            "structures": ["Wyoming LLC (operating entity)", "Revocable Living Trust (holding entity)", "Umbrella Insurance"],
            "protection_score": 55.0,
            "best_for": ["net_worth < $2M", "low_threat", "standard_professional"],
            "cost": "$5,000–$15,000 setup",
        },
        "strong_domestic": {
            "name": "Strong Domestic Protection",
            "description": "DAPT + LLC layered structure",
            "structures": [
                "Wyoming LLC (operating/holding entity)",
                "South Dakota DAPT (holding LLC interests)",
                "Irrevocable Trust (estate planning overlay)",
                "Umbrella Insurance",
            ],
            "protection_score": 82.0,
            "best_for": ["net_worth $2M-$10M", "medium_threat", "physician_attorney_business_owner"],
            "cost": "$15,000–$40,000 setup + annual admin",
        },
        "maximum_domestic": {
            "name": "Maximum Domestic Protection Stack",
            "description": "Layered LLC + DAPT + Dynasty Trust in best states",
            "structures": [
                "Wyoming LLC #1 (operating company)",
                "Wyoming LLC #2 (holding company, owns LLC #1)",
                "South Dakota Dynasty DAPT (owns LLC #2)",
                "Irrevocable Life Insurance Trust (ILIT)",
                "Family Limited Partnership (for valuation discounts)",
                "Umbrella Insurance",
            ],
            "protection_score": 90.0,
            "best_for": ["net_worth $5M-$25M", "high_threat", "ultra-high_risk_professional"],
            "cost": "$40,000–$100,000 setup + ongoing admin",
        },
        "offshore_nuclear": {
            "name": "Offshore Nuclear Option",
            "description": "Cook Islands Trust + Nevis LLC + Domestic DAPT",
            "structures": [
                "Cook Islands International Trust (outer layer)",
                "Nevis LLC (held by Cook Islands Trust)",
                "South Dakota DAPT (domestic backup layer)",
                "Wyoming LLC (operating entity)",
                "ILIT for life insurance",
            ],
            "protection_score": 97.0,
            "best_for": ["net_worth > $5M", "extreme_threat", "active_litigation_risk"],
            "cost": "$50,000–$150,000 setup + $15,000–$30,000/year",
        },
        "real_estate_specific": {
            "name": "Real Estate Protection Stack",
            "description": "Land trust + LLC + Trust overlay for real estate portfolios",
            "structures": [
                "Illinois-style Land Trust for each property (privacy)",
                "Wyoming LLC (holds beneficial interests in land trusts)",
                "Irrevocable Trust or DAPT (holds LLC membership interests)",
                "Homestead exemption for primary residence",
                "Umbrella and commercial property insurance",
            ],
            "protection_score": 80.0,
            "best_for": ["real_estate_investors", "landlords", "commercial_property_owners"],
            "cost": "$10,000–$30,000 setup per property + admin",
        },
        "physician_protection": {
            "name": "Medical Professional Protection Plan",
            "description": "Customized for physicians with malpractice exposure",
            "structures": [
                "Professional Corporation or PLLC for practice",
                "Wyoming LLC (holds personal assets, separate from practice)",
                "Nevada or South Dakota DAPT (holds LLC)",
                "ILIT (life insurance outside estate)",
                "Qualified Retirement Plans (401k, profit-sharing — federally protected)",
                "Homestead exemption maximized",
                "Offshore backup (Cook Islands) for net worth > $5M",
            ],
            "protection_score": 88.0,
            "best_for": ["physicians", "surgeons", "anesthesiologists", "high-risk_specialists"],
            "cost": "$20,000–$60,000 setup depending on offshore component",
        },
    }

    def create_protection_plan(
        self,
        assets: List[Asset],
        threats: List[str],
        goals: List[str],
    ) -> ProtectionPlan:
        """
        Create a comprehensive asset protection plan.

        Args:
            assets: List of Asset objects to protect
            threats: List of threat types (lawsuits, divorce, creditors, etc.)
            goals: List of protection goals (estate_tax_reduction, probate_avoidance, etc.)
        """
        total_value = sum(a.estimated_value for a in assets)
        asset_types = list(set(a.asset_type for a in assets))
        threat_set = set(t.lower() for t in threats)
        goal_set = set(g.lower() for g in goals)

        # Determine threat level
        threat_level = "low"
        if len(threat_set) >= 3 or "lawsuit" in threat_set or "professional_liability" in threat_set:
            threat_level = "high"
        elif len(threat_set) >= 1:
            threat_level = "medium"
        if total_value > 10_000_000:
            threat_level = "high" if threat_level == "medium" else threat_level

        # Select appropriate layered strategy
        if total_value > 5_000_000 and ("lawsuits" in threat_set or "professional_liability" in threat_set):
            base_strategy = self.LAYERED_STRATEGIES["maximum_domestic"]
            if total_value > 10_000_000:
                base_strategy = self.LAYERED_STRATEGIES["offshore_nuclear"]
        elif "real_estate" in asset_types and len(asset_types) == 1:
            base_strategy = self.LAYERED_STRATEGIES["real_estate_specific"]
        elif threat_level == "high" and total_value > 2_000_000:
            base_strategy = self.LAYERED_STRATEGIES["strong_domestic"]
        else:
            base_strategy = self.LAYERED_STRATEGIES["moderate_protection"]

        # Build recommended structures list
        recommended_structures = []
        seen_structures = set()

        # Threat-specific structures
        for threat in threats:
            threat_lower = threat.lower().replace(" ", "_")
            for struct in self.THREAT_STRUCTURE_MAP.get(threat_lower, []):
                if struct not in seen_structures:
                    seen_structures.add(struct)
                    protection = self.STRUCTURE_PROTECTION_SCORES.get(struct, 50.0)
                    recommended_structures.append({
                        "structure": struct,
                        "purpose": f"Protection against: {threat}",
                        "protection_score": protection,
                        "priority": "High" if protection > 75 else "Medium",
                    })

        # Asset-specific structures
        for asset in assets:
            for struct in self.ASSET_STRUCTURE_MAP.get(asset.asset_type, [])[:2]:
                if struct not in seen_structures:
                    seen_structures.add(struct)
                    protection = self.STRUCTURE_PROTECTION_SCORES.get(struct, 50.0)
                    recommended_structures.append({
                        "structure": struct,
                        "purpose": f"Protect {asset.asset_type}: {asset.description}",
                        "protection_score": protection,
                        "priority": "Medium",
                    })

        # Goal-based structures
        if "estate_tax_reduction" in goal_set or "estate_planning" in goal_set:
            for struct in ["dynasty_trust", "ilit", "idgt"]:
                if struct not in seen_structures:
                    seen_structures.add(struct)
                    recommended_structures.append({
                        "structure": struct,
                        "purpose": "Estate tax reduction",
                        "protection_score": self.STRUCTURE_PROTECTION_SCORES.get(struct, 60.0),
                        "priority": "Medium",
                    })

        if "probate_avoidance" in goal_set:
            if "revocable_trust" not in seen_structures:
                seen_structures.add("revocable_trust")
                recommended_structures.append({
                    "structure": "revocable_trust",
                    "purpose": "Probate avoidance and incapacity planning",
                    "protection_score": 5.0,
                    "priority": "High",
                })

        # Sort by protection score
        recommended_structures.sort(key=lambda x: x["protection_score"], reverse=True)

        # Calculate overall protection score
        if recommended_structures:
            top_3_scores = [s["protection_score"] for s in recommended_structures[:3]]
            overall_protection = min(100.0, sum(top_3_scores) / len(top_3_scores) * 1.1)
        else:
            overall_protection = 10.0

        # Implementation order
        impl_order = [
            "Step 1: Execute prenuptial or postnuptial agreement (if married and divorce risk)",
            "Step 2: Maximize retirement account contributions (federally protected)",
            "Step 3: Ensure homestead exemption is perfected for primary residence",
            "Step 4: Form Wyoming LLC(s) for operating businesses/investments",
            "Step 5: Establish Revocable Living Trust (probate avoidance baseline)",
            "Step 6: Establish DAPT (Nevada/South Dakota) and transfer LLC interests",
            "Step 7: Fund Irrevocable Life Insurance Trust with life insurance policies",
            "Step 8: Implement dynasty trust for estate planning layer",
            "Step 9: Consider offshore structure if threat level warrants",
        ]

        # Filter to relevant steps
        relevant_steps = [s for s in impl_order if any(
            kw in s.lower() for kw in [t.lower() for t in threats] + [a.asset_type for a in assets]
        )]
        if not relevant_steps:
            relevant_steps = impl_order[:5]

        # Key risks
        key_risks = []
        if "lawsuits" in threat_set or "creditors" in threat_set:
            key_risks.append("⚠️ Fraudulent transfer: All transfers must be made while solvent and not during pending litigation")
        if "divorce" in threat_set:
            key_risks.append("⚠️ SLAT divorce risk: If beneficiary spouse divorces donor, assets may be accessible")
        if "offshore" in str(recommended_structures):
            key_risks.append("⚠️ Offshore reporting: Form 3520, FBAR, and FATCA compliance is mandatory")
        key_risks.append("Insurance gap: Ensure umbrella insurance covers periods before structures are funded")
        key_risks.append("Commingling: Keep personal and trust/LLC finances strictly separate")

        # Synergies
        synergies = []
        for asset in assets:
            if asset.current_protection:
                synergies.append(f"Existing {asset.current_protection} for {asset.description} can be integrated into new structure")

        # Tax impact
        tax_impacts = []
        if any("dapt" in s["structure"] for s in recommended_structures):
            tax_impacts.append("DAPT: Grantor trust for income tax — you continue to pay taxes on trust income")
        if any("dynasty" in s["structure"] for s in recommended_structures):
            tax_impacts.append("Dynasty Trust: Allocate GST exemption ($13.61M/person in 2024)")
        if any("ilit" in s["structure"] for s in recommended_structures):
            tax_impacts.append("ILIT: Life insurance proceeds excluded from estate — massive leverage")
        tax_impact = "; ".join(tax_impacts) if tax_impacts else "Standard tax treatment applies — consult CPA"

        # Cost and timeline
        if total_value > 10_000_000:
            cost_estimate = "$75,000–$200,000 setup + $20,000–$50,000/year maintenance"
            timeline_months = 6
        elif total_value > 3_000_000:
            cost_estimate = "$25,000–$75,000 setup + $10,000–$20,000/year"
            timeline_months = 4
        elif total_value > 500_000:
            cost_estimate = "$10,000–$30,000 setup + $3,000–$8,000/year"
            timeline_months = 3
        else:
            cost_estimate = "$3,000–$10,000 setup + $1,000–$3,000/year"
            timeline_months = 2

        priority_actions = [
            "Conduct solvency analysis and fraudulent transfer risk assessment BEFORE any transfers",
            "Meet with trust attorney and CPA simultaneously to coordinate legal and tax strategy",
            "Obtain personal umbrella insurance immediately as a low-cost, fast first layer",
            f"Form Wyoming LLC within {30 if threat_level == 'high' else 60} days",
        ]

        long_term_maintenance = [
            "Annual trust review with attorney to ensure compliance with changing laws",
            "Annual CPA meeting to address tax elections and reporting (especially offshore)",
            "Maintain corporate/trust formalities — separate accounts, annual minutes",
            "Continue UCC filings and renewals (5-year expiration)",
            "Update beneficiary designations on retirement accounts and insurance annually",
            "Review asset transfers for GST exemption allocation",
        ]

        return ProtectionPlan(
            recommended_structures=recommended_structures,
            implementation_order=relevant_steps if relevant_steps else impl_order[:4],
            estimated_protection_level=overall_protection,
            tax_impact=tax_impact,
            cost_estimate=cost_estimate,
            timeline_months=timeline_months,
            key_risks=key_risks,
            synergies_with_existing=synergies,
            total_assets_analyzed=total_value,
            priority_actions=priority_actions,
            long_term_maintenance=long_term_maintenance,
        )

    def evaluate_existing_protection(self, current_structures: List[str]) -> ProtectionAudit:
        """
        Audit existing protection structures and identify gaps.

        Args:
            current_structures: List of existing structures (e.g., ["Wyoming LLC", "Revocable Trust"])
        """
        strengths = []
        gaps = []
        recommendations = []
        immediate_actions = []

        structures_lower = [s.lower() for s in current_structures]

        # Calculate overall score
        total_score = 0.0
        matched_structures = []

        for struct_name, score in self.STRUCTURE_PROTECTION_SCORES.items():
            struct_words = struct_name.replace("_", " ")
            if any(struct_words in sl or struct_name in sl for sl in structures_lower):
                total_score += score * 0.15  # Weight — stacking increases protection
                matched_structures.append((struct_name, score))
                strengths.append(f"✓ {struct_name.replace('_', ' ').title()} (protection score: {score}/100)")

        # Cap total score
        overall_score = min(95.0, total_score) if matched_structures else 5.0

        # Gap analysis
        has_llc = any("llc" in s for s in structures_lower)
        has_trust = any("trust" in s for s in structures_lower)
        has_irrev = any("irrevocable" in s or "irrev" in s for s in structures_lower)
        has_dapt = any("dapt" in s or "asset protection" in s for s in structures_lower)
        has_ilit = any("ilit" in s or "life insurance trust" in s for s in structures_lower)
        has_insurance = any("insurance" in s or "umbrella" in s for s in structures_lower)

        if not has_llc:
            gaps.append("No LLC structure — personal and business assets are exposed")
            recommendations.append("Form Wyoming LLC to provide charging order protection and liability shield")
            immediate_actions.append("Form Wyoming LLC immediately — can be done in 48 hours, ~$500")

        if not has_trust:
            gaps.append("No trust structure — assets subject to probate and lack privacy")
            recommendations.append("Establish Revocable Living Trust for probate avoidance")
            immediate_actions.append("Execute Revocable Living Trust with successor trustee provisions")

        if has_trust and not has_irrev:
            gaps.append("Only revocable trust present — no creditor protection from trust")
            recommendations.append("Consider irrevocable trust or DAPT overlay for creditor protection")

        if not has_dapt and overall_score < 70:
            gaps.append("No Domestic Asset Protection Trust — significant creditor exposure")
            recommendations.append("Establish South Dakota or Nevada DAPT to protect liquid assets and LLC interests")

        if not has_ilit:
            gaps.append("Life insurance policies likely in taxable estate — ILIT recommended")
            recommendations.append("Transfer existing life insurance to ILIT or purchase new policy through ILIT")
            immediate_actions.append("Review life insurance policies — if owned personally, create ILIT within 3 years of death to exclude")

        if not has_insurance:
            gaps.append("No umbrella insurance detected — first line of defense is missing")
            immediate_actions.append("Purchase $2M-$5M umbrella insurance policy immediately — cheap and fast first layer")

        cost_to_remedy = "$0" if not gaps else (
            "$50,000–$150,000" if len(gaps) >= 4 else
            "$20,000–$50,000" if len(gaps) >= 2 else
            "$5,000–$20,000"
        )

        return ProtectionAudit(
            structures_analyzed=current_structures,
            overall_protection_score=overall_score,
            gaps_identified=gaps,
            strengths=strengths,
            recommendations=recommendations,
            immediate_actions=immediate_actions if immediate_actions else ["Current protection appears adequate — schedule annual review"],
            cost_to_remedy_gaps=cost_to_remedy,
        )

    def calculate_asset_protection_score(self, structure_description: str) -> float:
        """
        Calculate the asset protection score for a described structure.

        Args:
            structure_description: Natural language description of the structure
        """
        desc_lower = structure_description.lower()
        score = 0.0
        max_single = 0.0

        # Score each recognized structure
        for struct_name, struct_score in self.STRUCTURE_PROTECTION_SCORES.items():
            struct_words = struct_name.replace("_", " ")
            if struct_words in desc_lower or struct_name.split("_")[0] in desc_lower:
                # Each additional structure adds diminishing returns
                score += struct_score * (0.5 if score > 0 else 1.0)
                max_single = max(max_single, struct_score)

        # Keyword bonuses
        if "offshore" in desc_lower and "cook" in desc_lower:
            score = max(score, 95.0)
        elif "offshore" in desc_lower:
            score = max(score, 85.0)
        if "layered" in desc_lower or "combination" in desc_lower or "stack" in desc_lower:
            score = min(100.0, score * 1.1)

        # Penalties
        if "revocable" in desc_lower and "irrevocable" not in desc_lower:
            score = min(score, 30.0)  # Revocable provides minimal protection
        if "single member llc" in desc_lower and "wyoming" not in desc_lower:
            score = min(score, 40.0)  # Many states have weak charging order for SMLLC

        return min(100.0, max(0.0, score if score > 0 else max_single * 0.5))
