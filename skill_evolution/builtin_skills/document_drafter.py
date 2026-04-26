"""
Document Drafter Skill

Generates legal documents from templates given a context dictionary.
Templates include demand letters, motions, contracts, and agreements.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..skill_types import SkillCategory, SkillTemplate


# ---------------------------------------------------------------------------
# Built-in document templates
# ---------------------------------------------------------------------------

DOCUMENT_TEMPLATES: Dict[str, str] = {
    "demand_letter": """\
{date}

{sender_name}
{sender_address}

{recipient_name}
{recipient_address}

Re: Demand for Payment – {matter_description}

Dear {recipient_name},

This letter constitutes formal notice that you owe the sum of {amount} to {sender_name}
arising from {basis_of_claim}.

You are hereby demanded to pay the full amount within {deadline_days} days of the date
of this letter. Failure to do so may result in legal proceedings being initiated against you
without further notice.

Please direct any response or payment to the address above.

Sincerely,
{sender_name}
""",

    "retainer_agreement": """\
LEGAL SERVICES RETAINER AGREEMENT

This Retainer Agreement ("Agreement") is entered into as of {date}

BETWEEN: {attorney_name}, Attorney at Law ("Attorney")
AND:     {client_name} ("Client")

1. SCOPE OF REPRESENTATION
   Attorney agrees to represent Client in connection with:
   {scope_of_representation}

2. FEES AND BILLING
   Client agrees to pay Attorney at the rate of {hourly_rate} per hour.
   An initial retainer of {retainer_amount} is due upon execution of this Agreement.

3. TERMINATION
   Either party may terminate this Agreement upon {notice_days} days written notice.

4. GOVERNING LAW
   This Agreement shall be governed by the laws of {governing_state}.

_________________________          _________________________
{attorney_name}                    {client_name}
Attorney                           Client
Date: {date}
""",

    "motion_to_dismiss": """\
IN THE {court_name}
{case_caption}

Case No. {case_number}

DEFENDANT'S MOTION TO DISMISS PURSUANT TO {rule_citation}

Defendant {defendant_name} respectfully moves this Court to dismiss the Complaint
filed by Plaintiff {plaintiff_name} for the following reasons:

GROUNDS FOR DISMISSAL:
{grounds_for_dismissal}

MEMORANDUM OF LAW:
{memorandum}

WHEREFORE, Defendant respectfully requests that this Court dismiss the Complaint
{with_or_without} prejudice, and for such other and further relief as the Court
deems just and proper.

Respectfully submitted,

{attorney_name}
Attorney for Defendant
{date}
""",

    "nda": """\
NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement ("Agreement") is made as of {date}

BETWEEN: {disclosing_party} ("Disclosing Party")
AND:     {receiving_party} ("Receiving Party")

1. DEFINITION OF CONFIDENTIAL INFORMATION
   "Confidential Information" means {confidential_info_definition}.

2. OBLIGATIONS OF RECEIVING PARTY
   The Receiving Party agrees to:
   (a) Hold the Confidential Information in strict confidence;
   (b) Not disclose the Confidential Information to third parties without prior written consent;
   (c) Use the Confidential Information solely for {permitted_purpose}.

3. TERM
   This Agreement shall remain in effect for {term_years} years from the date hereof.

4. GOVERNING LAW
   This Agreement shall be governed by the laws of {governing_state}.

_________________________          _________________________
{disclosing_party}                 {receiving_party}
Disclosing Party                   Receiving Party
Date: {date}
""",
}


class DocumentDrafterSkill(SkillTemplate):
    """Generates legal documents from templates."""

    @property
    def skill_id(self) -> str:
        return "builtin_doc_draft"

    @property
    def name(self) -> str:
        return "doc_draft"

    @property
    def description(self) -> str:
        return "Generates legal documents from templates given a context dictionary."

    @property
    def category(self) -> SkillCategory:
        return SkillCategory.LEGAL

    @property
    def parameter_schema(self) -> Dict[str, Any]:
        return {
            "template_name": {
                "type": "str",
                "required": True,
                "description": f"Template to use. Available: {list(DOCUMENT_TEMPLATES.keys())}",
            },
            "context": {
                "type": "dict",
                "required": True,
                "description": "Variables to fill into the template",
            },
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Generate a document from the specified template and context."""
        template_name = kwargs.get("template_name", "")
        context = kwargs.get("context", {})

        if template_name not in DOCUMENT_TEMPLATES:
            return {
                "error": f"Unknown template '{template_name}'. Available: {list(DOCUMENT_TEMPLATES.keys())}",
                "success": False,
            }

        template = DOCUMENT_TEMPLATES[template_name]

        # Add default date if not provided
        if "date" not in context:
            context["date"] = datetime.utcnow().strftime("%B %d, %Y")

        # Find unfilled placeholders
        all_placeholders = re.findall(r"\{(\w+)\}", template)
        missing = [p for p in all_placeholders if p not in context]

        # Fill template with safe formatting
        document = template
        for key, value in context.items():
            document = document.replace("{" + key + "}", str(value))

        return {
            "document": document,
            "template_name": template_name,
            "missing_placeholders": missing,
            "context_provided": list(context.keys()),
            "word_count": len(document.split()),
            "generated_at": datetime.utcnow().isoformat(),
            "success": True,
        }

    def list_templates(self) -> List[str]:
        """Return available template names."""
        return list(DOCUMENT_TEMPLATES.keys())

    def get_template_placeholders(self, template_name: str) -> List[str]:
        """Return the list of placeholder variables for a template."""
        template = DOCUMENT_TEMPLATES.get(template_name, "")
        return list(set(re.findall(r"\{(\w+)\}", template)))
