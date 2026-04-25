"""
Real Estate Intelligence — Master Real Estate from Purchase to Portfolio
SintraPrime Life & Entity Governance Engine
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class HomePurchaseStrategy:
    """Comprehensive home purchase strategy."""
    pre_approval_steps: List[str]
    offer_strategy: Dict[str, Any]
    inspection_guide: str
    title_insurance_guide: str
    closing_cost_breakdown: Dict[str, Any]
    first_time_buyer_programs: List[str]
    down_payment_assistance: List[str]
    timeline: str


@dataclass
class MortgageStrategy:
    """Comprehensive mortgage optimization strategy."""
    loan_type_comparison: List[Dict[str, Any]]
    rate_shopping_strategy: str
    points_analysis: Dict[str, Any]
    arm_vs_fixed: str
    refinance_analysis: Dict[str, Any]
    pmi_elimination: List[str]
    total_interest_calculator: str


@dataclass
class LandlordGuide:
    """State-specific landlord guide."""
    state: str
    lease_essentials: List[str]
    security_deposit_rules: str
    eviction_process: str
    fair_housing_compliance: List[str]
    required_disclosures: List[str]
    rent_control_info: str
    landlord_rights: List[str]
    tenant_rights: List[str]


@dataclass
class InvestmentRealEstateGuide:
    """Real estate investment strategy guide."""
    strategy: str
    strategy_description: str
    how_to_execute: List[str]
    financing_options: List[str]
    tax_advantages: List[str]
    risks: List[str]
    expected_returns: str
    getting_started: List[str]


@dataclass
class DeedGuide:
    """Guide to types of deeds and when to use each."""
    deed_types: List[Dict[str, str]]
    tod_deed_states: List[str]
    lady_bird_deed_states: List[str]
    transfer_to_trust_guidance: str
    recording_requirements: str


# ---------------------------------------------------------------------------
# State-specific data
# ---------------------------------------------------------------------------

SECURITY_DEPOSIT_RULES: Dict[str, Dict[str, Any]] = {
    "CA": {"max": "2 months (unfurnished), 3 months (furnished)", "return_days": 21, "interest_required": False},
    "NY": {"max": "1 month", "return_days": 14, "interest_required": True, "notes": "Interest required for buildings with 6+ units"},
    "FL": {"max": "None (no statutory limit)", "return_days": 15, "interest_required": False},
    "TX": {"max": "None (no statutory limit)", "return_days": 30, "interest_required": False},
    "WA": {"max": "None", "return_days": 21, "interest_required": False},
    "IL": {"max": "None (Chicago: 1.5 months)", "return_days": 30, "interest_required": False},
    "MA": {"max": "1 month", "return_days": 30, "interest_required": True},
    "CO": {"max": "2 months (1 month if pet-free)", "return_days": 30, "interest_required": False},
    "GA": {"max": "None", "return_days": 30, "interest_required": False},
    "AZ": {"max": "1.5 months", "return_days": 14, "interest_required": False},
    "DEFAULT": {"max": "Varies by state — no statutory limit in many states", "return_days": 30, "interest_required": False},
}

EVICTION_TIMELINES: Dict[str, str] = {
    "CA": "3-day Notice → 30-day Notice (1-yr lease or less) → Unlawful Detainer filing → Court hearing (20-45 days) → Writ of Possession → Sheriff lockout. Total: 45-120 days minimum.",
    "TX": "3-day Notice to Vacate → Justice of Peace filing → Hearing (10-21 days) → Writ of Possession → Constable lockout. Total: 30-60 days.",
    "FL": "3-day Notice (non-payment) or 7-day Notice (lease violation) → Circuit Court filing → Hearing → Writ of Possession → Sheriff enforcement. Total: 30-90 days.",
    "NY": "14-day Rent Demand (non-payment) or 10-day Notice (violation) → Housing Court filing → Trial → Warrant of Eviction → Marshal. Total: 60-180+ days (tenant-friendly).",
    "WA": "3-day Notice (non-payment) or 10-day Notice (violation) → Unlawful Detainer filing → Court hearing → Sheriff enforcement. Total: 30-60 days.",
    "DEFAULT": "Typically: Notice period (3-30 days) → Court filing → Hearing → Writ → Sheriff enforcement. Total: 30-90 days. Never use self-help eviction — illegal in all states.",
}

RENT_CONTROL_STATES: Dict[str, str] = {
    "CA": "Statewide AB 1482 (5% + CPI max increase for buildings 15+ years old). Additional local ordinances: LA, SF, Oakland, San Jose.",
    "NY": "NYC Rent Stabilization and Rent Control for qualifying units. Vacancy decontrol eliminated (2019).",
    "OR": "Statewide: 7% + CPI max (first state with statewide rent control).",
    "NJ": "Municipal rent control — varies by city (Newark, Jersey City, etc.).",
    "MD": "Montgomery County, Prince George's County have rent control.",
    "WA": "No statewide rent control. Seattle restrictions on move-in fees.",
    "DEFAULT": "No statewide rent control.",
}

TOD_DEED_STATES = [
    "AK", "AZ", "AR", "CA", "CO", "DC", "HI", "IL", "IN", "KS", "MN",
    "MO", "MT", "NE", "NV", "NM", "ND", "OH", "OK", "OR", "SD", "TX",
    "UT", "VA", "WA", "WV", "WI", "WY",
]

LADY_BIRD_DEED_STATES = ["FL", "TX", "MI", "VT", "WV"]


# ---------------------------------------------------------------------------
# Real Estate Intelligence
# ---------------------------------------------------------------------------

class RealEstateIntelligence:
    """
    Master real estate intelligence engine.

    Covers home purchase, mortgage optimization, landlord guidance,
    investment strategies, and deed types.
    """

    def home_purchase_guide(self, facts: dict) -> HomePurchaseStrategy:
        """
        Generate a comprehensive home purchase strategy.

        Args:
            facts: dict with 'purchase_price', 'down_payment', 'credit_score',
                   'state', 'first_time_buyer', 'veteran', 'income',
                   'debt_monthly'
        """
        purchase_price = facts.get("purchase_price", 500_000)
        down_payment_pct = facts.get("down_payment_pct", 0.20)
        down_payment = facts.get("down_payment", purchase_price * down_payment_pct)
        credit_score = facts.get("credit_score", 740)
        state = facts.get("state", "CA")
        first_time_buyer = facts.get("first_time_buyer", False)
        veteran = facts.get("veteran", False)
        income = facts.get("income", 150_000)

        pre_approval_steps = [
            "1. Pull all 3 credit reports (AnnualCreditReport.com — free). Dispute errors 30+ days before applying.",
            "2. Pay down revolving debt to below 30% utilization (ideally <10%).",
            "3. Do NOT open new credit accounts or close old ones for 6 months before applying.",
            "4. Document income: 2 years W-2s, recent pay stubs, bank statements (3 months).",
            f"5. Calculate maximum mortgage: Monthly payment should not exceed 28% of gross income (${income * 0.28 / 12:,.0f}/month max).",
            "6. Get pre-approval letters from 3+ lenders (multiple inquiries within 45 days = 1 hard pull).",
            "7. Lock rate when you have an accepted offer (rate locks: 30-60 days typically).",
        ]

        offer_strategy = {
            "competitive_market_tactics": [
                "Escalation clause: 'I offer $X, and will beat any bona fide offer by $Y, up to $Z'",
                "Larger earnest money deposit (2-3% instead of 1%) — signals seriousness",
                "Shorter inspection contingency period (7-10 days instead of 14)",
                "Flexible closing date — accommodate seller's timeline",
                "Pre-approval letter (not just pre-qualification) in offer package",
                "Personal letter to seller (where legally permitted — avoid Fair Housing issues)",
            ],
            "contingencies_to_keep": [
                "Financing contingency — protects earnest money if loan falls through",
                "Inspection contingency — allows negotiation on defects",
                "Appraisal contingency — protection if home appraises below purchase price",
            ],
            "negotiation_leverage": [
                "Seller's closing costs contribution (up to 3% conventional)",
                "Home warranty (1 year, ~$500-$700 cost to seller)",
                "Repair credits instead of actual repairs (faster closing)",
                "Personal property inclusion (appliances, furniture)",
            ],
        }

        inspection_guide = (
            f"Budget ${purchase_price * 0.003:,.0f}-${purchase_price * 0.005:,.0f} for inspections. "
            "Standard inspection covers: foundation, roof, electrical, plumbing, HVAC, structure. "
            "Specialty inspections: pest/termite, sewer scope, radon, mold, lead paint (pre-1978 homes). "
            "Negotiate: major defects (negotiate price reduction or repair credit); minor items (accept as-is). "
            "Walking away: foundation issues, major structural defects, active termite infestation, roof replacement needed."
        )

        title_insurance = (
            "Owner's title insurance (one-time premium ~$500-$2,000) protects against: "
            "prior liens, recording errors, fraud, missing heirs' claims, survey disputes. "
            "ALWAYS purchase owner's title insurance (lender requires lender's policy; owner's is optional but recommended). "
            "Shop around — title insurance rates are regulated in many states."
        )

        closing_costs = {
            "buyer_total_estimate": f"${purchase_price * 0.025:,.0f}-${purchase_price * 0.04:,.0f} (2.5-4% of purchase price)",
            "breakdown": {
                "Loan origination fee": f"${purchase_price * 0.01:,.0f} (0.5-1%)",
                "Appraisal": "$500-$800",
                "Title insurance (owner's)": "$500-$2,000",
                "Title insurance (lender's)": "$200-$500",
                "Attorney fee (if required)": "$500-$1,500",
                "Recording fees": "$50-$300",
                "Prepaid interest": f"${purchase_price * 0.06 / 365 * 15:,.0f} (~15 days)",
                "Property tax escrow": f"${purchase_price * 0.012 / 4:,.0f} (3 months)",
                "Homeowner's insurance escrow": f"${purchase_price * 0.003 / 4:,.0f} (3 months first)",
                "Transfer tax": f"Varies by state (${purchase_price * 0.001:,.0f}-${purchase_price * 0.015:,.0f})",
            }
        }

        ftb_programs = []
        if first_time_buyer:
            ftb_programs = [
                f"HUD-approved first-time homebuyer counseling (required for many programs)",
                "Fannie Mae HomeReady loan: 3% down, reduced PMI, flexible income sources",
                "Freddie Mac Home Possible: 3% down for low-to-moderate income buyers",
                f"{state} state first-time homebuyer program — search: '{state} first time homebuyer program'",
                "Local government down payment assistance (city/county programs — search your local housing authority)",
                "FHA loan: 3.5% down with 580+ credit score; 10% down with 500-579",
            ]

        dpa_programs = [
            "State Housing Finance Agency programs (every state has one)",
            "USDA Rural Development loan: 0% down for eligible rural/suburban areas",
            "VA loan: 0% down for veterans and active duty (no PMI ever)",
            "HUD Good Neighbor Next Door: 50% off list price for teachers, firefighters, police, EMTs",
            "Fannie Mae HomePath: 3% down on Fannie-owned foreclosures",
            "Chenoa Fund: Down payment assistance (up to 3.5% of loan amount)",
            "Down Payment Resource: downpaymentresource.com — find all programs in your area",
        ] if first_time_buyer else [
            "VA loan (0% down) for veterans" if veteran else "20% down to avoid PMI",
            "Piggyback loan (80/10/10) to avoid PMI without 20% down",
        ]

        return HomePurchaseStrategy(
            pre_approval_steps=pre_approval_steps,
            offer_strategy=offer_strategy,
            inspection_guide=inspection_guide,
            title_insurance_guide=title_insurance,
            closing_cost_breakdown=closing_costs,
            first_time_buyer_programs=ftb_programs,
            down_payment_assistance=dpa_programs,
            timeline=(
                "Pre-approval: 1-3 days → Home search: 1-6 months → Offer accepted → "
                "Inspection (7-14 days) → Appraisal (2-3 weeks) → Underwriting (2-4 weeks) → "
                "Closing (typically 30-45 days from accepted offer)"
            ),
        )

    def mortgage_optimizer(self, facts: dict) -> MortgageStrategy:
        """
        Optimize mortgage strategy for a given situation.

        Args:
            facts: dict with 'purchase_price', 'down_payment', 'credit_score',
                   'income', 'loan_amount', 'veteran', 'property_type'
        """
        purchase_price = facts.get("purchase_price", 500_000)
        down_pct = facts.get("down_payment_pct", 0.20)
        down = down_pct * purchase_price
        loan_amount = facts.get("loan_amount", purchase_price - down)
        credit_score = facts.get("credit_score", 740)
        veteran = facts.get("veteran", False)
        income = facts.get("income", 150_000)

        loan_types = [
            {
                "type": "Conventional (Conforming)",
                "min_down": "3%",
                "min_credit": 620,
                "loan_limits": "$766,550 (2024; $1,149,825 in high-cost areas)",
                "pmi": "Required if <20% down; can be removed when 20% equity reached",
                "best_for": "Borrowers with good credit and 5%+ down",
                "rate_premium": "Best rates for 740+ credit",
            },
            {
                "type": "FHA Loan",
                "min_down": "3.5% (580+ credit); 10% (500-579 credit)",
                "min_credit": 500,
                "loan_limits": "$498,257 (2024 standard); $1,149,825 (high-cost)",
                "pmi": "MIP required for life of loan if <10% down; 11 years if 10%+",
                "best_for": "Lower credit scores, first-time buyers, smaller down payment",
                "rate_premium": "Rates similar to conventional; MIP adds ~0.55-0.85% annually",
            },
            {
                "type": "VA Loan",
                "min_down": "0%",
                "min_credit": "Typically 620+ (VA has no minimum)",
                "loan_limits": "No limit for eligible veterans (with full entitlement)",
                "pmi": "NO PMI — ever. One-time funding fee (1.4-3.6%, can be financed)",
                "best_for": "Veterans, active duty, surviving spouses",
                "rate_premium": "Often 0.25-0.5% BELOW conventional rates",
            } if veteran else None,
            {
                "type": "USDA Loan",
                "min_down": "0%",
                "min_credit": "640+ preferred",
                "loan_limits": "No loan limit; income limits apply (typically ≤115% area median income)",
                "pmi": "Annual fee: 0.35% of loan balance; upfront: 1%",
                "best_for": "Rural and some suburban areas; moderate income borrowers",
                "rate_premium": "Competitive rates; great for eligible areas",
            },
            {
                "type": "Jumbo Loan",
                "min_down": "10-20%",
                "min_credit": "700-720 minimum; 740+ for best rates",
                "loan_limits": "Above conforming limits ($766,550+)",
                "pmi": "Varies by lender; some require none with 20% down",
                "best_for": "High-cost area purchases above conforming limits",
                "rate_premium": "Historically higher; recent market: sometimes same or lower than conforming",
            },
        ]
        loan_types = [lt for lt in loan_types if lt is not None]

        points_analysis = {
            "what_are_points": "Each discount point = 1% of loan amount paid upfront to lower interest rate (typically 0.25% rate reduction per point)",
            "example": f"On ${loan_amount:,.0f} loan: 1 point = ${loan_amount * 0.01:,.0f} upfront; saves ~${loan_amount * 0.0025 / 12:,.0f}/month",
            "break_even": f"${loan_amount * 0.01:,.0f} / ${loan_amount * 0.0025 / 12:,.0f}/month savings = {(loan_amount * 0.01) / (loan_amount * 0.0025 / 12):.0f} months to break even",
            "buy_points_if": "You plan to stay longer than break-even period AND have cash available",
            "skip_points_if": "You might sell or refinance within 5-7 years",
        }

        arm_vs_fixed = (
            "FIXED RATE: Rate locked for life of loan. Best for: long-term ownership (7+ years), "
            "risk-averse borrowers, when rates are relatively low. "
            "ADJUSTABLE RATE MORTGAGE (ARM): Fixed for initial period (5/1, 7/1, 10/1), then adjusts annually. "
            f"ARM currently offers lower initial rate (typically 0.5-1% lower). "
            "Best for: borrowers who plan to sell or refinance before adjustment period, "
            "expect rates to fall, or want lower initial payment. "
            "Risk: Rates can adjust significantly after fixed period — understand caps (periodic and lifetime)."
        )

        refinance_analysis = {
            "when_to_refinance": [
                "Rate drops 0.75%+ below your current rate",
                "Credit score improved significantly since original loan",
                "Switching from ARM to fixed before adjustment",
                "Cash-out refinance for home improvement (interest may be deductible)",
                "Removing PMI (if equity reached 20%)",
                "Shortening loan term (30-year to 15-year)",
            ],
            "break_even_formula": "Closing costs / Monthly savings = Months to break even",
            "rate_and_term_vs_cashout": "Rate-and-term: Lower rate; Cash-out: Access equity (rate slightly higher)",
            "costs": f"Typically ${loan_amount * 0.02:,.0f}-${loan_amount * 0.03:,.0f} in closing costs (2-3% of loan)",
            "npv_analysis": "Calculate net present value considering time value of money for refinance decisions",
        }

        pmi_elimination = [
            "Make 20% down payment — avoid PMI entirely",
            "Piggyback loan (80/10/10 or 80/15/5) — no PMI on first mortgage",
            "Request PMI cancellation when loan reaches 80% LTV (you must request it)",
            "Automatic cancellation at 78% LTV (Homeowners Protection Act requires this)",
            "Appraise the home — if market appreciation brought LTV below 80%, request removal",
            "Make extra principal payments to reach 80% faster",
            "Lender-paid PMI (LPMI) — slightly higher rate; PMI built into rate (non-cancellable)",
        ]

        return MortgageStrategy(
            loan_type_comparison=loan_types,
            rate_shopping_strategy=(
                "RATE SHOPPING STRATEGY: Apply to 3-5 lenders within 14-45 days "
                "(FICO treats multiple mortgage inquiries as single inquiry if within window). "
                "Compare: APR (not just rate), points, origination fees, closing costs. "
                "Check: Banks, credit unions, mortgage brokers, online lenders (Better, Rocket, loanDepot). "
                "Negotiate: Ask each lender to beat the best offer you've received."
            ),
            points_analysis=points_analysis,
            arm_vs_fixed=arm_vs_fixed,
            refinance_analysis=refinance_analysis,
            pmi_elimination=pmi_elimination,
            total_interest_calculator=(
                f"30-year vs 15-year comparison on ${loan_amount:,.0f} at 7% vs 6.5%: "
                f"30-year: ${loan_amount * 0.00665 * 360:,.0f} total interest. "
                f"15-year: ${loan_amount * 0.00872 * 180:,.0f} total interest. "
                f"Savings: ${(loan_amount * 0.00665 * 360) - (loan_amount * 0.00872 * 180):,.0f} — "
                "but consider opportunity cost of extra payments."
            ),
        )

    def landlord_legal_guide(self, state: str) -> LandlordGuide:
        """
        Generate a comprehensive state-specific landlord legal guide.

        Args:
            state: Two-letter state code
        """
        state = state.upper()
        deposit_rules = SECURITY_DEPOSIT_RULES.get(state, SECURITY_DEPOSIT_RULES["DEFAULT"])
        eviction = EVICTION_TIMELINES.get(state, EVICTION_TIMELINES["DEFAULT"])
        rent_control = RENT_CONTROL_STATES.get(state, RENT_CONTROL_STATES["DEFAULT"])

        lease_essentials = [
            "Names of all tenants and landlord",
            "Property address and description (unit number, parking space, storage)",
            "Lease term: start date and end date (or month-to-month)",
            "Rent amount and due date (and grace period, if any)",
            "Late fee: typically 5-10% of monthly rent; must comply with state law",
            "Security deposit amount and conditions for deductions",
            "Pet policy (allowed/not allowed, pet deposit/fee, breed restrictions)",
            "Maintenance responsibilities (who pays for what)",
            "Entry notice requirements (24-48 hours in most states)",
            "Subletting policy",
            "Smoking policy",
            "Guest policy (definition of unauthorized occupants)",
            "Utilities — which are included vs. tenant-paid",
            "Parking rules",
            "HOA rules if applicable",
            "Renewal terms (automatic vs. must give notice)",
            "Termination and notice requirements",
            "Governing law (state of property)",
        ]

        disclosures = [
            "Lead-based paint disclosure (required for all pre-1978 properties — federal law)",
            "Carbon monoxide detector disclosure",
            "Smoke detector compliance",
            "Mold disclosure (required in many states — CA, TX, etc.)",
            "Asbestos disclosure (pre-1981 properties)",
            "Sexual offender registry notification (some states)",
            "Known defects / habitability issues",
            "Bed bug disclosure (required in some states)",
            f"{state}-specific disclosures — check state landlord-tenant act",
        ]

        return LandlordGuide(
            state=state,
            lease_essentials=lease_essentials,
            security_deposit_rules=(
                f"Maximum: {deposit_rules['max']}. "
                f"Return deadline: {deposit_rules['return_days']} days after move-out. "
                f"Interest required: {'Yes' if deposit_rules.get('interest_required') else 'No'}. "
                f"Must provide itemized deduction list with receipts. "
                f"Keep deposit in SEPARATE bank account (required in many states). "
                f"Notes: {deposit_rules.get('notes', 'N/A')}"
            ),
            eviction_process=eviction,
            fair_housing_compliance=[
                "Federal Fair Housing Act prohibits discrimination based on:",
                "Race, Color, National Origin, Religion, Sex, Familial Status, Disability",
                "Additional protected classes in many states: Sexual orientation, source of income, marital status",
                "NEVER advertise 'no children' or 'adults only' (familial status discrimination)",
                "NEVER ask about disability; DO make reasonable accommodations",
                "Screen tenants consistently using objective criteria",
                "Document all screening decisions",
                "Use HUD-approved screening criteria",
            ],
            required_disclosures=disclosures,
            rent_control_info=rent_control,
            landlord_rights=[
                "Right to receive rent on time",
                "Right to inspect property with proper notice (24-48 hours in most states)",
                "Right to evict for non-payment or lease violation (following legal process)",
                "Right to not renew lease (with proper notice, outside rent control)",
                "Right to enter for emergencies without notice",
                "Right to screen tenants using objective criteria",
            ],
            tenant_rights=[
                "Right to habitable dwelling (Implied Warranty of Habitability)",
                "Right to quiet enjoyment",
                "Right to privacy (proper notice before entry)",
                "Right to return of security deposit with itemization",
                "Protection from retaliation for reporting habitability issues",
                "Right to repair-and-deduct in many states",
            ],
        )

    def real_estate_investor_guide(self, strategy: str) -> InvestmentRealEstateGuide:
        """
        Generate a guide for a specific real estate investment strategy.

        Args:
            strategy: One of 'brrrr', 'house_hacking', 'short_term_rental',
                       'commercial', 'syndication', 'dst_1031'
        """
        strategies = {
            "brrrr": {
                "description": "Buy Rehab Rent Refinance Repeat — recycle capital across multiple properties",
                "execute": [
                    "BUY: Find distressed property at 70-75% ARV (After Repair Value) minus repair costs",
                    "REHAB: Renovate to rentable condition; focus on kitchens, baths, mechanicals",
                    "RENT: Lease to qualified tenant; stable cash flow demonstrates value for refi",
                    "REFINANCE: Cash-out refinance at 75-80% LTV of new appraised value",
                    "REPEAT: Use cash-out proceeds to buy next property",
                ],
                "financing": ["Hard money loan for purchase+rehab (12-18% interest, short-term)", "DSCR loan for refinance (no income verification)", "Portfolio lender for long-term hold"],
                "tax_advantages": ["Depreciation (27.5 years residential)", "Cost segregation study (accelerated depreciation)", "1031 exchange on eventual sale", "Deduct repairs, mortgage interest, property management"],
                "risks": ["Rehab cost overruns", "Finding buyers at target prices", "Refinance appraisal risk", "Vacancy during rehab"],
                "expected_returns": "Target: 12-20% cash-on-cash return; equity recycling means potentially infinite return on invested capital",
                "getting_started": ["Find off-market deals (driving for dollars, direct mail, wholesalers)", "Build contractor relationships", "Open DSCR lender relationships before needed"],
            },
            "house_hacking": {
                "description": "Live in one unit of a 2-4 unit property; rent other units to cover mortgage",
                "execute": [
                    "Purchase 2-4 unit property (multifamily) with owner-occupant financing (3.5% FHA or 5% conventional)",
                    "Live in one unit; rent remaining units",
                    "Rental income offsets or eliminates mortgage payment",
                    "After 1 year, move out and repeat with new property",
                ],
                "financing": ["FHA loan: 3.5% down on 2-4 unit", "Conventional: 5-15% down on 2-4 unit", "VA loan: 0% down (veterans)", "75% of rents can be added to qualifying income"],
                "tax_advantages": ["Depreciate rental portion of property", "Deduct proportional expenses (mortgage interest, insurance, repairs)", "Potential primary residence capital gains exclusion on sale"],
                "risks": ["Living next to tenants (privacy, neighbor issues)", "Vacancy risk", "Property management while living on-site"],
                "expected_returns": "Many house hackers live for free or near-free; 20-30%+ cash-on-cash in strong markets",
                "getting_started": ["Target neighborhoods with strong rental demand", "Calculate numbers: PITI vs. market rents for non-owner units", "Screen tenants carefully — they're neighbors"],
            },
            "short_term_rental": {
                "description": "Airbnb/VRBO rental — highest nightly rates but more management intensive",
                "execute": [
                    "Research market (AirDNA, Mashvisor) for occupancy rates and ADR",
                    "Purchase property in vacation/travel market or urban center",
                    "Furnish and equip to 5-star standard (professional photography)",
                    "List on Airbnb, VRBO, Booking.com",
                    "Hire property manager (20-30% of revenue) or self-manage",
                ],
                "financing": ["Conventional 20-25% down (investment property)", "DSCR loan — qualifies on projected rental income", "AirBnb-specific lenders emerging"],
                "tax_advantages": ["Bonus depreciation on furnishings (100% first year)", "Augusta Rule: Rent your home up to 14 days/year tax-free", "Business deductions if meet material participation test"],
                "risks": ["Regulatory risk (cities restricting STRs)", "Seasonality", "Platform rule changes", "High management intensity", "HOA restrictions"],
                "expected_returns": "2-3x long-term rental revenue in strong markets; significant variability",
                "getting_started": ["Check local regulations before buying", "Use AirDNA to analyze market", "Start with one property before scaling"],
            },
            "commercial": {
                "description": "Commercial real estate: office, retail, industrial, multifamily 5+ units",
                "execute": [
                    "Identify asset class: multifamily, industrial, retail, office, mixed-use",
                    "Analyze: NOI (Net Operating Income), Cap Rate, DSCR",
                    "Due diligence: rent rolls, leases, environmental phase I/II",
                    "Finance with commercial loan (20-35% down, 5-10 year term)",
                    "Professional property management typically required",
                ],
                "financing": ["Commercial mortgage (5-year term, 20-year amortization)", "SBA 504 loan (owner-occupied commercial)", "CMBS loan for large deals", "Life company loans for top-quality properties"],
                "tax_advantages": ["39-year depreciation (commercial) vs 27.5 (residential)", "Triple net leases (tenant pays all operating expenses)", "1031 exchange", "Opportunity Zone investment (capital gains deferral)"],
                "risks": ["Higher complexity", "Economic sensitivity (office especially)", "Larger capital requirements", "Longer vacancy risk"],
                "expected_returns": "Cap rates typically 5-8%; total returns 8-15%",
                "getting_started": ["Join local commercial real estate investors network", "Start with small multifamily (5-20 units)", "Partner with experienced operator on first deal"],
            },
            "syndication": {
                "description": "Passive investment in real estate partnerships as a limited partner",
                "execute": [
                    "Find syndication sponsor (operator) — research track record",
                    "Review PPM (Private Placement Memorandum) with attorney",
                    "Invest as LP (typically $25,000-$100,000 minimum)",
                    "Receive quarterly distributions and K-1 at year end",
                    "Exit when property sold (typically 5-7 year hold)",
                ],
                "financing": ["Your cash investment only (no leverage for LPs)", "Syndicate uses commercial financing on property level"],
                "tax_advantages": ["Passive losses from depreciation (shelter other passive income)", "K-1 tax benefits flow through to investors", "1031 exchange at entity level (may not flow to LPs)", "Preferred return typically 6-8%"],
                "risks": ["Illiquid — cannot exit early", "Dependent on sponsor's skill", "No control as LP", "Market risk"],
                "expected_returns": "Target: 15-20% IRR; 1.5-2.5x equity multiple over 5-7 years",
                "getting_started": ["Must be Accredited Investor ($1M net worth or $200K income)", "Research on CrowdStreet, RealtyMogul, or direct sponsor relationships"],
            },
            "dst_1031": {
                "description": "Delaware Statutory Trust — 1031 exchange into passive ownership of institutional properties",
                "execute": [
                    "Sell investment property; identify DST within 45 days",
                    "Choose DST sponsor (large, institutional-quality properties)",
                    "Invest 1031 proceeds into DST (minimum typically $100K-$250K)",
                    "Passive investor — no management responsibility",
                    "Receive monthly income distributions",
                    "DST typically holds 5-10 years then sells; can 1031 again",
                ],
                "financing": ["All cash — exchange proceeds fund DST investment"],
                "tax_advantages": ["Defers capital gains and depreciation recapture from sold property", "Receive depreciation on DST property (new basis)", "Potentially 1031 again when DST sells"],
                "risks": ["Illiquid (7-10 year hold typically)", "Must trust DST sponsor", "Limited upside potential vs active ownership"],
                "expected_returns": "Income: 4-6%/year; Total: 8-12% including appreciation",
                "getting_started": ["Work with 1031 exchange intermediary (QI) before closing sale", "Research DST sponsors: ExchangeRight, Inland, Passco, AEI"],
            },
        }

        strategy_data = strategies.get(strategy.lower(), strategies["brrrr"])

        return InvestmentRealEstateGuide(
            strategy=strategy,
            strategy_description=strategy_data["description"],
            how_to_execute=strategy_data["execute"],
            financing_options=strategy_data["financing"],
            tax_advantages=strategy_data["tax_advantages"],
            risks=strategy_data["risks"],
            expected_returns=strategy_data["expected_returns"],
            getting_started=strategy_data["getting_started"],
        )

    def deed_types_guide(self) -> DeedGuide:
        """
        Comprehensive guide to deed types and when to use each.
        """
        deed_types = [
            {
                "type": "General Warranty Deed",
                "description": "Grantor warrants title against ALL claims (including claims arising before grantor owned property)",
                "grantor_liability": "Highest — warrants entire chain of title",
                "when_to_use": "Standard residential sales between unrelated parties; arm's-length transactions",
                "when_not_to_use": "Foreclosure sales, estate sales, family transfers",
            },
            {
                "type": "Special Warranty Deed (Limited Warranty)",
                "description": "Grantor warrants only against defects arising DURING grantor's ownership",
                "grantor_liability": "Moderate — limited to grantor's period of ownership",
                "when_to_use": "Commercial real estate sales, bank/lender sales, foreclosure sales",
                "when_not_to_use": "Buyer should be cautious — doesn't cover prior title issues",
            },
            {
                "type": "Quitclaim Deed",
                "description": "Transfers whatever interest grantor has — no warranties whatsoever",
                "grantor_liability": "None — no title warranty",
                "when_to_use": "Family transfers, divorce property settlement, adding/removing spouse, correcting deed errors, transferring to LLC or trust",
                "when_not_to_use": "Arm's-length sales — buyer has no title protection",
            },
            {
                "type": "Grant Deed (California)",
                "description": "California version — implies two warranties: (1) grantor hasn't previously conveyed, (2) no encumbrances added by grantor",
                "grantor_liability": "Moderate — implied warranties",
                "when_to_use": "Standard residential transfers in California",
                "when_not_to_use": "Outside California (few other states use this)",
            },
            {
                "type": "Transfer on Death Deed (TOD / Beneficiary Deed)",
                "description": "Transfers property automatically at death WITHOUT probate; grantor retains full control and can revoke during lifetime",
                "grantor_liability": "None — like a will, no current transfer",
                "when_to_use": "Estate planning to avoid probate on real estate; simple alternative to living trust for real estate",
                "when_not_to_use": "If multiple beneficiaries and uncertain wishes; if state doesn't recognize TOD deed",
                "available_states": TOD_DEED_STATES,
            },
            {
                "type": "Lady Bird Deed (Enhanced Life Estate Deed)",
                "description": "Grantor retains life estate with power to sell, mortgage, or lease without beneficiary consent. Property transfers at death without probate AND is excluded from Medicaid estate recovery.",
                "grantor_liability": "None",
                "when_to_use": "Florida, Texas, Michigan, Vermont, West Virginia estate planning; Medicaid planning; avoid probate while retaining full control",
                "when_not_to_use": "Outside the 5 states where recognized",
                "available_states": LADY_BIRD_DEED_STATES,
            },
            {
                "type": "Trustee's Deed",
                "description": "Used when a trustee (of a trust) conveys real property",
                "grantor_liability": "Special warranty as trustee",
                "when_to_use": "Sales by living trust trustee; sales by trustee in bankruptcy; foreclosure trustee sales",
                "when_not_to_use": "Non-trust transactions",
            },
        ]

        return DeedGuide(
            deed_types=deed_types,
            tod_deed_states=TOD_DEED_STATES,
            lady_bird_deed_states=LADY_BIRD_DEED_STATES,
            transfer_to_trust_guidance=(
                "To transfer real estate to a revocable living trust: "
                "Prepare a deed (usually quitclaim or grant deed) FROM '[Your Name]' "
                "TO '[Your Name], Trustee of [Trust Name] dated [Date]'. "
                "Record with County Recorder/Register of Deeds. "
                "Cost: Recording fee ($15-$50). "
                "NOTE: Informs mortgage lender (Garn-St. Germain Act allows transfer to living trust without due-on-sale trigger). "
                "NOTE: Inform title insurance company and homeowner's insurance company."
            ),
            recording_requirements=(
                "Deeds must be recorded with the County Recorder or Register of Deeds "
                "in the county where property is located. "
                "Requirements: Signed by grantor, notarized, legal description, "
                "grantee's name and address, consideration amount. "
                "Recording fee: Typically $10-$50 per page. "
                "Transfer tax: Varies significantly by state and county. "
                "Some states require additional forms (property tax transfer forms, etc.)."
            ),
        )
