"""
Event Router - Topic-based routing and event dispatch.

Features:
- Topic-based routing
- Priority queue support
- Event filtering & transformation
- Backpressure handling
- Async event dispatch
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from queue import PriorityQueue, Queue, Full, Empty
import time
import threading

from .event_hub import Event

logger = logging.getLogger(__name__)


@dataclass
class PrioritizedEvent:
    """Event with priority for queue ordering."""
    priority: int
    timestamp: float
    event: Event
    
    def __lt__(self, other):
        """Compare for priority queue."""
        if self.priority != other.priority:
            return self.priority > other.priority  # Higher priority first
        return self.timestamp < other.timestamp  # Earlier timestamp first


class EventRouter:
    """
    Routes events to subscribers based on topics.
    
    Supports:
    - Topic-based routing (hierarchical)
    - Priority queue processing
    - Event filtering
    - Event transformation
    - Backpressure handling
    """
    
    def __init__(self, max_queue_size: int = 5000, workers: int = 4):
        """
        Initialize EventRouter.
        
        Args:
            max_queue_size: Maximum queue size
            workers: Number of async workers
        """
        self.max_queue_size = max_queue_size
        self.workers = workers
        
        # Topic-based subscriptions
        self.topic_subscriptions: Dict[str, List[Callable]] = defaultdict(list)
        self.wildcard_topic_subscriptions: Dict[str, List[Callable]] = defaultdict(list)
        
        # Priority queue for events
        self.event_queue: PriorityQueue = PriorityQueue()
        self.processing_queue: Queue = Queue()
        
        # Filters and transformers
        self.filters: List[Callable] = []
        self.transformers: List[Callable] = []
        
        # Metrics
        self.routed_events = 0
        self.filtered_events = 0
        self.transformed_events = 0
        self.backpressure_drops = 0
        
        # Thread safety
        self._lock = threading.RLock()
        self._running = False
        self._worker_tasks: List[asyncio.Task] = []
    
    def subscribe_to_topic(self, topic: str, callback: Callable) -> str:
        """
        Subscribe to events on a specific topic.
        
        Topics support wildcards: "orders/*" matches "orders/created", "orders/updated"
        
        Args:
            topic: Topic pattern
            callback: Handler function
            
        Returns:
            Subscription ID
        """
        with self._lock:
            self.topic_subscriptions[topic].append(callback)
            logger.info("Subscribed to topic: %s", topic)
            return f"{topic}:{id(callback)}"
    
    def unsubscribe_from_topic(self, topic: str, callback: Callable) -> bool:
        """
        Unsubscribe from a topic.
        
        Args:
            topic: Topic pattern
            callback: Handler function
            
        Returns:
            True if unsubscribed
        """
        with self._lock:
            if topic in self.topic_subscriptions and callback in self.topic_subscriptions[topic]:
                self.topic_subscriptions[topic].remove(callback)
                return True
            return False
    
    def add_filter(self, filter_fn: Callable) -> None:
        """
        Add a filter to exclude events.
        
        Filter function should return True to keep event, False to filter out.
        
        Args:
            filter_fn: Filter function(event) -> bool
        """
        with self._lock:
            self.filters.append(filter_fn)
            logger.debug("Added filter: %s", filter_fn.__name__)
    
    def add_transformer(self, transformer_fn: Callable) -> None:
        """
        Add a transformer to modify events.
        
        Transformer should take an event and return modified event.
        
        Args:
            transformer_fn: Transformer function(event) -> event
        """
        with self._lock:
            self.transformers.append(transformer_fn)
            logger.debug("Added transformer: %s", transformer_fn.__name__)
    
    async def route_event(self, event: Event, topic: str) -> bool:
        """
        Route an event to subscribers of a topic.
        
        Args:
            event: Event to route
            topic: Topic path
            
        Returns:
            True if routed successfully
        """
        # Apply filters
        filters = self.filters.copy()
        for filter_fn in filters:
            try:
                if not filter_fn(event):
                    self.filtered_events += 1
                    logger.debug("Event filtered: %s", event.event_id)
                    return True  # Filtered out, not an error
            except Exception as e:
                logger.error("Error in filter: %s", str(e))
                return False
        
        # Apply transformers
        transformers = self.transformers.copy()
        for transformer_fn in transformers:
            try:
                event = transformer_fn(event)
                self.transformed_events += 1
            except Exception as e:
                logger.error("Error in transformer: %s", str(e))
                return False
        
        # Get matching subscribers
        subscribers = self._get_matching_subscribers(topic)
        
        if not subscribers:
            logger.debug("No subscribers for topic: %s", topic)
            return True
        
        # Add to priority queue
        try:
            prioritized = PrioritizedEvent(
                priority=event.priority,
                timestamp=time.time(),
                event=event
            )
            self.event_queue.put_nowait(prioritized)
            self.routed_events += 1
            return True
        except Full:
            self.backpressure_drops += 1
            logger.warning("Event queue full, dropping event")
            return False
    
    def _get_matching_subscribers(self, topic: str) -> List[Callable]:
        """
        Get all subscribers matching a topic pattern.
        
        Args:
            topic: Topic path
            
        Returns:
            List of subscriber callbacks
        """
        with self._lock:
            subscribers = []
            
            # Exact match
            if topic in self.topic_subscriptions:
                subscribers.extend(self.topic_subscriptions[topic])
            
            # Wildcard matching
            parts = topic.split("/")
            for i in range(len(parts)):
                pattern = "/".join(parts[:i+1]) + "/*"
                if pattern in self.wildcard_topic_subscriptions:
                    subscribers.extend(self.wildcard_topic_subscriptions[pattern])
            
            return subscribers
    
    async def dispatch_to_subscribers(self, event: Event, subscribers: List[Callable]) -> List[str]:
        """
        Dispatch event to multiple subscribers asynchronously.
        
        Args:
            event: Event to dispatch
            subscribers: List of subscriber callbacks
            
        Returns:
            List of failed subscriber IDs
        """
        failed = []
        tasks = []
        
        for subscriber in subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    tasks.append(self._safe_call_async(subscriber, event))
                else:
                    self._safe_call_sync(subscriber, event)
            except Exception as e:
                logger.error("Error dispatching to subscriber: %s", str(e))
                failed.append(subscriber.__name__)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error("Subscriber dispatch error: %s", str(result))
                    failed.append(subscribers[i].__name__)
        
        return failed
    
    async def _safe_call_async(self, fn: Callable, event: Event) -> None:
        """Safely call async function."""
        try:
            await fn(event)
        except Exception as e:
            logger.error("Error in async subscriber: %s", str(e))
            raise
    
    def _safe_call_sync(self, fn: Callable, event: Event) -> None:
        """Safely call sync function."""
        try:
            fn(event)
        except Exception as e:
            logger.error("Error in sync subscriber: %s", str(e))
            raise
    
    def enable_backpressure(self, enable: bool = True) -> None:
        """
        Enable/disable backpressure handling.
        
        When enabled, events exceeding queue capacity are dropped.
        
        Args:
            enable: True to enable backpressure
        """
        logger.info("Backpressure handling %s", "enabled" if enable else "disabled")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get router metrics.
        
        Returns:
            Dictionary of metrics
        """
        with self._lock:
            return {
                "routed_events": self.routed_events,
                "filtered_events": self.filtered_events,
                "transformed_events": self.transformed_events,
                "backpressure_drops": self.backpressure_drops,
                "queue_size": self.event_queue.qsize(),
                "topic_count": len(self.topic_subscriptions),
                "filter_count": len(self.filters),
                "transformer_count": len(self.transformers),
            }
