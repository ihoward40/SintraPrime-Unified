import json
import unittest
from pathlib import Path

import pytest

from ws8_cmrd.calculator import VERSION, calculate, replay

BASE = {"mailing_date": "2024-02-28", "delivery_date": "2024-03-01", "trigger": "mailing",
            "period": 2, "day_type": "calendar", "start_day": "exclude", "jurisdiction": "NJ",
            "holidays": [], "today": "2024-02-28"}

class CalculatorTests(unittest.TestCase):
    def calc(self, **changes):
        return calculate(**(BASE | changes))

    def test_leap_year_and_separate_delivery(self):
        r = self.calc()
        assert r["calculation"]["value"] == "2024-03-01"
        assert r["calculation_mode"] == "SCENARIO_ARITHMETIC"
        assert r["calculation"]["adjusted_date"] is None
        assert len(r["chronology"]) == 3

    def test_inclusive_start_and_year_boundary(self):
        assert self.calc(mailing_date="2026-12-31", delivery_date=None, start_day="include")["calculation"]["value"] == "2027-01-01"

    def test_business_holiday_and_weekend(self):
        r = self.calc(mailing_date="2026-12-24", delivery_date=None, period=2,
                      day_type="business", holidays=["2026-12-25"])
        assert r["calculation"]["value"] == "2026-12-29"

    def test_weekend_is_never_adjusted(self):
        r = self.calc(mailing_date="2026-09-24", delivery_date=None, period=2)
        assert r["calculation"]["value"] == "2026-09-26"
        assert r["calculation"]["falls_on_weekend"]
        assert r["calculation"]["adjusted_date"] is None

    def test_missing_trigger_or_business_calendar_fails(self):
        with pytest.raises(ValueError, match="delivery date is required for selected trigger"):
            self.calc(trigger="delivery", delivery_date=None)
        with pytest.raises(ValueError, match="business-day arithmetic requires an explicit holiday list"):
            self.calc(day_type="business", holidays=None)

    def test_conflicting_chronology_fails(self):
        with pytest.raises(ValueError, match="delivery date precedes mailing date"):
            self.calc(delivery_date="2024-02-27")


    def test_manifest_replay_and_failure_cases(self):
        manifest = json.loads(Path("ws8_cmrd/test-manifest.json").read_text())
        assert manifest["calculator_version"] == VERSION
        assert len(manifest["passing_scenarios"]) == 6
        for case in manifest["passing_scenarios"]:
            with self.subTest(case=case["id"]):
                receipt = calculate(**case["inputs"])
                assert receipt["calculation"]["value"] == case["expected_date"]
                exported = json.loads(json.dumps(receipt))
                assert replay(exported)["replay_status"] == "PASS"
        for case in manifest["failure_scenarios"]:
            with self.subTest(case=case["id"]):
                if case["target"] == "calculate":
                    with pytest.raises(ValueError):  # noqa: PT011 -- manifest failure set raises heterogeneous ValueErrors
                        calculate(**case["inputs"])
                else:
                    receipt = self.calc()
                    for key, value in case["mutations"].items():
                        if key.startswith("user_inputs."):
                            receipt["user_inputs"][key.split(".", 1)[1]] = value
                        elif key.startswith("calculation."):
                            receipt["calculation"][key.split(".", 1)[1]] = value
                        else:
                            receipt[key] = value
                    with pytest.raises(ValueError):  # noqa: PT011 -- manifest failure set raises heterogeneous ValueErrors
                        replay(receipt)

if __name__ == "__main__":
    unittest.main()
