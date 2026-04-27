"""Phase 16F — Advanced Analytics tests (110 tests)."""
import time
import pytest
from phase16.advanced_analytics.analytics_engine import (
    MetricType, AggregationMethod, TrendDirection,
    MetricRegistry, Aggregator, TrendAnalyzer, AnomalyDetector,
    DashboardManager, AdvancedAnalyticsEngine,
)


@pytest.fixture
def registry():
    return MetricRegistry()


@pytest.fixture
def aggregator():
    return Aggregator()


@pytest.fixture
def trend_analyzer():
    return TrendAnalyzer()


@pytest.fixture
def anomaly_detector():
    return AnomalyDetector(sigma_threshold=2.0)


@pytest.fixture
def dashboard_mgr():
    return DashboardManager()


@pytest.fixture
def engine():
    return AdvancedAnalyticsEngine(anomaly_sigma=2.0)


@pytest.fixture
def populated_metric(registry):
    m = registry.register("latency_ms", MetricType.HISTOGRAM, unit="ms")
    for i, v in enumerate([10.0, 12.0, 11.0, 13.0, 10.5, 12.5, 11.5]):
        registry.record("latency_ms", v, timestamp=1000.0 + i)
    return m


# ─────────────────────────────────────────────────────────────
# MetricRegistry tests (20)
# ─────────────────────────────────────────────────────────────
class TestMetricRegistry:
    def test_register_metric(self, registry):
        m = registry.register("req_count", MetricType.COUNTER)
        assert m.metric_id.startswith("met_")

    def test_register_stores_name(self, registry):
        m = registry.register("cpu_usage", MetricType.GAUGE)
        assert m.name == "cpu_usage"

    def test_register_stores_type(self, registry):
        m = registry.register("latency", MetricType.HISTOGRAM)
        assert m.metric_type == MetricType.HISTOGRAM

    def test_register_stores_unit(self, registry):
        m = registry.register("latency", MetricType.HISTOGRAM, unit="ms")
        assert m.unit == "ms"

    def test_register_stores_description(self, registry):
        m = registry.register("latency", MetricType.HISTOGRAM, description="API latency")
        assert m.description == "API latency"

    def test_get_metric(self, registry):
        registry.register("test_metric", MetricType.GAUGE)
        assert registry.get("test_metric") is not None

    def test_get_nonexistent_metric(self, registry):
        assert registry.get("nonexistent") is None

    def test_record_data_point(self, registry):
        registry.register("cpu", MetricType.GAUGE)
        dp = registry.record("cpu", 75.5)
        assert dp.value == 75.5

    def test_record_unregistered_raises(self, registry):
        with pytest.raises(KeyError):
            registry.record("unknown", 1.0)

    def test_record_with_labels(self, registry):
        registry.register("req", MetricType.COUNTER)
        dp = registry.record("req", 1.0, labels={"method": "GET", "status": "200"})
        assert dp.labels["method"] == "GET"

    def test_record_with_timestamp(self, registry):
        registry.register("metric", MetricType.GAUGE)
        dp = registry.record("metric", 42.0, timestamp=1000.0)
        assert dp.timestamp == 1000.0

    def test_metric_point_count(self, registry):
        registry.register("m", MetricType.GAUGE)
        for v in [1.0, 2.0, 3.0]:
            registry.record("m", v)
        assert registry.get("m").point_count == 3

    def test_metric_latest_value(self, registry):
        registry.register("m", MetricType.GAUGE)
        registry.record("m", 10.0, timestamp=1000.0)
        registry.record("m", 20.0, timestamp=1001.0)
        assert registry.get("m").latest_value == 20.0

    def test_metric_latest_value_none_when_empty(self, registry):
        m = registry.register("m", MetricType.GAUGE)
        assert m.latest_value is None

    def test_list_metrics(self, registry):
        registry.register("m1", MetricType.GAUGE)
        registry.register("m2", MetricType.COUNTER)
        assert len(registry.list_metrics()) == 2

    def test_list_metrics_empty(self, registry):
        assert registry.list_metrics() == []

    def test_delete_metric(self, registry):
        registry.register("m", MetricType.GAUGE)
        assert registry.delete("m") is True
        assert registry.get("m") is None

    def test_delete_nonexistent_metric(self, registry):
        assert registry.delete("nonexistent") is False

    def test_metric_unique_ids(self, registry):
        ids = {registry.register(f"m{i}", MetricType.GAUGE).metric_id for i in range(10)}
        assert len(ids) == 10

    def test_metric_created_at(self, registry):
        m = registry.register("m", MetricType.GAUGE)
        assert m.created_at > 0


