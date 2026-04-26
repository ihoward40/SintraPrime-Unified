"""
LegalOperator – SintraPrime-specific legal operator skills.

Extends OperatorAgent with specialized legal research, document drafting,
court docket monitoring, and deadline tracking capabilities.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .operator_agent import OperatorAgent, TaskResult, TaskStatus
from .browser_controller import ActionResult
from .web_researcher import ResearchReport, Citation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Legal-specific data classes
# ---------------------------------------------------------------------------


@dataclass
class CaseLawResult:
    """A single case law result."""
    case_name: str
    citation: str
    jurisdiction: str
    year: int
    summary: str
    url: str = ""
    relevance_score: float = 0.0


@dataclass
class CaseLawReport:
    """Full case law research report."""
    query: str
    jurisdiction: str
    cases: List[CaseLawResult]
    summary: str
    citations: List[Citation] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            f"# Case Law Research: {self.query}",
            f"**Jurisdiction:** {self.jurisdiction}",
            "",
            "## Summary",
            self.summary,
            "",
            "## Cases Found",
        ]
        for i, case in enumerate(self.cases, 1):
            lines.append(f"### {i}. {case.case_name}")
            lines.append(f"- **Citation:** {case.citation}")
            lines.append(f"- **Year:** {case.year}")
            lines.append(f"- **Jurisdiction:** {case.jurisdiction}")
            lines.append(f"- **Summary:** {case.summary}")
            if case.url:
                lines.append(f"- **Source:** [{case.url}]({case.url})")
            lines.append("")
        return "\n".join(lines)


@dataclass
class LegalDocument:
    """A generated legal document."""
    doc_type: str
    parties: Dict[str, str]
    terms: Dict[str, Any]
    content: str
    warnings: List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        return self.content

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.content)
        logger.info(f"Legal document saved: {path}")


@dataclass
class DocketEntry:
    """A single court docket entry."""
    date: str
    event: str
    description: str
    document_url: str = ""


@dataclass
class DocketReport:
    """Court docket monitoring result."""
    case_number: str
    court: str
    case_name: str = ""
    status: str = ""
    entries: List[DocketEntry] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    new_entries_since_last_check: int = 0


@dataclass
class GovernmentForm:
    """A found government form."""
    form_name: str
    form_number: str
    agency: str
    description: str
    download_url: str = ""
    instructions_url: str = ""
    local_path: str = ""


@dataclass
class LegalDeadline:
    """A legal deadline entry."""
    matter_id: str
    deadline_type: str
    due_date: str
    description: str
    days_remaining: int
    is_critical: bool = False
    notes: str = ""


@dataclass
class CompetitiveLegalReport:
    """Deep competitive legal research report."""
    topic: str
    depth: int
    key_cases: List[CaseLawResult] = field(default_factory=list)
    regulatory_landscape: str = ""
    jurisdictional_comparison: Dict[str, str] = field(default_factory=dict)
    trends: List[str] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    report_markdown: str = ""


# ---------------------------------------------------------------------------
# Legal database sources
# ---------------------------------------------------------------------------

LEGAL_DATABASES = {
    "google_scholar": "https://scholar.google.com/scholar?q={query}&as_sdt=2006",
    "justia": "https://law.justia.com/cases/?q={query}",
    "courtlistener": "https://www.courtlistener.com/?q={query}&type=o",
    "caselaw_access": "https://api.case.law/v1/cases/?search={query}",
    "leagle": "https://www.leagle.com/search?q={query}",
}

GOVERNMENT_FORM_SOURCES = {
    "irs": "https://www.irs.gov/forms-instructions-and-publications",
    "uscis": "https://www.uscis.gov/forms",
    "doj": "https://www.justice.gov/forms",
    "courts": "https://www.uscourts.gov/forms",
    "sec": "https://www.sec.gov/cgi-bin/browse-edgar",
    "ca_courts": "https://www.courts.ca.gov/forms.htm",
    "ca_sos": "https://www.sos.ca.gov/business-programs/business-entities/forms",
}

# DOCUMENT_TEMPLATES is defined after all template functions below


def _retainer_agreement_template(parties: Dict[str, str], terms: Dict[str, Any]) -> str:
    client = parties.get("client", "[CLIENT NAME]")
    attorney = parties.get("attorney", "[ATTORNEY NAME]")
    firm = parties.get("firm", "[LAW FIRM NAME]")
    retainer_fee = terms.get("retainer_fee", "[RETAINER FEE]")
    hourly_rate = terms.get("hourly_rate", "[HOURLY RATE]")
    matter = terms.get("matter", "[LEGAL MATTER DESCRIPTION]")
    date = terms.get("date", time.strftime("%B %d, %Y"))

    return f"""# LEGAL RETAINER AGREEMENT

