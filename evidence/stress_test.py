"""
Phase 4B: Kernel Stress Test Suite for CaseTemplate v2.1.0 RC1

Tests:
1. Cross-domain validation (5 synthetic cases across different modules)
2. Failure testing (seeded problems that the kernel should detect)
3. Renderer parity (all outputs internally consistent)
4. Performance test (large evidence set)

Release criteria:
- 5 synthetic cases created successfully
- Zero schema validation failures
- Contradiction engine detects seeded conflicts
- Sufficiency rules produce expected pass/fail results
- All renderers generate internally consistent outputs
- Integrity validation detects seeded problems
- Performance acceptable with large evidence sets
"""

import json
import os
import sys
import time
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from case_template import CaseTemplate, KERNEL_VERSION

PASS = 0
FAIL = 0
RESULTS = []

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        RESULTS.append(f"PASS: {name}")
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        RESULTS.append(f"FAIL: {name} - {detail}")
        print(f"  FAIL: {name} - {detail}")

def cleanup_case(case_id):
    base = Path(r"C:\Users\admin\Desktop\SintraPrime-Unified\evidence")
    d = base / case_id
    if d.exists():
        shutil.rmtree(d)


# ════════════════════════════════════════════════════════════════════
# OBJECTIVE 1: Cross-Domain Validation
# ════════════════════════════════════════════════════════════════════

print("=" * 60)
print("OBJECTIVE 1: Cross-Domain Validation")
print("=" * 60)

test_cases = [
    {"id": "TEST-001", "name": "Debt Collection Test", "module": "debt_collection",
     "description": "Baseline regression test for debt collection module"},
    {"id": "TEST-002", "name": "Credit Reporting Test", "module": "credit_reporting",
     "description": "Multiple tradelines and bureau disputes"},
    {"id": "TEST-003", "name": "Auto Finance Test", "module": "auto_finance",
     "description": "Repossession, payment history, deficiency balance"},
    {"id": "TEST-004", "name": "Tax Test", "module": "tax",
     "description": "IRS notices, correspondence, deadlines"},
    {"id": "TEST-005", "name": "Banking Test", "module": "banking",
     "description": "Deposit disputes, account closures, transaction records"},
]

created_cases = []
for tc in test_cases:
    cleanup_case(tc["id"])
    case = CaseTemplate(
        case_id=tc["id"],
        case_name=tc["name"],
        description=tc["description"],
        priority="medium",
    )
    case.enable_module(tc["module"])

    # Register sample evidence
    ev = case.register_evidence(
        text_content=f"Test evidence for {tc['name']}",
        title=f"Test Document - {tc['module']}",
        description="Synthetic test evidence",
        source="Test Suite",
        folder="06_Evidence",
    )

    # Add a fact
    fact = case.add_fact(
        fact_text=f"Test fact for {tc['module']} module",
        supporting_evidence_ids=[ev["evidence_id"]],
        status="partially_supported",
        confidence_score=0.6,
    )

    # Add an authority
    auth = case.add_authority(
        authority=f"Test authority for {tc['module']}",
        citation="Test citation",
        authority_type="federal_statute",
    )

    # Add a legal analysis
    legal = case.add_legal_analysis(
        question=f"Test legal question for {tc['module']}?",
        analysis_text=f"Test analysis for {tc['module']}",
        supporting_fact_ids=[fact["fact_id"]],
        legal_authority_ids=[auth["authority_id"]],
        status="partially_supported",
        confidence_score=0.5,
    )

    # Add a decision
    dec = case.add_decision(
        question=f"Test decision for {tc['module']}?",
        decision="Proceed with test",
        reason="Testing kernel behavior",
        inputs=[legal["analysis_id"]],
    )

    # Add an event
    evt = case.add_event(
        date="2026-07-03",
        event_type="test_event",
        description=f"Test event for {tc['module']}",
        related_evidence=[ev["evidence_id"]],
    )

    # Add a sufficiency rule
    rule = case.add_sufficiency_rule(
        rule_name=f"Test sufficiency for {tc['module']}",
        claim_description=f"Test claim for {tc['module']}",
        required_documents=["Test document 1", "Test document 2"],
    )

    # Detect contradictions
    contras = case.detect_contradictions()

    # Validate integrity
    integrity = case.validate_integrity()

    # Generate packet
    packet = case.generate_packet()

    # Render all types
    timeline = case.render("timeline")
    exhibit = case.render("exhibit_index")
    log = case.render("evidence_log")
    demand = case.render("demand_letter")

    created_cases.append(case)

    check(f"{tc['id']} created", case.case_id == tc["id"])
    check(f"{tc['id']} module enabled", tc["module"] in case._enabled_modules)
    check(f"{tc['id']} evidence registered", ev["evidence_id"].startswith("EV-2026-"))
    check(f"{tc['id']} fact has numeric confidence", isinstance(fact["confidence"]["score"], (int, float)))
    check(f"{tc['id']} legal refs facts not evidence", legal["supporting_evidence_ids"] == [])
    check(f"{tc['id']} decision recorded", dec["decision_id"].startswith("DEC-"))
    check(f"{tc['id']} event recorded", evt["event_id"].startswith("EVT-"))
    check(f"{tc['id']} sufficiency rule", rule["rule_id"].startswith("SUF-"))
    check(f"{tc['id']} integrity valid", integrity["valid"], f"issues: {integrity['issue_count']}")
    check(f"{tc['id']} packet generated", "Case Packet" in packet)
    check(f"{tc['id']} template version", case._load_json(case.modules_path).get("template_version") == KERNEL_VERSION)

