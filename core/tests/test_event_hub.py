"""
Comprehensive test suite for Event Hub system.

Tests cover:
- Pub/sub functionality
- Event routing
- Event persistence
- Filter logic
- WebSocket streaming
- Performance under load
"""

import asyncio
import json
import pytest
import time
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Import event hub modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from universe.event_hub import (
    EventHub, Event, EventRouter, EventStore, EventFilter, FilterEngine,
    WebSocketServer
)
from universe.event_hub.event_hub import EventType, DeadLetterEvent
from universe.event_hub.event_filters import FilterOperator, FilterBuilder


class TestEventClass:
    """Tests for Event data class."""
    
    def test_event_creation(self):
        """Test creating an event."""
        event = Event(
            event_type=EventType.AGENT_CREATED,
            source="test_agent",
            payload={"name": "test"}
        )
        assert event.event_type == EventType.AGENT_CREATED
        assert event.source == "test_agent"
        assert event.payload == {"name": "test"}
        assert event.event_id is not None
        assert event.timestamp is not None
    
    def test_event_to_json(self):
        """Test event serialization."""
        event = Event(
            event_type="test.event",
            source="test",
            payload={"key": "value"}
        )
        json_str = event.to_json()
        assert "test.event" in json_str
        assert "test" in json_str
    
    def test_event_from_json(self):
        """Test event deserialization."""
        event = Event(
            event_type="test.event",
            source="test",
            payload={"key": "value"},
            tags=["tag1"]
        )
        json_str = event.to_json()
        restored = Event.from_json(json_str)
        assert restored.event_type == event.event_type
        assert restored.source == event.source
        assert restored.tags == event.tags


class TestEventHub:
    """Tests for EventHub pub/sub functionality."""
    
    def test_hub_initialization(self):
        """Test EventHub initialization."""
        hub = EventHub(max_queue_size=5000, dlq_size=500)
        assert hub.max_queue_size == 5000
        assert hub.events_published == 0
        assert hub.events_processed == 0
    
    def test_subscribe_and_publish(self):
        """Test basic pub/sub."""
        hub = EventHub()
        events_received = []
        
        def callback(event):
            events_received.append(event)
        
        hub.subscribe(EventType.AGENT_CREATED, callback)
        
        event = Event(
            event_type=EventType.AGENT_CREATED,
            source="test"
        )
        hub.publish(event)
        
        assert len(events_received) == 1
        assert events_received[0].event_type == EventType.AGENT_CREATED
    
    def test_unsubscribe(self):
        """Test unsubscribing."""
        hub = EventHub()
        events_received = []
        
        def callback(event):
            events_received.append(event)
        
        sub_id = hub.subscribe(EventType.AGENT_CREATED, callback)
        hub.unsubscribe(EventType.AGENT_CREATED, callback)
        
        event = Event(event_type=EventType.AGENT_CREATED, source="test")
        hub.publish(event)
        
        assert len(events_received) == 0
    
    def test_wildcard_subscription(self):
        """Test wildcard subscription."""
        hub = EventHub()
        events_received = []
        
        def callback(event):
            events_received.append(event)
        
        hub.subscribe("*", callback)
        
        hub.publish(Event(event_type=EventType.AGENT_CREATED, source="test"))
        hub.publish(Event(event_type=EventType.TASK_CREATED, source="test"))
        
        assert len(events_received) == 2
    
    def test_multiple_subscribers(self):
        """Test multiple subscribers to same event."""
        hub = EventHub()
        received1 = []
        received2 = []
        
        hub.subscribe(EventType.AGENT_CREATED, lambda e: received1.append(e))
        hub.subscribe(EventType.AGENT_CREATED, lambda e: received2.append(e))
        
        event = Event(event_type=EventType.AGENT_CREATED, source="test")
        hub.publish(event)
        
        assert len(received1) == 1
        assert len(received2) == 1
    
    def test_dead_letter_queue(self):
        """Test dead-letter queue for failed events."""
        hub = EventHub()
        
        def failing_callback(event):
            raise Exception("Test error")
        
        hub.subscribe(EventType.AGENT_CREATED, failing_callback)
        
        event = Event(event_type=EventType.AGENT_CREATED, source="test")
        hub.publish(event)
        
        dlq_events = hub.get_dlq_events()
        assert len(dlq_events) > 0
        assert dlq_events[0].error == "Test error"
    
    def test_event_priority(self):
        """Test event priority handling."""
        hub = EventHub()
        
        event_high = Event(
            event_type=EventType.AGENT_CREATED,
            source="test",
            priority=1
        )
        event_low = Event(
            event_type=EventType.AGENT_CREATED,
            source="test",
            priority=-1
        )
        
        assert event_high.priority > event_low.priority
    
    def test_metrics(self):
        """Test metrics collection."""
        hub = EventHub()
        
        received = []
        hub.subscribe(EventType.AGENT_CREATED, lambda e: received.append(e))
        
        for i in range(10):
            hub.publish(Event(event_type=EventType.AGENT_CREATED, source="test"))
        
        metrics = hub.get_metrics()
        assert metrics["events_published"] == 10
        assert metrics["events_processed"] == 10
        assert metrics["subscriber_count"] == 1


