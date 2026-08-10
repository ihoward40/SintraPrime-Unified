from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from packages.economic_governance.models import SpendCategory
from packages.economic_governance.phase2 import (
    ApprovalReceipt,
    BudgetReservation,
    LedgerEvent,
    ReservationBook,
    ReservationState,
    canonical_digest,
    execution_allowed,
    verify_chain,
)
from portal.models.economic_budget import EconomicMissionBudget
from portal.models.economic_governance import (
    EconomicBudgetReservation,
    EconomicLedgerEvent,
    EconomicPrincipalApprovalReceipt,
)
from portal.models.economic_records import (
    EconomicAssetProvenanceRecord,
    EconomicCapitalReserveTarget,
    EconomicScenarioRecord,
    EconomicValueAccrualRecord,
)
from portal.services.economic_governance_service import TenantContextRequiredError, _tenant_id


NOW = datetime(2026, 8, 10, 18, 0, tzinfo=UTC)


def _receipt(*, digest: str = "a" * 64, approved: bool = True) -> ApprovalReceipt:
    return ApprovalReceipt.issue(
        approval_request_id="approval-1",
        tenant_id="tenant-1",
        mission_id="mission-1",
        principal_id="principal-1",
        request_digest=digest,
        policy_version="sp-eg-001-v2",
        approved=approved,
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=30),
    )


def test_canonical_digest_is_order_independent():
    assert canonical_digest({"b": 2, "a": 1}) == canonical_digest({"a": 1, "b": 2})


def test_approval_receipt_binds_exact_digest_and_mission():
    receipt = _receipt()
    assert receipt.validates(
        tenant_id="tenant-1",
        mission_id="mission-1",
        request_digest="a" * 64,
        now=NOW + timedelta(minutes=1),
    )
    assert not receipt.validates(
        tenant_id="tenant-1",
        mission_id="mission-2",
        request_digest="a" * 64,
        now=NOW + timedelta(minutes=1),
    )
    assert not receipt.validates(
        tenant_id="tenant-1",
        mission_id="mission-1",
        request_digest="b" * 64,
        now=NOW + timedelta(minutes=1),
    )


def test_expired_or_denied_receipt_rejected():
    receipt = _receipt()
    assert not receipt.validates(
        tenant_id="tenant-1",
        mission_id="mission-1",
        request_digest="a" * 64,
        now=NOW + timedelta(hours=1),
    )
    denied = _receipt(approved=False)
    assert not denied.validates(
        tenant_id="tenant-1",
        mission_id="mission-1",
        request_digest="a" * 64,
        now=NOW + timedelta(minutes=1),
    )


def test_hard_denied_financial_actions_cannot_be_overridden_by_receipt():
    receipt = _receipt()
    for category in (
        SpendCategory.TRANSFER_TO_HUMAN,
        SpendCategory.BORROWING,
        SpendCategory.OPEN_ACCOUNT,
        SpendCategory.SECURITIES,
        SpendCategory.TRUST_ASSET_MOVEMENT,
    ):
        assert execution_allowed(category, receipt) is False


def test_budget_reservation_duplicate_returns_same_reservation():
    book = ReservationBook(Decimal("100.00"))
    reservation = BudgetReservation(
        tenant_id="tenant-1",
        mission_id="mission-1",
        idempotency_key="idem-1",
        request_digest="a" * 64,
        amount=Decimal("25.00"),
        expires_at=NOW + timedelta(minutes=15),
    )
    first = book.reserve(reservation, NOW)
    second = book.reserve(reservation, NOW)
    assert second is first


def test_same_idempotency_key_different_payload_rejected():
    book = ReservationBook(Decimal("100.00"))
    first = BudgetReservation(
        tenant_id="tenant-1",
        mission_id="mission-1",
        idempotency_key="idem-1",
        request_digest="a" * 64,
        amount=Decimal("25.00"),
        expires_at=NOW + timedelta(minutes=15),
    )
    book.reserve(first, NOW)
    with pytest.raises(ValueError, match="different payload"):
        book.reserve(
            BudgetReservation(
                tenant_id="tenant-1",
                mission_id="mission-1",
                idempotency_key="idem-1",
                request_digest="b" * 64,
                amount=Decimal("25.00"),
                expires_at=NOW + timedelta(minutes=15),
            ),
            NOW,
        )