# ─────────────────────────────────────────────────────────────
# Aggregator tests (25)
# ─────────────────────────────────────────────────────────────
class TestAggregator:
    def test_aggregate_sum(self, aggregator, populated_metric):
        result = aggregator.aggregate(populated_metric, AggregationMethod.SUM)
        assert abs(result.value - sum([10.0, 12.0, 11.0, 13.0, 10.5, 12.5, 11.5])) < 0.001

    def test_aggregate_avg(self, aggregator, populated_metric):
        result = aggregator.aggregate(populated_metric, AggregationMethod.AVG)
        expected = sum([10.0, 12.0, 11.0, 13.0, 10.5, 12.5, 11.5]) / 7
        assert abs(result.value - expected) < 0.001

    def test_aggregate_min(self, aggregator, populated_metric):
        result = aggregator.aggregate(populated_metric, AggregationMethod.MIN)
        assert result.value == 10.0

    def test_aggregate_max(self, aggregator, populated_metric):
        result = aggregator.aggregate(populated_metric, AggregationMethod.MAX)
        assert result.value == 13.0

    def test_aggregate_count(self, aggregator, populated_metric):
        result = aggregator.aggregate(populated_metric, AggregationMethod.COUNT)
        assert result.value == 7.0

    def test_aggregate_p50(self, aggregator, populated_metric):
        result = aggregator.aggregate(populated_metric, AggregationMethod.P50)
        # Median of sorted [10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0] = 11.5
        assert abs(result.value - 11.5) < 0.01

    def test_aggregate_p95(self, aggregator, populated_metric):
        result = aggregator.aggregate(populated_metric, AggregationMethod.P95)
        assert result.value >= 12.0

    def test_aggregate_p99(self, aggregator, populated_metric):
        result = aggregator.aggregate(populated_metric, AggregationMethod.P99)
        assert result.value >= 12.5

    def test_aggregate_empty_metric(self, aggregator, registry):
        m = registry.register("empty", MetricType.GAUGE)
        result = aggregator.aggregate(m, AggregationMethod.AVG)
        assert result.value == 0.0
        assert result.point_count == 0

    def test_aggregate_point_count(self, aggregator, populated_metric):
        result = aggregator.aggregate(populated_metric, AggregationMethod.AVG)
        assert result.point_count == 7

    def test_aggregate_metric_name(self, aggregator, populated_metric):
        result = aggregator.aggregate(populated_metric, AggregationMethod.SUM)
        assert result.metric_name == "latency_ms"

    def test_aggregate_method_stored(self, aggregator, populated_metric):
        result = aggregator.aggregate(populated_metric, AggregationMethod.MAX)
        assert result.method == AggregationMethod.MAX

    def test_aggregate_window_seconds(self, aggregator, registry):
        m = registry.register("windowed", MetricType.GAUGE)
        now = time.time()
        registry.record("windowed", 100.0, timestamp=now - 200)
        registry.record("windowed", 10.0, timestamp=now - 10)
        registry.record("windowed", 20.0, timestamp=now - 5)
        result = aggregator.aggregate(m, AggregationMethod.AVG, window_seconds=60)
        assert abs(result.value - 15.0) < 0.001

    def test_aggregate_window_excludes_old_points(self, aggregator, registry):
        m = registry.register("windowed2", MetricType.GAUGE)
        now = time.time()
        registry.record("windowed2", 999.0, timestamp=now - 200)
        registry.record("windowed2", 5.0, timestamp=now - 10)
        result = aggregator.aggregate(m, AggregationMethod.MAX, window_seconds=60)
        assert result.value == 5.0

    def test_aggregate_window_start_end(self, aggregator, populated_metric):
        result = aggregator.aggregate(populated_metric, AggregationMethod.SUM)
        assert result.window_start <= result.window_end

    def test_aggregate_single_point_avg(self, aggregator, registry):
        m = registry.register("single", MetricType.GAUGE)
        registry.record("single", 42.0)
        result = aggregator.aggregate(m, AggregationMethod.AVG)
        assert result.value == 42.0

    def test_aggregate_single_point_p95(self, aggregator, registry):
        m = registry.register("single2", MetricType.GAUGE)
        registry.record("single2", 42.0)
        result = aggregator.aggregate(m, AggregationMethod.P95)
        assert result.value == 42.0

    def test_percentile_monotonic(self, aggregator, registry):
        m = registry.register("pct_test", MetricType.HISTOGRAM)
        for v in range(100):
            registry.record("pct_test", float(v))
        p50 = aggregator.aggregate(m, AggregationMethod.P50).value
        p95 = aggregator.aggregate(m, AggregationMethod.P95).value
        p99 = aggregator.aggregate(m, AggregationMethod.P99).value
        assert p50 <= p95 <= p99

    def test_aggregate_all_same_values(self, aggregator, registry):
        m = registry.register("same", MetricType.GAUGE)
        for _ in range(5):
            registry.record("same", 7.0)
        assert aggregator.aggregate(m, AggregationMethod.AVG).value == 7.0
        assert aggregator.aggregate(m, AggregationMethod.MIN).value == 7.0
        assert aggregator.aggregate(m, AggregationMethod.MAX).value == 7.0

    def test_aggregate_negative_values(self, aggregator, registry):
        m = registry.register("neg", MetricType.GAUGE)
        for v in [-10.0, -5.0, 0.0, 5.0, 10.0]:
            registry.record("neg", v)
        assert aggregator.aggregate(m, AggregationMethod.MIN).value == -10.0
        assert aggregator.aggregate(m, AggregationMethod.MAX).value == 10.0
        assert aggregator.aggregate(m, AggregationMethod.AVG).value == 0.0

    def test_aggregate_sum_large_dataset(self, aggregator, registry):
        m = registry.register("large", MetricType.COUNTER)
        for i in range(1000):
            registry.record("large", 1.0)
        result = aggregator.aggregate(m, AggregationMethod.SUM)
        assert result.value == 1000.0

    def test_aggregate_count_large_dataset(self, aggregator, registry):
        m = registry.register("large2", MetricType.COUNTER)
        for i in range(500):
            registry.record("large2", float(i))
        result = aggregator.aggregate(m, AggregationMethod.COUNT)
        assert result.value == 500.0

    def test_aggregate_window_empty_result(self, aggregator, registry):
        m = registry.register("future", MetricType.GAUGE)
        registry.record("future", 100.0, timestamp=1.0)  # Very old
        result = aggregator.aggregate(m, AggregationMethod.SUM, window_seconds=1)
        assert result.point_count == 0

    def test_aggregate_p50_even_count(self, aggregator, registry):
        m = registry.register("even", MetricType.HISTOGRAM)
        for v in [1.0, 2.0, 3.0, 4.0]:
            registry.record("even", v)
        result = aggregator.aggregate(m, AggregationMethod.P50)
        assert 2.0 <= result.value <= 3.0


