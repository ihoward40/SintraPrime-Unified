"""Evidence Command Center - Exhibit Utilities

Utilities for creating court-ready exhibits from evidence.

Status: MVP (design validation)
Created: 2026-06-14
"""

from typing import List
from .models import Evidence, Exhibit, generate_exhibit_number
from .registry import ExhibitRegistry


def create_exhibit_from_evidence(
    evidence: Evidence,
    case_id: str,
    exhibit_registry: ExhibitRegistry,
    exhibit_prefix: str = None,
    label_format: str = "LETTER",
    bates_prefix: str = None
) -> Exhibit:
    """
    Create court-ready exhibit from evidence.
    
    Args:
        evidence: Source evidence item
        case_id: Case ID
        exhibit_registry: Registry to track exhibit
        exhibit_prefix: Optional prefix (e.g., "Plaintiff")
        label_format: LETTER, NUMBER, PREFIX_LETTER, PREFIX_NUMBER
        bates_prefix: Optional Bates numbering prefix
    
    Returns:
        Created Exhibit
    """
    # Generate IDs and numbers
    exhibit_id = exhibit_registry.generate_id(case_id)
    sequence_number = exhibit_registry.get_next_sequence_number(case_id)
    exhibit_number = generate_exhibit_number(sequence_number, label_format, exhibit_prefix)
    
    # Create exhibit title from evidence
    if evidence.category == "credit_report":
        title = f"{evidence.subcategory or 'Credit'} Credit Report"
    elif evidence.category == "collection_letter":
        title = "Collection Letter"
    elif evidence.category == "contract":
        title = "Contract Agreement"
    else:
        title = evidence.file_name or "Evidence Document"
    
    # Add date if available
    if evidence.metadata.get("report_date"):
        title += f" dated {evidence.metadata['report_date']}"
    elif evidence.date_acquired:
        title += f" acquired {evidence.date_acquired[:10]}"
    
    # Create description from evidence metadata
    description = evidence.metadata.get("ai_summary", "")
    if not description and evidence.category:
        description = f"{evidence.category.replace('_', ' ').title()} supporting case allegations"
    
    # Calculate Bates numbering if prefix provided
    bates_start = None
    bates_end = None
    bates_numbering = False
    
    if bates_prefix and evidence.metadata.get("pages"):
        page_count = evidence.metadata["pages"]
        # Get last Bates number used in case
        existing_exhibits = exhibit_registry.get_by_case(case_id)
        last_bates = max(
            (ex.bates_end for ex in existing_exhibits if ex.bates_end),
            default=0
        )
        bates_start = last_bates + 1
        bates_end = bates_start + page_count - 1
        bates_numbering = True
    
    # Create exhibit
    exhibit = Exhibit(
        exhibit_id=exhibit_id,
        case_id=case_id,
        evidence_id=evidence.evidence_id,
        exhibit_number=exhibit_number,
        exhibit_label_format=label_format,
        sequence_number=sequence_number,
        exhibit_prefix=exhibit_prefix,
        exhibit_title=title,
        exhibit_description=description,
        page_count=evidence.metadata.get("pages", 0),
        file_format="PDF",
        storage_key=f"exhibits/{case_id}/{exhibit_id}/Exhibit_{exhibit_number}.pdf",
        original_storage_key=evidence.storage_key,
        bates_numbering=bates_numbering,
        bates_prefix=bates_prefix,
        bates_start=bates_start,
        bates_end=bates_end,
        bates_format=f"{{{bates_prefix}-{{number:04d}}}}" if bates_prefix else None,
        status="FORMATTED",
        created_by=evidence.created_by
    )
    
    # Add to registry
    exhibit_registry.add(exhibit)
    
    return exhibit


def batch_create_exhibits(
    evidence_items: List[Evidence],
    case_id: str,
    exhibit_registry: ExhibitRegistry,
    exhibit_prefix: str = None,
    label_format: str = "LETTER",
    bates_prefix: str = None
) -> List[Exhibit]:
    """
    Create exhibits from multiple evidence items.
    
    Args:
        evidence_items: List of evidence to convert
        case_id: Case ID
        exhibit_registry: Registry to track exhibits
        exhibit_prefix: Optional prefix
        label_format: Numbering format
        bates_prefix: Optional Bates prefix
    
    Returns:
        List of created exhibits
    """
    exhibits = []
    
    for evidence in evidence_items:
        exhibit = create_exhibit_from_evidence(
            evidence=evidence,
            case_id=case_id,
            exhibit_registry=exhibit_registry,
            exhibit_prefix=exhibit_prefix,
            label_format=label_format,
            bates_prefix=bates_prefix
        )
        exhibits.append(exhibit)
    
    return exhibits


def generate_exhibit_manifest(exhibits: List[Exhibit]) -> str:
    """
    Generate table of exhibits for court filing.
    
    Args:
        exhibits: List of exhibits (will be sorted by sequence)
    
    Returns:
        Formatted table of exhibits text
    """
    if not exhibits:
        return "TABLE OF EXHIBITS\n\n(No exhibits)"
    
    lines = ["TABLE OF EXHIBITS\n"]
    lines.append(f"{'Exhibit':<10} | {'Description':<50} | {'Pages':<10}")
    lines.append("-" * 75)
    
    page_offset = 1
    
    for exhibit in sorted(exhibits, key=lambda e: e.sequence_number):
        if exhibit.page_count > 0:
            page_end = page_offset + exhibit.page_count - 1
            page_range = f"{page_offset}-{page_end}"
            page_offset = page_end + 1
        else:
            page_range = "N/A"
        
        # Truncate description if too long
        desc = exhibit.exhibit_title
        if len(desc) > 50:
            desc = desc[:47] + "..."
        
        lines.append(
            f"{exhibit.exhibit_number:<10} | {desc:<50} | {page_range:<10}"
        )
    
    return "\n".join(lines)


def get_exhibit_stats(exhibits: List[Exhibit]) -> dict:
    """
    Get statistics about exhibits.
    
    Returns:
        Dictionary with exhibit statistics
    """
    if not exhibits:
        return {
            "total_exhibits": 0,
            "total_pages": 0,
            "bates_range": None,
            "formats": []
        }
    
    total_pages = sum(ex.page_count for ex in exhibits)
    
    bates_exhibits = [ex for ex in exhibits if ex.bates_numbering]
    if bates_exhibits:
        min_bates = min(ex.bates_start for ex in bates_exhibits if ex.bates_start)
        max_bates = max(ex.bates_end for ex in bates_exhibits if ex.bates_end)
        bates_prefix = bates_exhibits[0].bates_prefix
        bates_range = f"{bates_prefix}-{min_bates:04d} to {bates_prefix}-{max_bates:04d}"
    else:
        bates_range = None
    
    formats = list(set(ex.file_format for ex in exhibits))
    
    return {
        "total_exhibits": len(exhibits),
        "total_pages": total_pages,
        "bates_range": bates_range,
        "formats": formats
    }
