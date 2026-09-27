import json
from pathlib import Path

from agents.howard_template_agent import TEMPLATES


def test_agent_passport_template_registered():
    payload = TEMPLATES["agent_passport_template.json"]

    for key in ("case_name", "evidence_type", "title", "source"):
        assert key in payload
    for section in (
        "identity",
        "portfolio",
        "authority",
        "competencies",
        "integrations",
        "performance",
        "trust_score",
    ):
        assert section in payload


def test_agent_passport_template_file_sections():
    template_path = (
        Path(__file__).resolve().parent.parent
        / "intake_templates"
        / "agent_passport_template.json"
    )
    payload = json.loads(template_path.read_text(encoding="utf-8"))

    for key in ("case_name", "evidence_type", "title", "source"):
        assert key in payload
    for section in (
        "identity",
        "portfolio",
        "authority",
        "competencies",
        "integrations",
        "performance",
        "trust_score",
    ):
        assert section in payload
