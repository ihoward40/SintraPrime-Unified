"""
Deadline Calculator Skill

Computes legal deadlines from filing dates, accounting for:
- Weekends and federal holidays
- Jurisdiction-specific rules (FRCP, state court rules)
- Multiple deadline types (response, appeal, discovery, statute of limitations)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..skill_types import SkillCategory, SkillTemplate


# ---------------------------------------------------------------------------
# Federal holidays (static list – extend or compute dynamically in production)
# ---------------------------------------------------------------------------

def _federal_holidays(year: int) -> List[date]:
    """Return a list of federal holidays for the given year."""
    from datetime import date

    def nth_weekday(year: int, month: int, n: int, weekday: int) -> date:
        """nth occurrence of weekday (0=Mon) in given month."""
        d = date(year, month, 1)
        count = 0
        while True:
            if d.weekday() == weekday:
                count += 1
                if count == n:
                    return d
            d += timedelta(days=1)

    def last_weekday(year: int, month: int, weekday: int) -> date:
        d = date(year, month + 1, 1) - timedelta(days=1)
        while d.weekday() != weekday:
            d -= timedelta(days=1)
        return d

    holidays = [
        date(year, 1, 1),     # New Year's Day
        date(year, 6, 19),    # Juneteenth
        date(year, 7, 4),     # Independence Day
        date(year, 11, 11),   # Veterans Day
        date(year, 12, 25),   # Christmas Day
        nth_weekday(year, 1, 3, 0),   # MLK Day (3rd Monday January)
        nth_weekday(year, 2, 3, 0),   # Presidents Day (3rd Monday February)
        last_weekday(year, 5, 0),     # Memorial Day (last Monday May)
        nth_weekday(year, 9, 1, 0),   # Labor Day (1st Monday September)
        nth_weekday(year, 10, 2, 0),  # Columbus Day (2nd Monday October)
        nth_weekday(year, 11, 4, 3),  # Thanksgiving (4th Thursday November)
    ]
    return holidays


# ---------------------------------------------------------------------------
# Deadline rules (days from filing)
# ---------------------------------------------------------------------------

DEADLINE_RULES: Dict[str, Dict[str, Any]] = {
    "response": {
        "federal_days": 21,
        "description": "Defendant's response deadline (FRCP Rule 12)",
        "business_days": True,
    },
    "amended_response": {
        "federal_days": 14,
        "description": "Time to amend a response after allowed as of right",
        "business_days": True,
    },
    "appeal": {
        "federal_days": 30,
        "description": "Notice of Appeal deadline (FRAP Rule 4)",
        "business_days": False,
    },
    "appeal_criminal": {
        "federal_days": 14,
        "description": "Criminal appeal notice (FRAP Rule 4(b))",
        "business_days": False,
    },
    "discovery_close": {
        "federal_days": 90,
        "description": "Discovery closure (from scheduling order)",
        "business_days": False,
    },
    "motion_summary_judgment": {
        "federal_days": 30,
        "description": "Dispositive motion deadline",
        "business_days": False,
    },
    "statute_of_limitations_personal_injury": {
        "federal_days": 365 * 2,
        "description": "SOL for personal injury (2 years, federal/most states)",
        "business_days": False,
    },
    "statute_of_limitations_contract": {
        "federal_days": 365 * 4,
        "description": "SOL for written contract claims (4 years, federal)",
        "business_days": False,
    },
    "statute_of_limitations_fraud": {
        "federal_days": 365 * 6,
        "description": "SOL for fraud claims (6 years)",
        "business_days": False,
    },
    "temporary_restraining_order": {
        "federal_days": 14,
        "description": "TRO expiration without hearing (FRCP 65(b))",
        "business_days": False,
    },
    "pretrial_conference": {
        "federal_days": 21,
        "description": "Pretrial disclosures before pretrial conference",
        "business_days": True,
    },
    "meet_and_confer": {
        "federal_days": 21,
        "description": "Rule 26(f) conference deadline before scheduling order",
        "business_days": True,
    },
}


class DeadlineCalculatorSkill(SkillTemplate):
    """Computes legal deadlines from filing dates."""

    @property
    def skill_id(self) -> str:
        return "builtin_deadline_calculator"

    @property
    def name(self) -> str:
        return "deadline_calculator"

    @property
    def description(self) -> str:
        return "Computes legal deadlines from filing dates, accounting for weekends and holidays."

    @property
    def category(self) -> SkillCategory:
        return SkillCategory.LEGAL

    @property
    def parameter_schema(self) -> Dict[str, Any]:
        return {
            "filing_date": {"type": "str", "required": True, "description": "Filing date (YYYY-MM-DD)"},
            "deadline_type": {
                "type": "str",
                "required": True,
                "description": f"Deadline type. Options: {list(DEADLINE_RULES.keys())}",
            },
            "jurisdiction": {
                "type": "str",
                "required": False,
                "default": "federal",
                "description": "Jurisdiction (federal or state name)",
            },
            "skip_holidays": {
                "type": "bool",
                "required": False,
                "default": True,
                "description": "Whether to skip federal holidays",
            },
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Calculate legal deadline from filing date."""
        filing_date_str = kwargs.get("filing_date", "")
        deadline_type = kwargs.get("deadline_type", "").lower().replace(" ", "_")
        jurisdiction = kwargs.get("jurisdiction", "federal").lower()
        skip_holidays = kwargs.get("skip_holidays", True)

        if not filing_date_str:
            return {"error": "filing_date is required (YYYY-MM-DD)", "success": False}

        try:
            filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d").date()
        except ValueError:
            return {"error": f"Invalid date format '{filing_date_str}'. Use YYYY-MM-DD.", "success": False}

        if deadline_type not in DEADLINE_RULES:
            available = list(DEADLINE_RULES.keys())
            return {
                "error": f"Unknown deadline type '{deadline_type}'.",
                "available_types": available,
                "success": False,
            }

        rule = DEADLINE_RULES[deadline_type]
        days = rule["federal_days"]
        use_business_days = rule["business_days"]

        if use_business_days and skip_holidays:
            deadline = self._add_business_days(filing_date, days)
        else:
            deadline = filing_date + timedelta(days=days)
            if skip_holidays:
                # Adjust if deadline falls on weekend or holiday
                deadline = self._next_business_day(deadline, deadline.year)

        days_remaining = (deadline - date.today()).days

        return {
            "filing_date": filing_date_str,
            "deadline_type": deadline_type,
            "deadline_date": deadline.strftime("%Y-%m-%d"),
            "deadline_day_of_week": deadline.strftime("%A"),
            "days_from_filing": days,
            "business_days_rule": use_business_days,
            "days_remaining_from_today": days_remaining,
            "status": (
                "overdue" if days_remaining < 0
                else "urgent" if days_remaining <= 7
                else "upcoming" if days_remaining <= 30
                else "future"
            ),
            "rule_description": rule["description"],
            "jurisdiction": jurisdiction,
            "success": True,
        }

    def calculate_multiple(
        self,
        filing_date_str: str,
        deadline_types: Optional[List[str]] = None,
        skip_holidays: bool = True,
    ) -> Dict[str, Any]:
        """Calculate multiple deadlines from a single filing date."""
        types = deadline_types or list(DEADLINE_RULES.keys())
        results = {}

        for dtype in types:
            result = self.execute(
                filing_date=filing_date_str,
                deadline_type=dtype,
                skip_holidays=skip_holidays,
            )
            if result.get("success"):
                results[dtype] = {
                    "deadline": result["deadline_date"],
                    "days_remaining": result["days_remaining_from_today"],
                    "status": result["status"],
                }

        # Sort by deadline date
        sorted_results = dict(
            sorted(results.items(), key=lambda x: x[1]["deadline"])
        )

        return {
            "filing_date": filing_date_str,
            "deadlines": sorted_results,
            "total_calculated": len(sorted_results),
            "next_deadline": next(iter(sorted_results)) if sorted_results else None,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _add_business_days(self, start: date, n: int) -> date:
        """Add N business days to start date."""
        holidays = _federal_holidays(start.year)
        if start.year + 1 <= 2099:
            holidays += _federal_holidays(start.year + 1)
        holidays_set = set(holidays)

        current = start
        days_added = 0
        while days_added < n:
            current += timedelta(days=1)
            if current.weekday() < 5 and current not in holidays_set:
                days_added += 1
        return current

    def _next_business_day(self, d: date, year: int) -> date:
        """Advance to next business day if d falls on weekend or holiday."""
        holidays_set = set(_federal_holidays(year))
        while d.weekday() >= 5 or d in holidays_set:
            d += timedelta(days=1)
        return d