**Date:** {date}

## PARTIES

**Client:** {client}
**Attorney:** {attorney}
**Law Firm:** {firm}

## ENGAGEMENT

This Retainer Agreement ("Agreement") is entered into as of {date} between {client} ("Client")
and {firm} ("Firm"), represented by {attorney}.

## SCOPE OF REPRESENTATION

The Firm agrees to represent the Client in the following matter:
{matter}

## FEES AND BILLING

**Retainer Fee:** {retainer_fee} (due upon signing)
**Hourly Rate:** {hourly_rate} per hour

The retainer fee will be placed in the Firm's client trust account and drawn against as
services are rendered. Client will be billed monthly for services exceeding the retainer.

## RESPONSIBILITIES

Client agrees to:
1. Provide complete and accurate information as requested by the Firm
2. Keep the Firm informed of any changes relevant to the matter
3. Pay all invoices within thirty (30) days of receipt
4. Cooperate fully in all legal proceedings

The Firm agrees to:
1. Represent Client's interests diligently and competently
2. Communicate regularly regarding the status of the matter
3. Maintain Client confidentiality per applicable rules of professional conduct
4. Provide itemized billing statements

## TERMINATION

Either party may terminate this Agreement upon written notice. Client shall remain
responsible for fees incurred through the date of termination.

## GOVERNING LAW

This Agreement shall be governed by the laws of the state where the Firm is licensed to practice.

---

**CLIENT SIGNATURE:** ___________________________ Date: ___________

**{client}**

**ATTORNEY SIGNATURE:** ___________________________ Date: ___________

**{attorney}, {firm}**

---

*This document was generated by SintraPrime AI and requires review by a licensed attorney
before execution. This is not legal advice.*
"""


def _nda_template(parties: Dict[str, str], terms: Dict[str, Any]) -> str:
    disclosing = parties.get("disclosing_party", "[DISCLOSING PARTY]")
    receiving = parties.get("receiving_party", "[RECEIVING PARTY]")
    purpose = terms.get("purpose", "[PURPOSE OF DISCLOSURE]")
    duration = terms.get("duration_years", "2")
    date = terms.get("date", time.strftime("%B %d, %Y"))

    return f"""# NON-DISCLOSURE AGREEMENT

**Date:** {date}

## PARTIES

**Disclosing Party:** {disclosing}
**Receiving Party:** {receiving}

## RECITALS

The parties wish to explore a business relationship regarding: {purpose}

In connection therewith, the Disclosing Party may share confidential information with the
Receiving Party. This Agreement establishes the terms under which such information may be shared.

## DEFINITION OF CONFIDENTIAL INFORMATION

"Confidential Information" means any information disclosed by the Disclosing Party to the
Receiving Party that is designated as confidential or that reasonably should be understood
to be confidential given the nature of the information and circumstances of disclosure.

## OBLIGATIONS

The Receiving Party agrees to:
1. Hold all Confidential Information in strict confidence
2. Not disclose Confidential Information to any third party without prior written consent
3. Use Confidential Information solely for the purpose stated above
4. Protect Confidential Information with at least the same degree of care used for its own
   confidential information (but not less than reasonable care)

## TERM

This Agreement shall remain in effect for {duration} years from the date of execution.

## EXCEPTIONS

Confidential Information does not include information that:
- Was publicly available at the time of disclosure
- Becomes publicly available through no fault of the Receiving Party
- Was independently developed by the Receiving Party
- Was required to be disclosed by law or court order

## REMEDIES

The parties acknowledge that breach of this Agreement may cause irreparable harm for
which monetary damages may be inadequate, and the non-breaching party shall be entitled
to seek equitable relief.

---

**DISCLOSING PARTY:** ___________________________ Date: ___________
{disclosing}

**RECEIVING PARTY:** ___________________________ Date: ___________
{receiving}

---