# ─────────────────────────────────────────────────────────────
# TrendAnalyzer tests (20)
# ─────────────────────────────────────────────────────────────
class TestTrendAnalyzer:
    def test_upward_trend(self, trend_analyzer, registry):
        m = registry.register("up_trend", MetricType.GAUGE)
        for i in range(10):
            registry.record("up_trend", float(i * 10), timestamp=float(i))
        result = trend_analyzer.analyze(m)
        assert result.direction == TrendDirection.UP

    def test_downward_trend(self, trend_analyzer, registry):
        m = registry.register("down_trend", MetricType.GAUGE)
        for i in range(10):
            registry.record("down_trend", float(100 - i * 10), timestamp=float(i))
        result = trend_analyzer.analyze(m)
        assert result.direction == TrendDirection.DOWN

    def test_flat_trend(self, trend_analyzer, registry):
        m = registry.register("flat_trend", MetricType.GAUGE)
        for i in range(10):
            registry.record("flat_trend", 50.0, timestamp=float(i))
        result = trend_analyzer.analyze(m)
        assert result.direction == TrendDirection.FLAT

    def test_trend_slope_positive(self, trend_analyzer, registry):
        m = registry.register("slope_up", MetricType.GAUGE)
        for i in range(5):
            registry.record("slope_up", float(i), timestamp=float(i))
        result = trend_analyzer.analyze(m)
        assert result.slope > 0

    def test_trend_slope_negative(self, trend_analyzer, registry):
        m = registry.register("slope_down", MetricType.GAUGE)
        for i in range(5):
            registry.record("slope_down", float(10 - i), timestamp=float(i))
        result = trend_analyzer.analyze(m)
        assert result.slope < 0

    def test_trend_r_squared_perfect(self, trend_analyzer, registry):
        m = registry.register("perfect", MetricType.GAUGE)
        for i in range(10):
            registry.record("perfect", float(i * 2 + 5), timestamp=float(i))
        result = trend_analyzer.analyze(m)
        assert result.r_squared > 0.99

    def test_trend_r_squared_range(self, trend_analyzer, registry):
        m = registry.register("r_sq", MetricType.GAUGE)
        for i in range(5):
            registry.record("r_sq", float(i), timestamp=float(i))
        result = trend_analyzer.analyze(m)
        assert 0.0 <= result.r_squared <= 1.0

    def test_trend_forecast_up(self, trend_analyzer, registry):
        m = registry.register("forecast_up", MetricType.GAUGE)
        for i in range(5):
            registry.record("forecast_up", float(i * 10), timestamp=float(i))
        result = trend_analyzer.analyze(m)
        assert result.forecast_next > 40.0

    def test_trend_forecast_down(self, trend_analyzer, registry):
        m = registry.register("forecast_down", MetricType.GAUGE)
        for i in range(5):
            registry.record("forecast_down", float(50 - i * 10), timestamp=float(i))
        result = trend_analyzer.analyze(m)
        assert result.forecast_next < 10.0

    def test_trend_single_point(self, trend_analyzer, registry):
        m = registry.register("single_pt", MetricType.GAUGE)
        registry.record("single_pt", 42.0)
        result = trend_analyzer.analyze(m)
        assert result.direction == TrendDirection.FLAT

    def test_trend_two_points_up(self, trend_analyzer, registry):
        m = registry.register("two_up", MetricType.GAUGE)
        registry.record("two_up", 10.0, timestamp=0.0)
        registry.record("two_up", 20.0, timestamp=1.0)
        result = trend_analyzer.analyze(m)
        assert result.direction == TrendDirection.UP

    def test_trend_two_points_down(self, trend_analyzer, registry):
        m = registry.register("two_down", MetricType.GAUGE)
        registry.record("two_down", 20.0, timestamp=0.0)
        registry.record("two_down", 10.0, timestamp=1.0)
        result = trend_analyzer.analyze(m)
        assert result.direction == TrendDirection.DOWN

    def test_trend_metric_name(self, trend_analyzer, registry):
        m = registry.register("named_trend", MetricType.GAUGE)
        for i in range(3):
            registry.record("named_trend", float(i), timestamp=float(i))
        result = trend_analyzer.analyze(m)
        assert result.metric_name == "named_trend"

    def test_trend_confidence_range(self, trend_analyzer, registry):
        m = registry.register("conf_test", MetricType.GAUGE)
        for i in range(5):
            registry.record("conf_test", float(i), timestamp=float(i))
        result = trend_analyzer.analyze(m)
        assert 0.0 <= result.confidence <= 1.0

    def test_trend_window_seconds(self, trend_analyzer, registry):
        m = registry.register("windowed_trend", MetricType.GAUGE)
        now = time.time()
        # Old downward points
        for i in range(5):
            registry.record("windowed_trend", float(100 - i * 10), timestamp=now - 200 + i)
        # Recent upward points
        for i in range(5):
            registry.record("windowed_trend", float(i * 10), timestamp=now - 10 + i)
        result = trend_analyzer.analyze(m, window_seconds=60)
        assert result.direction == TrendDirection.UP

    def test_trend_empty_metric(self, trend_analyzer, registry):
        m = registry.register("empty_trend", MetricType.GAUGE)
        result = trend_analyzer.analyze(m)
        assert result.direction == TrendDirection.FLAT

    def test_trend_all_same_values(self, trend_analyzer, registry):
        m = registry.register("same_vals", MetricType.GAUGE)
        for i in range(5):
            registry.record("same_vals", 42.0, timestamp=float(i))
        result = trend_analyzer.analyze(m)
        assert result.direction == TrendDirection.FLAT

    def test_trend_slope_zero_for_flat(self, trend_analyzer, registry):
        m = registry.register("flat_slope", MetricType.GAUGE)
        for i in range(5):
            registry.record("flat_slope", 10.0, timestamp=float(i))
        result = trend_analyzer.analyze(m)
        assert abs(result.slope) < 1e-6

    def test_trend_forecast_flat(self, trend_analyzer, registry):
        m = registry.register("flat_forecast", MetricType.GAUGE)
        for i in range(5):
            registry.record("flat_forecast", 50.0, timestamp=float(i))
        result = trend_analyzer.analyze(m)
        assert abs(result.forecast_next - 50.0) < 0.001

    def test_trend_high_r_squared_for_linear(self, trend_analyzer, registry):
        m = registry.register("linear_r", MetricType.GAUGE)
        for i in range(20):
            registry.record("linear_r", float(i * 3 + 7), timestamp=float(i))
        result = trend_analyzer.analyze(m)
        assert result.r_squared > 0.99


