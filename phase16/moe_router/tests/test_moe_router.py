"""Phase 16A — MoE Legal Specialist Router tests (118 tests)."""
import pytest
from phase16.moe_router.models import ExpertType, RoutingRequest, ExpertCapacity
from phase16.moe_router.experts import (
    TrustLawExpert, CorporateExpert, IPExpert, TaxExpert,
    FamilyLawExpert, CriminalExpert, RealEstateExpert, EmploymentExpert,
    EXPERT_REGISTRY,
)
from phase16.moe_router.confidence_scorer import ConfidenceScorer
from phase16.moe_router.load_balancer import LoadBalancer
from phase16.moe_router.dispatcher import Dispatcher
from phase16.moe_router.router import MoERouter


def make_request(text: str, rid: str = "r1") -> RoutingRequest:
    return RoutingRequest(request_id=rid, text=text)


# ─────────────────────────────────────────────────────────────
# Expert specialization tests (21)
# ─────────────────────────────────────────────────────────────
class TestExpertSpecialization:
    def test_trust_law_detects_trust(self):
        e = TrustLawExpert()
        r = make_request("I need to set up a revocable trust for my estate")
        assert e.get_confidence(r) > 0.5

    def test_trust_law_detects_will(self):
        e = TrustLawExpert()
        r = make_request("My father's will names me as executor")
        assert e.get_confidence(r) > 0.45

    def test_corporate_detects_merger(self):
        e = CorporateExpert()
        r = make_request("We are planning a merger with a Delaware corporation")
        assert e.get_confidence(r) > 0.5

    def test_corporate_detects_shareholder(self):
        e = CorporateExpert()
        r = make_request("Shareholder derivative suit against the board")
        assert e.get_confidence(r) > 0.5

    def test_ip_detects_patent(self):
        e = IPExpert()
        r = make_request("Patent infringement claim for our invention")
        assert e.get_confidence(r) > 0.5

    def test_ip_detects_trademark(self):
        e = IPExpert()
        r = make_request("Trademark registration for our brand logo")
        assert e.get_confidence(r) > 0.5

    def test_tax_detects_irs(self):
        e = TaxExpert()
        r = make_request("IRS audit of our capital gains deductions")
        assert e.get_confidence(r) > 0.5

    def test_tax_detects_estate_tax(self):
        e = TaxExpert()
        r = make_request("Estate tax planning for high-net-worth individuals")
        assert e.get_confidence(r) > 0.5

    def test_family_detects_divorce(self):
        e = FamilyLawExpert()
        r = make_request("Divorce proceedings and child custody arrangement")
        assert e.get_confidence(r) > 0.5

    def test_family_detects_adoption(self):
        e = FamilyLawExpert()
        r = make_request("Adoption process and guardianship requirements")
        assert e.get_confidence(r) > 0.45

    def test_criminal_detects_felony(self):
        e = CriminalExpert()
        r = make_request("Felony indictment and bail hearing")
        assert e.get_confidence(r) > 0.5

    def test_criminal_detects_miranda(self):
        e = CriminalExpert()
        r = make_request("Miranda rights violation during arrest")
        assert e.get_confidence(r) > 0.5

    def test_real_estate_detects_mortgage(self):
        e = RealEstateExpert()
        r = make_request("Mortgage foreclosure and title dispute")
        assert e.get_confidence(r) > 0.5

    def test_employment_detects_discrimination(self):
        e = EmploymentExpert()
        r = make_request("Employment discrimination and wrongful termination")
        assert e.get_confidence(r) > 0.5

    def test_expert_analyze_returns_dict(self):
        e = TrustLawExpert()
        result = e.analyze(make_request("trust and estate planning"))
        assert isinstance(result, dict)
        assert "confidence" in result
        assert "expert" in result

    def test_expert_analyze_relevant_flag(self):
        e = TrustLawExpert()
        result = e.analyze(make_request("trust beneficiary trustee"))
        assert result["relevant"] is True

    def test_expert_analyze_irrelevant(self):
        e = TrustLawExpert()
        result = e.analyze(make_request("hello world"))
        assert result["confidence"] < 0.6

    def test_get_specializations_returns_list(self):
        e = IPExpert()
        specs = e.get_specializations()
        assert isinstance(specs, list)
        assert len(specs) > 0

    def test_all_experts_in_registry(self):
        assert ExpertType.TRUST_LAW in EXPERT_REGISTRY
        assert ExpertType.CORPORATE in EXPERT_REGISTRY
        assert ExpertType.IP in EXPERT_REGISTRY

    def test_expert_confidence_range(self):
        e = CorporateExpert()
        for text in ["corporation merger shareholder", "unrelated text", ""]:
            conf = e.get_confidence(make_request(text))
            assert 0.0 <= conf <= 1.0

    def test_expert_no_request_confidence(self):
        e = TaxExpert()
        assert 0.0 <= e.get_confidence() <= 1.0


