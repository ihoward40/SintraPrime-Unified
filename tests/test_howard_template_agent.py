import json
from pathlib import Path

from agents.howard_template_agent import TEMPLATES


def _load_agent_passport_template_file():
    template_path = (
        Path(__file__).resolve().parent.parent
        / "intake_templates"
        / "agent_passport_template.json"
    )
    return json.loads(template_path.read_text(encoding="utf-8"))


def test_agent_passport_template_registered_matches_file_schema():
    payload = TEMPLATES["agent_passport_template.json"]
    file_payload = _load_agent_passport_template_file()

    for key in ("date_found",):
        file_payload[key] = payload[key]

    assert payload == file_payload


def test_agent_passport_template_file_sections():
    payload = _load_agent_passport_template_file()

    for key in ("case_name", "evidence_type", "title", "source"):
        assert key in payload
    assert {"role", "jurisdictions", "approval_level", "constraints"} <= set(payload["authority"])
    assert {"success_rate", "average_cycle_time_hours", "sla_compliance_rate", "period"} <= set(
        payload["performance"]
    )
    assert {"overall", "components", "last_updated"} <= set(payload["trust_score"])
    assert {
        "identity_confidence",
        "authority_compliance",
        "competency_reliability",
        "integration_health",
        "performance_consistency",
    } <= set(payload["trust_score"]["components"])
