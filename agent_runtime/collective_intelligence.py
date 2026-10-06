"""SP-COLLECTIVE-INTELLIGENCE-001 — governed organizational learning loop.

This module implements the authority-free core of:
learn -> challenge -> verify -> remember -> inherit -> demonstrate competency
-> propose value -> measure outcome -> learn again.

It intentionally performs no external side effects and grants no execution
authority. Knowledge may be distributed only after independent challenge and
verification. Competency is distinct from authorization.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from typing import Iterable


class LearningState(StrEnum):
    OBSERVED = "OBSERVED"
    CHALLENGED = "CHALLENGED"
    VERIFIED = "VERIFIED"
    DISTRIBUTABLE = "DISTRIBUTABLE"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"


class CompetencyState(StrEnum):
    UNTESTED = "UNTESTED"
    TESTED = "TESTED"
    CERTIFIED = "CERTIFIED"
    STALE = "STALE"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    evidence_id: str
    source_uri: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class Challenge:
    challenger_agent_id: str
    finding: str
    passed: bool
    evidence_refs: tuple[str, ...] = ()


@dataclass(slots=True)
class Lesson:
    lesson_id: str
    subject: str
    proposition: str
    source_agent_id: str
    evidence: tuple[EvidenceRef, ...]
    applicable_agents: tuple[str, ...]
    state: LearningState = LearningState.OBSERVED
    challenges: list[Challenge] = field(default_factory=list)
    verified_by: str | None = None
    verified_at: str | None = None
    supersedes: str | None = None

    @property
    def fingerprint(self) -> str:
        material = "|".join(
            [self.subject, self.proposition, *(e.content_hash for e in self.evidence)]
        )
        return sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class CompetencyReceipt:
    agent_id: str
    subject: str
    exam_id: str
    score: float
    threshold: float
    state: CompetencyState
    lesson_fingerprints: tuple[str, ...]
    tested_at: str


@dataclass(frozen=True, slots=True)
class ValueProposal:
    lesson_id: str
    proposal_type: str
    description: str
    expected_metric: str
    requires_principal_approval: bool = True


@dataclass(frozen=True, slots=True)
class Outcome:
    lesson_id: str
    proposal_type: str
    metric: str
    observed_value: float
    successful: bool
    evidence_refs: tuple[str, ...]
    recorded_at: str


class CollectiveIntelligenceError(RuntimeError):
    pass


class CollectiveIntelligence:
    """In-memory governed learning coordinator.

    Persistence adapters may store these typed records in existing governed
    memory/evidence systems. This class deliberately does not create a second
    memory engine.
    """

    def __init__(self) -> None:
        self._lessons: dict[str, Lesson] = {}
        self._competency: dict[tuple[str, str], CompetencyReceipt] = {}
        self._outcomes: list[Outcome] = []

    def observe(
        self,
        *,
        lesson_id: str,
        subject: str,
        proposition: str,
        source_agent_id: str,
        evidence: Iterable[EvidenceRef],
        applicable_agents: Iterable[str],
        supersedes: str | None = None,
    ) -> Lesson:
        if lesson_id in self._lessons:
            raise CollectiveIntelligenceError("duplicate lesson_id")
        evidence_tuple = tuple(evidence)
        if not evidence_tuple:
            raise CollectiveIntelligenceError("evidence required")
        lesson = Lesson(
            lesson_id=lesson_id,
            subject=subject,
            proposition=proposition,
            source_agent_id=source_agent_id,
            evidence=evidence_tuple,
            applicable_agents=tuple(sorted(set(applicable_agents))),
            supersedes=supersedes,
        )
        self._lessons[lesson_id] = lesson
        return lesson

    def challenge(
        self,
        lesson_id: str,
        *,
        challenger_agent_id: str,
        finding: str,
        passed: bool,
        evidence_refs: Iterable[str] = (),
    ) -> Lesson:
        lesson = self._require(lesson_id)
        if challenger_agent_id == lesson.source_agent_id:
            raise CollectiveIntelligenceError("independent challenger required")
        if lesson.state not in (LearningState.OBSERVED, LearningState.CHALLENGED):
            raise CollectiveIntelligenceError(f"cannot challenge from {lesson.state}")
        lesson.challenges.append(
            Challenge(challenger_agent_id, finding, passed, tuple(evidence_refs))
        )
        lesson.state = LearningState.CHALLENGED
        return lesson

    def verify(self, lesson_id: str, *, verifier_agent_id: str) -> Lesson:
        lesson = self._require(lesson_id)
        if verifier_agent_id == lesson.source_agent_id:
            raise CollectiveIntelligenceError("independent verifier required")
        if not lesson.challenges:
            raise CollectiveIntelligenceError("challenge required before verification")
        if verifier_agent_id in {c.challenger_agent_id for c in lesson.challenges}:
            raise CollectiveIntelligenceError("verifier must be independent of challengers")
        if not all(c.passed for c in lesson.challenges):
            lesson.state = LearningState.REJECTED
            raise CollectiveIntelligenceError("failed challenge blocks verification")
        lesson.state = LearningState.VERIFIED
        lesson.verified_by = verifier_agent_id
        lesson.verified_at = datetime.now(UTC).isoformat()
        return lesson

    def mark_distributable(self, lesson_id: str) -> Lesson:
        lesson = self._require(lesson_id)
        if lesson.state is not LearningState.VERIFIED:
            raise CollectiveIntelligenceError("only verified lessons may be distributed")
        lesson.state = LearningState.DISTRIBUTABLE
        return lesson

    def inherited_lessons(self, agent_id: str) -> tuple[Lesson, ...]:
        return tuple(
            lesson
            for lesson in self._lessons.values()
            if lesson.state is LearningState.DISTRIBUTABLE
            and agent_id in lesson.applicable_agents
        )

    def demonstrate_competency(
        self,
        *,
        agent_id: str,
        subject: str,
        exam_id: str,
        score: float,
        threshold: float,
        lesson_ids: Iterable[str],
    ) -> CompetencyReceipt:
        if not (0 <= score <= 100 and 0 <= threshold <= 100):
            raise CollectiveIntelligenceError("score and threshold must be 0..100")
        lessons = tuple(self._require(i) for i in lesson_ids)
        if not lessons or any(l.state is not LearningState.DISTRIBUTABLE for l in lessons):
            raise CollectiveIntelligenceError("competency requires distributable lessons")
        state = CompetencyState.CERTIFIED if score >= threshold else CompetencyState.FAILED
        receipt = CompetencyReceipt(
            agent_id=agent_id,
            subject=subject,
            exam_id=exam_id,
            score=score,
            threshold=threshold,
            state=state,
            lesson_fingerprints=tuple(l.fingerprint for l in lessons),
            tested_at=datetime.now(UTC).isoformat(),
        )
        self._competency[(agent_id, subject)] = receipt
        return receipt

    def competency(self, agent_id: str, subject: str) -> CompetencyReceipt | None:
        return self._competency.get((agent_id, subject))

    def propose_value(
        self,
        lesson_id: str,
        *,
        proposal_type: str,
        description: str,
        expected_metric: str,
    ) -> ValueProposal:
        lesson = self._require(lesson_id)
        if lesson.state is not LearningState.DISTRIBUTABLE:
            raise CollectiveIntelligenceError("unverified knowledge cannot drive value proposals")
        return ValueProposal(
            lesson_id=lesson_id,
            proposal_type=proposal_type,
            description=description,
            expected_metric=expected_metric,
            requires_principal_approval=True,
        )

    def record_outcome(
        self,
        *,
        lesson_id: str,
        proposal_type: str,
        metric: str,
        observed_value: float,
        successful: bool,
        evidence_refs: Iterable[str],
    ) -> Outcome:
        self._require(lesson_id)
        refs = tuple(evidence_refs)
        if not refs:
            raise CollectiveIntelligenceError("outcome evidence required")
        outcome = Outcome(
            lesson_id=lesson_id,
            proposal_type=proposal_type,
            metric=metric,
            observed_value=observed_value,
            successful=successful,
            evidence_refs=refs,
            recorded_at=datetime.now(UTC).isoformat(),
        )
        self._outcomes.append(outcome)
        return outcome

    def outcomes(self, lesson_id: str | None = None) -> tuple[Outcome, ...]:
        if lesson_id is None:
            return tuple(self._outcomes)
        return tuple(o for o in self._outcomes if o.lesson_id == lesson_id)

    def supersede(self, old_lesson_id: str, new_lesson_id: str) -> None:
        old = self._require(old_lesson_id)
        new = self._require(new_lesson_id)
        if new.state is not LearningState.DISTRIBUTABLE:
            raise CollectiveIntelligenceError("successor must be verified and distributable")
        old.state = LearningState.SUPERSEDED
        for key, receipt in tuple(self._competency.items()):
            if old.fingerprint in receipt.lesson_fingerprints:
                self._competency[key] = CompetencyReceipt(
                    agent_id=receipt.agent_id,
                    subject=receipt.subject,
                    exam_id=receipt.exam_id,
                    score=receipt.score,
                    threshold=receipt.threshold,
                    state=CompetencyState.STALE,
                    lesson_fingerprints=receipt.lesson_fingerprints,
                    tested_at=receipt.tested_at,
                )

    def _require(self, lesson_id: str) -> Lesson:
        try:
            return self._lessons[lesson_id]
        except KeyError as exc:
            raise CollectiveIntelligenceError(f"unknown lesson: {lesson_id}") from exc
