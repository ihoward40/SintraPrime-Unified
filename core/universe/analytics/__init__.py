"""
Analytics Package - SintraPrime UniVerse Analytics Engine
Provides comprehensive metrics collection, analysis, and reporting
"""

from .analytics_engine import (
    AnalyticsEngine,
    Metric,
    MetricType,
    TimeSeriesBuffer,
    MetricsCache,
    AggregationEngine
)

from .metrics_collector import (
    MetricsCollector,
    Counter,
    Gauge,
    Histogram,
    Timer,
    MetricEvent,
    EventBuffer
)

from .anomaly_detector import (
    AnomalyDetector,
    Anomaly,
    StatisticalDetector,
    IsolationForestDetector,
    ThresholdDetector,
    TrendAnalyzer
)

from .cost_analyzer import (
    CostAnalyzer,
    CostTracker,
    BudgetManager,
    CostForecaster,
    CostEntry,
    TokenCostCalculator
)

from .query_engine import (
    QueryEngine,
    QueryExecutor,
    QueryParser,
    QueryBuilder,
    QueryResult,
    ExportFormatter
)

__version__ = "1.0.0"
__all__ = [
    # Analytics Engine
    'AnalyticsEngine',
    'Metric',
    'MetricType',
    'TimeSeriesBuffer',
    'MetricsCache',
    'AggregationEngine',
    
    # Metrics Collector
    'MetricsCollector',
    'Counter',
    'Gauge',
    'Histogram',
    'Timer',
    'MetricEvent',
    'EventBuffer',
    
    # Anomaly Detector
    'AnomalyDetector',
    'Anomaly',
    'StatisticalDetector',
    'IsolationForestDetector',
    'ThresholdDetector',
    'TrendAnalyzer',
    
    # Cost Analyzer
    'CostAnalyzer',
    'CostTracker',
    'BudgetManager',
    'CostForecaster',
    'CostEntry',
    'TokenCostCalculator',
    
    # Query Engine
    'QueryEngine',
    'QueryExecutor',
    'QueryParser',
    'QueryBuilder',
    'QueryResult',
    'ExportFormatter',
]