class TestEventFilter:
    """Tests for event filtering."""
    
    def test_filter_equals(self):
        """Test EQUALS operator."""
        filter_obj = EventFilter(
            field="event_type",
            operator=FilterOperator.EQUALS,
            value=EventType.AGENT_CREATED
        )
        
        event = Event(event_type=EventType.AGENT_CREATED, source="test")
        assert filter_obj.matches(event)
        
        event = Event(event_type=EventType.AGENT_UPDATED, source="test")
        assert not filter_obj.matches(event)
    
    def test_filter_contains(self):
        """Test CONTAINS operator."""
        filter_obj = EventFilter(
            field="tags",
            operator=FilterOperator.CONTAINS,
            value="important"
        )
        
        event = Event(event_type="test", source="test", tags=["important", "urgent"])
        assert filter_obj.matches(event)
        
        event = Event(event_type="test", source="test", tags=["normal"])
        assert not filter_obj.matches(event)
    
    def test_filter_greater_than(self):
        """Test GREATER_THAN operator."""
        filter_obj = EventFilter(
            field="priority",
            operator=FilterOperator.GREATER_THAN,
            value=0
        )
        
        event = Event(event_type="test", source="test", priority=1)
        assert filter_obj.matches(event)
        
        event = Event(event_type="test", source="test", priority=-1)
        assert not filter_obj.matches(event)
    
    def test_filter_engine_and(self):
        """Test FilterEngine with AND logic."""
        engine = FilterEngine()
        engine.add_filter("event_type", FilterOperator.EQUALS, EventType.AGENT_CREATED)
        engine.add_filter("priority", FilterOperator.GREATER_THAN, 0)
        engine.and_filter()
        
        event = Event(
            event_type=EventType.AGENT_CREATED,
            source="test",
            priority=1
        )
        assert engine.matches(event)
        
        event = Event(
            event_type=EventType.AGENT_CREATED,
            source="test",
            priority=-1
        )
        assert not engine.matches(event)
    
    def test_filter_engine_or(self):
        """Test FilterEngine with OR logic."""
        engine = FilterEngine()
        engine.add_filter("source", FilterOperator.EQUALS, "source1")
        engine.add_filter("source", FilterOperator.EQUALS, "source2")
        engine.or_filter()
        
        event1 = Event(event_type="test", source="source1")
        event2 = Event(event_type="test", source="source2")
        event3 = Event(event_type="test", source="source3")
        
        assert engine.matches(event1)
        assert engine.matches(event2)
        assert not engine.matches(event3)
    
    def test_filter_builder(self):
        """Test FilterBuilder utility."""
        filter1 = FilterBuilder.event_type("test.event")
        assert filter1.matches(Event(event_type="test.event", source="test"))
        
        filter2 = FilterBuilder.has_tag("important")
        assert filter2.matches(Event(
            event_type="test",
            source="test",
            tags=["important"]
        ))
        
        filter3 = FilterBuilder.high_priority()
        assert filter3.matches(Event(event_type="test", source="test", priority=1))
        assert not filter3.matches(Event(event_type="test", source="test", priority=0))


