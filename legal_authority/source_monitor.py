"""Manual stale-source and statutory-drift monitoring helpers."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from legal_authority.models import AuditEvent, LegalAuthority, SourceRefreshResult
from legal_authority.repository import LegalAuthorityRepository


class SourceMonitor:
    """Compares supplied source metadata without fetching uncontrolled external content."""

    def __init__(self, repository: LegalAuthorityRepository | None = None) -> None:
        self.repository = repository or LegalAuthorityRepository()

    def refresh_authority_metadata(
        self,
        authority_id: str,
        actor_role: str,
        actor_identity: str | None,
        supplied_content: str | None = None,
        supplied_hash: str | None = None,
        source_available: bool = True,
        reason: str | None = None,
    ) -> SourceRefreshResult:
        authority = self.repository.get_authority(authority_id)
        if authority is None:
            raise KeyError(authority_id)
        current_hash = supplied_hash or self._hash_content(supplied_content)
        hash_changed = bool(
            authority.content_hash and current_hash and authority.content_hash != current_hash
        )
        source_available_state = "AVAILABLE" if source_available else "UNAVAILABLE"
        manual_state = authority.manual_review_status
        verification_status = authority.verification_status
        warnings: list[str] = []
        if authority.source_availability_status == "LOCATOR_ONLY":
            warnings.append(
                "Authority depends on a locator-only source and requires professional review."
            )
        if hash_changed:
            manual_state = "INVALIDATED_PENDING_REVIEW"
            verification_status = "HUMAN_REVIEW_REQUIRED"
            warnings.append("Authority content hash changed; dependent rules require review.")
        if not source_available:
            if not hash_changed:
                manual_state = "QUEUED"
            source_available_state = "UNAVAILABLE"
            warnings.append("Authority source was unavailable during manual refresh.")
        now = datetime.now(UTC)
        updated = authority.model_copy(
            update={
                "last_checked_at": now,
                "current_hash": current_hash,
                "change_detected": hash_changed,
                "source_availability_status": source_available_state,
                "manual_review_status": manual_state,
                "verification_status": verification_status,
                "broken_link_status": None if source_available else "BROKEN_LINK_OR_UNAVAILABLE",
                "updated_at": now,
            }
        )
        self.repository.replace_authority(updated)
        event = AuditEvent(
            id=f"audit-{uuid4()}",
            event_type="SOURCE_REFRESHED",
            object_type="LegalAuthority",
            object_id=authority_id,
            actor_role=actor_role,
            actor_identity=actor_identity,
            reason=reason,
            payload={
                "previous_hash": authority.content_hash,
                "current_hash": current_hash,
                "hash_changed": hash_changed,
                "source_available": source_available,
            },
            created_at=now,
        )
        self.repository.append_audit_event(authority.jurisdiction, event)
        return SourceRefreshResult(
            authority_id=authority_id,
            stale=self.is_overdue(updated, now),
            hash_changed=hash_changed,
            source_available=source_available,
            review_required=hash_changed
            or not source_available
            or updated.manual_review_status != "NOT_REQUIRED",
            previous_hash=authority.content_hash,
            current_hash=current_hash,
            warnings=warnings,
            audit_event=event,
        )

    @staticmethod
    def is_overdue(authority: LegalAuthority, now: datetime | None = None) -> bool:
        if authority.next_review_at is None:
            return False
        return authority.next_review_at <= (now or datetime.now(UTC))

    @staticmethod
    def _hash_content(content: str | None) -> str | None:
        if content is None:
            return None
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
