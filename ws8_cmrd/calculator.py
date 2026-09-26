"""WS8-CMRD-001 scenario arithmetic. No legal rule presets."""
from __future__ import annotations

import argparse
import json
import re
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

VERSION = "0.1.0"
NOTICE = "Calculated date based on the rule selected. Verify the governing statute, regulation, contract, court rule, or notice before relying on the date."


def calculate(*, mailing_date: str | None, delivery_date: str | None,
              trigger: str, period: int, day_type: str, start_day: str,
              jurisdiction: str, holidays: list[str] | None = None,
              today: str | None = None) -> dict:
    if trigger not in ("mailing", "delivery"):
        raise ValueError("trigger must be mailing or delivery")
    if day_type not in ("calendar", "business"):
        raise ValueError("day_type must be calendar or business")
    if start_day not in ("exclude", "include"):
        raise ValueError("start_day must be exclude or include")
    if not isinstance(period, int) or isinstance(period, bool) or period <= 0 or period > 3660:
        raise ValueError("period must be an integer from 1 to 3660")
    if not isinstance(jurisdiction, str) or not re.fullmatch(r"[A-Z]{2}(?:-[A-Z]{2})?", jurisdiction):
        raise ValueError("jurisdiction must be an explicit two-letter code or country-region code")
    if day_type == "calendar" and holidays:
        raise ValueError("holiday list cannot affect calendar-day arithmetic; remove it")
    dates = {"mailing": date.fromisoformat(mailing_date) if mailing_date else None,
             "delivery": date.fromisoformat(delivery_date) if delivery_date else None}
    if dates["mailing"] and dates["delivery"] and dates["delivery"] < dates["mailing"]:
        raise ValueError("delivery date precedes mailing date; correct or document this conflict")
    event = dates[trigger]
    if event is None:
        raise ValueError(f"{trigger} date is required for selected trigger")
    holiday_set = {date.fromisoformat(x) for x in (holidays or [])}
    if day_type == "business" and holidays is None:
        raise ValueError("business-day arithmetic requires an explicit holiday list (use [] if none)")
    cursor = event if start_day == "include" else event + timedelta(days=1)
    counted = []
    while len(counted) < period:
        if day_type == "calendar" or (cursor.weekday() < 5 and cursor not in holiday_set):
            counted.append(cursor)
        cursor += timedelta(days=1)
    due = counted[-1]
    reference = date.fromisoformat(today) if today else date.today()
    chronology = [
        {"date": d.isoformat(), "event": key + " date", "source": "user input"}
        for key, d in dates.items() if d is not None
    ]
    chronology.append({"date": due.isoformat(), "event": "scenario calculated date", "source": "arithmetic only"})
    chronology.sort(key=lambda x: (x["date"], x["event"]))
    return {
        "result_id": str(uuid.uuid4()), "utility_id": "WS8-CMRD-001",
        "calculator_version": VERSION, "calculation_mode": "SCENARIO_ARITHMETIC",
        "generated_at": datetime.now(UTC).isoformat(),
        "calculation": {"value": due.isoformat(), "method": f"{period} {day_type} days; start day {start_day}",
                        "intermediate_steps": [d.isoformat() for d in counted],
                        "days_remaining_as_of": reference.isoformat(),
                        "days_remaining": (due - reference).days,
                        "falls_on_weekend": due.weekday() >= 5,
                        "falls_on_supplied_holiday": due in holiday_set,
                        "adjusted_date": None},
        "user_inputs": {"mailing_date": mailing_date, "delivery_date": delivery_date,
                        "trigger": trigger, "period": period, "day_type": day_type,
                        "start_day": start_day, "jurisdiction": jurisdiction,
                        "holidays": sorted(x.isoformat() for x in holiday_set), "today": reference.isoformat()},
        "assumptions": ["The selected event and counting convention are user-defined scenario inputs.",
                        "No weekend/holiday adjustment is applied."],
        "governing_authority": [], "authority_effective_date": None,
        "exceptions_limitations": ["This is scenario arithmetic, not a legal deadline.", NOTICE],
        "evidence_used": [],
        "missing_evidence": ["Original notice or contract", "Envelope or mailing receipt",
                             "Delivery/tracking history", "Applicable governing rule"],
        "result_confidence": "LOW",
        "confidence_reasons": ["Arithmetic inputs are complete; governing rule and evidence are unverified."],
        "next_procedural_step": "Verify the triggering event and counting rule against the governing source.",
        "ike_service_route": None, "chronology": chronology,
    }



REPLAY_FIELDS = (
    "utility_id", "calculator_version", "calculation_mode", "calculation",
    "user_inputs", "assumptions", "governing_authority", "authority_effective_date",
    "exceptions_limitations", "evidence_used", "missing_evidence",
    "result_confidence", "confidence_reasons", "next_procedural_step",
    "ike_service_route", "chronology",
)


def replay(receipt: dict) -> dict:
    """Validate a scenario export against this exact algorithm version.

    This is consistency verification, not cryptographic authenticity.
    """
    if not isinstance(receipt, dict):
        raise ValueError("receipt must be an object")
    if receipt.get("calculator_version") != VERSION:
        raise ValueError("unsupported or altered calculator version")
    if receipt.get("utility_id") != "WS8-CMRD-001":
        raise ValueError("unsupported utility")
    if receipt.get("calculation_mode") != "SCENARIO_ARITHMETIC":
        raise ValueError("unsupported calculation_mode")
    inputs = receipt.get("user_inputs")
    if not isinstance(inputs, dict) or set(inputs) != {
        "mailing_date", "delivery_date", "trigger", "period", "day_type",
        "start_day", "jurisdiction", "holidays", "today"
    }:
        raise ValueError("incomplete or unexpected replay inputs")
    if not isinstance(inputs["holidays"], list) or not isinstance(inputs["today"], str):
        raise ValueError("invalid replay calendar or reference date")
    regenerated = calculate(**inputs)
    for field in REPLAY_FIELDS:
        if field not in receipt or receipt[field] != regenerated[field]:
            raise ValueError(f"replay mismatch: {field}")
    return {"replay_status": "PASS", "calculator_version": VERSION,
            "calculation_mode": "SCENARIO_ARITHMETIC",
            "matched_fields": list(REPLAY_FIELDS),
            "excluded_ephemeral_fields": ["result_id", "generated_at"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=NOTICE)
    parser.add_argument("--mailing-date")
    parser.add_argument("--delivery-date")
    parser.add_argument("--trigger", required=True, choices=["mailing", "delivery"])
    parser.add_argument("--period", required=True, type=int)
    parser.add_argument("--day-type", required=True, choices=["calendar", "business"])
    parser.add_argument("--start-day", required=True, choices=["include", "exclude"])
    parser.add_argument("--jurisdiction", required=True)
    parser.add_argument("--holiday", action="append", dest="holidays")
    parser.add_argument("--today")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = calculate(mailing_date=args.mailing_date, delivery_date=args.delivery_date,
                       trigger=args.trigger, period=args.period, day_type=args.day_type,
                       start_day=args.start_day, jurisdiction=args.jurisdiction,
                       holidays=args.holidays,
                       today=args.today)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Scenario date: {result['calculation']['value']} | export: {args.output}")


if __name__ == "__main__":
    main()