*Generated by SintraPrime AI. Consult a licensed attorney before execution.*
"""


def _demand_letter_template(parties: Dict[str, str], terms: Dict[str, Any]) -> str:
    sender = parties.get("sender", "[SENDER]")
    recipient = parties.get("recipient", "[RECIPIENT]")
    amount = terms.get("amount_owed", "[AMOUNT]")
    deadline_days = terms.get("deadline_days", "14")
    claim = terms.get("claim_description", "[DESCRIPTION OF CLAIM]")
    date = terms.get("date", time.strftime("%B %d, %Y"))

    return f"""# DEMAND LETTER

{date}

**VIA CERTIFIED MAIL / EMAIL**

{recipient}

**RE: Demand for Payment – {amount}**

Dear {recipient},

This letter serves as formal notice and demand for payment of {amount} owed to {sender}.

## BASIS FOR CLAIM

{claim}

## DEMAND

Accordingly, {sender} demands payment of **{amount}** within **{deadline_days} days**
of the date of this letter.

## CONSEQUENCES OF NON-PAYMENT

If payment is not received within the stated deadline, {sender} reserves the right to:
1. File a civil lawsuit seeking the amount owed plus interest, attorneys' fees, and costs
2. Report the unpaid debt to applicable credit reporting agencies
3. Pursue all other remedies available under applicable law

## RESPONSE

Please remit payment to:
[PAYMENT INSTRUCTIONS]

Or contact us to discuss resolution:
[CONTACT INFORMATION]

Sincerely,

{sender}

---

*This demand letter was generated by SintraPrime AI. It should be reviewed by a
licensed attorney before sending.*
"""


def _settlement_agreement_template(parties: Dict[str, str], terms: Dict[str, Any]) -> str:
    party_a = parties.get("party_a", "[PARTY A]")
    party_b = parties.get("party_b", "[PARTY B]")
    settlement_amount = terms.get("settlement_amount", "[AMOUNT]")
    dispute = terms.get("dispute_description", "[DISPUTE DESCRIPTION]")
    date = terms.get("date", time.strftime("%B %d, %Y"))

    return f"""# SETTLEMENT AGREEMENT AND RELEASE

**Date:** {date}

## PARTIES

This Settlement Agreement ("Agreement") is entered into between:
- **{party_a}** ("Party A")
- **{party_b}** ("Party B")

## RECITALS

WHEREAS, a dispute has arisen between the parties regarding: {dispute}

WHEREAS, the parties wish to resolve this dispute without further litigation;

NOW THEREFORE, in consideration of the mutual promises contained herein, the parties agree:

## SETTLEMENT TERMS

1. **Payment:** {party_b} shall pay {party_a} the sum of **{settlement_amount}** within
   thirty (30) days of execution of this Agreement.

2. **Release:** Upon receipt of payment, {party_a} hereby releases and forever discharges
   {party_b} from any and all claims, demands, damages, actions, or causes of action
   arising from the dispute described above.

3. **Confidentiality:** The parties agree to keep the terms of this Agreement confidential
   and shall not disclose the settlement amount to any third party.

4. **No Admission:** This Agreement does not constitute an admission of liability by either party.

5. **Entire Agreement:** This Agreement constitutes the entire agreement between the parties
   regarding the subject matter hereof.

## SIGNATURES

**{party_a}:** ___________________________ Date: ___________

**{party_b}:** ___________________________ Date: ___________

---

*Generated by SintraPrime AI. Review by a licensed attorney required before execution.*
"""


def _power_of_attorney_template(parties: Dict[str, str], terms: Dict[str, Any]) -> str:
    principal = parties.get("principal", "[PRINCIPAL NAME]")
    agent = parties.get("agent", "[AGENT NAME]")
    scope = terms.get("scope", "general financial and legal matters")
    date = terms.get("date", time.strftime("%B %d, %Y"))
    durable = terms.get("durable", True)

    durable_clause = (
        "This Power of Attorney shall not be affected by subsequent incapacity of the Principal."
        if durable else
        "This Power of Attorney shall terminate upon incapacity of the Principal."
    )

    return f"""# {"DURABLE " if durable else ""}POWER OF ATTORNEY

**Date:** {date}

## PRINCIPAL

I, **{principal}** ("Principal"), hereby appoint **{agent}** ("Agent") as my
attorney-in-fact to act on my behalf.

## GRANT OF AUTHORITY

Subject to the limitations set forth herein, my Agent is authorized to act on my behalf
in all matters relating to: **{scope}**

Specific powers granted include (as applicable to scope):
- Managing bank accounts and financial transactions
- Signing documents and contracts on my behalf
- Managing real property
- Filing tax returns
- Making legal decisions on my behalf