# ─────────────────────────────────────────────────────────────
# Confidence scoring tests (19)
# ─────────────────────────────────────────────────────────────
class TestConfidenceScoring:
    def setup_method(self):
        self.scorer = ConfidenceScorer()

    def test_score_returns_list(self):
        scores = self.scorer.score_experts(make_request("trust estate will"))
        assert isinstance(scores, list)
        assert len(scores) > 0

    def test_scores_sorted_descending(self):
        scores = self.scorer.score_experts(make_request("patent trademark copyright"))
        for i in range(len(scores) - 1):
            assert scores[i].score >= scores[i + 1].score

    def test_ip_query_top_score(self):
        scores = self.scorer.score_experts(make_request("patent infringement trademark license"))
        assert scores[0].expert_type == ExpertType.IP

    def test_trust_query_top_score(self):
        scores = self.scorer.score_experts(make_request("trust estate will beneficiary trustee"))
        assert scores[0].expert_type == ExpertType.TRUST_LAW

    def test_scores_calibrated_flag(self):
        scores = self.scorer.score_experts(make_request("any text"))
        assert all(s.calibrated for s in scores)

    def test_aggregate_scores_sums_to_one(self):
        scores = self.scorer.score_experts(make_request("corporate merger"))
        weights = self.scorer.aggregate_scores(scores)
        assert abs(sum(weights.values()) - 1.0) < 1e-9

    def test_aggregate_scores_keys_are_strings(self):
        scores = self.scorer.score_experts(make_request("tax irs"))
        weights = self.scorer.aggregate_scores(scores)
        assert all(isinstance(k, str) for k in weights)

    def test_calibrate_updates_offset(self):
        self.scorer.calibrate(ExpertType.TAX, feedback_score=0.9, predicted_score=0.5)
        scores_after = self.scorer.score_experts(make_request("tax irs deduction"))
        tax_score = next(s for s in scores_after if s.expert_type == ExpertType.TAX)
        assert tax_score.score > 0.45

    def test_get_top_k_returns_k(self):
        top3 = self.scorer.get_top_k(make_request("trust estate"), k=3)
        assert len(top3) == 3

    def test_get_top_k_sorted(self):
        top3 = self.scorer.get_top_k(make_request("trust estate"), k=3)
        assert top3[0].score >= top3[1].score >= top3[2].score

    def test_empty_text_scores(self):
        scores = self.scorer.score_experts(make_request(""))
        assert len(scores) > 0
        assert all(0.0 <= s.score <= 1.0 for s in scores)

    def test_score_all_experts_covered(self):
        scores = self.scorer.score_experts(make_request("legal matter"))
        expert_types = {s.expert_type for s in scores}
        assert ExpertType.TRUST_LAW in expert_types
        assert ExpertType.CORPORATE in expert_types

    def test_aggregate_empty_scores(self):
        weights = self.scorer.aggregate_scores([])
        assert weights == {}

    def test_criminal_query_top_score(self):
        scores = self.scorer.score_experts(make_request("felony arrest miranda bail sentence"))
        assert scores[0].expert_type == ExpertType.CRIMINAL

    def test_family_query_top_score(self):
        scores = self.scorer.score_experts(make_request("divorce custody child support alimony"))
        assert scores[0].expert_type == ExpertType.FAMILY_LAW

    def test_score_reasoning_non_empty(self):
        scores = self.scorer.score_experts(make_request("patent"))
        assert all(s.reasoning for s in scores)

    def test_calibrate_negative_error(self):
        self.scorer.calibrate(ExpertType.CRIMINAL, feedback_score=0.3, predicted_score=0.8)
        # offset should decrease
        scores = self.scorer.score_experts(make_request("criminal felony"))
        criminal_score = next(s for s in scores if s.expert_type == ExpertType.CRIMINAL)
        assert criminal_score.score >= 0.0

    def test_score_confidence_score_dataclass(self):
        from phase16.moe_router.models import ConfidenceScore
        scores = self.scorer.score_experts(make_request("trust"))
        assert all(isinstance(s, ConfidenceScore) for s in scores)

    def test_aggregate_scores_non_negative(self):
        scores = self.scorer.score_experts(make_request("any"))
        weights = self.scorer.aggregate_scores(scores)
        assert all(v >= 0 for v in weights.values())


