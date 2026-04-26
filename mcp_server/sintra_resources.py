"""
SintraPrime MCP Resources — Expose SintraPrime data as MCP resources.

Resources are addressable data that AI clients can read and use for context.
All resources follow the sintra:// URI scheme.

URI Catalog:
  sintra://legal/statutes/{jurisdiction}
  sintra://legal/cases/{citation}
  sintra://templates/{doc_type}
  sintra://skills/{skill_name}
  sintra://memory/{user_id}/recent
  sintra://tasks/active
  sintra://reports/{report_id}
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from .mcp_types import MCPResource

if TYPE_CHECKING:
    from .mcp_server import SintraMCPServer


# ===========================================================================
# Resource content functions
# ===========================================================================

def _get_statutes(jurisdiction: str = "federal") -> str:
    """Return statute database contents for a jurisdiction."""
    data = {
        "jurisdiction": jurisdiction,
        "database_version": "2026.Q1",
        "last_updated": "2026-03-31",
        "statute_count": 42_000 if jurisdiction == "federal" else 15_000,
        "sample_statutes": [
            {"citation": "42 U.S.C. § 1983", "title": "Civil Action for Deprivation of Rights"},
            {"citation": "28 U.S.C. § 1331", "title": "Federal Question Jurisdiction"},
            {"citation": "15 U.S.C. § 1", "title": "Sherman Act — Restraint of Trade"},
            {"citation": "26 U.S.C. § 7701", "title": "Definitions — Internal Revenue Code"},
        ],
        "access_note": f"Full-text search available via legal_research tool for {jurisdiction}",
    }
    return json.dumps(data, indent=2)


def _get_case(citation: str) -> str:
    """Return case law content for a citation."""
    data = {
        "citation": citation,
        "retrieved_at": datetime.now().isoformat(),
        "case": {
            "parties": citation.split(" v. ")[0] + " v. " + (citation.split(" v. ")[1] if " v. " in citation else "Unknown"),
            "court": "Extracted from citation",
            "year": "See citation",
            "holding": f"Full holding for {citation} from SintraPrime case law database",
            "headnotes": [
                "Constitutional law — due process",
                "Civil procedure — standing",
                "Remedies — injunctive relief",
            ],
            "full_text_available": True,
        },
        "related_cases": [
            "See legal_research tool for related precedents"
        ],
    }
    return json.dumps(data, indent=2)


def _get_template(doc_type: str) -> str:
    """Return a document template for a given doc type."""
    templates = {
        "nda": """NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement ("Agreement") is entered into as of {date}
between {party_a} ("Disclosing Party") and {party_b} ("Receiving Party").

1. CONFIDENTIAL INFORMATION
   [Confidential information definition and scope]

2. OBLIGATIONS
   [Non-disclosure obligations and standard of care]

3. EXCLUSIONS
   [Carve-outs from confidentiality]

4. TERM
   This Agreement shall remain in effect for {term} years.

5. GOVERNING LAW
   This Agreement shall be governed by the laws of {jurisdiction}.
""",
        "llc_operating_agreement": """LLC OPERATING AGREEMENT

This Operating Agreement of {company_name}, LLC is entered into as of {date}.

ARTICLE I — FORMATION
[Formation and registration details]

ARTICLE II — MEMBERS
[Member names, contributions, and ownership percentages]

ARTICLE III — MANAGEMENT
[Manager-managed vs. member-managed provisions]

ARTICLE IV — DISTRIBUTIONS
[Profit/loss allocation and distribution waterfall]

ARTICLE V — TRANSFER RESTRICTIONS
[Transfer limitations and right of first refusal]

ARTICLE VI — DISSOLUTION
[Events of dissolution and winding up]
""",
        "trust": """REVOCABLE LIVING TRUST

This Trust Agreement is entered into by {grantor_name} ("Grantor").

ARTICLE I — TRUST ESTABLISHMENT
The Grantor hereby establishes this revocable trust known as
the {trust_name} Revocable Living Trust.

ARTICLE II — TRUSTEES
Initial Trustee: {grantor_name}
Successor Trustee: {successor_trustee}

ARTICLE III — DISTRIBUTIONS DURING LIFETIME
[HEMS standard + discretionary provisions]

ARTICLE IV — DISTRIBUTION UPON DEATH
[Beneficiary designations and per stirpes distribution]

ARTICLE V — TRUSTEE POWERS
[Investment powers, administrative powers, tax elections]

