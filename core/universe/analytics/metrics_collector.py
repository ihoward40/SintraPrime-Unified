"""
Metrics Collector - Event capture and buffering system
Handles instrumentation, metric buffering, and batch writing
"""

import time
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue
import json


class MetricEventType(Enum):
    """Types of metric events"""
    COUNTER_INCREMENT = "counter_increment"
    GAUGE_SET = "gauge_set"
    HISTOGRAM_OBSERVE = "histogram_observe"
    TIMER_START = "timer_start"
    TIMER_END = "timer_end"
    EVENT = "event"


@dataclass
class MetricEvent:
    """Represents a single metric event"""
    event_type: str
    agent_id: str
    metric_name: str
    value: float = 0.0
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'event_type': self.event_type,
            'agent_id': self.agent_id,
            'metric_name': self.metric_name,
            'value': self.value,
            'tags': self.tags,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


class EventBuffer:
    """Circular buffer for metric events"""
    
    def __init__(self, max_size: int = 50000):
        self.max_size = max_size
        self.events: List[MetricEvent] = []
        self.lock = threading.RLock()
        self.write_count = 0
        
    def add(self, event: MetricEvent) -> None:
        """Add event to buffer"""
        with self.lock:
            self.events.append(event)
            self.write_count += 1
            if len(self.events) > self.max_size:
                self.events.pop(0)  # FIFO eviction
                
    def get_all(self) -> List[MetricEvent]:
        """Get all events"""
        with self.lock:
            return self.events.copy()
            
    def clear(self) -> None:
        """Clear all events"""
        with self.lock:
            self.events.clear()
            
    def get_since(self, timestamp: datetime) -> List[MetricEvent]:
        """Get events since timestamp"""
        with self.lock:
            return [e for e in self.events if e.timestamp >= timestamp]


class Counter:
    """Thread-safe counter metric"""
    
    def __init__(self, agent_id: str, metric_name: str, 
                 collector: 'MetricsCollector', tags: Optional[Dict[str, str]] = None):
        self.agent_id = agent_id
        self.metric_name = metric_name
        self.collector = collector
        self.tags = tags or {}
        self.value = 0
        self.lock = threading.RLock()
        
    def increment(self, amount: float = 1.0) -> None:
        """Increment counter"""
        with self.lock:
            self.value += amount
        event = MetricEvent(
            event_type=MetricEventType.COUNTER_INCREMENT.value,
            agent_id=self.agent_id,
            metric_name=self.metric_name,
            value=amount,
            tags=self.tags
        )
        self.collector.record_event(event)


class Gauge:
    """Thread-safe gauge metric"""
    
    def __init__(self, agent_id: str, metric_name: str,
                 collector: 'MetricsCollector', tags: Optional[Dict[str, str]] = None):
        self.agent_id = agent_id
        self.metric_name = metric_name
        self.collector = collector
        self.tags = tags or {}
        self.value = 0.0
        self.lock = threading.RLock()
        
    def set(self, value: float) -> None:
        """Set gauge value"""
        with self.lock:
            self.value = value
        event = MetricEvent(
            event_type=MetricEventType.GAUGE_SET.value,
            agent_id=self.agent_id,
            metric_name=self.metric_name,
            value=value,
            tags=self.tags
        )
        self.collector.record_event(event)
        
    def get(self) -> float:
        """Get current value"""
        with self.lock:
            return self.value


class Histogram:
    """Thread-safe histogram metric"""
    
    def __init__(self, agent_id: str, metric_name: str,
                 collector: 'MetricsCollector', tags: Optional[Dict[str, str]] = None,
                 buckets: Optional[List[float]] = None):
        self.agent_id = agent_id
        self.metric_name = metric_name
        self.collector = collector
        self.tags = tags or {}
        self.buckets = buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self.observations: List[float] = []
        self.lock = threading.RLock()
        
    def observe(self, value: float) -> None:
        """Record observation"""
        with self.lock:
            self.observations.append(value)
        event = MetricEvent(
            event_type=MetricEventType.HISTOGRAM_OBSERVE.value,
            agent_id=self.agent_id,
            metric_name=self.metric_name,
            value=value,
            tags=self.tags
        )
        self.collector.record_event(event)