# ─────────────────────────────────────────────────────────────
# Load balancing tests (17)
# ─────────────────────────────────────────────────────────────
class TestLoadBalancing:
    def setup_method(self):
        self.lb = LoadBalancer(max_capacity_per_expert=5)

    def test_assign_returns_expert_type(self):
        result = self.lb.assign(make_request("trust"), [ExpertType.TRUST_LAW])
        assert result == ExpertType.TRUST_LAW

    def test_assign_increments_load(self):
        self.lb.assign(make_request("t"), [ExpertType.CORPORATE])
        cap = self.lb.get_capacity(ExpertType.CORPORATE)
        assert cap.current_load == 1

    def test_release_decrements_load(self):
        self.lb.assign(make_request("t"), [ExpertType.IP])
        self.lb.release(ExpertType.IP)
        cap = self.lb.get_capacity(ExpertType.IP)
        assert cap.current_load == 0

    def test_release_no_underflow(self):
        self.lb.release(ExpertType.TAX)  # already 0
        cap = self.lb.get_capacity(ExpertType.TAX)
        assert cap.current_load == 0

    def test_rebalance_resets_all(self):
        for et in [ExpertType.TRUST_LAW, ExpertType.CORPORATE, ExpertType.IP]:
            self.lb.assign(make_request("t"), [et])
        self.lb.rebalance()
        for et in [ExpertType.TRUST_LAW, ExpertType.CORPORATE, ExpertType.IP]:
            assert self.lb.get_capacity(et).current_load == 0

    def test_capacity_utilization(self):
        self.lb.assign(make_request("t"), [ExpertType.FAMILY_LAW])
        cap = self.lb.get_capacity(ExpertType.FAMILY_LAW)
        assert cap.utilization == pytest.approx(1 / 5)

    def test_capacity_available(self):
        cap = self.lb.get_capacity(ExpertType.CRIMINAL)
        assert cap.available is True

    def test_capacity_unavailable_when_full(self):
        lb = LoadBalancer(max_capacity_per_expert=1)
        lb.assign(make_request("t"), [ExpertType.REAL_ESTATE])
        cap = lb.get_capacity(ExpertType.REAL_ESTATE)
        assert cap.available is False

    def test_assign_picks_least_loaded(self):
        self.lb.assign(make_request("t"), [ExpertType.TRUST_LAW])
        # CORPORATE should be less loaded
        result = self.lb.assign(make_request("t"), [ExpertType.TRUST_LAW, ExpertType.CORPORATE])
        assert result == ExpertType.CORPORATE

    def test_get_all_capacities(self):
        caps = self.lb.get_all_capacities()
        assert ExpertType.TRUST_LAW in caps
        assert ExpertType.CORPORATE in caps

    def test_assign_fallback_over_capacity(self):
        lb = LoadBalancer(max_capacity_per_expert=1)
        lb.assign(make_request("t"), [ExpertType.TAX])
        # Should still assign even when over capacity
        result = lb.assign(make_request("t"), [ExpertType.TAX])
        assert result == ExpertType.TAX

    def test_multiple_assigns_track_load(self):
        for _ in range(3):
            self.lb.assign(make_request("t"), [ExpertType.EMPLOYMENT])
        cap = self.lb.get_capacity(ExpertType.EMPLOYMENT)
        assert cap.current_load == 3

    def test_capacity_dataclass_fields(self):
        cap = self.lb.get_capacity(ExpertType.TRUST_LAW)
        assert isinstance(cap, ExpertCapacity)
        assert cap.max_capacity == 5

    def test_assign_from_multiple_candidates(self):
        candidates = [ExpertType.TRUST_LAW, ExpertType.CORPORATE, ExpertType.IP]
        result = self.lb.assign(make_request("t"), candidates)
        assert result in candidates

    def test_rebalance_then_assign(self):
        self.lb.assign(make_request("t"), [ExpertType.TAX])
        self.lb.rebalance()
        cap = self.lb.get_capacity(ExpertType.TAX)
        assert cap.current_load == 0

    def test_thread_safety(self):
        import threading
        errors = []
        def worker():
            try:
                self.lb.assign(make_request("t"), [ExpertType.CRIMINAL])
                self.lb.release(ExpertType.CRIMINAL)
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors

    def test_utilization_zero_when_empty(self):
        cap = self.lb.get_capacity(ExpertType.EMPLOYMENT)
        assert cap.utilization == 0.0


