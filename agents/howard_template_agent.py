import json
from datetime import datetime
from pathlib import Path

TEMPLATE_DIR = Path("intake_templates")
TEMPLATE_DIR.mkdir(exist_ok=True)

TODAY = datetime.now().strftime("%Y-%m-%d")


TEMPLATES = {
    "paypal_evidence_template.json": {
        "case_name": "PayPal",
        "evidence_type": "screenshot",
        "title": "PayPal evidence title here",
        "source": "PayPal screenshot / PayPal account page / Gmail",
        "date_found": TODAY,
        "amount": "",
        "account_identifier": "isiahhoward49@gmail.com",
        "gmail_link": "",
        "file_path": "",
        "notes": "Describe exactly what the PayPal record shows. Example: account limitation, negative balance, transaction ID, notice, restriction, or ledger issue. External action remains locked."
    },

    "uacc_vroom_evidence_template.json": {
        "case_name": "UACC",
        "evidence_type": "email",
        "title": "UACC / Vroom evidence title here",
        "source": "Gmail / contract / statement / credit report / PDF",
        "date_found": TODAY,
        "amount": "",
        "account_identifier": "UACC / Vroom / 2015 Ford Taurus / VIN ending FG124116",
        "gmail_link": "",
        "file_path": "",
        "notes": "Describe the UACC/Vroom record. Include balance claimed, charge-off, settlement, validation issue, assignment issue, repo/deficiency issue, or reporting issue. External action remains locked."
    },

    "halsted_lvnv_evidence_template.json": {
        "case_name": "Halsted",
        "evidence_type": "email",
        "title": "Halsted / LVNV collection evidence title here",
        "source": "Gmail / collection notice / credit report",
        "date_found": TODAY,
        "amount": "",
        "account_identifier": "Halsted / LVNV Funding / Bank of Missouri / Milestone Mastercard",
        "gmail_link": "",
        "file_path": "",
        "notes": "Describe the collection notice, claimed creditor, alleged balance, payment offer, date, prior payment claim, validation issue, or reporting issue. External action remains locked."
    },

    "aff_finwise_evidence_template.json": {
        "case_name": "AFF",
        "evidence_type": "email",
        "title": "AFF / FinWise evidence title here",
        "source": "Gmail / CFPB / state complaint / credit report / account statement",
        "date_found": TODAY,
        "amount": "",
        "account_identifier": "American First Finance / FinWise Bank",
        "gmail_link": "",
        "file_path": "",
        "notes": "Describe the AFF/FinWise record. Include complaint number, dispute record, tradeline issue, rent-a-bank/usury issue, or billing/accounting issue if supported by evidence. External action remains locked."
    },

    "self_leadbank_evidence_template.json": {
        "case_name": "Self",
        "evidence_type": "credit report",
        "title": "Self Financial / Lead Bank evidence title here",
        "source": "Experian / Equifax / TransUnion / Credit monitoring / Gmail",
        "date_found": TODAY,
        "amount": "",
        "account_identifier": "Self Financial / Lead Bank",
        "gmail_link": "",
        "file_path": "",
        "notes": "Describe the tradeline, alert, derogatory reporting, dispute result, balance issue, date issue, or account-status issue. External action remains locked."
    },

    "verizon_evidence_template.json": {
        "case_name": "Verizon",
        "evidence_type": "complaint record",
        "title": "Verizon evidence title here",
        "source": "CFPB / FCC / Verizon Executive Relations / bill / screenshot / Gmail",
        "date_found": TODAY,
        "amount": "",
        "account_identifier": "Verizon Wireless / Verizon complaint matter",
        "gmail_link": "",
        "file_path": "",
        "notes": "Describe the Verizon record. Include complaint number, billing issue, service disconnection, executive relations case number, account notes, or payment dispute. External action remains locked."
    },

    "chase_wells_ews_evidence_template.json": {
        "case_name": "Chase",
        "evidence_type": "bank record",
        "title": "Chase / Wells Fargo / EWS evidence title here",
        "source": "Bank statement / Early Warning disclosure / adverse action notice / Gmail",
        "date_found": TODAY,
        "amount": "",
        "account_identifier": "Chase / Wells Fargo / Early Warning Services",
        "gmail_link": "",
        "file_path": "",
        "notes": "Describe the bank-screening record, adverse action, account closure, NSF/post-no-debits notation, EWS disclosure item, or statement issue. External action remains locked."
    },

    "sap_fmcsa_evidence_template.json": {
        "case_name": "SAP",
        "evidence_type": "employment / drug-test record",
        "title": "SAP / FMCSA evidence title here",
        "source": "FMCSA Clearinghouse / DataQs / SAP provider / Concentra / employer / temp agency",
        "date_found": TODAY,
        "amount": "",
        "account_identifier": "SAP / FMCSA / trucking employment matter",
        "gmail_link": "",
        "file_path": "",
        "notes": "Describe the drug-test, SAP, Clearinghouse, DataQs, employer, MRO, chain-of-custody, split-specimen, or passed follow-up test evidence. External action remains locked."
    },

    "expungement_evidence_template.json": {
        "case_name": "Expungement",
        "evidence_type": "court record",
        "title": "Expungement evidence title here",
        "source": "Court record / disposition / attorney email / docket / background check",
        "date_found": TODAY,
        "amount": "",
        "account_identifier": "New Jersey / Bergen County / criminal record matter",
        "gmail_link": "",
        "file_path": "",
        "notes": "Describe the case record, charge, disposition, docket, PCR issue, attorney communication, background-check harm, or expungement eligibility item. External action remains locked."
    },

    "funding_grants_evidence_template.json": {
        "case_name": "Funding",
        "evidence_type": "grant / funding record",
        "title": "Funding / Grants evidence title here",
        "source": "Grant portal / email / application / denial / business document",
        "date_found": TODAY,
        "amount": "",
        "account_identifier": "IKE SOLUTIONS / ISIAH TARIK HOWARD TRUST / grant or funding matter",
        "gmail_link": "",
        "file_path": "",
        "notes": "Describe grant opportunity, deadline, denial, eligibility issue, application record, funding amount, or supporting business evidence. External action remains locked."
    },

    "generic_evidence_template.json": {
        "case_name": "",
        "evidence_type": "",
        "title": "",
        "source": "",
        "date_found": TODAY,
        "amount": "",
        "account_identifier": "",
        "gmail_link": "",
        "file_path": "",
        "notes": "Describe what the evidence proves. Keep it factual. No unsupported legal conclusions. External action remains locked."
    },

    "batch_evidence_template.json": {
        "evidence_items": [
            {
                "case_name": "PayPal",
                "evidence_type": "screenshot",
                "title": "Batch evidence item 1 title",
                "source": "Screenshot / Gmail / PDF",
                "date_found": TODAY,
                "amount": "",
                "account_identifier": "",
                "gmail_link": "",
                "file_path": "",
                "notes": "Describe evidence item 1. External action remains locked."
            },
            {
                "case_name": "Verizon",
                "evidence_type": "complaint record",
                "title": "Batch evidence item 2 title",
                "source": "Complaint portal / Gmail / account record",
                "date_found": TODAY,
                "amount": "",
                "account_identifier": "",
                "gmail_link": "",
                "file_path": "",
                "notes": "Describe evidence item 2. External action remains locked."
            }
        ]
    }
}


