"""
Client C-0001 UACC Fixture - Evidence Command Center Validation

This script generates exhibits and readiness report for the UACC test case
using the Evidence Command Center models.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages"))

from evidence_command_center import (
    EvidenceRegistry,
    ViolationRegistry,
    ExhibitRegistry,
    Evidence,
    Violation,
    Exhibit,
    Statute,
    Severity,
    EvidenceStatus,
    ViolationStatus,
    calculate_readiness_score,
    create_exhibit_id,
)


def load_fixture_data(base_path: Path):
    """Load fixture JSON files"""
    with open(base_path / "evidence_manifest.json") as f:
        evidence_data = json.load(f)
    with open(base_path / "violation_candidates.json") as f:
        violation_data = json.load(f)
    return evidence_data, violation_data


def register_evidence(evidence_data: dict, evidence_registry: EvidenceRegistry):
    """Register all evidence items from fixture"""
    case_id = evidence_data["case_id"]
    
    for item in evidence_data["evidence_items"]:
        # Map fixture fields to Evidence model fields
        evidence = Evidence(
            evidence_id=item["evidence_id"],
            case_id=case_id,
            source_type=item["source"],
            date_acquired=item["acquisition_date"],
            sha256_hash=item.get("hash", ""),
            category=item["category"],
            status=EvidenceStatus.APPROVED if item["status"] == "verified" else EvidenceStatus.REJECTED,
            file_name=item.get("file_location", ""),
            metadata=item.get("metadata", {}),
        )
        evidence_registry.add(evidence)
    return evidence_registry


def register_violations(violation_data: dict, violation_registry: ViolationRegistry):
    """Register all violation candidates from fixture"""
    case_id = violation_data.get("case_id", "CASE-UACC-2026-001")
    
    for item in violation_data["violations"]:
        # Map statute string to enum
        statute_map = {
            "UCC": Statute.UCC,
            "FCRA": Statute.FCRA,
            "FDCPA": Statute.FDCPA,
            "TCPA": Statute.TCPA,
            "RESPA": Statute.RESPA,
            "TILA": Statute.TILA,
            "ECOA": Statute.ECOA,
        }
        
        # Map severity
        severity_map = {
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
        }
        
        # Map status
        status_map = {
            "candidate": ViolationStatus.DETECTED,
            "future_investigation": ViolationStatus.DETECTED,
        }
        
        violation = Violation(
            violation_id=item["violation_id"],
            case_id=case_id,
            client_id="C-0001",
            statute=statute_map.get(item["statute"], Statute.OTHER),
            statute_full_name=item["statute"],
            statute_citation=f"{item['statute']} {item.get('section', '')}",
            subsection=item.get("section"),
            violation_type=item.get("category", ""),
            violation_description=item["description"],
            severity=severity_map.get(item["severity"], Severity.MEDIUM),
            linked_evidence=item.get("supporting_evidence", []),
            status=status_map.get(item.get("status", "candidate"), ViolationStatus.DETECTED),
            ai_detected=True,
            ai_confidence=item.get("confidence"),
            ai_analysis={"legal_basis": item.get("legal_basis", ""), "notes": item.get("notes", "")},
            remedy_notes=item.get("potential_remedy"),
        )
        violation_registry.add(violation)
    return violation_registry


def generate_exhibits(
    evidence_registry: EvidenceRegistry, exhibit_registry: ExhibitRegistry, case_id: str
):
    """Generate exhibits from verified evidence"""
    # Get all evidence for the case
    all_evidence = evidence_registry.get_by_case(case_id)
    verified_evidence = [e for e in all_evidence if e.status == EvidenceStatus.APPROVED]

    year = datetime.now().year
    
    for idx, evidence in enumerate(verified_evidence, start=1):
        # Standard exhibit numbering: Exhibit A, B, C, etc.
        exhibit_letter = chr(64 + idx)  # A=65, B=66, etc.
        exhibit_number = f"Exhibit {exhibit_letter}"
        
        exhibit = Exhibit(
            exhibit_id=create_exhibit_id(case_id, year, idx),
            case_id=case_id,
            evidence_id=evidence.evidence_id,
            exhibit_number=exhibit_number,
            exhibit_title=evidence.metadata.get("document_type", "Evidence"),
            exhibit_description=evidence.file_name or f"Evidence {evidence.evidence_id}",
            page_count=evidence.metadata.get("page_count", 0),
            sequence_number=idx,
        )
        
        exhibit_registry.add(exhibit)

    return exhibit_registry


def generate_readiness_report(
    case_id: str,
    evidence_registry: EvidenceRegistry,
    violation_registry: ViolationRegistry,
    exhibit_registry: ExhibitRegistry,
):
    """Generate comprehensive case readiness report"""

    # Calculate readiness score
    all_evidence = evidence_registry.get_by_case(case_id)
    all_violations = violation_registry.get_by_case(case_id)
    all_exhibits = exhibit_registry.get_by_case(case_id)
    
    readiness = calculate_readiness_score(
        evidence_items=all_evidence,
        violations=all_violations,
        exhibits=all_exhibits,
        required_evidence_categories=["contract", "financial_records", "correspondence", "credit_report"],
    )
    
    return readiness, all_evidence, all_violations, all_exhibits


def build_full_report(
    case_id: str,
    readiness: "ReadinessScore",
    all_evidence: List[Evidence],
    all_violations: List[Violation],
    all_exhibits: List["Exhibit"],
):
    """Build full readiness report from component data"""

    # Build report
    verified_count = len([e for e in all_evidence if e.status == EvidenceStatus.APPROVED])
    missing_count = len([e for e in all_evidence if e.status == EvidenceStatus.REJECTED])
    
    high_severity = len([v for v in all_violations if v.severity == Severity.HIGH])
    medium_severity = len([v for v in all_violations if v.severity == Severity.MEDIUM])
    low_severity = len([v for v in all_violations if v.severity == Severity.LOW])
    
    report = {
        "case_id": case_id,
        "generated_date": datetime.now().isoformat(),
        "overall_readiness_score": readiness.overall_score,
        "readiness_level": readiness.readiness_level,
        "component_scores": {
            "evidence_completeness": readiness.evidence_completeness,
            "violation_support": readiness.violation_support,
            "chain_of_custody": readiness.chain_of_custody,
            "timeline_completeness": readiness.timeline_completeness,
            "document_quality": readiness.document_quality,
        },
        "evidence_summary": {
            "total_evidence": len(all_evidence),
            "verified": verified_count,
            "missing": missing_count,
            "partial": 0,
        },
        "violation_summary": {
            "total_violations": len(all_violations),
            "high_severity": high_severity,
            "medium_severity": medium_severity,
            "low_severity": low_severity,
            "by_statute": {},
        },
        "exhibit_summary": {
            "total_exhibits": len(all_exhibits),
            "exhibits": [
                {
                    "exhibit_number": ex.exhibit_number,
                    "description": ex.exhibit_description,
                    "evidence_count": 1,
                }
                for ex in all_exhibits
            ],
        },
        "readiness_analysis": {
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
        },
        "missing_evidence_impact": readiness.gaps,
        "violation_support_analysis": readiness.recommendations,
    }

    # Statute breakdown
    for violation in all_violations:
        statute = violation.statute.value
        report["violation_summary"]["by_statute"][statute] = (
            report["violation_summary"]["by_statute"].get(statute, 0) + 1
        )

    # Analyze strengths and weaknesses
    if report["component_scores"]["evidence_completeness"] >= 70:
        report["readiness_analysis"]["strengths"].append(
            "Strong evidence collection and documentation"
        )
    else:
        report["readiness_analysis"]["weaknesses"].append(
            f"Evidence collection incomplete ({report['component_scores']['evidence_completeness']:.1f}%)"
        )

    if report["component_scores"]["violation_support"] >= 70:
        report["readiness_analysis"]["strengths"].append(
            "Violations well-supported by evidence"
        )
    else:
        report["readiness_analysis"]["weaknesses"].append(
            "Violation claims need stronger evidence support"
        )

    if report["component_scores"]["chain_of_custody"] >= 70:
        report["readiness_analysis"]["strengths"].append(
            "Chain of custody properly maintained"
        )
    else:
        report["readiness_analysis"]["weaknesses"].append(
            "Chain of custody concerns present"
        )

    # Recommendations
    if report["evidence_summary"]["missing"] > 0:
        report["readiness_analysis"]["recommendations"].append(
            f"Obtain {report['evidence_summary']['missing']} missing evidence items"
        )

    if report["overall_readiness_score"] < 70:
        report["readiness_analysis"]["recommendations"].append(
            "Case not yet ready for formal dispute or litigation - continue evidence collection"
        )
    elif report["overall_readiness_score"] < 85:
        report["readiness_analysis"]["recommendations"].append(
            "Case operational for settlement negotiations - strengthen evidence before litigation"
        )
    else:
        report["readiness_analysis"]["recommendations"].append(
            "Case litigation-ready - proceed with formal dispute or court filing"
        )

    return report


def main():
    """Main execution"""
    # Paths
    fixture_path = Path(__file__).parent
    output_path = fixture_path / "readiness_report.json"
    exhibit_path = fixture_path / "exhibit_manifest.json"

    # Load fixture data
    print("Loading UACC fixture data...")
    evidence_data, violation_data = load_fixture_data(fixture_path)

    # Initialize registries
    evidence_registry = EvidenceRegistry()
    violation_registry = ViolationRegistry()
    exhibit_registry = ExhibitRegistry()

    # Register evidence
    print("Registering evidence...")
    register_evidence(evidence_data, evidence_registry)

    # Register violations
    print("Registering violations...")
    register_violations(violation_data, violation_registry)

    # Generate exhibits
    print("Generating exhibits...")
    generate_exhibits(evidence_registry, exhibit_registry, "CASE-UACC-2026-001")

    # Generate readiness report
    print("Calculating readiness score...")
    readiness, all_evidence, all_violations, all_exhibits = generate_readiness_report(
        case_id="CASE-UACC-2026-001",
        evidence_registry=evidence_registry,
        violation_registry=violation_registry,
        exhibit_registry=exhibit_registry,
    )
    
    # Build full report
    readiness_report = build_full_report(
        "CASE-UACC-2026-001",
        readiness,
        all_evidence,
        all_violations,
        all_exhibits
    )

    # Save exhibit manifest
    print(f"Saving exhibit manifest to {exhibit_path}...")
    exhibit_manifest = {
        "case_id": "CASE-UACC-2026-001",
        "exhibit_count": len(all_exhibits),
        "exhibits": [
            {
                "exhibit_number": ex.exhibit_number,
                "evidence_ids": [ex.evidence_id],
                "description": ex.exhibit_description,
                "page_count": ex.page_count,
                "hash": "",
            }
            for ex in all_exhibits
        ],
    }
    with open(exhibit_path, "w") as f:
        json.dump(exhibit_manifest, f, indent=2)

    # Save readiness report
    print(f"Saving readiness report to {output_path}...")
    with open(output_path, "w") as f:
        json.dump(readiness_report, f, indent=2)

    # Display summary
    print("\n" + "=" * 60)
    print("UACC CASE READINESS SUMMARY")
    print("=" * 60)
    print(f"Case ID: {readiness_report['case_id']}")
    print(f"Overall Readiness: {readiness_report['overall_readiness_score']:.1f}/100")
    print(f"Readiness Level: {readiness_report['readiness_level']}")
    print()
    print("Component Scores:")
    for component, score in readiness_report["component_scores"].items():
        print(f"  {component.replace('_', ' ').title()}: {score:.1f}%")
    print()
    print(f"Evidence: {readiness_report['evidence_summary']['verified']} verified, "
          f"{readiness_report['evidence_summary']['missing']} missing")
    print(f"Violations: {readiness_report['violation_summary']['total_violations']} total, "
          f"{readiness_report['violation_summary']['high_severity']} high severity")
    print(f"Exhibits: {readiness_report['exhibit_summary']['total_exhibits']} generated")
    print()
    print("Recommendations:")
    for rec in readiness_report["readiness_analysis"]["recommendations"]:
        print(f"  • {rec}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