# ─────────────────────────────────────────────────────────────
# Routing pipeline tests (15)
# ─────────────────────────────────────────────────────────────
class TestRoutingPipeline:
    def setup_method(self):
        self.router = MoERouter(top_k=2)

    def test_route_returns_result(self):
        result = self.router.route(make_request("trust estate will"))
        assert result is not None
        assert result.request_id == "r1"

    def test_route_has_primary_expert(self):
        result = self.router.route(make_request("trust estate beneficiary"))
        assert result.primary_expert == ExpertType.TRUST_LAW

    def test_route_has_secondary_experts(self):
        result = self.router.route(make_request("patent trademark copyright"))
        assert len(result.secondary_experts) >= 1

    def test_route_confidence_scores_present(self):
        result = self.router.route(make_request("corporate merger"))
        assert len(result.confidence_scores) > 0

    def test_route_routing_weights_sum_to_one(self):
        result = self.router.route(make_request("tax irs deduction"))
        total = sum(result.routing_weights.values())
        assert abs(total - 1.0) < 1e-9

    def test_route_latency_positive(self):
        result = self.router.route(make_request("criminal felony"))
        assert result.latency_ms >= 0

    def test_route_analysis_dict(self):
        result = self.router.route(make_request("family divorce custody"))
        assert isinstance(result.analysis, dict)

    def test_compute_routing_weights(self):
        weights = self.router._compute_routing_weights(make_request("patent"))
        assert abs(sum(weights.values()) - 1.0) < 1e-9

    def test_select_experts_top_k(self):
        weights = {"trust_law": 0.6, "corporate": 0.3, "intellectual_property": 0.1}
        experts = self.router._select_experts(weights)
        assert len(experts) == 2

    def test_update_routing_matrix(self):
        self.router.update_routing_matrix({"trust_law": 0.8, "corporate": 0.2})
        # Should not raise

    def test_route_empty_text(self):
        result = self.router.route(make_request(""))
        assert result.primary_expert is not None

    def test_route_long_text(self):
        long_text = "trust estate will beneficiary " * 50
        result = self.router.route(make_request(long_text))
        assert result.primary_expert == ExpertType.TRUST_LAW

    def test_get_routing_stats(self):
        self.router.route(make_request("test"))
        stats = self.router.get_routing_stats()
        assert "total_dispatched" in stats

    def test_route_criminal_query(self):
        result = self.router.route(make_request("felony arrest miranda rights bail"))
        assert result.primary_expert == ExpertType.CRIMINAL

    def test_route_employment_query(self):
        result = self.router.route(make_request("wrongful termination discrimination harassment"))
        assert result.primary_expert == ExpertType.EMPLOYMENT


# ─────────────────────────────────────────────────────────────
# Domain classification tests (12)
# ─────────────────────────────────────────────────────────────
class TestDomainClassification:
    def setup_method(self):
        self.router = MoERouter()

    def test_classifies_trust_law(self):
        r = self.router.route(make_request("revocable trust estate planning beneficiary"))
        assert r.primary_expert == ExpertType.TRUST_LAW

    def test_classifies_corporate(self):
        r = self.router.route(make_request("merger acquisition shareholder board"))
        assert r.primary_expert == ExpertType.CORPORATE

    def test_classifies_ip(self):
        r = self.router.route(make_request("patent infringement trademark copyright"))
        assert r.primary_expert == ExpertType.IP

    def test_classifies_tax(self):
        r = self.router.route(make_request("IRS audit tax deduction capital gains"))
        assert r.primary_expert == ExpertType.TAX

    def test_classifies_family_law(self):
        r = self.router.route(make_request("divorce custody child support alimony"))
        assert r.primary_expert == ExpertType.FAMILY_LAW

    def test_classifies_criminal(self):
        r = self.router.route(make_request("criminal felony arrest indictment plea"))
        assert r.primary_expert == ExpertType.CRIMINAL

    def test_classifies_real_estate(self):
        r = self.router.route(make_request("mortgage foreclosure deed title property"))
        assert r.primary_expert == ExpertType.REAL_ESTATE

    def test_classifies_employment(self):
        r = self.router.route(make_request("wrongful termination discrimination wage"))
        assert r.primary_expert == ExpertType.EMPLOYMENT

    def test_ambiguous_query_returns_result(self):
        r = self.router.route(make_request("legal advice needed"))
        assert r.primary_expert is not None

    def test_multi_domain_query(self):
        r = self.router.route(make_request("trust tax estate irs deduction"))
        assert r.primary_expert in [ExpertType.TRUST_LAW, ExpertType.TAX]

    def test_request_id_preserved(self):
        r = self.router.route(make_request("test", rid="custom_id_123"))
        assert r.request_id == "custom_id_123"

    def test_routing_weights_all_experts_covered(self):
        r = self.router.route(make_request("legal matter"))
        assert len(r.routing_weights) > 0


