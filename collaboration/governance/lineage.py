"""Trust, lineage, and evidence quality (§62-64, §140)."""

from __future__ import annotations

from dataclasses import dataclass, field


class LineageClass(str):
    USER_ASSERTED = "user_asserted"
    SYSTEM_OBSERVED = "system_observed"
    PRIMARY_SOURCE = "primary_source"
    SECONDARY_SOURCE = "secondary_source"
    EXTERNAL_UNVERIFIED = "external_unverified"
    AGENT_INFERRED = "agent_inferred"
    VERIFIED = "verified"
    CERTIFIED = "certified"
    DISPUTED = "disputed"
    SUPERSEDED = "superseded"


@dataclass
class LineageTag:
    artifact_id: str
    lineage_class: str
    source_refs: list[str] = field(default_factory=list)
    provenance: str = ""
    tenant_id: str = ""
    matter_id: str = ""

    def as_dict(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "lineage_class": self.lineage_class,
            "source_refs": list(self.source_refs),
            "provenance": self.provenance,
            "tenant_id": self.tenant_id,
            "matter_id": self.matter_id,
        }


class TaintTracker:
    """Authority taint: location does not upgrade provenance (§62)."""

    def __init__(self):
        self._tags: dict[str, LineageTag] = {}

    def tag(self, tag: LineageTag) -> None:
        self._tags[tag.artifact_id] = tag

    def get(self, artifact_id: str) -> LineageTag | None:
        return self._tags.get(artifact_id)

    def combine(self, *artifact_ids: str) -> str:
        """Provenance of a derived artifact = weakest lineage of inputs."""
        classes = []
        for aid in artifact_ids:
            tag = self._tags.get(aid)
            if tag is not None:
                classes.append(tag.lineage_class)
        if not classes:
            return LineageClass.AGENT_INFERRED
        order = [
            LineageClass.EXTERNAL_UNVERIFIED,
            LineageClass.DISPUTED,
            LineageClass.USER_ASSERTED,
            LineageClass.SECONDARY_SOURCE,
            LineageClass.AGENT_INFERRED,
            LineageClass.SYSTEM_OBSERVED,
            LineageClass.PRIMARY_SOURCE,
            LineageClass.VERIFIED,
            LineageClass.CERTIFIED,
        ]
        rank = {c: i for i, c in enumerate(order)}
        return min(classes, key=lambda c: rank.get(c, 99))

    def propagate(self, derived_id: str, *source_ids: str) -> LineageTag:
        """§62: EXTERNAL_UNVERIFIED stays EXTERNAL_UNVERIFIED downstream."""
        combined = self.combine(*source_ids)
        tag = LineageTag(artifact_id=derived_id, lineage_class=combined)
        self.tag(tag)
        return tag


class EvidenceScorer:
    """Evidence quality score (§64). Model confidence ≠ evidence quality."""

    def __init__(self):
        self._sources: dict[str, list[str]] = {}

    def register_sources(self, artifact_id: str, sources: list[str]) -> None:
        self._sources[artifact_id] = list(sources)

    def score(self, artifact_id: str) -> dict:
        sources = self._sources.get(artifact_id, [])
        unique_sources = set(sources)
        return {
            "artifact_id": artifact_id,
            "source_count": len(sources),
            "source_diversity": len(unique_sources),
            "has_primary_source": any("primary" in s.lower() for s in sources),
            "evidence_score": min(100, len(sources) * 20 + len(unique_sources) * 5),
        }
