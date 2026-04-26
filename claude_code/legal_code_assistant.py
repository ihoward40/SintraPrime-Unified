"""
Legal-specific Claude Code assistant for SintraPrime.
Generates legal automation code for trust documents, contracts, court filings, and more.
"""
import os
from typing import Optional
import anthropic


class LegalCodeAssistant:
    """
    Specialized Claude Code features for legal professionals:
    - Generate trust document parsers
    - Build court filing scripts
    - Create contract analysis tools
    - Automate legal research workflows
    - Generate financial calculation scripts (for trust accounting)
    """

    SUPPORTED_CONTRACT_TYPES = ["NDA", "LLC", "Trust", "Lease", "Employment", "Partnership", "Service"]
    SUPPORTED_FILING_TYPES = ["motion", "complaint", "answer", "brief", "petition", "order"]

    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY")
        )
        self.model = "claude-opus-4-5"

    def _send(self, system: str, user: str, max_tokens: int = 4096) -> str:
        """Send a message to Claude and return the text response."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return message.content[0].text

    async def generate_trust_parser(self, sample_document: str) -> str:
        """Generate a Python script to parse a trust document format."""
        system = (
            "You are an expert legal document parser developer specializing in trust law. "
            "Generate Python code that parses trust documents and extracts structured data. "
            "Use regex, NLP patterns, and rule-based extraction. Include type hints and error handling."
        )
        user = (
            f"Generate a Python trust document parser based on this sample document:\n\n"
            f"{sample_document}\n\n"
            "The parser should extract: grantor name, trustee(s), beneficiaries, trust type, "
            "assets, distribution rules, successor trustees, and effective date. "
            "Return a Python class with a parse() method that returns a typed dataclass."
        )
        return self._send(system, user)

    async def generate_contract_analyzer(self, contract_type: str) -> str:
        """Generate a contract analysis tool for: NDA, LLC, Trust, Lease, Employment."""
        if contract_type not in self.SUPPORTED_CONTRACT_TYPES:
            contract_type_hint = f"(Note: standard supported types are {self.SUPPORTED_CONTRACT_TYPES})"
        else:
            contract_type_hint = ""

        system = (
            "You are an expert legal NLP engineer specializing in contract analysis. "
            "Generate production Python code that analyzes contracts and extracts key provisions, "
            "identifies risks, and flags missing clauses. Use modern Python with type hints."
        )
        user = (
            f"Generate a {contract_type} contract analyzer in Python. {contract_type_hint}\n\n"
            "Include: 1) Key clause extraction, 2) Risk identification, "
            "3) Missing clause detection, 4) Plain-English summary generation, "
            "5) Compliance checklist for the contract type. "
            "Return a complete, runnable Python module."
        )
        return self._send(system, user)

    async def generate_court_filing_script(self, jurisdiction: str, filing_type: str) -> str:
        """Generate a script to automate court filing for a jurisdiction."""
        system = (
            "You are a legal technology expert specializing in court filing automation. "
            "Generate Python scripts that automate court document preparation and filing. "
            "Include document formatting, required fields validation, and submission workflows. "
            "Note: Always include disclaimers that attorneys must review before actual filing."
        )
        user = (
            f"Generate a Python script to automate {filing_type} preparation for {jurisdiction} courts.\n\n"
            "Include: 1) Document template with required fields for this jurisdiction, "
            "2) Field validation, 3) PDF generation, 4) Filing checklist, "
            "5) Attorney review reminder. Add DISCLAIMER that this is a template requiring attorney review."
        )
        return self._send(system, user)

    async def explain_legal_code(self, code: str) -> str:
        """Explain legal automation code to a non-technical attorney."""
        system = (
            "You are a legal technology consultant explaining software to attorneys. "
            "Use legal analogies, avoid technical jargon, and focus on what the code accomplishes "
            "in practical legal terms. Reference familiar legal concepts when explaining technical ones."
        )
        user = (
            f"Explain this legal automation code to a non-technical attorney:\n\n"
            f"```python\n{code}\n```\n\n"
            "Use bullet points. Start with a one-sentence summary of what this does legally. "
            "Then explain each major section in plain English."
        )
        return self._send(system, user)

    async def code_review_for_compliance(self, code: str, jurisdiction: str) -> dict:
        """Review code for legal compliance issues in a specific jurisdiction."""
        system = (
            f"You are a legal compliance expert for {jurisdiction} reviewing legal automation software. "
            "Identify compliance risks related to: unauthorized practice of law, data privacy, "
            "attorney-client privilege, bar association ethics rules, and {jurisdiction}-specific requirements. "
            "Provide actionable remediation steps."
        )
        user = (
            f"Review this legal automation code for compliance in {jurisdiction}:\n\n"
            f"```python\n{code}\n```\n\n"
            "Provide: 1) Compliance risks found, 2) Severity (High/Medium/Low), "
            "3) Specific {jurisdiction} rules implicated, 4) Remediation steps, "
            "5) Overall compliance score (1-10)."
        )
        result = self._send(system, user)
        return {
            "review": result,
            "jurisdiction": jurisdiction,
            "model": self.model,
        }

    async def generate_trust_accounting_script(self, trust_type: str = "revocable") -> str:
        """Generate a financial calculation script for trust accounting."""
        system = (
            "You are an expert trust accountant and Python developer. "
            "Generate trust accounting scripts that handle distributions, "
            "income/principal allocations, tax reporting, and beneficiary tracking. "
            "Follow UPIA (Uniform Principal and Income Act) standards."
        )
        user = (
            f"Generate a Python trust accounting module for a {trust_type} trust.\n\n"
            "Include: 1) Income/principal tracking, 2) Distribution calculations, "
            "3) Beneficiary ledger, 4) Tax withholding calculations, "
            "5) Annual accounting report generation. Follow UPIA standards."
        )
        return self._send(system, user)
