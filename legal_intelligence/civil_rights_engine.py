"""
Civil Rights Engine — SintraPrime Legal Intelligence System

Constitutional rights enforcement covering Section 1983, Title VII, ADA,
First and Fourth Amendment claims, qualified immunity, and damages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class Section1983Analysis:
    """
    Analysis of a 42 U.S.C. § 1983 civil rights claim.

    Example:
        >>> analysis = Section1983Analysis(
        ...     viable=True,
        ...     color_of_law=True,
        ...     constitutional_violation="Excessive force — 4th Amendment",
        ...     defendants=["Officer Smith (individual capacity)", "City of Springfield (Monell)"],
        ...     qualified_immunity_risk="High — excessive force clearly established",
        ...     municipal_liability=True,
        ...     estimated_damages={"compensatory": 150000, "punitive": 0}
        ... )
    """
    viable: bool
    color_of_law: bool
    constitutional_violation: str
    defendants: List[str]
    qualified_immunity_risk: str
    municipal_liability: bool
    estimated_damages: Dict[str, float]
    key_cases: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recommended_claims: List[str] = field(default_factory=list)


@dataclass
class EmploymentDiscriminationAnalysis:
    """
    Analysis of an employment discrimination claim under Title VII, ADA, or ADEA.

    Example:
        >>> analysis = EmploymentDiscriminationAnalysis(
        ...     viable=True,
        ...     statute="Title VII (42 U.S.C. § 2000e)",
        ...     protected_class="Race",
        ...     adverse_action="Termination",
        ...     discrimination_theory="Disparate treatment",
        ...     prima_facie_elements_met=True,
        ...     strength=0.75
        ... )
    """
    viable: bool
    statute: str
    protected_class: str
    adverse_action: str
    discrimination_theory: str  # "disparate treatment" | "disparate impact" | "hostile environment"
    prima_facie_elements_met: bool
    strength: float  # 0.0 - 1.0
    exhaustion_required: bool = True
    eeoc_deadline_days: int = 300
    pretext_evidence: List[str] = field(default_factory=list)
    comparator_evidence: List[str] = field(default_factory=list)
    damages_available: List[str] = field(default_factory=list)
    caps: Dict[str, int] = field(default_factory=dict)


@dataclass
class ADAAnalysis:
    """
    Analysis of an Americans with Disabilities Act claim.

    Example:
        >>> analysis = ADAAnalysis(
        ...     viable=True,
        ...     disability_established=True,
        ...     major_life_activity_limited="Walking, standing",
        ...     qualified_individual=True,
        ...     reasonable_accommodation_requested=True,
        ...     undue_hardship_defense="Unlikely given employer size",
        ...     adverse_action="Termination after accommodation request"
        ... )
    """
    viable: bool
    disability_established: bool
    major_life_activity_limited: str
    qualified_individual: bool
    reasonable_accommodation_requested: bool
    undue_hardship_defense: str
    adverse_action: str
    coverage: str = "Title I (employment)"  # I, II, III
    interactive_process: bool = False
    damages: List[str] = field(default_factory=list)


@dataclass
class FirstAmendmentAnalysis:
    """
    Analysis of a First Amendment free speech or religion claim.

    Example:
        >>> analysis = FirstAmendmentAnalysis(
        ...     viable=True,
        ...     forum_type="traditional public forum",
        ...     restriction_type="content-based",
        ...     scrutiny_level="strict",
        ...     government_interest="",
        ...     narrowly_tailored=False,
        ...     likely_unconstitutional=True
        ... )
    """
    viable: bool
    forum_type: str  # "traditional public forum" | "designated" | "nonpublic" | "private"
    restriction_type: str  # "content-based" | "content-neutral" | "viewpoint-based"
    scrutiny_level: str  # "strict" | "intermediate" | "rational basis"
    government_interest: str
    narrowly_tailored: bool
    likely_unconstitutional: bool
    protected_speech: bool = True
    prior_restraint: bool = False
    overbreadth_challenge: bool = False
    vagueness_challenge: bool = False
    key_cases: List[str] = field(default_factory=list)


@dataclass
class FourthAmendmentAnalysis:
    """
    Fourth Amendment civil rights analysis (distinct from criminal suppression).

    Example:
        >>> analysis = FourthAmendmentAnalysis(
        ...     search_unreasonable=True,
        ...     reasonable_expectation_of_privacy=True,
        ...     warrant_required=True,
        ...     exceptions_apply=[],
        ...     civil_remedy_available=True
        ... )
    """
    search_unreasonable: bool
    reasonable_expectation_of_privacy: bool
    warrant_required: bool
    exceptions_apply: List[str]
    civil_remedy_available: bool
    key_cases: List[str] = field(default_factory=list)
    bivens_claim: bool = False  # Federal actor
    section_1983_claim: bool = False  # State actor


@dataclass
class QualifiedImmunityAnalysis:
    """
    Analysis of qualified immunity defense to § 1983 claims.

    Example:
        >>> analysis = QualifiedImmunityAnalysis(
        ...     immunity_likely=False,
        ...     right_clearly_established=True,
        ...     controlling_case="Graham v. Connor (1989)",
        ...     specific_fact_match="Existing precedent clearly prohibited conduct",
        ...     recommendation="Proceed — immunity defense likely to fail"
        ... )
    """
    immunity_likely: bool
    right_clearly_established: bool
    controlling_case: str
    specific_fact_match: str
    recommendation: str
    high_court_trend: str = "SCOTUS has consistently expanded QI; but circuit courts have begun limiting it"
    legislative_reform_notes: str = "Several states (CO, NM, NY) have limited or eliminated state-law QI"


@dataclass
class DamagesEstimate:
    """
    Estimate of civil rights damages.

    Example:
        >>> estimate = DamagesEstimate(
        ...     compensatory=50000.0,
        ...     punitive=25000.0,
        ...     attorney_fees=30000.0,
        ...     nominal=0.0,
        ...     total_estimated=105000.0,
        ...     statutory_cap=300000
        ... )
    """
    compensatory: float
    punitive: float
    attorney_fees: float
    nominal: float
    total_estimated: float
    statutory_cap: Optional[int]
    back_pay: float = 0.0
    front_pay: float = 0.0
    emotional_distress: float = 0.0
    notes: str = ""


# ---------------------------------------------------------------------------
# Civil Rights Engine
# ---------------------------------------------------------------------------

class CivilRightsEngine:
    """
    Constitutional rights enforcement system covering all major civil rights claims.

    Analyzes Section 1983, employment discrimination, ADA, First and Fourth
    Amendment claims, qualified immunity, and damages calculations.

    Example:
        >>> engine = CivilRightsEngine()
        >>> analysis = engine.analyze_section_1983_claim({
        ...     "government_actor": True,
        ...     "constitutional_violation": "excessive force",
        ...     "city_policy": False
        ... })
        >>> analysis.viable
        True
    """

    TITLE_VII_CAPS: Dict[str, int] = {
        "15-100 employees": 50000,
        "101-200 employees": 100000,
        "201-500 employees": 200000,
        "500+ employees": 300000,
    }

    PROTECTED_CLASSES = {
        "title_vii": ["race", "color", "religion", "sex", "national origin"],
        "adea": ["age (40+)"],
        "ada": ["disability"],
        "section_1981": ["race (contract rights)"],
        "first_amendment": ["political speech", "religious exercise", "association", "petition"],
        "fourteenth_amendment": ["equal protection (any classification)"],
    }

    def analyze_section_1983_claim(self, facts: dict) -> Section1983Analysis:
        """
        Analyze viability of a 42 U.S.C. § 1983 civil rights claim.

        Elements required:
        1. Person acting under color of state law
        2. Deprivation of federal constitutional or statutory right
        3. Causation

        Args:
            facts: Dict with case facts (government_actor, constitutional_violation,
                   city_policy, supervisor_involvement, etc.).

        Returns:
            Section1983Analysis with viability assessment and strategy.

        Example:
            >>> engine = CivilRightsEngine()
            >>> result = engine.analyze_section_1983_claim({
            ...     "government_actor": True, "excessive_force": True,
            ...     "city_policy": True, "injury": "broken arm"
            ... })
            >>> result.viable
            True
        """
        government_actor = facts.get("government_actor", facts.get("state_actor", True))
        color_of_law = government_actor  # Police, public officials, state employees

        # Identify constitutional violation
        violation = ""
        if facts.get("excessive_force", False) or facts.get("constitutional_violation", "").lower() == "excessive force":
            violation = "Excessive force in violation of Fourth Amendment (Graham v. Connor, 490 U.S. 386 (1989))"
        elif facts.get("free_speech", False):
            violation = "First Amendment free speech violation"
        elif facts.get("due_process", False):
            violation = "Fourteenth Amendment due process violation"
        elif facts.get("equal_protection", False):
            violation = "Fourteenth Amendment equal protection violation"
        elif facts.get("unlawful_search", False):
            violation = "Fourth Amendment unreasonable search and seizure"
        elif facts.get("constitutional_violation"):
            violation = facts["constitutional_violation"]
        else:
            violation = "Potential constitutional violation — specific right to be identified"

        viable = color_of_law and bool(violation)

        # Defendants
        defendants = []
        if facts.get("officer_name") or facts.get("individual_defendant"):
            officer = facts.get("officer_name", "Government official")
            defendants.append(f"{officer} — individual capacity (personal liability)")
            defendants.append(f"{officer} — official capacity (injunctive relief)")

        # Monell municipal liability
        municipal = False
        if facts.get("city_policy", False) or facts.get("custom", False) or facts.get("failure_to_train", False):
            municipal = True
            city = facts.get("city", "Municipality")
            defendants.append(f"{city} — Monell liability (policy, custom, or failure to train)")

        if not defendants:
            defendants = ["Individual government actor", "Municipality (if policy/custom shown)"]

        # Qualified immunity assessment
        if "excessive force" in violation.lower():
            qi_risk = "Moderate-High — Graham clearly established standard, but fact-specific analysis required"
        elif "free speech" in violation.lower():
            qi_risk = "Low-Moderate — First Amendment rights well-established"
        else:
            qi_risk = "Assess whether 'clearly established' prong is met by specific factual precedent"

        # Damages
        damages = {
            "compensatory": float(facts.get("medical_bills", 0)) + float(facts.get("lost_wages", 0)),
            "punitive": 0.0,  # Against individual officers only (not municipalities)
            "nominal": 1.0 if not facts.get("actual_damages", True) else 0.0,
            "attorney_fees": 0.0,  # Available under 42 U.S.C. § 1988
        }

        key_cases = [
            "Monroe v. Pape, 365 U.S. 167 (1961) — § 1983 suits against individuals",
            "Monell v. Department of Social Services, 436 U.S. 658 (1978) — municipal liability",
            "Harlow v. Fitzgerald, 457 U.S. 800 (1982) — qualified immunity standard",
            "Graham v. Connor, 490 U.S. 386 (1989) — excessive force standard",
            "Will v. Michigan Dept. of State Police, 491 U.S. 58 (1989) — states not 'persons' under § 1983",
        ]

        weaknesses = []
        if not municipal and not government_actor:
            weaknesses.append("Defendant may not be acting under color of state law")
        if not facts.get("injury"):
            weaknesses.append("Document concrete injury — nominal damages insufficient for punitive")

        return Section1983Analysis(
            viable=viable,
            color_of_law=color_of_law,
            constitutional_violation=violation,
            defendants=defendants,
            qualified_immunity_risk=qi_risk,
            municipal_liability=municipal,
            estimated_damages=damages,
            key_cases=key_cases,
            weaknesses=weaknesses,
            recommended_claims=[
                "42 U.S.C. § 1983 — constitutional violation",
                "42 U.S.C. § 1988 — attorney's fees upon prevailing",
                "State tort claims (if applicable and not barred by state immunity)",
            ],
        )

    def analyze_title_vii_claim(self, facts: dict) -> EmploymentDiscriminationAnalysis:
        """
        Analyze employment discrimination claim under Title VII.

        Uses McDonnell Douglas burden-shifting framework.

        Args:
            facts: Dict with facts (protected_class, adverse_action, employer_size,
                   comparators, pretext_evidence, etc.).

        Returns:
            EmploymentDiscriminationAnalysis with viability assessment.

        Example:
            >>> engine = CivilRightsEngine()
            >>> result = engine.analyze_title_vii_claim({
            ...     "protected_class": "race",
            ...     "adverse_action": "termination",
            ...     "employer_size": 200,
            ...     "comparator_treated_better": True
            ... })
            >>> result.viable
            True
        """
        protected_class = facts.get("protected_class", "")
        adverse_action = facts.get("adverse_action", "adverse employment action")
        employer_size = facts.get("employer_size", 100)
        theory = facts.get("theory", "disparate_treatment")

        # Check coverage — Title VII requires 15+ employees
        if employer_size < 15:
            return EmploymentDiscriminationAnalysis(
                viable=False,
                statute="Title VII — NOT COVERED (fewer than 15 employees)",
                protected_class=protected_class,
                adverse_action=adverse_action,
                discrimination_theory="N/A",
                prima_facie_elements_met=False,
                strength=0.0,
                damages_available=["Consider state law claims (many states have lower thresholds)"],
            )

        # Prima facie elements (McDonnell Douglas)
        prima_facie_elements = [
            f"Member of protected class ({protected_class})",
            f"Qualified for position",
            f"Suffered adverse employment action ({adverse_action})",
            f"Similarly situated employees outside class treated more favorably",
        ]

        prima_facie_met = bool(protected_class) and bool(adverse_action)

        # Determine theory
        if "hostile" in str(facts).lower() or "harassment" in str(facts).lower():
            theory_desc = "hostile work environment"
        elif "disparate impact" in str(facts).lower() or facts.get("policy_effect"):
            theory_desc = "disparate impact"
        else:
            theory_desc = "disparate treatment"

        # Strength assessment
        strength = 0.5
        if facts.get("comparator_treated_better", False):
            strength += 0.15
        if facts.get("direct_evidence", False):  # Direct comment about protected class
            strength += 0.20
        if facts.get("statistical_evidence", False):
            strength += 0.10
        if facts.get("temporal_proximity", False):  # Fired shortly after protected activity
            strength += 0.10
        if facts.get("documented_pretext", False):
            strength += 0.15
        strength = min(0.95, strength)

        # Caps
        if employer_size >= 500:
            cap = 300000
            cap_key = "500+ employees"
        elif employer_size >= 201:
            cap = 200000
            cap_key = "201-500 employees"
        elif employer_size >= 101:
            cap = 100000
            cap_key = "101-200 employees"
        else:
            cap = 50000
            cap_key = "15-100 employees"

        damages_available = [
            f"Compensatory damages (capped at ${cap:,} for employers with {cap_key})",
            "Back pay — wages lost from termination to judgment",
            "Front pay — future lost wages if reinstatement impractical",
            "Reinstatement (equitable relief — no cap)",
            "Attorney's fees under 42 U.S.C. § 1988",
            "Punitive damages (if willful/malicious — subject to same cap)",
        ]

        return EmploymentDiscriminationAnalysis(
            viable=prima_facie_met and bool(protected_class),
            statute=f"Title VII of the Civil Rights Act, 42 U.S.C. § 2000e",
            protected_class=protected_class,
            adverse_action=adverse_action,
            discrimination_theory=theory_desc,
            prima_facie_elements_met=prima_facie_met,
            strength=strength,
            exhaustion_required=True,
            eeoc_deadline_days=300,
            pretext_evidence=facts.get("pretext_evidence", [
                "Shifting explanations for adverse action",
                "Prior positive performance reviews",
                "Statistical disparity in treatment of protected class",
                "Suspicious timing relative to protected activity",
            ]),
            comparator_evidence=["Identify comparators treated better under similar circumstances"],
            damages_available=damages_available,
            caps={cap_key: cap},
        )

    def analyze_ada_claim(self, facts: dict) -> ADAAnalysis:
        """
        Analyze Americans with Disabilities Act claim.

        Args:
            facts: Dict with ADA facts (disability, major_life_activity, accommodation_requested,
                   employer_size, adverse_action, coverage_type).

        Returns:
            ADAAnalysis with viability assessment.

        Example:
            >>> engine = CivilRightsEngine()
            >>> result = engine.analyze_ada_claim({
            ...     "disability": "PTSD", "accommodation": "flexible schedule",
            ...     "accommodation_denied": True, "employer_size": 50
            ... })
            >>> result.viable
            True
        """
        disability = facts.get("disability", "")
        accommodation = facts.get("accommodation", facts.get("accommodation_requested", ""))
        denied = facts.get("accommodation_denied", False)
        employer_size = facts.get("employer_size", 50)
        adverse_action = facts.get("adverse_action", "adverse employment action")
        major_life_activity = facts.get("major_life_activity", "working")
        coverage = facts.get("coverage", "Title I (employment)")

        # ADA Title I requires 15+ employees
        if "Title I" in coverage and employer_size < 15:
            return ADAAnalysis(
                viable=False,
                disability_established=False,
                major_life_activity_limited="N/A — employer too small",
                qualified_individual=False,
                reasonable_accommodation_requested=False,
                undue_hardship_defense="N/A",
                adverse_action="N/A",
                damages=["Consider state disability discrimination law (lower thresholds)"],
            )

        disability_established = bool(disability)

        # After ADAAA 2008: broad interpretation of disability
        ada_coverage_notes = [
            "ADAAA (2008) broadened disability definition — most impairments qualify",
            "Major life activities include: caring for self, walking, seeing, hearing, speaking, breathing, "
            "learning, reading, concentrating, thinking, communicating, working",
            "Major bodily functions also covered: immune, digestive, neurological, respiratory, etc.",
        ]

        # Reasonable accommodation analysis
        reasonable_accommodation = accommodation in [
            "flexible schedule", "modified duties", "leave of absence", "wheelchair accessible space",
            "screen reader", "sign language interpreter", "remote work", "ergonomic equipment",
        ] or bool(accommodation)

        # Undue hardship factors
        undue_hardship_factors = [
            "Cost of accommodation vs. employer's resources",
            "Employer's financial capacity",
            "Type of business operations",
            "Impact on other employees",
        ]

        if employer_size > 500:
            undue_hardship = "Low risk — large employer; undue hardship difficult to establish for most accommodations"
        elif employer_size > 50:
            undue_hardship = "Moderate risk — depends on cost and nature of accommodation"
        else:
            undue_hardship = "Higher risk — small employer may have limited resources"

        viable = disability_established and bool(adverse_action or denied)

        damages = [
            "Back pay",
            "Compensatory damages (emotional distress)",
            "Punitive damages (willful/malicious violations)",
            "Reinstatement",
            f"Compensatory/punitive cap: ${self.TITLE_VII_CAPS.get('500+ employees', 300000):,}",
            "Attorney's fees",
        ]

        return ADAAnalysis(
            viable=viable,
            disability_established=disability_established,
            major_life_activity_limited=major_life_activity,
            qualified_individual=True,  # Presumed from facts
            reasonable_accommodation_requested=bool(accommodation),
            undue_hardship_defense=undue_hardship,
            adverse_action=adverse_action,
            coverage=coverage,
            interactive_process=facts.get("interactive_process", False),
            damages=damages,
        )

    def analyze_first_amendment(self, facts: dict) -> FirstAmendmentAnalysis:
        """
        Analyze First Amendment free speech, religion, or assembly claim.

        Args:
            facts: Dict with facts (speech_type, forum, restriction_type,
                   government_interest, public_employee, etc.).

        Returns:
            FirstAmendmentAnalysis with viability assessment.

        Example:
            >>> engine = CivilRightsEngine()
            >>> result = engine.analyze_first_amendment({
            ...     "forum": "public park",
            ...     "restriction": "content-based ban on political speech",
            ...     "government_interest": "aesthetics"
            ... })
            >>> result.scrutiny_level == "strict"
            True
        """
        forum = facts.get("forum", "")
        restriction = facts.get("restriction", facts.get("restriction_type", ""))
        government_interest = facts.get("government_interest", "")
        public_employee = facts.get("public_employee", False)
        speech_type = facts.get("speech_type", "political speech")

        # Determine forum type
        forum_lower = forum.lower()
        if any(f in forum_lower for f in ["park", "sidewalk", "street", "public square"]):
            forum_type = "traditional public forum"
            default_scrutiny = "strict"
        elif any(f in forum_lower for f in ["school", "government building opened", "designated"]):
            forum_type = "designated public forum"
            default_scrutiny = "strict"
        elif any(f in forum_lower for f in ["government office", "airport", "military", "prison"]):
            forum_type = "nonpublic forum"
            default_scrutiny = "rational basis (reasonableness)"
        elif any(f in forum_lower for f in ["social media", "private", "company"]):
            forum_type = "private forum (First Amendment generally does not apply)"
            default_scrutiny = "N/A"
        else:
            forum_type = "forum to be determined"
            default_scrutiny = "strict"

        # Content-based vs. content-neutral
        restriction_lower = restriction.lower()
        if any(term in restriction_lower for term in ["content-based", "viewpoint", "topic", "subject matter",
                                                       "political", "religious", "specific message"]):
            restriction_type = "content-based (or viewpoint-based)"
            scrutiny = "strict"
        elif any(term in restriction_lower for term in ["time, place, manner", "time place manner", "neutral"]):
            restriction_type = "content-neutral time/place/manner restriction"
            scrutiny = "intermediate"
        else:
            restriction_type = restriction or "restriction on speech"
            scrutiny = default_scrutiny

        # Narrowly tailored?
        narrowly_tailored = facts.get("narrowly_tailored", False)

        # Unconstitutional?
        likely_unconstitutional = (
            scrutiny == "strict" and not narrowly_tailored
        ) or "viewpoint" in restriction_lower

        # Public employee analysis (Garcetti v. Ceballos)
        if public_employee:
            if facts.get("speech_as_citizen", False):
                forum_type += " (public employee speaking as citizen on matter of public concern)"
            else:
                forum_type += " (public employee speaking pursuant to official duties — NOT protected per Garcetti)"
                likely_unconstitutional = False

        # Prior restraint
        prior_restraint = "prior restraint" in restriction_lower or "injunction" in restriction_lower
        if prior_restraint:
            likely_unconstitutional = True  # Prior restraints carry heavy presumption of invalidity

        key_cases = [
            "Tinker v. Des Moines, 393 U.S. 503 (1969) — student speech",
            "Snyder v. Phelps, 562 U.S. 443 (2011) — public figure, public concern speech fully protected",
            "Reed v. Town of Gilbert, 576 U.S. 155 (2015) — content-based = strict scrutiny",
            "Ward v. Rock Against Racism, 491 U.S. 781 (1989) — TPM restrictions",
            "Garcetti v. Ceballos, 547 U.S. 410 (2006) — public employee speech",
            "Near v. Minnesota, 283 U.S. 697 (1931) — prior restraints presumptively invalid",
        ]

        return FirstAmendmentAnalysis(
            viable=likely_unconstitutional and "private" not in forum_type.lower(),
            forum_type=forum_type,
            restriction_type=restriction_type,
            scrutiny_level=scrutiny,
            government_interest=government_interest or "Not articulated",
            narrowly_tailored=narrowly_tailored,
            likely_unconstitutional=likely_unconstitutional,
            protected_speech="unprotected" not in speech_type.lower(),
            prior_restraint=prior_restraint,
            overbreadth_challenge=facts.get("overbroad", False),
            vagueness_challenge=facts.get("vague", False),
            key_cases=key_cases,
        )

    def analyze_fourth_amendment(self, facts: dict) -> FourthAmendmentAnalysis:
        """
        Analyze Fourth Amendment civil rights claim (civil context).

        Args:
            facts: Dict with search/seizure facts.

        Returns:
            FourthAmendmentAnalysis for civil remedy purposes.

        Example:
            >>> engine = CivilRightsEngine()
            >>> result = engine.analyze_fourth_amendment({
            ...     "home_searched": True, "warrant": False, "federal_actor": True
            ... })
            >>> result.search_unreasonable
            True
        """
        home = facts.get("home_searched", False)
        warrant = facts.get("warrant", False)
        federal_actor = facts.get("federal_actor", False)
        state_actor = facts.get("state_actor", True)
        exceptions = facts.get("exceptions", [])

        # Home searches require warrant absent emergency
        search_unreasonable = home and not warrant and not exceptions
        rep = home or facts.get("person", False) or facts.get("phone", False)

        exceptions_found = []
        if facts.get("consent", False):
            exceptions_found.append("Consent")
        if facts.get("exigent", False):
            exceptions_found.append("Exigent circumstances")
        if facts.get("plain_view", False):
            exceptions_found.append("Plain view")

        if exceptions_found:
            search_unreasonable = False

        civil_remedy = search_unreasonable and (federal_actor or state_actor)

        return FourthAmendmentAnalysis(
            search_unreasonable=search_unreasonable,
            reasonable_expectation_of_privacy=rep,
            warrant_required=home,
            exceptions_apply=exceptions_found,
            civil_remedy_available=civil_remedy,
            key_cases=[
                "Kyllo v. United States, 533 U.S. 27 (2001) — home is special; thermal imaging = search",
                "Carpenter v. United States, 585 U.S. 296 (2018) — cell phone location data = search",
                "Riley v. California, 573 U.S. 373 (2014) — cell phone search requires warrant",
            ],
            bivens_claim=federal_actor,
            section_1983_claim=state_actor,
        )

    def calculate_damages(self, violation_type: str, facts: dict) -> DamagesEstimate:
        """
        Calculate estimated civil rights damages.

        Args:
            violation_type: Type of civil rights violation.
            facts: Dict with damages facts (medical_bills, lost_wages, emotional_distress, etc.).

        Returns:
            DamagesEstimate with breakdown of recoverable damages.

        Example:
            >>> engine = CivilRightsEngine()
            >>> estimate = engine.calculate_damages(
            ...     "employment_discrimination",
            ...     {"lost_wages_monthly": 5000, "months_unemployed": 12, "emotional_distress": 50000}
            ... )
            >>> estimate.total_estimated > 0
            True
        """
        medical = float(facts.get("medical_bills", 0))
        lost_wages = float(facts.get("lost_wages", facts.get("lost_wages_monthly", 0) *
                                    facts.get("months_unemployed", 0)))
        emotional = float(facts.get("emotional_distress", 0))
        front_pay_years = float(facts.get("front_pay_years", 0))
        monthly_wage = float(facts.get("monthly_wage", facts.get("lost_wages_monthly", 0)))
        front_pay = front_pay_years * 12 * monthly_wage

        compensatory = medical + lost_wages + emotional
        back_pay = lost_wages

        # Punitive damages
        punitive = 0.0
        if facts.get("willful_malicious", False) or facts.get("egregious", False):
            punitive = compensatory * 2  # Rule of thumb; varies

        # Attorney fees (42 U.S.C. § 1988 — prevailing party gets fees)
        estimated_attorney_fees = compensatory * 0.30  # Lodestar rough estimate

        # Title VII cap
        employer_size = facts.get("employer_size", 500)
        if "employment" in violation_type.lower() or "title_vii" in violation_type.lower():
            if employer_size >= 500:
                cap = 300000
            elif employer_size >= 201:
                cap = 200000
            elif employer_size >= 101:
                cap = 100000
            else:
                cap = 50000
            # Cap applies to compensatory + punitive combined (not back/front pay)
            capped_amount = min(compensatory + punitive, cap)
            total = back_pay + front_pay + capped_amount + estimated_attorney_fees
            statutory_cap: Optional[int] = cap
        else:
            statutory_cap = None
            total = compensatory + punitive + estimated_attorney_fees

        return DamagesEstimate(
            compensatory=compensatory,
            punitive=punitive,
            attorney_fees=estimated_attorney_fees,
            nominal=1.0 if compensatory == 0 else 0.0,
            total_estimated=round(total, 2),
            statutory_cap=statutory_cap,
            back_pay=back_pay,
            front_pay=front_pay,
            emotional_distress=emotional,
            notes=(
                "Attorney fees under 42 U.S.C. § 1988 available to prevailing plaintiff. "
                "Punitive damages against municipalities prohibited under City of Newport v. Fact Concerts. "
                "Punitive damages against individuals require malice or reckless indifference."
            ),
        )

    def identify_qualified_immunity_issues(self, facts: dict) -> QualifiedImmunityAnalysis:
        """
        Analyze qualified immunity defense to a § 1983 claim.

        The two-step test (Pearson v. Callahan):
        1. Did officer violate a constitutional right?
        2. Was the right clearly established at time of conduct?

        Args:
            facts: Dict with immunity facts (violation_type, controlling_precedent,
                   date_of_conduct, etc.).

        Returns:
            QualifiedImmunityAnalysis with immunity assessment.

        Example:
            >>> engine = CivilRightsEngine()
            >>> result = engine.identify_qualified_immunity_issues({
            ...     "excessive_force": True,
            ...     "clearly_established_precedent": True
            ... })
            >>> result.immunity_likely
            False
        """
        violation = facts.get("violation_type", facts.get("excessive_force", False))
        clearly_established = facts.get("clearly_established_precedent",
                                        facts.get("right_clearly_established", False))
        analogous_case = facts.get("analogous_case", "")
        egregious = facts.get("egregious", False)

        if not clearly_established and not egregious:
            immunity_likely = True
            controlling_case = "Taylor v. Riojas, 592 U.S. ___ (2020) — immunity denied even without case on point for obviously unconstitutional conduct"
            specific_fact_match = "No clear controlling precedent identified — immunity may apply"
            recommendation = (
                "Qualified immunity defense is strong. Identify specific analogous precedent "
                "with nearly identical facts to overcome QI. General prohibition on excessive force "
                "insufficient — need specific precedent. Brosseau v. Haugen (2004)."
            )
        elif egregious:
            immunity_likely = False
            controlling_case = "Hope v. Pelzer, 536 U.S. 730 (2002) — obvious unconstitutionality can clearly establish right without factually similar case"
            specific_fact_match = "Conduct so obviously unconstitutional that any reasonable officer would know it violates Constitution"
            recommendation = "QI defense should fail — conduct obviously unconstitutional regardless of specific precedent."
        else:
            immunity_likely = False
            controlling_case = analogous_case or "Controlling circuit precedent"
            specific_fact_match = "Existing precedent clearly prohibited the specific conduct at issue"
            recommendation = "QI defense likely to fail — right clearly established by specific precedent."

        return QualifiedImmunityAnalysis(
            immunity_likely=immunity_likely,
            right_clearly_established=clearly_established or egregious,
            controlling_case=controlling_case,
            specific_fact_match=specific_fact_match,
            recommendation=recommendation,
            high_court_trend=(
                "SCOTUS has consistently expanded QI (Pearson 2009, Mullenix 2015, etc.). "
                "But Taylor v. Riojas (2020) and McCoy v. Alamu (2021) show some limits. "
                "QI is most commonly cited reason § 1983 excessive force cases are dismissed."
            ),
            legislative_reform_notes=(
                "Colorado (HB 1217, 2020), New Mexico (2021), New York (2021), and Massachusetts have "
                "limited or eliminated state-law qualified immunity. Federal reform (George Floyd Justice in Policing Act) has not passed."
            ),
        )