print(f"\nObjective 1: {PASS} passed, {FAIL} failed across {len(test_cases)} cases\n")


# ════════════════════════════════════════════════════════════════════
# OBJECTIVE 2: Failure Testing
# ════════════════════════════════════════════════════════════════════

print("=" * 60)
print("OBJECTIVE 2: Failure Testing")
print("=" * 60)

obj2_pass_before = PASS
cleanup_case("TEST-FAIL-001")
fail_case = CaseTemplate(case_id="TEST-FAIL-001", case_name="Failure Test Case")

# Seed a fact referencing non-existent evidence
fail_case.add_fact(
    fact_text="Fact with dangling evidence reference",
    supporting_evidence_ids=["EV-2026-99999"],  # doesn't exist
    status="partially_supported",
    confidence_score=0.5,
)

# Seed a legal analysis referencing non-existent fact
fail_legal = fail_case.add_legal_analysis(
    question="Test with dangling fact ref?",
    analysis_text="Analysis referencing non-existent fact",
    supporting_fact_ids=["FCT-9999"],  # doesn't exist
    status="unsupported",
    confidence_score=0.2,
)

# Seed an unreferenced authority
fail_case.add_authority(
    authority="Unreferenced authority",
    citation="Test cite",
    authority_type="federal_statute",
)

# Seed contradictory facts
fail_case.add_fact(
    fact_text="Balance is $1,000",
    supporting_evidence_ids=[],
    status="supported",
    confidence_score=0.8,
)
fail_case.add_fact(
    fact_text="Balance is $1,000",
    supporting_evidence_ids=[],
    status="contradicted",
    confidence_score=0.3,
)

# Run integrity validation
integrity = fail_case.validate_integrity()
check("Integrity detects dangling evidence ref",
      any(i["type"] == "dangling_evidence_reference" for i in integrity["issues"]),
      f"issues: {[i['type'] for i in integrity['issues']]}")
check("Integrity detects dangling fact ref",
      any(i["type"] == "dangling_fact_reference" for i in integrity["issues"]))
check("Integrity detects unreferenced authority",
      any(i["type"] == "unreferenced_authority" for i in integrity["issues"]))
check("Integrity marks case as invalid", not integrity["valid"])

# Run contradiction detection
contras = fail_case.detect_contradictions()
check("Contradiction engine detects contradicted fact",
      any(c["type"] == "fact_status" for c in contras),
      f"contradictions: {[c['type'] for c in contras]}")

# Test sufficiency with no evidence
fail_case.add_sufficiency_rule(
    rule_name="Empty test rule",
    claim_description="Claim with no evidence",
    required_documents=["Nonexistent document 1", "Nonexistent document 2"],
    minimum_required=2,
)
evals = fail_case.evaluate_sufficiency()
check("Sufficiency correctly shows NOT SATISFIED",
      all(not e["satisfied"] for e in evals),
      f"results: {[(e['rule_id'], e['satisfied']) for e in evals]}")

print(f"\nObjective 2: {PASS - obj2_pass_before} passed, {FAIL - (FAIL)} failed\n")


