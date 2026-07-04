"""
Generic CaseTemplate class for litigation-grade evidence management.
Version 2.1.0 - RC1 with Decision Ledger, Contradiction Detection, Sufficiency Rules

Architecture (7 layers):
  Evidence Registry -> Fact Ledger -> Legal Analysis Ledger -> Authority Ledger
  -> Decision Ledger -> Evidence Request Register -> Packet Generator

Key design principle: Legal conclusions never directly reference evidence.
They reference facts. Facts reference evidence. That chain is auditable.

v2.1.0 additions:
- Decision Ledger (auditable strategic decisions with alternatives)
- Contradiction Detection (automatic conflict flagging between facts)
- Evidence Sufficiency Rules (deterministic requirements, not subjective percentages)
- Kernel versioning (template_version embedded in every case)

Usage:
    from case_template import CaseTemplate
    case = CaseTemplate("CASE-666234B709", "Halsted / LVNV / Milestone")
    case.enable_module("debt_collection")
    case.register_evidence(...)
    case.add_fact(...)
    case.add_legal_analysis(...)
    case.add_authority(...)
    case.add_decision(...)
    case.add_sufficiency_rule(...)
    case.detect_contradictions()
    case.generate_packet()
    case.render("demand_letter")
"""

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ── Constants ────────────────────────────────────────────────────────

EVIDENCE_BASE = Path(r"C:\Users\admin\Desktop\SintraPrime-Unified\evidence")

FOLDER_STRUCTURE = [
    "01_Intake", "02_Credit_Reports", "03_Original_Creditor",
    "04_Collection_Agency", "05_Correspondence", "06_Evidence",
    "07_Legal_Research", "08_Drafts", "09_Submitted",
    "10_Responses", "11_Deadlines", "Audit",
]

RELATIONSHIP_TYPES = {
    "authenticates", "contradicts", "supplements",
    "duplicates", "supersedes", "references",
}

AUTHORITY_TYPES = {
    "constitution", "federal_statute", "state_statute", "regulation",
    "case_law", "administrative_guidance", "contract", "court_order",
}

AUTHORITY_STRENGTH = {"primary", "secondary", "persuasive", "binding"}

KERNEL_VERSION = "2.1.0"

MODULES = {
    "debt_collection": "FDCPA, FCRA, state debt collection laws",
    "credit_reporting": "FCRA, dispute letters, bureau communications",
    "auto_finance": "UCC, auto loan disputes, repossession defense",
    "identity_theft": "FCRA identity theft provisions, FTC rules",
    "tax": "IRS procedures, tax court, collection due process",
    "banking": "banking regulations, EWS/ChexSystems, account disputes",
}


# ── Utility ──────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with filepath.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sanitize_filename(title: str) -> str:
    replacements = {
        " ": "_", "/": "-", "\\": "-", ":": "-",
        "\u2014": "-", "\u2013": "-", "|": "-",
        "?": "", "*": "", "<": "", ">": "", '"': "",
    }
    for old, new in replacements.items():
        title = title.replace(old, new)
    return title


def confidence_label(score: float) -> str:
    if score >= 0.8:
        return "high"
    elif score >= 0.5:
        return "moderate"
    else:
        return "low"


# ── CaseTemplate v2.0 ────────────────────────────────────────────────

