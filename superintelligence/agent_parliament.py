"""
agent_parliament.py — Democratic multi-agent debate and voting for SintraPrime.

For critical decisions, agents debate and vote democratically.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PARLIAMENT_LOG_PATH = Path("/agent/home/parliament_decisions.jsonl")


def _now_ts() -> float:
    return time.time()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ParliamentMember:
    member_id: str
    role: str
    expertise_domains: List[str]
    voting_weight: float        # 0.0 – 1.0
    track_record: Dict[str, int] = field(default_factory=lambda: {"correct": 0, "incorrect": 0})

    def __repr__(self) -> str:
        return f"ParliamentMember(role={self.role!r}, weight={self.voting_weight:.2f})"

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class DebateRound:
    round_num: int
    speaker: str          # role name
    statement: str
    counter_arguments: List[str] = field(default_factory=list)
    support_score: float = 0.5

    def __repr__(self) -> str:
        return f"DebateRound(round={self.round_num}, speaker={self.speaker!r})"

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ParliamentaryDecision:
    decision_id: str
    timestamp: float
    question: str
    winning_proposal: str
    vote_counts: Dict[str, float]
    consensus_achieved: bool
    rounds: List[Dict]
    vetoes: List[Dict]
    was_correct: Optional[bool] = None

    def to_dict(self) -> Dict:
        d = asdict(self)
        return d

    def __repr__(self) -> str:
        return (f"ParliamentaryDecision(id={self.decision_id[:8]}, "
                f"consensus={self.consensus_achieved}, "
                f"decision={self.winning_proposal[:50]!r})")


# ---------------------------------------------------------------------------
# Role-specific reasoning stances
# ---------------------------------------------------------------------------

MEMBER_STANCES = {
    "Critic": {
        "intro": "I must challenge this proposal.",
        "angle": "What are the risks, flaws, and weaknesses here?",
        "bias": "skeptical",
    },
    "Advocate": {
        "intro": "I support this direction.",
        "angle": "The benefits and opportunities are clear:",
        "bias": "supportive",
    },
    "Realist": {
        "intro": "Let me assess the practical feasibility.",
        "angle": "In practice, we must consider constraints and resources.",
        "bias": "pragmatic",
    },
    "Innovator": {
        "intro": "This is an opportunity to think differently.",
        "angle": "Novel approaches could be:",
        "bias": "creative",
    },
    "Ethicist": {
        "intro": "We must consider the ethical dimensions.",
        "angle": "The moral implications and fairness considerations are:",
        "bias": "ethical",
    },
    "Analyst": {
        "intro": "Let me examine the data and evidence.",
        "angle": "The analysis suggests:",
        "bias": "data-driven",
    },
}


def _generate_statement(role: str, question: str, round_num: int,
                         previous_statements: List[DebateRound]) -> str:
    """Generate a role-appropriate statement for a debate round."""
    stance = MEMBER_STANCES.get(role, {"intro": "My view:", "angle": "Considering all aspects:", "bias": "neutral"})
    prev_context = ""
    if previous_statements:
        prev_context = f" Building on {previous_statements[-1].speaker}'s point about '{previous_statements[-1].statement[:50]}'..."

    if round_num == 1:
        statement = (
            f"{stance['intro']}{prev_context} "
            f"Regarding '{question[:80]}': "
            f"{stance['angle']} "
            f"From a {stance['bias']} perspective, "
            f"the key consideration is how this aligns with our goals and constraints."
        )
    elif round_num == 2:
        statement = (
            f"[Round {round_num} - {role}] "
            f"Having heard initial positions, I maintain that '{question[:60]}' requires "
            f"us to prioritize {stance['bias']} analysis. "
            f"Specifically: {stance['angle']}"
        )
    else:
        statement = (
            f"[Final Round - {role}] "
            f"My conclusive stance on '{question[:60]}': "
            f"{stance['intro']} "
            f"The {stance['bias']} argument leads me to recommend "
            f"{'proceeding with caution' if stance['bias'] in ('skeptical', 'ethical') else 'moving forward'}."
        )
    return statement


def _generate_counter_arguments(speaker_role: str, other_roles: List[str],
                                  question: str) -> List[str]:
    """Generate counter-arguments from other roles' perspectives."""
    counters = []
    for other_role in other_roles[:2]:
        other_stance = MEMBER_STANCES.get(other_role, {})
        angle = other_stance.get("angle", "This perspective ignores")
        counters.append(
            f"{other_role} challenges: {angle} aspects that {speaker_role} hasn't addressed "
            f"in the context of '{question[:40]}'."
        )
    return counters


# ---------------------------------------------------------------------------
# AgentParliament
# ---------------------------------------------------------------------------