## DURABILITY

{durable_clause}

## REVOCATION

I reserve the right to revoke this Power of Attorney at any time by executing a written
revocation and delivering it to my Agent and any relevant third parties.

## SIGNATURE

Executed this {date}.

**PRINCIPAL:** ___________________________ Date: ___________
{principal}

**NOTARIZATION:**

State of _______________
County of _______________

Before me, the undersigned notary public, personally appeared {principal}, known to me to be
the person whose name is subscribed to the foregoing instrument.

**Notary Public:** ___________________________ Date: ___________
My Commission Expires: _______________

---

*Generated by SintraPrime AI. A licensed attorney must review before execution.
Requirements vary by state.*
"""


def _trust_document_template(parties: Dict[str, str], terms: Dict[str, Any]) -> str:
    grantor = parties.get("grantor", "[GRANTOR NAME]")
    trustee = parties.get("trustee", "[TRUSTEE NAME]")
    successor_trustee = parties.get("successor_trustee", "[SUCCESSOR TRUSTEE]")
    beneficiaries = terms.get("beneficiaries", ["[BENEFICIARY 1]"])
    trust_name = terms.get("trust_name", f"The {grantor} Revocable Living Trust")
    state = terms.get("state", "[STATE]")
    date = terms.get("date", time.strftime("%B %d, %Y"))

    bene_list = "\n".join(f"- **{b}**" for b in beneficiaries)

    return f"""# {trust_name.upper()}

**Date of Execution:** {date}
**Governing Law:** State of {state}

## DECLARATION OF TRUST

I, **{grantor}** ("Grantor" and initial "Trustee"), hereby declare that I hold and will
hold in trust, for the benefit of the beneficiaries named herein, all property transferred
to this trust, under the following terms and conditions:

## ARTICLE I: NAME AND PURPOSE

1.1 This trust shall be known as the **{trust_name}**.

1.2 The purpose of this trust is to provide for the management of trust assets during
    the Grantor's lifetime and the distribution of trust assets upon the Grantor's death.

## ARTICLE II: TRUSTEE

2.1 **Initial Trustee:** {trustee}

2.2 **Successor Trustee:** Upon the death, incapacity, or resignation of the initial
    Trustee, {successor_trustee} shall serve as Successor Trustee.

2.3 The Trustee shall manage trust assets prudently and in the best interests of the
    beneficiaries.

## ARTICLE III: BENEFICIARIES

The following persons are named as beneficiaries of this trust:

{bene_list}

Distribution to beneficiaries shall occur according to the terms set forth in Article IV.

## ARTICLE IV: DISTRIBUTION OF TRUST ESTATE

4.1 **During Grantor's Lifetime:** The Trustee shall distribute to the Grantor such income
    and principal as the Grantor requests.

4.2 **Upon Grantor's Death:** The Trustee shall distribute the trust estate to the named
    beneficiaries in equal shares, or as otherwise specified by amendment to this trust.

## ARTICLE V: REVOCABILITY

This trust is revocable and may be amended or revoked by the Grantor at any time during
the Grantor's lifetime by a written instrument delivered to the Trustee.

## ARTICLE VI: TRUSTEE POWERS

The Trustee shall have all powers necessary or appropriate to carry out the purposes of
this trust, including but not limited to:
- Investing and reinvesting trust assets
- Buying, selling, and managing real property
- Maintaining and operating business interests
- Making distributions to beneficiaries

## SIGNATURES

**GRANTOR/TRUSTEE:** ___________________________ Date: ___________
{grantor}

**NOTARIZATION:**

State of {state}
County of _______________

Before me, the undersigned notary public, personally appeared {grantor}.

**Notary Public:** ___________________________ Date: ___________
Commission Expires: _______________

---

