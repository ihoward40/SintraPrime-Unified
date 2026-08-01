"""Model/migration parity tests for payment webhook increment one.

Verifies that SQLAlchemy model column definitions match the expected
column names from the SQL migration files. Does not require a live database.
"""

from __future__ import annotations

import pytest

from ..models.payment_event import PaymentEvent
from ..models.provider_tenant_mapping import ProviderTenantMapping

EXPECTED_PAYMENT_EVENT_COLUMNS = {
    "id",
    "tenant_id",
    "provider",
    "provider_account_id",
    "provider_event_id",
    "operation",
    "payload_digest",
    "status",
    "correlation_id",
    "result_reference",
    "processing_owner",
    "lease_expires_at",
    "attempt_count",
    "last_error_code",
    "created_at",
    "started_at",
    "completed_at",
    "updated_at",
    "expiry_at",
    "version",
}

EXPECTED_MAPPING_COLUMNS = {
    "id",
    "tenant_id",
    "provider",
    "provider_account_id",
    "provider_customer_id",
    "mapping_status",
    "created_by",
    "created_at",
    "updated_at",
    "updated_by",
    "deactivated_at",
    "deactivated_by",
    "deactivation_reason",
}


class TestPaymentEventModelParity:
    """Verify PaymentEvent model matches add_payment_events.sql."""

    def test_table_name(self):
        assert PaymentEvent.__tablename__ == "payment_events"

    def test_column_names(self):
        actual = set(PaymentEvent.__table__.columns.keys())
        assert actual == EXPECTED_PAYMENT_EVENT_COLUMNS, (
            f"Missing: {EXPECTED_PAYMENT_EVENT_COLUMNS - actual}, "
            f"Extra: {actual - EXPECTED_PAYMENT_EVENT_COLUMNS}"
        )

    def test_tenant_id_foreign_key_restrict(self):
        col = PaymentEvent.__table__.columns["tenant_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        fk = fks[0]
        assert fk.column.table.name == "tenants"
        assert fk.ondelete == "RESTRICT"

    def test_provider_account_id_default(self):
        col = PaymentEvent.__table__.columns["provider_account_id"]
        assert col.default is not None
        assert col.default.arg == "__platform__"

    def test_unique_index_exists(self):
        index_names = {idx.name for idx in PaymentEvent.__table__.indexes}
        assert "uq_provider_event" in index_names


class TestProviderTenantMappingModelParity:
    """Verify ProviderTenantMapping model matches add_provider_tenant_mappings.sql."""

    def test_table_name(self):
        assert ProviderTenantMapping.__tablename__ == "provider_tenant_mappings"

    def test_column_names(self):
        actual = set(ProviderTenantMapping.__table__.columns.keys())
        assert actual == EXPECTED_MAPPING_COLUMNS, (
            f"Missing: {EXPECTED_MAPPING_COLUMNS - actual}, "
            f"Extra: {actual - EXPECTED_MAPPING_COLUMNS}"
        )

    def test_tenant_id_foreign_key_restrict(self):
        col = ProviderTenantMapping.__table__.columns["tenant_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        fk = fks[0]
        assert fk.column.table.name == "tenants"
        assert fk.ondelete == "RESTRICT"

    def test_partial_unique_indexes_exist(self):
        index_names = {idx.name for idx in ProviderTenantMapping.__table__.indexes}
        assert "uq_active_provider_account" in index_names
        assert "uq_active_provider_customer" in index_names

    def test_lifecycle_fields_present(self):
        cols = ProviderTenantMapping.__table__.columns
        assert "updated_by" in cols
        assert "deactivated_at" in cols
        assert "deactivated_by" in cols
        assert "deactivation_reason" in cols
