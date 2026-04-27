"""Phase 16F — Advanced Analytics Engine."""
from __future__ import annotations
import time
import uuid
import math
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    RATE = "rate"


class AggregationMethod(str, Enum):
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    P50 = "p50"
    P95 = "p95"
    P99 = "p99"


class TrendDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


@dataclass
class DataPoint:
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Metric:
    metric_id: str
    name: str
    metric_type: MetricType
    unit: str = ""
    description: str = ""
    data_points: List[DataPoint] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def add_point(self, value: float, labels: Optional[Dict[str, str]] = None,
                  timestamp: Optional[float] = None) -> DataPoint:
        dp = DataPoint(
            timestamp=timestamp if timestamp is not None else time.time(),
            value=value,
            labels=labels or {},
        )
        self.data_points.append(dp)
        return dp

    @property
    def latest_value(self) -> Optional[float]:
        if not self.data_points:
            return None
        return max(self.data_points, key=lambda p: p.timestamp).value

    @property
    def point_count(self) -> int:
        return len(self.data_points)


@dataclass
class AggregationResult:
    metric_name: str
    method: AggregationMethod
    value: float
    window_start: float
    window_end: float
    point_count: int


@dataclass
class TrendAnalysis:
    metric_name: str
    direction: TrendDirection
    slope: float
    r_squared: float
    forecast_next: float
    confidence: float


@dataclass
class Anomaly:
    anomaly_id: str
    metric_name: str
    timestamp: float
    value: float
    expected_value: float
    deviation_sigma: float
    severity: str  # "low", "medium", "high", "critical"


@dataclass
class Dashboard:
    dashboard_id: str
    name: str
    metric_ids: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricRegistry:
    """Stores and retrieves metrics."""

    def __init__(self):
        self._metrics: Dict[str, Metric] = {}

    def register(self, name: str, metric_type: MetricType,
                 unit: str = "", description: str = "") -> Metric:
        metric = Metric(
            metric_id=f"met_{uuid.uuid4().hex[:8]}",
            name=name,
            metric_type=metric_type,
            unit=unit,
            description=description,
        )
        self._metrics[name] = metric
        return metric

    def get(self, name: str) -> Optional[Metric]:
        return self._metrics.get(name)

    def record(self, name: str, value: float,
               labels: Optional[Dict[str, str]] = None,
               timestamp: Optional[float] = None) -> DataPoint:
        metric = self._metrics.get(name)
        if not metric:
            raise KeyError(f"Metric '{name}' not registered")
        return metric.add_point(value, labels=labels, timestamp=timestamp)

    def list_metrics(self) -> List[Metric]:
        return list(self._metrics.values())

    def delete(self, name: str) -> bool:
        if name in self._metrics:
            del self._metrics[name]
            return True
        return False


class Aggregator:
    """Computes aggregations over metric data points."""

    def aggregate(self, metric: Metric, method: AggregationMethod,
                  window_seconds: Optional[float] = None) -> AggregationResult:
        points = metric.data_points
        if window_seconds:
            cutoff = time.time() - window_seconds
            points = [p for p in points if p.timestamp >= cutoff]

        values = [p.value for p in points]
        if not values:
            return AggregationResult(
                metric_name=metric.name,
                method=method,
                value=0.0,
                window_start=0.0,
                window_end=time.time(),
                point_count=0,
            )

        window_start = min(p.timestamp for p in points)
        window_end = max(p.timestamp for p in points)

        result_value = self._compute(values, method)
        return AggregationResult(
            metric_name=metric.name,
            method=method,
            value=result_value,
            window_start=window_start,
            window_end=window_end,
            point_count=len(values),
        )

    def _compute(self, values: List[float], method: AggregationMethod) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        if method == AggregationMethod.SUM:
            return sum(values)
        elif method == AggregationMethod.AVG:
            return sum(values) / len(values)
        elif method == AggregationMethod.MIN:
            return min(values)
        elif method == AggregationMethod.MAX:
            return max(values)
        elif method == AggregationMethod.COUNT:
            return float(len(values))
        elif method == AggregationMethod.P50:
            return self._percentile(sorted_vals, 50)
        elif method == AggregationMethod.P95:
            return self._percentile(sorted_vals, 95)
        elif method == AggregationMethod.P99:
            return self._percentile(sorted_vals, 99)
        return 0.0

    def _percentile(self, sorted_vals: List[float], pct: int) -> float:
        if not sorted_vals:
            return 0.0
        idx = (len(sorted_vals) - 1) * pct / 100
        lower = int(idx)
        upper = min(lower + 1, len(sorted_vals) - 1)
        frac = idx - lower
        return sorted_vals[lower] + frac * (sorted_vals[upper] - sorted_vals[lower])


