"""
Court Monitor Skill

Monitors court docket entries for specified case numbers or parties.
In production, integrates with PACER, CourtListener, or state court APIs.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..skill_types import SkillCategory, SkillTemplate


# ---------------------------------------------------------------------------
# Sample docket data (replace with real API calls in production)
# ---------------------------------------------------------------------------

SAMPLE_DOCKETS: List[Dict[str, Any]] = [
    {
        "case_number": "2024-CV-001234",
        "court": "U.S. District Court, S.D.N.Y.",
        "parties": ["Smith Corp.", "Jones LLC"],
        "case_type": "civil",
        "filed_date": "2024-03-15",
        "status": "active",
        "entries": [
            {"date": "2024-03-15", "docket_number": 1, "description": "Complaint Filed"},
            {"date": "2024-04-01", "docket_number": 2, "description": "Summons Issued"},
            {"date": "2024-04-20", "docket_number": 3, "description": "Answer Filed by Defendant"},
            {"date": "2024-05-10", "docket_number": 4, "description": "Scheduling Order Entered"},
        ],
    },
    {
        "case_number": "2024-BK-567890",
        "court": "U.S. Bankruptcy Court, D. Del.",
        "parties": ["Acme Industries Inc.", "Chapter 11 Trustee"],
        "case_type": "bankruptcy",
        "filed_date": "2024-01-08",
        "status": "active",
        "entries": [
            {"date": "2024-01-08", "docket_number": 1, "description": "Voluntary Petition Filed"},
            {"date": "2024-01-09", "docket_number": 2, "description": "Automatic Stay Entered"},
            {"date": "2024-02-15", "docket_number": 3, "description": "Schedules of Assets and Liabilities Filed"},
            {"date": "2024-03-01", "docket_number": 4, "description": "Meeting of Creditors Held"},
            {"date": "2024-04-10", "docket_number": 5, "description": "Plan of Reorganization Filed"},
        ],
    },
    {
        "case_number": "2023-CR-007777",
        "court": "U.S. District Court, N.D. Cal.",
        "parties": ["United States of America", "John Doe"],
        "case_type": "criminal",
        "filed_date": "2023-11-20",
        "status": "closed",
        "entries": [
            {"date": "2023-11-20", "docket_number": 1, "description": "Indictment Filed"},
            {"date": "2023-11-25", "docket_number": 2, "description": "Arraignment Held; Not Guilty Plea Entered"},
            {"date": "2024-01-10", "docket_number": 3, "description": "Motions Deadline"},
            {"date": "2024-02-20", "docket_number": 4, "description": "Trial Commenced"},
            {"date": "2024-02-28", "docket_number": 5, "description": "Verdict: Not Guilty"},
        ],
    },
]


class CourtMonitorSkill(SkillTemplate):
    """Monitors court docket entries for case numbers or parties."""

    @property
    def skill_id(self) -> str:
        return "builtin_court_search"

    @property
    def name(self) -> str:
        return "court_monitor"

    @property
    def description(self) -> str:
        return "Monitors court docket entries for specified case numbers or parties."

    @property
    def category(self) -> SkillCategory:
        return SkillCategory.LEGAL

    @property
    def parameter_schema(self) -> Dict[str, Any]:
        return {
            "court": {"type": "str", "required": True, "description": "Court identifier or 'all'"},
            "case_number": {"type": "str", "required": False, "description": "Specific case number"},
            "party_name": {"type": "str", "required": False, "description": "Party name to search"},
            "since_date": {"type": "str", "required": False, "description": "Only show entries since YYYY-MM-DD"},
            "case_type": {"type": "str", "required": False, "description": "civil|criminal|bankruptcy|all"},
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Search dockets for matching cases and entries."""
        court = kwargs.get("court", "all").lower()
        case_number = kwargs.get("case_number", "").strip()
        party_name = kwargs.get("party_name", "").strip().lower()
        since_date = kwargs.get("since_date", "")
        case_type = kwargs.get("case_type", "all").lower()

        if not case_number and not party_name:
            return {
                "error": "Provide at least one of: case_number, party_name",
                "success": False,
            }

        matching_cases = []

        for docket in SAMPLE_DOCKETS:
            # Filter by court
            if court != "all" and court not in docket["court"].lower():
                continue

            # Filter by case type
            if case_type != "all" and docket["case_type"] != case_type:
                continue

            # Filter by case number
            if case_number and case_number.upper() != docket["case_number"].upper():
                continue

            # Filter by party name
            if party_name:
                party_match = any(party_name in p.lower() for p in docket["parties"])
                if not party_match:
                    continue

            # Filter entries by since_date
            entries = docket["entries"]
            if since_date:
                try:
                    cutoff = datetime.strptime(since_date, "%Y-%m-%d")
                    entries = [
                        e for e in entries
                        if datetime.strptime(e["date"], "%Y-%m-%d") >= cutoff
                    ]
                except ValueError:
                    pass

            case_summary = {
                "case_number": docket["case_number"],
                "court": docket["court"],
                "parties": docket["parties"],
                "case_type": docket["case_type"],
                "filed_date": docket["filed_date"],
                "status": docket["status"],
                "recent_entries": entries[-5:],  # Last 5 entries
                "total_entries": len(docket["entries"]),
                "entries_in_range": len(entries),
            }
            matching_cases.append(case_summary)

        return {
            "cases_found": len(matching_cases),
            "cases": matching_cases,
            "searched_at": datetime.utcnow().isoformat(),
            "filters": {
                "court": court,
                "case_number": case_number,
                "party_name": party_name,
                "since_date": since_date,
                "case_type": case_type,
            },
            "success": True,
        }

    def get_upcoming_deadlines(self, days_ahead: int = 30) -> Dict[str, Any]:
        """Return cases with deadlines in the next N days."""
        upcoming = []
        now = datetime.utcnow()
        cutoff = now + timedelta(days=days_ahead)

        for docket in SAMPLE_DOCKETS:
            if docket["status"] != "active":
                continue
            latest_entry = docket["entries"][-1] if docket["entries"] else None
            if latest_entry:
                entry_date = datetime.strptime(latest_entry["date"], "%Y-%m-%d")
                # Estimate next deadline = 30 days after latest entry
                estimated_next = entry_date + timedelta(days=30)
                if now <= estimated_next <= cutoff:
                    upcoming.append({
                        "case_number": docket["case_number"],
                        "court": docket["court"],
                        "estimated_next_deadline": estimated_next.strftime("%Y-%m-%d"),
                        "last_activity": latest_entry["description"],
                    })

        return {
            "upcoming_deadlines": upcoming,
            "days_ahead": days_ahead,
            "generated_at": now.isoformat(),
        }