class TestEventRouter:
    """Tests for event routing."""
    
    @pytest.mark.asyncio
    async def test_router_initialization(self):
        """Test EventRouter initialization."""
        router = EventRouter(max_queue_size=5000, workers=4)
        assert router.max_queue_size == 5000
        assert router.workers == 4
    
    def test_subscribe_to_topic(self):
        """Test subscribing to topics."""
        router = EventRouter()
        
        def callback(event):
            pass
        
        sub_id = router.subscribe_to_topic("orders/created", callback)
        assert sub_id is not None
    
    @pytest.mark.asyncio
    async def test_route_event(self):
        """Test routing an event."""
        router = EventRouter()
        events_received = []
        
        def callback(event):
            events_received.append(event)
        
        router.subscribe_to_topic("orders/created", callback)
        
        event = Event(event_type="order.created", source="order_service")
        result = await router.route_event(event, "orders/created")
        
        assert result
        assert router.routed_events > 0
    
    def test_router_add_filter(self):
        """Test adding filters to router."""
        router = EventRouter()
        
        router.add_filter(lambda e: e.priority >= 0)
        
        assert len(router.filters) == 1
    
    def test_router_add_transformer(self):
        """Test adding transformers to router."""
        router = EventRouter()
        
        def add_tag(event):
            event.tags.append("processed")
            return event
        
        router.add_transformer(add_tag)
        
        assert len(router.transformers) == 1
    
    def test_router_metrics(self):
        """Test router metrics."""
        router = EventRouter()
        
        metrics = router.get_metrics()
        
        assert "routed_events" in metrics
        assert "filtered_events" in metrics
        assert "queue_size" in metrics


class TestEventStore:
    """Tests for event persistence."""
    
    def test_store_initialization(self):
        """Test EventStore initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            store = EventStore(db_path=db_path, retention_days=7)
            assert store.db_path == db_path
            assert store.retention_days == 7
    
    def test_store_event(self):
        """Test storing an event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            store = EventStore(db_path=db_path)
            
            event = Event(
                event_type=EventType.AGENT_CREATED,
                source="test",
                payload={"name": "test_agent"}
            )
            
            result = store.store(event)
            assert result
            assert store.events_stored > 0
    
    def test_retrieve_event(self):
        """Test retrieving a stored event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            store = EventStore(db_path=db_path)
            
            event = Event(
                event_type=EventType.AGENT_CREATED,
                source="test",
                payload={"name": "test_agent"}
            )
            
            store.store(event)
            retrieved = store.retrieve(event.event_id)
            
            assert retrieved is not None
            assert retrieved.event_id == event.event_id
            assert retrieved.event_type == event.event_type
    
    def test_query_events(self):
        """Test querying events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            store = EventStore(db_path=db_path)
            
            # Store multiple events
            for i in range(5):
                event = Event(
                    event_type=EventType.AGENT_CREATED,
                    source=f"source_{i}",
                    payload={"index": i}
                )
                store.store(event)
            
            # Query all events
            results = store.query(limit=10)
            assert len(results) > 0
    
    def test_query_by_type(self):
        """Test querying by event type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            store = EventStore(db_path=db_path)
            
            # Store different event types
            store.store(Event(event_type=EventType.AGENT_CREATED, source="test"))
            store.store(Event(event_type=EventType.TASK_CREATED, source="test"))
            
            # Query specific type
            results = store.query(event_type=EventType.AGENT_CREATED)
            assert all(e.event_type == EventType.AGENT_CREATED for e in results)
    
    @pytest.mark.asyncio
    async def test_replay_events(self):
        """Test event replay."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            store = EventStore(db_path=db_path)
            
            # Store events
            now = datetime.utcnow()
            for i in range(3):
                event = Event(
                    event_type=EventType.AGENT_CREATED,
                    source="test",
                    timestamp=(now - timedelta(minutes=i)).isoformat()
                )
                store.store(event)
            
            # Replay events
            replayed_events = []
            async def callback(event):
                replayed_events.append(event)
            
            count = await store.replay_events(
                replay_id="test_replay",
                start_time=(now - timedelta(hours=1)).isoformat(),
                end_time=now.isoformat(),
                callback=callback
            )
            
            assert count > 0
            assert store.replays_executed > 0
    
    def test_store_metrics(self):
        """Test store metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            store = EventStore(db_path=db_path)
            
            for i in range(5):
                store.store(Event(event_type="test", source=f"source_{i}"))
            
            metrics = store.get_metrics()
            
            assert "events_stored" in metrics
            assert "replays_executed" in metrics
            assert metrics["events_stored"] > 0


class TestWebSocketServer:
    """Tests for WebSocket server."""
    
    def test_ws_initialization(self):
        """Test WebSocketServer initialization."""
        ws_server = WebSocketServer(heartbeat_interval=30)
        assert ws_server.heartbeat_interval == 30
        assert ws_server.active_connections == 0
    
    def test_ws_metrics(self):
        """Test WebSocket metrics."""
        ws_server = WebSocketServer()
        
        metrics = ws_server.get_metrics()
        
        assert "total_connections" in metrics
        assert "active_connections" in metrics
        assert "messages_sent" in metrics
        assert "messages_received" in metrics
    
    @pytest.mark.asyncio
    async def test_broadcast_event(self):
        """Test broadcasting events."""
        ws_server = WebSocketServer()
        
        event = Event(
            event_type=EventType.AGENT_CREATED,
            source="test"
        )
        
        # In a real scenario, we'd have actual WebSocket connections
        # For now, test the broadcast infrastructure
        count = await ws_server.broadcast_event(event, "agents/created")
        
        assert ws_server.broadcast_count > 0


class TestIntegration:
    """Integration tests combining multiple components."""
    
    def test_hub_to_store_integration(self):
        """Test EventHub publishing to EventStore."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            
            hub = EventHub()
            store = EventStore(db_path=db_path)
            
            # Subscribe hub to store events
            hub.subscribe("*", lambda e: store.store(e))
            
            # Publish events
            for i in range(5):
                hub.publish(Event(
                    event_type=f"event.{i}",
                    source="test"
                ))
            
            # Verify stored
            results = store.query(limit=10)
            assert len(results) == 5
    
    def test_filter_engine_integration(self):
        """Test FilterEngine with EventHub."""
        hub = EventHub()
        received = []
        
        # Create filtered subscription
        def filtered_callback(event):
            engine = FilterEngine()
            engine.add_filter("priority", FilterOperator.GREATER_THAN, 0)
            if engine.matches(event):
                received.append(event)
        
        hub.subscribe("*", filtered_callback)
        
        # Publish events with different priorities
        hub.publish(Event(event_type="test", source="test", priority=1))
        hub.publish(Event(event_type="test", source="test", priority=-1))
        hub.publish(Event(event_type="test", source="test", priority=0))
        
        # Only high priority should be in received
        assert len(received) == 1
        assert received[0].priority > 0