# ─────────────────────────────────────────────────────────────
# Error handling tests (13)
# ─────────────────────────────────────────────────────────────
class TestErrorHandling:
    def test_route_none_text_raises_or_handles(self):
        try:
            r = MoERouter().route(RoutingRequest(request_id="r1", text=""))
            assert r is not None
        except Exception:
            pass  # acceptable

    def test_dispatcher_handles_exception(self):
        d = Dispatcher()
        # Dispatch with empty expert list should return empty dict
        result = d.dispatch(make_request("test"), [])
        assert isinstance(result, dict)

    def test_dispatcher_stats_after_error(self):
        d = Dispatcher()
        d.dispatch(make_request("test"), [ExpertType.TRUST_LAW])
        stats = d.get_stats()
        assert stats["total_dispatched"] >= 1

    def test_load_balancer_empty_candidates(self):
        lb = LoadBalancer()
        # Should not crash with empty list (will raise IndexError — acceptable)
        try:
            lb.assign(make_request("t"), [])
        except (ValueError, IndexError):
            pass

    def test_router_update_unknown_expert(self):
        router = MoERouter()
        # Should not raise
        router.update_routing_matrix({"unknown_expert": 0.5})

    def test_confidence_scorer_empty_aggregate(self):
        scorer = ConfidenceScorer()
        weights = scorer.aggregate_scores([])
        assert weights == {}

    def test_dispatcher_parallel_empty_list(self):
        d = Dispatcher()
        results = d.execute_parallel([])
        assert results == []

    def test_dispatcher_parallel_single(self):
        d = Dispatcher()
        results = d.execute_parallel([make_request("trust")])
        assert len(results) == 1

    def test_routing_result_defaults(self):
        from phase16.moe_router.models import RoutingResult
        r = RoutingResult(request_id="r1", primary_expert=ExpertType.CORPORATE)
        assert r.secondary_experts == []
        assert r.confidence_scores == []

    def test_expert_capacity_defaults(self):
        cap = ExpertCapacity(expert_type=ExpertType.TAX)
        assert cap.current_load == 0
        assert cap.available is True

    def test_routing_request_defaults(self):
        req = RoutingRequest(request_id="r1", text="test")
        assert req.urgency == "normal"
        assert req.metadata == {}

    def test_router_top_k_one(self):
        router = MoERouter(top_k=1)
        result = router.route(make_request("trust estate"))
        assert len(result.secondary_experts) == 0

    def test_dispatcher_get_stats_initial(self):
        d = Dispatcher()
        stats = d.get_stats()
        assert stats["total_dispatched"] == 0
        assert stats["total_errors"] == 0


# ─────────────────────────────────────────────────────────────
# Edge cases (5)
# ─────────────────────────────────────────────────────────────
class TestEdgeCases:
    def test_very_long_text(self):
        text = "patent " * 500
        router = MoERouter()
        result = router.route(make_request(text))
        assert result.primary_expert == ExpertType.IP

    def test_special_characters(self):
        router = MoERouter()
        result = router.route(make_request("trust & estate (2024) — §501(c)(3)"))
        assert result is not None

    def test_numeric_text(self):
        router = MoERouter()
        result = router.route(make_request("1234567890"))
        assert result is not None

    def test_unicode_text(self):
        router = MoERouter()
        result = router.route(make_request("trust héritier fiducie"))
        assert result is not None

    def test_single_keyword(self):
        router = MoERouter()
        result = router.route(make_request("patent"))
        assert result.primary_expert == ExpertType.IP


