"""
Immigration Engine — SintraPrime Legal Intelligence System

Complete immigration law coverage including visa options, green card pathways,
naturalization, removal defense, DACA, asylum, employer compliance, and waivers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class VisaOption:
    """
    A visa category available to an individual.

    Example:
        >>> option = VisaOption(
        ...     visa_category="H-1B",
        ...     name="Specialty Occupation Worker",
        ...     eligibility="Bachelor's degree in specialty occupation",
        ...     annual_cap=65000,
        ...     duration="3 years (extendable to 6)",
        ...     path_to_green_card=True,
        ...     score=85
        ... )
    """
    visa_category: str
    name: str
    eligibility: str
    annual_cap: Optional[int]
    duration: str
    path_to_green_card: bool
    score: int  # 0-100 relevance/viability score
    requirements: List[str] = field(default_factory=list)
    processing_time: str = ""
    notes: str = ""


@dataclass
class GreenCardOption:
    """
    A permanent residence (green card) pathway.

    Example:
        >>> option = GreenCardOption(
        ...     category="EB-1A",
        ...     name="Alien of Extraordinary Ability",
        ...     priority_date="Current",
        ...     self_petition=True,
        ...     annual_limit=40000,
        ...     estimated_wait_years=0,
        ...     requirements=["Extraordinary ability evidence (10 criteria)"]
        ... )
    """
    category: str
    name: str
    priority_date: str
    self_petition: bool
    annual_limit: int
    estimated_wait_years: float
    requirements: List[str]
    score: int = 0  # 0-100 viability score
    notes: str = ""


@dataclass
class NaturalizationAnalysis:
    """
    Analysis of naturalization eligibility.

    Example:
        >>> analysis = NaturalizationAnalysis(
        ...     eligible=True,
        ...     five_year_rule_met=True,
        ...     continuous_residence=True,
        ...     physical_presence_met=True,
        ...     good_moral_character=True,
        ...     english_requirement_met=True,
        ...     civics_requirement_met=True
        ... )
    """
    eligible: bool
    five_year_rule_met: bool
    continuous_residence: bool
    physical_presence_met: bool
    good_moral_character: bool
    english_requirement_met: bool
    civics_requirement_met: bool
    bars_to_naturalization: List[str] = field(default_factory=list)
    exceptions_available: List[str] = field(default_factory=list)
    earliest_filing_date: str = ""
    notes: str = ""


@dataclass
class RemovalDefenseStrategy:
    """
    Strategy for defending against removal/deportation.

    Example:
        >>> strategy = RemovalDefenseStrategy(
        ...     viable_relief=["Cancellation of Removal", "Asylum"],
        ...     primary_strategy="Cancellation — 10 years presence + exceptional hardship",
        ...     strengths=["US citizen children", "Long residence", "Clean record"],
        ...     weaknesses=["Prior deportation order"],
        ...     immediate_actions=["File motion for continuance", "Gather hardship evidence"]
        ... )
    """
    viable_relief: List[str]
    primary_strategy: str
    strengths: List[str]
    weaknesses: List[str]
    immediate_actions: List[str]
    timeline: str = ""
    probability_of_success: float = 0.5
    key_statutes: List[str] = field(default_factory=list)


@dataclass
class AsylumAnalysis:
    """
    Analysis of asylum claim viability.

    Example:
        >>> analysis = AsylumAnalysis(
        ...     viable=True,
        ...     ground="Political Opinion",
        ...     well_founded_fear=True,
        ...     past_persecution=True,
        ...     nexus=True,
        ...     bars_to_asylum=[],
        ...     one_year_filing_deadline_met=True
        ... )
    """
    viable: bool
    ground: str  # Race, Religion, Nationality, Political Opinion, Particular Social Group
    well_founded_fear: bool
    past_persecution: bool
    nexus: bool
    bars_to_asylum: List[str]
    one_year_filing_deadline_met: bool
    withholding_viable: bool = False
    cat_viable: bool = False  # Convention Against Torture
    strength_assessment: float = 0.5
    country_conditions_support: bool = False
    credibility_factors: List[str] = field(default_factory=list)


@dataclass
class DACAAnalysis:
    """
    Analysis of DACA eligibility and current status.

    Example:
        >>> analysis = DACAAnalysis(
        ...     eligible=True,
        ...     age_at_entry_met=True,
        ...     continuous_residence_met=True,
        ...     education_met=True,
        ...     criminal_bars=False,
        ...     current_program_status="Active — renewals ongoing per court orders"
        ... )
    """
    eligible: bool
    age_at_entry_met: bool
    continuous_residence_met: bool
    education_met: bool
    criminal_bars: bool
    current_program_status: str
    benefits: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    litigation_status: str = ""


@dataclass
class I9ComplianceReport:
    """
    I-9 employer compliance audit report.

    Example:
        >>> report = I9ComplianceReport(
        ...     compliant=False,
        ...     violations=["Missing I-9 for 3 employees", "Expired documents accepted"],
        ...     civil_penalty_range="$272 - $2,701 per violation",
        ...     recommendations=["Complete missing I-9s", "Conduct self-audit"],
        ...     audit_date="2024-03-15"
        ... )
    """
    compliant: bool
    violations: List[str]
    civil_penalty_range: str
    recommendations: List[str]
    audit_date: str = ""
    criminal_penalty_risk: bool = False
    e_verify_status: str = "Not enrolled"


@dataclass
class WaiverStrategy:
    """
    Strategy for seeking an immigration inadmissibility waiver.

    Example:
        >>> strategy = WaiverStrategy(
        ...     grounds=["Prior removal", "Unlawful presence"],
        ...     available_waivers=["I-212 (Permission to Reapply)", "I-601A (Unlawful Presence Waiver)"],
        ...     hardship_required=True,
        ...     qualifying_relatives=["US citizen spouse"],
        ...     approval_likelihood=0.6
        ... )
    """
    grounds: List[str]
    available_waivers: List[str]
    hardship_required: bool
    qualifying_relatives: List[str]
    approval_likelihood: float
    required_forms: List[str] = field(default_factory=list)
    timeline: str = ""
    notes: str = ""


# ---------------------------------------------------------------------------
# Immigration Engine
# ---------------------------------------------------------------------------

class ImmigrationEngine:
    """
    Complete immigration law system covering visas, green cards, naturalization,
    removal defense, asylum, DACA, employer compliance, and waivers.

    Example:
        >>> engine = ImmigrationEngine()
        >>> options = engine.analyze_visa_options({
        ...     "job_offer": True,
        ...     "specialty_occupation": True,
        ...     "bachelor_degree": True,
        ...     "employer_petitions": True
        ... })
        >>> any(opt.visa_category == "H-1B" for opt in options)
        True
    """

    VISA_CATEGORIES: Dict[str, Dict] = {
        "H-1B": {
            "name": "Specialty Occupation",
            "requirements": ["Bachelor's degree in related field", "Job offer from US employer",
                             "Employer files LCA and H-1B petition", "Specialty occupation"],
            "annual_cap": 65000,
            "duration": "3 years (extendable to 6; unlimited if EB-1/2/3 petition pending)",
            "path_to_green_card": True,
            "processing_time": "3-6 months standard; 15 days premium processing",
            "conditions": ["specialty_occupation", "bachelor_degree", "job_offer"],
        },
        "L-1A": {
            "name": "Intracompany Transferee (Manager/Executive)",
            "requirements": ["Employed abroad for 1+ year in past 3 years", "Transfer to US parent/sub/affiliate",
                             "Manager or executive capacity"],
            "annual_cap": None,
            "duration": "3 years initial (extendable); 7 years max",
            "path_to_green_card": True,
            "processing_time": "2-4 months",
            "conditions": ["intracompany_transfer", "manager_executive"],
        },
        "L-1B": {
            "name": "Intracompany Transferee (Specialized Knowledge)",
            "requirements": ["Employed abroad for 1+ year in past 3 years", "Specialized knowledge"],
            "annual_cap": None,
            "duration": "3 years initial; 5 years max",
            "path_to_green_card": True,
            "conditions": ["intracompany_transfer", "specialized_knowledge"],
        },
        "O-1A": {
            "name": "Extraordinary Ability (Science, Arts, Education, Business, Athletics)",
            "requirements": ["Extraordinary ability (sustained national/international acclaim)",
                             "No employer sponsor required (self-petition ok)",
                             "Evidence: awards, publications, high salary, critical role, etc."],
            "annual_cap": None,
            "duration": "3 years initial (extendable)",
            "path_to_green_card": True,
            "processing_time": "2-3 months",
            "conditions": ["extraordinary_ability"],
        },
        "EB-1A": {
            "name": "Employment-Based Green Card — Extraordinary Ability (Self-Petition)",
            "requirements": ["Extraordinary ability shown by 3 of 10 criteria",
                             "No job offer required", "Premium processing available"],
            "annual_cap": 40000,
            "duration": "Permanent",
            "path_to_green_card": True,
            "processing_time": "6-12 months",
            "conditions": ["extraordinary_ability"],
        },
        "TN": {
            "name": "TN Visa (Canada/Mexico USMCA Professionals)",
            "requirements": ["Canadian or Mexican national",
                             "Profession listed in USMCA Schedule 2",
                             "US employer's job offer", "Qualifying degree/credentials"],
            "annual_cap": None,
            "duration": "3 years (indefinitely renewable)",
            "path_to_green_card": False,
            "processing_time": "Same day (Canadian nationals at port of entry)",
            "conditions": ["canadian_or_mexican", "tn_profession"],
        },
        "E-2": {
            "name": "Treaty Investor",
            "requirements": ["Treaty country national", "Substantial investment in US enterprise",
                             "Investment is real and at risk", "Investor controls investment"],
            "annual_cap": None,
            "duration": "Up to 5 years (renewable indefinitely)",
            "path_to_green_card": False,
            "processing_time": "2-3 months",
            "conditions": ["treaty_country_national", "substantial_investment"],
        },
        "F-1": {
            "name": "Student Visa",
            "requirements": ["Acceptance to SEVP-accredited school", "English proficiency",
                             "Financial support", "Intent to return home"],
            "annual_cap": None,
            "duration": "Duration of status (D/S)",
            "path_to_green_card": False,
            "processing_time": "2-3 months",
            "conditions": ["student"],
        },
        "B-1/B-2": {
            "name": "Visitor (Business/Tourism)",
            "requirements": ["No immigrant intent", "Financial support",
                             "Strong home country ties"],
            "annual_cap": None,
            "duration": "Up to 6 months",
            "path_to_green_card": False,
            "conditions": ["visitor"],
        },
        "U Visa": {
            "name": "Crime Victim Visa",
            "requirements": ["Victim of qualifying crime", "Suffered substantial abuse",
                             "Helpful, being helpful, or likely to be helpful to law enforcement",
                             "Law enforcement certification"],
            "annual_cap": 10000,
            "duration": "4 years",
            "path_to_green_card": True,
            "processing_time": "4-7 years (backlog)",
            "conditions": ["crime_victim"],
        },
        "T Visa": {
            "name": "Human Trafficking Victim Visa",
            "requirements": ["Victim of severe trafficking",
                             "Physical presence due to trafficking",
                             "Compliance with law enforcement requests (with exceptions)"],
            "annual_cap": 5000,
            "duration": "4 years",
            "path_to_green_card": True,
            "conditions": ["trafficking_victim"],
        },
        "VAWA": {
            "name": "VAWA Self-Petition (Abuse Victims)",
            "requirements": ["Victim of battery/extreme cruelty by USC/LPR spouse, parent, or child",
                             "Resided with abuser", "Good moral character"],
            "annual_cap": None,
            "duration": "Path to LPR",
            "path_to_green_card": True,
            "conditions": ["abuse_by_usc_lpr_family"],
        },
    }

    GREEN_CARD_CATEGORIES: Dict[str, Dict] = {
        "EB-1A": {"name": "Extraordinary Ability", "cap": 40000, "self_petition": True, "wait": 0},
        "EB-1B": {"name": "Outstanding Professor/Researcher", "cap": 40000, "self_petition": False, "wait": 0},
        "EB-1C": {"name": "Multinational Executive/Manager", "cap": 40000, "self_petition": False, "wait": 0},
        "EB-2 NIW": {"name": "National Interest Waiver", "cap": 40000, "self_petition": True, "wait": 2},
        "EB-2 PERM": {"name": "Advanced Degree (with PERM)", "cap": 40000, "self_petition": False, "wait": 2},
        "EB-3": {"name": "Skilled Worker", "cap": 40000, "self_petition": False, "wait": 5},
        "EB-4": {"name": "Special Immigrants (religious workers, etc.)", "cap": 10000, "self_petition": False, "wait": 2},
        "EB-5": {"name": "Investor ($800,000 / $1,050,000 investment)", "cap": 10000, "self_petition": True, "wait": 5},
        "IR-1": {"name": "Immediate Relative of USC (Spouse)", "cap": 0, "self_petition": False, "wait": 0},
        "IR-2": {"name": "Immediate Relative of USC (Unmarried child <21)", "cap": 0, "self_petition": False, "wait": 0},
        "IR-5": {"name": "Immediate Relative of USC (Parent)", "cap": 0, "self_petition": False, "wait": 0},
        "F-2A": {"name": "Spouse/child of LPR", "cap": 114200, "self_petition": False, "wait": 2},
        "F-2B": {"name": "Unmarried adult child of LPR", "cap": 114200, "self_petition": False, "wait": 5},
        "Asylum": {"name": "Asylum Grant → Green Card", "cap": 10000, "self_petition": True, "wait": 1},
        "Diversity Lottery": {"name": "DV Lottery (50,000 annually)", "cap": 50000, "self_petition": True, "wait": 0},
    }

    def analyze_visa_options(self, facts: dict) -> List[VisaOption]:
        """
        Analyze and rank all available visa options for an individual.

        Args:
            facts: Dict with individual's background (job_offer, specialty_occupation,
                   bachelor_degree, extraordinary_ability, investor, student, etc.).

        Returns:
            Ranked list of VisaOption objects (highest viability first).

        Example:
            >>> engine = ImmigrationEngine()
            >>> options = engine.analyze_visa_options({
            ...     "job_offer": True, "specialty_occupation": True, "bachelor_degree": True
            ... })
            >>> len(options) > 0
            True
        """
        viable_options: List[VisaOption] = []

        for category, info in self.VISA_CATEGORIES.items():
            score = self._score_visa(category, info, facts)
            if score > 20:
                option = VisaOption(
                    visa_category=category,
                    name=info["name"],
                    eligibility="; ".join(info["requirements"][:2]),
                    annual_cap=info.get("annual_cap"),
                    duration=info["duration"],
                    path_to_green_card=info["path_to_green_card"],
                    score=score,
                    requirements=info["requirements"],
                    processing_time=info.get("processing_time", "Varies"),
                    notes=f"Cap: {info.get('annual_cap', 'No cap')}",
                )
                viable_options.append(option)

        # Sort by score descending
        viable_options.sort(key=lambda x: x.score, reverse=True)
        return viable_options

    def _score_visa(self, category: str, info: dict, facts: dict) -> int:
        """Score a visa category based on individual facts."""
        score = 30  # Base score

        conditions = info.get("conditions", [])

        condition_checks = {
            "specialty_occupation": facts.get("specialty_occupation", False),
            "bachelor_degree": facts.get("bachelor_degree", False),
            "job_offer": facts.get("job_offer", False),
            "intracompany_transfer": facts.get("intracompany_transfer", False),
            "manager_executive": facts.get("manager_executive", False),
            "specialized_knowledge": facts.get("specialized_knowledge", False),
            "extraordinary_ability": facts.get("extraordinary_ability", False),
            "canadian_or_mexican": facts.get("canadian_or_mexican", False),
            "tn_profession": facts.get("tn_profession", False),
            "treaty_country_national": facts.get("treaty_country_national", False),
            "substantial_investment": facts.get("substantial_investment", False),
            "student": facts.get("student", False),
            "visitor": facts.get("visitor", False),
            "crime_victim": facts.get("crime_victim", False),
            "trafficking_victim": facts.get("trafficking_victim", False),
            "abuse_by_usc_lpr_family": facts.get("abuse_by_usc_lpr_family", False),
        }

        for condition in conditions:
            if condition_checks.get(condition, False):
                score += 25

        # Bonus for immigrant visa path desire
        if facts.get("wants_green_card", True) and info.get("path_to_green_card", False):
            score += 10

        # Deduct for annual caps if backlogged
        if info.get("annual_cap") and info["annual_cap"] < 10000:
            score -= 10

        return min(100, max(0, score))

    def green_card_pathways(self, facts: dict) -> List[GreenCardOption]:
        """
        Analyze all available green card pathways.

        Args:
            facts: Dict with background (usc_spouse, usc_parent, lpr_spouse, extraordinary_ability,
                   employer_sponsor, investor, asylum_pending, etc.).

        Returns:
            Ranked list of GreenCardOption objects.

        Example:
            >>> engine = ImmigrationEngine()
            >>> options = engine.green_card_pathways({"usc_spouse": True})
            >>> any(opt.category == "IR-1" for opt in options)
            True
        """
        options: List[GreenCardOption] = []

        scores = {
            "IR-1": 90 if facts.get("usc_spouse", False) else 0,
            "IR-2": 90 if facts.get("usc_parent_of_minor", False) else 0,
            "IR-5": 90 if facts.get("usc_child_over_21_petitioning", False) else 0,
            "EB-1A": 80 if facts.get("extraordinary_ability", False) else 0,
            "EB-1B": 75 if facts.get("outstanding_researcher", False) else 0,
            "EB-1C": 75 if facts.get("multinational_exec", False) else 0,
            "EB-2 NIW": 70 if facts.get("national_interest_waiver", False) or facts.get("advanced_degree", False) else 0,
            "EB-2 PERM": 65 if facts.get("employer_sponsor", False) and facts.get("advanced_degree", False) else 0,
            "EB-3": 55 if facts.get("employer_sponsor", False) else 0,
            "EB-5": 70 if facts.get("investor", False) and facts.get("investment_amount", 0) >= 800000 else 0,
            "Asylum": 80 if facts.get("asylum_pending", False) or facts.get("asylum_approved", False) else 0,
            "F-2A": 70 if facts.get("lpr_spouse", False) else 0,
            "Diversity Lottery": 40 if facts.get("diversity_lottery_eligible", False) else 0,
        }

        for cat, info in self.GREEN_CARD_CATEGORIES.items():
            score = scores.get(cat, 0)
            if score > 0:
                options.append(GreenCardOption(
                    category=cat,
                    name=info["name"],
                    priority_date="Current" if info["wait"] == 0 else f"~{info['wait']} year(s) backlog",
                    self_petition=info["self_petition"],
                    annual_limit=info["cap"] or 0,
                    estimated_wait_years=float(info["wait"]),
                    requirements=["See USCIS requirements for " + cat],
                    score=score,
                ))

        options.sort(key=lambda x: x.score, reverse=True)
        return options

    def naturalization_eligibility(self, facts: dict) -> NaturalizationAnalysis:
        """
        Analyze naturalization eligibility under 8 U.S.C. § 1427.

        Args:
            facts: Dict with LPR history (lpr_years, continuous_residence_breaks,
                   physical_presence_days, good_moral_character, english_proficient,
                   married_to_usc).

        Returns:
            NaturalizationAnalysis with eligibility determination.

        Example:
            >>> engine = ImmigrationEngine()
            >>> result = engine.naturalization_eligibility({
            ...     "lpr_years": 6, "continuous_residence": True,
            ...     "physical_presence_days": 913, "good_moral_character": True
            ... })
            >>> result.eligible
            True
        """
        lpr_years = facts.get("lpr_years", 0)
        married_usc = facts.get("married_to_usc", False)
        continuous_residence = facts.get("continuous_residence", True)
        physical_presence_days = facts.get("physical_presence_days", 0)
        good_moral_character = facts.get("good_moral_character", True)
        english = facts.get("english_proficient", True)

        # Requirement periods
        if married_usc and facts.get("living_with_usc", True):
            required_years = 3
            required_physical_days = 548  # 1.5 years
        else:
            required_years = 5
            required_physical_days = 913  # 2.5 years

        five_year = lpr_years >= required_years
        physical = physical_presence_days >= required_physical_days

        # Breaks in continuous residence
        if facts.get("abroad_more_than_6_months", False):
            continuous_residence = False
        if facts.get("abroad_more_than_1_year", False):
            continuous_residence = False
            # Presumption of abandonment

        bars = []
        exceptions = []

        # Statutory bars to naturalization
        if facts.get("aggravated_felony", False):
            bars.append("Aggravated felony conviction bars naturalization permanently (INA § 101(a)(43))")
        if facts.get("terrorist_activity", False):
            bars.append("Terrorist activity — absolute bar")
        if facts.get("nazi_persecution", False):
            bars.append("Nazi persecution participation — bar")
        if facts.get("selective_service_failure", False) and facts.get("male_age_18_26", False):
            bars.append("Failure to register for selective service may bar naturalization")

        # Exceptions
        if facts.get("age_50_20_year_lpr", False):
            exceptions.append("Over 50 with 20+ years LPR — English exemption")
        if facts.get("age_55_15_year_lpr", False):
            exceptions.append("Over 55 with 15+ years LPR — English exemption")
        if facts.get("disability_exemption", False):
            exceptions.append("Civics/English exemption for physical/developmental disability (N-648)")
        if facts.get("military_service", False):
            exceptions.append("Military service — expedited or exception to residence requirements")

        eligible = (five_year and physical and continuous_residence and
                    good_moral_character and english and len(bars) == 0)

        return NaturalizationAnalysis(
            eligible=eligible,
            five_year_rule_met=five_year,
            continuous_residence=continuous_residence,
            physical_presence_met=physical,
            good_moral_character=good_moral_character,
            english_requirement_met=english,
            civics_requirement_met=facts.get("civics_knowledge", True),
            bars_to_naturalization=bars,
            exceptions_available=exceptions,
            earliest_filing_date=f"After {required_years} years LPR + 90-day early filing window",
            notes=(
                "Good moral character period: last 5 years (3 if married to USC). "
                "Bars include: murder, aggravated felony, terrorism, Nazi persecution. "
                "Absences of 6-12 months disrupt continuous residence; 12+ months = presumption of abandonment."
            ),
        )

    def removal_defense(self, facts: dict) -> RemovalDefenseStrategy:
        """
        Develop a removal defense strategy.

        Args:
            facts: Dict with case facts (years_in_us, family_ties, criminal_history,
                   fear_of_return, entered_legally, etc.).

        Returns:
            RemovalDefenseStrategy with viable relief and approach.

        Example:
            >>> engine = ImmigrationEngine()
            >>> strategy = engine.removal_defense({
            ...     "years_in_us": 12, "lpr": False,
            ...     "us_citizen_children": True, "fear_of_country": True
            ... })
            >>> len(strategy.viable_relief) > 0
            True
        """
        years_in_us = facts.get("years_in_us", 0)
        lpr = facts.get("lpr", False)
        usc_children = facts.get("us_citizen_children", False)
        usc_spouse = facts.get("usc_spouse", False)
        fear_of_country = facts.get("fear_of_country", False)
        criminal_history = facts.get("criminal_history", False)
        entered_legally = facts.get("entered_legally", False)
        prior_deportation = facts.get("prior_deportation", False)

        viable_relief = []
        strengths = []
        weaknesses = []

        # Cancellation of Removal (INA § 240A)
        if not lpr and years_in_us >= 10 and not criminal_history:
            viable_relief.append(
                "Cancellation of Removal (INA § 240A(b)) — 10 years continuous presence, "
                "good moral character, exceptional and extremely unusual hardship to USC/LPR spouse/parent/child"
            )
            if usc_children or usc_spouse:
                strengths.append("US citizen family members provide strong hardship showing")

        # LPR Cancellation
        if lpr and years_in_us >= 5 and facts.get("lpr_years", 0) >= 7:
            viable_relief.append(
                "LPR Cancellation of Removal (INA § 240A(a)) — 5 years LPR, 7 years continuous residence, no aggravated felony"
            )

        # Asylum, Withholding, CAT
        if fear_of_country:
            viable_relief.append("Asylum — well-founded fear on protected ground (INA § 208)")
            viable_relief.append("Withholding of Removal (INA § 241(b)(3)) — more-likely-than-not persecution")
            viable_relief.append("Convention Against Torture (CAT) — more-likely-than-not torture by government")

        # Adjustment of Status
        if usc_spouse or usc_children:
            if not prior_deportation and entered_legally:
                viable_relief.append(
                    "Adjustment of Status through family petition (I-130 + I-485)"
                )

        # Voluntary Departure
        viable_relief.append("Voluntary Departure (INA § 240B) — preserves right to return")

        # Weaknesses
        if criminal_history:
            weaknesses.append("Criminal history may bar cancellation and asylum")
        if prior_deportation:
            weaknesses.append("Prior removal order requires I-212 consent before reentry")
        if not entered_legally:
            weaknesses.append("Unlawful entry may bar adjustment of status (I-601A waiver needed)")

        # Immediate actions
        immediate = [
            "REQUEST CONTINUANCE at first master calendar hearing",
            "DO NOT SIGN VOLUNTARY DEPARTURE without counsel review",
            "File G-28 Notice of Entry of Appearance",
            "Gather all immigration documents immediately",
            "Compile evidence of US ties (family, employment, taxes, community)",
            "If fear of country — do NOT delay; file asylum application or assert fear at hearing",
        ]

        if not viable_relief:
            viable_relief = ["Voluntary Departure", "Motion to Reopen (if in absentia order)"]
            primary = "Explore all possible relief; voluntary departure may be best available option"
        else:
            primary = viable_relief[0]

        return RemovalDefenseStrategy(
            viable_relief=viable_relief,
            primary_strategy=primary,
            strengths=strengths or ["Length of US residence", "Community ties"],
            weaknesses=weaknesses,
            immediate_actions=immediate,
            timeline="Master Calendar → Individual Hearing (often 2-4 years) → BIA → Circuit Court",
            probability_of_success=0.6 if len(viable_relief) >= 2 else 0.35,
            key_statutes=[
                "INA § 240A — Cancellation of Removal",
                "INA § 208 — Asylum",
                "INA § 241(b)(3) — Withholding of Removal",
                "8 CFR § 1208.16 — CAT",
            ],
        )

    def daca_analysis(self, facts: dict) -> DACAAnalysis:
        """
        Analyze DACA eligibility and current program status.

        Args:
            facts: Dict with DACA facts (age_at_arrival, arrival_date, us_since_2007,
                   currently_in_school_or_graduated, criminal_history).

        Returns:
            DACAAnalysis with eligibility and program status.

        Example:
            >>> engine = ImmigrationEngine()
            >>> result = engine.daca_analysis({
            ...     "age_at_arrival": 5, "us_since_2007": True,
            ...     "hs_graduate": True, "criminal_history": False
            ... })
            >>> result.eligible
            True
        """
        age_at_arrival = facts.get("age_at_arrival", 99)
        us_since_2007 = facts.get("us_since_2007", False)  # June 15, 2007
        born_after_june_1981 = facts.get("born_after_june_1981", True)
        in_school = facts.get("in_school", False)
        hs_grad = facts.get("hs_graduate", False)
        ged = facts.get("ged", False)
        military = facts.get("honorably_discharged", False)
        criminal = facts.get("criminal_history", False)
        felony = facts.get("felony", False)
        three_misdemeanors = facts.get("three_misdemeanors", False)

        age_at_entry_met = age_at_arrival < 16
        education_met = in_school or hs_grad or ged or military
        criminal_bar = felony or three_misdemeanors

        # DACA eligibility criteria
        eligible = (
            age_at_entry_met and
            us_since_2007 and
            born_after_june_1981 and
            education_met and
            not criminal_bar
        )

        benefits = [
            "Work authorization (Employment Authorization Document — EAD)",
            "Social Security Number",
            "Driver's license eligibility in most states",
            "Deferred action (not a deportation priority)",
            "Potential for advance parole (travel with permission)",
        ]

        limitations = [
            "NOT a path to citizenship or green card (legislative solution needed)",
            "Must renew every 2 years",
            "Does not confer lawful status",
            "Can be revoked at any time by administration",
            "No federal financial aid for DACA recipients (varies by state)",
        ]

        return DACAAnalysis(
            eligible=eligible,
            age_at_entry_met=age_at_entry_met,
            continuous_residence_met=us_since_2007,
            education_met=education_met,
            criminal_bars=criminal_bar,
            current_program_status=(
                "ACTIVE — USCIS accepting initial and renewal DACA applications per court orders. "
                "Status as of 2024: ongoing litigation in 5th Circuit; new applications blocked in "
                "certain states but renewals continuing nationwide. Monitor USCIS.gov for updates."
            ),
            benefits=benefits,
            limitations=limitations,
            litigation_status=(
                "United States v. Texas (5th Cir.) — DACA program constitutionality under litigation. "
                "New initial applications blocked in some jurisdictions. Renewals continuing. "
                "Supreme Court has not definitively resolved program's future."
            ),
        )

    def asylum_analysis(self, facts: dict) -> AsylumAnalysis:
        """
        Analyze asylum claim viability.

        The five protected grounds under INA § 101(a)(42):
        1. Race
        2. Religion
        3. Nationality
        4. Political Opinion
        5. Particular Social Group (PSG)

        Args:
            facts: Dict with asylum facts (ground, persecution, nexus, one_year_filing, etc.).

        Returns:
            AsylumAnalysis with viability and strength assessment.

        Example:
            >>> engine = ImmigrationEngine()
            >>> result = engine.asylum_analysis({
            ...     "ground": "political opinion",
            ...     "past_persecution": True,
            ...     "one_year_filing": True
            ... })
            >>> result.viable
            True
        """
        ground = facts.get("ground", "political opinion")
        past_persecution = facts.get("past_persecution", False)
        fear_of_future = facts.get("well_founded_fear", facts.get("fear_of_future", True))
        nexus = facts.get("nexus", True)  # Persecution ON ACCOUNT OF protected ground
        one_year = facts.get("one_year_filing", True)
        country_conditions = facts.get("country_conditions_support", False)

        # Bars to asylum
        bars = []
        if facts.get("persecutor", False):
            bars.append("Persecutor bar — participated in persecution of others")
        if facts.get("particularly_serious_crime", False):
            bars.append("Particularly serious crime bar (aggravated felony or other PSC)")
        if facts.get("security_danger", False):
            bars.append("National security danger bar")
        if facts.get("firmly_resettled", False):
            bars.append("Firmly resettled in third country bar")
        if not one_year and not facts.get("changed_circumstances", False):
            bars.append("One-year filing deadline missed without changed/extraordinary circumstances exception")

        # Withholding (higher standard — 51%+ chance of persecution)
        withholding = past_persecution or (fear_of_future and nexus)

        # CAT (torture by government/government acquiescence)
        cat = facts.get("torture_risk", False) and facts.get("government_involvement", False)

        # Strength
        strength = 0.4
        if past_persecution:
            strength += 0.25  # Creates rebuttable presumption
        if country_conditions:
            strength += 0.15
        if nexus:
            strength += 0.10
        if one_year:
            strength += 0.05
        strength = min(0.90, strength)

        # Credibility
        credibility = [
            "Consistent, detailed, specific testimony is critical",
            "Corroborating evidence: country conditions reports, witnesses, medical/police records",
            "Demeanor, plausibility, consistency across application and hearing",
        ]

        viable = (bool(ground) and (past_persecution or fear_of_future) and nexus and
                  not any("persecutor" in b or "security" in b for b in bars))

        return AsylumAnalysis(
            viable=viable,
            ground=ground,
            well_founded_fear=fear_of_future,
            past_persecution=past_persecution,
            nexus=nexus,
            bars_to_asylum=bars,
            one_year_filing_deadline_met=one_year,
            withholding_viable=withholding,
            cat_viable=cat,
            strength_assessment=strength,
            country_conditions_support=country_conditions,
            credibility_factors=credibility,
        )

    def employer_compliance_audit(self, facts: dict) -> I9ComplianceReport:
        """
        Conduct an I-9 employer compliance audit.

        Args:
            facts: Dict with employer info (num_employees, i9_completed_all, reverification_done,
                   e_verify_enrolled, document_issues, etc.).

        Returns:
            I9ComplianceReport with violations and recommendations.

        Example:
            >>> engine = ImmigrationEngine()
            >>> report = engine.employer_compliance_audit({
            ...     "num_employees": 50, "i9_completed_all": False,
            ...     "missing_i9s": 3
            ... })
            >>> report.compliant
            False
        """
        num_employees = facts.get("num_employees", 0)
        all_completed = facts.get("i9_completed_all", True)
        missing = facts.get("missing_i9s", 0)
        expired_docs = facts.get("expired_documents_accepted", False)
        reverification = facts.get("reverification_done", True)
        e_verify = facts.get("e_verify_enrolled", False)
        knowingly_hired = facts.get("knowingly_hired_unauthorized", False)

        violations = []
        recommendations = []

        if missing > 0:
            violations.append(f"{missing} employees missing I-9 forms — required for all employees hired after Nov 6, 1986")
            recommendations.append(f"Complete I-9 for all {missing} employees immediately")

        if expired_docs:
            violations.append("Employer accepted expired List A, B, or C documents — not permitted")
            recommendations.append("Train HR on acceptable I-9 documents; expired documents not acceptable except for auto-extended documents")

        if not reverification and facts.get("employees_with_expiring_work_auth", False):
            violations.append("Failure to reverify employees with expiring work authorization")
            recommendations.append("Establish tickler system for reverification 90 days before EAD expiration")

        if knowingly_hired:
            violations.append("Knowing hire of unauthorized worker — civil and criminal penalties apply")
            recommendations.append("URGENT: Consult immigration counsel immediately; criminal referral risk")

        # Civil penalty range (2024 rates)
        if violations:
            if knowingly_hired:
                penalty_range = "$698 - $27,894 per unauthorized worker (civil); criminal up to 6 months"
            else:
                penalty_range = "$272 - $2,701 per paperwork violation (first offense)"
        else:
            penalty_range = "No violations — no penalties"

        compliant = len(violations) == 0

        recommendations.extend([
            "Conduct annual I-9 self-audit",
            "Train all HR personnel on I-9 completion requirements",
            "Store I-9 forms separately from personnel files",
            "Retain I-9 for 3 years from hire OR 1 year from separation (whichever is later)",
            "Consider E-Verify enrollment for additional protection",
        ])

        return I9ComplianceReport(
            compliant=compliant,
            violations=violations,
            civil_penalty_range=penalty_range,
            recommendations=recommendations,
            audit_date=facts.get("audit_date", ""),
            criminal_penalty_risk=knowingly_hired,
            e_verify_status="Enrolled" if e_verify else "Not enrolled",
        )

    def inadmissibility_waivers(self, grounds: List[str]) -> WaiverStrategy:
        """
        Identify available waivers for inadmissibility grounds.

        Args:
            grounds: List of inadmissibility grounds (e.g., ["unlawful_presence", "prior_removal"]).

        Returns:
            WaiverStrategy with available waivers and requirements.

        Example:
            >>> engine = ImmigrationEngine()
            >>> strategy = engine.inadmissibility_waivers(["unlawful_presence", "prior_removal"])
            >>> len(strategy.available_waivers) >= 1
            True
        """
        available_waivers = []
        required_forms = []
        hardship_required = False
        qualifying_relatives = []
        approval_likelihood = 0.5

        waiver_map = {
            "unlawful_presence": {
                "waiver": "I-601A Provisional Unlawful Presence Waiver",
                "form": "I-601A",
                "hardship": True,
                "qualifying_relatives": ["US citizen or LPR spouse or parent"],
                "likelihood": 0.65,
                "notes": "3-year bar for 6-12 months; 10-year bar for 12+ months unlawful presence",
            },
            "prior_removal": {
                "waiver": "I-212 Application for Permission to Reapply",
                "form": "I-212",
                "hardship": False,
                "qualifying_relatives": [],
                "likelihood": 0.70,
                "notes": "Discretionary; 10-year bar for most; 20-year for aggravated felons",
            },
            "criminal_ground": {
                "waiver": "I-601 Waiver of Grounds of Inadmissibility",
                "form": "I-601",
                "hardship": True,
                "qualifying_relatives": ["US citizen or LPR spouse or parent"],
                "likelihood": 0.55,
                "notes": "Covers crimes involving moral turpitude; not available for aggravated felonies",
            },
            "misrepresentation": {
                "waiver": "I-601 Waiver (INA § 212(i))",
                "form": "I-601",
                "hardship": True,
                "qualifying_relatives": ["US citizen or LPR spouse or parent"],
                "likelihood": 0.60,
            },
            "public_charge": {
                "waiver": "I-944 Declaration of Self-Sufficiency (not a waiver per se)",
                "form": "I-944",
                "hardship": False,
                "qualifying_relatives": [],
                "likelihood": 0.75,
            },
            "health_related": {
                "waiver": "I-601 Health-Related Waiver (INA § 212(g))",
                "form": "I-601",
                "hardship": False,
                "qualifying_relatives": ["USC/LPR parent, spouse, or son/daughter"],
                "likelihood": 0.80,
            },
        }

        for ground in grounds:
            ground_lower = ground.lower().replace(" ", "_")
            for key, info in waiver_map.items():
                if key in ground_lower or ground_lower in key:
                    available_waivers.append(info["waiver"])
                    required_forms.append(info["form"])
                    if info.get("hardship"):
                        hardship_required = True
                    qualifying_relatives.extend(info.get("qualifying_relatives", []))
                    approval_likelihood = (approval_likelihood + info.get("likelihood", 0.5)) / 2

        if not available_waivers:
            available_waivers = ["Consult immigration attorney — grounds may not have waiver available"]
            approval_likelihood = 0.3

        return WaiverStrategy(
            grounds=grounds,
            available_waivers=list(set(available_waivers)),
            hardship_required=hardship_required,
            qualifying_relatives=list(set(qualifying_relatives)),
            approval_likelihood=approval_likelihood,
            required_forms=list(set(required_forms)),
            timeline="6-18 months processing typical",
            notes=(
                "Hardship waivers require showing 'extreme hardship' to qualifying relatives (US citizen or LPR). "
                "Self-hardship and general hardship are insufficient — must show hardship beyond that normally expected. "
                "Aggregate hardship factors (economic, medical, educational, country conditions) to maximize chances."
            ),
        )