class TrendAnalyzer:
    """Linear regression-based trend analysis."""

    def analyze(self, metric: Metric, window_seconds: Optional[float] = None) -> TrendAnalysis:
        points = metric.data_points
        if window_seconds:
            cutoff = time.time() - window_seconds
            points = [p for p in points if p.timestamp >= cutoff]

        if len(points) < 2:
            return TrendAnalysis(
                metric_name=metric.name,
                direction=TrendDirection.FLAT,
                slope=0.0,
                r_squared=0.0,
                forecast_next=points[0].value if points else 0.0,
                confidence=0.0,
            )

        # Normalize timestamps to avoid floating point issues
        t0 = points[0].timestamp
        xs = [p.timestamp - t0 for p in points]
        ys = [p.value for p in points]
        slope, intercept, r_sq = self._linear_regression(xs, ys)

        # Forecast next point (one average interval ahead)
        avg_interval = (xs[-1] - xs[0]) / (len(xs) - 1) if len(xs) > 1 else 1.0
        forecast = slope * (xs[-1] + avg_interval) + intercept

        if abs(slope) < 1e-9:
            direction = TrendDirection.FLAT
        elif slope > 0:
            direction = TrendDirection.UP
        else:
            direction = TrendDirection.DOWN

        return TrendAnalysis(
            metric_name=metric.name,
            direction=direction,
            slope=slope,
            r_squared=r_sq,
            forecast_next=forecast,
            confidence=min(r_sq, 1.0),
        )

    def _linear_regression(self, xs: List[float], ys: List[float]) -> Tuple[float, float, float]:
        n = len(xs)
        sum_x = sum(xs)
        sum_y = sum(ys)
        sum_xx = sum(x * x for x in xs)
        sum_xy = sum(x * y for x, y in zip(xs, ys))
        denom = n * sum_xx - sum_x * sum_x
        if abs(denom) < 1e-12:
            return 0.0, sum_y / n, 0.0
        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n
        # R²
        y_mean = sum_y / n
        ss_tot = sum((y - y_mean) ** 2 for y in ys)
        if ss_tot < 1e-12:
            return slope, intercept, 1.0
        y_pred = [slope * x + intercept for x in xs]
        ss_res = sum((y - yp) ** 2 for y, yp in zip(ys, y_pred))
        r_sq = max(0.0, 1.0 - ss_res / ss_tot)
        return slope, intercept, r_sq


class AnomalyDetector:
    """Z-score based anomaly detection."""

    def __init__(self, sigma_threshold: float = 3.0):
        self.sigma_threshold = sigma_threshold

    def detect(self, metric: Metric, window_seconds: Optional[float] = None) -> List[Anomaly]:
        points = metric.data_points
        if window_seconds:
            cutoff = time.time() - window_seconds
            points = [p for p in points if p.timestamp >= cutoff]

        if len(points) < 3:
            return []

        values = [p.value for p in points]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance) if variance > 0 else 0.0

        if std == 0.0:
            return []

        anomalies = []
        for point in points:
            z = abs(point.value - mean) / std
            if z >= self.sigma_threshold:
                severity = "low"
                if z >= 5:
                    severity = "critical"
                elif z >= 4:
                    severity = "high"
                elif z >= 3.5:
                    severity = "medium"
                anomalies.append(Anomaly(
                    anomaly_id=f"ano_{uuid.uuid4().hex[:8]}",
                    metric_name=metric.name,
                    timestamp=point.timestamp,
                    value=point.value,
                    expected_value=mean,
                    deviation_sigma=z,
                    severity=severity,
                ))
        return anomalies


class DashboardManager:
    """Manages analytics dashboards."""

    def __init__(self):
        self._dashboards: Dict[str, Dashboard] = {}

    def create(self, name: str, metric_ids: Optional[List[str]] = None) -> Dashboard:
        dash = Dashboard(
            dashboard_id=f"dash_{uuid.uuid4().hex[:8]}",
            name=name,
            metric_ids=metric_ids or [],
        )
        self._dashboards[dash.dashboard_id] = dash
        return dash

    def add_metric(self, dashboard_id: str, metric_id: str) -> Dashboard:
        dash = self._get(dashboard_id)
        if metric_id not in dash.metric_ids:
            dash.metric_ids.append(metric_id)
        return dash

    def remove_metric(self, dashboard_id: str, metric_id: str) -> Dashboard:
        dash = self._get(dashboard_id)
        dash.metric_ids = [m for m in dash.metric_ids if m != metric_id]
        return dash

    def get(self, dashboard_id: str) -> Optional[Dashboard]:
        return self._dashboards.get(dashboard_id)

    def list_dashboards(self) -> List[Dashboard]:
        return list(self._dashboards.values())

    def delete(self, dashboard_id: str) -> bool:
        if dashboard_id in self._dashboards:
            del self._dashboards[dashboard_id]
            return True
        return False

    def _get(self, dashboard_id: str) -> Dashboard:
        dash = self._dashboards.get(dashboard_id)
        if not dash:
            raise KeyError(f"Dashboard {dashboard_id} not found")
        return dash


class AdvancedAnalyticsEngine:
    """Top-level analytics engine combining all sub-systems."""

    def __init__(self, anomaly_sigma: float = 3.0):
        self.registry = MetricRegistry()
        self.aggregator = Aggregator()
        self.trend_analyzer = TrendAnalyzer()
        self.anomaly_detector = AnomalyDetector(sigma_threshold=anomaly_sigma)
        self.dashboards = DashboardManager()

    def track(self, name: str, value: float,
              metric_type: MetricType = MetricType.GAUGE,
              labels: Optional[Dict[str, str]] = None,
              unit: str = "",
              timestamp: Optional[float] = None) -> DataPoint:
        """Auto-register and record a metric in one call."""
        if not self.registry.get(name):
            self.registry.register(name, metric_type, unit=unit)
        return self.registry.record(name, value, labels, timestamp)

    def summarize(self, name: str) -> Dict[str, Any]:
        """Return a full summary dict for a metric."""
        metric = self.registry.get(name)
        if not metric:
            raise KeyError(f"Metric '{name}' not found")
        agg = self.aggregator.aggregate(metric, AggregationMethod.AVG)
        trend = self.trend_analyzer.analyze(metric)
        anomalies = self.anomaly_detector.detect(metric)
        return {
            "name": name,
            "point_count": metric.point_count,
            "latest_value": metric.latest_value,
            "avg": agg.value,
            "trend_direction": trend.direction.value,
            "trend_slope": trend.slope,
            "forecast_next": trend.forecast_next,
            "anomaly_count": len(anomalies),
        }