# ════════════════════════════════════════════════════════════════════
# OBJECTIVE 3: Renderer Parity
# ════════════════════════════════════════════════════════════════════

print("=" * 60)
print("OBJECTIVE 3: Renderer Parity")
print("=" * 60)

obj3_pass_before = PASS
test_case = created_cases[0]  # TEST-001

packet = test_case.generate_packet()
timeline = test_case.render("timeline")
exhibit = test_case.render("exhibit_index")
evidence_log = test_case.render("evidence_log")
demand = test_case.render("demand_letter")

# Check fact appears in packet and demand letter
reg = test_case._load_json(test_case.registry_path)
ev_id = reg["evidence_items"][0]["evidence_id"]
check("Evidence ID in packet", ev_id in packet)
check("Evidence ID in exhibit index", ev_id in exhibit)
check("Evidence ID in evidence log", ev_id in evidence_log)

facts = test_case._load_json(test_case.fact_ledger_path)
fact_text = facts["facts"][0]["fact"]
check("Fact text in packet", fact_text in packet)
check("Fact text in demand letter", fact_text in demand)

# Check timeline has chronology events
chron = test_case._load_json(test_case.chronology_path)
if chron["events"]:
    event_text = chron["events"][0]["event"]
    check("Chronology event in timeline", event_text in timeline)

print(f"\nObjective 3: {PASS - obj3_pass_before} passed\n")


# ════════════════════════════════════════════════════════════════════
# OBJECTIVE 4: Performance Test
# ════════════════════════════════════════════════════════════════════

print("=" * 60)
print("OBJECTIVE 4: Performance Test")
print("=" * 60)

obj4_pass_before = PASS
cleanup_case("TEST-PERF-001")
perf_case = CaseTemplate(case_id="TEST-PERF-001", case_name="Performance Test")

# Register 500 evidence items (batch mode for performance)
start = time.time()
for i in range(500):
    perf_case.register_evidence(
        text_content=f"Performance test evidence item {i}",
        title=f"Perf Doc {i}",
        description=f"Performance test document number {i}",
        source="Performance Test",
        folder="06_Evidence",
        _skip_save=True,
    )
perf_case.flush_registry()
register_time = time.time() - start
check("500 evidence items registered", len(perf_case._load_json(perf_case.registry_path)["evidence_items"]) == 500)
check("Registration time < 30s", register_time < 30, f"took {register_time:.1f}s")

# Test readiness calculation
start = time.time()
readiness = perf_case.calculate_readiness()
readiness_time = time.time() - start
check("Readiness calculated for 500 items", readiness["overall_readiness"] >= 0)
check("Readiness calculation < 5s", readiness_time < 5, f"took {readiness_time:.1f}s")

# Test integrity validation
start = time.time()
integrity = perf_case.validate_integrity()
integrity_time = time.time() - start
check("Integrity validation for 500 items", "issue_count" in integrity)
check("Integrity validation < 10s", integrity_time < 10, f"took {integrity_time:.1f}s")

print(f"\nObjective 4: {PASS - obj4_pass_before} passed\n")


# ════════════════════════════════════════════════════════════════════
# CLEANUP & SUMMARY
# ════════════════════════════════════════════════════════════════════

# Clean up test cases
for tc in test_cases:
    cleanup_case(tc["id"])
cleanup_case("TEST-FAIL-001")
cleanup_case("TEST-PERF-001")

print("=" * 60)
print("STRESS TEST SUMMARY")
print("=" * 60)
print(f"Total: {PASS} passed, {FAIL} failed")
print(f"Kernel version: {KERNEL_VERSION}")
print()
if FAIL == 0:
    print("RELEASE CRITERIA: ALL PASSED")
    print("CaseTemplate v2.1.0 RC1 is ready for promotion to stable release.")
else:
    print(f"RELEASE CRITERIA: {FAIL} FAILURES - do not promote yet")
    for r in RESULTS:
        if r.startswith("FAIL"):
            print(f"  {r}")

# Write results to file
results_path = Path(r"C:\Users\admin\Desktop\SintraPrime-Unified\evidence\stress_test_results.json")
results_path.write_text(json.dumps({
    "kernel_version": KERNEL_VERSION,
    "total_pass": PASS,
    "total_fail": FAIL,
    "results": RESULTS,
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "release_ready": FAIL == 0,
}, indent=2), encoding="utf-8")
print(f"\nResults saved to: {results_path}")