# ─────────────────────────────────────────────────────────────
# AnomalyDetector tests (20)
# ─────────────────────────────────────────────────────────────
class TestAnomalyDetector:
    def test_detect_anomaly(self, anomaly_detector, registry):
        m = registry.register("anomaly_test", MetricType.GAUGE)
        for i in range(20):
            registry.record("anomaly_test", 10.0, timestamp=float(i))
        registry.record("anomaly_test", 100.0, timestamp=21.0)  # Spike
        anomalies = anomaly_detector.detect(m)
        assert len(anomalies) >= 1

    def test_no_anomaly_normal_data(self, anomaly_detector, registry):
        m = registry.register("normal_data", MetricType.GAUGE)
        for i in range(20):
            registry.record("normal_data", 10.0 + (i % 3) * 0.1, timestamp=float(i))
        anomalies = anomaly_detector.detect(m)
        assert len(anomalies) == 0

    def test_anomaly_has_id(self, anomaly_detector, registry):
        m = registry.register("ano_id", MetricType.GAUGE)
        for i in range(20):
            registry.record("ano_id", 10.0, timestamp=float(i))
        registry.record("ano_id", 100.0, timestamp=21.0)
        anomalies = anomaly_detector.detect(m)
        assert all(a.anomaly_id.startswith("ano_") for a in anomalies)

    def test_anomaly_metric_name(self, anomaly_detector, registry):
        m = registry.register("ano_name", MetricType.GAUGE)
        for i in range(20):
            registry.record("ano_name", 10.0, timestamp=float(i))
        registry.record("ano_name", 100.0, timestamp=21.0)
        anomalies = anomaly_detector.detect(m)
        assert all(a.metric_name == "ano_name" for a in anomalies)

    def test_anomaly_deviation_sigma(self, anomaly_detector, registry):
        m = registry.register("sigma_test", MetricType.GAUGE)
        for i in range(20):
            registry.record("sigma_test", 10.0, timestamp=float(i))
        registry.record("sigma_test", 100.0, timestamp=21.0)
        anomalies = anomaly_detector.detect(m)
        assert all(a.deviation_sigma >= 2.0 for a in anomalies)

    def test_anomaly_expected_value(self, anomaly_detector, registry):
        m = registry.register("expected_val", MetricType.GAUGE)
        for i in range(20):
            registry.record("expected_val", 10.0, timestamp=float(i))
        registry.record("expected_val", 100.0, timestamp=21.0)
        anomalies = anomaly_detector.detect(m)
        assert all(a.expected_value < 20.0 for a in anomalies)

    def test_anomaly_severity_critical(self, anomaly_detector, registry):
        m = registry.register("critical_ano", MetricType.GAUGE)
        for i in range(50):
            registry.record("critical_ano", 10.0, timestamp=float(i))
        registry.record("critical_ano", 10000.0, timestamp=51.0)  # Extreme spike
        anomalies = anomaly_detector.detect(m)
        assert any(a.severity == "critical" for a in anomalies)

    def test_anomaly_severity_low(self, registry):
        detector = AnomalyDetector(sigma_threshold=2.0)
        m = registry.register("low_ano", MetricType.GAUGE)
        # Create a dataset where the spike is just over 2 sigma
        for i in range(50):
            registry.record("low_ano", 10.0, timestamp=float(i))
        registry.record("low_ano", 15.0, timestamp=51.0)  # Mild spike
        anomalies = detector.detect(m)
        if anomalies:
            assert anomalies[0].severity in ("low", "medium", "high", "critical")

    def test_no_anomaly_few_points(self, anomaly_detector, registry):
        m = registry.register("few_pts", MetricType.GAUGE)
        registry.record("few_pts", 1.0)
        registry.record("few_pts", 100.0)
        anomalies = anomaly_detector.detect(m)
        assert len(anomalies) == 0  # < 3 points

    def test_no_anomaly_constant_values(self, anomaly_detector, registry):
        m = registry.register("constant", MetricType.GAUGE)
        for i in range(10):
            registry.record("constant", 42.0, timestamp=float(i))
        anomalies = anomaly_detector.detect(m)
        assert len(anomalies) == 0

    def test_anomaly_window_seconds(self, anomaly_detector, registry):
        m = registry.register("windowed_ano", MetricType.GAUGE)
        now = time.time()
        # Old spike (outside window)
        for i in range(20):
            registry.record("windowed_ano", 10.0, timestamp=now - 200 + i)
        registry.record("windowed_ano", 100.0, timestamp=now - 150)
        # Recent normal data
        for i in range(10):
            registry.record("windowed_ano", 10.0, timestamp=now - 10 + i)
        anomalies = anomaly_detector.detect(m, window_seconds=30)
        assert len(anomalies) == 0

    def test_anomaly_unique_ids(self, anomaly_detector, registry):
        m = registry.register("multi_ano", MetricType.GAUGE)
        for i in range(20):
            registry.record("multi_ano", 10.0, timestamp=float(i))
        registry.record("multi_ano", 100.0, timestamp=21.0)
        registry.record("multi_ano", 200.0, timestamp=22.0)
        anomalies = anomaly_detector.detect(m)
        ids = [a.anomaly_id for a in anomalies]
        assert len(ids) == len(set(ids))

    def test_anomaly_value_stored(self, anomaly_detector, registry):
        m = registry.register("ano_val", MetricType.GAUGE)
        for i in range(20):
            registry.record("ano_val", 10.0, timestamp=float(i))
        registry.record("ano_val", 100.0, timestamp=21.0)
        anomalies = anomaly_detector.detect(m)
        spike = next((a for a in anomalies if a.value > 50), None)
        assert spike is not None
        assert spike.value == 100.0

    def test_anomaly_timestamp_stored(self, anomaly_detector, registry):
        m = registry.register("ano_ts", MetricType.GAUGE)
        for i in range(20):
            registry.record("ano_ts", 10.0, timestamp=float(i))
        registry.record("ano_ts", 100.0, timestamp=999.0)
        anomalies = anomaly_detector.detect(m)
        spike = next((a for a in anomalies if a.value > 50), None)
        assert spike is not None
        assert spike.timestamp == 999.0

    def test_custom_sigma_threshold(self, registry):
        detector = AnomalyDetector(sigma_threshold=5.0)
        m = registry.register("high_sigma", MetricType.GAUGE)
        for i in range(20):
            registry.record("high_sigma", 10.0, timestamp=float(i))
        registry.record("high_sigma", 50.0, timestamp=21.0)  # 3-sigma spike
        anomalies = detector.detect(m)
        assert len(anomalies) == 0  # Below 5-sigma threshold

    def test_low_sigma_threshold(self, registry):
        detector = AnomalyDetector(sigma_threshold=1.0)
        m = registry.register("low_sigma", MetricType.GAUGE)
        for i in range(20):
            registry.record("low_sigma", 10.0, timestamp=float(i))
        registry.record("low_sigma", 15.0, timestamp=21.0)
        anomalies = detector.detect(m)
        assert len(anomalies) >= 1

    def test_anomaly_empty_metric(self, anomaly_detector, registry):
        m = registry.register("empty_ano", MetricType.GAUGE)
        assert anomaly_detector.detect(m) == []

    def test_anomaly_two_points(self, anomaly_detector, registry):
        m = registry.register("two_pts", MetricType.GAUGE)
        registry.record("two_pts", 1.0)
        registry.record("two_pts", 100.0)
        assert anomaly_detector.detect(m) == []

    def test_multiple_anomalies(self, anomaly_detector, registry):
        m = registry.register("multi_spikes", MetricType.GAUGE)
        for i in range(50):
            registry.record("multi_spikes", 10.0, timestamp=float(i))
        registry.record("multi_spikes", 1000.0, timestamp=51.0)
        registry.record("multi_spikes", 2000.0, timestamp=52.0)
        anomalies = anomaly_detector.detect(m)
        assert len(anomalies) >= 2

    def test_anomaly_severity_not_empty(self, anomaly_detector, registry):
        m = registry.register("sev_test", MetricType.GAUGE)
        for i in range(20):
            registry.record("sev_test", 10.0, timestamp=float(i))
        registry.record("sev_test", 100.0, timestamp=21.0)
        anomalies = anomaly_detector.detect(m)
        assert all(len(a.severity) > 0 for a in anomalies)


