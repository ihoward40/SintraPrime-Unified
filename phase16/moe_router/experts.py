"""Phase 16A — Legal domain experts for the MoE Router."""
from __future__ import annotations
from typing import Any, Dict, List
from phase16.moe_router.models import ExpertType, RoutingRequest


class BaseLegalExpert:
    """Base class for all legal domain experts."""

    expert_type: ExpertType
    _keywords: List[str] = []
    _base_confidence: float = 0.5

    def analyze(self, request: RoutingRequest) -> Dict[str, Any]:
        """Analyze a routing request and return structured findings."""
        text_lower = request.text.lower()
        matched = [kw for kw in self._keywords if kw in text_lower]
        confidence = self.get_confidence(request)
        return {
            "expert": self.expert_type.value,
            "confidence": confidence,
            "matched_keywords": matched,
            "recommendation": self._generate_recommendation(request, matched),
            "relevant": confidence > 0.3,
        }

    def get_confidence(self, request: RoutingRequest = None) -> float:
        """Return confidence score for this expert on the given request."""
        if request is None:
            return self._base_confidence
        text_lower = request.text.lower()
        matched = sum(1 for kw in self._keywords if kw in text_lower)
        score = self._base_confidence + (matched * 0.08)
        return min(score, 0.99)

    def get_specializations(self) -> List[str]:
        """Return list of sub-specializations."""
        return list(self._keywords[:5])

    def _generate_recommendation(self, request: RoutingRequest, matched: List[str]) -> str:
        if not matched:
            return f"No strong {self.expert_type.value} indicators found."
        return f"Strong {self.expert_type.value} case. Key indicators: {', '.join(matched[:3])}."


class TrustLawExpert(BaseLegalExpert):
    """Expert in trust, estate, and probate law."""
    expert_type = ExpertType.TRUST_LAW
    _keywords = [
        "trust", "estate", "probate", "will", "beneficiary", "trustee",
        "inheritance", "executor", "fiduciary", "revocable", "irrevocable",
        "grantor", "settlor", "bequest", "testamentary",
    ]
    _base_confidence = 0.45


class CorporateExpert(BaseLegalExpert):
    """Expert in corporate, M&A, and securities law."""
    expert_type = ExpertType.CORPORATE
    _keywords = [
        "corporation", "merger", "acquisition", "shareholder", "board",
        "securities", "ipo", "llc", "partnership", "bylaws", "articles",
        "fiduciary duty", "derivative", "proxy", "dividend",
    ]
    _base_confidence = 0.45


class IPExpert(BaseLegalExpert):
    """Expert in intellectual property law."""
    expert_type = ExpertType.IP
    _keywords = [
        "patent", "trademark", "copyright", "trade secret", "infringement",
        "license", "royalty", "fair use", "dmca", "invention", "claim",
        "prior art", "novelty", "obviousness", "registration",
    ]
    _base_confidence = 0.45


class TaxExpert(BaseLegalExpert):
    """Expert in tax law and IRS matters."""
    expert_type = ExpertType.TAX
    _keywords = [
        "tax", "irs", "deduction", "income", "capital gains", "audit",
        "501c3", "nonprofit", "depreciation", "basis", "withholding",
        "estate tax", "gift tax", "1031 exchange", "tax lien",
    ]
    _base_confidence = 0.45


class FamilyLawExpert(BaseLegalExpert):
    """Expert in family, divorce, and custody law."""
    expert_type = ExpertType.FAMILY_LAW
    _keywords = [
        "divorce", "custody", "child support", "alimony", "spousal",
        "prenuptial", "adoption", "guardianship", "domestic violence",
        "separation", "visitation", "parenting plan", "marital",
    ]
    _base_confidence = 0.45


class CriminalExpert(BaseLegalExpert):
    """Expert in criminal defense and prosecution."""
    expert_type = ExpertType.CRIMINAL
    _keywords = [
        "criminal", "felony", "misdemeanor", "arrest", "indictment",
        "plea", "bail", "sentence", "probation", "parole", "miranda",
        "fourth amendment", "search warrant", "grand jury", "acquittal",
    ]
    _base_confidence = 0.45


class RealEstateExpert(BaseLegalExpert):
    """Expert in real estate and property law."""
    expert_type = ExpertType.REAL_ESTATE
    _keywords = [
        "property", "deed", "mortgage", "foreclosure", "easement",
        "zoning", "title", "closing", "escrow", "landlord", "tenant",
        "lease", "eviction", "lien", "real estate",
    ]
    _base_confidence = 0.45


class EmploymentExpert(BaseLegalExpert):
    """Expert in employment and labor law."""
    expert_type = ExpertType.EMPLOYMENT
    _keywords = [
        "employment", "wrongful termination", "discrimination", "harassment",
        "wage", "overtime", "fmla", "ada", "title vii", "nlra",
        "non-compete", "severance", "workers compensation", "osha",
    ]
    _base_confidence = 0.45


EXPERT_REGISTRY: Dict[ExpertType, BaseLegalExpert] = {
    ExpertType.TRUST_LAW: TrustLawExpert(),
    ExpertType.CORPORATE: CorporateExpert(),
    ExpertType.IP: IPExpert(),
    ExpertType.TAX: TaxExpert(),
    ExpertType.FAMILY_LAW: FamilyLawExpert(),
    ExpertType.CRIMINAL: CriminalExpert(),
    ExpertType.REAL_ESTATE: RealEstateExpert(),
    ExpertType.EMPLOYMENT: EmploymentExpert(),
}
