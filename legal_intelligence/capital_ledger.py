"""SP-CAPITAL-LEDGER-001 — double-entry private-capital subledger.

Tracks internal advances, principal, accrued interest, payments, collateral values,
reserve status, delinquency, and policy exceptions. This is an operational subledger;
it does not replace the entity's general ledger, tax books, or regulated servicing system.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


TWOPLACES = Decimal("0.01")


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class LedgerLine:
    account: str
    debit: Decimal = Decimal("0.00")
    credit: Decimal = Decimal("0.00")
    memo: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"account": self.account, "debit": str(self.debit), "credit": str(self.credit), "memo": self.memo}


@dataclass
class CapitalLedgerEntry:
    entry_id: str
    effective_date: str
    facility_id: str
    event_type: str
    lines: list[LedgerLine]
    source_ref: str
    approved_by: str
    exception_codes: list[str] = field(default_factory=list)

    @property
    def balanced(self) -> bool:
        debits = sum((x.debit for x in self.lines), Decimal("0.00"))
        credits = sum((x.credit for x in self.lines), Decimal("0.00"))
        return debits == credits

    def as_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "effective_date": self.effective_date,
            "facility_id": self.facility_id,
            "event_type": self.event_type,
            "source_ref": self.source_ref,
            "approved_by": self.approved_by,
            "exception_codes": list(self.exception_codes),
            "balanced": self.balanced,
            "lines": [x.as_dict() for x in self.lines],
        }


@dataclass
class FacilitySnapshot:
    facility_id: str
    principal_outstanding: Decimal
    accrued_interest: Decimal
    payments_received: Decimal
    collateral_value: Decimal
    reserve_required: Decimal
    reserve_available: Decimal
    days_past_due: int
    exception_codes: list[str]
    status: str
    beneficial_suggestions: list[str]

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ["principal_outstanding", "accrued_interest", "payments_received", "collateral_value", "reserve_required", "reserve_available"]:
            data[key] = str(data[key])
        return data


class CapitalLedgerEngine:
    MODULE_ID = "SP-CAPITAL-LEDGER-001"

    def validate_entry(self, entry: CapitalLedgerEntry) -> list[str]:
        errors: list[str] = []
        if not entry.entry_id:
            errors.append("LEDGER_ENTRY_ID_REQUIRED")
        if not entry.facility_id:
            errors.append("LEDGER_FACILITY_ID_REQUIRED")
        if not entry.source_ref:
            errors.append("LEDGER_SOURCE_REF_REQUIRED")
        if not entry.approved_by:
            errors.append("LEDGER_APPROVER_REQUIRED")
        if not entry.lines:
            errors.append("LEDGER_LINES_REQUIRED")
        if not entry.balanced:
            errors.append("LEDGER_ENTRY_NOT_BALANCED")
        return errors

    def funding_entry(self, *, entry_id: str, facility_id: str, amount: Any, source_ref: str, approved_by: str, effective_date: str | None = None) -> CapitalLedgerEntry:
        amt = _money(amount)
        return CapitalLedgerEntry(
            entry_id=entry_id,
            effective_date=effective_date or date.today().isoformat(),
            facility_id=facility_id,
            event_type="FUNDING",
            source_ref=source_ref,
            approved_by=approved_by,
            lines=[
                LedgerLine("internal_loan_receivable", debit=amt, memo="funded principal"),
                LedgerLine("cash", credit=amt, memo="cash advanced"),
            ],
        )

    def interest_accrual_entry(self, *, entry_id: str, facility_id: str, amount: Any, source_ref: str, approved_by: str, effective_date: str | None = None) -> CapitalLedgerEntry:
        amt = _money(amount)
        return CapitalLedgerEntry(
            entry_id=entry_id,
            effective_date=effective_date or date.today().isoformat(),
            facility_id=facility_id,
            event_type="INTEREST_ACCRUAL",
            source_ref=source_ref,
            approved_by=approved_by,
            lines=[
                LedgerLine("accrued_interest_receivable", debit=amt),
                LedgerLine("interest_income", credit=amt),
            ],
        )

    def payment_entry(self, *, entry_id: str, facility_id: str, cash_amount: Any, principal_amount: Any, interest_amount: Any, source_ref: str, approved_by: str, effective_date: str | None = None) -> CapitalLedgerEntry:
        cash = _money(cash_amount)
        principal = _money(principal_amount)
        interest = _money(interest_amount)
        lines = [LedgerLine("cash", debit=cash)]
        if interest:
            lines.append(LedgerLine("accrued_interest_receivable", credit=interest))
        if principal:
            lines.append(LedgerLine("internal_loan_receivable", credit=principal))
        entry = CapitalLedgerEntry(
            entry_id=entry_id,
            effective_date=effective_date or date.today().isoformat(),
            facility_id=facility_id,
            event_type="PAYMENT",
            source_ref=source_ref,
            approved_by=approved_by,
            lines=lines,
        )
        if principal + interest != cash:
            entry.exception_codes.append("PAYMENT_ALLOCATION_MISMATCH")
        return entry

    def snapshot(self, context: dict[str, Any]) -> FacilitySnapshot:
        principal = _money(context.get("principal_outstanding"))
        interest = _money(context.get("accrued_interest"))
        payments = _money(context.get("payments_received"))
        collateral = _money(context.get("collateral_value"))
        reserve_required = _money(context.get("reserve_required"))
        reserve_available = _money(context.get("reserve_available"))
        days_past_due = int(context.get("days_past_due") or 0)
        exceptions = list(dict.fromkeys(context.get("exception_codes") or []))
        if reserve_available < reserve_required:
            exceptions.append("RESERVE_SHORTFALL")
        if days_past_due >= 30:
            exceptions.append("DELINQUENCY_30_PLUS")
        if principal > 0 and collateral > 0 and collateral < principal:
            exceptions.append("UNDERCOLLATERALIZED")
        status = "EXCEPTION" if exceptions else "CURRENT"
        suggestions = [
            "Reconcile the capital subledger to the general ledger and bank statements monthly.",
            "Attach immutable source references for every funding, accrual, payment, collateral revaluation, and exception override.",
        ]
        if "RESERVE_SHORTFALL" in exceptions:
            suggestions.append("Suspend discretionary new advances until the reserve floor is restored or Principal approves a documented exception.")
        if "DELINQUENCY_30_PLUS" in exceptions:
            suggestions.append("Escalate to servicing review, covenant testing, collateral verification, and a documented workout/default decision.")
        return FacilitySnapshot(
            facility_id=str(context.get("facility_id") or ""),
            principal_outstanding=principal,
            accrued_interest=interest,
            payments_received=payments,
            collateral_value=collateral,
            reserve_required=reserve_required,
            reserve_available=reserve_available,
            days_past_due=days_past_due,
            exception_codes=list(dict.fromkeys(exceptions)),
            status=status,
            beneficial_suggestions=suggestions,
        )