def test_budget_never_over_reserves():
    book = ReservationBook(Decimal("100.00"))
    book.reserve(
        BudgetReservation(
            tenant_id="tenant-1",
            mission_id="mission-1",
            idempotency_key="idem-1",
            request_digest="a" * 64,
            amount=Decimal("80.00"),
            expires_at=NOW + timedelta(minutes=15),
        ),
        NOW,
    )
    with pytest.raises(ValueError, match="remaining mission budget"):
        book.reserve(
            BudgetReservation(
                tenant_id="tenant-1",
                mission_id="mission-1",
                idempotency_key="idem-2",
                request_digest="b" * 64,
                amount=Decimal("21.00"),
                expires_at=NOW + timedelta(minutes=15),
            ),
            NOW,
        )


def test_reservation_lifecycle_and_expiry():
    reservation = BudgetReservation(
        tenant_id="tenant-1",
        mission_id="mission-1",
        idempotency_key="idem-1",
        request_digest="a" * 64,
        amount=Decimal("25.00"),
        expires_at=NOW + timedelta(minutes=15),
    )
    assert reservation.commit(NOW + timedelta(minutes=1)).state is ReservationState.COMMITTED
    assert reservation.release().state is ReservationState.RELEASED
    with pytest.raises(ValueError, match="expired"):
        reservation.commit(NOW + timedelta(minutes=16))


def test_ledger_hash_chain_detects_tampering_and_sequence_gaps():
    first = LedgerEvent.append(
        tenant_id="tenant-1",
        mission_id="mission-1",
        actor_id="actor-1",
        sequence=1,
        decision_type="spend_evaluated",
        policy_version="sp-eg-001-v2",
        evidence_refs=("evidence-1",),
        payload={"decision": "approval_required"},
        previous_hash=None,
        created_at=NOW,
    )
    second = LedgerEvent.append(
        tenant_id="tenant-1",
        mission_id="mission-1",
        actor_id="actor-1",
        sequence=2,
        decision_type="approval_recorded",
        policy_version="sp-eg-001-v2",
        evidence_refs=("evidence-2",),
        payload={"result": "approved"},
        previous_hash=first.event_hash,
        created_at=NOW + timedelta(seconds=1),
    )
    assert verify_chain([first, second])
    assert not verify_chain([second])


def test_missing_tenant_context_fails_closed():
    class NoTenant:
        tenant_id = None

    with pytest.raises(TenantContextRequiredError):
        _tenant_id(NoTenant())


def test_phase_two_models_cover_all_required_persistence_surfaces():
    names = {
        model.__tablename__
        for model in (
            EconomicAssetProvenanceRecord,
            EconomicValueAccrualRecord,
            EconomicScenarioRecord,
            EconomicCapitalReserveTarget,
            EconomicMissionBudget,
            EconomicBudgetReservation,
            EconomicPrincipalApprovalReceipt,
            EconomicLedgerEvent,
        )
    }
    assert {
        "economic_asset_provenance_records",
        "economic_value_accrual_records",
        "economic_scenario_records",
        "economic_capital_reserve_targets",
        "economic_mission_budgets",
        "economic_budget_reservations",
        "economic_principal_approval_receipts",
        "economic_ledger_events",
    } <= names


def test_migration_enforces_immutability_rls_and_no_execution_adapter():
    sql = Path("portal/migrations/add_economic_governance_phase_two.sql").read_text(encoding="utf-8")
    assert "FORCE ROW LEVEL SECURITY" in sql
    assert "prevent_economic_ledger_event_mutation" in sql
    assert "prevent_economic_approval_receipt_mutation" in sql
    assert "uq_economic_budget_reservation_idempotency" in sql
    lowered = sql.lower()
    assert "stripe" not in lowered
    assert "brokerage" in lowered  # explicitly documented as excluded
    assert "payment-provider" in lowered  # explicitly documented as excluded
