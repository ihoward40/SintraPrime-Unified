"""Tests for provider tenant mapping lifecycle and uniqueness."""

from __future__ import annotations

import pytest

from portal.models.provider_tenant_mapping import ProviderTenantMapping


class TestProviderTenantMappingModel:
    """Test mapping model structure and constraints."""

    def test_table_name(self):
        assert ProviderTenantMapping.__tablename__ == "provider_tenant_mappings"

    def test_lifecycle_fields_present(self):
        cols = ProviderTenantMapping.__table__.columns
        assert "updated_by" in cols
        assert "deactivated_at" in cols
        assert "deactivated_by" in cols
        assert "deactivation_reason" in cols

    def test_tenant_id_uses_on_delete_restrict(self):
        col = ProviderTenantMapping.__table__.columns["tenant_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert fks[0].ondelete == "RESTRICT"

    def test_partial_unique_indexes(self):
        index_names = {idx.name for idx in ProviderTenantMapping.__table__.indexes}
        assert "uq_active_provider_account" in index_names
        assert "uq_active_provider_customer" in index_names

    def test_mapping_status_default_active(self):
        col = ProviderTenantMapping.__table__.columns["mapping_status"]
        assert col.default is not None
        assert col.default.arg == "active"

    def test_deactivated_mapping_not_deleted(self):
        """Deactivated mappings persist — they are not physically deleted."""
        cols = ProviderTenantMapping.__table__.columns
        assert "deactivated_at" in cols
        assert "deactivation_reason" in cols


class TestPermissionEnum:
    """Test that new permissions exist and are SUPER_ADMIN only."""

    def test_create_permission_exists(self):
        from portal.auth.rbac import Permission
        assert hasattr(Permission, "PROVIDER_TENANT_MAPPING_CREATE")
        assert Permission.PROVIDER_TENANT_MAPPING_CREATE == "provider_tenant_mapping:create"

    def test_deactivate_permission_exists(self):
        from portal.auth.rbac import Permission
        assert hasattr(Permission, "PROVIDER_TENANT_MAPPING_DEACTIVATE")
        assert Permission.PROVIDER_TENANT_MAPPING_DEACTIVATE == "provider_tenant_mapping:deactivate"

    def test_super_admin_gets_all_permissions(self):
        from portal.auth.rbac import ROLE_PERMISSIONS, Permission, Role
        all_perms = ROLE_PERMISSIONS[Role.SUPER_ADMIN]
        assert Permission.PROVIDER_TENANT_MAPPING_CREATE in all_perms
        assert Permission.PROVIDER_TENANT_MAPPING_DEACTIVATE in all_perms

    def test_firm_admin_does_not_get_mapping_permissions(self):
        from portal.auth.rbac import ROLE_PERMISSIONS, Permission, Role
        firm_perms = ROLE_PERMISSIONS[Role.FIRM_ADMIN]
        assert Permission.PROVIDER_TENANT_MAPPING_CREATE not in firm_perms
        assert Permission.PROVIDER_TENANT_MAPPING_DEACTIVATE not in firm_perms
