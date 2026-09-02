"""Permanent identity FK type consistency gate (Section 16 of Principal directive).

CI should fail when parent identity domain != child FK identity domain.
Blocks: String(36)→PortableUUID, PortableUUID→String(36), UUID→VARCHAR, VARCHAR→UUID
where they represent the same database FK relationship.
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _extract_identity_columns(module_path: str) -> list[dict]:
    """Extract identity column definitions from a Python module using AST."""
    results = []
    full_path = REPO / module_path
    if not full_path.exists():
        return results

    content = full_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return results

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        class_name = node.name
        for child in ast.walk(node):
            if isinstance(child, ast.AnnAssign) and hasattr(child, "target"):
                attr_name = ""
                if isinstance(child.target, ast.Name):
                    attr_name = child.target.id
                elif isinstance(child.target, ast.Attribute):
                    attr_name = child.target.attr

                if attr_name not in ("id", "tenant_id", "user_id", "principal_id",
                                     "matter_id", "case_id", "client_id", "document_id",
                                     "agent_id", "service_id", "run_id", "mission_id",
                                     "approval_id"):
                    continue

                if isinstance(child.value, ast.Call):
                    call_str = ast.unparse(child.value) if hasattr(ast, "unparse") else ""
                    if "mapped_column" in call_str or "Column" in call_str:
                        # Determine column type
                        col_type = "unknown"
                        if "PortableUUID" in call_str:
                            col_type = "PortableUUID"
                        elif "UUID(as_uuid" in call_str:
                            col_type = "UUID"
                        elif "String(36)" in call_str:
                            col_type = "String(36)"
                        elif "String(128)" in call_str:
                            col_type = "String(128)"

                        # Check if it has a ForeignKey
                        has_fk = "ForeignKey" in call_str
                        fk_target = ""
                        if has_fk:
                            # Extract FK target
                            for n in ast.walk(child.value):
                                if isinstance(n, ast.Constant) and isinstance(n.value, str):
                                    if "." in n.value and ("tenants" in n.value or "users" in n.value):
                                        fk_target = n.value

                        results.append({
                            "file": module_path,
                            "class": class_name,
                            "attribute": attr_name,
                            "type": col_type,
                            "has_fk": has_fk,
                            "fk_target": fk_target,
                        })
    return results


def test_no_string36_identity_columns_remain() -> None:
    """No identity columns should use String(36) after PortableUUID migration.

    This test will start failing once Worker B converts all columns.
    It serves as a permanent gate against regression.
    """
    model_files = [
        "portal/models/user.py",
        "portal/models/audit.py",
        "portal/models/billing.py",
        "portal/models/case.py",
        "portal/models/client.py",
        "portal/models/document.py",
        "portal/models/message.py",
        "portal/models/mission_control_command.py",
        "portal/models/mission_control_execution.py",
        "portal/models/mission_control_outbox.py",
        "portal/models/mission_control_run_approval.py",
        "portal/models/mission_control_run_control.py",
        "portal/models/orchestration.py",
        "portal/models/tenant_principal.py",
    ]

    violations: list[str] = []

    for mf in model_files:
        cols = _extract_identity_columns(mf)
        for col in cols:
            if col["type"] == "String(36)" and col["attribute"] in ("id", "tenant_id", "user_id"):
                violations.append(
                    f"{col['file']}::{col['class']}.{col['attribute']} "
                    f"still uses String(36) — should be PortableUUID"
                )

    if violations:
        pytest.fail(
            f"IDENTITY_FK_TYPE_DRIFT detected — {len(violations)} identity columns "
            f"still use String(36):\n" + "\n".join(violations)
        )


def test_no_uuid_as_uuid_identity_columns_remain() -> None:
    """No identity columns should use raw UUID(as_uuid=True) after migration.

    PortableUUID handles dialect-awareness. Raw UUID(as_uuid=True) is
    PostgreSQL-only and breaks SQLite compatibility.
    """
    model_files = [
        "portal/models/user.py",
        "portal/models/audit.py",
        "portal/models/billing.py",
        "portal/models/case.py",
        "portal/models/client.py",
        "portal/models/document.py",
        "portal/models/message.py",
    ]

    # Also check routers for inline models
    router_files = [
        "portal/routers/notifications.py",
    ]

    violations: list[str] = []

    for mf in model_files + router_files:
        cols = _extract_identity_columns(mf)
        for col in cols:
            if col["type"] == "UUID" and col["attribute"] in ("id", "tenant_id", "user_id"):
                violations.append(
                    f"{col['file']}::{col['class']}.{col['attribute']} "
                    f"uses UUID(as_uuid=True) — should be PortableUUID"
                )

    if violations:
        pytest.fail(
            f"IDENTITY_FK_TYPE_DRIFT detected — {len(violations)} identity columns "
            f"use raw UUID(as_uuid=True) instead of PortableUUID:\n" + "\n".join(violations)
        )


def test_tenant_fk_type_consistency() -> None:
    """All FKs targeting tenants.id must use the same type as Tenant.id."""
    # After migration, Tenant.id should be PortableUUID
    # All child tenant_id FKs should also be PortableUUID
    all_files = [
        "portal/models/user.py",
        "portal/models/audit.py",
        "portal/models/billing.py",
        "portal/models/case.py",
        "portal/models/client.py",
        "portal/models/document.py",
        "portal/models/message.py",
        "portal/models/mission_control_command.py",
        "portal/models/tenant_principal.py",
        "portal/routers/notifications.py",
    ]

    all_cols: list[dict] = []
    for mf in all_files:
        all_cols.extend(_extract_identity_columns(mf))

    # Find Tenant.id type
    tenant_id_type = None
    for col in all_cols:
        if col["class"] == "Tenant" and col["attribute"] == "id":
            tenant_id_type = col["type"]
            break

    if tenant_id_type is None:
        pytest.skip("Tenant.id not found — model may not be loaded")

    if tenant_id_type == "unknown":
        pytest.skip("Tenant.id type could not be determined")

    # Check all FKs targeting tenants.id
    tenant_fks = [c for c in all_cols if c["has_fk"] and "tenants" in c.get("fk_target", "")]
    mismatches = []
    for fk in tenant_fks:
        if fk["type"] != tenant_id_type and fk["type"] != "unknown":
            mismatches.append(
                f"{fk['file']}::{fk['class']}.{fk['attribute']} "
                f"type={fk['type']} != Tenant.id type={tenant_id_type}"
            )

    if mismatches:
        pytest.fail(
            f"TENANT_FK_TYPE_DRIFT — {len(mismatches)} FKs have mismatched types:\n"
            + "\n".join(mismatches)
        )


def test_user_fk_type_consistency() -> None:
    """All FKs targeting users.id must use the same type as User.id."""
    all_files = [
        "portal/models/user.py",
        "portal/models/audit.py",
        "portal/models/billing.py",
        "portal/models/case.py",
        "portal/models/client.py",
        "portal/models/document.py",
        "portal/models/message.py",
        "portal/models/mission_control_command.py",
        "portal/routers/notifications.py",
    ]

    all_cols: list[dict] = []
    for mf in all_files:
        all_cols.extend(_extract_identity_columns(mf))

    # Find User.id type
    user_id_type = None
    for col in all_cols:
        if col["class"] == "User" and col["attribute"] == "id":
            user_id_type = col["type"]
            break

    if user_id_type is None:
        pytest.skip("User.id not found")

    if user_id_type == "unknown":
        pytest.skip("User.id type could not be determined")

    # Check all FKs targeting users.id
    user_fks = [c for c in all_cols if c["has_fk"] and "users" in c.get("fk_target", "")]
    mismatches = []
    for fk in user_fks:
        if fk["type"] != user_id_type and fk["type"] != "unknown":
            mismatches.append(
                f"{fk['file']}::{fk['class']}.{fk['attribute']} "
                f"type={fk['type']} != User.id type={user_id_type}"
            )

    if mismatches:
        pytest.fail(
            f"USER_FK_TYPE_DRIFT — {len(mismatches)} FKs have mismatched types:\n"
            + "\n".join(mismatches)
        )
