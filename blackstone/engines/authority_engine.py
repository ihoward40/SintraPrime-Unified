"""
Authority Engine — determine controlling vs persuasive authority per jurisdiction.
"""
from __future__ import annotations

from datetime import datetime

from blackstone.models import (
    Claim,
    Jurisdiction,
    Source,
    SourceClassification,
)


class AuthorityEngine:
    """
    Identify controlling authority for a claim within a jurisdiction and detect conflicts.
    """

    def __init__(self, default_jurisdiction: Jurisdiction | None = None) -> None:
        self._sources: dict[str, Source] = {}
        self._jurisdictions: dict[str, Jurisdiction] = {}
        self.default_jurisdiction = default_jurisdiction

    def register_jurisdiction(self, jurisdiction: Jurisdiction) -> None:
        self._jurisdictions[jurisdiction.name] = jurisdiction

    def register_source(self, source: Source) -> None:
        self._sources[source.id] = source

    def controlling_authority(self, claim: Claim, target_date: datetime | None = None) -> Source | None:
        """
        Return the highest-ranked controlling source for a claim in its jurisdiction.
        """
        jurisdiction = claim.jurisdiction or self.default_jurisdiction
        if not jurisdiction:
            return None

        candidates = [
            e.source
            for e in claim.evidence
            if e.source.jurisdiction
            and e.source.jurisdiction.name == jurisdiction.name
            and e.source.classification == SourceClassification.PRIMARY_LEGAL
            and (target_date is None or self._is_effective_on(e.source, target_date))
        ]

        if not candidates:
            return None

        from datetime import UTC, datetime

        sentinel = datetime.min.replace(tzinfo=UTC)
        return max(
            candidates,
            key=lambda s: (self._specificity_score(s.jurisdiction) if s.jurisdiction else 0, s.effective_date or sentinel),
        )

    def find_conflicts(self, claim: Claim) -> list[dict[str, str]]:
        """
        Identify materially conflicting authorities across jurisdictions or levels.
        """
        conflicts: list[dict[str, str]] = []
        sources = [e.source for e in claim.evidence]
        primary_sources = [s for s in sources if s.classification == SourceClassification.PRIMARY_LEGAL]

        for i, a in enumerate(primary_sources):
            for b in primary_sources[i + 1 :]:
                if self._material_conflict(a, b):
                    conflicts.append(
                        {
                            "source_a": a.id,
                            "source_b": b.id,
                            "jurisdiction_a": a.jurisdiction.name if a.jurisdiction else "",
                            "jurisdiction_b": b.jurisdiction.name if b.jurisdiction else "",
                            "reason": "conflicting primary authority",
                        }
                    )

        return conflicts

    def authority_summary(self, claim: Claim, target_date: datetime | None = None) -> dict[str, object]:
        controlling = self.controlling_authority(claim, target_date)
        conflicts = self.find_conflicts(claim)
        persuasive = [
            e.source.id
            for e in claim.evidence
            if e.source.classification in (SourceClassification.SECONDARY_LEGAL, SourceClassification.SCHOLARLY)
        ]
        return {
            "claim_id": claim.id,
            "controlling_authority": controlling.to_dict() if controlling else None,
            "conflicts": conflicts,
            "persuasive_authorities": persuasive,
        }

    @staticmethod
    def _is_effective_on(source: Source, target_date: datetime) -> bool:
        if source.effective_date is None:
            return True
        return source.effective_date <= target_date

    @staticmethod
    def _specificity_score(jurisdiction: Jurisdiction) -> int:
        """
        Prefer more specific jurisdictions: municipal > county > state > federal.
        """
        precedence = {
            "municipal": 4,
            "county": 3,
            "state": 2,
            "federal": 1,
            "international": 0,
            "unknown": 0,
        }
        return precedence.get(jurisdiction.level, 0)

    @staticmethod
    def _material_conflict(a: Source, b: Source) -> bool:
        if a.jurisdiction is None or b.jurisdiction is None:
            return False
        # Same jurisdiction at same level is a direct conflict.
        return a.jurisdiction.name == b.jurisdiction.name and a.jurisdiction.level == b.jurisdiction.level