class CaseTemplate:
    """Reusable litigation-grade evidence management framework."""

    def __init__(
        self,
        case_id: str,
        case_name: str,
        evidence_counter_start: int = 420,
        description: str = "",
        priority: str = "high",
        external_action: str = "locked",
    ):
        self.case_id = case_id
        self.case_name = case_name
        self.description = description
        self.priority = priority
        self.external_action = external_action
        self.case_dir = EVIDENCE_BASE / case_id
        self._ev_counter = evidence_counter_start
        self._packet_version = 0
        self._enabled_modules: List[str] = []
        self._registry_cache: Optional[Dict[str, Any]] = None

        # Paths
        self.registry_path = self.case_dir / "evidence_registry.json"
        self.chronology_path = self.case_dir / "chronology.json"
        self.fact_ledger_path = self.case_dir / "fact_ledger.json"
        self.legal_ledger_path = self.case_dir / "legal_analysis_ledger.json"
        self.authority_ledger_path = self.case_dir / "authority_ledger.json"
        self.request_register_path = self.case_dir / "evidence_request_register.json"
        self.dependency_graph_path = self.case_dir / "dependency_graph.json"
        self.relationships_path = self.case_dir / "evidence_relationships.json"
        self.decision_ledger_path = self.case_dir / "decision_ledger.json"
        self.contradictions_path = self.case_dir / "contradictions.json"
        self.sufficiency_path = self.case_dir / "sufficiency_rules.json"
        self.event_ledger_path = self.case_dir / "event_ledger.json"
        self.readiness_path = self.case_dir / "readiness_score.json"
        self.modules_path = self.case_dir / "modules.json"

        self._init_folders()
        self._init_registries()

    def _init_folders(self):
        for folder in FOLDER_STRUCTURE:
            (self.case_dir / folder).mkdir(parents=True, exist_ok=True)

    def _init_registries(self):
        defaults = {
            self.registry_path: {"case_id": self.case_id, "case_name": self.case_name, "evidence_items": [], "next_evidence_number": self._ev_counter, "registry_revision": 0},
            self.chronology_path: {"case_id": self.case_id, "case_name": self.case_name, "events": []},
            self.fact_ledger_path: {"case_id": self.case_id, "facts": [], "ledger_revision": 0},
            self.legal_ledger_path: {"case_id": self.case_id, "analyses": [], "ledger_revision": 0},
            self.authority_ledger_path: {"case_id": self.case_id, "authorities": [], "ledger_revision": 0},
            self.request_register_path: {"case_id": self.case_id, "requests": []},
            self.dependency_graph_path: {"case_id": self.case_id, "dependencies": []},
            self.relationships_path: {"case_id": self.case_id, "relationships": []},
            self.decision_ledger_path: {"case_id": self.case_id, "decisions": [], "ledger_revision": 0},
            self.contradictions_path: {"case_id": self.case_id, "contradictions": []},
            self.sufficiency_path: {"case_id": self.case_id, "rules": []},
            self.event_ledger_path: {"case_id": self.case_id, "events": []},
            self.modules_path: {"case_id": self.case_id, "enabled_modules": [], "template_version": KERNEL_VERSION},
        }
        for path, default in defaults.items():
            if not path.exists():
                self._save_json(path, default)

    def _load_json(self, path: Path) -> Dict[str, Any]:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_json(self, path: Path, data: Dict[str, Any]):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _bump_revision(self, path: Path, key: str = "registry_revision"):
        data = self._load_json(path)
        data[key] = data.get(key, 0) + 1
        self._save_json(path, data)

    # ── Module System ────────────────────────────────────────────────

    def enable_module(self, module_name: str):
        assert module_name in MODULES, f"Unknown module: {module_name}. Available: {list(MODULES.keys())}"
        if module_name not in self._enabled_modules:
            self._enabled_modules.append(module_name)
            mods = self._load_json(self.modules_path)
            if module_name not in mods["enabled_modules"]:
                mods["enabled_modules"].append(module_name)
            self._save_json(self.modules_path, mods)

    # ── Evidence Registration ────────────────────────────────────────

    def register_evidence(
        self,
        source_file: Optional[Path] = None,
        text_content: Optional[str] = None,
        evidence_type: str = "document",
        title: str = "",
        description: str = "",
        source: str = "",
        custodian: str = "Isiah Howard",
        folder: str = "06_Evidence",
        date_of_event: str = "",
        notes: str = "",
        acquisition_method: str = "",
        acquisition_date: str = "",
        obtained_from: str = "",
        authenticity_status: str = "unverified",
        verification_status: str = "unverified",
        related_evidence: Optional[List[str]] = None,
        parent_evidence_id: str = "",
        _skip_save: bool = False,
    ) -> Dict[str, Any]:
        # Use cached registry if available (for batch operations)
        if self._registry_cache is not None:
            reg = self._registry_cache
        else:
            reg = self._load_json(self.registry_path)
        ev_num = reg["next_evidence_number"]
        evidence_id = f"EV-2026-{ev_num:05d}"
        reg["next_evidence_number"] = ev_num + 1
        timestamp = now_iso()

        file_hash = ""
        file_size = 0
        file_name = ""
        stored_path = ""

        if source_file and source_file.exists():
            file_hash = sha256_file(source_file)
            file_size = source_file.stat().st_size
            file_name = source_file.name
            dest = self.case_dir / folder / f"{evidence_id}_{file_name}"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, dest)
            stored_path = str(dest)
        elif text_content:
            file_hash = sha256_text(text_content)
            file_size = len(text_content.encode("utf-8"))
            safe = sanitize_filename(title)
            file_name = f"{evidence_id}_{safe}.txt"
            dest = self.case_dir / folder / file_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text_content, encoding="utf-8")
            stored_path = str(dest)

        version = 1
        if parent_evidence_id:
            version = max(
                (i.get("version", 1) for i in reg["evidence_items"]
                 if i.get("parent_evidence_id") == parent_evidence_id or i.get("evidence_id") == parent_evidence_id),
                default=0,
            ) + 1

        item = {
            "evidence_id": evidence_id,
            "parent_evidence_id": parent_evidence_id,
            "version": version,
            "title": title,
            "description": description,
            "evidence_type": evidence_type,
            "source": source,
            "custodian": custodian,
            "folder": folder,
            "file_name": file_name,
            "stored_path": stored_path,
            "sha256": file_hash,
            "file_size_bytes": file_size,
            "registered_at": timestamp,
            "date_of_event": date_of_event,
            "notes": notes,
            "related_evidence": related_evidence or [],
            "provenance": {
                "acquisition_method": acquisition_method,
                "acquisition_date": acquisition_date or date_of_event,
                "obtained_from": obtained_from or source,
                "authenticity_status": authenticity_status,
                "verification_status": verification_status,
                "verified_by": "SHA-256" if file_hash else "",
                "verification_date": timestamp if file_hash else "",
            },
            "chain_of_custody": [
                {"action": "registered", "actor": "Hermes", "timestamp": timestamp, "notes": "Initial registration"}
            ],
        }

        reg["evidence_items"].append(item)
        reg["registry_revision"] = reg.get("registry_revision", 0) + 1
        if _skip_save:
            self._registry_cache = reg
        else:
            self._registry_cache = None
            self._save_json(self.registry_path, reg)
        return item

    def flush_registry(self):
        """Save the cached registry to disk (use after batch registrations with _skip_save=True)."""
        if self._registry_cache is not None:
            self._save_json(self.registry_path, self._registry_cache)
            self._registry_cache = None

    # ── Typed Evidence Relationships ─────────────────────────────────

    def add_relationship(
        self,
        source_evidence_id: str,
        target_evidence_id: str,
        relationship_type: str,
        notes: str = "",
    ) -> Dict[str, Any]:
        assert relationship_type in RELATIONSHIP_TYPES, f"Type must be one of {RELATIONSHIP_TYPES}"
        rels = self._load_json(self.relationships_path)
        entry = {
            "source": source_evidence_id,
            "target": target_evidence_id,
            "type": relationship_type,
            "notes": notes,
            "registered_at": now_iso(),
        }
        rels["relationships"].append(entry)
        self._save_json(self.relationships_path, rels)
        return entry

    # ── Chronology ───────────────────────────────────────────────────

    def add_chronology_event(
        self,
        date: str,
        event: str,
        category: str = "general",
        evidence_ids: Optional[List[str]] = None,
        notes: str = "",
    ) -> Dict[str, Any]:
        chron = self._load_json(self.chronology_path)
        entry = {
            "date": date, "event": event, "category": category,
            "evidence_ids": evidence_ids or [], "notes": notes, "recorded_at": now_iso(),
        }
        chron["events"].append(entry)
        chron["events"].sort(key=lambda x: x["date"])
        self._save_json(self.chronology_path, chron)
        return entry

    # ── Fact Ledger ──────────────────────────────────────────────────

    def add_fact(
        self,
        fact_text: str,
        supporting_evidence_ids: Optional[List[str]] = None,
        status: str = "unsupported",
        confidence_score: float = 0.0,
        missing: str = "",
        notes: str = "",
    ) -> Dict[str, Any]:
        """Facts reference evidence directly. Legal analyses reference facts."""
        assert 0.0 <= confidence_score <= 1.0, "confidence_score must be 0.0-1.0"
        assert status in {"supported", "partially_supported", "unsupported", "contradicted"}
        ledger = self._load_json(self.fact_ledger_path)
        fact_id = f"FCT-{len(ledger['facts']) + 1:04d}"
        entry = {
            "fact_id": fact_id,
            "fact": fact_text,
            "supporting_evidence_ids": supporting_evidence_ids or [],
            "status": status,
            "confidence": {"score": confidence_score, "label": confidence_label(confidence_score)},
            "missing": missing,
            "notes": notes,
            "registered_at": now_iso(),
        }
        ledger["facts"].append(entry)
        ledger["ledger_revision"] = ledger.get("ledger_revision", 0) + 1
        self._save_json(self.fact_ledger_path, ledger)
        return entry

    # ── Legal Analysis Ledger ────────────────────────────────────────

    def add_legal_analysis(
        self,
        question: str,
        analysis_text: str,
        supporting_fact_ids: Optional[List[str]] = None,
        legal_authority_ids: Optional[List[str]] = None,
        status: str = "unsupported",
        confidence_score: float = 0.0,
        conclusion: str = "",
        notes: str = "",
    ) -> Dict[str, Any]:
        """Legal analyses reference facts and authorities, NOT evidence directly."""
        assert 0.0 <= confidence_score <= 1.0
        assert status in {"supported", "partially_supported", "unsupported", "contradicted"}
        ledger = self._load_json(self.legal_ledger_path)
        analysis_id = f"LEG-{len(ledger['analyses']) + 1:04d}"
        entry = {
            "analysis_id": analysis_id,
            "question": question,
            "analysis": analysis_text,
            "supporting_fact_ids": supporting_fact_ids or [],
            "legal_authority_ids": legal_authority_ids or [],
            "supporting_evidence_ids": [],  # Empty by design — legal references facts, not evidence
            "status": status,
            "confidence": {"score": confidence_score, "label": confidence_label(confidence_score)},
            "conclusion": conclusion,
            "notes": notes,
            "registered_at": now_iso(),
        }
        ledger["analyses"].append(entry)
        ledger["ledger_revision"] = ledger.get("ledger_revision", 0) + 1
        self._save_json(self.legal_ledger_path, ledger)
        return entry

    # ── Authority Ledger ─────────────────────────────────────────────

    def add_authority(
        self,
        authority: str,
        citation: str,
        authority_type: str = "federal_statute",
        jurisdiction: str = "federal",
        supports: Optional[List[str]] = None,
        strength: str = "primary",
        status: str = "applicable",
        quoted: bool = False,
        mandatory: bool = True,
        weight: float = 1.0,
        notes: str = "",
    ) -> Dict[str, Any]:
        assert authority_type in AUTHORITY_TYPES, f"Type must be one of {AUTHORITY_TYPES}"
        assert strength in AUTHORITY_STRENGTH, f"Strength must be one of {AUTHORITY_STRENGTH}"
        assert 0.0 <= weight <= 1.0
        ledger = self._load_json(self.authority_ledger_path)
        auth_id = f"AUTH-{len(ledger['authorities']) + 1:04d}"
        entry = {
            "authority_id": auth_id,
            "authority": authority,
            "citation": citation,
            "authority_type": authority_type,
            "jurisdiction": jurisdiction,
            "supports": supports or [],
            "strength": strength,
            "status": status,
            "quoted": quoted,
            "mandatory": mandatory,
            "weight": weight,
            "notes": notes,
            "registered_at": now_iso(),
        }
        ledger["authorities"].append(entry)
        ledger["ledger_revision"] = ledger.get("ledger_revision", 0) + 1
        self._save_json(self.authority_ledger_path, ledger)
        return entry

    # ── Evidence Request Register ────────────────────────────────────

    def add_evidence_request(
        self,
        document_requested: str,
        requested_from: str,
        date_requested: str,
        status: str = "outstanding",
        response_received: str = "",
        response_date: str = "",
        notes: str = "",
    ) -> Dict[str, Any]:
        assert status in {"outstanding", "partially_received", "received", "denied", "overdue"}
        reqs = self._load_json(self.request_register_path)
        req_id = f"REQ-{len(reqs['requests']) + 1:04d}"
        entry = {
            "request_id": req_id,
            "document_requested": document_requested,
            "requested_from": requested_from,
            "date_requested": date_requested,
            "status": status,
            "response_received": response_received,
            "response_date": response_date,
            "notes": notes,
            "registered_at": now_iso(),
        }
        reqs["requests"].append(entry)
        self._save_json(self.request_register_path, reqs)
        return entry

    # ── Decision Ledger ──────────────────────────────────────────────

    def add_decision(
        self,
        question: str,
        decision: str,
        reason: str,
        inputs: Optional[List[str]] = None,
        alternatives_considered: Optional[List[str]] = None,
        decision_date: str = "",
        author: str = "Hermes",
        notes: str = "",
    ) -> Dict[str, Any]:
        """Record a strategic decision with its inputs, reasoning, and alternatives."""
        ledger = self._load_json(self.decision_ledger_path)
        dec_id = f"DEC-{len(ledger['decisions']) + 1:04d}"
        entry = {
            "decision_id": dec_id,
            "question": question,
            "decision": decision,
            "reason": reason,
            "inputs": inputs or [],
            "alternatives_considered": alternatives_considered or [],
            "decision_date": decision_date or now_iso()[:10],
            "author": author,
            "notes": notes,
            "registered_at": now_iso(),
        }
        ledger["decisions"].append(entry)
        ledger["ledger_revision"] = ledger.get("ledger_revision", 0) + 1
        self._save_json(self.decision_ledger_path, ledger)
        return entry

    # ── Event Ledger ─────────────────────────────────────────────────

    def add_event(
        self,
        date: str,
        event_type: str,
        description: str,
        related_evidence: Optional[List[str]] = None,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Record a case event (correspondence received, filed, disputed, etc.)."""
        ledger = self._load_json(self.event_ledger_path)
        event_id = f"EVT-{len(ledger['events']) + 1:04d}"
        entry = {
            "event_id": event_id,
            "date": date,
            "type": event_type,
            "description": description,
            "related_evidence": related_evidence or [],
            "notes": notes,
            "registered_at": now_iso(),
        }
        ledger["events"].append(entry)
        ledger["events"].sort(key=lambda x: x["date"])
        self._save_json(self.event_ledger_path, ledger)
        return entry

    # ── Integrity Validation ─────────────────────────────────────────

    def validate_integrity(self) -> Dict[str, Any]:
        """
        Check for structural problems:
        - Facts referencing non-existent evidence
        - Legal analyses referencing non-existent facts
        - Authorities never referenced by any analysis
        - Missing chain-of-custody
        - Orphaned evidence (registered but never referenced)
        """
        reg = self._load_json(self.registry_path)
        facts = self._load_json(self.fact_ledger_path)
        legal = self._load_json(self.legal_ledger_path)
        auths = self._load_json(self.authority_ledger_path)

        ev_ids = {i["evidence_id"] for i in reg.get("evidence_items", [])}
        fact_ids = {f["fact_id"] for f in facts.get("facts", [])}
        all_auth_ids = {a["authority_id"] for a in auths.get("authorities", [])}

        issues = []

        # 1. Facts referencing non-existent evidence
        for f in facts.get("facts", []):
            for ev_id in f.get("supporting_evidence_ids", []):
                if ev_id not in ev_ids:
                    issues.append({
                        "type": "dangling_evidence_reference",
                        "source": f["fact_id"],
                        "missing": ev_id,
                        "severity": "high",
                    })

        # 2. Legal analyses referencing non-existent facts
        for a in legal.get("analyses", []):
            for fid in a.get("supporting_fact_ids", []):
                if fid not in fact_ids:
                    issues.append({
                        "type": "dangling_fact_reference",
                        "source": a["analysis_id"],
                        "missing": fid,
                        "severity": "high",
                    })

        # 3. Authorities never referenced
        referenced_auths = set()
        for a in legal.get("analyses", []):
            for aid in a.get("legal_authority_ids", []):
                referenced_auths.add(aid)
        for a in auths.get("authorities", []):
            if a["authority_id"] not in referenced_auths:
                issues.append({
                    "type": "unreferenced_authority",
                    "source": a["authority_id"],
                    "severity": "low",
                })

        # 4. Missing chain-of-custody
        for item in reg.get("evidence_items", []):
            if not item.get("chain_of_custody"):
                issues.append({
                    "type": "missing_chain_of_custody",
                    "source": item["evidence_id"],
                    "severity": "medium",
                })

        # 5. Orphaned evidence (not referenced by any fact)
        referenced_ev = set()
        for f in facts.get("facts", []):
            for ev_id in f.get("supporting_evidence_ids", []):
                referenced_ev.add(ev_id)
        for item in reg.get("evidence_items", []):
            if item["evidence_id"] not in referenced_ev:
                issues.append({
                    "type": "orphaned_evidence",
                    "source": item["evidence_id"],
                    "severity": "low",
                })

        return {
            "case_id": self.case_id,
            "validated_at": now_iso(),
            "issues": issues,
            "issue_count": len(issues),
            "high_severity": sum(1 for i in issues if i["severity"] == "high"),
            "medium_severity": sum(1 for i in issues if i["severity"] == "medium"),
            "low_severity": sum(1 for i in issues if i["severity"] == "low"),
            "valid": len([i for i in issues if i["severity"] == "high"]) == 0,
        }

    # ── Contradiction Detection ──────────────────────────────────────

    def detect_contradictions(self) -> List[Dict[str, Any]]:
        """
        Detect contradictions between facts.
        Flags facts with opposing statuses on the same subject matter.
        Also checks typed evidence relationships with 'contradicts' type.
        """
        facts = self._load_json(self.fact_ledger_path)
        rels = self._load_json(self.relationships_path)
        all_facts = facts.get("facts", [])

        contradictions = []

        # 1. Check typed 'contradicts' relationships
        for r in rels.get("relationships", []):
            if r["type"] == "contradicts":
                contradictions.append({
                    "type": "evidence_relationship",
                    "source": r["source"],
                    "target": r["target"],
                    "notes": r.get("notes", ""),
                    "confidence": "high",
                    "review_required": True,
                    "detected_at": now_iso(),
                })

        # 2. Check for facts with 'contradicted' status
        for f in all_facts:
            if f["status"] == "contradicted":
                contradictions.append({
                    "type": "fact_status",
                    "fact_id": f["fact_id"],
                    "fact": f["fact"],
                    "confidence": f["confidence"]["label"],
                    "review_required": True,
                    "detected_at": now_iso(),
                })

        # 3. Check for duplicate facts with conflicting confidence/status
        seen = {}
        for f in all_facts:
            key = f["fact"].lower().strip()[:50]
            if key in seen:
                prev = seen[key]
                if prev["status"] != f["status"]:
                    contradictions.append({
                        "type": "conflicting_status",
                        "fact_ids": [prev["fact_id"], f["fact_id"]],
                        "fact": f["fact"],
                        "statuses": [prev["status"], f["status"]],
                        "confidence": "moderate",
                        "review_required": True,
                        "detected_at": now_iso(),
                    })
            else:
                seen[key] = f

        result = {"case_id": self.case_id, "contradictions": contradictions, "last_scan": now_iso()}
        self._save_json(self.contradictions_path, result)
        return contradictions

    # ── Evidence Sufficiency Rules ───────────────────────────────────

    def add_sufficiency_rule(
        self,
        rule_name: str,
        claim_description: str,
        required_documents: List[str],
        minimum_required: int = 0,
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Define explicit requirements for a claim.
        minimum_required: if 0, ALL required_documents must be present.
        If >0, at least that many must be present.
        """
        rules = self._load_json(self.sufficiency_path)
        rule_id = f"SUF-{len(rules['rules']) + 1:04d}"
        if minimum_required == 0:
            minimum_required = len(required_documents)
        entry = {
            "rule_id": rule_id,
            "rule_name": rule_name,
            "claim_description": claim_description,
            "required_documents": required_documents,
            "minimum_required": minimum_required,
            "notes": notes,
            "registered_at": now_iso(),
        }
        rules["rules"].append(entry)
        self._save_json(self.sufficiency_path, rules)
        return entry

    def evaluate_sufficiency(self) -> List[Dict[str, Any]]:
        """Evaluate all sufficiency rules against current evidence only (not requests)."""
        rules = self._load_json(self.sufficiency_path)
        reg = self._load_json(self.registry_path)

        # Only check evidence titles/descriptions — NOT outstanding requests
        ev_text = " ".join(
            (i["title"] + " " + i.get("description", "")).lower()
            for i in reg.get("evidence_items", [])
        )

        results = []
        for rule in rules.get("rules", []):
            found = []
            missing = []
            for doc in rule["required_documents"]:
                keywords = doc.lower().split()[:3]
                # Require ALL first 3 keywords to match, not just one
                if all(w in ev_text for w in keywords):
                    found.append(doc)
                else:
                    missing.append(doc)
            satisfied = len(found) >= rule["minimum_required"]
            results.append({
                "rule_id": rule["rule_id"],
                "rule_name": rule["rule_name"],
                "claim": rule["claim_description"],
                "found": found,
                "missing": missing,
                "minimum_required": rule["minimum_required"],
                "found_count": len(found),
                "satisfied": satisfied,
                "evaluated_at": now_iso(),
            })
        return results

    # ── Evidence Dependency Graph ────────────────────────────────────

    def add_dependency(
        self,
        claim_id: str,
        claim_text: str,
        required_evidence: List[str],
        current_evidence: Optional[List[str]] = None,
        current_facts: Optional[List[str]] = None,
        outstanding_requests: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Map: claim -> required evidence -> current evidence/facts -> outstanding requests."""
        graph = self._load_json(self.dependency_graph_path)
        entry = {
            "claim_id": claim_id,
            "claim_text": claim_text,
            "required_evidence": required_evidence,
            "current_evidence": current_evidence or [],
            "current_facts": current_facts or [],
            "outstanding_requests": outstanding_requests or [],
            "gap_count": len(required_evidence) - len(current_evidence or []),
            "registered_at": now_iso(),
        }
        graph["dependencies"].append(entry)
        self._save_json(self.dependency_graph_path, graph)
        return entry

    # ── Four-Dimension Readiness Score ───────────────────────────────

    def calculate_readiness(self) -> Dict[str, Any]:
        reg = self._load_json(self.registry_path)
        chron = self._load_json(self.chronology_path)
        facts = self._load_json(self.fact_ledger_path)
        legal = self._load_json(self.legal_ledger_path)
        auths = self._load_json(self.authority_ledger_path)
        reqs = self._load_json(self.request_register_path)
        items = reg.get("evidence_items", [])

        folder_counts = {}
        for item in items:
            f = item["folder"]
            folder_counts[f] = folder_counts.get(f, 0) + 1

        # 1. Repository Completeness
        completeness_cats = {
            "Evidence": {"weight": 0.25, "score": min(100, len(items) * 10) if items else 0, "detail": f"{len(items)} items"},
            "Timeline": {"weight": 0.20, "score": min(100, len(chron.get("events", [])) * 15) if chron.get("events") else 0, "detail": f"{len(chron.get('events', []))} events"},
            "Authentication": {"weight": 0.20, "score": 100 if all(i.get("sha256") for i in items) else (0 if not items else 50), "detail": "All SHA-256 hashed" if items else "None"},
            "Correspondence": {"weight": 0.15, "score": min(100, folder_counts.get("05_Correspondence", 0) * 20), "detail": f"{folder_counts.get('05_Correspondence', 0)} items"},
            "Preservation": {"weight": 0.20, "score": 100 if all(i.get("stored_path") for i in items) else (0 if not items else 50), "detail": "All stored" if items else "None"},
        }
        repository = round(sum(c["score"] * c["weight"] for c in completeness_cats.values()))

        # 2. Evidence Strength (confidence-weighted facts)
        all_facts = facts.get("facts", [])
        if all_facts:
            conf_w = {"high": 1.0, "moderate": 0.7, "low": 0.4}
            weighted = sum(conf_w.get(f["confidence"]["label"], 0.4) for f in all_facts if f["status"] in ("supported", "partially_supported"))
            evidence_strength = round((weighted / len(all_facts)) * 100)
        else:
            evidence_strength = 0

        # 3. Legal Readiness (legal analyses + authorities)
        all_legal = legal.get("analyses", [])
        all_auths = auths.get("authorities", [])
        if all_legal:
            legal_conf_w = {"high": 1.0, "moderate": 0.7, "low": 0.4}
            legal_weighted = sum(legal_conf_w.get(a["confidence"]["label"], 0.4) for a in all_legal if a["status"] in ("supported", "partially_supported"))
            legal_base = round((legal_weighted / len(all_legal)) * 100)
        else:
            legal_base = 0
        # Authority coverage bonus
        auth_coverage = min(100, len(all_auths) * 20) if all_auths else 0
        legal_readiness = round(legal_base * 0.7 + auth_coverage * 0.3)

        # 4. Procedural Readiness (requests, deadlines, packets)
        all_reqs = reqs.get("requests", [])
        outstanding = sum(1 for r in all_reqs if r["status"] == "outstanding")
        received = sum(1 for r in all_reqs if r["status"] == "received")
        total_reqs = len(all_reqs)
        if total_reqs > 0:
            procedural = round((received / total_reqs) * 100)
        else:
            procedural = 100  # No requests needed = fully ready procedurally

        # Overall (weighted average of 4 dimensions)
        overall = round(repository * 0.3 + evidence_strength * 0.25 + legal_readiness * 0.25 + procedural * 0.20)

        result = {
            "case_id": self.case_id,
            "calculated_at": now_iso(),
            "dimensions": {
                "repository_completeness": {"score": repository, "categories": completeness_cats},
                "evidence_strength": {"score": evidence_strength, "facts_count": len(all_facts)},
                "legal_readiness": {"score": legal_readiness, "analyses_count": len(all_legal), "authorities_count": len(all_auths)},
                "procedural_readiness": {"score": procedural, "requests_total": total_reqs, "outstanding": outstanding, "received": received},
            },
            "overall_readiness": overall,
            "grade": "A" if overall >= 90 else "B" if overall >= 80 else "C" if overall >= 70 else "D" if overall >= 60 else "F",
            "note": "Four dimensions: Repository (file completeness), Evidence (fact confidence), Legal (analysis + authority coverage), Procedural (request resolution).",
        }
        self._save_json(self.readiness_path, result)
        return result

    # ── Immutable Packet Generation with Reproducibility ─────────────

    def generate_packet(self) -> str:
        self._packet_version += 1
        version_str = f"v{self._packet_version:03d}"

        reg = self._load_json(self.registry_path)
        chron = self._load_json(self.chronology_path)
        facts = self._load_json(self.fact_ledger_path)
        legal = self._load_json(self.legal_ledger_path)
        auths = self._load_json(self.authority_ledger_path)
        reqs = self._load_json(self.request_register_path)
        deps = self._load_json(self.dependency_graph_path)
        rels = self._load_json(self.relationships_path)
        mods = self._load_json(self.modules_path)
        decisions = self._load_json(self.decision_ledger_path)
        contradictions = self._load_json(self.contradictions_path)
        readiness = self.calculate_readiness()
        sufficiency = self.evaluate_sufficiency()

        L = []
        L.append(f"# Case Packet {version_str} - {self.case_id}")
        L.append(f"# {self.case_name}")
        L.append(f"# Generated: {readiness['calculated_at']}")
        L.append(f"# Readiness: {readiness['overall_readiness']}% (Grade {readiness['grade']})")
        L.append(f"# Packet Version: {version_str} (immutable, reproducible)")
        L.append("")
        L.append("---")
        L.append("")

        # Reproducibility metadata
        L.append("## Reproducibility Metadata")
        L.append("")
        L.append(f"- registry_revision: {reg.get('registry_revision', 0)}")
        L.append(f"- fact_ledger_revision: {facts.get('ledger_revision', 0)}")
        L.append(f"- legal_ledger_revision: {legal.get('ledger_revision', 0)}")
        L.append(f"- authority_ledger_revision: {auths.get('ledger_revision', 0)}")
        L.append(f"- generated_at: {readiness['calculated_at']}")
        L.append(f"- packet_version: {version_str}")
        L.append("")

        # Cover Sheet
        L.append("## Cover Sheet")
        L.append("")
        L.append(f"- Case ID: {self.case_id}")
        L.append(f"- Case Name: {self.case_name}")
        L.append(f"- Priority: {self.priority.upper()}")
        L.append(f"- External Action: {self.external_action.upper()}")
        L.append(f"- Modules: {', '.join(mods.get('enabled_modules', [])) or 'none'}")
        L.append(f"- Evidence Items: {len(reg.get('evidence_items', []))}")
        L.append(f"- Facts: {len(facts.get('facts', []))}")
        L.append(f"- Legal Analyses: {len(legal.get('analyses', []))}")
        L.append(f"- Authorities: {len(auths.get('authorities', []))}")
        L.append(f"- Requests: {len(reqs.get('requests', []))}")
        L.append(f"- Dependencies: {len(deps.get('dependencies', []))}")
        L.append(f"- Relationships: {len(rels.get('relationships', []))}")
        L.append("")

        # Timeline
        L.append("## Timeline")
        L.append("")
        for e in chron.get("events", []):
            L.append(f"- {e['date']} [{e['category']}]: {e['event']}")
        L.append("")

        # Evidence Index
        L.append("## Evidence Index")
        L.append("")
        items = reg.get("evidence_items", [])
        if items:
            L.append("| Evidence ID | Title | Type | Version | SHA-256 (16) | Date | Folder |")
            L.append("|---|---|---|---|---|---|---|")
            for item in items:
                sha = item.get("sha256", "")[:16] or "N/A"
                L.append(f"| {item['evidence_id']} | {item['title']} | {item['evidence_type']} | v{item.get('version', 1)} | {sha}... | {item.get('date_of_event', '')} | {item['folder']} |")
        else:
            L.append("(No evidence items)")
        L.append("")

        # Evidence Relationships
        L.append("## Evidence Relationships")
        L.append("")
        all_rels = rels.get("relationships", [])
        if all_rels:
            L.append("| Source | Target | Type | Notes |")
            L.append("|---|---|---|---|")
            for r in all_rels:
                L.append(f"| {r['source']} | {r['target']} | {r['type']} | {r.get('notes', '')} |")
        else:
            L.append("(No relationships)")
        L.append("")

        # Fact Ledger
        L.append("## Fact Ledger")
        L.append("")
        all_facts = facts.get("facts", [])
        if all_facts:
            L.append("| Fact ID | Fact | Status | Confidence | Score | Evidence | Missing |")
            L.append("|---|---|---|---|---|---|---|")
            for f in all_facts:
                ev = ", ".join(f["supporting_evidence_ids"]) or "None"
                L.append(f"| {f['fact_id']} | {f['fact']} | {f['status']} | {f['confidence']['label']} | {f['confidence']['score']} | {ev} | {f.get('missing', 'None')} |")
        else:
            L.append("(No facts)")
        L.append("")

        # Legal Analysis Ledger
        L.append("## Legal Analysis Ledger")
        L.append("")
        all_legal = legal.get("analyses", [])
        if all_legal:
            L.append("| ID | Question | Analysis | Status | Confidence | Facts | Authorities | Conclusion |")
            L.append("|---|---|---|---|---|---|---|---|")
            for a in all_legal:
                fids = ", ".join(a.get("supporting_fact_ids", [])) or "None"
                aids = ", ".join(a.get("legal_authority_ids", [])) or "None"
                L.append(f"| {a['analysis_id']} | {a['question']} | {a['analysis']} | {a['status']} | {a['confidence']['label']} | {fids} | {aids} | {a.get('conclusion', '')} |")
        else:
            L.append("(No legal analyses)")
        L.append("")

        # Authority Ledger
        L.append("## Authority Ledger")
        L.append("")
        all_auths = auths.get("authorities", [])
        if all_auths:
            L.append("| ID | Authority | Citation | Type | Jurisdiction | Strength | Mandatory | Weight | Supports |")
            L.append("|---|---|---|---|---|---|---|---|---|")
            for a in all_auths:
                supports = ", ".join(a["supports"]) or "None"
                L.append(f"| {a['authority_id']} | {a['authority']} | {a['citation']} | {a['authority_type']} | {a['jurisdiction']} | {a['strength']} | {'Yes' if a['mandatory'] else 'No'} | {a['weight']} | {supports} |")
        else:
            L.append("(No authorities)")
        L.append("")

        # Evidence Request Register
        L.append("## Evidence Request Register")
        L.append("")
        all_reqs = reqs.get("requests", [])
        if all_reqs:
            L.append("| Request ID | Document | From | Date | Status |")
            L.append("|---|---|---|---|---|")
            for r in all_reqs:
                L.append(f"| {r['request_id']} | {r['document_requested']} | {r['requested_from']} | {r['date_requested']} | {r['status']} |")
        else:
            L.append("(No requests)")
        L.append("")

        # Dependency Graph
        L.append("## Evidence Dependency Graph")
        L.append("")
        all_deps = deps.get("dependencies", [])
        if all_deps:
            for d in all_deps:
                L.append(f"### {d['claim_id']}: {d['claim_text']}")
                L.append(f"  Required: {', '.join(d['required_evidence'])}")
                L.append(f"  Current Evidence: {', '.join(d.get('current_evidence', [])) or 'None'}")
                L.append(f"  Current Facts: {', '.join(d.get('current_facts', [])) or 'None'}")
                L.append(f"  Outstanding: {', '.join(d['outstanding_requests']) or 'None'}")
                L.append(f"  Gap: {d['gap_count']} missing")
                L.append("")
        else:
            L.append("(No dependencies)")
        L.append("")

        # Four-Dimension Readiness
        L.append("## Litigation Readiness (Four Dimensions)")
        L.append("")
        dims = readiness["dimensions"]
        L.append(f"Overall: {readiness['overall_readiness']}% (Grade {readiness['grade']})")
        L.append("")
        L.append("| Dimension | Score |")
        L.append("|---|---|")
        L.append(f"| Repository Completeness | {dims['repository_completeness']['score']}% |")
        L.append(f"| Evidence Strength | {dims['evidence_strength']['score']}% |")
        L.append(f"| Legal Readiness | {dims['legal_readiness']['score']}% |")
        L.append(f"| Procedural Readiness | {dims['procedural_readiness']['score']}% |")
        L.append("")
        L.append(f"Note: {readiness['note']}")
        L.append("")

        # Decision Ledger
        L.append("## Decision Ledger")
        L.append("")
        all_decs = decisions.get("decisions", [])
        if all_decs:
            L.append("| Decision ID | Question | Decision | Reason | Date | Author |")
            L.append("|---|---|---|---|---|---|")
            for d in all_decs:
                L.append(f"| {d['decision_id']} | {d['question']} | {d['decision']} | {d['reason']} | {d['decision_date']} | {d['author']} |")
        else:
            L.append("(No decisions recorded)")
        L.append("")

        # Contradiction Detection
        L.append("## Contradiction Detection")
        L.append("")
        all_contras = contradictions.get("contradictions", [])
        if all_contras:
            L.append("| Type | Details | Confidence | Review Required |")
            L.append("|---|---|---|---|")
            for c in all_contras:
                details = json.dumps({k: v for k, v in c.items() if k not in ("type", "confidence", "review_required", "detected_at")})
                L.append(f"| {c['type']} | {details} | {c.get('confidence', '')} | {'Yes' if c.get('review_required') else 'No'} |")
        else:
            L.append("No contradictions detected.")
        L.append("")

        # Sufficiency Evaluation
        L.append("## Evidence Sufficiency Evaluation")
        L.append("")
        if sufficiency:
            L.append("| Rule ID | Rule | Required | Found | Missing | Satisfied |")
            L.append("|---|---|---|---|---|---|")
            for s in sufficiency:
                missing_str = ", ".join(s["missing"][:3]) if s["missing"] else "None"
                L.append(f"| {s['rule_id']} | {s['rule_name']} | {s['minimum_required']} | {s['found_count']} | {missing_str} | {'YES' if s['satisfied'] else 'NO'} |")
        else:
            L.append("(No sufficiency rules defined)")
        L.append("")

        # Audit Receipt
        L.append("## Audit Receipt")
        L.append("")
        L.append(f"- Packet version: {version_str}")
        L.append(f"- Generated at: {readiness['calculated_at']}")
        L.append(f"- Generated by: Hermes (automated)")
        L.append(f"- External action: {self.external_action.upper()}")
        L.append(f"- Approval required: YES")
        L.append("")
        L.append("---")
        L.append(f"# End of Case Packet {version_str} for {self.case_id}")

        packet_text = "\n".join(L)
        packet_path = self.case_dir / "08_Drafts" / f"case_packet_{version_str}.md"
        packet_path.parent.mkdir(parents=True, exist_ok=True)
        packet_path.write_text(packet_text, encoding="utf-8")
        return packet_text

    # ── Renderer: Multiple output types from same data ───────────────

    def render(self, output_type: str) -> str:
        """Render different document types from the same underlying data."""
        if output_type == "case_packet":
            return self.generate_packet()
        elif output_type == "timeline":
            return self._render_timeline()
        elif output_type == "exhibit_index":
            return self._render_exhibit_index()
        elif output_type == "evidence_log":
            return self._render_evidence_log()
        elif output_type == "demand_letter":
            return self._render_demand_letter()
        else:
            raise ValueError(f"Unknown output type: {output_type}. Available: case_packet, timeline, exhibit_index, evidence_log, demand_letter")

    def _render_timeline(self) -> str:
        chron = self._load_json(self.chronology_path)
        L = [f"# Timeline - {self.case_id}", f"# {self.case_name}", f"# Generated: {now_iso()}", ""]
        for e in chron.get("events", []):
            L.append(f"**{e['date']}** [{e['category']}]: {e['event']}")
            if e.get("evidence_ids"):
                L.append(f"  Evidence: {', '.join(e['evidence_ids'])}")
            L.append("")
        path = self.case_dir / "08_Drafts" / f"timeline_{now_iso()[:10]}.md"
        path.write_text("\n".join(L), encoding="utf-8")
        return "\n".join(L)

    def _render_exhibit_index(self) -> str:
        reg = self._load_json(self.registry_path)
        L = [f"# Exhibit Index - {self.case_id}", f"# {self.case_name}", f"# Generated: {now_iso()}", ""]
        L.append("| Exhibit # | Evidence ID | Title | Type | SHA-256 |")
        L.append("|---|---|---|---|---|")
        for i, item in enumerate(reg.get("evidence_items", []), 1):
            L.append(f"| {i} | {item['evidence_id']} | {item['title']} | {item['evidence_type']} | {item.get('sha256', '')[:16]}... |")
        path = self.case_dir / "08_Drafts" / f"exhibit_index_{now_iso()[:10]}.md"
        path.write_text("\n".join(L), encoding="utf-8")
        return "\n".join(L)

    def _render_evidence_log(self) -> str:
        reg = self._load_json(self.registry_path)
        L = [f"# Evidence Log - {self.case_id}", f"# {self.case_name}", f"# Generated: {now_iso()}", ""]
        for item in reg.get("evidence_items", []):
            L.append(f"## {item['evidence_id']}")
            L.append(f"- Title: {item['title']}")
            L.append(f"- Type: {item['evidence_type']}")
            L.append(f"- Source: {item.get('source', '')}")
            L.append(f"- Custodian: {item.get('custodian', '')}")
            L.append(f"- SHA-256: {item.get('sha256', '')}")
            L.append(f"- Date of Event: {item.get('date_of_event', '')}")
            L.append(f"- Registered: {item.get('registered_at', '')}")
            L.append(f"- Provenance: {json.dumps(item.get('provenance', {}), indent=2)}")
            L.append("")
        path = self.case_dir / "08_Drafts" / f"evidence_log_{now_iso()[:10]}.md"
        path.write_text("\n".join(L), encoding="utf-8")
        return "\n".join(L)

    def _render_demand_letter(self) -> str:
        facts = self._load_json(self.fact_ledger_path)
        legal = self._load_json(self.legal_ledger_path)
        auths = self._load_json(self.authority_ledger_path)
        reqs = self._load_json(self.request_register_path)
        L = [f"# Demand Letter Draft - {self.case_id}", f"# {self.case_name}", f"# Generated: {now_iso()}", ""]
        L.append("**STATUS: DRAFT - NOT FOR SUBMISSION WITHOUT APPROVAL**")
        L.append("")
        L.append("## Factual Basis")
        L.append("")
        for f in facts.get("facts", []):
            L.append(f"- {f['fact_id']}: {f['fact']} (Confidence: {f['confidence']['label']})")
        L.append("")
        L.append("## Legal Basis")
        L.append("")
        for a in legal.get("analyses", []):
            L.append(f"- {a['analysis_id']}: {a['question']} -> {a.get('conclusion', '')}")
        L.append("")
        L.append("## Authorities Cited")
        L.append("")
        for a in auths.get("authorities", []):
            L.append(f"- {a['authority_id']}: {a['citation']} ({a['authority_type']}, {a['strength']})")
        L.append("")
        L.append("## Documents Requested")
        L.append("")
        for r in reqs.get("requests", []):
            L.append(f"- {r['request_id']}: {r['document_requested']} (Status: {r['status']})")
        L.append("")
        L.append("**External submission: LOCKED. Approval required: YES.**")
        path = self.case_dir / "08_Drafts" / f"demand_letter_draft_{now_iso()[:10]}.md"
        path.write_text("\n".join(L), encoding="utf-8")
        return "\n".join(L)

    # ── Status ───────────────────────────────────────────────────────

    def status(self) -> str:
        reg = self._load_json(self.registry_path)
        chron = self._load_json(self.chronology_path)
        facts = self._load_json(self.fact_ledger_path)
        legal = self._load_json(self.legal_ledger_path)
        auths = self._load_json(self.authority_ledger_path)
        reqs = self._load_json(self.request_register_path)
        deps = self._load_json(self.dependency_graph_path)
        rels = self._load_json(self.relationships_path)
        mods = self._load_json(self.modules_path)
        decs = self._load_json(self.decision_ledger_path)
        r = self.calculate_readiness()

        lines = [
            f"Case: {self.case_id} - {self.case_name}",
            f"Template version: {mods.get('template_version', 'unknown')}",
            f"Modules: {', '.join(mods.get('enabled_modules', [])) or 'none'}",
            f"Evidence items: {len(reg.get('evidence_items', []))}",
            f"Chronology events: {len(chron.get('events', []))}",
            f"Facts: {len(facts.get('facts', []))}",
            f"Legal analyses: {len(legal.get('analyses', []))}",
            f"Authorities: {len(auths.get('authorities', []))}",
            f"Decisions: {len(decs.get('decisions', []))}",
            f"Evidence requests: {len(reqs.get('requests', []))}",
            f"Dependencies: {len(deps.get('dependencies', []))}",
            f"Relationships: {len(rels.get('relationships', []))}",
            f"Readiness: {r['overall_readiness']}% (Grade {r['grade']})",
            f"  Repository: {r['dimensions']['repository_completeness']['score']}%",
            f"  Evidence: {r['dimensions']['evidence_strength']['score']}%",
            f"  Legal: {r['dimensions']['legal_readiness']['score']}%",
            f"  Procedural: {r['dimensions']['procedural_readiness']['score']}%",
            f"Case dir: {self.case_dir}",
        ]
        return "\n".join(lines)