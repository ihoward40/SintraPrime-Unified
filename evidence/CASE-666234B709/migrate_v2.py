"""
Migrate CASE-666234B709 to CaseTemplate v2.0.
Updates: numeric confidence, legal analyses reference facts not evidence,
rich authority metadata, typed relationships, four-dimension readiness,
module system, renderer outputs.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from case_template import CaseTemplate

CASE_ID = "CASE-666234B709"
CASE_NAME = "Halsted / LVNV / Bank of Missouri / Milestone"
CASE_DIR = Path(r"C:\Users\admin\Desktop\SintraPrime-Unified\evidence") / CASE_ID

case = CaseTemplate(
    case_id=CASE_ID,
    case_name=CASE_NAME,
    evidence_counter_start=420,
    description="Celtic Bank/Reflex account ending 9370. LVNV acquisition. Resurgent collection.",
    priority="high",
    external_action="locked",
)

# Enable debt collection module
case.enable_module("debt_collection")
print("Module: debt_collection enabled")

# Migrate evidence + chronology from existing files
old_reg = json.load(open(CASE_DIR / "evidence_registry.json", "r", encoding="utf-8"))
# Add related_evidence if missing, keep registry_revision
if "registry_revision" not in old_reg:
    old_reg["registry_revision"] = len(old_reg["evidence_items"])
for item in old_reg["evidence_items"]:
    if "related_evidence" not in item:
        item["related_evidence"] = []
case._save_json(case.registry_path, old_reg)
print(f"Migrated {len(old_reg['evidence_items'])} evidence items")

old_chron = json.load(open(CASE_DIR / "chronology.json", "r", encoding="utf-8"))
case._save_json(case.chronology_path, old_chron)
print(f"Migrated {len(old_chron['events'])} chronology events")

# Migrate evidence requests
old_reqs = json.load(open(CASE_DIR / "evidence_request_register.json", "r", encoding="utf-8"))
case._save_json(case.request_register_path, old_reqs)
print(f"Migrated {len(old_reqs['requests'])} evidence requests")

# ── Rebuild fact ledger with numeric confidence ──────────────────────
# Old facts used string confidence. Map to numeric.
old_facts = json.load(open(CASE_DIR / "fact_ledger.json", "r", encoding="utf-8"))
conf_map = {"high": 0.85, "moderate": 0.60, "low": 0.30}

new_facts = {"case_id": CASE_ID, "facts": [], "ledger_revision": 0}
for f in old_facts["facts"]:
    old_conf = f.get("confidence", "low")
    if isinstance(old_conf, dict):
        score = old_conf["score"]
    else:
        score = conf_map.get(old_conf, 0.30)
    f["confidence"] = {"score": score, "label": "high" if score >= 0.8 else "moderate" if score >= 0.5 else "low"}
    new_facts["facts"].append(f)
new_facts["ledger_revision"] = len(new_facts["facts"])
case._save_json(case.fact_ledger_path, new_facts)
print(f"Migrated {len(new_facts['facts'])} facts with numeric confidence")

# ── Rebuild legal analysis ledger (references facts, not evidence) ───
old_legal = json.load(open(CASE_DIR / "legal_analysis_ledger.json", "r", encoding="utf-8"))
new_legal = {"case_id": CASE_ID, "analyses": [], "ledger_revision": 0}
for a in old_legal["analyses"]:
    old_conf = a.get("confidence", "low")
    if isinstance(old_conf, dict):
        score = old_conf["score"]
    else:
        score = conf_map.get(old_conf, 0.30)
    # Clear direct evidence references — legal references facts only
    a["supporting_evidence_ids"] = []
    a["confidence"] = {"score": score, "label": "high" if score >= 0.8 else "moderate" if score >= 0.5 else "low"}
    # Add question field if missing
    if "question" not in a:
        a["question"] = a["analysis"][:80] + "..."
    new_legal["analyses"].append(a)
new_legal["ledger_revision"] = len(new_legal["analyses"])
case._save_json(case.legal_ledger_path, new_legal)
print(f"Migrated {len(new_legal['analyses'])} legal analyses (evidence refs cleared)")

# ── Rebuild authority ledger with rich metadata ──────────────────────
old_auths = json.load(open(CASE_DIR / "authority_ledger.json", "r", encoding="utf-8"))
new_auths = {"case_id": CASE_ID, "authorities": [], "ledger_revision": 0}
auth_meta = {
    0: {"authority_type": "federal_statute", "jurisdiction": "federal", "strength": "primary", "mandatory": True, "weight": 1.0},
    1: {"authority_type": "federal_statute", "jurisdiction": "federal", "strength": "primary", "mandatory": True, "weight": 1.0},
    2: {"authority_type": "federal_statute", "jurisdiction": "federal", "strength": "primary", "mandatory": True, "weight": 1.0},
    3: {"authority_type": "state_statute", "jurisdiction": "state", "strength": "persuasive", "mandatory": False, "weight": 0.7},
}
for i, a in enumerate(old_auths["authorities"]):
    meta = auth_meta.get(i, {"authority_type": "federal_statute", "jurisdiction": "federal", "strength": "primary", "mandatory": True, "weight": 1.0})
    a.update(meta)
    new_auths["authorities"].append(a)
new_auths["ledger_revision"] = len(new_auths["authorities"])
case._save_json(case.authority_ledger_path, new_auths)
print(f"Migrated {len(new_auths['authorities'])} authorities with rich metadata")

# Migrate dependency graph
old_deps = json.load(open(CASE_DIR / "dependency_graph.json", "r", encoding="utf-8"))
case._save_json(case.dependency_graph_path, old_deps)
print(f"Migrated {len(old_deps['dependencies'])} dependencies")

# ── Add typed evidence relationships ─────────────────────────────────
case.add_relationship("EV-2026-00420", "EV-2026-00421", "references",
                       "Deficiency notice references the Resurgent response packet")
print("Relationship: EV-00420 -> EV-00421 (references)")

# ── Generate packet v001 with v2.0 format ────────────────────────────
print()
print("Generating case packet v001 (v2.0 format)...")
packet = case.generate_packet()
print("Packet v001 generated")

# Render additional output types
print()
print("Rendering timeline...")
case.render("timeline")
print("Rendering exhibit index...")
case.render("exhibit_index")
print("Rendering evidence log...")
case.render("evidence_log")
print("Rendering demand letter draft...")
case.render("demand_letter")

print()
print(case.status())