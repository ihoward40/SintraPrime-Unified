"""
Phase 15C — CPA Partnership Engine
Auto-routes tax and financial cases to registered CPA partners,
tracks referral fees, and manages the full partner lifecycle.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class CaseType(str, Enum):
    TAX_PREPARATION = "tax_preparation"
    TAX_DISPUTE = "tax_dispute"
    IRS_AUDIT = "irs_audit"
    BUSINESS_FORMATION = "business_formation"
    BOOKKEEPING = "bookkeeping"
    PAYROLL = "payroll"
    ESTATE_PLANNING = "estate_planning"
    BANKRUPTCY = "bankruptcy"
    FINANCIAL_PLANNING = "financial_planning"
    OTHER = "other"


class PartnerStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_REVIEW = "pending_review"


class ReferralStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FEE_PAID = "fee_paid"


class FeeStructure(str, Enum):
    FLAT = "flat"
    PERCENTAGE = "percentage"
    TIERED = "tiered"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class CPAPartner:
    partner_id: str
    name: str
    firm_name: str
    email: str
    phone: Optional[str] = None
    license_number: Optional[str] = None
    states_licensed: List[str] = field(default_factory=list)
    specializations: List[CaseType] = field(default_factory=list)
    status: PartnerStatus = PartnerStatus.ACTIVE
    fee_structure: FeeStructure = FeeStructure.PERCENTAGE
    fee_rate: float = 0.15  # 15% of first-year revenue by default
    flat_fee: float = 0.0
    max_monthly_referrals: int = 20
    current_month_referrals: int = 0
    total_referrals: int = 0
    total_fees_earned: float = 0.0
    rating: float = 5.0
    response_time_hours: float = 24.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def can_accept_referral(self) -> bool:
        return (
            self.status == PartnerStatus.ACTIVE
            and self.current_month_referrals < self.max_monthly_referrals
        )

    def handles_case_type(self, case_type: CaseType) -> bool:
        return not self.specializations or case_type in self.specializations

    def is_licensed_in(self, state: str) -> bool:
        return not self.states_licensed or state.upper() in [s.upper() for s in self.states_licensed]

    def calculate_fee(self, case_value: float) -> float:
        if self.fee_structure == FeeStructure.FLAT:
            return self.flat_fee
        elif self.fee_structure == FeeStructure.PERCENTAGE:
            return round(case_value * self.fee_rate, 2)
        elif self.fee_structure == FeeStructure.TIERED:
            # Tiered: 20% on first $5k, 15% on $5k-$20k, 10% above $20k
            if case_value <= 5000:
                return round(case_value * 0.20, 2)
            elif case_value <= 20000:
                return round(5000 * 0.20 + (case_value - 5000) * 0.15, 2)
            else:
                return round(5000 * 0.20 + 15000 * 0.15 + (case_value - 20000) * 0.10, 2)
        return 0.0


@dataclass
class TaxCase:
    case_id: str
    client_name: str
    client_email: str
    case_type: CaseType
    state: str
    estimated_value: float = 0.0
    description: str = ""
    urgency: int = 3  # 1=low, 5=critical
    client_phone: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def is_urgent(self) -> bool:
        return self.urgency >= 4


@dataclass
class Referral:
    referral_id: str
    case: TaxCase
    partner: CPAPartner
    status: ReferralStatus = ReferralStatus.PENDING
    fee_amount: float = 0.0
    fee_paid: bool = False
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    fee_paid_at: Optional[datetime] = None

    def accept(self) -> None:
        self.status = ReferralStatus.ACCEPTED
        self.accepted_at = datetime.utcnow()
        self.partner.current_month_referrals += 1
        self.partner.total_referrals += 1

    def complete(self, actual_value: Optional[float] = None) -> None:
        self.status = ReferralStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if actual_value is not None:
            self.fee_amount = self.partner.calculate_fee(actual_value)

    def mark_fee_paid(self) -> None:
        self.fee_paid = True
        self.status = ReferralStatus.FEE_PAID
        self.fee_paid_at = datetime.utcnow()
        self.partner.total_fees_earned += self.fee_amount


@dataclass
class PartnerScore:
    partner: CPAPartner
    score: float
    reasons: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Routing algorithm
# ---------------------------------------------------------------------------

class PartnerRouter:
    """
    Scores and ranks CPA partners for a given tax case.
    Factors: specialization match, state license, capacity, rating, response time.
    """

    WEIGHTS = {
        "specialization": 40,
        "state_license": 30,
        "capacity": 15,
        "rating": 10,
        "response_time": 5,
    }

    def score_partner(self, partner: CPAPartner, case: TaxCase) -> PartnerScore:
        score = 0.0
        reasons: List[str] = []

        # Specialization match
        if partner.handles_case_type(case.case_type):
            if case.case_type in partner.specializations:
                score += self.WEIGHTS["specialization"]
                reasons.append(f"Specializes in {case.case_type.value}")
            else:
                score += self.WEIGHTS["specialization"] * 0.5
                reasons.append("General practice (no specific specialization)")
        else:
            reasons.append(f"Does not handle {case.case_type.value}")

        # State license
        if partner.is_licensed_in(case.state):
            score += self.WEIGHTS["state_license"]
            reasons.append(f"Licensed in {case.state}")
        else:
            reasons.append(f"Not licensed in {case.state}")

        # Capacity (remaining slots vs max)
        remaining = partner.max_monthly_referrals - partner.current_month_referrals
        capacity_score = (remaining / max(partner.max_monthly_referrals, 1)) * self.WEIGHTS["capacity"]
        score += capacity_score
        reasons.append(f"Capacity: {remaining}/{partner.max_monthly_referrals} slots remaining")

        # Rating (5.0 = full points)
        rating_score = (partner.rating / 5.0) * self.WEIGHTS["rating"]
        score += rating_score
        reasons.append(f"Rating: {partner.rating}/5.0")

        # Response time (lower is better; 1h = full, 48h = 0)
        rt_score = max(0, 1 - (partner.response_time_hours / 48)) * self.WEIGHTS["response_time"]
        score += rt_score
        reasons.append(f"Avg response time: {partner.response_time_hours}h")

        return PartnerScore(partner=partner, score=round(score, 2), reasons=reasons)

    def rank_partners(
        self, partners: List[CPAPartner], case: TaxCase
    ) -> List[PartnerScore]:
        eligible = [p for p in partners if p.can_accept_referral()]
        scores = [self.score_partner(p, case) for p in eligible]
        return sorted(scores, key=lambda s: s.score, reverse=True)

    def select_best(
        self, partners: List[CPAPartner], case: TaxCase
    ) -> Optional[PartnerScore]:
        ranked = self.rank_partners(partners, case)
        return ranked[0] if ranked else None


# ---------------------------------------------------------------------------
# Fee tracker
# ---------------------------------------------------------------------------

class FeeTracker:
    """Tracks all referral fees — pending, earned, and paid."""

    def __init__(self):
        self._referrals: Dict[str, Referral] = {}

    def register(self, referral: Referral) -> None:
        self._referrals[referral.referral_id] = referral

    def get_pending_fees(self) -> List[Referral]:
        return [
            r for r in self._referrals.values()
            if r.status == ReferralStatus.COMPLETED and not r.fee_paid
        ]

    def get_total_earned(self, partner_id: Optional[str] = None) -> float:
        refs = self._referrals.values()
        if partner_id:
            refs = [r for r in refs if r.partner.partner_id == partner_id]
        return sum(r.fee_amount for r in refs if r.fee_paid)

    def get_total_pending(self) -> float:
        return sum(r.fee_amount for r in self.get_pending_fees())

    def get_monthly_summary(self, year: int, month: int) -> Dict[str, Any]:
        month_refs = [
            r for r in self._referrals.values()
            if r.created_at.year == year and r.created_at.month == month
        ]
        return {
            "year": year,
            "month": month,
            "total_referrals": len(month_refs),
            "completed": sum(1 for r in month_refs if r.status in (
                ReferralStatus.COMPLETED, ReferralStatus.FEE_PAID)),
            "fees_earned": sum(r.fee_amount for r in month_refs if r.fee_paid),
            "fees_pending": sum(r.fee_amount for r in month_refs
                                if r.status == ReferralStatus.COMPLETED and not r.fee_paid),
        }


# ---------------------------------------------------------------------------
# Notification adapter (stub)
# ---------------------------------------------------------------------------

class NotificationAdapter:
    """Sends partner notifications via email/SMS."""

    def notify_partner(self, partner: CPAPartner, referral: Referral) -> bool:
        logger.info(
            "Notifying partner %s (%s) of referral %s",
            partner.name, partner.email, referral.referral_id,
        )
        return True

    def notify_client(self, case: TaxCase, partner: CPAPartner) -> bool:
        logger.info(
            "Notifying client %s of partner assignment: %s",
            case.client_email, partner.name,
        )
        return True

    def notify_fee_due(self, referral: Referral) -> bool:
        logger.info(
            "Fee due notification: %s owes $%.2f for referral %s",
            referral.partner.name, referral.fee_amount, referral.referral_id,
        )
        return True


# ---------------------------------------------------------------------------
# Main CPA Partnership Engine
# ---------------------------------------------------------------------------

class CPAPartnershipEngine:
    """
    Manages the full CPA partner lifecycle:
    - Partner registration and management
    - Automatic case routing
    - Referral tracking
    - Fee calculation and payment tracking
    """

    def __init__(
        self,
        router: Optional[PartnerRouter] = None,
        fee_tracker: Optional[FeeTracker] = None,
        notifier: Optional[NotificationAdapter] = None,
        on_referral_created: Optional[Callable[[Referral], None]] = None,
        on_fee_earned: Optional[Callable[[Referral], None]] = None,
    ):
        self._router = router or PartnerRouter()
        self._fee_tracker = fee_tracker or FeeTracker()
        self._notifier = notifier or NotificationAdapter()
        self._partners: Dict[str, CPAPartner] = {}
        self._referrals: Dict[str, Referral] = {}
        self._cases: Dict[str, TaxCase] = {}
        self._on_referral_created = on_referral_created
        self._on_fee_earned = on_fee_earned

    # ------------------------------------------------------------------
    # Partner management
    # ------------------------------------------------------------------

    def register_partner(self, partner: CPAPartner) -> CPAPartner:
        self._partners[partner.partner_id] = partner
        logger.info("Partner registered: %s (%s)", partner.name, partner.partner_id)
        return partner

    def get_partner(self, partner_id: str) -> Optional[CPAPartner]:
        return self._partners.get(partner_id)

    def list_partners(self, status: Optional[PartnerStatus] = None) -> List[CPAPartner]:
        partners = list(self._partners.values())
        if status:
            partners = [p for p in partners if p.status == status]
        return partners

    def deactivate_partner(self, partner_id: str) -> bool:
        partner = self._partners.get(partner_id)
        if not partner:
            return False
        partner.status = PartnerStatus.INACTIVE
        return True

    def reset_monthly_counts(self) -> None:
        """Call at the start of each month."""
        for partner in self._partners.values():
            partner.current_month_referrals = 0

    # ------------------------------------------------------------------
    # Case routing
    # ------------------------------------------------------------------

    def route_case(self, case: TaxCase) -> Optional[Referral]:
        """
        Automatically routes a tax case to the best available CPA partner.
        Returns the created Referral, or None if no partner is available.
        """
        self._cases[case.case_id] = case
        active_partners = self.list_partners(status=PartnerStatus.ACTIVE)

        best = self._router.select_best(active_partners, case)
        if not best:
            logger.warning("No available partner for case %s", case.case_id)
            return None

        referral = Referral(
            referral_id=f"REF-{uuid.uuid4().hex[:8].upper()}",
            case=case,
            partner=best.partner,
            fee_amount=best.partner.calculate_fee(case.estimated_value),
        )
        referral.accept()
        self._referrals[referral.referral_id] = referral
        self._fee_tracker.register(referral)

        self._notifier.notify_partner(best.partner, referral)
        self._notifier.notify_client(case, best.partner)

        if self._on_referral_created:
            self._on_referral_created(referral)

        logger.info(
            "Case %s routed to %s (score=%.1f, fee=$%.2f)",
            case.case_id, best.partner.name, best.score, referral.fee_amount,
        )
        return referral

    def get_ranked_partners(self, case: TaxCase) -> List[PartnerScore]:
        """Returns ranked list of partners for a case without creating a referral."""
        active = self.list_partners(status=PartnerStatus.ACTIVE)
        return self._router.rank_partners(active, case)

    # ------------------------------------------------------------------
    # Referral management
    # ------------------------------------------------------------------

    def get_referral(self, referral_id: str) -> Optional[Referral]:
        return self._referrals.get(referral_id)

    def complete_referral(
        self, referral_id: str, actual_value: Optional[float] = None
    ) -> bool:
        referral = self._referrals.get(referral_id)
        if not referral:
            return False
        referral.complete(actual_value)
        self._notifier.notify_fee_due(referral)
        return True

    def mark_fee_paid(self, referral_id: str) -> bool:
        referral = self._referrals.get(referral_id)
        if not referral:
            return False
        referral.mark_fee_paid()
        if self._on_fee_earned:
            self._on_fee_earned(referral)
        return True

    def decline_referral(self, referral_id: str, reason: str = "") -> bool:
        referral = self._referrals.get(referral_id)
        if not referral:
            return False
        referral.status = ReferralStatus.DECLINED
        referral.notes = reason
        # Re-route to next best partner
        remaining_partners = [
            p for p in self.list_partners(status=PartnerStatus.ACTIVE)
            if p.partner_id != referral.partner.partner_id
        ]
        if remaining_partners:
            best = self._router.select_best(remaining_partners, referral.case)
            if best:
                referral.partner = best.partner
                referral.status = ReferralStatus.PENDING
                referral.fee_amount = best.partner.calculate_fee(
                    referral.case.estimated_value
                )
                referral.accept()
                self._notifier.notify_partner(best.partner, referral)
        return True

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        total_refs = len(self._referrals)
        completed = sum(1 for r in self._referrals.values()
                        if r.status in (ReferralStatus.COMPLETED, ReferralStatus.FEE_PAID))
        fees_earned = self._fee_tracker.get_total_earned()
        fees_pending = self._fee_tracker.get_total_pending()

        return {
            "total_partners": len(self._partners),
            "active_partners": len(self.list_partners(PartnerStatus.ACTIVE)),
            "total_cases": len(self._cases),
            "total_referrals": total_refs,
            "completed_referrals": completed,
            "completion_rate": round(completed / total_refs * 100, 1) if total_refs else 0.0,
            "total_fees_earned": fees_earned,
            "fees_pending": fees_pending,
            "projected_monthly_revenue": fees_earned + fees_pending,
        }

    def get_partner_leaderboard(self) -> List[Dict[str, Any]]:
        partners = self.list_partners(PartnerStatus.ACTIVE)
        board = []
        for p in partners:
            board.append({
                "partner_id": p.partner_id,
                "name": p.name,
                "firm": p.firm_name,
                "total_referrals": p.total_referrals,
                "total_fees_earned": p.total_fees_earned,
                "rating": p.rating,
            })
        return sorted(board, key=lambda x: x["total_fees_earned"], reverse=True)
