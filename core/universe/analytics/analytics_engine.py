"""
Analytics Engine - Core metrics aggregation and query system
Provides real-time metrics collection, time-series data management, and efficient caching
"""

import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import numpy as np
from enum import Enum


class MetricType(Enum):
    """Supported metric types"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Metric:
    """Represents a single metric data point"""
    agent_id: str
    metric_name: str
    metric_value: float
    metric_type: str
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'agent_id': self.agent_id,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'metric_type': self.metric_type,
            'timestamp': self.timestamp.isoformat(),
            'tags': self.tags
        }


class TimeSeriesBuffer:
    """Efficient time-series data storage with aggregation"""
    
    def __init__(self, max_size: int = 100000, ttl_hours: int = 24):
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)
        self.data: List[Metric] = []
        self.lock = threading.RLock()
        
    def add(self, metric: Metric) -> None:
        """Add metric to buffer"""
        with self.lock:
            self.data.append(metric)
            if len(self.data) > self.max_size:
                self._evict_old()
                
    def _evict_old(self) -> None:
        """Remove old metrics based on TTL"""
        cutoff = datetime.now() - self.ttl
        self.data = [m for m in self.data if m.timestamp > cutoff]
        
    def get_range(self, start: datetime, end: datetime) -> List[Metric]:
        """Get metrics within time range"""
        with self.lock:
            return [m for m in self.data if start <= m.timestamp <= end]
            
    def get_by_name(self, metric_name: str, start: datetime, 
                    end: datetime) -> List[Metric]:
        """Get specific metric within time range"""
        with self.lock:
            return [m for m in self.data 
                   if m.metric_name == metric_name and start <= m.timestamp <= end]


class MetricsCache:
    """In-memory cache with expiration"""
    
    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.lock = threading.RLock()
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        with self.lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl_seconds:
                    return value
                else:
                    del self.cache[key]
        return None
        
    def set(self, key: str, value: Any) -> None:
        """Set cache value"""
        with self.lock:
            self.cache[key] = (value, time.time())
            
    def invalidate(self, pattern: str) -> None:
        """Invalidate cache entries matching pattern"""
        with self.lock:
            keys_to_delete = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.cache[key]


class AggregationEngine:
    """Aggregates metrics across time and dimensions"""
    
    @staticmethod
    def sum(metrics: List[Metric]) -> float:
        """Sum metric values"""
        return sum(m.metric_value for m in metrics)
        
    @staticmethod
    def avg(metrics: List[Metric]) -> float:
        """Calculate average"""
        if not metrics:
            return 0.0
        return sum(m.metric_value for m in metrics) / len(metrics)
        
    @staticmethod
    def min(metrics: List[Metric]) -> float:
        """Get minimum value"""
        return min((m.metric_value for m in metrics), default=0.0)
        
    @staticmethod
    def max(metrics: List[Metric]) -> float:
        """Get maximum value"""
        return max((m.metric_value for m in metrics), default=0.0)
        
    @staticmethod
    def percentile(metrics: List[Metric], p: float) -> float:
        """Calculate percentile"""
        if not metrics:
            return 0.0
        values = sorted([m.metric_value for m in metrics])
        idx = int(len(values) * p / 100)
        return values[min(idx, len(values) - 1)]
        
    @staticmethod
    def rate(metrics: List[Metric]) -> float:
        """Calculate per-second rate"""
        if len(metrics) < 2:
            return 0.0
        sorted_metrics = sorted(metrics, key=lambda m: m.timestamp)
        time_diff = (sorted_metrics[-1].timestamp - sorted_metrics[0].timestamp).total_seconds()
        if time_diff == 0:
            return 0.0
        value_diff = sorted_metrics[-1].metric_value - sorted_metrics[0].metric_value
        return value_diff / time_diff
        
    @staticmethod
    def group_by(metrics: List[Metric], tag_key: str) -> Dict[str, List[Metric]]:
        """Group metrics by tag"""
        groups = defaultdict(list)
        for metric in metrics:
            key = metric.tags.get(tag_key, "unknown")
            groups[key].append(metric)
        return dict(groups)


class AnalyticsEngine:
    """Main analytics engine coordinating all operations"""
    
    def __init__(self, buffer_size: int = 100000, cache_ttl: int = 300):
        self.buffer = TimeSeriesBuffer(max_size=buffer_size)
        self.cache = MetricsCache(ttl_seconds=cache_ttl)
        self.aggregation = AggregationEngine()
        self.lock = threading.RLock()
        self.metrics_count = 0
        self.start_time = time.time()
        
    def record_metric(self, agent_id: str, metric_name: str, value: float,
                     metric_type: str = "gauge", tags: Optional[Dict[str, str]] = None) -> None:
        """Record a new metric"""
        metric = Metric(
            agent_id=agent_id,
            metric_name=metric_name,
            metric_value=value,
            metric_type=metric_type,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        with self.lock:
            self.buffer.add(metric)
            self.metrics_count += 1
        # Invalidate relevant caches - use metric_name:agent_id format to match cache_key
        self.cache.invalidate(f"{metric_name}:{agent_id}")
        
    def query(self, metric_name: str, agent_id: Optional[str] = None,
             start: Optional[datetime] = None, end: Optional[datetime] = None,
             tags: Optional[Dict[str, str]] = None) -> List[Metric]:
        """Query metrics with optional caching"""
        cache_key = f"query:{metric_name}:{agent_id}:{start}:{end}:{json.dumps(tags or {})}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
            
        start = start or (datetime.now() - timedelta(hours=1))
        end = end or datetime.now()
        
        metrics = self.buffer.get_by_name(metric_name, start, end)
        
        if agent_id:
            metrics = [m for m in metrics if m.agent_id == agent_id]
            
        if tags:
            for key, value in tags.items():
                metrics = [m for m in metrics if m.tags.get(key) == value]
                
        self.cache.set(cache_key, metrics)
        return metrics
        
    def aggregate(self, metric_name: str, operation: str = "avg",
                 agent_id: Optional[str] = None, 
                 start: Optional[datetime] = None,
                 end: Optional[datetime] = None) -> float:
        """Aggregate metrics using specified operation"""
        metrics = self.query(metric_name, agent_id, start, end)
        
        ops = {
            'sum': self.aggregation.sum,
            'avg': self.aggregation.avg,
            'min': self.aggregation.min,
            'max': self.aggregation.max,
            'rate': self.aggregation.rate,
        }
        
        op_func = ops.get(operation, self.aggregation.avg)
        return op_func(metrics)
        
    def get_percentile(self, metric_name: str, percentile: float = 95,
                      agent_id: Optional[str] = None,
                      start: Optional[datetime] = None,
                      end: Optional[datetime] = None) -> float:
        """Get metric percentile"""
        metrics = self.query(metric_name, agent_id, start, end)
        return self.aggregation.percentile(metrics, percentile)
        
    def group_metrics(self, metric_name: str, group_by: str,
                     agent_id: Optional[str] = None,
                     start: Optional[datetime] = None,
                     end: Optional[datetime] = None) -> Dict[str, float]:
        """Group metrics by tag and aggregate"""
        metrics = self.query(metric_name, agent_id, start, end)
        groups = self.aggregation.group_by(metrics, group_by)
        return {key: self.aggregation.avg(group_metrics) 
                for key, group_metrics in groups.items()}
        
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        uptime = time.time() - self.start_time
        throughput = self.metrics_count / uptime if uptime > 0 else 0
        return {
            'metrics_recorded': self.metrics_count,
            'uptime_seconds': uptime,
            'throughput_per_second': throughput,
            'buffer_size': len(self.buffer.data),
            'cache_size': len(self.cache.cache)
        }
        
    def clear_cache(self) -> None:
        """Clear all caches"""
        with self.cache.lock:
            self.cache.cache.clear()