def write_template(filename, payload):
    path = TEMPLATE_DIR / filename
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def main():
    print("Howard Template Agent starting...")
    print("Phase 2G Auto-Create Intake JSON Templates: ACTIVE")

    created = []

    for filename, payload in TEMPLATES.items():
        path = write_template(filename, payload)
        created.append(str(path))
        print(f"Created template: {path}")

    index_path = TEMPLATE_DIR / "README_HOW_TO_USE_TEMPLATES.txt"
    index_path.write_text(
        "HOWARD RECOVERY INTAKE TEMPLATE GUIDE\n\n"
        "1. Open any .json template in this folder.\n"
        "2. Fill in the blanks without changing the field names.\n"
        "3. Save a completed copy into the intake folder.\n"
        "4. Howard Intake Watch Agent will process it automatically.\n"
        "5. Good files move to processed. Bad files move to errors.\n"
        "6. External action remains locked. These templates do not send, file, email, call, or contact anyone.\n\n"
        "Minimum required fields:\n"
        "- case_name or case_id\n"
        "- evidence_type\n"
        "- title\n"
        "- source\n\n"
        "Use case_name when possible. The Case ID Resolver will find the active case ID.\n",
        encoding="utf-8"
    )

    print(f"Created guide: {index_path}")
    print("Done. Templates are ready.")


if __name__ == "__main__":
    main()