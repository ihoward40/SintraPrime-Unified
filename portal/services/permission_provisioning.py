"""Deterministic Mission Control permission provisioning."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..auth.rbac import Permission, ROLE_PERMISSIONS, Role
from ..models.user import Permission as PermissionModel
from ..models.user import Role as RoleModel
from ..models.user import RolePermission

MANIFEST_SCHEMA_VERSION = 1

MISSION_CONTROL_PERMISSION_PREFIX = "mission_control:"
MUTATION_PERMISSIONS = {
    Permission.MISSION_COMMAND_CREATE.value,
    Permission.MISSION_RUN_PAUSE.value,
}


class PermissionSyncError(RuntimeError):
    """Raised when a reconcile request cannot safely proceed."""


class DriftSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    BLOCKING = "BLOCKING"


class SyncMode(StrEnum):
    VERIFY = "VERIFY"
    DRY_RUN = "DRY_RUN"
    RECONCILE = "RECONCILE"


@dataclass(slots=True)
class PermissionSyncReport:
    manifest_hash: str
    drift_detected: bool
    severity: DriftSeverity = DriftSeverity.INFO
    mode: SyncMode = SyncMode.VERIFY
    manifest_schema_version: int = MANIFEST_SCHEMA_VERSION
    current_state: dict[str, Any] = field(default_factory=dict)
    proposed_state: dict[str, Any] = field(default_factory=dict)
    permission_missing: list[str] = field(default_factory=list)
    permission_extra: list[str] = field(default_factory=list)
    role_grant_missing: dict[str, list[str]] = field(default_factory=dict)
    role_grant_extra: dict[str, list[str]] = field(default_factory=dict)
    ambiguous_roles: list[str] = field(default_factory=list)
    unknown_roles: list[str] = field(default_factory=list)
    permissions_created: int = 0
    permissions_unchanged: int = 0
    permissions_removed: int = 0
    permissions_failed: int = 0
    role_grants_created: int = 0
    role_grants_unchanged: int = 0
    role_grants_removed: int = 0
    role_grants_failed: int = 0
    created_records: list[str] = field(default_factory=list)
    unchanged_records: list[str] = field(default_factory=list)
    removed_records: list[str] = field(default_factory=list)
    failed_records: list[str] = field(default_factory=list)

    @property
    def permissions_missing(self) -> list[str]:
        return self.permission_missing

    @property
    def permissions_extra(self) -> list[str]:
        return self.permission_extra

    @property
    def role_grants_missing(self) -> dict[str, list[str]]:
        return self.role_grant_missing

    @property
    def role_grants_extra(self) -> dict[str, list[str]]:
        return self.role_grant_extra


@dataclass(frozen=True, slots=True)
class PermissionManifest:
    schema_version: int
    permissions: tuple[str, ...]
    roles: dict[str, tuple[str, ...]]


verify_permission_manifest = inspect_permission_manifest = None  # type: ignore[assignment]
plan_permission_manifest = None  # type: ignore[assignment]


async def inspect_permission_manifest(db: AsyncSession) -> PermissionSyncReport:
    """Read-only verification of the canonical manifest against persistence."""
    return await _reconcile_permission_manifest(db, apply_changes=False, mode=SyncMode.VERIFY)


async def plan_permission_manifest(db: AsyncSession) -> PermissionSyncReport:
    """Dry-run reconciliation that computes the exact proposed changes."""
    return await _reconcile_permission_manifest(db, apply_changes=False, mode=SyncMode.DRY_RUN)


async def sync_permission_manifest(db: AsyncSession) -> PermissionSyncReport:
    """Explicit trusted reconciliation of the canonical manifest."""
    return await _reconcile_permission_manifest(db, apply_changes=True, mode=SyncMode.RECONCILE)


verify_permission_manifest = inspect_permission_manifest


def canonical_permission_manifest() -> PermissionManifest:
    permissions = tuple(sorted(permission.value for permission in Permission))
    roles = {
        role.value: tuple(sorted(permission.value for permission in ROLE_PERMISSIONS[role]))
        for role in Role
    }
    return PermissionManifest(schema_version=MANIFEST_SCHEMA_VERSION, permissions=permissions, roles=roles)


def canonical_manifest_hash() -> str:
    return _sha256_json(_canonical_manifest_payload())


async def _reconcile_permission_manifest(
    db: AsyncSession,
    *,
    apply_changes: bool,
    mode: SyncMode,
) -> PermissionSyncReport:
    manifest = _canonical_manifest_payload()
    manifest_hash = _sha256_json(manifest)

    permission_rows = (await db.execute(select(PermissionModel))).scalars().all()
    role_rows = (
        await db.execute(
            select(RoleModel)
            .options(selectinload(RoleModel.permissions))
            .order_by(RoleModel.name.asc())
        )
    ).scalars().all()

    current_permissions = {row.name: row for row in permission_rows}
    current_roles = {row.name: row for row in role_rows}
    current_grants = {
        role.name: {permission.name for permission in role.permissions}
        for role in role_rows
    }

    report = PermissionSyncReport(
        manifest_hash=manifest_hash,
        drift_detected=False,
        mode=mode,
        current_state=_build_state_snapshot(current_permissions, current_grants, current_roles),
        proposed_state=_build_proposed_state_snapshot(manifest),
    )

    desired_permissions = set(manifest["permissions"])
    current_permission_names = set(current_permissions)
    report.permission_missing = sorted(desired_permissions - current_permission_names)
    report.permission_extra = sorted(current_permission_names - desired_permissions)

    desired_role_names = set(manifest["roles"])
    current_role_names = set(current_roles)
    missing_roles = sorted(desired_role_names - current_role_names)
    extra_roles = sorted(current_role_names - desired_role_names)

    report.unknown_roles = sorted(
        role_name
        for role_name in current_role_names - desired_role_names
        if not current_roles[role_name].is_system
    )
    report.ambiguous_roles = sorted(
        role_name
        for role_name in desired_role_names & current_role_names
        if not current_roles[role_name].is_system
    )
    if extra_roles:
        report.unknown_roles = sorted(set(report.unknown_roles).union(extra_roles))

    if report.ambiguous_roles and apply_changes:
        raise PermissionSyncError(
            "ambiguous system-role identity: " + ", ".join(report.ambiguous_roles)
        )

    report.drift_detected = bool(
        report.permission_missing
        or report.permission_extra
        or missing_roles
        or extra_roles
        or report.ambiguous_roles
    )

    if apply_changes:
        for permission_name in report.permission_missing:
            resource, action = _split_permission(permission_name)
            db.add(
                PermissionModel(
                    id=str(uuid.uuid4()),
                    name=permission_name,
                    resource=resource,
                    action=action,
                    description=f"Canonical permission for {permission_name}",
                )
            )
            report.permissions_created += 1
            report.created_records.append(f"permission:{permission_name}")

        for role_name in missing_roles:
            db.add(
                RoleModel(
                    id=str(uuid.uuid4()),
                    name=role_name,
                    display_name=_display_name_for_role(role_name),
                    description="Canonical Mission Control system role",
                    is_system=True,
                )
            )
            report.created_records.append(f"role:{role_name}")

        await db.flush()

        permission_rows = (await db.execute(select(PermissionModel))).scalars().all()
        role_rows = (
            await db.execute(
                select(RoleModel)
                .options(selectinload(RoleModel.permissions))
                .order_by(RoleModel.name.asc())
            )
        ).scalars().all()
        current_permissions = {row.name: row for row in permission_rows}
        current_roles = {row.name: row for row in role_rows}
        current_grants = {
            role.name: {permission.name for permission in role.permissions}
            for role in role_rows
        }

    for role_name, desired_set in manifest["roles"].items():
        role = current_roles.get(role_name)
        if role is None:
            continue

        if not role.is_system:
            report.unknown_roles.append(role_name)
            continue

        actual_set = current_grants.get(role_name, set())
        missing_grants = sorted(set(desired_set) - actual_set)
        extra_grants = sorted(actual_set - set(desired_set))

        report.role_grant_missing[role_name] = missing_grants
        report.role_grant_extra[role_name] = extra_grants
        if missing_grants or extra_grants:
            report.drift_detected = True

        if apply_changes:
            for permission_name in missing_grants:
                permission = current_permissions.get(permission_name)
                if permission is None:
                    report.role_grants_failed += 1
                    report.failed_records.append(f"role_grant:{role_name}:{permission_name}:missing_permission")
                    continue
                if not await _role_permission_exists(db, role.id, permission.id):
                    db.add(RolePermission(role_id=role.id, permission_id=permission.id))
                    report.role_grants_created += 1
                    report.created_records.append(f"role_grant:{role_name}:{permission_name}")

            if extra_grants:
                extra_permission_ids = {
                    current_permissions[name].id
                    for name in extra_grants
                    if name in current_permissions
                }
                if extra_permission_ids:
                    await db.execute(
                        delete(RolePermission).where(
                            RolePermission.role_id == role.id,
                            RolePermission.permission_id.in_(extra_permission_ids),
                        )
                    )
                    report.role_grants_removed += len(extra_permission_ids)
                    for permission_name in extra_grants:
                        if permission_name in current_permissions:
                            report.removed_records.append(f"role_grant:{role_name}:{permission_name}")
        else:
            report.role_grants_unchanged += len(set(desired_set).intersection(actual_set))

    if apply_changes:
        await db.flush()
        permission_rows = (await db.execute(select(PermissionModel))).scalars().all()
        role_rows = (
            await db.execute(
                select(RoleModel)
                .options(selectinload(RoleModel.permissions))
                .order_by(RoleModel.name.asc())
            )
        ).scalars().all()
        current_permissions = {row.name: row for row in permission_rows}
        current_roles = {row.name: row for row in role_rows}
        current_grants = {
            role.name: {permission.name for permission in role.permissions}
            for role in role_rows
        }

    report.permission_missing = sorted(desired_permissions - set(current_permissions))
    report.permission_extra = sorted(set(current_permissions) - desired_permissions)
    report.role_grant_missing = {
        role_name: sorted(set(desired_set) - current_grants.get(role_name, set()))
        for role_name, desired_set in manifest["roles"].items()
        if role_name in current_roles and current_roles[role_name].is_system
    }
    report.role_grant_extra = {
        role_name: sorted(current_grants.get(role_name, set()) - set(desired_set))
        for role_name, desired_set in manifest["roles"].items()
        if role_name in current_roles and current_roles[role_name].is_system
    }
    report.permissions_unchanged = len(desired_permissions.intersection(set(current_permissions)))
    report.role_grants_unchanged = sum(
        len(set(desired_set).intersection(current_grants.get(role_name, set())))
        for role_name, desired_set in manifest["roles"].items()
        if role_name in current_roles and current_roles[role_name].is_system
    )
    report.drift_detected = bool(
        report.permission_missing
        or report.permission_extra
        or any(report.role_grant_missing.values())
        or any(report.role_grant_extra.values())
        or report.ambiguous_roles
    )
    report.unknown_roles = sorted(set(report.unknown_roles))
    report.ambiguous_roles = sorted(set(report.ambiguous_roles))
    report.severity = _classify_drift_severity(report, current_roles, current_grants)
    return report


async def _role_permission_exists(db: AsyncSession, role_id: str, permission_id: str) -> bool:
    result = await db.execute(
        select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        )
    )
    return result.scalar_one_or_none() is not None


def _canonical_manifest_payload() -> dict[str, Any]:
    manifest = canonical_permission_manifest()
    return {
        "schema_version": manifest.schema_version,
        "permissions": list(manifest.permissions),
        "roles": {name: list(perms) for name, perms in sorted(manifest.roles.items())},
    }


def _build_state_snapshot(
    permissions: dict[str, PermissionModel],
    grants: dict[str, set[str]],
    roles: dict[str, RoleModel],
) -> dict[str, Any]:
    return {
        "permissions": sorted(permissions),
        "roles": {
            role_name: {
                "is_system": roles[role_name].is_system,
                "grants": sorted(grants.get(role_name, set())),
            }
            for role_name in sorted(grants)
        },
    }


def _build_proposed_state_snapshot(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "permissions": list(manifest["permissions"]),
        "roles": {role_name: list(perms) for role_name, perms in manifest["roles"].items()},
    }


def _classify_drift_severity(
    report: PermissionSyncReport,
    current_roles: dict[str, RoleModel],
    current_grants: dict[str, set[str]],
) -> DriftSeverity:
    if report.ambiguous_roles:
        return DriftSeverity.BLOCKING

    for role_name, grants in current_grants.items():
        if role_name in ROLE_PERMISSIONS:
            desired = {permission.value for permission in ROLE_PERMISSIONS[Role(role_name)]}
            if grants - desired and MUTATION_PERMISSIONS.intersection(grants):
                return DriftSeverity.CRITICAL
        elif MUTATION_PERMISSIONS.intersection(grants):
            return DriftSeverity.CRITICAL

    if any(report.role_grant_missing.values()):
        return DriftSeverity.HIGH

    if any(permission.startswith(MISSION_CONTROL_PERMISSION_PREFIX) for permission in report.permission_missing):
        return DriftSeverity.HIGH

    if report.permission_missing:
        return DriftSeverity.WARNING

    if report.permission_extra or any(report.role_grant_extra.values()) or report.unknown_roles:
        return DriftSeverity.WARNING

    return DriftSeverity.INFO


def _split_permission(permission_name: str) -> tuple[str, str]:
    resource, action = permission_name.split(":", 1)
    return resource, action


def _display_name_for_role(role_name: str) -> str:
    return role_name.replace("_", " ").title()


def _sha256_json(data: Any) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