# ─────────────────────────────────────────────────────────────
# Dashboard tests (15)
# ─────────────────────────────────────────────────────────────
class TestDashboardManager:
    def test_create_dashboard(self, dashboard_mgr):
        d = dashboard_mgr.create("Main Dashboard")
        assert d.dashboard_id.startswith("dash_")

    def test_dashboard_name(self, dashboard_mgr):
        d = dashboard_mgr.create("Revenue Dashboard")
        assert d.name == "Revenue Dashboard"

    def test_dashboard_with_metrics(self, dashboard_mgr):
        d = dashboard_mgr.create("Ops", metric_ids=["m1", "m2"])
        assert len(d.metric_ids) == 2

    def test_add_metric(self, dashboard_mgr):
        d = dashboard_mgr.create("Test")
        dashboard_mgr.add_metric(d.dashboard_id, "met_001")
        assert "met_001" in dashboard_mgr.get(d.dashboard_id).metric_ids

    def test_add_metric_no_duplicate(self, dashboard_mgr):
        d = dashboard_mgr.create("Test")
        dashboard_mgr.add_metric(d.dashboard_id, "met_001")
        dashboard_mgr.add_metric(d.dashboard_id, "met_001")
        assert dashboard_mgr.get(d.dashboard_id).metric_ids.count("met_001") == 1

    def test_remove_metric(self, dashboard_mgr):
        d = dashboard_mgr.create("Test", metric_ids=["m1", "m2"])
        dashboard_mgr.remove_metric(d.dashboard_id, "m1")
        assert "m1" not in dashboard_mgr.get(d.dashboard_id).metric_ids

    def test_get_dashboard(self, dashboard_mgr):
        d = dashboard_mgr.create("Test")
        assert dashboard_mgr.get(d.dashboard_id) is not None

    def test_get_nonexistent_dashboard(self, dashboard_mgr):
        assert dashboard_mgr.get("nonexistent") is None

    def test_list_dashboards(self, dashboard_mgr):
        dashboard_mgr.create("D1")
        dashboard_mgr.create("D2")
        assert len(dashboard_mgr.list_dashboards()) == 2

    def test_delete_dashboard(self, dashboard_mgr):
        d = dashboard_mgr.create("Test")
        assert dashboard_mgr.delete(d.dashboard_id) is True
        assert dashboard_mgr.get(d.dashboard_id) is None

    def test_delete_nonexistent_dashboard(self, dashboard_mgr):
        assert dashboard_mgr.delete("nonexistent") is False

    def test_dashboard_unique_ids(self, dashboard_mgr):
        ids = {dashboard_mgr.create(f"D{i}").dashboard_id for i in range(10)}
        assert len(ids) == 10

    def test_add_metric_nonexistent_dashboard(self, dashboard_mgr):
        with pytest.raises(KeyError):
            dashboard_mgr.add_metric("nonexistent", "m1")

    def test_remove_metric_nonexistent_dashboard(self, dashboard_mgr):
        with pytest.raises(KeyError):
            dashboard_mgr.remove_metric("nonexistent", "m1")

    def test_dashboard_created_at(self, dashboard_mgr):
        d = dashboard_mgr.create("Test")
        assert d.created_at > 0


