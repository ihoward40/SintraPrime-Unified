# Trust Compliance Module — Notion Schema

This document describes the Notion database schema for logging Trust
Compliance Module runs, risk registers, and exhibit indexes. Each database
entry corresponds to one `runTrustComplianceMission` execution.

---

## Database: Trust Compliance Runs

| Property | Type | Description |
|---|---|---|
| **Run ID** | Title | Unique run identifier (SHA-256 prefix, 24 chars) |
| **Document Title** | Text | Title extracted from the uploaded document |
| **Document Type** | Select | `CERTIFICATION_OF_TRUST` · `UCC_FINANCING_STATEMENT` · `SECURITY_AGREEMENT` · `AFFIDAVIT` · `BANKING_RESOLUTION` · `TRUSTEE_MINUTES` · `TAX_FORM_W8` · `TAX_FORM` · `GENERAL_TRUST_DOCUMENT` |
| **Run Date** | Date | ISO timestamp of the run |
| **Total Clauses** | Number | Count of sections classified |
| **GREEN Count** | Number | Sections classified GREEN |
| **YELLOW Count** | Number | Sections classified YELLOW |
| **RED Count** | Number | Sections classified RED |
| **Blocked Exports** | Number | Sections blocked from external use |
| **Public Exhibits** | Number | Count of public exhibit entries |
| **Reserve Exhibits** | Number | Count of reserve exhibit entries (internal only) |
| **Status** | Select | `COMPLETE` · `BLOCKED` · `REWRITE_REQUIRED` · `PENDING_REVIEW` |
| **Assigned To** | Person | Team member responsible for review |
| **Tags** | Multi-select | Risk tags present in the run (from risk register) |
| **Receipt JSON** | Files | Attached `run_receipt.json` |
| **Risk Register** | Files | Attached `risk_register.json` |
| **Notes** | Text | Manual notes from the reviewing trustee or counsel |

---

## Database: Risk Register Entries

Linked to the **Trust Compliance Runs** database (many entries per run).

| Property | Type | Description |
|---|---|---|
| **Clause ID** | Title | Unique clause identifier |
| **Run** | Relation | Linked Trust Compliance Run |
| **Section Title** | Text | Title of the document section |
| **Classification** | Select | `GREEN` · `YELLOW` · `RED` |
| **Risk Tags** | Multi-select | Tags applied (see risk tag definitions) |
| **Reason** | Text | Explanation for the classification |
| **Action** | Select | `use` · `rewrite` · `block` |
| **Rewritten Text** | Text | Compliance-rewritten version (populated for YELLOW) |
| **Blocked** | Checkbox | True if the clause is blocked from external use |

---

## Database: Exhibit Index

Linked to the **Trust Compliance Runs** database.

| Property | Type | Description |
|---|---|---|
| **Exhibit ID** | Title | Exhibit identifier (e.g., `Ex-A`, `R-1`) |
| **Run** | Relation | Linked Trust Compliance Run |
| **Title** | Text | Exhibit title |
| **Type** | Select | `public` · `reserve` |
| **Description** | Text | Description of the exhibit contents |
| **Restricted** | Checkbox | True for reserve exhibits (internal only) |
| **Source Document ID** | Text | ID of the source document |
| **File** | Files | Uploaded exhibit file (if available) |

---

## Automation Triggers (Notion + Make.com)

1. **On new Run record created** → trigger Make.com scenario to:
   - Create Google Drive folder: `Trust Compliance / {Run Date} — {Document Title}`
   - Copy `run_receipt.json` and `risk_register.json` to the folder
   - Send Slack/email notification to assigned reviewer

2. **On Status = COMPLETE and RED Count = 0** → mark for optional client delivery

3. **On Status = BLOCKED or RED Count > 0** → flag for mandatory attorney/CPA review before any client delivery

---

## Notes

- Never expose reserve exhibit content to clients without attorney sign-off.
- Run receipts are immutable; do not edit after creation.
- All database entries should be archived (not deleted) to maintain the audit trail.