class AgentParliament:
    """Democratic multi-agent debate and voting system."""

    CONSENSUS_TOPICS = {"safety", "ethics", "critical_system", "irreversible"}

    def __init__(self, log_path: Path = PARLIAMENT_LOG_PATH):
        self.log_path = log_path
        self._members: Dict[str, ParliamentMember] = {}
        self._decisions: List[ParliamentaryDecision] = []
        self._vetoes: List[Dict] = []
        self._setup_members()
        self._load_decisions()

    def _setup_members(self):
        """Initialize the six parliament members."""
        configs = [
            ("critic",    "Critic",    ["risk", "security", "quality"],    0.85),
            ("advocate",  "Advocate",  ["opportunities", "benefits"],        0.75),
            ("realist",   "Realist",   ["resources", "feasibility"],         0.90),
            ("innovator", "Innovator", ["creativity", "design", "novel"],    0.70),
            ("ethicist",  "Ethicist",  ["ethics", "fairness", "safety"],     0.95),
            ("analyst",   "Analyst",   ["data", "metrics", "evidence"],      0.85),
        ]
        for mid, role, domains, weight in configs:
            self._members[mid] = ParliamentMember(
                member_id=mid,
                role=role,
                expertise_domains=domains,
                voting_weight=weight,
            )

    def _load_decisions(self):
        if self.log_path.exists():
            with open(self.log_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            d = json.loads(line)
                            decision = ParliamentaryDecision(**{
                                k: v for k, v in d.items()
                            })
                            self._decisions.append(decision)
                        except Exception:
                            pass

    def _log_decision(self, decision: ParliamentaryDecision):
        with open(self.log_path, "a") as f:
            f.write(json.dumps(decision.to_dict()) + "\n")

    def debate(self, question: str, rounds: int = 3) -> List[DebateRound]:
        """Structured debate between parliament members."""
        all_rounds: List[DebateRound] = []
        members = list(self._members.values())

        for round_num in range(1, rounds + 1):
            for member in members:
                other_roles = [m.role for m in members if m.role != member.role]
                statement = _generate_statement(
                    member.role, question, round_num, all_rounds
                )
                counters = _generate_counter_arguments(member.role, other_roles, question)
                # Compute support score based on round and role dynamics
                base_support = 0.5
                # Ethicist and Analyst tend to be more persuasive
                if member.role in ("Ethicist", "Analyst"):
                    base_support += 0.1
                if round_num > 1:
                    base_support += 0.05 * round_num  # positions harden

                dr = DebateRound(
                    round_num=round_num,
                    speaker=member.role,
                    statement=statement,
                    counter_arguments=counters,
                    support_score=min(base_support, 0.95),
                )
                all_rounds.append(dr)

        return all_rounds

    def vote(self, proposals: List[str]) -> Dict[str, float]:
        """Weighted voting on proposals."""
        if not proposals:
            return {}
        vote_counts: Dict[str, float] = {p: 0.0 for p in proposals}
        for member in self._members.values():
            # Each member votes for one proposal (simple heuristic: by index)
            # In a real system, each member would reason about the proposals
            preferred_idx = hash(member.role + str(proposals)) % len(proposals)
            vote_counts[proposals[preferred_idx]] += member.voting_weight
        # Normalize
        total = sum(vote_counts.values())
        if total > 0:
            vote_counts = {k: round(v / total, 4) for k, v in vote_counts.items()}
        return vote_counts

    def veto(self, member_id: str, proposal: str, reason: str) -> Dict[str, Any]:
        """Any member can veto with reason."""
        if member_id not in self._members:
            return {"success": False, "error": f"Unknown member: {member_id}"}
        member = self._members[member_id]
        veto_record = {
            "veto_id": str(uuid.uuid4()),
            "timestamp": _now_ts(),
            "member_id": member_id,
            "member_role": member.role,
            "proposal": proposal,
            "reason": reason,
        }
        self._vetoes.append(veto_record)
        return {"success": True, "veto": veto_record}

    def consensus_required(self, topic: str) -> bool:
        """Check if a topic requires full consensus."""
        topic_lower = topic.lower()
        return any(ct in topic_lower for ct in self.CONSENSUS_TOPICS)

    def record_decision(self, question: str, decision: str,
                         reasoning: str = "") -> ParliamentaryDecision:
        """Log a parliamentary decision."""
        proposals = [decision]
        vote_counts = self.vote(proposals)
        rounds = self.debate(question, rounds=2)
        consensus = self.consensus_required(question)

        pd = ParliamentaryDecision(
            decision_id=str(uuid.uuid4()),
            timestamp=_now_ts(),
            question=question,
            winning_proposal=decision,
            vote_counts=vote_counts,
            consensus_achieved=consensus,
            rounds=[r.to_dict() for r in rounds],
            vetoes=[v for v in self._vetoes if v.get("proposal") == decision],
        )
        self._decisions.append(pd)
        self._log_decision(pd)
        return pd

    def review_past_decisions(self) -> List[Dict[str, Any]]:
        """Periodically review if past decisions were right."""
        reviews = []
        for d in self._decisions[-20:]:  # Review last 20
            review = {
                "decision_id": d.decision_id,
                "question": d.question[:80],
                "decision": d.winning_proposal[:80],
                "was_correct": d.was_correct,
                "age_days": (_now_ts() - d.timestamp) / 86400,
                "vetoes": len(d.vetoes),
            }
            reviews.append(review)
        return reviews

    def mark_decision_correct(self, decision_id: str, correct: bool):
        """Update a decision's correctness based on outcome."""
        for d in self._decisions:
            if d.decision_id == decision_id:
                d.was_correct = correct
                # Update member track records
                for member in self._members.values():
                    if correct:
                        member.track_record["correct"] += 1
                    else:
                        member.track_record["incorrect"] += 1
                return d
        return None

    def members(self) -> List[ParliamentMember]:
        return list(self._members.values())

    def decisions(self) -> List[ParliamentaryDecision]:
        return list(self._decisions)

    def stats(self) -> Dict[str, Any]:
        correct = sum(1 for d in self._decisions if d.was_correct is True)
        incorrect = sum(1 for d in self._decisions if d.was_correct is False)
        return {
            "total_decisions": len(self._decisions),
            "correct": correct,
            "incorrect": incorrect,
            "unknown": len(self._decisions) - correct - incorrect,
            "accuracy": round(correct / max(correct + incorrect, 1), 3),
            "total_vetoes": len(self._vetoes),
            "members": {m.role: m.track_record for m in self._members.values()},
        }

    def __repr__(self) -> str:
        return (f"AgentParliament(members={len(self._members)}, "
                f"decisions={len(self._decisions)})")
