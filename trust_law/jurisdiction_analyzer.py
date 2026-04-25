"""
Jurisdiction Analyzer
=====================
Optimal jurisdiction finder, comparator, and migration planner for trust law.
Covers all major domestic and international trust jurisdictions with
comprehensive scoring and analysis.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re


@dataclass
class JurisdictionScore:
    """Score for a single jurisdiction."""
    name: str
    full_name: str
    total_score: float
    breakdown: Dict[str, float]
    key_strengths: List[str]
    key_weaknesses: List[str]
    recommendation_notes: str


@dataclass
class JurisdictionRanking:
    """Ranked list of jurisdictions for given requirements."""
    requirements_summary: str
    ranked_jurisdictions: List[JurisdictionScore]
    top_recommendation: str
    rationale: str
    alternative_options: List[str]
    implementation_notes: List[str]


@dataclass
class Comparison:
    """Side-by-side comparison of two jurisdictions."""
    jurisdiction_1: str
    jurisdiction_2: str
    trust_type: str
    winner: str
    winner_reasoning: str
    head_to_head: Dict[str, Dict[str, Any]]
    scenarios_where_j2_wins: List[str]
    scenarios_where_j1_wins: List[str]


@dataclass
class OffshoreOption:
    """An offshore jurisdiction option."""
    jurisdiction: str
    protection_level: str
    estimated_setup_cost: str
    annual_maintenance_cost: str
    us_reporting_requirements: List[str]
    best_for: List[str]
    risks: List[str]
    statute_of_limitations: str


@dataclass
class MigrationPlan:
    """Plan for migrating a trust to a different jurisdiction."""
    current_state: str
    target_state: str
    trust_type: str
    migration_method: str
    steps: List[str]
    estimated_cost: str
    timeline_weeks: int
    risks: List[str]
    benefits: List[str]
    legal_requirements: List[str]


class JurisdictionAnalyzer:
    """
    Comprehensive trust jurisdiction analysis engine.
    Evaluates, compares, and recommends jurisdictions based on client needs.
    """

    # Comprehensive jurisdiction data matrix
    JURISDICTION_DATA: Dict[str, Dict[str, Any]] = {
        "south_dakota": {
            "full_name": "South Dakota",
            "type": "domestic",
            "asset_protection": 9.5,
            "tax_efficiency": 10.0,
            "dynasty_trust": 10.0,
            "privacy": 9.5,
            "ease_of_admin": 8.0,
            "cost_efficiency": 7.0,
            "self_settled": True,
            "dynasty_allowed": True,
            "decanting": True,
            "state_income_tax": False,
            "perpetuities": "Abolished — unlimited duration",
            "sol_fraudulent_transfer": "2 years (§55-16-14)",
            "directed_trust_statute": True,
            "family_office_friendly": True,
            "statutes": ["SDCL 55-1A", "SDCL 55-16", "SDCL 43-5-1"],
            "strengths": [
                "Unlimited trust duration (perpetuities abolished)",
                "No state income tax on trust income",
                "Best directed trust statute in US",
                "Strong privacy laws (no public disclosure of trust assets)",
                "Decanting statute allows modification of irrevocable trusts",
                "Institutional trust company infrastructure",
                "2-year SOL for self-settled trusts",
                "Self-settled asset protection trusts permitted",
            ],
            "weaknesses": [
                "Must have SD trustee with SD presence",
                "Remote jurisdiction — not convenient for all clients",
                "Bankruptcy court may limit DAPT effectiveness",
            ],
            "notes": "Preeminent US trust jurisdiction. Over $500B in trust assets.",
        },
        "nevada": {
            "full_name": "Nevada",
            "type": "domestic",
            "asset_protection": 9.0,
            "tax_efficiency": 9.5,
            "dynasty_trust": 8.5,
            "privacy": 8.5,
            "ease_of_admin": 8.5,
            "cost_efficiency": 7.5,
            "self_settled": True,
            "dynasty_allowed": True,
            "decanting": True,
            "state_income_tax": False,
            "perpetuities": "365 years",
            "sol_fraudulent_transfer": "2 years (shortest in US)",
            "directed_trust_statute": True,
            "family_office_friendly": True,
            "statutes": ["NRS 166.015", "NRS 163.185", "NRS 163.556"],
            "strengths": [
                "Shortest fraudulent transfer SOL in US (2 years from transfer)",
                "No state income tax",
                "Strong charging order protection for LLCs",
                "No exception creditors except child support/alimony",
                "Self-settled trusts permitted",
                "Decanting statute",
                "Directed trust statute",
            ],
            "weaknesses": [
                "365-year perpetuities limit (less than SD unlimited)",
                "Less institutional trust infrastructure than SD",
                "Bankruptcy court jurisdiction still applies",
            ],
            "notes": "2-year SOL makes Nevada among the strongest domestic APT states.",
        },
        "alaska": {
            "full_name": "Alaska",
            "type": "domestic",
            "asset_protection": 8.0,
            "tax_efficiency": 9.5,
            "dynasty_trust": 9.0,
            "privacy": 7.5,
            "ease_of_admin": 7.5,
            "cost_efficiency": 7.5,
            "self_settled": True,
            "dynasty_allowed": True,
            "decanting": True,
            "state_income_tax": False,
            "perpetuities": "1000 years (effectively unlimited)",
            "sol_fraudulent_transfer": "4 years",
            "directed_trust_statute": True,
            "family_office_friendly": True,
            "statutes": ["AS 34.40.110", "AS 13.36.035"],
            "strengths": [
                "First US state to allow self-settled APTs (1997)",
                "No state income tax",
                "1000-year dynasty trust duration",
                "Decanting allowed",
                "Strong judicial system for trust disputes",
            ],
            "weaknesses": [
                "4-year SOL (longer than Nevada's 2 years)",
                "Geographic remoteness",
                "Less institutional infrastructure than SD",
                "Bankruptcy still poses risk",
            ],
            "notes": "Pioneer DAPT state; Alaska Trust Act widely respected.",
        },
        "delaware": {
            "full_name": "Delaware",
            "type": "domestic",
            "asset_protection": 8.0,
            "tax_efficiency": 9.0,
            "dynasty_trust": 9.0,
            "privacy": 8.0,
            "ease_of_admin": 8.5,
            "cost_efficiency": 6.5,
            "self_settled": True,
            "dynasty_allowed": True,
            "decanting": True,
            "state_income_tax": False,
            "perpetuities": "Repealed for personal property trusts",
            "sol_fraudulent_transfer": "4 years",
            "directed_trust_statute": True,
            "family_office_friendly": True,
            "statutes": ["12 Del. C. §3570", "12 Del. C. §3801"],
            "strengths": [
                "No DE income tax for non-resident trust income",
                "Excellent directed trust statute",
                "Well-developed trust law jurisprudence",
                "Superior Chancery Court for trust disputes",
                "Delaware Statutory Trust (DST) for 1031 exchanges",
                "Self-settled trusts permitted",
            ],
            "weaknesses": [
                "4-year SOL for fraudulent transfers",
                "Higher professional costs",
                "Less privacy than South Dakota",
            ],
            "notes": "Superior Court infrastructure; excellent for complex trust litigation.",
        },
        "wyoming": {
            "full_name": "Wyoming",
            "type": "domestic",
            "asset_protection": 8.5,
            "tax_efficiency": 10.0,
            "dynasty_trust": 8.5,
            "privacy": 9.5,
            "ease_of_admin": 8.5,
            "cost_efficiency": 8.5,
            "self_settled": True,
            "dynasty_allowed": True,
            "decanting": True,
            "state_income_tax": False,
            "perpetuities": "1000 years",
            "sol_fraudulent_transfer": "4 years",
            "directed_trust_statute": True,
            "family_office_friendly": True,
            "statutes": ["Wyo. Stat. 4-10-101", "Wyo. Stat. 17-29-101"],
            "strengths": [
                "No state income tax",
                "Strongest US charging order protection (exclusive remedy)",
                "Excellent LLC/trust combination structures",
                "High privacy — no public member/trust records",
                "Low costs and fees",
                "Self-settled trusts allowed",
                "New trust-friendly legislation growing rapidly",
            ],
            "weaknesses": [
                "Newer trust jurisdiction — less case law",
                "Smaller institutional trust company presence",
                "4-year SOL",
            ],
            "notes": "Rising star in domestic trust jurisdictions; excellent LLC charging order protection.",
        },
        "cook_islands": {
            "full_name": "Cook Islands (South Pacific)",
            "type": "offshore",
            "asset_protection": 10.0,
            "tax_efficiency": 6.0,
            "dynasty_trust": 9.0,
            "privacy": 9.0,
            "ease_of_admin": 5.0,
            "cost_efficiency": 3.0,
            "self_settled": True,
            "dynasty_allowed": True,
            "decanting": True,
            "state_income_tax": False,
            "perpetuities": "None",
            "sol_fraudulent_transfer": "2 years (from transfer date)",
            "directed_trust_statute": True,
            "family_office_friendly": True,
            "statutes": ["International Trusts Act 1984", "Amendment Acts through 2004"],
            "strengths": [
                "Does NOT enforce US court judgments",
                "Creditor must re-litigate from scratch in Cook Islands",
                "2-year SOL even for offshore transfers",
                "High burden of proof for fraudulent transfer (beyond reasonable doubt in some cases)",
                "Established track record of protecting US clients",
                "No Cook Islands tax on offshore income",
            ],
            "weaknesses": [
                "US grantor faces contempt risk if court orders repatriation",
                "FBAR, Form 3520, FATCA reporting required",
                "High costs: $25,000-$60,000 setup, $10,000-$30,000/year",
                "Reputational concerns",
                "Geographic remoteness creates practical challenges",
            ],
            "notes": "Gold standard for asset protection. Most tested offshore APT jurisdiction.",
        },
        "nevis": {
            "full_name": "Nevis, Federation of St. Kitts and Nevis",
            "type": "offshore",
            "asset_protection": 9.0,
            "tax_efficiency": 6.0,
            "dynasty_trust": 8.5,
            "privacy": 9.0,
            "ease_of_admin": 6.0,
            "cost_efficiency": 5.0,
            "self_settled": True,
            "dynasty_allowed": True,
            "decanting": True,
            "state_income_tax": False,
            "perpetuities": "None",
            "sol_fraudulent_transfer": "2 years",
            "directed_trust_statute": False,
            "family_office_friendly": True,
            "statutes": ["Nevis International Exempt Trust Ordinance 1994", "Nevis LLC Ordinance 1995"],
            "strengths": [
                "Creditor must post $25,000 bond before suing",
                "Does not enforce US judgments",
                "Nevis LLC provides additional creditor protection layer",
                "Lower cost than Cook Islands",
                "Multiform Foundation available",
                "2-year SOL",
            ],
            "weaknesses": [
                "Less tested than Cook Islands in US court challenges",
                "Smaller legal system",
                "Political risk in small island nation",
                "Full US reporting required",
            ],
            "notes": "Strong second-tier offshore option; excellent for LLC/trust combinations.",
        },
        "liechtenstein": {
            "full_name": "Principality of Liechtenstein",
            "type": "offshore",
            "asset_protection": 9.0,
            "tax_efficiency": 5.5,
            "dynasty_trust": 10.0,
            "privacy": 8.0,
            "ease_of_admin": 6.5,
            "cost_efficiency": 3.0,
            "self_settled": True,
            "dynasty_allowed": True,
            "decanting": True,
            "state_income_tax": False,
            "perpetuities": "None",
            "sol_fraudulent_transfer": "Varies",
            "directed_trust_statute": True,
            "family_office_friendly": True,
            "statutes": ["PGR Art. 552 et seq.", "Foundation Law 2009"],
            "strengths": [
                "Civil law Foundation structure provides unique flexibility",
                "Stable political and legal system",
                "No inheritance tax or capital gains tax",
                "Exceptional for multi-generational European family wealth",
                "Anstalt (establishment) — hybrid corporate/trust vehicle",
            ],
            "weaknesses": [
                "OECD CRS automatic information exchange (reduced privacy)",
                "Very high professional fees",
                "Civil law system unfamiliar to common law practitioners",
                "FATCA compliance required",
            ],
            "notes": "Premier European wealth management jurisdiction; foundation structure unique.",
        },
    }

    def find_optimal_jurisdiction(self, requirements: Dict[str, Any]) -> JurisdictionRanking:
        """
        Find the optimal trust jurisdiction based on client requirements.

        Args:
            requirements: Dict with keys:
                - asset_protection_priority (0-10)
                - tax_minimization (0-10)
                - dynasty_goals (0-10)
                - privacy_needs (0-10)
                - ease_of_administration (0-10)
                - budget (str: "low", "medium", "high", "unlimited")
                - offshore_acceptable (bool)
                - domestic_only (bool)
                - self_settled_needed (bool)
                - net_worth_millions (float)
                - threat_level (str: "low", "medium", "high", "extreme")
        """
        ap_weight = requirements.get("asset_protection_priority", 5) / 10
        tax_weight = requirements.get("tax_minimization", 5) / 10
        dynasty_weight = requirements.get("dynasty_goals", 3) / 10
        _pn = requirements.get("privacy_needs", 5)
        _pn_map = {"low": 2, "medium": 5, "moderate": 5, "high": 8, "extreme": 10, "critical": 10}
        if isinstance(_pn, str):
            _pn = _pn_map.get(_pn.lower(), 5)
        privacy_weight = _pn / 10
        admin_weight = requirements.get("ease_of_administration", 5) / 10
        budget = requirements.get("budget", "medium")
        offshore_ok = requirements.get("offshore_acceptable", False)
        domestic_only = requirements.get("domestic_only", False)
        self_settled = requirements.get("self_settled_needed", False)
        threat_level = requirements.get("threat_level", "medium")

        # Budget-to-cost score mapping
        cost_budget_map = {"low": 8, "medium": 6, "high": 4, "unlimited": 2}
        min_cost_score = cost_budget_map.get(budget, 6)

        # Threat-level adjustments to AP weight
        threat_ap_boost = {"low": 0, "medium": 0.1, "high": 0.2, "extreme": 0.35}
        ap_weight = min(1.0, ap_weight + threat_ap_boost.get(threat_level, 0))

        scored: List[JurisdictionScore] = []
        for jkey, jdata in self.JURISDICTION_DATA.items():
            # Filter based on requirements
            if domestic_only and jdata["type"] != "domestic":
                continue
            if not offshore_ok and jdata["type"] == "offshore":
                continue
            if self_settled and not jdata.get("self_settled"):
                continue

            # Cost filter
            if jdata["cost_efficiency"] < min_cost_score:
                continue  # Too expensive for budget

            # Calculate weighted score
            score = (
                jdata["asset_protection"] * ap_weight * 0.30 +
                jdata["tax_efficiency"] * tax_weight * 0.25 +
                jdata["dynasty_trust"] * dynasty_weight * 0.15 +
                jdata["privacy"] * privacy_weight * 0.15 +
                jdata["ease_of_admin"] * admin_weight * 0.10 +
                jdata["cost_efficiency"] * 0.05
            )

            # Normalize to 100
            max_possible = 10 * (ap_weight * 0.30 + tax_weight * 0.25 + dynasty_weight * 0.15 +
                                  privacy_weight * 0.15 + admin_weight * 0.10 + 0.05)
            normalized_score = (score / max_possible * 100) if max_possible > 0 else 0

            breakdown = {
                "asset_protection": round(jdata["asset_protection"] * ap_weight * 0.30 / max_possible * 100, 1) if max_possible else 0,
                "tax_efficiency": round(jdata["tax_efficiency"] * tax_weight * 0.25 / max_possible * 100, 1) if max_possible else 0,
                "dynasty_trust": round(jdata["dynasty_trust"] * dynasty_weight * 0.15 / max_possible * 100, 1) if max_possible else 0,
                "privacy": round(jdata["privacy"] * privacy_weight * 0.15 / max_possible * 100, 1) if max_possible else 0,
                "ease_of_admin": round(jdata["ease_of_admin"] * admin_weight * 0.10 / max_possible * 100, 1) if max_possible else 0,
            }

            scored.append(JurisdictionScore(
                name=jkey,
                full_name=jdata["full_name"],
                total_score=round(normalized_score, 2),
                breakdown=breakdown,
                key_strengths=jdata["strengths"][:3],
                key_weaknesses=jdata["weaknesses"][:2],
                recommendation_notes=jdata["notes"],
            ))

        scored.sort(key=lambda x: x.total_score, reverse=True)
        top = scored[0] if scored else None

        implementation_notes = [
            "Consult with a trust attorney licensed in the target jurisdiction before proceeding",
            "Conduct a fraudulent transfer analysis before any asset transfers",
            "Ensure proper trustee independence and jurisdiction nexus",
            "Set up a trust protector for ongoing oversight and flexibility",
        ]
        if any(j.name in ["cook_islands", "nevis", "liechtenstein"] for j in scored[:3]):
            implementation_notes.append("Offshore jurisdiction: ensure FBAR, Form 3520/3520-A, and FATCA compliance")

        return JurisdictionRanking(
            requirements_summary=f"AP Priority={requirements.get('asset_protection_priority',5)}/10, Tax={requirements.get('tax_minimization',5)}/10, Dynasty={requirements.get('dynasty_goals',3)}/10, Budget={budget}, Threat={threat_level}",
            ranked_jurisdictions=scored[:5],
            top_recommendation=top.full_name if top else "South Dakota (default)",
            rationale=f"{top.full_name} scores highest ({top.total_score:.1f}/100) for the given requirements. " + (top.recommendation_notes if top else "") ,
            alternative_options=[j.full_name for j in scored[1:4]],
            implementation_notes=implementation_notes,
        )

    def compare_state_laws(self, state1: str, state2: str, trust_type: str) -> Comparison:
        """Compare two jurisdictions for a specific trust type."""
        s1_key = state1.lower().replace(" ", "_")
        s2_key = state2.lower().replace(" ", "_")
        j1 = self.JURISDICTION_DATA.get(s1_key)
        j2 = self.JURISDICTION_DATA.get(s2_key)

        if not j1 or not j2:
            available = list(self.JURISDICTION_DATA.keys())
            return Comparison(
                jurisdiction_1=state1,
                jurisdiction_2=state2,
                trust_type=trust_type,
                winner="Unknown",
                winner_reasoning=f"One or more jurisdictions not found. Available: {available}",
                head_to_head={},
                scenarios_where_j1_wins=[],
                scenarios_where_j2_wins=[],
            )

        # Define dimensions relevant to the trust type
        dimensions = {
            "asset_protection": ("Asset Protection Score", j1["asset_protection"], j2["asset_protection"]),
            "tax_efficiency": ("Tax Efficiency", j1["tax_efficiency"], j2["tax_efficiency"]),
            "dynasty_trust": ("Dynasty Trust Support", j1["dynasty_trust"], j2["dynasty_trust"]),
            "privacy": ("Privacy", j1["privacy"], j2["privacy"]),
            "ease_of_admin": ("Ease of Administration", j1["ease_of_admin"], j2["ease_of_admin"]),
            "cost_efficiency": ("Cost Efficiency", j1["cost_efficiency"], j2["cost_efficiency"]),
        }

        # Trust-type weighting
        weights_by_type = {
            "asset_protection": {"asset_protection": 4, "privacy": 2, "tax_efficiency": 2, "dynasty_trust": 1, "ease_of_admin": 1, "cost_efficiency": 1},
            "dynasty": {"dynasty_trust": 4, "tax_efficiency": 3, "asset_protection": 2, "privacy": 1, "ease_of_admin": 1, "cost_efficiency": 1},
            "revocable": {"ease_of_admin": 4, "cost_efficiency": 3, "tax_efficiency": 2, "asset_protection": 0, "privacy": 1, "dynasty_trust": 0},
            "charitable": {"tax_efficiency": 4, "ease_of_admin": 3, "cost_efficiency": 2, "asset_protection": 0, "privacy": 1, "dynasty_trust": 0},
        }
        trust_key = trust_type.lower().split("_")[0]
        weights = weights_by_type.get(trust_key, {dim: 1 for dim in dimensions})

        j1_total = sum(j1[dim] * weights.get(dim, 1) for dim in dimensions)
        j2_total = sum(j2[dim] * weights.get(dim, 1) for dim in dimensions)
        winner = j1["full_name"] if j1_total >= j2_total else j2["full_name"]

        head_to_head = {}
        for dim, (label, v1, v2) in dimensions.items():
            head_to_head[label] = {
                j1["full_name"]: v1,
                j2["full_name"]: v2,
                "winner": j1["full_name"] if v1 >= v2 else j2["full_name"],
                "weight": weights.get(dim, 1),
            }

        j1_scenarios = [s for s in j1["strengths"] if s not in j2["strengths"]][:3]
        j2_scenarios = [s for s in j2["strengths"] if s not in j1["strengths"]][:3]

        return Comparison(
            jurisdiction_1=j1["full_name"],
            jurisdiction_2=j2["full_name"],
            trust_type=trust_type,
            winner=winner,
            winner_reasoning=f"{winner} scores higher ({max(j1_total, j2_total):.1f} vs {min(j1_total, j2_total):.1f}) for {trust_type} trust weighted criteria.",
            head_to_head=head_to_head,
            scenarios_where_j1_wins=j1_scenarios,
            scenarios_where_j2_wins=j2_scenarios,
        )

    def get_offshore_options(self, asset_value: float, threat_level: str) -> List[OffshoreOption]:
        """
        Get ranked offshore options based on asset value and threat level.

        Args:
            asset_value: Total asset value in USD
            threat_level: "low", "medium", "high", "extreme"
        """
        options = []

        if asset_value >= 500_000:
            options.append(OffshoreOption(
                jurisdiction="Nevis",
                protection_level="High (9/10)",
                estimated_setup_cost="$8,000–$20,000",
                annual_maintenance_cost="$3,000–$8,000",
                us_reporting_requirements=["Form 3520", "Form 3520-A", "FBAR (if applicable)", "FATCA Form 8938"],
                best_for=["Entry-level offshore protection", "Nevis LLC combination", "Moderate threat levels"],
                risks=["US contempt risk", "Less tested than Cook Islands", "Political risk"],
                statute_of_limitations="2 years",
            ))

        if asset_value >= 1_000_000:
            options.append(OffshoreOption(
                jurisdiction="Cook Islands",
                protection_level="Extreme (10/10)",
                estimated_setup_cost="$25,000–$60,000",
                annual_maintenance_cost="$10,000–$30,000",
                us_reporting_requirements=["Form 3520 (annual)", "Form 3520-A (annual)", "FBAR (FinCEN 114)", "FATCA Form 8938", "Possible Form 8865/8858"],
                best_for=["Maximum asset protection", "High-risk professionals", "Pre-litigation protection", "Extreme threat scenarios"],
                risks=["US contempt of court risk", "Very high cost", "IRS scrutiny", "Cannot be used post-litigation"],
                statute_of_limitations="2 years from transfer",
            ))

        if asset_value >= 3_000_000:
            options.append(OffshoreOption(
                jurisdiction="Liechtenstein Foundation",
                protection_level="Very High (9/10)",
                estimated_setup_cost="$50,000–$150,000+",
                annual_maintenance_cost="$15,000–$50,000",
                us_reporting_requirements=["Form 3520", "Form 3520-A", "FBAR", "FATCA", "Potential Form 5471 if using company"],
                best_for=["Multi-generational European wealth", "Civil law flexibility", "International family offices"],
                risks=["OECD CRS information exchange", "Very high cost", "Civil law complexity"],
                statute_of_limitations="Varies",
            ))

        if asset_value >= 500_000 and threat_level in ["high", "extreme"]:
            options.append(OffshoreOption(
                jurisdiction="Belize",
                protection_level="Moderate-High (7/10)",
                estimated_setup_cost="$5,000–$15,000",
                annual_maintenance_cost="$2,000–$5,000",
                us_reporting_requirements=["Form 3520", "FBAR", "FATCA"],
                best_for=["Budget offshore option", "Preliminary protection layer", "Caribbean alternative"],
                risks=["Less established legal system", "Less tested in US courts", "Political/currency risk"],
                statute_of_limitations="120 years (trusts)",
            ))

        # Sort by protection level
        options.sort(key=lambda x: float(x.protection_level.split("(")[1].split("/")[0]), reverse=True)
        return options

    def analyze_migration_strategy(
        self, current_state: str, target_state: str, trust_type: str
    ) -> MigrationPlan:
        """
        Analyze the strategy for migrating a trust from one jurisdiction to another.
        """
        current_key = current_state.lower().replace(" ", "_")
        target_key = target_state.lower().replace(" ", "_")
        current_data = self.JURISDICTION_DATA.get(current_key, {})
        target_data = self.JURISDICTION_DATA.get(target_key, {})

        # Determine migration method
        if trust_type.lower() in ["revocable", "revocable_living_trust"]:
            method = "Revocation and Re-execution in Target State"
            steps = [
                "1. Grantor executes an Amendment to change governing law to target state",
                "2. Grantor executes a new Restatement of the Trust under target state law",
                "3. Ensure trustee has nexus in target state (appoint target state trustee)",
                "4. Update Schedule A — no re-titling needed (assets already in trust)",
                "5. File change of situs with relevant financial institutions if required",
                "6. Update pour-over will to reference new trust",
                "7. Obtain legal opinion on effectiveness of migration",
            ]
            method_cost = "$2,000–$5,000"
            timeline = 4
        elif "decanting" in str(target_data.get("decanting", "")):
            method = "Trust Decanting (pour trust assets into new trust in target state)"
            steps = [
                "1. Verify current state allows decanting (or trustee has power to decant)",
                "2. Draft new trust agreement in target state with desired provisions",
                "3. Trustee exercises decanting power — distributes assets to new trust",
                "4. File notice of decanting with current state court (if required)",
                "5. Transfer all assets from old trust to new trust",
                "6. Re-title assets in name of new trust",
                "7. Notify beneficiaries as required by statute",
                "8. Confirm new trust's governing law is effective",
            ]
            method_cost = "$5,000–$15,000"
            timeline = 8
        else:
            method = "Non-Judicial Settlement Agreement (NJSA) and Trust Modification"
            steps = [
                "1. Identify all qualified beneficiaries and obtain their consent",
                "2. Draft Non-Judicial Settlement Agreement under target state UTC §111",
                "3. All parties sign NJSA agreeing to change of situs and governing law",
                "4. Execute amendment to trust changing governing law to target state",
                "5. Appoint trustee with target state nexus",
                "6. Update all financial institution account agreements",
                "7. File any required notices with current state court",
            ]
            method_cost = "$8,000–$25,000"
            timeline = 12

        current_ap = current_data.get("asset_protection", 5)
        target_ap = target_data.get("asset_protection", 5)

        benefits = []
        if target_ap > current_ap:
            benefits.append(f"Asset protection improvement: {current_ap}/10 → {target_ap}/10")
        if not target_data.get("state_income_tax") and current_data.get("state_income_tax"):
            benefits.append("Eliminate state income tax on trust income")
        if target_data.get("dynasty_trust") and not current_data.get("dynasty_trust"):
            benefits.append("Gain access to dynasty trust / unlimited duration")
        if target_data.get("self_settled") and not current_data.get("self_settled"):
            benefits.append("Enable self-settled asset protection trust")
        if not benefits:
            benefits.append("Regulatory/administrative optimization")
            benefits.append(f"Access to {target_state}'s superior trust statutes")

        risks = [
            "Full faith and credit concerns — current state may not release jurisdiction",
            "Tax consequences of asset transfers during migration",
            "Beneficiary consents required for irrevocable trust modifications",
            "Existing creditor claims may follow the trust to new jurisdiction",
            "Attorney fees and administrative costs of migration",
        ]

        legal_requirements = [
            f"Review {current_state} law for requirements to change trust situs",
            f"Confirm {target_state} trustee or trust company with required nexus",
            "Obtain qualified legal opinion on migration effectiveness",
            "Notify all beneficiaries of material changes",
            "Update all account titles and registrations",
        ]

        return MigrationPlan(
            current_state=current_state,
            target_state=target_state,
            trust_type=trust_type,
            migration_method=method,
            steps=steps,
            estimated_cost=method_cost,
            timeline_weeks=timeline,
            risks=risks,
            benefits=benefits,
            legal_requirements=legal_requirements,
        )