*This trust document was generated by SintraPrime AI as a starting template only.
A licensed estate planning attorney MUST review and customize this document before
execution. Laws vary significantly by state. This is not legal advice.*
"""


# ---------------------------------------------------------------------------
# LegalOperator
# ---------------------------------------------------------------------------


class LegalOperator(OperatorAgent):
    """
    SintraPrime-specific legal operator.

    Extends OperatorAgent with specialized capabilities for:
    - Case law research across legal databases
    - Autonomous legal document drafting
    - Court docket monitoring
    - Government form finding and downloading
    - Legal deadline tracking
    - Deep competitive legal research

    Example:
        op = LegalOperator()
        report = op.research_case_law("trust formation California", "California")
        print(report.to_markdown())
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._docket_cache: Dict[str, DocketReport] = {}
        self._deadline_registry: Dict[str, List[LegalDeadline]] = {}

    # ------------------------------------------------------------------
    # Case Law Research
    # ------------------------------------------------------------------

    def research_case_law(
        self, query: str, jurisdiction: str = "Federal", depth: int = 3
    ) -> CaseLawReport:
        """
        Autonomously browse legal databases to find relevant case law.

        Searches Google Scholar, Justia, CourtListener, and Leagle.

        Args:
            query: Legal research query (e.g., "trust formation requirements").
            jurisdiction: Jurisdiction filter (e.g., "California", "Federal", "9th Circuit").
            depth: Number of databases to search (1-5).

        Returns:
            CaseLawReport with structured case citations and summaries.
        """
        logger.info(f"Researching case law: '{query}' in {jurisdiction}")
        cases: List[CaseLawResult] = []
        citations: List[Citation] = []

        # Build jurisdiction-specific search queries
        jur_query = f"{query} {jurisdiction} case law"

        databases = list(LEGAL_DATABASES.items())[:depth]

        for db_name, db_url_template in databases:
            encoded_query = query.replace(" ", "+")
            db_url = db_url_template.format(query=encoded_query)

            nav = self.browser.navigate(db_url)
            if not nav:
                continue

            content_result = self.browser.extract_text("body")
            if not content_result:
                continue

            text = content_result.data or ""
            extracted_cases = self._parse_cases_from_text(text, jurisdiction, db_name, db_url)
            cases.extend(extracted_cases)
            citations.append(Citation(url=db_url, title=f"Search: {db_name}",
                                      relevant_quote=text[:200]))

        # Also do a web search for case law
        search = self.browser.search_web(f"{jur_query} site:law.justia.com OR site:scholar.google.com", max_results=5)
        for hit in (search.data or []):
            if hit.url.startswith("http") and any(
                domain in hit.url for domain in ["justia", "scholar.google", "courtlistener", "leagle"]
            ):
                citations.append(Citation(url=hit.url, title=hit.title,
                                          relevant_quote=hit.snippet[:200]))
                # Try to parse case name from title
                if "v." in hit.title or "vs." in hit.title.lower():
                    year_match = re.search(r"\b(19|20)\d{2}\b", hit.snippet)
                    year = int(year_match.group()) if year_match else 0
                    cases.append(CaseLawResult(
                        case_name=hit.title[:100],
                        citation=hit.snippet[:50],
                        jurisdiction=jurisdiction,
                        year=year,
                        summary=hit.snippet,
                        url=hit.url,
                        relevance_score=0.7,
                    ))

        # Deduplicate by case name
        seen = set()
        unique_cases: List[CaseLawResult] = []
        for case in cases:
            key = case.case_name.lower().strip()
            if key not in seen:
                seen.add(key)
                unique_cases.append(case)

        # Sort by year descending
        unique_cases.sort(key=lambda c: c.year, reverse=True)

        summary = (
            f"Found {len(unique_cases)} relevant cases in {jurisdiction} jurisdiction "
            f"matching '{query}'. Searched {len(databases)} legal databases."
        )

        return CaseLawReport(
            query=query,
            jurisdiction=jurisdiction,
            cases=unique_cases[:20],
            summary=summary,
            citations=citations,
        )

    def _parse_cases_from_text(
        self, text: str, jurisdiction: str, source: str, source_url: str
    ) -> List[CaseLawResult]:
        """Extract case citations from raw page text using regex heuristics."""
        cases = []

        # Pattern: "Party A v. Party B, [Reporter] [Year]"
        case_pattern = re.compile(
            r"([A-Z][A-Za-z\s,\.]+)\s+v\.\s+([A-Z][A-Za-z\s,\.]+)(?:,\s*([\d\s\w\.]+))?\s*\(?(\d{4})?\)?",
            re.MULTILINE,
        )

        for match in case_pattern.finditer(text):
            party_a = match.group(1).strip()[:50]
            party_b = match.group(2).strip()[:50]
            citation_str = match.group(3) or ""
            year_str = match.group(4)
            year = int(year_str) if year_str and year_str.isdigit() else 0

            case_name = f"{party_a} v. {party_b}"
            snippet_start = max(0, match.start() - 100)
            snippet_end = min(len(text), match.end() + 200)
            summary = text[snippet_start:snippet_end].strip()

            cases.append(CaseLawResult(
                case_name=case_name,
                citation=citation_str.strip(),
                jurisdiction=jurisdiction,
                year=year,
                summary=summary[:300],
                url=source_url,
                relevance_score=0.5,
            ))

            if len(cases) >= 10:
                break

        return cases

    # ------------------------------------------------------------------
    # Document Drafting
    # ------------------------------------------------------------------

    def draft_document(
        self,
        doc_type: str,
        parties: Dict[str, str],
        terms: Dict[str, Any],
    ) -> LegalDocument:
        """
        Generate a legal document from a template.

        Supported doc_types:
            retainer_agreement, nda, demand_letter, settlement_agreement,
            power_of_attorney, trust_document

        Args:
            doc_type: Document type key.
            parties: Dictionary of party names (e.g., {"client": "John Doe"}).
            terms: Dictionary of terms and parameters for the document.

        Returns:
            LegalDocument with content and warnings.
        """
        logger.info(f"Drafting {doc_type} for parties: {list(parties.values())}")

        template_fn = DOCUMENT_TEMPLATES.get(doc_type)
        if template_fn is None:
            # Generate a generic document
            content = self._generic_document(doc_type, parties, terms)
        else:
            content = template_fn(parties, terms)

        warnings = [
            "⚠️  This document was generated by AI and is NOT legal advice.",
            "⚠️  It MUST be reviewed by a licensed attorney before execution.",
            "⚠️  Requirements vary by jurisdiction.",
        ]

        return LegalDocument(
            doc_type=doc_type,
            parties=parties,
            terms=terms,
            content=content,
            warnings=warnings,
        )

    def _generic_document(
        self, doc_type: str, parties: Dict[str, str], terms: Dict[str, Any]
    ) -> str:
        date = terms.get("date", time.strftime("%B %d, %Y"))
        parties_str = "\n".join(f"- **{role.title()}:** {name}"
                                for role, name in parties.items())
        terms_str = "\n".join(f"- **{k.replace('_', ' ').title()}:** {v}"
                               for k, v in terms.items())
        return f"""# {doc_type.replace('_', ' ').upper()}

**Date:** {date}

## PARTIES

{parties_str}

## TERMS AND CONDITIONS

{terms_str}

## AGREEMENT

The parties named above hereby agree to the terms set forth herein.

---

*Generated by SintraPrime AI. Legal review required.*
"""

    # ------------------------------------------------------------------
    # Court Docket Monitoring
    # ------------------------------------------------------------------

    def monitor_court_docket(
        self, case_number: str, court: str = "PACER", interval_hours: int = 24
    ) -> DocketReport:
        """
        Watch a court docket for new entries and updates.

        Args:
            case_number: Court case number (e.g., "2:23-cv-01234").
            court: Court system to monitor ("PACER", "CA_Superior", "NYCOURTS").
            interval_hours: How often to check (in hours).

        Returns:
            DocketReport with latest entries and any new activity.
        """
        logger.info(f"Monitoring docket: {case_number} on {court}")

        # Build search URLs based on court system
        search_urls = {
            "PACER": f"https://ecf.pacer.gov/cgi-bin/iquery.pl?caseid={case_number}",
            "CA_Superior": f"https://www.lacourt.org/casesummary/ui/?number={case_number}",
            "NYCOURTS": f"https://iapps.courts.state.ny.us/nyscef/CaseSearch?IndexNo={case_number}",
            "CourtListener": f"https://www.courtlistener.com/?q={case_number}&type=r",
        }

        search_url = search_urls.get(court, search_urls["CourtListener"])

        # Try to navigate to the docket
        nav = self.browser.navigate(search_url)
        entries: List[DocketEntry] = []
        case_name = ""
        status = "Unknown"

        if nav:
            content_result = self.browser.extract_text("body")
            text = content_result.data or ""

            # Parse docket entries (naive date-based parsing)
            date_pattern = re.compile(r"(\d{1,2}/\d{1,2}/\d{2,4})\s+(.+?)(?=\d{1,2}/\d{1,2}/\d{2,4}|$)",
                                      re.DOTALL)
            for match in date_pattern.finditer(text[:5000]):
                date_str = match.group(1)
                event_text = match.group(2).strip()[:200]
                entries.append(DocketEntry(
                    date=date_str,
                    event="Docket Entry",
                    description=event_text,
                ))
                if len(entries) >= 20:
                    break

            # Extract case name if found
            if "v." in text:
                case_match = re.search(
                    r"([A-Z][A-Za-z\s]+)\s+v\.\s+([A-Z][A-Za-z\s]+)", text
                )
                if case_match:
                    case_name = case_match.group(0)

        # Check for new entries vs cached
        cached = self._docket_cache.get(case_number)
        new_entries = len(entries) - (len(cached.entries) if cached else 0)
        new_entries = max(0, new_entries)

        report = DocketReport(
            case_number=case_number,
            court=court,
            case_name=case_name,
            status=status,
            entries=entries,
            new_entries_since_last_check=new_entries,
        )

        self._docket_cache[case_number] = report
        return report

    # ------------------------------------------------------------------
    # Government Form Finder
    # ------------------------------------------------------------------

    def file_finder(self, agency: str, form_name: str) -> GovernmentForm:
        """
        Find and optionally download a government form from the appropriate agency.

        Args:
            agency: Agency name or key (e.g., "IRS", "USCIS", "CA_Courts").
            form_name: Form name or number (e.g., "W-9", "I-485", "FL-100").

        Returns:
            GovernmentForm with download URL and metadata.
        """
        logger.info(f"Finding form '{form_name}' from {agency}")

        agency_key = agency.lower().replace(" ", "_")
        base_url = GOVERNMENT_FORM_SOURCES.get(agency_key, "")

        # Search for the form
        search_query = f"{agency} {form_name} form PDF download official"
        search = self.browser.search_web(search_query, max_results=5)
        hits = search.data or []

        download_url = ""
        description = ""
        instructions_url = ""

        for hit in hits:
            hit_lower = (hit.title + hit.snippet).lower()
            if form_name.lower() in hit_lower or agency.lower() in hit_lower:
                download_url = hit.url
                description = hit.snippet
                break

        # Try navigating to agency base URL if no direct download found
        if not download_url and base_url:
            nav = self.browser.navigate(base_url)
            if nav:
                content = self.browser.extract_text("body")
                text = content.data or ""
                if form_name.lower() in text.lower():
                    download_url = base_url
                    description = f"Found form {form_name} on {agency} official website."

        return GovernmentForm(
            form_name=form_name,
            form_number=form_name,
            agency=agency,
            description=description or f"{form_name} from {agency}",
            download_url=download_url,
            instructions_url=instructions_url,
        )

    # ------------------------------------------------------------------
    # Deadline Tracker
    # ------------------------------------------------------------------

    def deadline_tracker(self, matter_id: str) -> List[LegalDeadline]:
        """
        Monitor and return legal deadlines for a matter.

        Args:
            matter_id: Unique matter/case identifier.

        Returns:
            List of LegalDeadline objects sorted by days_remaining.
        """
        deadlines = self._deadline_registry.get(matter_id, [])

        # Update days remaining
        today = time.strftime("%Y-%m-%d")
        for deadline in deadlines:
            try:
                import datetime
                due = datetime.date.fromisoformat(deadline.due_date)
                today_d = datetime.date.fromisoformat(today)
                deadline.days_remaining = (due - today_d).days
                deadline.is_critical = deadline.days_remaining <= 7
            except Exception:
                pass

        # Sort by urgency
        deadlines.sort(key=lambda d: d.days_remaining)
        return deadlines

    def add_deadline(
        self,
        matter_id: str,
        deadline_type: str,
        due_date: str,
        description: str,
    ) -> LegalDeadline:
        """
        Register a new legal deadline for a matter.

        Args:
            matter_id: Matter identifier.
            deadline_type: Type of deadline (e.g., "Filing", "Response", "Statute of Limitations").
            due_date: Due date in ISO format (YYYY-MM-DD).
            description: Human-readable description.

        Returns:
            The created LegalDeadline.
        """
        import datetime
        try:
            due = datetime.date.fromisoformat(due_date)
            today = datetime.date.today()
            days_remaining = (due - today).days
        except Exception:
            days_remaining = 0

        deadline = LegalDeadline(
            matter_id=matter_id,
            deadline_type=deadline_type,
            due_date=due_date,
            description=description,
            days_remaining=days_remaining,
            is_critical=days_remaining <= 7,
        )

        if matter_id not in self._deadline_registry:
            self._deadline_registry[matter_id] = []
        self._deadline_registry[matter_id].append(deadline)

        logger.info(f"Deadline added for matter {matter_id}: {deadline_type} due {due_date}")
        return deadline

    # ------------------------------------------------------------------
    # Competitive Legal Research
    # ------------------------------------------------------------------

    def competitive_legal_research(
        self, topic: str, depth: int = 5
    ) -> CompetitiveLegalReport:
        """
        Conduct deep competitive legal research on a topic.

        Covers case law, regulatory landscape, jurisdictional comparison,
        and emerging trends across multiple legal databases.

        Args:
            topic: Legal research topic.
            depth: Research depth (1-5, where 5 = most thorough).

        Returns:
            CompetitiveLegalReport with comprehensive analysis.
        """
        logger.info(f"Competitive legal research: '{topic}' (depth={depth})")

        key_jurisdictions = ["Federal", "California", "New York", "Texas", "Florida"][:depth]
        all_cases: List[CaseLawResult] = []
        jurisdictional_comparison: Dict[str, str] = {}
        trends: List[str] = []
        citations: List[Citation] = []

        # Research case law in multiple jurisdictions
        for jurisdiction in key_jurisdictions:
            jur_report = self.research_case_law(topic, jurisdiction, depth=min(depth, 3))
            all_cases.extend(jur_report.cases[:3])
            citations.extend(jur_report.citations[:2])

            # Build jurisdictional summary
            if jur_report.cases:
                jurisdictional_comparison[jurisdiction] = (
                    f"{len(jur_report.cases)} relevant cases found. "
                    f"Most recent: {jur_report.cases[0].case_name} ({jur_report.cases[0].year})"
                )
            else:
                jurisdictional_comparison[jurisdiction] = "No cases found in search."

        # Research regulatory landscape
        reg_search = self.browser.search_web(
            f"{topic} regulations statutes federal state 2024", max_results=5
        )
        reg_hits = reg_search.data or []
        regulatory_landscape = (
            f"Regulatory environment for {topic}: "
            + ". ".join(h.snippet[:100] for h in reg_hits[:3])
            if reg_hits else f"Regulatory research for {topic} pending."
        )

        # Identify trends
        trend_search = self.browser.search_web(
            f"{topic} legal trends emerging issues 2024", max_results=5
        )
        for hit in (trend_search.data or [])[:5]:
            if hit.snippet:
                trends.append(hit.snippet[:150])
            citations.append(Citation(url=hit.url, title=hit.title))

        # Deduplicate cases
        seen_names = set()
        unique_cases = []
        for case in all_cases:
            if case.case_name not in seen_names:
                seen_names.add(case.case_name)
                unique_cases.append(case)

        # Build full markdown report
        report_lines = [
            f"# Competitive Legal Research: {topic}",
            f"**Research Depth:** {depth}/5",
            f"**Jurisdictions Covered:** {', '.join(key_jurisdictions)}",
            "",
            "## Regulatory Landscape",
            regulatory_landscape,
            "",
            "## Key Cases",
        ]
        for case in unique_cases[:10]:
            report_lines.append(f"- **{case.case_name}** ({case.year}, {case.jurisdiction}): {case.summary[:100]}...")
        report_lines.append("")
        report_lines.append("## Jurisdictional Comparison")
        for jur, summary in jurisdictional_comparison.items():
            report_lines.append(f"**{jur}:** {summary}")
        report_lines.append("")
        report_lines.append("## Emerging Trends")
        for trend in trends[:5]:
            report_lines.append(f"- {trend}")
        report_lines.append("")
        report_lines.append("## Sources")
        for i, cit in enumerate(citations[:10], 1):
            report_lines.append(f"{i}. [{cit.title}]({cit.url})")

        return CompetitiveLegalReport(
            topic=topic,
            depth=depth,
            key_cases=unique_cases[:10],
            regulatory_landscape=regulatory_landscape,
            jurisdictional_comparison=jurisdictional_comparison,
            trends=trends[:10],
            citations=citations,
            report_markdown="\n".join(report_lines),
        )


# ---------------------------------------------------------------------------
# Document Templates Registry (must be defined after all template functions)
# ---------------------------------------------------------------------------

DOCUMENT_TEMPLATES = {
    "retainer_agreement": _retainer_agreement_template,
    "nda": _nda_template,
    "demand_letter": _demand_letter_template,
    "settlement_agreement": _settlement_agreement_template,
    "power_of_attorney": _power_of_attorney_template,
    "trust_document": _trust_document_template,
}