class TestPerformance:
    """Performance and load tests."""
    
    def test_hub_throughput(self):
        """Test EventHub throughput."""
        hub = EventHub()
        
        event_count = 0
        def counter(event):
            nonlocal event_count
            event_count += 1
        
        hub.subscribe("*", counter)
        
        # Publish events and measure throughput
        start = time.time()
        for i in range(1000):
            hub.publish(Event(event_type="test", source="test"))
        elapsed = time.time() - start
        
        throughput = 1000 / elapsed
        assert throughput > 100  # Should handle at least 100 events/sec
        assert hub.events_published == 1000
    
    def test_store_bulk_insert(self):
        """Test bulk event insertion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            store = EventStore(db_path=db_path)
            
            # Insert events
            start = time.time()
            for i in range(100):
                store.store(Event(
                    event_type=f"event.{i % 5}",
                    source="test"
                ))
            elapsed = time.time() - start
            
            assert store.events_stored == 100
            # Should complete in reasonable time
            assert elapsed < 10
    
    def test_filter_performance(self):
        """Test filter matching performance."""
        engine = FilterEngine()
        engine.add_filter("event_type", FilterOperator.EQUALS, "important")
        engine.add_filter("priority", FilterOperator.GREATER_THAN, 0)
        engine.and_filter()
        
        # Test matching 1000 events
        start = time.time()
        for i in range(1000):
            event = Event(
                event_type="important" if i % 10 == 0 else "normal",
                source="test",
                priority=1 if i % 5 == 0 else -1
            )
            engine.matches(event)
        elapsed = time.time() - start
        
        # Should be very fast
        assert elapsed < 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