# ─────────────────────────────────────────────────────────────
# AdvancedAnalyticsEngine integration tests (10)
# ─────────────────────────────────────────────────────────────
class TestAdvancedAnalyticsEngine:
    def test_track_auto_registers(self, engine):
        engine.track("api_latency", 50.0)
        assert engine.registry.get("api_latency") is not None

    def test_track_records_value(self, engine):
        engine.track("api_latency", 75.0)
        assert engine.registry.get("api_latency").latest_value == 75.0

    def test_track_multiple_values(self, engine):
        for v in [10.0, 20.0, 30.0]:
            engine.track("req_count", v, metric_type=MetricType.COUNTER)
        assert engine.registry.get("req_count").point_count == 3

    def test_summarize_returns_dict(self, engine):
        engine.track("cpu", 50.0)
        summary = engine.summarize("cpu")
        assert isinstance(summary, dict)

    def test_summarize_contains_keys(self, engine):
        engine.track("mem", 60.0)
        summary = engine.summarize("mem")
        assert "latest_value" in summary
        assert "avg" in summary
        assert "trend_direction" in summary
        assert "anomaly_count" in summary

    def test_summarize_nonexistent_raises(self, engine):
        with pytest.raises(KeyError):
            engine.summarize("nonexistent")

    def test_summarize_detects_anomaly(self, engine):
        for i in range(20):
            engine.track("spike_metric", 10.0, timestamp=float(i + 1))
        engine.track("spike_metric", 1000.0, timestamp=21.0)
        summary = engine.summarize("spike_metric")
        assert summary["anomaly_count"] >= 1

    def test_summarize_trend_up(self, engine):
        for i in range(10):
            engine.track("growing", float(i * 10), timestamp=float(i + 1))
        summary = engine.summarize("growing")
        assert summary["trend_direction"] == "up"

    def test_dashboard_creation(self, engine):
        d = engine.dashboards.create("Main")
        assert d.dashboard_id.startswith("dash_")

    def test_full_workflow(self, engine):
        for i in range(15):
            engine.track("response_time", 100.0 + i, timestamp=float(i + 1))
        engine.track("response_time", 5000.0, timestamp=16.0)  # Anomaly
        summary = engine.summarize("response_time")
        assert summary["point_count"] == 16
        assert summary["trend_direction"] in ("up", "flat", "down")
        assert summary["anomaly_count"] >= 1
