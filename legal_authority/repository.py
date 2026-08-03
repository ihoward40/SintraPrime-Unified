"""JSON-backed repository for governed legal authority data."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from functools import cached_property
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from legal_authority.constants import JURISDICTION_SLUGS, REQUIRED_JURISDICTION_PACKAGE_FILES
from legal_authority.models import (
    AuditEvent,
    ConflictRecord,
    JurisdictionRule,
    LegalAuthority,
    LegalChallenge,
    ProfessionalReview,
)


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
        records: dict[str, ConflictRecord] = {}
        for jurisdiction_dir in self._jurisdiction_dirs():
            path = jurisdiction_dir / "conflicts.json"
            if not path.exists():
                continue
            for item in self._read_json(path):
                conflict = ConflictRecord.model_validate(item)
                records[conflict.id] = conflict
        return records

    @cached_property
    def reviews(self) -> dict[str, ProfessionalReview]:
        records: dict[str, ProfessionalReview] = {}
        for jurisdiction_dir in self._jurisdiction_dirs():
            path = jurisdiction_dir / "reviews.json"
            if not path.exists():
                continue
            for item in self._read_json(path):
                review = ProfessionalReview.model_validate(item)
                records[review.id] = review
        return records

    @cached_property
    def challenges(self) -> dict[str, LegalChallenge]:
        records: dict[str, LegalChallenge] = {}
        for jurisdiction_dir in self._jurisdiction_dirs():
            path = jurisdiction_dir / "challenges.json"
            if not path.exists():
                continue
            for item in self._read_json(path):
                challenge = LegalChallenge.model_validate(item)
                records[challenge.id] = challenge
        return records

    @cached_property
    def audit_events(self) -> dict[str, AuditEvent]:
        records: dict[str, AuditEvent] = {}
        for jurisdiction_dir in self._jurisdiction_dirs():
            path = jurisdiction_dir / "audit_events.json"
            if not path.exists():
                continue
            for item in self._read_json(path):
                event = AuditEvent.model_validate(item)
                records[event.id] = event
        return records

    def get_authority(self, authority_id: str) -> LegalAuthority | None:
        return self.authorities.get(authority_id)

    def get_rule(self, rule_id: str) -> JurisdictionRule | None:
        return self.rules.get(rule_id)

    def get_review(self, review_id: str) -> ProfessionalReview | None:
        return self.reviews.get(review_id)

    def get_challenge(self, challenge_id: str) -> LegalChallenge | None:
        return self.challenges.get(challenge_id)

    def reviews_for_rule(self, rule_id: str) -> list[ProfessionalReview]:
        return sorted(
            [review for review in self.reviews.values() if review.object_id == rule_id],
            key=lambda review: review.reviewed_at
            or review.expires_at
            or datetime.min.replace(tzinfo=UTC),
        )

    def challenges_for_rule(self, rule_id: str) -> list[LegalChallenge]:
        return sorted(
            [challenge for challenge in self.challenges.values() if challenge.object_id == rule_id],
            key=lambda challenge: challenge.created_at,
        )

    def conflicts_for_jurisdiction(self, jurisdiction: str) -> list[ConflictRecord]:
        return sorted(
            [
                conflict
                for conflict in self.conflicts.values()
                if conflict.jurisdiction == jurisdiction.upper()
            ],
            key=lambda conflict: conflict.id,
        )

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

    def stale_authorities(self, jurisdiction: str) -> list[LegalAuthority]:
        normalized = jurisdiction.upper()
        return sorted(
            [
                authority
                for authority in self.authorities.values()
                if authority.jurisdiction == normalized
                and (
                    authority.change_detected
                    or authority.source_availability_status
                    in {"LOCATOR_ONLY", "BROKEN_LINK", "UNAVAILABLE"}
                    or authority.manual_review_status in {"QUEUED", "INVALIDATED_PENDING_REVIEW"}
                )
            ],
            key=lambda authority: authority.id,
        )

    def authorities_for_rule(self, rule: JurisdictionRule) -> list[LegalAuthority]:
        return [self.authorities[authority_id] for authority_id in rule.authority_ids]

    def append_review(self, review: ProfessionalReview) -> None:
        self._append_jurisdiction_record(review.jurisdiction, "reviews.json", review)
        self._clear_cache("reviews")

    def append_challenge(self, challenge: LegalChallenge) -> None:
        self._append_jurisdiction_record(challenge.jurisdiction, "challenges.json", challenge)
        self._clear_cache("challenges")

    def append_audit_event(self, jurisdiction: str, event: AuditEvent) -> None:
        self._append_jurisdiction_record(jurisdiction, "audit_events.json", event)
        self._clear_cache("audit_events")

    def replace_authority(self, authority: LegalAuthority) -> None:
        path = self._jurisdiction_dir(authority.jurisdiction) / "authorities.json"
        records = self._read_json(path)
        replaced = False
        updated = authority.model_dump(mode="json")
        for index, record in enumerate(records):
            if record["id"] == authority.id:
                records[index] = updated
                replaced = True
                break
        if not replaced:
            raise KeyError(authority.id)
        self._write_json(path, records)
        self._clear_cache("authorities")

    def _append_jurisdiction_record(
        self, jurisdiction: str, filename: str, model: BaseModel
    ) -> None:
        path = self._jurisdiction_dir(jurisdiction) / filename
        records = self._read_json(path) if path.exists() else []
        records.append(model.model_dump(mode="json"))
        self._write_json(path, records)

    def validate_jurisdiction_packages(self) -> dict[str, Any]:
        """Validate governed jurisdiction package structure and relationships."""
        errors: list[str] = []
        seen_authorities: set[str] = set()
        seen_rules: set[str] = set()
        loaded_authorities = self.authorities
        loaded_rules = self.rules
        for jurisdiction in self.list_jurisdictions():
            code = jurisdiction["code"]
            slug = JURISDICTION_SLUGS.get(code)
            if not slug:
                continue
            package_dir = self.data_root / slug
            if not package_dir.exists():
                errors.append(f"{code}: missing package directory {slug}")
                continue
            missing_files = sorted(
                name
                for name in REQUIRED_JURISDICTION_PACKAGE_FILES
                if not (package_dir / name).exists()
            )
            if missing_files:
                errors.append(f"{code}: missing package files {missing_files}")

            for raw in self._read_json(package_dir / "authorities.json"):
                authority = LegalAuthority.model_validate(raw)
                if authority.jurisdiction not in {code, "FED"}:
                    errors.append(
                        f"{code}: authority {authority.id} has jurisdiction {authority.jurisdiction}"
                    )
                if authority.id in seen_authorities:
                    errors.append(f"duplicate authority id {authority.id}")
                seen_authorities.add(authority.id)

            for raw in self._read_json(package_dir / "rules.json"):
                rule = JurisdictionRule.model_validate(raw)
                if rule.jurisdiction != code:
                    errors.append(f"{code}: rule {rule.id} has jurisdiction {rule.jurisdiction}")
                if rule.id in seen_rules:
                    errors.append(f"duplicate rule id {rule.id}")
                seen_rules.add(rule.id)
                missing_refs = [aid for aid in rule.authority_ids if aid not in loaded_authorities]
                if missing_refs:
                    errors.append(f"{code}: rule {rule.id} missing authorities {missing_refs}")
                if rule.review_status == "APPROVED" and rule.requires_human_review:
                    errors.append(f"{code}: rule {rule.id} bypasses human-review gate")

            for filename, model_type in (
                ("conflicts.json", ConflictRecord),
                ("reviews.json", ProfessionalReview),
                ("challenges.json", LegalChallenge),
                ("audit_events.json", AuditEvent),
            ):
                path = package_dir / filename
                for raw in self._read_json(path):
                    record = model_type.model_validate(raw)
                    record_jurisdiction = getattr(record, "jurisdiction", code)
                    if record_jurisdiction != code:
                        errors.append(
                            f"{code}: {filename} record {getattr(record, 'id', 'unknown')} has jurisdiction {record_jurisdiction}"
                        )

        if errors:
            raise ValueError("jurisdiction package validation failed: " + "; ".join(errors))
        return {
            "validated_packages": sorted(JURISDICTION_SLUGS.values()),
            "authority_count": len(loaded_authorities),
            "rule_count": len(loaded_rules),
            "errors": [],
        }

    def _jurisdiction_dirs(self) -> list[Path]:
        return sorted([path for path in self.data_root.iterdir() if path.is_dir()])

    def _jurisdiction_dir(self, jurisdiction: str) -> Path:
        normalized_code = jurisdiction.upper()
        slug = JURISDICTION_SLUGS.get(normalized_code, normalized_code.lower())
        path = self.data_root / slug
        if not path.exists():
            raise KeyError(jurisdiction)
        return path

    def _clear_cache(self, name: str) -> None:
        self.__dict__.pop(name, None)

    @staticmethod
    def _read_json(path: Path) -> Any:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=False)
            handle.write("\n")