ARTICLE VI — AMENDMENT AND REVOCATION
The Grantor reserves the right to amend or revoke this Trust.
""",
    }

    normalized = doc_type.lower().replace(" ", "_").replace("-", "_")
    template = templates.get(normalized, f"Template for '{doc_type}' — use draft_document tool to generate customized document.")

    return json.dumps({
        "doc_type": doc_type,
        "template": template,
        "version": "2026.1",
        "variables": [
            "{party_a}", "{party_b}", "{date}", "{jurisdiction}", "{term}"
        ],
        "usage": "Use draft_document tool with this template's variables",
    }, indent=2)


def _get_skill(skill_name: str) -> str:
    """Return skill definition from the skill library."""
    skills = {
        "contract_review": {
            "name": "contract_review",
            "version": "3.1",
            "description": "Systematic contract review and redlining",
            "steps": [
                "Extract parties and recitals",
                "Map obligations for each party",
                "Identify risk allocation clauses",
                "Flag non-standard provisions",
                "Generate redline suggestions",
            ],
            "tools_used": ["analyze_contract", "find_precedent", "draft_document"],
        },
        "due_diligence": {
            "name": "due_diligence",
            "version": "2.0",
            "description": "M&A due diligence workflow",
            "steps": [
                "Corporate structure review",
                "Material contracts analysis",
                "IP and technology audit",
                "Litigation and liability search",
                "Financial statement review",
            ],
            "tools_used": ["legal_research", "analyze_contract", "credit_analysis"],
        },
    }

    skill = skills.get(skill_name.lower(), {
        "name": skill_name,
        "description": f"Skill definition for '{skill_name}'",
        "status": "Available in SintraPrime skill library",
        "execute_via": f"execute_skill('{skill_name}', params={{}})",
    })

    return json.dumps(skill, indent=2)


def _get_recent_memory(user_id: str) -> str:
    """Return recent memories for a user."""
    data = {
        "user_id": user_id,
        "retrieved_at": datetime.now().isoformat(),
        "memories": [
            {
                "id": "mem_001",
                "content": "User researched trust law in California",
                "timestamp": "2026-04-20T14:30:00Z",
                "tags": ["trust", "california", "legal"],
                "importance": 0.9,
            },
            {
                "id": "mem_002",
                "content": "User requested NDA template for software deal",
                "timestamp": "2026-04-18T09:15:00Z",
                "tags": ["nda", "software", "template"],
                "importance": 0.75,
            },
            {
                "id": "mem_003",
                "content": "User analyzed LLC vs S-Corp for consulting business",
                "timestamp": "2026-04-15T11:00:00Z",
                "tags": ["entity", "llc", "s-corp", "financial"],
                "importance": 0.85,
            },
        ],
        "total_memories": 47,
        "search_tip": "Use recall_memory tool for semantic search across all memories",
    }
    return json.dumps(data, indent=2)


def _get_active_tasks() -> str:
    """Return list of currently active scheduled tasks."""
    data = {
        "retrieved_at": datetime.now().isoformat(),
        "active_tasks": [
            {
                "id": "task_0001",
                "description": "Monitor SEC enforcement actions",
                "scheduled_for": "2026-04-27T09:00:00Z",
                "status": "SCHEDULED",
                "priority": "HIGH",
            },
            {
                "id": "task_0002",
                "description": "Generate weekly legal news digest",
                "scheduled_for": "2026-04-28T08:00:00Z",
                "status": "SCHEDULED",
                "priority": "MEDIUM",
            },
        ],
        "total_active": 2,
        "completed_today": 5,
    }
    return json.dumps(data, indent=2)


_report_store: dict = {}


def _get_report(report_id: str) -> str:
    """Retrieve a generated report by ID."""
    report = _report_store.get(report_id)
    if report:
        return report
    return json.dumps({
        "report_id": report_id,
        "status": "NOT_FOUND",
        "message": f"Report '{report_id}' not found. Use generate_report tool to create reports.",
    }, indent=2)


# ===========================================================================
# Registration
# ===========================================================================

def register_all_resources(server: "SintraMCPServer") -> None:
    """Register all SintraPrime resources with the MCP server."""

    resources = [
        MCPResource(
            uri="sintra://legal/statutes/federal",
            name="Federal Statute Database",
            description="Federal statute database with full text and annotations",
            mime_type="application/json",
            content_fn=lambda: _get_statutes("federal"),
        ),
        MCPResource(
            uri="sintra://legal/statutes/{jurisdiction}",
            name="State Statute Database",
            description="State statute database — replace {jurisdiction} with state abbreviation",
            mime_type="application/json",
            content_fn=_get_statutes,
        ),
        MCPResource(
            uri="sintra://legal/cases/{citation}",
            name="Case Law",
            description="Case law retrieval by citation",
            mime_type="application/json",
            content_fn=_get_case,
        ),
        MCPResource(
            uri="sintra://templates/nda",
            name="NDA Template",
            description="Non-disclosure agreement template",
            mime_type="application/json",
            content_fn=lambda: _get_template("nda"),
        ),
        MCPResource(
            uri="sintra://templates/llc_operating_agreement",
            name="LLC Operating Agreement Template",
            description="LLC operating agreement template",
            mime_type="application/json",
            content_fn=lambda: _get_template("llc_operating_agreement"),
        ),
        MCPResource(
            uri="sintra://templates/trust",
            name="Revocable Living Trust Template",
            description="Revocable living trust document template",
            mime_type="application/json",
            content_fn=lambda: _get_template("trust"),
        ),
        MCPResource(
            uri="sintra://templates/{doc_type}",
            name="Document Template",
            description="Document template library — replace {doc_type} with template name",
            mime_type="application/json",
            content_fn=_get_template,
        ),
        MCPResource(
            uri="sintra://skills/{skill_name}",
            name="Skill Definition",
            description="SintraPrime skill definitions — replace {skill_name} with skill name",
            mime_type="application/json",
            content_fn=_get_skill,
        ),
        MCPResource(
            uri="sintra://memory/{user_id}/recent",
            name="Recent Memories",
            description="Recent agent memories for a user — replace {user_id} with user ID",
            mime_type="application/json",
            content_fn=_get_recent_memory,
        ),
        MCPResource(
            uri="sintra://tasks/active",
            name="Active Tasks",
            description="Currently active and scheduled autonomous tasks",
            mime_type="application/json",
            content_fn=_get_active_tasks,
        ),
        MCPResource(
            uri="sintra://reports/{report_id}",
            name="Generated Report",
            description="Retrieve a generated report by ID",
            mime_type="application/json",
            content_fn=_get_report,
        ),
    ]

    for resource in resources:
        server.register_resource(resource)
