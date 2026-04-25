"""
Core Event Hub - Pub/Sub pattern implementation for SintraPrime UniVerse.

Provides real-time event distribution with:
- Publisher/Subscriber pattern
- Event registration & routing
- Subscriber management
- Event serialization
- Dead-letter queue handling
"""

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
import threading
from queue import Queue, Full, Empty

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Standard event types in the system."""
    AGENT_CREATED = "agent.created"
    AGENT_UPDATED = "agent.updated"
    AGENT_DELETED = "agent.deleted"
    TASK_CREATED = "task.created"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    WEBHOOK_RECEIVED = "webhook.received"
    ALERT_TRIGGERED = "alert.triggered"
    METRICS_UPDATED = "metrics.updated"
    SYSTEM_ERROR = "system.error"
    INTEGRATION_CONNECTED = "integration.connected"
    INTEGRATION_DISCONNECTED = "integration.disconnected"


@dataclass
class Event:
    """Represents a single event in the system."""
    event_type: str
    source: str
    agent_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    priority: int = 0  # 0=normal, 1=high, -1=low
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    expires_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Serialize event to JSON."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> "Event":
        """Deserialize event from JSON."""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class DeadLetterEvent:
    """Represents an event that failed processing."""
    event: Event
    error: str
    subscriber_id: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    retry_count: int = 0


class EventHub:
    """
    Central event hub for pub/sub pattern.
    
    Features:
    - Subscribe to specific event types
    - Publish events to subscribers
    - Async event processing
    - Dead-letter queue for failed events
    - Event metrics & monitoring
    """
    
    def __init__(self, max_queue_size: int = 10000, dlq_size: int = 1000):
        """
        Initialize EventHub.
        
        Args:
            max_queue_size: Maximum size of subscriber queues
            dlq_size: Maximum size of dead-letter queue
        """
        self.max_queue_size = max_queue_size
        self.dlq_size = dlq_size
        
        # Subscriber management
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.async_subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.wildcard_subscribers: List[Callable] = []
        
        # Event tracking
        self.events_published = 0
        self.events_processed = 0
        self.events_failed = 0
        
        # Dead-letter queue
        self.dead_letter_queue: Queue = Queue(maxsize=dlq_size)
        
        # Thread safety
        self._lock = threading.RLock()
        self._async_loop: Optional[asyncio.AbstractEventLoop] = None
        
        logger.info("EventHub initialized with max_queue_size=%d, dlq_size=%d",
                   max_queue_size, dlq_size)
    
    def subscribe(self, event_type: str, callback: Callable) -> str:
        """
        Subscribe to events of a specific type.
        
        Args:
            event_type: Type of events to subscribe to
            callback: Function to call when event is published
            
        Returns:
            Subscription ID
        """
        with self._lock:
            if event_type == "*":
                self.wildcard_subscribers.append(callback)
            else:
                self.subscribers[event_type].append(callback)
            
            sub_id = str(uuid.uuid4())
            logger.info("Subscription created: %s for event_type=%s", sub_id, event_type)
            return sub_id
    
    def subscribe_async(self, event_type: str, callback: Callable) -> str:
        """
        Subscribe to events with async callback.
        
        Args:
            event_type: Type of events to subscribe to
            callback: Async function to call when event is published
            
        Returns:
            Subscription ID
        """
        with self._lock:
            self.async_subscribers[event_type].append(callback)
            sub_id = str(uuid.uuid4())
            logger.info("Async subscription created: %s for event_type=%s", sub_id, event_type)
            return sub_id
    
    def unsubscribe(self, event_type: str, callback: Callable) -> bool:
        """
        Unsubscribe from events.
        
        Args:
            event_type: Type of events to unsubscribe from
            callback: Callback to remove
            
        Returns:
            True if unsubscribed, False if callback not found
        """
        with self._lock:
            if event_type == "*":
                if callback in self.wildcard_subscribers:
                    self.wildcard_subscribers.remove(callback)
                    return True
            elif event_type in self.subscribers and callback in self.subscribers[event_type]:
                self.subscribers[event_type].remove(callback)
                return True
            
            return False
    
    def publish(self, event: Event) -> bool:
        """
        Publish an event to all subscribers.
        
        Args:
            event: Event to publish
            
        Returns:
            True if published successfully
        """
        with self._lock:
            self.events_published += 1
            
            # Get subscribers for this event type
            callbacks = self.subscribers.get(event.event_type, []).copy()
            callbacks.extend(self.wildcard_subscribers)
            
            if not callbacks:
                logger.debug("No subscribers for event type: %s", event.event_type)
                return True
            
            # Call all subscribers
            failed_callbacks = []
            for callback in callbacks:
                try:
                    callback(event)
                    self.events_processed += 1
                except Exception as e:
                    logger.error("Error in subscriber callback: %s", str(e))
                    self.events_failed += 1
                    failed_callbacks.append((callback, event, str(e)))
            
            # Handle failed events
            for callback, evt, error in failed_callbacks:
                self._add_to_dlq(evt, error, callback.__name__)
            
            return True
    
    async def publish_async(self, event: Event) -> bool:
        """
        Publish an event asynchronously.
        
        Args:
            event: Event to publish
            
        Returns:
            True if published successfully
        """
        with self._lock:
            self.events_published += 1
            
            # Get subscribers for this event type
            callbacks = self.async_subscribers.get(event.event_type, []).copy()
            
            # Also publish to sync subscribers
            sync_callbacks = self.subscribers.get(event.event_type, []).copy()
            sync_callbacks.extend(self.wildcard_subscribers)
            
            failed_events = []
            
            # Process async subscribers
            tasks = []
            for callback in callbacks:
                try:
                    task = callback(event)
                    if asyncio.iscoroutine(task):
                        tasks.append(task)
                except Exception as e:
                    logger.error("Error scheduling async subscriber: %s", str(e))
                    failed_events.append((event, str(e), callback.__name__))
            
            # Wait for all async tasks
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        logger.error("Async subscriber error: %s", str(result))
                        self.events_failed += 1
                    else:
                        self.events_processed += 1
            
            # Process sync subscribers
            for callback in sync_callbacks:
                try:
                    callback(event)
                    self.events_processed += 1
                except Exception as e:
                    logger.error("Error in sync subscriber: %s", str(e))
                    self.events_failed += 1
                    failed_events.append((event, str(e), callback.__name__))
            
            # Handle failed events
            for evt, error, subscriber_id in failed_events:
                self._add_to_dlq(evt, error, subscriber_id)
            
            return True
    
    def _add_to_dlq(self, event: Event, error: str, subscriber_id: str) -> None:
        """Add event to dead-letter queue."""
        dlq_event = DeadLetterEvent(
            event=event,
            error=error,
            subscriber_id=subscriber_id
        )
        try:
            self.dead_letter_queue.put_nowait(dlq_event)
        except Full:
            logger.warning("Dead-letter queue is full, dropping event")
    
    def get_dlq_events(self, count: int = 10) -> List[DeadLetterEvent]:
        """
        Retrieve events from dead-letter queue.
        
        Args:
            count: Number of events to retrieve
            
        Returns:
            List of dead-letter events
        """
        events = []
        for _ in range(count):
            try:
                event = self.dead_letter_queue.get_nowait()
                events.append(event)
            except Empty:
                break
        return events
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get event hub metrics.
        
        Returns:
            Dictionary of metrics
        """
        with self._lock:
            return {
                "events_published": self.events_published,
                "events_processed": self.events_processed,
                "events_failed": self.events_failed,
                "dlq_size": self.dead_letter_queue.qsize(),
                "subscriber_count": sum(len(v) for v in self.subscribers.values()),
                "async_subscriber_count": sum(len(v) for v in self.async_subscribers.values()),
                "wildcard_subscriber_count": len(self.wildcard_subscribers),
            }
    
    def reset_metrics(self) -> None:
        """Reset event hub metrics."""
        with self._lock:
            self.events_published = 0
            self.events_processed = 0
            self.events_failed = 0
            logger.info("Metrics reset")
