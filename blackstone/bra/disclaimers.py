"""
BRA — Standard Disclaimer Library
===================================
Approved disclaimer texts from BKR-14 and BKR-15.

Agents MUST use these approved texts for external outputs.
Custom drafting is not permitted without a CDR authorizing a new variant.
These texts are frozen at BKGC v2.0 adoption. Any change requires a CDR.

Usage:
    from blackstone.bra.disclaimers import get_disclaimer, select_disclaimers
    text = get_disclaimer("DIS-NLA-01")
    ids = select_disclaimers(claim_status_code="EDU", confidence_code="CONF-H")
    # ids → ["DIS-NLA-01"]
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# BKR-14 — Not Legal Advice Disclaimers
# ---------------------------------------------------------------------------

NLA_DISCLAIMERS: dict[str, dict[str, str]] = {
    "DIS-NLA-01": {
        "name": "Standard — General External Output",
        "context": "Use for most external Educational or Scholarly outputs",
        "text": (
            "This material is provided for educational and informational purposes only. "
            "It does not constitute legal advice and does not create an attorney-client relationship. "
            "The information presented reflects research conducted as of the date noted and may not account "
            "for subsequent changes in law, regulation, or judicial interpretation. Legal rules vary by "
            "jurisdiction. For advice about your specific situation, consult a qualified attorney licensed "
            "in the applicable jurisdiction."
        ),
    },
    "DIS-NLA-02": {
        "name": "Consumer Rights — Specific Context",
        "context": "Use for consumer rights, credit, and debt-related educational content",
        "text": (
            "This material provides general educational information about consumer rights topics. "
            "It does not constitute legal advice. Consumer protection laws, credit reporting rules, and "
            "debt collection regulations vary by state and depend on the specific facts of each situation. "
            "For guidance about your individual circumstances — including specific accounts, collection "
            "notices, or disputed items — consult a qualified consumer law attorney. Free or low-cost legal "
            "resources may be available in your area."
        ),
    },
    "DIS-NLA-03": {
        "name": "Abbreviated — In-Line Use",
        "context": "Use when a full disclaimer has already appeared in the same document",
        "text": (
            "Educational content only — not legal advice. Rules vary by jurisdiction. "
            "Consult qualified counsel for advice about your specific situation."
        ),
    },
    "DIS-NLA-04": {
        "name": "IRS and Tax Matters",
        "context": "Use for tax, IRS, and federal tax procedure educational content",
        "text": (
            "This material provides general educational information about federal tax procedures and IRS "
            "matters. It does not constitute legal or tax advice and does not create a practitioner-client "
            "relationship. IRS rules, deadlines, and procedures are subject to change. Individual tax "
            "situations are highly fact-specific. For advice about a particular IRS notice, assessment, or "
            "dispute, consult a qualified tax attorney, CPA, or enrolled agent familiar with your specific "
            "circumstances."
        ),
    },
}

# ---------------------------------------------------------------------------
# BKR-15 — Uncertainty and Preliminary Status Disclosures
# ---------------------------------------------------------------------------

UNC_DISCLAIMERS: dict[str, dict[str, str]] = {
    "DIS-UNC-01": {
        "name": "Preliminary Assessment Disclosure",
        "context": "Use when claim carries Confidence Level: Preliminary Assessment (CONF-P)",
        "text": (
            "The following represents a preliminary assessment based on currently available evidence. "
            "This analysis is expected to be materially revised as additional evidence is gathered. "
            "It should not be relied upon for final decisions."
        ),
    },
    "DIS-UNC-02": {
        "name": "Disputed Claim Disclosure",
        "context": "Use when claim carries Claim Status: Disputed (DISP)",
        "text": (
            "The following claim is subject to credible disagreement among authorities. The competing "
            "positions are presented as documented — no single position is currently established as "
            "controlling in the relevant jurisdiction. The applicable outcome in any specific situation "
            "will depend on the jurisdiction, the specific facts, and the authority a court or agency "
            "finds persuasive."
        ),
    },
    "DIS-UNC-03": {
        "name": "Jurisdictional Variance Disclosure",
        "context": "Use when output covers a MULTI:{} jurisdiction knowledge object",
        "text": (
            "The rules described below vary by jurisdiction. The status of this claim in each relevant "
            "jurisdiction is noted. The applicable rule in your situation depends on which jurisdiction "
            "governs your matter. Where jurisdiction has not been confirmed, the most protective or "
            "conservative characterization is presented. Confirmation of the applicable jurisdiction is "
            "recommended before any reliance."
        ),
    },
    "DIS-UNC-04": {
        "name": "Temporal Currency Disclosure",
        "context": "Use when output cites authority that may be subject to change",
        "text": (
            "The authorities cited below reflect the law and regulatory guidance as of the date noted. "
            "Laws, regulations, and agency guidance are subject to change. Readers should verify the "
            "current status of any cited authority before reliance, particularly in rapidly changing "
            "regulatory areas."
        ),
    },
}

# Combined registry
ALL_DISCLAIMERS: dict[str, dict[str, str]] = {**NLA_DISCLAIMERS, **UNC_DISCLAIMERS}


def get_disclaimer(disclaimer_id: str) -> str:
    """
    Retrieve the approved disclaimer text for a given DIS-ID.

    Args:
        disclaimer_id: e.g. "DIS-NLA-01", "DIS-UNC-02"

    Returns:
        The approved text string.

    Raises:
        KeyError: If the disclaimer ID is not registered.
    """
    record = ALL_DISCLAIMERS.get(disclaimer_id)
    if record is None:
        registered = list(ALL_DISCLAIMERS.keys())
        raise KeyError(
            f"Disclaimer ID {disclaimer_id!r} not found in approved library. "
            f"Registered IDs: {registered}. "
            f"To add a new variant, file a CDR per BGS-13."
        )
    return record["text"]


def get_disclaimer_record(disclaimer_id: str) -> dict[str, str]:
    """Return the full record (id, name, context, text) for a disclaimer."""
    record = ALL_DISCLAIMERS.get(disclaimer_id)
    if record is None:
        raise KeyError(f"Disclaimer ID {disclaimer_id!r} not found.")
    return {"id": disclaimer_id, **record}


def select_disclaimers(
    *,
    claim_status_code: str = "",
    confidence_code: str = "",
    jurisdiction_code: str = "",
    is_tax_matter: bool = False,
    is_consumer_rights: bool = False,
    temporal_current: bool = True,
    inline_only: bool = False,
) -> list[str]:
    """
    Recommend which disclaimers to attach to an output based on KO attributes.

    Returns a list of DIS-IDs in recommended display order.
    These are recommendations — agents must include all that apply.
    """
    ids: list[str] = []

    # NLA base
    if inline_only:
        ids.append("DIS-NLA-03")
    elif is_tax_matter:
        ids.append("DIS-NLA-04")
    elif is_consumer_rights:
        ids.append("DIS-NLA-02")
    elif claim_status_code in ("EDU", "SCHOL", "EMRG", "UNVR"):
        ids.append("DIS-NLA-01")

    # Uncertainty overlays
    if confidence_code == "CONF-P":
        ids.append("DIS-UNC-01")
    if claim_status_code == "DISP":
        ids.append("DIS-UNC-02")
    if jurisdiction_code and jurisdiction_code.startswith("MULTI:"):
        ids.append("DIS-UNC-03")
    if not temporal_current:
        ids.append("DIS-UNC-04")

    return ids


def list_all() -> list[dict[str, str]]:
    """Return all registered disclaimer records."""
    return [{"id": k, **v} for k, v in ALL_DISCLAIMERS.items()]