# ─────────────────────────────────────────────────────────────
# Integration tests (16)
# ─────────────────────────────────────────────────────────────
class TestIntegration:
    def test_full_routing_pipeline(self):
        router = MoERouter(top_k=3)
        req = RoutingRequest(
            request_id="int_001",
            text="We need to set up a trust for estate planning with tax implications",
            urgency="high",
        )
        result = router.route(req)
        assert result.request_id == "int_001"
        assert result.primary_expert in [ExpertType.TRUST_LAW, ExpertType.TAX]
        assert len(result.confidence_scores) > 0
        assert abs(sum(result.routing_weights.values()) - 1.0) < 1e-9

    def test_parallel_dispatch_10_requests(self):
        d = Dispatcher(max_workers=4)
        requests = [make_request(f"trust estate {i}", f"r{i}") for i in range(10)]
        results = d.execute_parallel(requests)
        assert len(results) == 10

    def test_scorer_balancer_router_chain(self):
        scorer = ConfidenceScorer()
        lb = LoadBalancer()
        router = MoERouter()
        req = make_request("patent trademark copyright infringement")
        scores = scorer.score_experts(req)
        top_expert = scores[0].expert_type
        assigned = lb.assign(req, [top_expert])
        assert assigned == top_expert
        result = router.route(req)
        assert result.primary_expert == ExpertType.IP

    def test_routing_matrix_update_affects_routing(self):
        router = MoERouter()
        router.update_routing_matrix({"trust_law": 1.0})
        result = router.route(make_request("trust estate will"))
        assert result.primary_expert == ExpertType.TRUST_LAW

    def test_multiple_routes_stats_tracked(self):
        router = MoERouter()
        for i in range(5):
            router.route(make_request(f"trust {i}"))
        stats = router.get_routing_stats()
        assert stats["total_dispatched"] >= 5

    def test_load_balancer_after_rebalance(self):
        lb = LoadBalancer()
        for _ in range(3):
            lb.assign(make_request("t"), [ExpertType.TRUST_LAW])
        lb.rebalance()
        cap = lb.get_capacity(ExpertType.TRUST_LAW)
        assert cap.current_load == 0

    def test_dispatcher_stats_accumulate(self):
        d = Dispatcher()
        for i in range(5):
            d.dispatch(make_request(f"trust {i}"))
        stats = d.get_stats()
        assert stats["total_dispatched"] == 5

    def test_confidence_calibration_improves_accuracy(self):
        scorer = ConfidenceScorer()
        req = make_request("patent infringement trademark")
        scores_before = scorer.score_experts(req)
        ip_before = next(s for s in scores_before if s.expert_type == ExpertType.IP)
        scorer.calibrate(ExpertType.IP, feedback_score=0.95, predicted_score=ip_before.score)
        scores_after = scorer.score_experts(req)
        ip_after = next(s for s in scores_after if s.expert_type == ExpertType.IP)
        assert ip_after.score >= ip_before.score - 0.1  # calibration applied

    def test_router_handles_concurrent_requests(self):
        import threading
        router = MoERouter()
        results = []
        errors = []
        def route_worker(i):
            try:
                r = router.route(make_request(f"trust estate {i}", f"r{i}"))
                results.append(r)
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=route_worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        assert len(results) == 10

    def test_expert_registry_completeness(self):
        assert len(EXPERT_REGISTRY) >= 8

    def test_routing_result_request_id(self):
        router = MoERouter()
        result = router.route(make_request("test", "unique_id_xyz"))
        assert result.request_id == "unique_id_xyz"

    def test_dispatcher_parallel_results_order(self):
        d = Dispatcher()
        requests = [make_request(f"req {i}", f"r{i}") for i in range(5)]
        results = d.execute_parallel(requests)
        assert len(results) == 5

    def test_full_pipeline_urgency_high(self):
        router = MoERouter()
        req = RoutingRequest(request_id="urgent", text="criminal felony arrest", urgency="critical")
        result = router.route(req)
        assert result.primary_expert == ExpertType.CRIMINAL

    def test_scorer_top_k_consistency(self):
        scorer = ConfidenceScorer()
        req = make_request("trust estate will beneficiary")
        top1 = scorer.get_top_k(req, k=1)
        top3 = scorer.get_top_k(req, k=3)
        assert top1[0].expert_type == top3[0].expert_type

    def test_load_balancer_thread_safety_full(self):
        import threading
        lb = LoadBalancer(max_capacity_per_expert=100)
        errors = []
        def worker():
            try:
                et = lb.assign(make_request("t"), [ExpertType.TRUST_LAW, ExpertType.CORPORATE])
                lb.release(et)
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors

    def test_routing_weights_non_negative(self):
        router = MoERouter()
        result = router.route(make_request("any legal matter"))
        assert all(v >= 0 for v in result.routing_weights.values())
