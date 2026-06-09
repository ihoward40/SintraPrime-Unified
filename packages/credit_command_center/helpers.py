"""Helper utilities for the Credit Command Center.

Includes folder naming conventions, scorecard rating, and receipt creation.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from .models import ActionReceipt, Scorecard, ScorecardRating


def normalize_client_name(name: str) -> str:
    """Convert a client name to a filesystem-safe slug.

    Examples:
        "Isiah Howard" -> "isiah-howard"
        "John  Doe"    -> "john-doe"
        "Alice-Bob"    -> "alice-bob"
    """
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def build_case_folder_path(base_dir: str, client_name: str) -> str:
    """Build the root folder path for a client's case.

    Args:
        base_dir: Root directory for all client cases (e.g. "clients").
        client_name: Full client name.

    Returns:
        Absolute folder path string.
    """
    slug = normalize_client_name(client_name)
    return f"{base_dir}/{slug}"


def build_evidence_folder_path(base_dir: str, client_name: str, subfolder: str) -> str:
    """Build a subfolder path within a client's case directory.

    Args:
        base_dir: Root directory for all client cases.
        client_name: Full client name.
        subfolder: One of: intake, credit-reports, disputes, correspondence,
                   evidence, output.

    Returns:
        Absolute folder path string.
    """
    case_root = build_case_folder_path(base_dir, client_name)
    return f"{case_root}/{subfolder}"


def rate_scorecard(scorecard: Scorecard) -> ScorecardRating:
    """Derive the overall rating from a Scorecard.

    Delegates to Scorecard.rating for consistency.
    """
    return scorecard.rating


def create_receipt(
    case_id: str,
    actor: str,
    action: str,
    details: dict | None = None,
    file_path: str | None = None,
    receipt_id: str | None = None,
) -> ActionReceipt:
    """Create an ActionReceipt with auto-generated timestamp.

    Args:
        case_id: The case this receipt belongs to.
        actor: Who performed the action (Hermes / Isiah / System).
        action: Action verb (e.g. intake_received, document_cataloged).
        details: Optional dict with action-specific data.
        file_path: Optional path to a file read or written.
        receipt_id: Optional explicit ID. Auto-generated if omitted.

    Returns:
        A fully populated ActionReceipt.
    """
    if receipt_id is None:
        ts = datetime.now(UTC)
        receipt_id = f"R-{ts.strftime('%Y%m%d%H%M%S')}"

    return ActionReceipt(
        receipt_id=receipt_id,
        case_id=case_id,
        actor=actor,
        action=action,
        details=details or {},
        file_path=file_path,
    )
