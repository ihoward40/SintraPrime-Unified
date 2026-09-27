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

    assert set(payload) == {
        "case_name",
        "evidence_type",
        "title",
        "source",
        "date_found",
        "agent_id",
        "agent_name",
        "identity",
        "portfolio",
        "authority",
        "competencies",
        "integrations",
        "performance",
        "trust_score",
        "notes",
    }
    assert set(payload["identity"]) == {"agent_type", "version", "owner", "status"}
    assert set(payload["portfolio"]) == {"domains", "products", "active_programs"}
    assert set(payload["authority"]) == {"role", "jurisdictions", "approval_level", "constraints"}
    assert set(payload["performance"]) == {
        "success_rate",
        "average_cycle_time_hours",
        "sla_compliance_rate",
        "period",
    }
    assert set(payload["trust_score"]) == {"overall", "components", "last_updated"}
    assert set(payload["trust_score"]["components"]) == {
        "identity_confidence",
        "authority_compliance",
        "competency_reliability",
        "integration_health",
        "performance_consistency",
    }
    assert len(payload["competencies"]) == 1
    assert set(payload["competencies"][0]) == {"name", "proficiency", "last_validated"}
    assert len(payload["integrations"]) == 1
    assert set(payload["integrations"][0]) == {"name", "type", "status"}
