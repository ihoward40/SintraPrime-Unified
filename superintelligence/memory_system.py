"""
memory_system.py — Three-tier memory architecture for SintraPrime

Provides EpisodicMemory, SemanticMemory, ProceduralMemory,
MemoryConsolidator, and UnifiedMemory facade.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
EPISODIC_PATH = Path("/agent/home/episodic_memory.jsonl")
SEMANTIC_PATH = Path("/agent/home/semantic_memory.json")
PROCEDURAL_PATH = Path("/agent/home/procedural_memory.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_ts() -> float:
    return time.time()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def _tf_idf_similarity(query: str, doc: str) -> float:
    """Simple TF-IDF cosine similarity between two strings."""
    q_tokens = _tokenize(query)
    d_tokens = _tokenize(doc)
    if not q_tokens or not d_tokens:
        return 0.0
    vocab = set(q_tokens) | set(d_tokens)
    q_freq: Dict[str, int] = defaultdict(int)
    d_freq: Dict[str, int] = defaultdict(int)
    for t in q_tokens:
        q_freq[t] += 1
    for t in d_tokens:
        d_freq[t] += 1
    dot = sum(q_freq[t] * d_freq[t] for t in vocab)
    mag_q = math.sqrt(sum(v * v for v in q_freq.values()))
    mag_d = math.sqrt(sum(v * v for v in d_freq.values()))
    if mag_q == 0 or mag_d == 0:
        return 0.0
    return dot / (mag_q * mag_d)


# ---------------------------------------------------------------------------
# EpisodicMemory
# ---------------------------------------------------------------------------

@dataclass
class Episode:
    episode_id: str
    timestamp: float
    event_type: str
    content: str
    context: str
    outcome: str
    importance_score: float
    tags: List[str]
    compressed: bool = False

    def __repr__(self) -> str:
        return (f"Episode(id={self.episode_id[:8]}, type={self.event_type}, "
                f"importance={self.importance_score:.2f})")

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "Episode":
        return cls(**d)

    def age_days(self) -> float:
        return (_now_ts() - self.timestamp) / 86400.0


class EpisodicMemory:
    """Stores agent experiences as timestamped episodes with persistence."""

    CONSOLIDATION_INTERVAL = 100  # episodes between consolidations

    def __init__(self, path: Path = EPISODIC_PATH):
        self.path = path
        self._episodes: List[Episode] = []
        self._episode_count_since_last_consolidation = 0
        self._load()

    def _load(self):
        if self.path.exists():
            with open(self.path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            ep = Episode.from_dict(json.loads(line))
                            self._episodes.append(ep)
                        except Exception:
                            pass

    def _append_to_file(self, ep: Episode):
        with open(self.path, "a") as f:
            f.write(json.dumps(ep.to_dict()) + "\n")

    def _compute_importance(self, event_type: str, content: str, outcome: str) -> float:
        """Heuristic importance scoring."""
        score = 0.5
        positive_outcomes = ["success", "completed", "solved", "learned", "improved"]
        negative_outcomes = ["failure", "error", "failed", "incorrect", "mistake"]
        outcome_lower = outcome.lower()
        if any(w in outcome_lower for w in positive_outcomes):
            score += 0.2
        if any(w in outcome_lower for w in negative_outcomes):
            score += 0.15  # failures are important to remember
        if event_type in ("critical", "error", "milestone", "discovery"):
            score += 0.2
        # length as a proxy for richness
        score += min(len(content) / 2000.0, 0.1)
        return min(score, 1.0)

    def record(self, event_type: str, content: str, context: str = "",
               outcome: str = "") -> Episode:
        """Store a new episode."""
        importance = self._compute_importance(event_type, content, outcome)
        # Extract simple tags from content
        words = _tokenize(content)
        tags = list(set(w for w in words if len(w) > 5))[:10]
        ep = Episode(
            episode_id=str(uuid.uuid4()),
            timestamp=_now_ts(),
            event_type=event_type,
            content=content,
            context=context,
            outcome=outcome,
            importance_score=importance,
            tags=tags,
        )
        self._episodes.append(ep)
        self._append_to_file(ep)
        self._episode_count_since_last_consolidation += 1
        return ep

    def recall(self, query: str, n: int = 10) -> List[Tuple[float, Episode]]:
        """Semantic search over episodes using TF-IDF similarity."""
        scored = []
        for ep in self._episodes:
            if ep.compressed:
                continue
            text = f"{ep.event_type} {ep.content} {ep.context} {ep.outcome}"
            sim = _tf_idf_similarity(query, text)
            scored.append((sim, ep))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:n]

    def recent(self, n: int = 20) -> List[Episode]:
        """Get most recent N episodes."""
        return sorted(self._episodes, key=lambda e: e.timestamp, reverse=True)[:n]

    def important(self, threshold: float = 0.8) -> List[Episode]:
        """Get high-importance episodes."""
        return [e for e in self._episodes if e.importance_score >= threshold]

    def compress_old(self, days: int = 30) -> int:
        """Summarize episodes older than N days into compressed memories."""
        cutoff = _now_ts() - days * 86400.0
        old_eps = [e for e in self._episodes if e.timestamp < cutoff and not e.compressed]
        if not old_eps:
            return 0
        # Group by event_type and create a summary episode
        groups: Dict[str, List[Episode]] = defaultdict(list)
        for ep in old_eps:
            groups[ep.event_type].append(ep)
        compressed_count = 0
        for etype, eps in groups.items():
            summary = f"Compressed {len(eps)} episodes of type '{etype}'. "
            summary += "Common outcomes: " + "; ".join(
                set(e.outcome[:50] for e in eps[:5] if e.outcome)
            )
            avg_importance = sum(e.importance_score for e in eps) / len(eps)
            comp_ep = Episode(
                episode_id=str(uuid.uuid4()),
                timestamp=_now_ts(),
                event_type="compressed_" + etype,
                content=summary,
                context=f"Compressed from {len(eps)} old episodes",
                outcome="compression",
                importance_score=avg_importance,
                tags=["compressed", etype],
                compressed=True,
            )
            self._episodes.append(comp_ep)
            self._append_to_file(comp_ep)
            # Mark originals as compressed
            for ep in eps:
                ep.compressed = True
            compressed_count += len(eps)
        # Rewrite file to reflect compression
        self._rewrite_file()
        return compressed_count

    def _rewrite_file(self):
        with open(self.path, "w") as f:
            for ep in self._episodes:
                f.write(json.dumps(ep.to_dict()) + "\n")

    def all_episodes(self) -> List[Episode]:
        return list(self._episodes)

    def count(self) -> int:
        return len(self._episodes)

    def __repr__(self) -> str:
        return f"EpisodicMemory(episodes={len(self._episodes)}, path={self.path})"


# ---------------------------------------------------------------------------
# SemanticMemory
# ---------------------------------------------------------------------------

@dataclass
class Fact:
    key: str
    value: Any
    confidence: float
    source: str
    timestamp: float
    access_count: int = 0

    def __repr__(self) -> str:
        return f"Fact(key={self.key!r}, confidence={self.confidence:.2f})"

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "Fact":
        return cls(**d)


class SemanticMemory:
    """Stores facts, knowledge, and learned patterns as key-value pairs."""

    def __init__(self, path: Path = SEMANTIC_PATH):
        self.path = path
        self._facts: Dict[str, Fact] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path, "r") as f:
                    data = json.load(f)
                for k, v in data.items():
                    self._facts[k] = Fact.from_dict(v)
            except Exception:
                self._facts = {}

    def _save(self):
        data = {k: f.to_dict() for k, f in self._facts.items()}
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)

    def learn(self, key: str, value: Any, confidence: float = 0.7,
              source: str = "agent") -> Fact:
        """Store a fact with confidence score."""
        confidence = max(0.0, min(1.0, confidence))
        if key in self._facts:
            existing = self._facts[key]
            # Blend confidence
            existing.confidence = (existing.confidence + confidence) / 2
            existing.value = value
            existing.timestamp = _now_ts()
            fact = existing
        else:
            fact = Fact(
                key=key,
                value=value,
                confidence=confidence,
                source=source,
                timestamp=_now_ts(),
            )
            self._facts[key] = fact
        self._save()
        return fact

    def recall(self, query: str) -> List[Tuple[float, Fact]]:
        """Fuzzy lookup by key or semantic similarity."""
        scored = []
        for key, fact in self._facts.items():
            key_sim = _tf_idf_similarity(query, key)
            val_str = str(fact.value) if not isinstance(fact.value, str) else fact.value
            val_sim = _tf_idf_similarity(query, val_str)
            sim = max(key_sim, val_sim)
            # Weight by confidence
            sim *= fact.confidence
            if sim > 0:
                scored.append((sim, fact))
        scored.sort(key=lambda x: x[0], reverse=True)
        # Track access
        for _, fact in scored[:5]:
            fact.access_count += 1
        if scored:
            self._save()
        return scored

    def update(self, key: str, new_value: Any, confidence: float = 0.7) -> Optional[Fact]:
        """Update existing knowledge."""
        if key not in self._facts:
            return None
        fact = self._facts[key]
        fact.value = new_value
        fact.confidence = max(0.0, min(1.0, confidence))
        fact.timestamp = _now_ts()
        self._save()
        return fact

    def forget(self, key: str) -> bool:
        """Remove a fact."""
        if key in self._facts:
            del self._facts[key]
            self._save()
            return True
        return False

    def related(self, key: str, n: int = 5) -> List[Tuple[float, Fact]]:
        """Find semantically related facts."""
        if key not in self._facts:
            return []
        source_fact = self._facts[key]
        query = f"{key} {source_fact.value}"
        results = self.recall(query)
        # Exclude the queried fact itself
        return [(s, f) for s, f in results if f.key != key][:n]

    def count(self) -> int:
        return len(self._facts)

    def all_facts(self) -> Dict[str, Fact]:
        return dict(self._facts)

    def __repr__(self) -> str:
        return f"SemanticMemory(facts={len(self._facts)}, path={self.path})"


# ---------------------------------------------------------------------------
# ProceduralMemory
# ---------------------------------------------------------------------------

@dataclass
class Procedure:
    name: str
    steps: List[str]
    success_rate: float
    context: str
    timestamp: float
    use_count: int = 0
    tags: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (f"Procedure(name={self.name!r}, steps={len(self.steps)}, "
                f"success_rate={self.success_rate:.2f})")

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "Procedure":
        return cls(**d)


class ProceduralMemory:
    """Stores successful procedures/workflows as reusable patterns."""

    def __init__(self, path: Path = PROCEDURAL_PATH):
        self.path = path
        self._procedures: Dict[str, Procedure] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path, "r") as f:
                    data = json.load(f)
                for name, v in data.items():
                    self._procedures[name] = Procedure.from_dict(v)
            except Exception:
                self._procedures = {}

    def _save(self):
        data = {name: p.to_dict() for name, p in self._procedures.items()}
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)

    def record_procedure(self, name: str, steps: List[str],
                          success_rate: float = 0.8,
                          context: str = "") -> Procedure:
        """Store a workflow."""
        tags = list(set(_tokenize(name + " " + context)))[:8]
        proc = Procedure(
            name=name,
            steps=steps,
            success_rate=max(0.0, min(1.0, success_rate)),
            context=context,
            timestamp=_now_ts(),
            tags=tags,
        )
        self._procedures[name] = proc
        self._save()
        return proc

    def find_procedure(self, goal_description: str) -> Optional[Tuple[float, Procedure]]:
        """Find best matching procedure for a goal."""
        best: Optional[Tuple[float, Procedure]] = None
        for name, proc in self._procedures.items():
            text = f"{name} {proc.context} {' '.join(proc.steps)}"
            sim = _tf_idf_similarity(goal_description, text)
            # Weight by success rate
            score = sim * proc.success_rate
            if best is None or score > best[0]:
                best = (score, proc)
        return best

    def update_success_rate(self, name: str, success: bool) -> Optional[Procedure]:
        """Update procedure reliability using running average."""
        if name not in self._procedures:
            return None
        proc = self._procedures[name]
        proc.use_count += 1
        # Exponential moving average
        alpha = 0.1
        proc.success_rate = (1 - alpha) * proc.success_rate + alpha * (1.0 if success else 0.0)
        self._save()
        return proc

    def combine_procedures(self, name1: str, name2: str,
                            new_name: Optional[str] = None) -> Optional[Procedure]:
        """Create a new procedure from two successful ones."""
        if name1 not in self._procedures or name2 not in self._procedures:
            return None
        p1 = self._procedures[name1]
        p2 = self._procedures[name2]
        combined_steps = p1.steps + ["--- transition ---"] + p2.steps
        combined_name = new_name or f"{name1}+{name2}"
        combined_rate = (p1.success_rate + p2.success_rate) / 2 * 0.9  # slight discount
        context = f"Combined from '{name1}' and '{name2}'"
        return self.record_procedure(combined_name, combined_steps, combined_rate, context)

    def all_procedures(self) -> Dict[str, Procedure]:
        return dict(self._procedures)

    def count(self) -> int:
        return len(self._procedures)

    def __repr__(self) -> str:
        return f"ProceduralMemory(procedures={len(self._procedures)}, path={self.path})"


# ---------------------------------------------------------------------------
# MemoryConsolidator
# ---------------------------------------------------------------------------

class MemoryConsolidator:
    """Runs consolidation cycle — moves important episodic memories to semantic."""

    CONSOLIDATION_EPISODE_THRESHOLD = 100

    def __init__(self, episodic: EpisodicMemory, semantic: SemanticMemory,
                 procedural: ProceduralMemory):
        self.episodic = episodic
        self.semantic = semantic
        self.procedural = procedural
        self._consolidation_count = 0

    def consolidate(self) -> Dict[str, int]:
        """Move important episodic memories to semantic memory."""
        important_eps = self.episodic.important(threshold=0.75)
        consolidated = 0
        for ep in important_eps:
            key = f"episode:{ep.episode_id[:8]}:{ep.event_type}"
            # Only consolidate if not already in semantic memory
            if not any(f.key == key for f in self.semantic.all_facts().values()):
                self.semantic.learn(
                    key=key,
                    value={
                        "content": ep.content,
                        "outcome": ep.outcome,
                        "event_type": ep.event_type,
                        "tags": ep.tags,
                    },
                    confidence=ep.importance_score,
                    source="episodic_consolidation",
                )
                consolidated += 1
        self._consolidation_count += 1
        return {"consolidated": consolidated, "cycle": self._consolidation_count}

    def prune(self, min_importance: float = 0.2, max_age_days: int = 90) -> Dict[str, int]:
        """Remove low-importance, old memories."""
        cutoff = _now_ts() - max_age_days * 86400.0
        before = self.episodic.count()
        self.episodic._episodes = [
            ep for ep in self.episodic._episodes
            if ep.importance_score >= min_importance or ep.timestamp >= cutoff
        ]
        self.episodic._rewrite_file()
        # Prune low-confidence semantic facts
        low_conf_keys = [
            k for k, f in self.semantic.all_facts().items()
            if f.confidence < 0.15
        ]
        for k in low_conf_keys:
            self.semantic.forget(k)
        pruned_ep = before - self.episodic.count()
        return {"pruned_episodes": pruned_ep, "pruned_facts": len(low_conf_keys)}

    def stats(self) -> Dict[str, Any]:
        """Return memory usage statistics."""
        eps = self.episodic.all_episodes()
        facts = self.semantic.all_facts()
        procs = self.procedural.all_procedures()
        avg_importance = sum(e.importance_score for e in eps) / max(len(eps), 1)
        avg_confidence = sum(f.confidence for f in facts.values()) / max(len(facts), 1)
        return {
            "episodic": {
                "total": len(eps),
                "compressed": sum(1 for e in eps if e.compressed),
                "avg_importance": round(avg_importance, 3),
                "high_importance": sum(1 for e in eps if e.importance_score >= 0.8),
            },
            "semantic": {
                "total": len(facts),
                "avg_confidence": round(avg_confidence, 3),
                "high_confidence": sum(1 for f in facts.values() if f.confidence >= 0.8),
            },
            "procedural": {
                "total": len(procs),
                "avg_success_rate": round(
                    sum(p.success_rate for p in procs.values()) / max(len(procs), 1), 3
                ),
            },
            "consolidation_cycles": self._consolidation_count,
        }

    def __repr__(self) -> str:
        return f"MemoryConsolidator(cycles={self._consolidation_count})"


# ---------------------------------------------------------------------------
# UnifiedMemory (facade)
# ---------------------------------------------------------------------------

class UnifiedMemory:
    """Single interface to all three memory types."""

    def __init__(self,
                 episodic_path: Path = EPISODIC_PATH,
                 semantic_path: Path = SEMANTIC_PATH,
                 procedural_path: Path = PROCEDURAL_PATH):
        self.episodic = EpisodicMemory(episodic_path)
        self.semantic = SemanticMemory(semantic_path)
        self.procedural = ProceduralMemory(procedural_path)
        self.consolidator = MemoryConsolidator(self.episodic, self.semantic, self.procedural)

    def _classify_memory_type(self, content: str, memory_type: str) -> str:
        """Auto-classify content into a memory type."""
        if memory_type != "auto":
            return memory_type
        content_lower = content.lower()
        if any(w in content_lower for w in ["step", "procedure", "workflow", "process", "how to"]):
            return "procedural"
        if any(w in content_lower for w in ["fact", "is", "are", "was", "definition", "means"]):
            return "semantic"
        return "episodic"

    def remember(self, content: str, memory_type: str = "auto",
                 **kwargs) -> Any:
        """Auto-classify and store a memory."""
        mtype = self._classify_memory_type(content, memory_type)
        if mtype == "episodic":
            return self.episodic.record(
                event_type=kwargs.get("event_type", "observation"),
                content=content,
                context=kwargs.get("context", ""),
                outcome=kwargs.get("outcome", ""),
            )
        elif mtype == "semantic":
            return self.semantic.learn(
                key=kwargs.get("key", content[:50]),
                value=content,
                confidence=kwargs.get("confidence", 0.7),
                source=kwargs.get("source", "agent"),
            )
        elif mtype == "procedural":
            return self.procedural.record_procedure(
                name=kwargs.get("name", content[:30]),
                steps=kwargs.get("steps", [content]),
                success_rate=kwargs.get("success_rate", 0.7),
                context=content,
            )
        return None

    def recall_all(self, query: str, n_each: int = 5) -> List[Dict[str, Any]]:
        """Search across all memory types, return ranked results."""
        results = []
        # Episodic
        for score, ep in self.episodic.recall(query, n=n_each):
            results.append({
                "type": "episodic",
                "score": score,
                "id": ep.episode_id,
                "content": ep.content,
                "outcome": ep.outcome,
                "importance": ep.importance_score,
                "timestamp": ep.timestamp,
            })
        # Semantic
        for score, fact in self.semantic.recall(query)[:n_each]:
            results.append({
                "type": "semantic",
                "score": score,
                "key": fact.key,
                "value": fact.value,
                "confidence": fact.confidence,
                "timestamp": fact.timestamp,
            })
        # Procedural
        match = self.procedural.find_procedure(query)
        if match:
            proc_score, proc = match
            results.append({
                "type": "procedural",
                "score": proc_score,
                "name": proc.name,
                "steps": proc.steps,
                "success_rate": proc.success_rate,
            })
        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def export_memories(self) -> Dict[str, Any]:
        """Export all memories as structured JSON."""
        return {
            "exported_at": _now_iso(),
            "episodic": [ep.to_dict() for ep in self.episodic.all_episodes()],
            "semantic": {k: f.to_dict() for k, f in self.semantic.all_facts().items()},
            "procedural": {n: p.to_dict() for n, p in self.procedural.all_procedures().items()},
        }

    def import_memories(self, data: Dict[str, Any]) -> Dict[str, int]:
        """Import memories from another agent (sharing!)."""
        imported = {"episodic": 0, "semantic": 0, "procedural": 0}
        for ep_dict in data.get("episodic", []):
            try:
                ep = Episode.from_dict(ep_dict)
                # Avoid duplicates
                existing_ids = {e.episode_id for e in self.episodic.all_episodes()}
                if ep.episode_id not in existing_ids:
                    self.episodic._episodes.append(ep)
                    self.episodic._append_to_file(ep)
                    imported["episodic"] += 1
            except Exception:
                pass
        for key, fact_dict in data.get("semantic", {}).items():
            try:
                fact = Fact.from_dict(fact_dict)
                self.semantic.learn(fact.key, fact.value, fact.confidence, fact.source)
                imported["semantic"] += 1
            except Exception:
                pass
        for name, proc_dict in data.get("procedural", {}).items():
            try:
                proc = Procedure.from_dict(proc_dict)
                self.procedural.record_procedure(
                    proc.name, proc.steps, proc.success_rate, proc.context
                )
                imported["procedural"] += 1
            except Exception:
                pass
        return imported

    def consolidate(self) -> Dict[str, Any]:
        """Run consolidation cycle."""
        cons = self.consolidator.consolidate()
        prune = self.consolidator.prune()
        return {"consolidation": cons, "pruning": prune}

    def stats(self) -> Dict[str, Any]:
        return self.consolidator.stats()

    def __repr__(self) -> str:
        return (f"UnifiedMemory(episodic={self.episodic.count()}, "
                f"semantic={self.semantic.count()}, "
                f"procedural={self.procedural.count()})")