class Timer:
    """Context manager for timing operations"""
    
    def __init__(self, agent_id: str, metric_name: str,
                 collector: 'MetricsCollector', tags: Optional[Dict[str, str]] = None):
        self.agent_id = agent_id
        self.metric_name = metric_name
        self.collector = collector
        self.tags = tags or {}
        self.start_time = None
        
    def __enter__(self):
        """Start timer"""
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timer and record"""
        if self.start_time:
            duration = time.time() - self.start_time
            event = MetricEvent(
                event_type=MetricEventType.TIMER_END.value,
                agent_id=self.agent_id,
                metric_name=self.metric_name,
                value=duration * 1000,  # Convert to milliseconds
                tags=self.tags,
                metadata={'duration_seconds': duration}
            )
            self.collector.record_event(event)
        return False


class MetricsCollector:
    """Central metrics collection and instrumentation system"""
    
    def __init__(self, batch_size: int = 1000, flush_interval_seconds: int = 5):
        self.batch_size = batch_size
        self.flush_interval = flush_interval_seconds
        self.event_buffer = EventBuffer()
        self.write_queue: Queue[MetricEvent] = Queue()
        self.metric_instances: Dict[str, Any] = {}
        self.write_callbacks: List[Callable] = []
        self.lock = threading.RLock()
        self.running = True
        
        # Start background flush thread
        self.flush_thread = threading.Thread(target=self._flush_worker, daemon=True)
        self.flush_thread.start()
        
    def counter(self, agent_id: str, metric_name: str,
               tags: Optional[Dict[str, str]] = None) -> Counter:
        """Create or get counter"""
        key = f"counter:{agent_id}:{metric_name}"
        with self.lock:
            if key not in self.metric_instances:
                self.metric_instances[key] = Counter(agent_id, metric_name, self, tags)
        return self.metric_instances[key]
        
    def gauge(self, agent_id: str, metric_name: str,
             tags: Optional[Dict[str, str]] = None) -> Gauge:
        """Create or get gauge"""
        key = f"gauge:{agent_id}:{metric_name}"
        with self.lock:
            if key not in self.metric_instances:
                self.metric_instances[key] = Gauge(agent_id, metric_name, self, tags)
        return self.metric_instances[key]
        
    def histogram(self, agent_id: str, metric_name: str,
                 tags: Optional[Dict[str, str]] = None,
                 buckets: Optional[List[float]] = None) -> Histogram:
        """Create or get histogram"""
        key = f"histogram:{agent_id}:{metric_name}"
        with self.lock:
            if key not in self.metric_instances:
                self.metric_instances[key] = Histogram(agent_id, metric_name, self, tags, buckets)
        return self.metric_instances[key]
        
    def timer(self, agent_id: str, metric_name: str,
             tags: Optional[Dict[str, str]] = None) -> Timer:
        """Create timer"""
        return Timer(agent_id, metric_name, self, tags)
        
    def record_event(self, event: MetricEvent) -> None:
        """Record a metric event"""
        self.event_buffer.add(event)
        self.write_queue.put(event)
        
    def register_write_callback(self, callback: Callable) -> None:
        """Register callback for batch writes"""
        with self.lock:
            self.write_callbacks.append(callback)
            
    def _flush_worker(self) -> None:
        """Background worker that flushes events periodically"""
        while self.running:
            time.sleep(self.flush_interval)
            self.flush()
            
    def flush(self) -> None:
        """Flush buffered events"""
        batch = []
        while len(batch) < self.batch_size:
            try:
                event = self.write_queue.get_nowait()
                batch.append(event)
            except:
                break
                
        if batch:
            with self.lock:
                for callback in self.write_callbacks:
                    try:
                        callback(batch)
                    except Exception as e:
                        print(f"Error in write callback: {e}")
                        
    def get_buffer_stats(self) -> Dict[str, Any]:
        """Get buffer statistics"""
        return {
            'buffer_size': len(self.event_buffer.get_all()),
            'queue_size': self.write_queue.qsize(),
            'metrics_instances': len(self.metric_instances)
        }
        
    def shutdown(self) -> None:
        """Gracefully shutdown collector"""
        self.running = False
        self.flush()
        if self.flush_thread.is_alive():
            self.flush_thread.join(timeout=5)
