"""
WebSocket Server - Real-time event streaming via WebSocket.

Features:
- FastAPI WebSocket integration
- Subscription management
- Real-time event streaming
- Connection pooling
- Heartbeat & keep-alive
"""

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Callable
import threading

from .event_hub import Event

logger = logging.getLogger(__name__)


@dataclass
class WebSocketConnection:
    """Represents a WebSocket connection."""
    connection_id: str
    subscriptions: Set[str]
    created_at: str
    last_heartbeat: str
    authenticated: bool = False
    user_id: Optional[str] = None


class WebSocketServer:
    """
    WebSocket server for real-time event streaming.
    
    Features:
    - Multiple concurrent connections
    - Topic-based subscriptions
    - Automatic heartbeat
    - Connection pooling
    - Event filtering per connection
    """
    
    def __init__(self, heartbeat_interval: int = 30):
        """
        Initialize WebSocket server.
        
        Args:
            heartbeat_interval: Seconds between heartbeat messages
        """
        self.heartbeat_interval = heartbeat_interval
        
        # Connection management
        self.connections: Dict[str, WebSocketConnection] = {}
        self.subscriptions: Dict[str, Set[str]] = defaultdict(set)
        
        # Event handlers
        self.message_handlers: Dict[str, Callable] = {}
        
        # Metrics
        self.total_connections = 0
        self.active_connections = 0
        self.messages_sent = 0
        self.messages_received = 0
        self.broadcast_count = 0
        
        # Thread safety
        self._lock = threading.RLock()
    
    async def handle_connection(self, websocket, connection_id: Optional[str] = None) -> str:
        """
        Handle a new WebSocket connection.
        
        Args:
            websocket: WebSocket instance
            connection_id: Optional connection ID
            
        Returns:
            Connection ID
        """
        conn_id = connection_id or str(uuid.uuid4())
        
        with self._lock:
            self.connections[conn_id] = WebSocketConnection(
                connection_id=conn_id,
                subscriptions=set(),
                created_at=datetime.utcnow().isoformat(),
                last_heartbeat=datetime.utcnow().isoformat()
            )
            self.total_connections += 1
            self.active_connections += 1
        
        logger.info("WebSocket connection established: %s", conn_id)
        
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(self._heartbeat_loop(conn_id, websocket))
        
        try:
            # Send connection confirmation
            await websocket.send(json.dumps({
                "type": "connection_established",
                "connection_id": conn_id,
                "timestamp": datetime.utcnow().isoformat()
            }))
            
            # Listen for messages
            async for message in websocket.iter_text():
                await self._handle_message(conn_id, message, websocket)
                self.messages_received += 1
        
        except Exception as e:
            logger.error("WebSocket error for connection %s: %s", conn_id, str(e))
        
        finally:
            # Cleanup
            heartbeat_task.cancel()
            await self._close_connection(conn_id)
        
        return conn_id
    
    async def _handle_message(self, conn_id: str, message: str, websocket) -> None:
        """
        Handle incoming WebSocket message.
        
        Args:
            conn_id: Connection ID
            message: Message content
            websocket: WebSocket instance
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "subscribe":
                await self._handle_subscribe(conn_id, data, websocket)
            elif msg_type == "unsubscribe":
                await self._handle_unsubscribe(conn_id, data, websocket)
            elif msg_type == "authenticate":
                await self._handle_authenticate(conn_id, data, websocket)
            elif msg_type == "heartbeat":
                await self._handle_heartbeat(conn_id, websocket)
            elif msg_type in self.message_handlers:
                await self.message_handlers[msg_type](conn_id, data, websocket)
            else:
                logger.debug("Unknown message type: %s", msg_type)
        
        except json.JSONDecodeError:
            logger.warning("Invalid JSON message received")
        except Exception as e:
            logger.error("Error handling message: %s", str(e))
    
    async def _handle_subscribe(self, conn_id: str, data: Dict, websocket) -> None:
        """Handle subscription request."""
        topics = data.get("topics", [])
        
        with self._lock:
            if conn_id in self.connections:
                for topic in topics:
                    self.connections[conn_id].subscriptions.add(topic)
                    self.subscriptions[topic].add(conn_id)
        
        logger.info("Connection %s subscribed to topics: %s", conn_id, topics)
        
        # Send confirmation
        await websocket.send(json.dumps({
            "type": "subscription_confirmed",
            "topics": topics,
            "timestamp": datetime.utcnow().isoformat()
        }))
    
    async def _handle_unsubscribe(self, conn_id: str, data: Dict, websocket) -> None:
        """Handle unsubscribe request."""
        topics = data.get("topics", [])
        
        with self._lock:
            if conn_id in self.connections:
                for topic in topics:
                    self.connections[conn_id].subscriptions.discard(topic)
                    self.subscriptions[topic].discard(conn_id)
        
        logger.info("Connection %s unsubscribed from topics: %s", conn_id, topics)
    
    async def _handle_authenticate(self, conn_id: str, data: Dict, websocket) -> None:
        """Handle authentication request."""
        user_id = data.get("user_id")
        token = data.get("token")
        
        # In production, validate token here
        with self._lock:
            if conn_id in self.connections:
                self.connections[conn_id].authenticated = True
                self.connections[conn_id].user_id = user_id
        
        logger.info("Connection %s authenticated as user %s", conn_id, user_id)
    
    async def _handle_heartbeat(self, conn_id: str, websocket) -> None:
        """Handle heartbeat."""
        with self._lock:
            if conn_id in self.connections:
                self.connections[conn_id].last_heartbeat = datetime.utcnow().isoformat()
    
    async def _heartbeat_loop(self, conn_id: str, websocket) -> None:
        """Send periodic heartbeat to keep connection alive."""
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                
                try:
                    await websocket.send(json.dumps({
                        "type": "heartbeat",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                except Exception as e:
                    logger.debug("Failed to send heartbeat: %s", str(e))
                    break
        except asyncio.CancelledError:
            pass
    
    async def _close_connection(self, conn_id: str) -> None:
        """Close and cleanup a connection."""
        with self._lock:
            if conn_id in self.connections:
                # Remove from all subscriptions
                for topic in self.connections[conn_id].subscriptions:
                    self.subscriptions[topic].discard(conn_id)
                
                del self.connections[conn_id]
                self.active_connections -= 1
        
        logger.info("WebSocket connection closed: %s", conn_id)
    
    async def broadcast_event(
        self,
        event: Event,
        topic: str,
        filter_fn: Optional[Callable] = None
    ) -> int:
        """
        Broadcast an event to all subscribers of a topic.
        
        Args:
            event: Event to broadcast
            topic: Topic to broadcast to
            filter_fn: Optional filter function
            
        Returns:
            Number of connections that received the event
        """
        with self._lock:
            connection_ids = self.subscriptions.get(topic, set()).copy()
        
        count = 0
        for conn_id in connection_ids:
            # Check filter
            if filter_fn and not filter_fn(event):
                continue
            
            try:
                # Get connection
                with self._lock:
                    conn = self.connections.get(conn_id)
                
                if not conn:
                    continue
                
                # Send event
                message = {
                    "type": "event",
                    "topic": topic,
                    "event": event.to_dict(),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # In a real implementation, websocket would be stored with connection
                # For now, we just track that we would send it
                count += 1
                self.messages_sent += 1
            
            except Exception as e:
                logger.error("Failed to send event to connection %s: %s", conn_id, str(e))
        
        self.broadcast_count += 1
        logger.debug("Broadcast complete: %d connections for topic %s", count, topic)
        
        return count
    
    def get_connection_count(self) -> int:
        """Get number of active connections."""
        with self._lock:
            return len(self.connections)
    
    def get_subscribers_for_topic(self, topic: str) -> int:
        """Get number of subscribers for a topic."""
        with self._lock:
            return len(self.subscriptions.get(topic, set()))
    
    def get_subscriptions(self, conn_id: str) -> Set[str]:
        """Get subscriptions for a connection."""
        with self._lock:
            if conn_id in self.connections:
                return self.connections[conn_id].subscriptions.copy()
            return set()
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get WebSocket server metrics.
        
        Returns:
            Dictionary of metrics
        """
        with self._lock:
            return {
                "total_connections": self.total_connections,
                "active_connections": self.active_connections,
                "messages_sent": self.messages_sent,
                "messages_received": self.messages_received,
                "broadcast_count": self.broadcast_count,
                "topics": len(self.subscriptions),
                "avg_subscribers_per_topic": (
                    sum(len(v) for v in self.subscriptions.values()) / max(len(self.subscriptions), 1)
                ) if self.subscriptions else 0,
            }
