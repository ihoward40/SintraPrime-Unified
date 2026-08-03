"""JSON-backed repository for Phase 1 legal authority data."""

from __future__ import annotations

import json
from functools import cached_property
from pathlib import Path
from typing import Any

from legal_authority.models import ConflictRecord, JurisdictionRule, LegalAuthority


class LegalAuthorityRepository:
    """Loads and validates jurisdiction authority/rule JSON files."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parents[1]
        self.data_root = self.root / "data" / "jurisdictions"

    @cached_property
    def coverage(self) -> dict[str, Any]:
        return self._read_json(self.data_root / "coverage.json")

    def list_jurisdictions(self) -> list[dict[str, Any]]:
        return list(self.coverage["jurisdictions"])

    def get_jurisdiction(self, code: str) -> dict[str, Any] | None:
        normalized = code.upper()
        for jurisdiction in self.list_jurisdictions():
            if jurisdiction["code"] == normalized:
                return jurisdiction
        return None

    def get_coverage(self, code: str) -> dict[str, Any] | None:
        return self.get_jurisdiction(code)

    @cached_property
    def authorities(self) -> dict[str, LegalAuthority]:
        records: dict[str, LegalAuthority] = {}
        for jurisdiction_dir in self._jurisdiction_dirs():
            path = jurisdiction_dir / "authorities.json"
            if not path.exists():
                continue
            for raw in self._read_json(path):
                authority = LegalAuthority.model_validate(raw)
                records[authority.id] = authority
        return records

    @cached_property
    def rules(self) -> dict[str, JurisdictionRule]:
        records: dict[str, JurisdictionRule] = {}
        for jurisdiction_dir in self._jurisdiction_dirs():
            path = jurisdiction_dir / "rules.json"
            if not path.exists():
                continue
            for raw in self._read_json(path):
                rule = JurisdictionRule.model_validate(raw)
                missing = [
                    authority_id
                    for authority_id in rule.authority_ids
                    if authority_id not in self.authorities
                ]
                if missing:
                    raise ValueError(f"orphan rule {rule.id}: missing authorities {missing}")
                records[rule.id] = rule
        return records

    @cached_property
    def conflicts(self) -> dict[str, ConflictRecord]:
        path = self.data_root / "new_jersey" / "conflicts.json"
        if not path.exists():
            return {}
        return {item["id"]: ConflictRecord.model_validate(item) for item in self._read_json(path)}

    def get_authority(self, authority_id: str) -> LegalAuthority | None:
        return self.authorities.get(authority_id)

    def get_rule(self, rule_id: str) -> JurisdictionRule | None:
        return self.rules.get(rule_id)

    def query_rules(
        self,
        jurisdiction: str | None = None,
        domain: str | None = None,
        topic: str | None = None,
        status: str | None = None,
        verification_state: str | None = None,
        requires_human_review: bool | None = None,
    ) -> list[JurisdictionRule]:
        selected = list(self.rules.values())
        if jurisdiction:
            selected = [rule for rule in selected if rule.jurisdiction == jurisdiction.upper()]
        if domain:
            selected = [rule for rule in selected if rule.domain == domain]
        if topic:
            selected = [rule for rule in selected if topic.lower() in rule.topic.lower()]
        if status:
            selected = [rule for rule in selected if rule.status == status]
        if requires_human_review is not None:
            selected = [
                rule for rule in selected if rule.requires_human_review == requires_human_review
            ]
        if verification_state:
            selected = [
                rule
                for rule in selected
                if any(
                    self.authorities[authority_id].verification_status == verification_state
                    for authority_id in rule.authority_ids
                )
            ]
        return sorted(
            selected, key=lambda rule: (rule.jurisdiction, rule.domain, rule.topic, rule.id)
        )

    def authorities_for_rule(self, rule: JurisdictionRule) -> list[LegalAuthority]:
        return [self.authorities[authority_id] for authority_id in rule.authority_ids]

    def _jurisdiction_dirs(self) -> list[Path]:
        return [path for path in self.data_root.iterdir() if path.is_dir()]

    @staticmethod
    def _read_json(path: Path) -> Any:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
