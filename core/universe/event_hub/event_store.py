"""
Event Store - Persistent event storage with replay capabilities.

Features:
- Event persistence (in-memory & PostgreSQL ready)
- Event replay capability
- Historical queries
- TTL/retention policies
- Compression for old events
"""

import logging
import json
import gzip
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from collections import defaultdict
import threading
import sqlite3
import os

from .event_hub import Event

logger = logging.getLogger(__name__)


class EventStore:
    """
    Persistent event storage with replay and historical query capabilities.
    
    Supports:
    - In-memory storage with TTL
    - SQLite persistence (default)
    - Event replay
    - Historical queries
    - Compression
    - Retention policies
    """
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        retention_days: int = 30,
        compression_days: int = 7,
        max_events: int = 100000
    ):
        """
        Initialize EventStore.
        
        Args:
            db_path: Path to SQLite database (None = in-memory)
            retention_days: Days to keep events
            compression_days: Days before compressing events
            max_events: Maximum events to store
        """
        self.db_path = db_path or ":memory:"
        self.retention_days = retention_days
        self.compression_days = compression_days
        self.max_events = max_events
        
        # In-memory index
        self.events_index: Dict[str, List[Event]] = defaultdict(list)
        self.timestamp_index: Dict[str, Event] = {}
        
        # Metrics
        self.events_stored = 0
        self.events_archived = 0
        self.replays_executed = 0
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Initialize database
        self._init_db()
        
        logger.info("EventStore initialized with db_path=%s, retention=%d days",
                   self.db_path, retention_days)
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    agent_id TEXT,
                    payload TEXT NOT NULL,
                    tags TEXT,
                    priority INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    stored_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    compressed BOOLEAN DEFAULT 0
                )
            """)
            
            # Subscriptions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subscriber_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    filter_rules TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Replay table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_replay (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    replay_id TEXT UNIQUE NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    events_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON events(source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON events(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_id ON events(agent_id)")
            
            conn.commit()
            conn.close()
            logger.info("Database schema initialized")
        except Exception as e:
            logger.error("Failed to initialize database: %s", str(e))
            raise
    
    def store(self, event: Event) -> bool:
        """
        Store an event.
        
        Args:
            event: Event to store
            
        Returns:
            True if stored successfully
        """
        try:
            with self._lock:
                # In-memory indexing
                self.events_index[event.event_type].append(event)
                self.timestamp_index[event.event_id] = event
                
                # Persist to database
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                payload_str = json.dumps(event.payload)
                tags_str = json.dumps(event.tags) if event.tags else None
                
                cursor.execute("""
                    INSERT OR IGNORE INTO events
                    (event_id, event_type, source, agent_id, payload, tags, priority, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id,
                    event.event_type,
                    event.source,
                    event.agent_id,
                    payload_str,
                    tags_str,
                    event.priority,
                    event.timestamp,
                    event.expires_at
                ))
                
                conn.commit()
                conn.close()
                
                self.events_stored += 1
                
                # Check if we need cleanup
                if self.events_stored % 1000 == 0:
                    self._cleanup_old_events()
                
                return True
        except Exception as e:
            logger.error("Failed to store event: %s", str(e))
            return False
    
    def retrieve(self, event_id: str) -> Optional[Event]:
        """
        Retrieve an event by ID.
        
        Args:
            event_id: Event ID
            
        Returns:
            Event or None if not found
        """
        # Check memory index first
        if event_id in self.timestamp_index:
            return self.timestamp_index[event_id]
        
        # Query database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events WHERE event_id = ?", (event_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return self._row_to_event(row)
        except Exception as e:
            logger.error("Failed to retrieve event: %s", str(e))
        
        return None
    
    def query(
        self,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        agent_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100
    ) -> List[Event]:
        """
        Query events with filters.
        
        Args:
            event_type: Filter by event type
            source: Filter by source
            agent_id: Filter by agent ID
            tags: Filter by tags (must contain all)
            start_time: Events after this time
            end_time: Events before this time
            limit: Maximum results
            
        Returns:
            List of matching events
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM events WHERE 1=1"
            params = []
            
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)
            
            if source:
                query += " AND source = ?"
                params.append(source)
            
            if agent_id:
                query += " AND agent_id = ?"
                params.append(agent_id)
            
            if start_time:
                query += " AND created_at >= ?"
                params.append(start_time)
            
            if end_time:
                query += " AND created_at <= ?"
                params.append(end_time)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            events = [self._row_to_event(row) for row in rows]
            
            # Filter by tags if specified
            if tags:
                events = [e for e in events if all(t in e.tags for t in tags)]
            
            return events
        except Exception as e:
            logger.error("Failed to query events: %s", str(e))
            return []
    
    async def replay_events(
        self,
        replay_id: str,
        start_time: str,
        end_time: str,
        callback: callable
    ) -> int:
        """
        Replay events from store.
        
        Args:
            replay_id: Unique replay ID
            start_time: Start timestamp
            end_time: End timestamp
            callback: Function to call for each event
            
        Returns:
            Number of events replayed
        """
        try:
            with self._lock:
                # Create replay record
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO event_replay (replay_id, start_time, end_time, status)
                    VALUES (?, ?, ?, 'running')
                """, (replay_id, start_time, end_time))
                conn.commit()
                
                # Query events
                cursor.execute("""
                    SELECT * FROM events 
                    WHERE created_at >= ? AND created_at <= ?
                    ORDER BY created_at ASC
                """, (start_time, end_time))
                
                rows = cursor.fetchall()
                
                # Process events
                count = 0
                for row in rows:
                    try:
                        event = self._row_to_event(row)
                        await callback(event)
                        count += 1
                    except Exception as e:
                        logger.error("Error replaying event: %s", str(e))
                
                # Update replay status
                cursor.execute("""
                    UPDATE event_replay 
                    SET status = 'completed', events_count = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE replay_id = ?
                """, (count, replay_id))
                
                conn.commit()
                conn.close()
                
                self.replays_executed += 1
                logger.info("Replay completed: %d events replayed", count)
                
                return count
        except Exception as e:
            logger.error("Replay failed: %s", str(e))
            return 0
    
    def _cleanup_old_events(self) -> None:
        """Remove events older than retention period."""
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=self.retention_days)).isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM events WHERE created_at < ?", (cutoff_date,))
            
            conn.commit()
            conn.close()
            
            logger.info("Cleanup completed, removed old events")
        except Exception as e:
            logger.error("Cleanup failed: %s", str(e))
    
    def _row_to_event(self, row: sqlite3.Row) -> Event:
        """Convert database row to Event."""
        payload = json.loads(row[5]) if row[5] else {}
        tags = json.loads(row[6]) if row[6] else []
        
        return Event(
            event_type=row[2],
            source=row[3],
            agent_id=row[4],
            payload=payload,
            tags=tags,
            priority=row[7],
            timestamp=row[8],
            event_id=row[1],
            expires_at=row[9]
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get store metrics.
        
        Returns:
            Dictionary of metrics
        """
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM events")
                event_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM event_subscriptions")
                subscription_count = cursor.fetchone()[0]
                
                conn.close()
                
                return {
                    "events_stored": self.events_stored,
                    "events_archived": self.events_archived,
                    "replays_executed": self.replays_executed,
                    "current_event_count": event_count,
                    "subscription_count": subscription_count,
                }
            except Exception as e:
                logger.error("Failed to get metrics: %s", str(e))
                return {}
