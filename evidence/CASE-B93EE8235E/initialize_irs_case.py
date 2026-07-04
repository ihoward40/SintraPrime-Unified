"""
Initialize IRS case using CaseTemplate v2.1.0.
Case: IRS CP23 / Letter 3176C / 2024 Tax Dispute
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from case_template import CaseTemplate

case = CaseTemplate(
    case_id="CASE-B93EE8235E",
    case_name="IRS CP23 / Letter 3176C / 2024 Tax Dispute",
    evidence_counter_start=600,
    description="IRS assessed $74,280 for tax year 2024. Return claimed $250,000 estimated tax payments via vouchers. IRS did not credit payments. Letter 3176C classifies return as frivolous. $5,000 penalty risk under IRC 6702.",
    priority="high",
    external_action="locked",
)

case.enable_module("tax")
print("Module: tax enabled")

# ── Register Evidence ────────────────────────────────────────────────

downloads = Path(r"C:\Users\admin\Downloads")

evidence_files = [
    ("IRS cp23.pdf", "CP23 Notice - IRS applied payment differently than intended", "10_Responses", "2026-01-01"),
    ("IRS LTR 3176C.pdf", "Letter 3176C - Frivolous return warning, 30-day response deadline", "10_Responses", "2026-06-03"),
    ("IRS cp504.pdf", "CP504 - Final Balance Due Reminder, Notice of Intent to Levy", "10_Responses", "2026-01-01"),
    ("cp71c.pdf", "CP71C - IRS balance due notice", "10_Responses", "2026-01-01"),
    ("IRS cp71c (1).pdf", "CP71C - Additional IRS balance notice", "10_Responses", "2026-01-01"),
    ("IRS Letter 2026-06-17.pdf", "IRS Tax Compliance Report dated June 18, 2026", "10_Responses", "2026-06-18"),
    ("2024 IRS account trans.pdf", "2024 IRS Account Transcript - shows TC 150, TC 810 freeze, no $250k credit", "02_Credit_Reports", "2026-01-01"),
    ("2024 IRS Record of account trans.pdf", "2024 Record of Account Transcript", "02_Credit_Reports", "2026-01-01"),
    ("2024 IRS Return trans.pdf", "2024 Return Transcript", "02_Credit_Reports", "2026-01-01"),
    ("2024 IRS Wages.pdf", "2024 Wage and Income Transcript", "02_Credit_Reports", "2026-01-01"),
    ("2024_TaxReturn.pdf", "2024 Form 1040 - claimed $250k estimated payments, $74,280 tax", "03_Original_Creditor", "2025-02-05"),
    ("ihoward40_TaxReturnFromTTO_Filing.pdf", "TurboTax filing package for 2024 return", "03_Original_Creditor", "2025-02-05"),
    ("IRS_CP23_Conditional_Acceptance_2024.pdf", "Conditional Acceptance response to CP23 (draft)", "08_Drafts", "2026-01-01"),
    ("IRS_CP23_Conditional_Acceptance_2024 (1).pdf", "Conditional Acceptance response to CP23 (version 2)", "08_Drafts", "2026-01-01"),
    ("IRS_Frivolous_Designation_Challenge.pdf", "Challenge to IRS frivolous return designation (draft)", "08_Drafts", "2026-01-01"),
    ("Defense_and_Refund_Credit_Strategy_for_Isiah_Howard.pdf", "Defense and refund credit strategy document", "07_Legal_Research", "2026-01-01"),
]

for filename, title, folder, date in evidence_files:
    filepath = downloads / filename
    if filepath.exists():
        item = case.register_evidence(
            source_file=filepath,
            evidence_type="pdf",
            title=title,
            description=f"Source: {filename}",
            source="IRS / TurboTax / ChatGPT analysis",
            custodian="Isiah Howard",
            folder=folder,
            date_of_event=date,
            acquisition_method="download",
            acquisition_date="2026-07-03",
            obtained_from="Downloads folder",
            authenticity_status="original",
            verification_status="unverified",
        )
        print(f"Evidence: {item['evidence_id']} - {title[:60]}")
    else:
        print(f"NOT FOUND: {filename}")

# ── Chronology ───────────────────────────────────────────────────────

events = [
    ("2023-04-01", "Q1 2024 estimated tax payment voucher prepared ($62,500)", "payment_voucher"),
    ("2023-06-01", "Q2 2024 estimated tax payment voucher prepared ($62,500)", "payment_voucher"),
    ("2023-09-01", "Q3 2024 estimated tax payment voucher prepared ($62,500)", "payment_voucher"),
    ("2024-01-01", "Q4 2024 estimated tax payment voucher prepared ($62,500)", "payment_voucher"),
    ("2024-11-30", "Cover letter transmitting vouchers and payment instruments to IRS", "correspondence_outgoing"),
    ("2024-12-05", "IRS Kansas City received package (certified mail)", "delivery_confirmed"),
    ("2025-01-08", "IRS Kansas City received second package (certified mail)", "delivery_confirmed"),
    ("2025-01-21", "IRS placed TC 810 Refund Freeze on account", "irs_action"),
    ("2025-01-28", "IRS Kansas City received third package (certified mail)", "delivery_confirmed"),
    ("2025-02-05", "2024 Form 1040 filed - claimed $250,000 estimated payments, $74,280 tax, $175,720 refund", "tax_filing"),
    ("2025-03-31", "IRS processed return (TC 150) - assessed $74,280 tax", "irs_action"),
    ("2026-01-01", "CP23 notice issued - IRS applied payment differently", "irs_notice"),
    ("2026-01-01", "CP504 notice issued - Final balance due, intent to levy", "irs_notice"),
    ("2026-06-03", "Letter 3176C issued - frivolous return warning, 30-day deadline", "irs_notice"),
    ("2026-06-17", "IRS Tax Compliance Report shows $89,458.02 balance for 2024", "irs_notice"),
    ("2026-07-03", "Evidence repository established for IRS case", "system"),
]

for date, event, cat in events:
    case.add_chronology_event(date=date, event=event, category=cat)
print(f"\nChronology: {len(events)} events added")

# ── Facts ────────────────────────────────────────────────────────────

facts = [
    ("2024 Form 1040 was filed on February 5, 2025", ["EV-2026-00611", "EV-2026-00612"], "supported", 0.9, "", "Confirmed by Return Transcript and filing package"),
    ("The return claimed $250,000 in estimated tax payments on Line 26", ["EV-2026-00611"], "supported", 0.9, "", "Visible on Form 1040"),
    ("The return reported $74,280 total tax", ["EV-2026-00611"], "supported", 0.9, "", "Visible on Form 1040"),
    ("The return claimed $175,720 refund", ["EV-2026-00611"], "supported", 0.9, "", "Calculated from $250,000 payments minus $74,280 tax"),
    ("IRS processed the return on March 31, 2025 (TC 150)", ["EV-2026-00607"], "supported", 0.9, "", "Visible on Account Transcript"),
    ("IRS placed TC 810 Refund Freeze on January 21, 2025", ["EV-2026-00607"], "supported", 0.9, "", "Visible on Account Transcript"),
    ("IRS Account Transcript does NOT show a $250,000 payment posting (TC 670)", ["EV-2026-00607"], "supported", 0.85, "", "No TC 670 for $250,000 visible on transcript"),
    ("Certified mail confirms IRS received packages on Dec 5 2024, Jan 8 2025, Jan 28 2025", [], "partially_supported", 0.6, "Green card photos need to be registered as evidence", "ChatGPT analysis confirms receipt dates"),
    ("IRS issued Letter 3176C classifying the return as frivolous on June 3, 2026", ["EV-2026-00602"], "supported", 0.9, "", "Letter in evidence"),
    ("IRS balance for 2024 is approximately $89,458 including penalties and interest", ["EV-2026-00606"], "supported", 0.85, "", "Per IRS Tax Compliance Report June 18, 2026"),
    ("The $250,000 in vouchers were prepared as 1040-ES estimated payment vouchers", [], "partially_supported", 0.5, "Physical voucher evidence needs registration", "ChatGPT analysis of photographs"),
    ("No EFTPS confirmation, cancelled check, or Treasury payment receipt has been located", [], "supported", 0.7, "May exist but not yet found in evidence", "Critical evidence gap"),
]

for fact_text, ev_ids, status, conf, missing, notes in facts:
    case.add_fact(
        fact_text=fact_text,
        supporting_evidence_ids=ev_ids,
        status=status,
        confidence_score=conf,
        missing=missing,
        notes=notes,
    )
print(f"Facts: {len(facts)} added")

# ── Authorities ──────────────────────────────────────────────────────

authorities = [
    ("IRC 6702 - Frivolous Tax Submissions Penalty", "26 U.S.C. 6702", "federal_statute", "federal", [], "primary", True, 1.0, "The $5,000 penalty IRS is threatening. Must be responded to within 30 days."),
    ("IRC 6651 - Failure to Pay Penalty", "26 U.S.C. 6651", "federal_statute", "federal", [], "primary", True, 0.8, "Penalties being added to balance"),
    ("IRC 6601 - Interest on Underpayment", "26 U.S.C. 6601", "federal_statute", "federal", [], "primary", True, 0.8, "Interest accruing on assessed balance"),
    ("26 CFR 601.506 - Inspection of IRS Records", "26 C.F.R. 601.506", "regulation", "federal", [], "persuasive", False, 0.5, "Can be used to request IRS internal records showing what happened to submitted packages"),
    ("IRC 7433 - Civil Action for IRS Unauthorized Collection", "26 U.S.C. 7433", "federal_statute", "federal", [], "persuasive", False, 0.4, "Potential cause of action if IRS mishandled submissions"),
    ("IRC 6151 - Time for Payment", "26 U.S.C. 6151", "federal_statute", "federal", [], "primary", True, 0.6, "Governs when tax must be paid"),
    ("Notice 2010-33 - Frivolous Positions List", "IRS Notice 2010-33", "administrative_guidance", "federal", [], "primary", True, 0.9, "IRS list of frivolous positions. Voucher/lawful money theories likely on this list."),
    ("IRC 6343 - Levy Restrictions", "26 U.S.C. 6343", "federal_statute", "federal", [], "persuasive", False, 0.5, "Hardship levy protection. Can request Currently Not Collectible status."),
]

for auth, cite, atype, jur, sup, strength, mand, weight, notes in authorities:
    case.add_authority(
        authority=auth, citation=cite, authority_type=atype, jurisdiction=jur,
        supports=sup, strength=strength, mandatory=mand, weight=weight, notes=notes,
    )
print(f"Authorities: {len(authorities)} added")

# ── Legal Analyses ───────────────────────────────────────────────────

# Need to get fact IDs first
fact_data = case._load_json(case.fact_ledger_path)
fct_ids = [f["fact_id"] for f in fact_data["facts"]]

analyses = [
    ("Did the IRS receive the taxpayer's submissions?",
     "Certified mail receipts confirm delivery to IRS Kansas City on three dates. However, receipt of mail is not the same as processing or crediting payments.",
     [fct_ids[7]], ["AUTH-0004"], "partially_supported", 0.5,
     "IRS received packages but transcript shows no corresponding payment credit",
     "Need IRS internal records via 601.506 request to determine what happened after receipt"),
    ("Is the $250,000 estimated tax payment claim supported by evidence?",
     "The return claims $250,000 but no conventional payment evidence (EFTPS, cancelled check, Treasury receipt) has been located. Vouchers show intent but not payment.",
     [fct_ids[1], fct_ids[10], fct_ids[11]], ["AUTH-0007"], "unsupported", 0.2,
     "Claim is not supported by conventional payment evidence",
     "CRITICAL: Without payment proof, IRS position that no payment was made is stronger"),
    ("Should the frivolous return designation be challenged directly?",
     "Notice 2010-33 lists positions similar to voucher/lawful money theories as frivolous. Direct challenge risks $5,000 penalty. Safer path: file corrected return.",
     [fct_ids[8]], ["AUTH-0001", "AUTH-0007"], "partially_supported", 0.6,
     "Direct challenge is risky. Corrected return is safer.",
     "ChatGPT recommendation: withdraw frivolous position, file corrected 1040-X"),
    ("Can the assessed tax be reduced through a corrected return?",
     "If 2024 Schedule C income was overstated, a corrected return with actual income figures could reduce the $74,280 assessment. Requires bank statement reconstruction.",
     [fct_ids[2], fct_ids[3]], [], "partially_supported", 0.5,
     "Possible but requires income reconstruction from bank records",
     "Need to collect all 2024 bank statements, payment app records, and business expense documentation"),
    ("Should hardship/CNC status be requested?",
     "If taxpayer cannot pay the assessed balance, IRC 6343 allows hardship protection. This stops collection while the correction is processed.",
     [fct_ids[9]], ["AUTH-0008"], "partially_supported", 0.5,
     "Recommended parallel action while correcting the return",
     "File Form 433-F or 433-A with hardship request"),
]

for q, text, fids, aids, status, conf, conclusion, notes in analyses:
    case.add_legal_analysis(
        question=q, analysis_text=text, supporting_fact_ids=fids,
        legal_authority_ids=aids, status=status, confidence_score=conf,
        conclusion=conclusion, notes=notes,
    )
print(f"Legal analyses: {len(analyses)} added")

# ── Decisions ────────────────────────────────────────────────────────

decisions = [
    ("Should we file another voucher/remittance package?", "NO",
     "Letter 3176C classifies the return as frivolous. Another voucher submission would trigger $5,000 penalty under IRC 6702 and strengthen IRS position.",
     ["LEG-0002", "LEG-0003"], ["Continue voucher strategy", "File corrected return instead"],
     "2026-07-03", "ChatGPT + Hermes"),
    ("Should we file a corrected 2024 Form 1040-X?", "YES - PENDING INCOME RECONSTRUCTION",
     "Corrected return removes frivolous position and establishes real tax liability. Must reconstruct actual 2024 income from bank statements first.",
     ["LEG-0004"], ["Accept current assessment", "File another voucher"],
     "2026-07-03", "ChatGPT + Hermes",
     "Do NOT file until income reconstruction is complete from bank statements"),
    ("Should we request hardship/CNC status?", "YES - IN PARALLEL",
     "Stops collection activity while correction is processed. Reduces pressure from levies and notices.",
     ["LEG-0005"], ["Wait for correction to process", "Set up installment agreement"],
     "2026-07-03", "ChatGPT + Hermes"),
    ("Should we request IRS internal records via 26 CFR 601.506?", "YES",
     "Need to determine what IRS did with the three certified mail packages. This is a records request, not a tax theory argument.",
     ["LEG-0001"], ["Assume IRS discarded packages", "File TIGTA complaint"],
     "2026-07-03", "ChatGPT + Hermes",
     "Request IDRS history, payment posting records, and correspondence file for all three delivery dates"),
]

for q, d, r, inputs, alts, date, author, *extra in decisions:
    notes = extra[0] if extra else ""
    case.add_decision(question=q, decision=d, reason=r, inputs=inputs, alternatives_considered=alts, decision_date=date, author=author, notes=notes)
print(f"Decisions: {len(decisions)} added")

# ── Sufficiency Rules ────────────────────────────────────────────────

rules = [
    ("Payment Evidence", "The $250,000 estimated tax payment was actually made",
     ["EFTPS confirmation", "Cancelled check", "Treasury payment receipt", "Bank statement showing debit", "IRS transcript showing TC 670"], 1),
    ("Income Documentation", "The 2024 Schedule C income figure is accurate",
     ["Bank statements Jan-Dec 2024", "Payment app records", "Invoices", "Business expense receipts"], 2),
    ("IRS Receipt Proof", "IRS received and processed the submitted packages",
     ["Certified mail green cards", "IRS internal records", "IDRS activity log"], 2),
    ("Hardship Qualification", "Taxpayer qualifies for Currently Not Collectible status",
     ["Form 433-F", "Income documentation", "Expense documentation", "Asset documentation"], 3),
]

for name, claim, docs, min_req in rules:
    case.add_sufficiency_rule(rule_name=name, claim_description=claim, required_documents=docs, minimum_required=min_req)
print(f"Sufficiency rules: {len(rules)} added")

# ── Detect Contradictions ────────────────────────────────────────────

contras = case.detect_contradictions()
print(f"Contradictions: {len(contras)} detected")

# ── Validate Integrity ───────────────────────────────────────────────

integrity = case.validate_integrity()
print(f"Integrity: {integrity['issue_count']} issues, valid={integrity['valid']}")

# ── Generate Packet ──────────────────────────────────────────────────

print("\nGenerating case packet v001...")
case.generate_packet()

print()
print(case.status())